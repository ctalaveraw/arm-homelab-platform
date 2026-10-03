# Incident: R5C USB Storage I/O Failure

Date: 2026-10-03
Status: Mitigated; root cause unresolved.

## Observed Symptoms

- Storage operations became unresponsive.
- Attempted remote reboot did not complete normally.
- SSH temporarily returned connection refused.
- A forced power cycle restored management access.
- systemd subsequently reported smartmontools failure.
- Kernel logs recorded read I/O errors against /dev/sda.

## Investigation

smartd initially exited with status 17 because no
monitorable devices were discovered.

The USB HDD enumerated afterward. Kernel logs recorded
read errors against sectors 136 and 2048.

The timing suggests a possible relationship between
storage I/O and the observed hang, but does not prove
the shutdown's precise failure mechanism.

## Mitigation

- Removed the USB archive from active fstab configuration.
- Disabled automatic SMART monitoring.
- Excluded optional archive storage from Ansible preflight.
- Continued using eMMC and validated SD storage.

## Outstanding

- Determine whether HDD, USB bridge, power or cable
  caused the I/O errors.
- Do not rely on the archive for application backups.
- Establish independent backup and restore procedures.
- Test storage dependencies before stateful deployment.

## Lesson

Optional storage failure must not unnecessarily block
management-plane operation.

Storage availability requires verification beyond
the existence of a directory path.
