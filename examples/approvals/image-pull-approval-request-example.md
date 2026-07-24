# Example Approval Request

This example represents the approval gate output for an image pull failure.

```text
Approval Request: Image pull failure / bad image or registry access
Target: demo/checkout-api
Severity: medium
Category: image_or_registry
Approval required: true
Policy check required: true
Detector can execute: false
```

Recommended options include inspecting image publication, rolling back the deployment, or restoring a known-good image. Production-changing actions are approval-required and policy-required.
