# BlackLedger

**Financial Services / Trading Operations** — Neomon Proving Grounds

BlackLedger simulates a financial services trading floor with order matching, market data feeds, risk management, settlement processing, and regulatory reporting. It covers the unique observability challenges of financial infrastructure: microsecond-sensitive latency, regulatory compliance (SOX/MiFID II/EMIR), risk limit monitoring, and multi-venue market data feeds.

---

## Quick Start

```bash
cd blackledger
docker compose up -d --build

# Open http://localhost:8003
```

Or run as part of the full suite from the root directory:

```bash
docker compose up -d --build
# BlackLedger available at http://localhost:8003
```

---

## Dashboard Views

### Trading Floor
Real-time trading KPIs: order volume, matching engine P99 latency, fill rate, market data feed status with per-venue message rates, order flow by desk

### Risk & Compliance
VaR utilization by desk, margin excess/deficit, compliance alert status, regulatory reporting status for EMIR, MiFID II, Dodd-Frank, and SOX

### Transactions
Settlement processing: daily volume, failure rate, pending T+1 positions, auto-reconciliation rate, settlement status by instrument type, SWIFT message queue

### Fault Console
Interactive fault injection control panel with 24 faults across 6 tiers



---

## Fault Injection Catalog

BlackLedger includes **21 fault scenarios** across 5 tiers:

| Tier | Count | Faults |
|------|-------|--------|
| Application | 5 faults | Order matching engine latency, market data feed interruption, FIX protocol session drop, client portal auth failure, settlement instruction rejection |
| Database | 4 faults | Position DB replication lag, trade ledger connection pool exhaustion, slow query on transaction history, SOX audit trail write failure |
| Infrastructure | 4 faults | CPU saturation on matching engine, tick database storage I/O, risk calculator OOM kill, SSL cert expiry |
| Network / SNMP | 4 faults | SNMP agent unreachable, UPS battery critical, low-latency link saturation, DNS resolution failure |
| Trading Operations | 4 faults | Risk limit breach, end-of-day settlement delay, margin call processing failure, regulatory report generation failure |


### Cross-Tier Cascade

APP-02 (market data feed interruption) → TRD-01 (risk limit breach) → TRD-04 (regulatory report failure). A market data outage causes stale pricing in VaR calculations, which triggers false risk limit breaches, which corrupts the data feeding into regulatory reports.

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
curl -X POST http://localhost:8003/api/faults/APP-01/activate

# Check active faults
curl http://localhost:8003/api/faults

# Deactivate
curl -X POST http://localhost:8003/api/faults/APP-01/deactivate
```

---

## Datadog Integration

### Custom Metrics

All dashboard KPIs emit custom metrics via DogStatsD with the `blackledger.*` namespace.

### Structured Logging

JSON logs to stdout, ready for Datadog log collection:

```json
{
  "timestamp": "2026-07-12T14:32:00Z",
  "level": "WARNING",
  "service": "blackledger",
  "fault_id": "APP-01",
  "message": "FAULT ACTIVATED: APP-01 — Order matching engine latency"
}
```

### APM Traces

FastAPI auto-instrumented with `ddtrace`. Activated faults inject artificial latency and error spans visible in APM flame graphs.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | `8003` | Server listen port |
| `DD_SERVICE` | `blackledger` | Datadog APM service name |
| `DD_ENV` | `proving-grounds` | Datadog environment tag |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `FAULT_STATE_FILE` | `/app/data/faults.json` | Fault state persistence path |

---

## Design

- **Accent color**: Blue (#60a5fa)
- **Theme**: Dark glass-cockpit with financial services / trading operations domain language
- **Architecture**: FastAPI + Jinja2 + vanilla CSS, single-container Docker

---

## License

Copyright © 2026 Neomon Labs. All rights reserved.
