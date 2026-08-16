"""SiteDown fault injection catalog — IT Operations themed."""

import json, os, time, logging
from config import FAULT_STATE_FILE

logger = logging.getLogger("sitedown.faults")

FAULT_CATALOG = [
    # ── Application tier ──────────────────────────────────────────────
    {
        "id": "APP-01", "tier": "Application", "severity": "critical",
        "name": "API gateway 5xx surge",
        "description": "Returns 502/503 on 40% of API gateway requests. Simulates upstream service crash behind load balancer.",
        "signals": {
            "metrics": ["http.status_code:5xx rate spikes to 40%", "sitedown.gateway.error_rate crosses threshold"],
            "logs": ["ERROR api_gateway upstream=svc-users status=502 retry=3/3"],
            "traces": ["Gateway span shows upstream_connection_refused on service map"],
            "monitors": ["API error rate > 5% — P1 on-call page"]
        }
    },
    {
        "id": "APP-02", "tier": "Application", "severity": "warning",
        "name": "OAuth/SSO provider timeout",
        "description": "Adds 30s timeout to SSO token validation. All authenticated endpoints block.",
        "signals": {
            "metrics": ["auth.validation_latency spikes to 30s", "sitedown.auth.timeout_count increments"],
            "logs": ["ERROR sso_validation provider=azure_ad status=timeout duration=30s"],
            "traces": ["Auth middleware span dominates every request trace"],
            "monitors": ["SSO validation P99 > 5s — security + platform team"]
        }
    },
    {
        "id": "APP-03", "tier": "Application", "severity": "critical",
        "name": "Message queue consumer lag",
        "description": "Pauses Kafka consumer group. Messages accumulate with growing consumer lag.",
        "signals": {
            "metrics": ["sitedown.kafka.consumer_lag grows linearly", "sitedown.kafka.messages_consumed_rate drops to 0"],
            "logs": ["CRITICAL kafka_consumer group=order-processor status=paused partitions=12"],
            "traces": ["Message processing pipeline shows no new spans"],
            "monitors": ["Kafka consumer lag > 10000 — P1 platform team"]
        }
    },
    {
        "id": "APP-04", "tier": "Application", "severity": "warning",
        "name": "CDN cache purge storm",
        "description": "Triggers mass cache invalidation. Origin servers absorb full traffic load.",
        "signals": {
            "metrics": ["sitedown.cdn.cache_hit_rate drops from 95% to 5%", "sitedown.origin.request_rate spikes 20x"],
            "logs": ["WARN cdn_cache_miss rate=95% origin_load=critical"],
            "traces": ["All frontend traces show origin fetch instead of cache hit"],
            "monitors": ["CDN cache hit rate < 50% — infrastructure team Slack"]
        }
    },
    {
        "id": "APP-05", "tier": "Application", "severity": "warning",
        "name": "Webhook delivery failure",
        "description": "Returns 5xx on outbound webhook delivery. Retry queue grows with DLQ overflow.",
        "signals": {
            "metrics": ["sitedown.webhooks.failure_rate spikes >30%", "sitedown.webhooks.dlq_depth grows"],
            "logs": ["ERROR webhook_delivery url=https://partner.api/callback status=503 attempt=5/5"],
            "traces": ["Webhook delivery span shows connection_timeout to partner"],
            "monitors": ["Webhook failure rate > 10% — integrations team"]
        }
    },
    # ── Database tier ─────────────────────────────────────────────────
    {
        "id": "DB-01", "tier": "Database", "severity": "warning",
        "name": "Primary-replica replication lag",
        "description": "Write-heavy migration causes replica lag >45s. Read-after-write consistency broken.",
        "signals": {
            "metrics": ["postgresql.replication_delay >45s", "db.active_connections saturating"],
            "logs": ["WARN replication_lag replica=db-read-01 lag_seconds=48"],
            "traces": ["Read-path spans tagged consistency_violation=true"],
            "monitors": ["Replication lag >15s — database team alert"]
        }
    },
    {
        "id": "DB-02", "tier": "Database", "severity": "critical",
        "name": "Connection pool exhaustion",
        "description": "ORM connection leak during deployment rollout. All services lose DB access.",
        "signals": {
            "metrics": ["db.pool.active hits db.pool.max (300/300)", "http.request.duration spikes globally"],
            "logs": ["ERROR pool_timeout service=api-core waited=30s error=cannot_acquire"],
            "traces": ["Every service span blocked at db_pool_wait"],
            "monitors": ["DB pool utilization >90% composite — P1 platform"]
        }
    },
    {
        "id": "DB-03", "tier": "Database", "severity": "warning",
        "name": "Redis cache eviction storm",
        "description": "Fills Redis memory to maxmemory limit. LRU evictions cause cache miss cascade.",
        "signals": {
            "metrics": ["redis.mem.used approaches redis.mem.maxmemory", "redis.keys.evicted spikes"],
            "logs": ["WARN redis_eviction policy=allkeys-lru evicted_keys=8400/min"],
            "traces": ["Cache miss spans cascade into DB read spans"],
            "monitors": ["Redis eviction rate anomaly — platform team"]
        }
    },
    {
        "id": "DB-04", "tier": "Database", "severity": "critical",
        "name": "Compliance audit log failure",
        "description": "Fills SOC 2 audit log partition. Regulatory write failures.",
        "signals": {
            "metrics": ["system.disk.pct_usage{mount:/var/log/audit} hits 100%", "sitedown.audit.write_failures increments"],
            "logs": ["FATAL disk_full partition=/var/log/audit error=ENOSPC"],
            "traces": ["Audit write span returns disk_full"],
            "monitors": ["Audit log failure — P1 + compliance team"]
        }
    },
    # ── Infrastructure tier ───────────────────────────────────────────
    {
        "id": "INF-01", "tier": "Infrastructure", "severity": "warning",
        "name": "Kubernetes node CPU pressure",
        "description": "stress-ng CPU burn causing pod evictions. Scheduler unable to place new pods.",
        "signals": {
            "metrics": ["system.cpu.user >95% on k8s-worker-03", "kubernetes.cpu.requests.pct >100%"],
            "logs": ["WARN node_pressure node=k8s-worker-03 condition=CPUPressure"],
            "traces": ["Pod startup spans show scheduling_failed"],
            "monitors": ["K8s node CPU pressure — cluster ops alert"]
        }
    },
    {
        "id": "INF-02", "tier": "Infrastructure", "severity": "critical",
        "name": "Persistent volume I/O degradation",
        "description": "I/O throttling on EBS/PV volume. Database and logging services impacted.",
        "signals": {
            "metrics": ["system.io.await jumps from 2ms to 300ms+", "kubernetes.io.write_bytes throttled"],
            "logs": ["WARN blk_update_request I/O error dev=xvdf sector=..."],
            "traces": ["All DB-dependent spans show proportional slowdown"],
            "monitors": ["PV I/O latency anomaly — storage + platform"]
        }
    },
    {
        "id": "INF-03", "tier": "Infrastructure", "severity": "critical",
        "name": "Container CrashLoopBackOff",
        "description": "Critical service container enters crash loop. Kubernetes restart backoff increasing.",
        "signals": {
            "metrics": ["kubernetes.containers.restarts spikes on api-core", "kubernetes.pods.running decreases"],
            "logs": ["FATAL container=api-core status=CrashLoopBackOff restart_count=8 backoff=5m"],
            "traces": ["Service map shows api-core node flapping red/grey"],
            "monitors": ["Pod CrashLoopBackOff — P1 platform on-call"]
        }
    },
    {
        "id": "INF-04", "tier": "Infrastructure", "severity": "info",
        "name": "SSL/TLS certificate expiration",
        "description": "Sets wildcard cert expiry to 7 days. Tests cert-manager alerting.",
        "signals": {
            "metrics": ["Synthetics: ssl.days_remaining drops below 14"],
            "logs": ["cert-manager: certificate renewal failed: acme challenge timeout"],
            "traces": [],
            "monitors": ["SSL cert expiry <14 days — infra team Slack"]
        }
    },
    # ── Network / SNMP tier ───────────────────────────────────────────
    {
        "id": "NET-01", "tier": "Network", "severity": "warning",
        "name": "SNMP agent unreachable",
        "description": "Stops snmpd on core switch. Network visibility gap in NDM.",
        "signals": {
            "metrics": ["snmp.can_check returns 0", "NDM: device goes grey"],
            "logs": ["WARN snmp_check host=core-sw-01 error=request_timeout"],
            "traces": [],
            "monitors": ["SNMP device unreachable — 3 consecutive failures"]
        }
    },
    {
        "id": "NET-02", "tier": "Network", "severity": "critical",
        "name": "SNMP trap: UPS on battery",
        "description": "Sends UPS on-battery trap. Data center power event.",
        "signals": {
            "metrics": ["snmp.ups.battery_pct dropping", "snmp.ups.on_battery = true"],
            "logs": ["CRITICAL trap_oid=1.3.6.1.2.1.33.1.6.3.2 source=ups-dc-01"],
            "traces": [],
            "monitors": ["UPS on battery — P1 facilities + DR activation check"]
        }
    },
    {
        "id": "NET-03", "tier": "Network", "severity": "warning",
        "name": "BGP peer flap",
        "description": "Oscillates BGP session with upstream ISP. Route convergence causes packet loss.",
        "signals": {
            "metrics": ["snmp.bgp.peer_state oscillates established/idle", "sitedown.bgp.flap_count increments"],
            "logs": ["WARN bgp_peer neighbor=203.0.113.1 state=idle reason=hold_timer_expired"],
            "traces": [],
            "monitors": ["BGP peer flap >3 in 10 min — network team page"]
        }
    },
    {
        "id": "NET-04", "tier": "Network", "severity": "warning",
        "name": "Load balancer health check failure",
        "description": "Fails LB health checks for backend pool. Traffic shifts to remaining nodes.",
        "signals": {
            "metrics": ["sitedown.lb.healthy_backends drops from 6 to 2", "sitedown.lb.request_distribution skewed"],
            "logs": ["WARN lb_health_check backend=api-pool-03 status=unhealthy consecutive=5"],
            "traces": ["Remaining backend spans show increased load/latency"],
            "monitors": ["LB healthy backends < 50% — platform team alert"]
        }
    },
    # ── CI/CD & DevOps tier ───────────────────────────────────────────
    {
        "id": "DEV-01", "tier": "CI/CD & DevOps", "severity": "critical",
        "name": "Deployment pipeline failure",
        "description": "Fails canary deployment health check. Rollback triggered but stuck in progress.",
        "signals": {
            "metrics": ["sitedown.deploy.canary_error_rate spikes >10%", "sitedown.deploy.rollback_status = in_progress"],
            "logs": ["CRITICAL deployment canary=api-v2.4.1 error_rate=14% threshold=5% action=rollback"],
            "traces": ["Canary traffic spans show elevated error rate vs baseline"],
            "monitors": ["Deployment canary failure — P1 release engineering"]
        }
    },
    {
        "id": "DEV-02", "tier": "CI/CD & DevOps", "severity": "warning",
        "name": "Container registry unavailable",
        "description": "Returns 503 on image pull from internal registry. New deployments and scale-outs blocked.",
        "signals": {
            "metrics": ["sitedown.registry.pull_failures increments", "kubernetes.pods.pending increases"],
            "logs": ["ERROR image_pull image=registry.internal/api-core:v2.4.1 error=503"],
            "traces": ["Pod startup spans show image_pull_backoff"],
            "monitors": ["Registry pull failure rate > 5% — platform team"]
        }
    },
    {
        "id": "DEV-03", "tier": "CI/CD & DevOps", "severity": "warning",
        "name": "Secret rotation failure",
        "description": "Vault secret rotation fails. Services using expiring credentials approach auth deadline.",
        "signals": {
            "metrics": ["sitedown.vault.rotation_failures increments", "sitedown.vault.secret_ttl_remaining decreasing"],
            "logs": ["ERROR vault_rotation path=secret/db/prod error=permission_denied lease_ttl=1800s"],
            "traces": ["Vault renewal span shows permission_denied"],
            "monitors": ["Secret TTL < 30 min — security + platform team"]
        }
    },
    {
        "id": "DEV-04", "tier": "CI/CD & DevOps", "severity": "critical",
        "name": "Terraform state lock contention",
        "description": "DynamoDB state lock held by zombie apply. All infrastructure changes blocked.",
        "signals": {
            "metrics": ["sitedown.terraform.lock_wait_seconds growing", "sitedown.terraform.blocked_runs increments"],
            "logs": ["CRITICAL terraform_lock state=locked lock_id=abc123 held_for=3600s"],
            "traces": [],
            "monitors": ["Terraform state locked > 30 min — infra team immediate"]
        }
    },
]

class FaultEngine:
    def __init__(self):
        self.catalog = {f["id"]: f for f in FAULT_CATALOG}
        self.active_faults = {}
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(FAULT_STATE_FILE):
                with open(FAULT_STATE_FILE, "r") as f:
                    self.active_faults = json.load(f)
        except Exception:
            self.active_faults = {}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(FAULT_STATE_FILE), exist_ok=True)
            with open(FAULT_STATE_FILE, "w") as f:
                json.dump(self.active_faults, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save fault state: {e}")

    def activate(self, fault_id):
        if fault_id not in self.catalog:
            return {"error": f"Unknown fault: {fault_id}"}
        self.active_faults[fault_id] = {"activated_at": time.time(), "fault": self.catalog[fault_id]}
        self._save_state()
        logger.warning(f"FAULT ACTIVATED: {fault_id} — {self.catalog[fault_id]['name']}")
        return {"status": "activated", "fault_id": fault_id}

    def deactivate(self, fault_id):
        if fault_id in self.active_faults:
            del self.active_faults[fault_id]
            self._save_state()
            logger.info(f"FAULT DEACTIVATED: {fault_id}")
        return {"status": "deactivated", "fault_id": fault_id}

    def is_active(self, fault_id): return fault_id in self.active_faults
    def get_active_faults(self): return list(self.active_faults.keys())

    def get_catalog_by_tier(self):
        tiers = {}
        for fault in FAULT_CATALOG:
            tier = fault["tier"]
            if tier not in tiers: tiers[tier] = []
            tiers[tier].append({**fault, "active": self.is_active(fault["id"])})
        return tiers

    def get_dashboard_effects(self):
        return {fid: self.catalog[fid]["name"] for fid in self.active_faults}

engine = FaultEngine()
