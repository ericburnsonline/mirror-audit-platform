# Phase 02: Application Foundation

## Goal

Establish a working local application stack before moving workloads to Kubernetes.
Validate core service interactions, database schema, and mirror data ingestion
against real-world data.

## Approach

Rather than building directly on the Kubernetes cluster, the application stack was
prototyped locally using Docker Compose. This is intentional — validating that
services communicate correctly and that data models are sound before introducing
cluster complexity.

## Environment

- Windows 11 laptop
- Docker Desktop with WSL2
- Python 3.13 in a virtual environment
- Postgres 15 (Docker)
- Redis 7 (Docker)

## Stack

- **FastAPI** — coordinator service, health check endpoint
- **Postgres** — mirror inventory and audit result storage
- **Redis** — job queue (wired up, ready for workers)
- **BeautifulSoup + requests** — mirror list parsing

## What Was Built

### Coordinator Service

A FastAPI application that serves as the central coordinator. Currently exposes:

- `GET /` — service status
- `GET /health` — live connectivity check against Postgres and Redis

### Database Schema

A `mirrors` table stores the mirror inventory:

```sql
CREATE TABLE mirrors (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10),
    protocol VARCHAR(10),
    url TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW()
);
```

### Mirror Discovery Worker

Fetches the official Slackware mirror list from
`https://mirrors.slackware.com/mirrorlist/`, parses all four protocol sections
(https, http, ftp, rsync), and upserts results into the mirrors table.

First run results:
- 249 mirrors parsed
- 247 new mirrors inserted
- Supports incremental updates — re-running updates `last_seen` without duplicating

## Design Decisions

### Why Local First

Kubernetes adds operational complexity. Validating the application layer locally
means cluster issues and application issues can be debugged independently. Once
the application stack is proven locally, moving it to k8s is a deployment problem,
not a debugging problem.

### Credentials and Secrets

All credentials are stored in a `.env` file that is gitignored. A `.env.example`
is provided for reference. Docker Compose reads credentials from the same `.env`
file as the application — single source of truth, nothing hardcoded.

### Why CHECKSUMS.md5 and Not HEAD Checks

The original motivation for this project was a security principle: get the file
from one source, verify the checksum from another. A compromised mirror could
trivially spoof a HEAD response — file size and timestamp can both be manipulated
in seconds on Linux. Size and date matching tells you nothing about content integrity.

Fetching and comparing CHECKSUMS.md5 content across mirrors against the authoritative
source is a meaningful integrity signal. If a mirror's CHECKSUMS.md5 diverges from
the authoritative source, that mirror is suspect regardless of what HEAD returns.

### Phased Audit Strategy

Audit coverage will expand in stages:

- **Phase A** — Compare `slackware64-15.0/CHECKSUMS.md5` content across all mirrors
  against the authoritative source. A diverging checksum file is a high-value signal
  on its own.
- **Phase B** — Expand to all versions and architectures.
- **Phase C** — Verify individual package files against their checksums.

This approach starts lightweight — one small file per mirror — but produces
high-value results immediately.

## Verification Commands

Start Docker containers:
```bash
docker compose -f infrastructure/docker-compose/docker-compose.yml --env-file .env up -d
```

Check running containers:
```bash
docker ps
```

Start the coordinator service:
```bash
uvicorn coordinator.main:app --reload
```

Verify coordinator endpoints:
```bash
# In browser or curl:
http://127.0.0.1:8000/
http://127.0.0.1:8000/health
```

Initialize the database:
```bash
python -m coordinator.db
```

Run mirror discovery:
```bash
python -m worker.discovery
```

Query mirror inventory:
```bash
docker exec -it map_postgres psql -U map_auditor -d mirror_audit \
  -c "SELECT protocol, count(*) FROM mirrors GROUP BY protocol ORDER BY protocol;"
```

Run mirror audit:
```bash
python -m worker.fetch
```

Run offline analysis:
```bash
python -m worker.analyze
```

## Lessons Learned

### Docker Compose and .env on Windows

Docker Compose does not reliably resolve relative `env_file` paths when run from
a subdirectory on Windows. The reliable solution is to always run Docker Compose
from the project root, passing the env file and compose file explicitly:

```bash
docker compose -f infrastructure/docker-compose/docker-compose.yml --env-file .env up -d
```

### HTML Parsing Requires Inspection

The Slackware mirror list looked simple but required inspecting the actual DOM
structure before the parser worked correctly. Initial assumption about element
nesting was wrong — all mirrors for a protocol section are children of a single
`<p>` tag, not loose elements in the `<pre>` block.

### echo $null Creates BOM Files on Windows PowerShell

Using `echo $null > file.py` in PowerShell creates a file with a UTF-16 BOM
that causes Python syntax errors. Use `New-Item` instead:

```bash
New-Item filename.py -ItemType File -Force
```

## Phase 02 Summary

- Local stack running and verified
- 249 Slackware mirrors ingested from live data
- Database schema in place
- Foundation ready for Phase A audit worker

## Next Steps

- Build Phase A fetch worker — compare CHECKSUMS.md5 across mirrors
- Wire fetch worker to Redis job queue
- Begin Phase 03 — Virtualization Layer on cool
