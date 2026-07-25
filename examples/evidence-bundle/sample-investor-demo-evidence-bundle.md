# Sample SafeOps Investor Evidence Bundle Output

A successful bundle run should end with output similar to:

```text
SafeOps investor demo evidence bundle created.
Bundle directory: /tmp/safeops-demo/safeops-investor-demo-bundle-demo-20260724-221500
Bundle zip: /tmp/safeops-demo/safeops-investor-demo-bundle-demo-20260724-221500.zip
Files packaged: 16
Demo result: PASSED
Audit verification valid: True
Executed allowlisted actions: 1
```

The bundle proves the end-to-end SafeOps recovery loop:

```text
real Kubernetes failure
→ evidence collection
→ remediation plan
→ human approval
→ allowlisted execution
→ health verification
→ tamper-evident audit trail
→ investor-ready evidence package
```
