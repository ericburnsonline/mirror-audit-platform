# Mirror Audit Platform

A distributed system for auditing Linux distribution mirrors for consistency using Kubernetes.

This project validates file integrity across public mirrors by distributing checksum and metadata verification workloads across a cluster. It is designed as a real-world system that balances performance, fairness to external services, and scalable architecture.

## Build Notes

This repository is not intended to be a universal Kubernetes installation guide.  
Instead, the `docs/phases/` directory documents the environment, design decisions, validation commands, and lessons learned while building this platform.

## Overview

Linux distributions are hosted across many public mirrors. While rare, inconsistencies can occur due to sync delays, partial updates, or corruption.

This system periodically audits mirrors by:

* Fetching file metadata (size, checksums)
* Comparing results across mirrors
* Identifying inconsistencies or anomalies
* Publishing results through a public dashboard

The goal is not to mirror data, but to **verify integrity across distributed sources**.

## Key Features

* Distributed validation using Kubernetes workers
* Parallel checksum and metadata collection
* Mirror-aware request distribution to avoid overloading sources
* Batch execution model (periodic audits rather than constant crawling)
* Centralized result collection and comparison
* Extensible to multiple Linux distributions

## Architecture

The system is composed of several logical components:

### Coordinator

Maintains the list of:

* Mirrors
* Distribution paths (starting with Slackware)

Distributes work to worker nodes.

### Workers

Kubernetes-managed workloads that:

* Retrieve file metadata from assigned mirrors
* Calculate or validate checksums
* Return structured results

### Result Store

Central storage for:

* Crawl results
* Historical runs
* Comparison data

### Analysis Layer

Processes collected data to:

* Compare mirrors
* Detect inconsistencies
* Flag anomalies

### Public Dashboard

A lightweight, separate system that:

* Displays audit results
* Shows crawl history
* Highlights inconsistencies

## Infrastructure

### Host System

* Ubuntu Server (LTS)
* RAID 10 SSD storage for performance
* High-core-count system for parallel workloads

### Cluster Design

* Multi-node Kubernetes cluster (VM-based)
* Separate control plane and worker nodes
* Designed to simulate production-style environments

### Storage Strategy

* SSD RAID 10 for active workloads and cluster performance
* Optional secondary storage (HDD) for archival data and backups

## Design Considerations

### Fair Usage

The system avoids overloading mirrors by:

* Randomizing request distribution
* Controlling concurrency

### Batch Processing

Audits run periodically rather than continuously to:

* Reduce unnecessary load
* Improve efficiency
* Align with real-world usage patterns

### Scalability

Workloads scale horizontally via Kubernetes:

* Additional workers increase throughput
* System can adapt to available resources

### Performance Optimization

The system is designed to:

* Maximize parallelism across CPU cores
* Balance network and I/O workloads
* Support future benchmarking and tuning

## Roadmap

### Project Phases

- [Phase 01 – Host Foundation](docs/phases/01-host-foundation.md) Completed
- [Phase 02 – Virtualization Layer](docs/phases/02-virtualization.md) In Progress
- [Phase 03 – VM Cluster Nodes](docs/phases/03-vm-cluster-nodes.md) Planned
- [Phase 04 – Kubernetes Cluster](docs/phases/04-kubernetes-cluster.md) Planned
- [Phase 05 – Mirror Worker System](docs/phases/05-mirror-worker.md) Planned
- [Phase 06 – Data Storage](docs/phases/06-result-storage.md) Planned
- [Phase 07 – Dashboard](docs/phases/07-dashboard.md) Planned
- [Phase 08 – Performance Tuning](docs/phases/08-performance.md) Planned

### Phase 1

* Base system setup (Ubuntu + RAID)
* Kubernetes cluster deployment

### Phase 2

* Basic worker jobs (single file validation)
* Parallel job execution

### Phase 3

* Mirror list ingestion
* Distributed crawl execution

### Phase 4

* Result storage and comparison logic

### Phase 5

* Public dashboard

### Phase 6

* Adaptive scaling and performance tuning

## Future Enhancements

* Support for additional distributions beyond Slackware
* Advanced anomaly detection
* Storage tiering (SSD vs archival storage)
* Performance benchmarking across hardware configurations
* Automated scheduling and reporting

## Why This Project

This project is designed to explore:

* Distributed systems design
* Kubernetes-based workload orchestration
* Real-world performance and scaling considerations
* Data integrity validation across decentralized infrastructure

It is intentionally built as a **production-style system**, not a toy example.

## License

Licensed under MIT for simplicity and ease of reuse.
