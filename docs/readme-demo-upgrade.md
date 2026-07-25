# SafeOps README Demo Upgrade

This milestone upgrades the GitHub landing page so a visitor immediately understands the real SafeOps demo.

It adds a generated README section covering:

- latest stable tag
- one-command real Kubernetes recovery demo
- investor/customer evidence bundle command
- expected output
- what the demo proves
- safety boundaries

Run:

```bash
./scripts/demo_update_readme_demo_section.sh
```

Then review:

```bash
git diff -- README.md
```

The script preserves the existing README and writes `README.md.bak` locally. The backup file should not be committed.
