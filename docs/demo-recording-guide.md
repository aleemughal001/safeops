# Demo Recording Guide

## Goal

Record a short 2-minute demo showing the SafeOps trust workflow.

## Before recording

Stop services:

```bash
./scripts/demo_stop_services.sh
```

Reset to healthy:

```bash
./scripts/demo_reset_healthy.sh
```

Check Git is clean:

```bash
git status
```

## Recommended screen layout

Use one terminal window with large font.

Suggested zoom/font size:

- Ubuntu Terminal: 14–16 pt
- Hide unnecessary desktop icons
- Keep the terminal width large enough for the final report

## Recording flow

1. Show repo and explain SafeOps in one sentence.
2. Run:

```bash
./scripts/demo_run_full.sh
```

3. Pause at human approval prompt.
4. Explain the safety controls.
5. Type `yes`.
6. Show final incident report.
7. End on audit `PASS` and verification `healthy`.

## Important message

SafeOps does not blindly let AI change infrastructure. It requires evidence, human approval, policy validation, scoped execution, verification, and audit logging.
