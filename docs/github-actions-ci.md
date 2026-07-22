# SafeOps GitHub Actions CI

Milestone 16 adds a lightweight continuous-integration smoke test for the SafeOps repository.

The goal is not to run the full Kubernetes investor demo inside GitHub Actions. The full demo depends on Docker, kind, local service startup, and interactive-style remediation artifacts. Instead, CI validates the repository structure and catches common mistakes before they reach `main`.

## What CI checks

The workflow runs on pushes, pull requests, and manual workflow dispatch.

It verifies:

1. Required project directories exist.
2. Required product/demo documentation exists.
3. Key demo scripts exist and are executable.
4. Shell scripts pass `bash -n` syntax checks.
5. Python files compile with `py_compile`.
6. Example JSON files are valid JSON.
7. The known-good Kubernetes manifest includes `REDIS_URL`.
8. The intentionally broken Kubernetes manifest omits `REDIS_URL`.
9. Sensitive local files such as `.pem`, `.key`, credentials CSVs, and `.zip` archives are not committed.

## Local usage

Run the same checks locally before committing:

```bash
cd ~/safeops-starter/safeops-starter
./scripts/ci_smoke_test.sh
```

Expected final output:

```text
== SafeOps CI smoke test complete ==
All checks passed.
```

## GitHub workflow

The workflow file is:

```text
.github/workflows/ci.yml
```

The workflow command is:

```bash
bash scripts/ci_smoke_test.sh
```

## Why this matters

SafeOps is a safety-focused DevOps automation project. Even the demo repository should prove basic engineering discipline:

- repeatable checks,
- no accidental secrets,
- valid scripts,
- valid example artifacts,
- and demo-critical Kubernetes manifests protected from accidental changes.

This CI workflow is intentionally lightweight so it can run quickly on every push.
