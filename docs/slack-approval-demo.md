# SafeOps Milestone 13: Slack Approval Simulation

Milestone 13 adds a Slack-style approval workflow to the SafeOps demo.

The goal is to show how SafeOps/AURA fits into the collaboration flow used by real DevOps teams. Instead of approving only in the terminal, the demo now generates a Slack-style incident card with approval buttons and then simulates a user clicking **Approve Fix**.

## What this milestone proves

The demo now shows this workflow:

1. Kubernetes deployment breaks.
2. SafeOps detects the failing checkout-api deployment.
3. CI/CD context correlates the failure with a manifest change.
4. SafeOps prepares a Slack-style approval card.
5. A human approves the fix from the simulated Slack flow.
6. SafeOps sends the approved action through policy validation.
7. The scoped executor restores `REDIS_URL`.
8. SafeOps verifies recovery.
9. Audit log and memory are updated.
10. SafeOps suggests a prevention PR.

## Run the Slack-aware demo

```bash
cd ~/safeops-starter/safeops-starter

./scripts/demo_stop_services.sh
DOCKER_BUILDKIT=0 ./scripts/demo_run_full_with_slack.sh
```

When prompted, type:

```text
approve
```

or:

```text
yes
```

## Generated files

During the demo, SafeOps writes Slack simulation artifacts to `/tmp/safeops-demo`:

```text
/tmp/safeops-demo/latest_slack_approval_card.txt
/tmp/safeops-demo/latest_slack_approval_card.json
/tmp/safeops-demo/latest_slack_approval_decision.json
```

Inspect them with:

```bash
cat /tmp/safeops-demo/latest_slack_approval_card.txt
cat /tmp/safeops-demo/latest_slack_approval_card.json | python3 -m json.tool
cat /tmp/safeops-demo/latest_slack_approval_decision.json | python3 -m json.tool
```

## Why this matters

The Slack workflow makes the product feel closer to how a real team would use AURA/SafeOps:

- engineers receive incident context where they already work;
- approval is explicit and recorded;
- AI cannot act without policy and approval;
- the execution path stays scoped and auditable;
- prevention can be offered immediately after recovery.

## What this is not yet

This milestone does not call the real Slack API yet. It is a local simulation that produces the exact approval payloads and decision artifacts needed for a later Slack app integration.

Future production Slack integration should add:

- Slack app OAuth installation;
- signed request verification;
- interactive buttons;
- approval identity mapping;
- RBAC for who can approve actions;
- Slack thread updates after execution and verification.
