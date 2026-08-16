# SiteDown

**IT Operations / SRE / Platform Engineering** — Neomon Proving Grounds

SiteDown simulates a modern IT operations center running cloud-native infrastructure. It covers the full SRE/platform engineering stack: API gateways, Kubernetes clusters, message queues, CDN, CI/CD pipelines, secret management, and multi-region service health. The application demonstrates observability challenges common to any engineering organization: deployment failures, infrastructure scaling, incident management, and SLO tracking.

---

## Quick Start

```bash
cd sitedown
docker compose up -d --build

# Open http://localhost:8004
```

Or run as part of the full suite from the root directory:

```bash
docker compose up -d --build
# SiteDown available at http://localhost:8004
```

---

## Dashboard Views

### NOC Overview
Global service status grid (18 services), overall uptime SLA, API gateway P99 latency, regional health across US-East, EU-West, and AP-Southeast

### Service Health
Critical path service uptime rings (API gateway, authentication, PostgreSQL), Kubernetes cluster status (pods running/pending/crashing, node health), external dependency monitoring (Stripe, SendGrid, Twilio, S3)

### Incidents
Open incidents with priority, MTTR trending, SLO error budget remaining, active incident details with timeline, and recent event chronology

### Fault Console
Interactive fault injection control panel with 24 faults across 6 tiers



---

## Fault Injection Catalog

SiteDown includes **21 fault scenarios** across 5 tiers:

| Tier | Count | Faults |
|------|-------|--------|
| Application | 5 faults | API gateway 5xx surge, OAuth/SSO provider timeout, Kafka consumer lag, CDN cache purge storm, webhook delivery failure |
| Database | 4 faults | Primary-replica replication lag, connection pool exhaustion, Redis cache eviction storm, compliance audit log failure |
| Infrastructure | 4 faults | K8s node CPU pressure, persistent volume I/O degradation, container CrashLoopBackOff, SSL/TLS cert expiry |
| Network / SNMP | 4 faults | SNMP agent unreachable, UPS on battery trap, BGP peer flap, load balancer health check failure |
| CI/CD & DevOps | 4 faults | Deployment pipeline failure, container registry unavailable, secret rotation failure, Terraform state lock contention |


### Cross-Tier Cascade

DEV-01 (deployment failure) → DEV-02 (registry unavailable) → INF-03 (CrashLoopBackOff). A canary deployment fails and triggers rollback, but the registry is down so the rollback image can't be pulled, leaving pods in CrashLoopBackOff — a cascading deployment failure.

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
curl -X POST http://localhost:8004/api/faults/APP-01/activate

# Check active faults
curl http://localhost:8004/api/faults

# Deactivate
curl -X POST http://localhost:8004/api/faults/APP-01/deactivate
```

---

## Datadog Integration

### Custom Metrics

All dashboard KPIs emit custom metrics via DogStatsD with the `sitedown.*` namespace.

### Structured Logging

JSON logs to stdout, ready for Datadog log collection:

```json
{
  "timestamp": "2026-07-12T14:32:00Z",
  "level": "WARNING",
  "service": "sitedown",
  "fault_id": "APP-01",
  "message": "FAULT ACTIVATED: APP-01 — API gateway 5xx surge"
}
```

### APM Traces

FastAPI auto-instrumented with `ddtrace`. Activated faults inject artificial latency and error spans visible in APM flame graphs.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | `8004` | Server listen port |
| `DD_SERVICE` | `sitedown` | Datadog APM service name |
| `DD_ENV` | `proving-grounds` | Datadog environment tag |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `FAULT_STATE_FILE` | `/app/data/faults.json` | Fault state persistence path |

---

## Design

- **Accent color**: Purple (#a78bfa)
- **Theme**: Dark glass-cockpit with it operations / sre / platform engineering domain language
- **Architecture**: FastAPI + Jinja2 + vanilla CSS, single-container Docker

---

## License

Copyright © 2026 Neomon Labs. All rights reserved.
