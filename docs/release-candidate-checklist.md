# SafeOps Release Candidate Checklist

Use this checklist before sharing the repository with investors, early customers, or technical reviewers.

## Required checks

```bash
./scripts/ci_smoke_test.sh
./scripts/demo_run_real_safeops_loop.sh demo aleemughal001
./scripts/demo_create_investor_bundle.sh demo aleemughal001
./scripts/demo_release_candidate_check.sh
```

## Expected results

- CI completes with `All checks passed`.
- One-command real loop ends with `Result: PASSED`.
- Investor bundle command creates a bundle zip and reports `Demo result: PASSED`.
- Release-candidate report says `Release candidate ready: True`.

## Before recording a demo

- Start from `main`.
- Confirm `git status` is clean.
- Confirm GitHub Actions is green.
- Do not show credentials, tokens, `.pem` files, or local cloud keys.
- Use the investor evidence bundle zip as the artifact package.
