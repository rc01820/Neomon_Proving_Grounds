# AvionDash

**Aviation / FAA Operations** — Neomon Proving Grounds

AvionDash is the flagship application of the Neomon Proving Grounds suite. It simulates an FAA air traffic control operations center with real-time flight tracking, ATC system monitoring, fleet management, and weather/NOTAM distribution. Designed with a glass-cockpit aesthetic, it provides a realistic proving ground for observability platform demonstrations in the aviation and government sector.

---

## Quick Start

```bash
cd aviondash
docker compose up -d --build

# Open http://localhost:8001
```

Or run as part of the full suite from the root directory:

```bash
docker compose up -d --build
# AvionDash available at http://localhost:8001
```

---

## Dashboard Views

### Dashboard
Flight operations overview with active flight count, departure delays, system uptime, sector traffic load, and runway utilization

### ATC Systems
ATC system health with uptime rings for primary radar (ASR-11), STARS display system, and voice communications (VSCS). Communication channel status for ground, tower, approach, and ATIS frequencies

### Fleet Mgmt
Fleet overview with aircraft type distribution, utilization rates, maintenance alerts (AOG, MEL, scheduled), and real-time aircraft status

### Fault Console
Interactive fault injection control panel with 22 faults across 5 tiers



---

## Fault Injection Catalog

AvionDash includes **20 fault scenarios** across 5 tiers:

| Tier | Count | Faults |
|------|-------|--------|
| Application | 4 faults | Flight tracking API latency, NOTAM distribution failure, weather data staleness, pilot auth timeout |
| Database | 4 faults | Replication lag, connection pool exhaustion, slow query cascade, audit log write failure |
| Infrastructure | 4 faults | CPU saturation, storage I/O latency, container OOM kill, SSL cert expiry |
| Network / SNMP | 4 faults | SNMP agent unreachable, radar PSU trap, interface saturation, VPN tunnel flap |
| ATC Systems | 4 faults | Radar feed interruption, ATIS broadcast delay, flight strip printer failure, runway status light malfunction |


### Cross-Tier Cascade

INF-02 (storage I/O) → APP-01 (flight tracking latency) → ATC-01 (radar feed interruption). A single storage event cascades into operational impact visible across all three dashboard views.

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
curl -X POST http://localhost:8001/api/faults/APP-01/activate

# Check active faults
curl http://localhost:8001/api/faults

# Deactivate
curl -X POST http://localhost:8001/api/faults/APP-01/deactivate
```

---

## Datadog Integration

### Custom Metrics

All dashboard KPIs emit custom metrics via DogStatsD with the `aviondash.*` namespace.

### Structured Logging

JSON logs to stdout, ready for Datadog log collection:

```json
{
  "timestamp": "2026-07-12T14:32:00Z",
  "level": "WARNING",
  "service": "aviondash",
  "fault_id": "APP-01",
  "message": "FAULT ACTIVATED: APP-01 — Flight tracking API latency"
}
```

### APM Traces

FastAPI auto-instrumented with `ddtrace`. Activated faults inject artificial latency and error spans visible in APM flame graphs.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | `8001` | Server listen port |
| `DD_SERVICE` | `aviondash` | Datadog APM service name |
| `DD_ENV` | `proving-grounds` | Datadog environment tag |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `FAULT_STATE_FILE` | `/app/data/faults.json` | Fault state persistence path |

---

## Design

- **Accent color**: Teal (#34d399)
- **Theme**: Dark glass-cockpit with aviation / faa operations domain language
- **Architecture**: FastAPI + Jinja2 + vanilla CSS, single-container Docker

---

## License

Copyright © 2026 Neomon Labs. All rights reserved.
