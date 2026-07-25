# SafeOps Demo Screenshots Guide

This guide explains which screens and artifacts to capture for investor, customer, or public demo use.

## Recommended screenshots

1. GitHub README top section  
   Shows the real Kubernetes demo command and investor evidence bundle command.

2. One-command real SafeOps loop terminal result  
   Command:
   ```bash
   ./scripts/demo_run_real_safeops_loop.sh demo aleemughal001
   ```
   Capture the final executive summary showing:
   - Final cluster state: healthy
   - Open root incidents after recovery: 0
   - Executed allowlisted actions: 1
   - Audit verification valid: True
   - Result: PASSED

3. Investor evidence bundle terminal result  
   Command:
   ```bash
   ./scripts/demo_create_investor_bundle.sh demo aleemughal001
   ```
   Capture:
   - Files packaged
   - Demo result: PASSED
   - Audit verification valid: True
   - Bundle zip path

4. Real Kubernetes cockpit dashboard  
   Commands:
   ```bash
   ./scripts/demo_real_k8s_cockpit.sh demo
   ./scripts/demo_open_real_k8s_cockpit.sh
   ```

5. Execution record  
   File:
   ```bash
   less /tmp/safeops-demo/real-k8s-execution-record.md
   ```

6. Tamper-evident audit trail  
   File:
   ```bash
   less /tmp/safeops-demo/real-k8s-audit-trail.md
   ```

7. Release-candidate report  
   Commands:
   ```bash
   ./scripts/demo_release_candidate_check.sh
   less /tmp/safeops-demo/safeops-release-candidate-report.md
   ```

## What these visuals prove

SafeOps can detect a real Kubernetes rollout failure, generate evidence, create a safe remediation plan, record approval, execute only an allowlisted rollback, verify recovery, and produce a tamper-evident audit trail.
