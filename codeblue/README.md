# CodeBlue

**Healthcare / Hospital Operations** — Neomon Proving Grounds

CodeBlue simulates a hospital operations center with patient flow management, clinical systems monitoring, and medical device connectivity. It covers the full healthcare IT stack — from EHR and PACS systems to HL7/FHIR interfaces, infusion pumps, and ventilator telemetry. The application demonstrates observability challenges unique to healthcare: HIPAA compliance, medical device monitoring, and patient flow bottleneck detection.

---

## Quick Start

```bash
cd codeblue
docker compose up -d --build

# Open http://localhost:8002
```

Or run as part of the full suite from the root directory:

```bash
docker compose up -d --build
# CodeBlue available at http://localhost:8002
```

---

## Dashboard Views

### Command Center
Hospital-wide KPIs: total census, ED wait time, bed occupancy, unit-by-unit occupancy bars, OR utilization with case counts and turnover time

### Patient Flow
ED arrivals/admissions/discharges with volume trends, discharge pipeline status (physician sign-off, transport, pharmacy holds), average length of stay by unit

### Clinical Systems
Uptime rings for EHR (Epic), PACS (GE), and LIS (PathNet). Lab turnaround times for CBC, BMP, Troponin, and blood culture. HL7/FHIR interface status with message throughput

### Fault Console
Interactive fault injection control panel with 24 faults across 6 tiers



---

## Fault Injection Catalog

CodeBlue includes **24 fault scenarios** across 6 tiers:

| Tier | Count | Faults |
|------|-------|--------|
| Application | 5 faults | EHR response degradation, patient portal auth failure, PACS image timeout, HL7 lab result failure, pharmacy order validation error |
| Database | 4 faults | Replication lag, connection pool exhaustion, slow query cascade, HIPAA audit log write failure |
| Infrastructure | 4 faults | CPU saturation, storage I/O latency, container OOM kill, SSL cert expiry |
| Network / SNMP | 4 faults | SNMP agent unreachable, UPS battery low trap, interface saturation, Wi-Fi AP failure |
| Medical Device | 4 faults | Ventilator heartbeat loss, telemetry data drift, infusion pump sync failure, pneumatic tube jam |
| Operations | 3 faults | ED boarding surge, discharge pipeline stall, OR schedule overrun |


### Cross-Tier Cascade

INF-02 (storage I/O) → APP-03 (PACS timeout) → OPS-01 (ED boarding surge). A storage array issue delays radiology reads, which slows admissions, which creates an ED boarding crisis — a three-tier cascade traceable end-to-end.

---

## API Reference

### Fault Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/faults` | List all faults with current state |
| `POST` | `/api/faults/{fault_id}/activate` | Activate a fault by ID |
| `POST` | `/api/faults/{fault_id}/deactivate` | Deactivate a fault by ID |
| `GET` | `/api/health` | Health check with active fault count |

### Example

```bash
# Activate a fault
curl -X POST http://localhost:8002/api/faults/APP-01/activate

# Check active faults
curl http://localhost:8002/api/faults

# Deactivate
curl -X POST http://localhost:8002/api/faults/APP-01/deactivate
```

---

## Datadog Integration

### Custom Metrics

All dashboard KPIs emit custom metrics via DogStatsD with the `codeblue.*` namespace.

### Structured Logging

JSON logs to stdout, ready for Datadog log collection:

```json
{
  "timestamp": "2026-07-12T14:32:00Z",
  "level": "WARNING",
  "service": "codeblue",
  "fault_id": "APP-01",
  "message": "FAULT ACTIVATED: APP-01 — EHR response degradation"
}
```

### APM Traces

FastAPI auto-instrumented with `ddtrace`. Activated faults inject artificial latency and error spans visible in APM flame graphs.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | `8002` | Server listen port |
| `DD_SERVICE` | `codeblue` | Datadog APM service name |
| `DD_ENV` | `proving-grounds` | Datadog environment tag |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `FAULT_STATE_FILE` | `/app/data/faults.json` | Fault state persistence path |

---

## Design

- **Accent color**: Red (#f87171)
- **Theme**: Dark glass-cockpit with healthcare / hospital operations domain language
- **Architecture**: FastAPI + Jinja2 + vanilla CSS, single-container Docker

---

## License

Copyright © 2026 Neomon Labs. All rights reserved.
