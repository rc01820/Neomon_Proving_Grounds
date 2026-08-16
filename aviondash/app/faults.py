"""AvionDash fault injection catalog — Aviation / FAA themed."""

import json, os, time, logging
from config import FAULT_STATE_FILE

logger = logging.getLogger("aviondash.faults")

FAULT_CATALOG = [
    # ── Application tier ──────────────────────────────────────────────
    {
        "id": "APP-01", "tier": "Application", "severity": "critical",
        "name": "Flight tracking API latency",
        "description": "Adds 3-10s artificial latency to flight position API responses. Simulates ADS-B feed processing delays.",
        "signals": {
            "metrics": ["http.request.duration spikes on /api/flights/*", "aviondash.flight_tracking.latency_p99 crosses 5s"],
            "logs": ["WARN slow_response endpoint=/api/flights/positions duration=8.4s"],
            "traces": ["Flight tracking service span shows upstream ADS-B timeout"],
            "monitors": ["Flight tracking P99 latency > 3s — PagerDuty escalation"]
        }
    },
    {
        "id": "APP-02", "tier": "Application", "severity": "critical",
        "name": "NOTAM distribution failure",
        "description": "Drops NOTAM push notifications to subscribing systems. Simulates message broker partition.",
        "signals": {
            "metrics": ["aviondash.notam.delivery_rate drops to 0", "aviondash.notam.queue_depth grows linearly"],
            "logs": ["ERROR notam_distributor channel=notam_push state=DISCONNECTED"],
            "traces": ["NOTAM publish span returns broker_unavailable error"],
            "monitors": ["NOTAM delivery rate anomaly detection alert"]
        }
    },
    {
        "id": "APP-03", "tier": "Application", "severity": "warning",
        "name": "Weather data ingestion delay",
        "description": "Introduces 5-minute staleness in METAR/TAF weather feeds. Simulates upstream NWS API degradation.",
        "signals": {
            "metrics": ["aviondash.weather.data_age_seconds exceeds 300", "aviondash.weather.refresh_errors increments"],
            "logs": ["WARN weather_feed source=nws staleness=312s threshold=60s"],
            "traces": ["Weather ingestion pipeline trace shows HTTP 503 from upstream"],
            "monitors": ["Weather data staleness > 5 min — ops team Slack"]
        }
    },
    {
        "id": "APP-04", "tier": "Application", "severity": "warning",
        "name": "Pilot authentication timeout",
        "description": "Returns 504 on pilot SSO token validation. Simulates IdP connection pool exhaustion.",
        "signals": {
            "metrics": ["auth.failure_rate jumps from 0.1% to 85%", "aviondash.auth.timeout_count increments"],
            "logs": ["ERROR sso_validation status=504 provider=okta timeout=30s"],
            "traces": ["Auth middleware span shows gateway_timeout"],
            "monitors": ["Synthetics: pilot portal login check fails"]
        }
    },
    # ── Database tier ─────────────────────────────────────────────────
    {
        "id": "DB-01", "tier": "Database", "severity": "warning",
        "name": "Flight plan DB replication lag",
        "description": "Write-heavy flight plan updates cause replica lag >30s. Read replicas serve stale routing data.",
        "signals": {
            "metrics": ["postgresql.replication_delay >30s", "db.active_connections near pool max"],
            "logs": ["WARN replication_lag replica=flightdb-ro-1 lag_bytes=524288000"],
            "traces": ["DB read span tagged with stale_read=true"],
            "monitors": ["Replication lag >10s threshold alert"]
        }
    },
    {
        "id": "DB-02", "tier": "Database", "severity": "critical",
        "name": "Connection pool exhaustion",
        "description": "Leaks DB connections during surge in flight plan amendments. Pool hits max capacity.",
        "signals": {
            "metrics": ["db.pool.active hits db.pool.max (200/200)", "http.request.duration spikes across all endpoints"],
            "logs": ["ERROR pool_timeout waited=30s error=cannot_acquire_connection"],
            "traces": ["All API spans show db_connection_wait dominating flamegraph"],
            "monitors": ["DB connection pool >90% composite alert"]
        }
    },
    {
        "id": "DB-03", "tier": "Database", "severity": "warning",
        "name": "Slow query on flight history",
        "description": "Drops index on flight_history table, causing full table scans on historical lookups.",
        "signals": {
            "metrics": ["DBM: query.avg_time jumps 50x on flight_history queries", "rows_examined/rows_returned ratio >1000:1"],
            "logs": ["WARN slow_query duration=12.4s table=flight_history scan=sequential"],
            "traces": ["DB span dominates request flamegraph at 94% of total duration"],
            "monitors": ["Slow query count anomaly detection"]
        }
    },
    {
        "id": "DB-04", "tier": "Database", "severity": "critical",
        "name": "Audit log partition full",
        "description": "Fills FAA-mandated audit log partition to 100%. Compliance-critical write failures.",
        "signals": {
            "metrics": ["system.disk.pct_usage{mount:/var/lib/audit} hits 100%", "aviondash.audit_write_failures increments"],
            "logs": ["FATAL disk_full partition=/var/lib/audit error=ENOSPC"],
            "traces": ["Audit write span returns disk_full error tag"],
            "monitors": ["FAA audit log write failure — P1 escalation"]
        }
    },
    # ── Infrastructure tier ───────────────────────────────────────────
    {
        "id": "INF-01", "tier": "Infrastructure", "severity": "warning",
        "name": "CPU saturation on tracking server",
        "description": "stress-ng CPU burn simulating ADS-B processing overload during high traffic volume.",
        "signals": {
            "metrics": ["system.cpu.user sustained >95%", "system.load.norm.15 exceeds vCPU count"],
            "logs": ["WARN process_throttled service=flight-tracker cpu_throttle_count=847"],
            "traces": ["All spans show increased duration proportional to CPU contention"],
            "monitors": ["Host CPU >90% for 5 min forecast alert"]
        }
    },
    {
        "id": "INF-02", "tier": "Infrastructure", "severity": "critical",
        "name": "Storage I/O latency",
        "description": "I/O throttling on radar data storage volume. Simulates SAN fabric congestion.",
        "signals": {
            "metrics": ["system.io.await jumps from 2ms to 200ms+", "system.io.r_await and w_await both elevated"],
            "logs": ["WARN blk_update_request I/O error dev=sdb sector=..."],
            "traces": ["File read spans show 100x duration increase"],
            "monitors": ["Disk I/O latency anomaly detection"]
        }
    },
    {
        "id": "INF-03", "tier": "Infrastructure", "severity": "critical",
        "name": "Container OOM kill",
        "description": "Memory leak in radar display container exceeds cgroup limit. Container restarts.",
        "signals": {
            "metrics": ["docker.mem.rss approaches docker.mem.limit", "docker.mem.oom_kill increments"],
            "logs": ["FATAL container=radar-display OOMKilled=true restart_count=3"],
            "traces": ["Service map shows radar-display node flapping red/green"],
            "monitors": ["Container OOM + restart composite alert"]
        }
    },
    {
        "id": "INF-04", "tier": "Infrastructure", "severity": "info",
        "name": "SSL certificate expiration",
        "description": "Sets cert expiry to 7 days out. Tests proactive alerting before ATC portal TLS rejection.",
        "signals": {
            "metrics": ["Synthetics: ssl.days_remaining drops below 14"],
            "logs": ["Nginx: TLS handshake warnings from cert-pinning clients"],
            "traces": [],
            "monitors": ["SSL cert expiry <14 days — Slack to infra team"]
        }
    },
    # ── Network / SNMP tier ───────────────────────────────────────────
    {
        "id": "NET-01", "tier": "Network", "severity": "warning",
        "name": "SNMP agent unreachable",
        "description": "Stops snmpd daemon on core switch. Simulates ACL change blocking UDP/161.",
        "signals": {
            "metrics": ["snmp.can_check returns 0 for target host", "NDM: device goes grey in network device map"],
            "logs": ["WARN snmp_check host=atc-switch-01 error=request_timeout"],
            "traces": [],
            "monitors": ["SNMP device unreachable after 3 consecutive failures"]
        }
    },
    {
        "id": "NET-02", "tier": "Network", "severity": "critical",
        "name": "SNMP trap: radar power supply failure",
        "description": "Sends crafted SNMP trap with enterprise OID (1.3.6.1.4.1.21308) signaling radar PSU alarm.",
        "signals": {
            "metrics": ["snmp.radar.psu_status changes to failed"],
            "logs": ["CRITICAL trap_oid=1.3.6.1.4.1.21308.1.1 source=radar-psu-01"],
            "traces": [],
            "monitors": ["SNMP trap received — P1 page to ATC facilities"]
        }
    },
    {
        "id": "NET-03", "tier": "Network", "severity": "warning",
        "name": "Interface bandwidth saturation",
        "description": "iperf3 flood on backbone link. Simulates radar data surge saturating inter-site WAN.",
        "signals": {
            "metrics": ["snmp.ifBandwidthInUsage.rate >90% on WAN trunk", "ifInErrors and ifInDiscards incrementing"],
            "logs": ["WARN interface=Gi0/1 input_drops=4821 output_drops=312"],
            "traces": [],
            "monitors": ["Interface bandwidth >85% — network team Slack"]
        }
    },
    {
        "id": "NET-04", "tier": "Network", "severity": "warning",
        "name": "VPN tunnel flap",
        "description": "Cycles IPSec tunnel between ATC sites. Simulates unstable WAN connectivity.",
        "signals": {
            "metrics": ["snmp.ipsec.tunnel_status oscillates up/down", "aviondash.vpn.flap_count increments"],
            "logs": ["WARN ipsec_tunnel site=atc-remote-2 status=down duration=45s"],
            "traces": [],
            "monitors": ["VPN tunnel flap count >3 in 10 min alert"]
        }
    },
    # ── ATC Systems tier ──────────────────────────────────────────────
    {
        "id": "ATC-01", "tier": "ATC Systems", "severity": "critical",
        "name": "Radar feed interruption",
        "description": "Stops simulated radar data feed (ASTERIX Cat 048). Primary surveillance display goes stale.",
        "signals": {
            "metrics": ["aviondash.radar.feed_rate drops to 0", "aviondash.radar.display_staleness exceeds 10s"],
            "logs": ["CRITICAL radar_feed source=primary_radar status=no_data last_update=12s_ago"],
            "traces": ["Radar ingestion pipeline trace shows upstream connection_reset"],
            "monitors": ["Radar feed interruption — P1 immediate ATC notification"]
        }
    },
    {
        "id": "ATC-02", "tier": "ATC Systems", "severity": "warning",
        "name": "ATIS broadcast delay",
        "description": "Delays automated ATIS voice generation by 15 minutes. Pilots receive outdated airport information.",
        "signals": {
            "metrics": ["aviondash.atis.broadcast_age_minutes exceeds 15", "aviondash.atis.generation_errors increments"],
            "logs": ["WARN atis_stale airport=KJFK current_info=KILO age_minutes=18"],
            "traces": ["ATIS generation span shows TTS service timeout"],
            "monitors": ["ATIS broadcast age > 10 min — tower supervisor alert"]
        }
    },
    {
        "id": "ATC-03", "tier": "ATC Systems", "severity": "critical",
        "name": "Flight strip printer failure",
        "description": "Simulates network printer offline for flight progress strips. Forces manual strip writing.",
        "signals": {
            "metrics": ["aviondash.strips.print_failures increments", "aviondash.strips.queue_depth grows"],
            "logs": ["ERROR strip_printer printer=tower-strip-01 error=offline queue_depth=34"],
            "traces": ["Print job span returns connection_refused"],
            "monitors": ["Strip printer offline — tower operations notification"]
        }
    },
    {
        "id": "ATC-04", "tier": "ATC Systems", "severity": "warning",
        "name": "Runway status light malfunction",
        "description": "Sets RWSL system status to degraded. Triggers enhanced visual monitoring procedures.",
        "signals": {
            "metrics": ["aviondash.rwsl.status changes to degraded", "aviondash.rwsl.light_failures increments"],
            "logs": ["WARN rwsl_degraded runway=04L/22R lights_affected=3 mode=manual_override"],
            "traces": [],
            "monitors": ["RWSL system degraded — airfield maintenance + ATC supervisor"]
        }
    },
]

class FaultEngine:
    """Manages fault state and effects."""

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

    def activate(self, fault_id: str) -> dict:
        if fault_id not in self.catalog:
            return {"error": f"Unknown fault: {fault_id}"}
        self.active_faults[fault_id] = {
            "activated_at": time.time(),
            "fault": self.catalog[fault_id]
        }
        self._save_state()
        logger.warning(f"FAULT ACTIVATED: {fault_id} — {self.catalog[fault_id]['name']}")
        return {"status": "activated", "fault_id": fault_id}

    def deactivate(self, fault_id: str) -> dict:
        if fault_id in self.active_faults:
            del self.active_faults[fault_id]
            self._save_state()
            logger.info(f"FAULT DEACTIVATED: {fault_id}")
        return {"status": "deactivated", "fault_id": fault_id}

    def is_active(self, fault_id: str) -> bool:
        return fault_id in self.active_faults

    def get_active_faults(self) -> list:
        return list(self.active_faults.keys())

    def get_catalog_by_tier(self) -> dict:
        tiers = {}
        for fault in FAULT_CATALOG:
            tier = fault["tier"]
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append({**fault, "active": self.is_active(fault["id"])})
        return tiers

    def get_dashboard_effects(self) -> dict:
        """Returns metric modifications based on active faults."""
        effects = {}
        for fault_id in self.active_faults:
            effects[fault_id] = self.catalog[fault_id]["name"]
        return effects

engine = FaultEngine()
