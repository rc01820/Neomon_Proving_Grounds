"""CodeBlue fault injection catalog — Healthcare themed."""

import json, os, time, logging
from config import FAULT_STATE_FILE

logger = logging.getLogger("codeblue.faults")

FAULT_CATALOG = [
    # ── Application tier ──────────────────────────────────────────────
    {
        "id": "APP-01", "tier": "Application", "severity": "critical",
        "name": "EHR response degradation",
        "description": "Adds 2-8s artificial latency to EHR API responses. Simulates Epic/Cerner slowdown during peak charting hours.",
        "signals": {
            "metrics": ["http.request.duration spikes on /api/patient/* endpoints", "codeblue.ehr.response_time_p99 crosses 5s"],
            "logs": ["WARN slow_query duration=6.2s query=patient_demographics"],
            "traces": ["Trace flamegraph shows DB query bottleneck in patient lookup service"],
            "monitors": ["EHR P99 latency > 3s — PagerDuty escalation"]
        }
    },
    {
        "id": "APP-02", "tier": "Application", "severity": "warning",
        "name": "Patient portal auth failure",
        "description": "Returns 401/403 on OAuth token validation for patient portal SSO. Simulates identity provider outage.",
        "signals": {
            "metrics": ["auth.failure_rate jumps from 0.2% baseline to 100%", "RUM: session.error_count spikes on /portal/login"],
            "logs": ["ERROR oauth_token_validation status=503 provider=okta"],
            "traces": ["Auth middleware span returns provider_unavailable"],
            "monitors": ["Synthetics: patient portal login check fails — on-call page"]
        }
    },
    {
        "id": "APP-03", "tier": "Application", "severity": "critical",
        "name": "PACS image retrieval timeout",
        "description": "Injects 15s timeout on DICOM C-MOVE/C-GET operations. Simulates storage array I/O saturation.",
        "signals": {
            "metrics": ["codeblue.pacs.image_retrieval_time exceeds 10s SLA", "system.io.await on storage node spikes >200ms"],
            "logs": ["ERROR dicom_retrieve study_uid=1.2.840... timeout=15s"],
            "traces": ["Distributed trace: DICOM service span shows timeout error tag"],
            "monitors": ["PACS retrieval SLA breach — P1 incident creation"]
        }
    },
    {
        "id": "APP-04", "tier": "Application", "severity": "critical",
        "name": "HL7 lab result delivery failure",
        "description": "Drops HL7 ORU^R01 messages between LIS and EHR integration engine. Simulates Mirth Connect channel failure.",
        "signals": {
            "metrics": ["codeblue.hl7.message_rate{channel:lab_results} drops to 0", "codeblue.hl7.queue_depth{channel:lab_results} grows linearly"],
            "logs": ["ERROR channel=lab_results state=STOPPED error=connection_refused"],
            "traces": ["HL7 message processing span shows channel_stopped error"],
            "monitors": ["HL7 message throughput anomaly detection alert"]
        }
    },
    {
        "id": "APP-05", "tier": "Application", "severity": "warning",
        "name": "Pharmacy order validation error",
        "description": "Injects malformed NDC codes into medication order API, causing drug interaction check failures.",
        "signals": {
            "metrics": ["codeblue.pharmacy.order_error_rate spikes >10%"],
            "logs": ["ERROR ndc_lookup code=12345-678-90 error=not_found"],
            "traces": ["APM: medication_validation span returns error: invalid_ndc"],
            "monitors": ["Pharmacy error rate threshold alert"]
        }
    },
    # ── Database tier ─────────────────────────────────────────────────
    {
        "id": "DB-01", "tier": "Database", "severity": "warning",
        "name": "Replication lag spike",
        "description": "Write-heavy transaction burst causes replica lag >30s. Read replicas serve stale patient data.",
        "signals": {
            "metrics": ["postgresql.replication_delay >30s", "db.active_connections saturates pool"],
            "logs": ["WARN replication_lag replica=db-ro-1 lag_bytes=524288000"],
            "traces": ["DB read span tagged stale_read=true"],
            "monitors": ["Replication lag >10s threshold alert"]
        }
    },
    {
        "id": "DB-02", "tier": "Database", "severity": "critical",
        "name": "Connection pool exhaustion",
        "description": "Leaks DB connections during shift change surge. Pool hits max capacity.",
        "signals": {
            "metrics": ["db.pool.active hits db.pool.max (200/200)", "http.request.duration spikes as requests queue"],
            "logs": ["ERROR pool_timeout waited=30s error=cannot_acquire_connection"],
            "traces": ["All API spans show db_connection_wait dominating flamegraph"],
            "monitors": ["DB connection pool utilization >90% composite alert"]
        }
    },
    {
        "id": "DB-03", "tier": "Database", "severity": "warning",
        "name": "Slow query cascade",
        "description": "Drops index on patient_encounters table, causing full table scans on census queries.",
        "signals": {
            "metrics": ["DBM: query.avg_time jumps 50x on patient queries", "rows_examined vs rows_returned shows sequential scan"],
            "logs": ["WARN slow_query duration=14.2s table=patient_encounters scan=sequential"],
            "traces": ["DB span duration dominates request flamegraph"],
            "monitors": ["Slow query count anomaly detection"]
        }
    },
    {
        "id": "DB-04", "tier": "Database", "severity": "critical",
        "name": "HIPAA audit log write failure",
        "description": "Fills audit log partition to 100%, causing write failures. Compliance-critical.",
        "signals": {
            "metrics": ["system.disk.pct_usage{mount:/var/lib/audit} hits 100%", "codeblue.hipaa.audit_write_failures increments"],
            "logs": ["FATAL disk_full partition=/var/lib/audit error=ENOSPC"],
            "traces": ["Audit write span returns disk_full error"],
            "monitors": ["HIPAA audit log write failure — P1 + compliance team"]
        }
    },
    # ── Infrastructure tier ───────────────────────────────────────────
    {
        "id": "INF-01", "tier": "Infrastructure", "severity": "warning",
        "name": "CPU saturation on EHR app server",
        "description": "stress-ng CPU burn simulating report generation contention.",
        "signals": {
            "metrics": ["system.cpu.user sustained >95% on ehr-app-01", "system.load.norm.15 exceeds vCPU count"],
            "logs": ["WARN oom_score_adj process=java pid=4821 adj=500"],
            "traces": ["All spans show proportional duration increase"],
            "monitors": ["Host CPU >90% for 5 min forecast alert"]
        }
    },
    {
        "id": "INF-02", "tier": "Infrastructure", "severity": "critical",
        "name": "Storage array I/O latency",
        "description": "I/O throttling on PACS storage volume via tc/dm-delay. Simulates SAN congestion.",
        "signals": {
            "metrics": ["system.io.await jumps from 2ms to 200ms+", "system.io.r_await and w_await both elevated"],
            "logs": ["WARN blk_update_request I/O error dev=sdb"],
            "traces": ["File I/O spans show 100x duration increase"],
            "monitors": ["Disk I/O anomaly — correlates with APP-03 PACS timeout"]
        }
    },
    {
        "id": "INF-03", "tier": "Infrastructure", "severity": "critical",
        "name": "Container OOM kill",
        "description": "Memory leak in patient dashboard container exceeds cgroup limit.",
        "signals": {
            "metrics": ["docker.mem.rss approaches docker.mem.limit", "docker.mem.oom_kill count increments"],
            "logs": ["FATAL container=dashboard-api OOMKilled=true"],
            "traces": ["Service map shows dashboard-api node flapping"],
            "monitors": ["Container restart + OOM composite alert"]
        }
    },
    {
        "id": "INF-04", "tier": "Infrastructure", "severity": "info",
        "name": "SSL certificate expiration",
        "description": "Sets cert expiry to 7 days out. Tests proactive alerting.",
        "signals": {
            "metrics": ["Synthetics: ssl.days_remaining drops below 14"],
            "logs": ["Nginx TLS handshake warnings from cert-pinning clients"],
            "traces": [],
            "monitors": ["SSL cert expiry <14 days — Slack to infra team"]
        }
    },
    # ── Network / SNMP tier ───────────────────────────────────────────
    {
        "id": "NET-01", "tier": "Network", "severity": "warning",
        "name": "SNMP agent unreachable",
        "description": "Stops snmpd daemon. Simulates firewall ACL change blocking UDP/161.",
        "signals": {
            "metrics": ["snmp.can_check returns 0 for target", "NDM: device goes grey/unreachable"],
            "logs": ["WARN snmp_check host=switch-core-01 error=request_timeout"],
            "traces": [],
            "monitors": ["SNMP device unreachable after 3 poll failures"]
        }
    },
    {
        "id": "NET-02", "tier": "Network", "severity": "critical",
        "name": "SNMP trap: UPS battery low",
        "description": "Sends SNMPv2c trap with upsAlarmBatteryLow OID (1.3.6.1.2.1.33.1.6.3.2).",
        "signals": {
            "metrics": ["snmp.ups.battery_pct drops below 25%"],
            "logs": ["CRITICAL trap_oid=1.3.6.1.2.1.33.1.6.3.2 source=ups-dc-01"],
            "traces": [],
            "monitors": ["SNMP trap received — P1 page to facilities + IT"]
        }
    },
    {
        "id": "NET-03", "tier": "Network", "severity": "warning",
        "name": "Interface utilization saturation",
        "description": "iperf3 flood on VLAN trunk. Simulates PACS transfer surge.",
        "signals": {
            "metrics": ["snmp.ifBandwidthInUsage.rate >90%", "ifInErrors and ifInDiscards incrementing"],
            "logs": ["WARN interface=Gi0/1 input_drops=4821"],
            "traces": [],
            "monitors": ["Interface bandwidth >85% — network team Slack"]
        }
    },
    {
        "id": "NET-04", "tier": "Network", "severity": "warning",
        "name": "Wi-Fi access point failure",
        "description": "Disassociates AP from WLC. Clinical floor loses WoW and badge scanner connectivity.",
        "signals": {
            "metrics": ["snmp.wlc.associated_clients{ap:floor3-ap2} drops to 0", "codeblue.wifi.client_count{floor:3} drops"],
            "logs": ["WARN ap_disassociated ap=floor3-ap2 reason=controller_timeout"],
            "traces": [],
            "monitors": ["AP client count anomaly + coverage map gap"]
        }
    },
    # ── Medical Device tier ───────────────────────────────────────────
    {
        "id": "MED-01", "tier": "Medical Device", "severity": "critical",
        "name": "Ventilator telemetry heartbeat loss",
        "description": "Stops MQTT/HL7 heartbeat from simulated ventilator agent. Device appears offline.",
        "signals": {
            "metrics": ["codeblue.meddevice.heartbeat{device:icu-v5} goes stale (>60s)", "codeblue.meddevice.connected_count{type:ventilator} decrements"],
            "logs": ["CRITICAL heartbeat_timeout device=ICU-V5 last_seen=13:12:04Z"],
            "traces": ["Device gateway span shows heartbeat_expired"],
            "monitors": ["Medical device heartbeat missing — P1 page biomed + nursing"]
        }
    },
    {
        "id": "MED-02", "tier": "Medical Device", "severity": "warning",
        "name": "Telemetry data drift",
        "description": "Sends gradually drifting vital sign values outside normal range. Tests anomaly detection.",
        "signals": {
            "metrics": ["codeblue.vitals.heart_rate{bed:tel-4} crosses 120bpm", "codeblue.vitals.spo2{bed:tel-4} crosses 92%"],
            "logs": ["WARN vitals_drift bed=TEL-4 hr=122 spo2=91 trend=worsening"],
            "traces": [],
            "monitors": ["Vitals anomaly forecast alert — nurse station"]
        }
    },
    {
        "id": "MED-03", "tier": "Medical Device", "severity": "warning",
        "name": "Infusion pump sync failure",
        "description": "Returns malformed drug library update response. Simulates BCMA integration failure.",
        "signals": {
            "metrics": ["codeblue.infusion.library_sync_failures spikes", "codeblue.infusion.drug_library_version{pump:pmp-3} behind fleet"],
            "logs": ["ERROR drug_library_sync pump=PMP-3 error=parse_failure"],
            "traces": ["Pump gateway span shows deserialization_error"],
            "monitors": ["Infusion pump sync failure count >3 in 15 min"]
        }
    },
    {
        "id": "MED-04", "tier": "Medical Device", "severity": "info",
        "name": "Pneumatic tube system jam",
        "description": "Sets tube station status to jammed. Affects lab specimen and medication delivery.",
        "signals": {
            "metrics": ["codeblue.pneumatic.station_status{station:lab-recv} = jammed", "codeblue.pneumatic.transit_time_avg increases"],
            "logs": ["WARN station=lab-recv status=jammed carrier_id=C-4812"],
            "traces": [],
            "monitors": ["Pneumatic tube station offline — facilities notification"]
        }
    },
    # ── Operations tier ───────────────────────────────────────────────
    {
        "id": "OPS-01", "tier": "Operations", "severity": "critical",
        "name": "ED boarding surge",
        "description": "Rapidly increments admitted-but-unplaced patient count. Simulates bed management failure.",
        "signals": {
            "metrics": ["codeblue.ed.boarders_count exceeds 15", "codeblue.ed.wait_time_avg climbs past 60 min", "codeblue.bed.occupancy_pct crosses 95%"],
            "logs": ["CRITICAL ed_surge boarders=18 wait_avg=72min capacity=exceeded"],
            "traces": [],
            "monitors": ["ED boarder count + wait time composite — capacity protocol"]
        }
    },
    {
        "id": "OPS-02", "tier": "Operations", "severity": "warning",
        "name": "Discharge pipeline stall",
        "description": "Freezes discharge transitions in pending state. Physician sign-off bottleneck.",
        "signals": {
            "metrics": ["codeblue.discharge.pending_count grows, completed flatlines", "codeblue.los.avg_hours trends upward"],
            "logs": ["WARN discharge_stall pending=24 completed_last_hour=0"],
            "traces": [],
            "monitors": ["Discharge throughput anomaly — care management notification"]
        }
    },
    {
        "id": "OPS-03", "tier": "Operations", "severity": "warning",
        "name": "OR schedule overrun",
        "description": "Extends active case durations beyond scheduled block time. Creates downstream delays.",
        "signals": {
            "metrics": ["codeblue.or.utilization_pct exceeds 100%", "codeblue.or.turnover_time_avg increases", "codeblue.or.cases_delayed_count increments"],
            "logs": ["WARN or_overrun room=OR-4 scheduled=120min actual=165min"],
            "traces": [],
            "monitors": ["OR schedule variance >20 min — perioperative services alert"]
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
        self.active_faults[fault_id] = {"activated_at": time.time(), "fault": self.catalog[fault_id]}
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
        effects = {}
        for fault_id in self.active_faults:
            effects[fault_id] = self.catalog[fault_id]["name"]
        return effects

engine = FaultEngine()
