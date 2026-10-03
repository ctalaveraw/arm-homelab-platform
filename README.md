# Homelab Platform

Reproducible infrastructure and platform engineering
laboratory.

## Architecture

Management plane:
- NanoPi R5C
- Armbian
- Docker Compose (planned)
- Ansible-managed configuration (planned)

Compute plane:
- Existing upstream Kubernetes cluster
- kubeadm-based deployment
- Raspberry Pi hardware
- One control-plane node and two workers
- Fourth Pi reserved for bootstrap testing

## Objectives

1. Capture existing infrastructure.
2. Automate the management plane.
3. Establish external Git and CI/CD.
4. Codify Kubernetes configuration.
5. Demonstrate deployment and recovery.
6. Introduce GitOps and observability.

## Working principles

- Git is the configuration source of truth.
- Existing working infrastructure is preserved.
- Every sprint produces verifiable evidence.
- Architectural decisions are documented.
- Bootstrap must not depend on Gitea.
