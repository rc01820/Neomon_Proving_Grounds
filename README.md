# Neomon Proving Grounds

**A suite of fault-injectable demo applications for observability enablement.**

Neomon Proving Grounds is a collection of four Docker-based web applications, each themed around a different industry vertical. Every app ships with a dark, glass-cockpit-style dashboard, a built-in chaos engine, and a fault injection console — designed as proving grounds for monitoring platforms like Datadog and SolarWinds.

Break things on purpose. Watch the signals light up. Learn what good observability looks like.

---

## The Suite

| App | Theme | Port | Faults | Description |
|-----|-------|------|--------|-------------|
| **AvionDash** | Aviation / FAA | `8001` | 22 | Flight operations, ATC systems, fleet management, weather/NOTAM, SNMP/network device monitoring |
| **CodeBlue** | Healthcare | `8002` | 24 | Hospital command center, patient flow, clinical systems (EHR/PACS/LIS), medical device telemetry |
| **BlackLedger** | Financial Services | `8003` | 24 | Trading floor, risk & compliance, transaction processing, market data, settlement systems |
| **SiteDown** | IT Operations | `8004` | 24 | NOC overview, service health, incident management, CI/CD pipelines, multi-cloud infrastructure |

Each application follows the same architecture:

- **FastAPI** backend with Jinja2 templates
- **Dark glass-cockpit UI** with tabbed dashboard views
- **Fault injection engine** with tiered fault catalog
- **Docker Compose** for single-command deployment
- **Observable by design** — every fault maps to specific metrics, logs, traces, and monitors

---

## Quick Start

### Interactive installer (recommended)

```bash
./install.sh
```

The installer walks you through selecting which apps to deploy and lets you customize ports. It also checks Docker prerequisites and port availability.

```bash
./install.sh status    # Check what's running
./install.sh stop      # Stop all apps
```

### Run the entire suite

```bash
docker compose --profile all up -d --build

# Apps are available at:
#   AvionDash:    http://localhost:8001
#   CodeBlue:     http://localhost:8002
#   BlackLedger:  http://localhost:8003
#   SiteDown:     http://localhost:8004
```

### Run by vertical (profiles)

Each app has a compose profile for selective deployment:

```bash
# Healthcare customer — just CodeBlue
docker compose --profile healthcare up -d --build

# Financial services — just BlackLedger
docker compose --profile financial up -d --build

# Multiple verticals
docker compose --profile healthcare --profile financial up -d --build
```

| Profile | App | Port |
|---------|-----|------|
| `aviation` | AvionDash | 8001 |
| `healthcare` | CodeBlue | 8002 |
| `financial` | BlackLedger | 8003 |
| `it-ops` | SiteDown | 8004 |
| `all` | All apps | 8001–8004 |

### Run a single app (standalone)

Each app is fully self-contained. Copy the folder to a customer and run it independently:

```bash
cd codeblue
cp .env.example .env    # Customize ports, Datadog config, etc.
docker compose up -d --build
# http://localhost:8002
```

### Custom ports

Override ports via environment variables or `.env`:

```bash
# Via environment
CODEBLUE_PORT=9002 docker compose --profile healthcare up -d --build

# Via .env file (per app)
cd codeblue
echo "APP_PORT=9002" > .env
docker compose up -d --build
```

### Stop

```bash
docker compose --profile all down     # Stop all (root compose)
cd codeblue && docker compose down    # Stop one app (standalone)
```

---

## Customer Delivery

### Package individual apps for delivery

Use `package.sh` to create standalone archives for specific customers:

```bash
# Package CodeBlue for a healthcare customer
./package.sh codeblue
# → dist/codeblue-20260816.tar.gz

# Package multiple apps together
./package.sh aviondash blackledger
# → dist/proving-grounds-aviondash-blackledger-20260816.tar.gz

# Package all apps as separate archives + a full bundle
./package.sh --all
# → dist/aviondash-20260816.tar.gz
# → dist/codeblue-20260816.tar.gz
# → dist/blackledger-20260816.tar.gz
# → dist/sitedown-20260816.tar.gz
# → dist/neomon-proving-grounds-20260816.tar.gz

# Custom output directory
./package.sh codeblue --output ~/customer-drops
```

Each packaged archive is fully self-contained — the customer extracts it, runs `docker compose up -d --build`, and they're running.

### Per-customer configuration

Each app includes a `.env.example` with all configurable settings:

```bash
cd codeblue
cp .env.example .env

# Edit for this customer's environment
vi .env
```

Key settings per customer:

| Variable | Purpose | Example |
|----------|---------|---------|
| `APP_PORT` | Change the listen port | `9002` |
| `DD_SERVICE` | Datadog service name | `acme-codeblue` |
| `DD_ENV` | Datadog environment tag | `acme-staging` |
| `DD_AGENT_HOST` | Datadog agent hostname | `dd-agent.internal` |
| `LOG_LEVEL` | Logging verbosity | `DEBUG` |

---

## Architecture

Every app in the suite shares the same internal architecture:

```
┌─────────────────────────────────────────────────┐
│  Browser (Dark Glass-Cockpit UI)                │
│  ┌───────────┬───────────┬───────────┬────────┐ │
│  │ Dashboard │ Dashboard │ Dashboard │ Fault  │ │
│  │  View 1   │  View 2   │  View 3   │Console │ │
│  └─────┬─────┴─────┬─────┴─────┬─────┴───┬────┘ │
│        │           │           │         │       │
│  ┌─────▼───────────▼───────────▼─────────▼────┐  │
│  │           FastAPI Application              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │  Routes  │  │  Fault   │  │  Config  │  │  │
│  │  │ /dash/*  │  │  Engine  │  │  Store   │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  │  │
│  └────────────────────────────────────────────┘  │
│                    Docker Container              │
└─────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   Datadog Agent        Log Aggregation
   (metrics, APM,       (structured JSON
    traces, SNMP)        log output)
```

### Fault Injection Engine

Each app's chaos engine works the same way:

1. **Fault catalog** — a structured list of faults organized by tier (Application, Database, Infrastructure, Network, and one or two domain-specific tiers)
2. **Activation API** — `POST /api/faults/{fault_id}/activate` and `POST /api/faults/{fault_id}/deactivate`
3. **State store** — in-memory fault state with JSON persistence at `/app/data/faults.json`
4. **Effect simulation** — activated faults alter dashboard metrics, inject errors into logs, and modify API response times
5. **Fault console UI** — browser-based control panel to activate/deactivate faults and observe real-time effects

### Fault Tier Structure

Every app organizes faults into tiers that mirror real-world observability layers:

| Tier | Prefix | Common Across Apps |
|------|--------|--------------------|
| Application | `APP-` | API latency, auth failures, service errors |
| Database | `DB-` | Replication lag, connection pool exhaustion, slow queries |
| Infrastructure | `INF-` | CPU saturation, disk I/O, container OOM, cert expiry |
| Network / SNMP | `NET-` | SNMP agent unreachable, interface saturation, traps |
| Domain-specific | Varies | Industry-specific faults unique to each app |

---

## Datadog Integration

Each app is designed to be monitored with Datadog. The integration points include:

### Metrics (DogStatsD)
Every dashboard KPI emits a custom metric via DogStatsD:
```
# Example: CodeBlue
codeblue.ed.wait_time_avg
codeblue.bed.occupancy_pct
codeblue.ehr.response_time_p99

# Example: BlackLedger
blackledger.trade.latency_p99
blackledger.settlement.failure_rate
blackledger.risk.var_utilization
```

### Logs (Structured JSON)
All apps emit structured JSON logs to stdout:
```json
{
  "timestamp": "2026-07-12T14:32:00Z",
  "level": "ERROR",
  "service": "codeblue",
  "fault_id": "APP-03",
  "message": "dicom_retrieve timeout=15s study_uid=1.2.840...",
  "tags": ["tier:application", "severity:critical"]
}
```

### APM / Traces
FastAPI is auto-instrumented with `ddtrace`. Activated faults inject artificial latency and error spans into traces, visible in Datadog APM flame graphs.

### Monitors
Each fault's README entry includes the recommended Datadog monitor configuration — metric query, threshold, alert message, and escalation path.

---

## Directory Structure

```
neomon-proving-grounds/
├── README.md                    ← You are here
├── docker-compose.yml           ← Runs all four apps
│
├── aviondash/                   ← Aviation / FAA
│   ├── README.md
│   ├── Dockerfile
│   ├── docker-compose.yml       ← Standalone
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── faults.py
│       ├── static/css/style.css
│       └── templates/
│           ├── base.html
│           ├── dashboard.html
│           ├── systems.html
│           ├── fleet.html
│           └── faults.html
│
├── codeblue/                    ← Healthcare
│   ├── README.md
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── faults.py
│       ├── static/css/style.css
│       └── templates/
│           ├── base.html
│           ├── command_center.html
│           ├── patient_flow.html
│           ├── clinical_systems.html
│           └── faults.html
│
├── blackledger/                 ← Financial Services
│   ├── README.md
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── faults.py
│       ├── static/css/style.css
│       └── templates/
│           ├── base.html
│           ├── trading_floor.html
│           ├── risk_compliance.html
│           ├── transactions.html
│           └── faults.html
│
└── sitedown/                    ← IT Operations
    ├── README.md
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    └── app/
        ├── main.py
        ├── config.py
        ├── faults.py
        ├── static/css/style.css
        └── templates/
            ├── base.html
            ├── noc_overview.html
            ├── service_health.html
            ├── incidents.html
            └── faults.html
```

---

## Observability Use Cases

The Proving Grounds suite is designed for:

- **Datadog POCs** — Spin up an app, connect the agent, and demo every major Datadog feature (APM, logs, metrics, SNMP, synthetics, RUM) against a realistic workload
- **Training & enablement** — Teach teams how to build monitors, set SLOs, correlate signals, and perform root cause analysis
- **Chaos engineering practice** — Inject faults and practice incident response workflows
- **Technology partner demonstrations** — Showcase observability platform capabilities to prospects in their industry's language
- **Interview & assessment** — Use as a sandbox for evaluating SRE/DevOps candidates on real observability scenarios

---

## Cross-App Scenarios

For advanced demos, run multiple apps simultaneously and simulate cross-service incidents:

| Scenario | Apps Involved | Story |
|----------|---------------|-------|
| Shared infrastructure failure | All | A DNS outage or storage array failure ripples across all four verticals |
| Compliance cascade | CodeBlue + BlackLedger | HIPAA audit log failure (CodeBlue DB-04) mirrors SOX audit failure (BlackLedger DB-04) |
| Network backbone | All | SNMP interface saturation (NET-03) affects every app's connectivity layer |
| Third-party API outage | BlackLedger + SiteDown | Market data feed failure cascades into SiteDown's external dependency monitoring |

---

## Requirements

- Docker Engine 20.10+
- Docker Compose v2+
- 4 GB RAM (1 GB per app)
- Datadog Agent (optional, for full observability integration)

---

## Configuration

Each app reads configuration from environment variables defined in its `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | (per app) | Application identifier used in metrics and logs |
| `APP_PORT` | (per app) | Port the FastAPI server listens on |
| `DD_AGENT_HOST` | `datadog-agent` | Hostname of the Datadog agent |
| `DD_SERVICE` | (per app) | Datadog APM service name |
| `DD_ENV` | `proving-grounds` | Datadog environment tag |
| `LOG_LEVEL` | `INFO` | Application log level |
| `FAULT_STATE_FILE` | `/app/data/faults.json` | Path to fault state persistence file |

---

## License

Copyright © 2026 Neomon Labs. All rights reserved.

---

## Links

- **Neomon Labs** — [https://www.neomon.com](https://www.neomon.com)
- **AvionDash Suite** — [https://avion.neomon.com](https://avion.neomon.com)
