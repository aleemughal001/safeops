# SafeOps Fresh Clone Demo Test

This milestone verifies that the public demo can be validated from a clean clone instead of relying only on the existing working directory.

## Command

```bash
./scripts/demo_fresh_clone_check.sh
```

The command creates a temporary clone under `/tmp/safeops-demo`, runs the repository smoke test inside the clean clone, checks that the public demo documentation and demo commands exist, and writes a report.

## What this proves

- The repository can be cloned cleanly.
- The smoke test passes in a fresh checkout.
- The README documents the real Kubernetes demo and investor bundle.
- The key demo scripts are present and executable.
- The latest public demo tags exist.

## Reports

The command writes:

```text
/tmp/safeops-demo/safeops-fresh-clone-report.json
/tmp/safeops-demo/safeops-fresh-clone-report.md
/tmp/safeops-demo/fresh-clone-ci-output.txt
```
