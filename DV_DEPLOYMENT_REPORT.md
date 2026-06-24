# DV Deployment Report

## Preflight

GitHub authentication and Pages settings were checked before implementation. The target repository is `chrisjvargo/chrisjvargo.github.io`, with GitHub Actions Pages deployment and custom domain `chrisjvargo.com`.

## Local Build

`make dv-release` passes. It runs tests, builds the root site and `/dv/`, validates the generated site, and hashes publication-audit artifacts.

## Deployment Status

Deployed through GitHub Pages after PR #1 was squash-merged to `main`.

The release is a status publication because the asserted final hypothesis-confirmation results were not reproducible from available artifacts.

GitHub Actions PR result: build passed; deploy skipped as intended for pull requests.

Main deployment run: https://github.com/chrisjvargo/chrisjvargo.github.io/actions/runs/28110209723

Deployment result: build passed and deploy passed.

Live path check on 2026-06-24: `https://chrisjvargo.com/dv/` returned HTTP 200 and displayed the unresolved-verification status page. Verification artifact: `dv_publication/live_url_verification.json`.

Rollback is a normal revert of the merge commit.
