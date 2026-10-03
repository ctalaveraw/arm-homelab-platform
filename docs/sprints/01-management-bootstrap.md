# Sprint 1 — Management Plane Bootstrap

## PLAT-002.1 — Ansible Preflight

Status: Complete

### Implementation
- Established local R5C inventory.
- Established Ansible project configuration.
- Implemented architecture validation.
- Implemented SD automount activation.
- Validated ext4 and expected filesystem label.
- Validated fstab configuration.

### Verification
- Syntax check passed.
- Playbook executed successfully.
- Recap: ok=6, changed=0, failed=0.
- USB archive intentionally excluded.

### Operational Notes
- USB HDD remains decommissioned pending hardware review.
- Automatic SMART monitoring disabled.
- Storage incident root cause remains unresolved.

### Next
PLAT-002.2: Implement the Ansible common role.

## PLAT-002.2 — Common Role

Status: Complete

### Implementation
- Created reusable common role.
- Defined baseline packages in defaults/main.yml.
- Implemented variable-driven APT task.
- Added python3-apt as a managed dependency.
- Integrated role into 01-management.yml.
- Made preflight inspection check-mode compatible.

### Verification
- Syntax validation passed.
- Check-mode execution passed.
- Two normal executions completed successfully.
- Both reported ok=7, changed=0, failed=0.

### Limitations
Packages were already installed on the R5C.
Fresh-host installation remains untested.

### Next
PLAT-002.3: Declarative directory management.

## PLAT-002.3 — Directory Management

Status: Complete

### Implementation
- Declaratively managed /srv/services.
- Declaratively managed /srv/backups.
- Declaratively managed /srv/storage.
- Enforced runner:runner ownership and 0750 mode.
- Preserved the SD-backed state mount.

### Verification
- First execution: ok=10, changed=1, failed=0.
- One intermediate sudo authentication failure.
- Final execution: ok=10, changed=0, failed=0.
- SD ext4 mount independently verified.
- Directory ownership inspected using stat.

### Next
PLAT-003: Docker Engine and Compose bootstrap.

## PLAT-003 — Docker Host Bootstrap

Status: Complete

### Implementation
- Created reusable docker_host Ansible role.
- Installed Docker using Debian Trixie packages.
- Added docker-cli after runtime verification
  identified the missing CLI dependency.
- Installed standalone Docker Compose v2.
- Managed docker.service declaratively.
- Retained /var/lib/docker on eMMC.

### Verification
- Ansible syntax validation passed.
- Initial Docker installation changed=1.
- Missing CLI identified through runtime testing.
- Corrected package baseline and reapplied.
- Subsequent execution changed=0.
- Docker Engine and containerd active.
- Docker service enabled at boot.
- Docker CLI/server operational.

### Deferred
- USB HDD remains decommissioned.
- Application persistence configured separately.
- Gitea has not yet been deployed.

### Next
PLAT-004: Deploy Gitea with Docker Compose.
