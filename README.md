# Mirror Audit Platform

A Linux mirror consistency and integrity auditing platform being built around Kubernetes.

Mirror Audit Platform collects checksum information from independent Linux distribution mirrors, compares the results, records discrepancies, and ultimately will publish historical mirror consistency data through a public dashboard.

Slackware is the first supported distribution.

## Why This Project Exists

Years ago, a Linux instructor gave me a piece of advice that stuck with me:

When downloading software from a mirror, obtain the software from one source and verify its checksum using a different, independent source.

The reasoning is straightforward. If a server is compromised, an attacker may be able to replace both a file and the checksum stored beside it. Compromising multiple independent sources is a substantially different problem.

That idea of **split-source verification** is the starting point for this project.

Linux distributions commonly make releases available through many independently operated mirrors. Mirror Audit Platform is intended to periodically compare integrity information across those mirrors and identify differences worth investigating.

A discrepancy does **not** automatically indicate compromise. Legitimate explanations can include synchronization delays, stale mirrors, incomplete content, configuration differences, or network problems. The purpose of the system is to identify and preserve those differences so they can be analyzed.

## Project Goals

The long-term system is intended to:

* Maintain an inventory of mirrors for supported Linux distributions
* Periodically retrieve published checksum information
* Compare checksum manifests and individual checksum entries across sources
* Identify missing, stale, unreachable, or inconsistent mirrors
* Preserve historical audit results
* Distribute mirror checks across multiple Kubernetes workers
* Control concurrency and request rates to avoid abusing public mirror infrastructure
* Adapt worker concurrency to available resources and workload
* Publish audit coverage and consistency results through a lightweight public dashboard
* Provide measurable data for performance and scalability experiments

The project also serves as a hands-on environment for learning and operating Kubernetes using a workload that has a real purpose beyond demonstrating Kubernetes itself.

## Current Status

**Active development**

The project currently has two completed foundation phases.

### Host Foundation

A dedicated physical server has been prepared as the eventual Kubernetes host:

* Ubuntu Server 24.04 LTS
* 2 x AMD Opteron 6128 processors
* 16 physical CPU cores
* 160 GB RAM
* Four-SSD Linux software RAID10
* Approximately 929 GB RAID capacity
* KVM/libvirt hardware virtualization enabled and verified

The next infrastructure milestone is to create reproducible virtual machines for Kubernetes control-plane and worker nodes.

### Application Foundation

Before introducing Kubernetes, the initial application components were developed locally so application problems could be separated from cluster problems.

The current prototype includes:

* FastAPI coordinator service
* PostgreSQL mirror inventory
* Redis service available for the future work queue
* Slackware mirror discovery
* Slackware `CHECKSUMS.md5` retrieval
* Checksum parsing and comparison
* Local preservation of retrieved checksum manifests
* Offline comparison and anomaly reporting

The initial Slackware discovery run parsed 249 mirror entries and inserted 247 unique mirrors into PostgreSQL.

Redis connectivity is currently validated by the coordinator, but the audit workers have **not yet been converted to Redis-backed distributed workers**.

## Current Audit Scope

The first audit target is:

```text
slackware64-15.0/CHECKSUMS.md5
```

The current prototype:

1. Retrieves the authoritative Slackware checksum manifest.
2. Loads active HTTPS mirrors from the database.
3. Retrieves the corresponding `CHECKSUMS.md5` from each reachable mirror.
4. Validates that the response resembles a checksum file rather than an HTML error page.
5. Parses individual filename/checksum entries.
6. Compares mirror entries against the authoritative manifest.
7. Separates results into matching, mismatching, missing, invalid, and unreachable categories.
8. Saves retrieved manifests for later offline analysis.

The current worker is sequential. Distributing this workload across Kubernetes workers is a later phase of the project.

## Audit Strategy

Audit coverage is intentionally being expanded in stages.

### Stage A - Checksum Manifest Comparison

Compare the Slackware 15.0 64-bit `CHECKSUMS.md5` manifest across mirrors.

This is inexpensive for both the auditing system and the public mirrors because it requires retrieving one relatively small file from each source.

### Stage B - Broader Distribution Coverage

Expand checksum comparison across additional Slackware versions and architectures.

### Stage C - File Verification

Retrieve selected files and independently calculate their checksums to verify that actual mirror content agrees with published checksum data.

### Later - Cross-Source Analysis

Expand the analysis beyond a single authoritative comparison to examine agreement and disagreement among multiple independent mirrors and historical audit runs.

This is closer to the split-source verification principle that originally motivated the project.

## Architecture

The project is being built incrementally. The current application prototype and the target distributed architecture are deliberately separated below.

### Current Prototype

```text
Slackware Mirror List
        |
        v
Mirror Discovery
        |
        v
   PostgreSQL
        |
        v
 Sequential Fetch Worker
        |
        +----> Authoritative CHECKSUMS.md5
        |
        +----> Mirror CHECKSUMS.md5 files
        |
        v
 Local Checksum Data
        |
        v
 Offline Analysis
```

FastAPI provides coordinator and health endpoints. PostgreSQL stores the current mirror inventory. Redis is running and health-checked but is not yet performing workload distribution.

### Target Architecture

```text
                  +----------------------+
                  |     Coordinator      |
                  +----------+-----------+
                             |
                             v
                     +---------------+
                     |   Work Queue  |
                     +-------+-------+
                             |
             +---------------+---------------+
             |               |               |
             v               v               v
        +---------+      +---------+      +---------+
        | Worker  |      | Worker  |      | Worker  |
        |   Pod   |      |   Pod   |      |   Pod   |
        +----+----+      +----+----+      +----+----+
             |                |                |
             +----------------+----------------+
                              |
                              v
                       Linux Mirrors
                              |
                              v
                       +--------------+
                       | Result Store |
                       +------+-------+
                              |
                              v
                         Analysis
                              |
                              v
                    Public Status Site
```

Kubernetes will eventually orchestrate the audit workers and supporting application components.

## Why Kubernetes?

Kubernetes is not required to retrieve a checksum file from a mirror. The initial prototype intentionally proves that.

The value of Kubernetes becomes more relevant as the system expands to:

* Hundreds or thousands of independent audit tasks
* Multiple Linux distributions and releases
* Worker isolation
* Resource requests and limits
* Controlled parallelism
* Scheduled batch workloads
* Worker failure and retry handling
* Horizontal scaling
* Application health monitoring
* Reproducible deployment
* Performance experiments involving different worker counts and resource allocations

Using a meaningful batch workload makes it possible to explore these capabilities while measuring whether additional complexity actually provides useful benefits.

## Fair Use

Public Linux mirrors are shared infrastructure. Avoiding unnecessary load is a core design requirement.

The distributed implementation is expected to include:

* Per-mirror request limits
* Controlled worker concurrency
* Request scheduling
* Mirror-aware workload distribution
* Retry backoff
* Timeouts
* Periodic batch operation instead of continuous crawling

The goal is to gather useful integrity information without behaving like an aggressive crawler.

## Infrastructure Strategy

### Physical Host

The Kubernetes lab runs on older server hardware rather than a cloud environment.

That is intentional.

The server provides enough CPU and memory for a multi-node virtualized cluster while also creating useful constraints for performance analysis.

The current host has:

| Resource             | Configuration           |
| -------------------- | ----------------------- |
| CPUs                 | 2 x AMD Opteron 6128    |
| Physical cores       | 16                      |
| RAM                  | 160 GB                  |
| Primary storage      | 4 x SSD                 |
| RAID                 | Linux software RAID10   |
| Usable RAID capacity | ~929 GB                 |
| Host OS              | Ubuntu Server 24.04 LTS |
| Virtualization       | KVM/libvirt             |

The CPUs can also be upgraded inexpensively, creating an opportunity to establish a baseline, change the hardware, and compare workload performance under otherwise similar conditions.

### Virtual Machines

The Kubernetes cluster will run on KVM virtual machines rather than directly on the physical host.

The planned topology includes:

* Dedicated control-plane VM
* Multiple worker VMs
* Explicit CPU, memory, and disk allocations
* Reproducible node definitions

This keeps the physical host separate from the Kubernetes nodes and makes rebuilding or experimenting with cluster configurations considerably easier.

### Storage

SSD RAID10 is used for the active system, VM disks, and working data.

Large spinning disks may later be added as a separate storage tier for:

* Historical results
* Database backups
* VM backups
* Archived audit data

They are not required for the initial implementation.

## Performance and Adaptive Scaling

One of the later goals is to determine how much parallelism this workload can use effectively.

Potential measurements include:

* Audit completion time
* Checks per second
* CPU utilization
* Memory utilization
* Network throughput
* Storage I/O
* Worker queue depth
* Worker failure rate
* Mirror response latency

Rather than simply configuring an arbitrarily large number of workers, the eventual system may adjust concurrency according to workload and host conditions.

Because the physical host supports inexpensive CPU upgrades, the same audit workload can also be used for before-and-after hardware comparisons.

## Project Phases

The phase documents are a **build journal**, not a generic Kubernetes installation guide.

They record:

* What was being built
* Important design decisions
* Commands used to validate the environment
* Expected results
* Problems encountered
* Troubleshooting
* Lessons learned

### Completed

* [Phase 01 - Host Foundation](docs/phases/01-host-foundation.md)
* [Phase 02 - Application Foundation](docs/phases/02-application-foundation.md)

### In Progress

**Phase 03 - Virtualization Layer**

Create and validate the KVM/libvirt VM environment that will host the Kubernetes nodes.

A Phase 03 document will be added as the work progresses.

### Planned

* **Phase 04 - VM Cluster Nodes** - Define and create the control-plane and worker VMs.
* **Phase 05 - Kubernetes Cluster** - Build and validate the multi-node Kubernetes environment.
* **Phase 06 - Distributed Mirror Workers** - Move audit work into Kubernetes-managed workers and introduce queue-based dispatch.
* **Phase 07 - Result Storage and Analysis** - Persist audit runs and structured results for historical comparison.
* **Phase 08 - Public Dashboard** - Publish audit coverage, dates, status, and consistency information.
* **Phase 09 - Performance Tuning** - Measure scaling behavior and experiment with adaptive concurrency and hardware changes.

Links will be added as each phase document is created.

## Repository Layout

```text
mirror-audit-platform/
├── coordinator/
│   ├── db.py
│   └── main.py
├── dashboard/
├── docs/
│   └── phases/
│       ├── 01-host-foundation.md
│       └── 02-application-foundation.md
├── infrastructure/
│   └── docker-compose/
│       └── docker-compose.yml
├── tests/
├── worker/
│   ├── analyze.py
│   ├── discovery.py
│   └── fetch.py
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

`dashboard/` and `tests/` currently contain placeholders for later development.

## Development Approach

This repository intentionally preserves some of the path taken to build the system instead of presenting a fictional perfect implementation.

Examples already documented include:

* RAID10 boot-layout tradeoffs
* BIOS virtualization configuration
* KVM validation
* Libvirt permissions
* Docker Compose environment handling on Windows
* Incorrect assumptions about the Slackware mirror-list HTML structure

The intent is to document not only **what worked**, but also **why decisions were made and what was learned when assumptions were wrong**.

AI tools are being used to assist with design, research, development, troubleshooting, and documentation. Generated suggestions are tested against the actual environment rather than treated as authoritative.

## Near-Term Work

The immediate priorities are:

1. Complete the first KVM virtual machine and establish a repeatable VM creation process.
2. Build the VM topology for the Kubernetes cluster.
3. Bring up and validate the Kubernetes cluster.
4. Convert the current sequential audit prototype into distributed workers.
5. Introduce Redis-backed work dispatch and structured audit-result persistence.

## Future Directions

Potential later work includes:

* Additional Linux distributions
* SHA-256 and other checksum formats
* Historical mirror health and consistency trends
* Mirror synchronization analysis
* Retry and failure classification
* Kubernetes autoscaling experiments
* Metrics and observability
* Automated scheduling
* Cold-storage archival
* Public API access
* Hardware performance comparisons
* Adaptive concurrency

## License

This project is licensed under the MIT License for simplicity and ease of reuse.
