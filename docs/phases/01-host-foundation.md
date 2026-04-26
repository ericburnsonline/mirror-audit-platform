# Phase 01: Host Foundation

## Goal
Set up the base Ubuntu host with RAID10 storage and networking.

## Environment
- Host OS: Ubuntu 24.04.4 LTS
- CPU: 16 cores at 2GHz
- RAM: 160 GB
- Storage: 929G RAID10

## Decisions
- Ubuntu Server LTS
- Software RAID10 via mdadm
  - I should have created a 1-2MB BIOS partion on each physical disk before creating md0 components
- KVM planned for VM-based Kubernetes nodes

## Verification Commands

After a
```bash
sudo apt update
```
I added a few other tools via
```bash
sudo apt install -y cpu-checker qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager
```

```bash
lsblk
cat /proc/mdstat
df -h
lscpu
free -h
ip a
```

## Verification

### Storage Layout

#### Command

```bash
lsblk
```

#### Expected

- 4 physical disks are visible, such as `sda`, `sdb`, `sdc`, and `sdd`
- A RAID device is present, such as `md0`, and it is RAID10
- A partition on the RAID device is mounted as `/`

Example:

```text
md0       raid10
└─md0p1   /
```

#### Problems to Watch For

- Fewer disks than expected
- No `md0` RAID device
- Root filesystem `/` is not mounted on the RAID device
- Unexpected leftover partitions from previous installs

---

### RAID Health

#### Command

```bash
cat /proc/mdstat
```

#### Expected

- RAID status shows `active raid10`
- All four disks are present
- Status shows `[4/4] [UUUU]`

Example:

```text
md0 : active raid10 sda3[3] sdd[2] sdc[1] sdb[0]
      [4/4] [UUUU]
```

RAID10 on my system shows as:

```text
Personalities : [raid10] [raid0] [raid1] [raid6] [raid5] [raid4]
md0 : active raid10 sda3[3] sdd[2] sdc[1] sdb[0]
      974911488 blocks super 1.2 512K chunks 2 near-copies [4/4] [UUUU]
      bitmap: 0/8 pages [0KB], 65536KB chunk

unused devices: <none>
```

#### Problems to Watch For

- `[U_UU]`, `[UUU_]`, or similar degraded status
- Missing devices
- RAID rebuild in progress that does not complete
- No RAID array listed

---

### Filesystem Usage

#### Command

```bash
df -h
```

#### Expected

- Root filesystem `/` is mounted on `/dev/md0p1`
- Available space is large enough for VMs and workloads
- Usage is low after initial install

Example from this system:

```text
/dev/md0p1   914G   13G   855G   2% /
```

#### Problems to Watch For

- Root mounted on a single disk instead of RAID
- Very low available space
- Missing root mount
- Unexpected mount layout

---

### CPU / System Info

#### Command

```bash
lscpu
```

#### Expected

- 16 CPUs total
- 2 sockets
- 8 cores per socket
- AMD virtualization flag `svm` is present

Example:

```text
CPU(s):              16
Socket(s):           2
Core(s) per socket:  8
Flags:               ... svm ...
```

#### Problems to Watch For

- Fewer CPUs than expected
- Missing `svm` flag
- Incorrect socket or core count
- BIOS virtualization disabled
  - for this I had to enable it in the BIOS

---

### Memory

#### Command

```bash
free -h
```

#### Expected

- Approximately 160GB total memory
- Most memory available after fresh install
- Swap is present

Example:

```text
               total        used        free      shared  buff/cache   available
Mem:           157Gi       1.5Gi       155Gi       1.5Mi       1.7Gi       155Gi
Swap:          8.0Gi          0B       8.0Gi
```

#### Problems to Watch For

- Significantly less RAM than expected
- High memory usage immediately after install
- No swap configured

---

### Network

#### Command

```bash
ip a
```

#### Expected

- One active network interface
- Interface state is `UP`
- Valid IPv4 address is assigned

Example:

```text
enp2s0: state UP
inet 192.168.1.200/24
```

#### Problems to Watch For

- No IPv4 address
- Main interface is `DOWN`
- Multiple conflicting active interfaces
- No network connectivity

---

## Phase 01 Confirmation

- RAID10 is active and healthy
- Root filesystem is mounted on RAID storage
- CPU and memory match expected hardware
- Network is functional
- Host is ready for virtualization setup

END
