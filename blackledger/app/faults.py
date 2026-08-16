"""BlackLedger fault injection catalog — Financial Services themed."""

import json, os, time, logging
from config import FAULT_STATE_FILE

logger = logging.getLogger("blackledger.faults")

FAULT_CATALOG = [
    # ── Application tier ──────────────────────────────────────────────
    {
        "id": "APP-01", "tier": "Application", "severity": "critical",
        "name": "Order matching engine latency",
        "description": "Adds 50-500ms latency to order matching API. Simulates exchange gateway congestion during market open.",
        "signals": {
            "metrics": ["blackledger.matching.latency_p99 crosses 100ms SLA", "http.request.duration spikes on /api/orders/match"],
            "logs": ["WARN slow_match order_id=ORD-8841 duration=340ms symbol=AAPL"],
            "traces": ["Order matching span shows queue_wait dominating flamegraph"],
            "monitors": ["Matching engine P99 > 100ms — trading desk escalation"]
        }
    },
    {
        "id": "APP-02", "tier": "Application", "severity": "critical",
        "name": "Market data feed interruption",
        "description": "Stops simulated Level 2 market data feed. Trading screens show stale quotes.",
        "signals": {
            "metrics": ["blackledger.marketdata.feed_rate drops to 0", "blackledger.marketdata.staleness_seconds exceeds 5"],
            "logs": ["CRITICAL market_feed source=exchange_gateway status=disconnected"],
            "traces": ["Market data ingestion pipeline shows connection_reset"],
            "monitors": ["Market data feed interruption — P1 immediate trading floor alert"]
        }
    },
    {
        "id": "APP-03", "tier": "Application", "severity": "warning",
        "name": "FIX protocol session drop",
        "description": "Drops FIX 4.4 session with simulated counterparty. Pending orders stuck in unacknowledged state.",
        "signals": {
            "metrics": ["blackledger.fix.session_status changes to disconnected", "blackledger.fix.pending_orders grows"],
            "logs": ["ERROR fix_session counterparty=PRIME-01 status=disconnected heartbeat_missed=3"],
            "traces": ["FIX session span shows heartbeat_timeout"],
            "monitors": ["FIX session disconnected — immediate counterparty notification"]
        }
    },
    {
        "id": "APP-04", "tier": "Application", "severity": "warning",
        "name": "Client portal authentication failure",
        "description": "Returns 403 on MFA token validation. Simulates HSM connectivity loss for token signing.",
        "signals": {
            "metrics": ["auth.failure_rate jumps to 100% on /portal/login", "blackledger.auth.hsm_errors increments"],
            "logs": ["ERROR mfa_validation status=503 error=hsm_unreachable"],
            "traces": ["Auth span shows hsm_signing_timeout"],
            "monitors": ["Synthetics: client portal login fails — security team page"]
        }
    },
    {
        "id": "APP-05", "tier": "Application", "severity": "warning",
        "name": "Settlement instruction rejection",
        "description": "Injects malformed SWIFT MT messages causing settlement instruction failures.",
        "signals": {
            "metrics": ["blackledger.settlement.rejection_rate spikes >5%"],
            "logs": ["ERROR swift_validation msg_type=MT103 error=invalid_bic field=59"],
            "traces": ["Settlement processing span returns validation_failed"],
            "monitors": ["Settlement rejection rate > 2% — ops team alert"]
        }
    },
    # ── Database tier ─────────────────────────────────────────────────
    {
        "id": "DB-01", "tier": "Database", "severity": "warning",
        "name": "Position database replication lag",
        "description": "Write-heavy trade booking causes replica lag >15s. Portfolio valuations use stale positions.",
        "signals": {
            "metrics": ["postgresql.replication_delay >15s on positions-ro", "db.active_connections near pool max"],
            "logs": ["WARN replication_lag replica=positions-ro-1 lag_seconds=18"],
            "traces": ["Portfolio valuation span tagged stale_position=true"],
            "monitors": ["Position DB replication lag >5s — risk team alert"]
        }
    },
    {
        "id": "DB-02", "tier": "Database", "severity": "critical",
        "name": "Trade ledger connection pool exhaustion",
        "description": "Leaks connections during market open trade surge. All booking operations queue.",
        "signals": {
            "metrics": ["db.pool.active hits db.pool.max (500/500)", "blackledger.trade.booking_latency spikes"],
            "logs": ["ERROR pool_timeout waited=30s error=cannot_acquire_connection service=trade-ledger"],
            "traces": ["Trade booking span blocked at db_pool_wait for 28s"],
            "monitors": ["Trade ledger DB pool >90% — P1 trading operations"]
        }
    },
    {
        "id": "DB-03", "tier": "Database", "severity": "warning",
        "name": "Slow query on transaction history",
        "description": "Drops index on transaction_log table. Report generation triggers full scans.",
        "signals": {
            "metrics": ["DBM: query.avg_time jumps 80x on transaction_log", "rows_examined/rows_returned >5000:1"],
            "logs": ["WARN slow_query duration=22s table=transaction_log scan=sequential"],
            "traces": ["Report generation trace dominated by DB span at 97%"],
            "monitors": ["Slow query count anomaly detection"]
        }
    },
    {
        "id": "DB-04", "tier": "Database", "severity": "critical",
        "name": "SOX audit trail write failure",
        "description": "Fills regulatory audit partition. SOX/MiFID II compliance write failures.",
        "signals": {
            "metrics": ["system.disk.pct_usage{mount:/var/lib/audit} hits 100%", "blackledger.sox.audit_write_failures increments"],
            "logs": ["FATAL disk_full partition=/var/lib/audit error=ENOSPC"],
            "traces": ["Audit write span returns disk_full error"],
            "monitors": ["SOX audit log failure — P1 + compliance officer + legal"]
        }
    },
    # ── Infrastructure tier ───────────────────────────────────────────
    {
        "id": "INF-01", "tier": "Infrastructure", "severity": "warning",
        "name": "CPU saturation on matching engine",
        "description": "CPU burn simulating options pricing recalculation storm.",
        "signals": {
            "metrics": ["system.cpu.user sustained >95% on matching-engine-01", "system.load.norm.15 exceeds vCPU count"],
            "logs": ["WARN cpu_throttle service=matching-engine throttle_count=1200"],
            "traces": ["All order matching spans show proportional latency increase"],
            "monitors": ["Matching engine CPU >90% for 2 min — immediate alert"]
        }
    },
    {
        "id": "INF-02", "tier": "Infrastructure", "severity": "critical",
        "name": "Tick database storage I/O",
        "description": "I/O throttling on tick data volume. Simulates time-series DB write amplification.",
        "signals": {
            "metrics": ["system.io.await jumps from 1ms to 150ms+", "system.io.w_await elevated on tick-store"],
            "logs": ["WARN blk_update_request I/O error dev=nvme0n1"],
            "traces": ["Tick data write spans show 100x latency"],
            "monitors": ["Tick DB I/O latency anomaly — market data team"]
        }
    },
    {
        "id": "INF-03", "tier": "Infrastructure", "severity": "critical",
        "name": "Container OOM kill — risk calculator",
        "description": "Memory leak in VaR calculation container. Monte Carlo simulation exhausts memory.",
        "signals": {
            "metrics": ["docker.mem.rss approaches docker.mem.limit on risk-calc", "docker.mem.oom_kill increments"],
            "logs": ["FATAL container=risk-calculator OOMKilled=true monte_carlo_iterations=1000000"],
            "traces": ["Risk calculation service flapping on service map"],
            "monitors": ["Risk calculator OOM — P1 risk management"]
        }
    },
    {
        "id": "INF-04", "tier": "Infrastructure", "severity": "info",
        "name": "SSL certificate expiration",
        "description": "Sets client portal cert expiry to 7 days. Tests proactive alerting.",
        "signals": {
            "metrics": ["Synthetics: ssl.days_remaining drops below 14"],
            "logs": ["Nginx TLS warnings from client cert-pinning apps"],
            "traces": [],
            "monitors": ["SSL cert expiry <14 days — infra + compliance"]
        }
    },
    # ── Network / SNMP tier ───────────────────────────────────────────
    {
        "id": "NET-01", "tier": "Network", "severity": "warning",
        "name": "SNMP agent unreachable",
        "description": "Stops snmpd on core switch. Simulates data center network visibility loss.",
        "signals": {
            "metrics": ["snmp.can_check returns 0", "NDM: device goes grey"],
            "logs": ["WARN snmp_check host=dc-core-sw-01 error=request_timeout"],
            "traces": [],
            "monitors": ["SNMP device unreachable after 3 failures"]
        }
    },
    {
        "id": "NET-02", "tier": "Network", "severity": "critical",
        "name": "SNMP trap: UPS battery critical",
        "description": "Sends UPS battery low trap. Data center power event affecting trading infrastructure.",
        "signals": {
            "metrics": ["snmp.ups.battery_pct drops below 20%"],
            "logs": ["CRITICAL trap_oid=1.3.6.1.2.1.33.1.6.3.2 source=ups-trading-dc"],
            "traces": [],
            "monitors": ["UPS battery critical — P1 facilities + BCP activation"]
        }
    },
    {
        "id": "NET-03", "tier": "Network", "severity": "warning",
        "name": "Low-latency link saturation",
        "description": "Floods exchange colocation cross-connect. Simulates market data burst saturation.",
        "signals": {
            "metrics": ["snmp.ifBandwidthInUsage.rate >90% on exchange link", "ifInDiscards incrementing on colo switch"],
            "logs": ["WARN interface=TenGi0/1 input_drops=12400 utilization=94%"],
            "traces": [],
            "monitors": ["Exchange link bandwidth >85% — network + trading"]
        }
    },
    {
        "id": "NET-04", "tier": "Network", "severity": "warning",
        "name": "DNS resolution failure",
        "description": "Returns SERVFAIL for market data endpoint DNS. Simulates split-brain DNS issue.",
        "signals": {
            "metrics": ["blackledger.dns.failure_count spikes", "blackledger.dns.resolution_time exceeds 5s"],
            "logs": ["ERROR dns_resolve host=marketdata.exchange.com error=SERVFAIL"],
            "traces": ["Market data connection span shows dns_resolution_failed"],
            "monitors": ["DNS failure rate > 1% — network team page"]
        }
    },
    # ── Trading Operations tier ───────────────────────────────────────
    {
        "id": "TRD-01", "tier": "Trading Operations", "severity": "critical",
        "name": "Risk limit breach",
        "description": "Pushes simulated VaR utilization past 95% threshold. Triggers automated position limit enforcement.",
        "signals": {
            "metrics": ["blackledger.risk.var_utilization exceeds 95%", "blackledger.risk.limit_breaches increments"],
            "logs": ["CRITICAL risk_breach desk=equities var_utilization=97% limit=95%"],
            "traces": ["Risk calculation span shows limit_exceeded tag"],
            "monitors": ["VaR limit breach — P1 risk management + CRO notification"]
        }
    },
    {
        "id": "TRD-02", "tier": "Trading Operations", "severity": "warning",
        "name": "End-of-day settlement delay",
        "description": "Delays T+1 settlement batch processing. Positions remain unsettled past cutoff.",
        "signals": {
            "metrics": ["blackledger.settlement.pending_count grows past cutoff", "blackledger.settlement.batch_duration exceeds window"],
            "logs": ["WARN settlement_delay batch=EOD-20260712 pending=847 cutoff=exceeded"],
            "traces": ["Settlement batch span shows timeout on clearing house"],
            "monitors": ["Settlement batch overrun — operations + compliance"]
        }
    },
    {
        "id": "TRD-03", "tier": "Trading Operations", "severity": "warning",
        "name": "Margin call processing failure",
        "description": "Injects errors into margin calculation engine. Incorrect margin requirements generated.",
        "signals": {
            "metrics": ["blackledger.margin.calculation_errors spikes", "blackledger.margin.recompute_count grows"],
            "logs": ["ERROR margin_calc account=ACCT-4421 error=pricing_data_stale"],
            "traces": ["Margin calculation span shows stale_market_data error"],
            "monitors": ["Margin calculation error rate > 1% — risk ops alert"]
        }
    },
    {
        "id": "TRD-04", "tier": "Trading Operations", "severity": "critical",
        "name": "Regulatory report generation failure",
        "description": "Fails EMIR/MiFID II trade reporting batch. Regulatory submission deadline at risk.",
        "signals": {
            "metrics": ["blackledger.regulatory.report_failures increments", "blackledger.regulatory.pending_submissions grows"],
            "logs": ["CRITICAL regulatory_report type=EMIR status=failed error=data_validation"],
            "traces": ["Report generation span shows schema_validation_error"],
            "monitors": ["Regulatory report failure — P1 compliance + legal immediate"]
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
