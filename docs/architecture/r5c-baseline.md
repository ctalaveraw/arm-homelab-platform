# R5C Management Plane — Initial Baseline

**Captured:** 2026-10-01
**Status:** Brownfield / Pre-Automation
**Purpose:** Reference state for Ansible bootstrap.

## 1. Operating System

```text
Hostname: home-phy-srv-deb-gitops-controller-01
PRETTY_NAME="Armbian 26.11.0-trunk.65 trixie"
VERSION_ID="13"
Kernel: 6.18.54-current-rockchip64
Architecture: aarch64
```

## 2. Hardware and Memory

```text
               total        used        free      shared  buff/cache   available
Mem:           3.8Gi       349Mi       2.1Gi       6.0Mi       1.5Gi       3.5Gi
Swap:          1.9Gi          0B       1.9Gi
```

## 3. Block Devices

```text
NAME           SIZE FSTYPE LABEL           MOUNTPOINTS
sda          931.5G
├─sda1       186.3G vfat   CORAL_MEDIA
└─sda2       745.2G ext4   storage_hdd_ext /srv/storage/archive
mmcblk1       28.9G
└─mmcblk1p1   28.6G ext4   armbi_root      /var/log.hdd
                                           /
mmcblk1boot0     4M
mmcblk1boot1     4M
mmcblk0       29.7G
└─mmcblk0p1   29.7G ext4   storage_sdcard  /srv/storage/state
zram0          1.9G swap                   [SWAP]
zram1           50M ext4   log2ram         /var/log
zram2            0B
```

## 4. Storage Mounts

```text
TARGET             SOURCE         FSTYPE OPTIONS
/srv/storage/state /dev/mmcblk0p1 ext4   rw,noatime
TARGET               SOURCE    FSTYPE OPTIONS
/srv/storage/archive /dev/sda2 ext4   rw,noatime
```

## 5. Filesystem Utilization

```text
Filesystem     Type  Size  Used Avail Use% Mounted on
/dev/mmcblk1p1 ext4   29G  1.9G   26G   7% /
/dev/mmcblk0p1 ext4   30G  2.1M   28G   1% /srv/storage/state
/dev/sda2      ext4  733G   28K  725G   1% /srv/storage/archive
```

## 6. Mount Verification

```text
Success, no errors or warnings detected
```

## 7. Network Interface State

Interface names and link state only.

```text
lo UNKNOWN
enP1p17s0 DOWN
enP2p33s0 UP
```

## 8. Installed Tooling

```text
Git: git version 2.47.3

Docker: Not installed
Compose: Not installed
Ansible: Not installed
```

## 9. Existing /srv Directories

```text
drwx------ 2 runner runner 4096 Oct  1 02:08 /srv/backups
drwx------ 7 runner runner 4096 Oct  1 02:18 /srv/platform
drwx------ 5 runner runner 4096 Oct  1 02:08 /srv/services
drwxr-xr-x 3 runner runner 4096 Sep 28 04:16 /srv/storage/archive
drwxr-xr-x 2 runner runner 4096 Oct  1 01:06 /srv/storage/state
```

## 10. Outstanding Work

- [ ] Establish external Git remote.
- [ ] Review existing bootstrap shell script.
- [ ] Create Ansible inventory.
- [ ] Implement common host role.
- [ ] Implement Docker installation role.
- [ ] Bootstrap Gitea using Compose.
- [ ] Validate backup and recovery strategy.

## Notes

This document captures observed system state.
It does not imply the infrastructure is already
reproducible or configuration-managed.


## Current-state delta — 2026-10-04

This file remains the original brownfield snapshot. It is not rewritten to make later automation appear to have existed at capture time.

Since the baseline:

- the SD state device was replaced with a 128 GB card while retaining `LABEL=storage_sdcard`;
- the USB archive was decommissioned after I/O failures;
- Ansible now manages the host baseline and all management-service lifecycles;
- Docker Engine and Compose are operational;
- Gitea, Gitea Actions runner, Gotify, Uptime Kuma and APT-Cacher-NG are operational;
- GitHub is canonical and Gitea is a private one-way pull mirror;
- GitHub-hosted and physical-R5C ARM64 repository validation are operational;
- `platform-hello` now builds and passes HTTP acceptance in GitHub Actions.

See [the current architecture overview](overview.md) for the live design.
