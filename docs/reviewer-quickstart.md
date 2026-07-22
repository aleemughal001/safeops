# Reviewer Quickstart

This is the fastest way to review SafeOps locally.

## 1. Clone

```bash
git clone https://github.com/aleemughal001/safeops.git
cd safeops
```

## 2. Run smoke checks

```bash
./scripts/ci_smoke_test.sh
```

Expected:

```text
== SafeOps CI smoke test complete ==
All checks passed.
```

## 3. Run full investor demo

```bash
DOCKER_BUILDKIT=0 ./scripts/demo_run_investor.sh
```

The demo uses automatic inputs for the Slack approval simulation and prevention PR generation.

## 4. Open generated cockpit

```bash
xdg-open /tmp/safeops-demo/investor-demo-package/incident-cockpit.html
```

Alternative:

```bash
python3 -m http.server 8088 --directory /tmp/safeops-demo/investor-demo-package
```

Open:

```text
http://127.0.0.1:8088/incident-cockpit.html
```

## 5. Read generated summary

```bash
cat /tmp/safeops-demo/investor-demo-package/investor-summary.md
```

## 6. Stop services

```bash
./scripts/demo_stop_services.sh
```

## Expected proof points

A successful demo should show:

- CI/CD correlation: high-correlation;
- Slack approval: approved;
- execution: executed;
- verification: healthy;
- audit: valid;
- prevention PR package: generated;
- cockpit: generated.
