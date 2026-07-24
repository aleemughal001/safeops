# SafeOps Incident Scenario Library

This directory is reserved for repeatable incident scenarios used to test and evaluate SafeOps.

The goal is not to keep only one controlled demo. SafeOps should grow into an expandable Incident Intelligence Library.

Initial categories:

- Kubernetes workload failures
- configuration failures
- image and registry failures
- CI/CD release failures
- networking and Service/Ingress failures
- resource pressure and scheduling failures
- dependency and database failures
- security and policy failures
- observability and alerting failures
- human/operator mistakes

Each scenario should eventually include:

- failure manifest or injection script
- expected Kubernetes symptoms
- expected evidence
- expected root-cause classification
- safe remediation options
- verification checks
- prevention recommendation
