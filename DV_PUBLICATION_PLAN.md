# DV Publication Plan

## Status

This branch implements a disclosure-safe status publication at `/dv/`. It does not publish final gender-disparity findings because the available public release cannot verify the asserted completed model results.

## Publication Gate

1. Load the sanitized release from `data/dv_public_release/`.
2. Validate release structure, claim language, and privacy constraints.
3. Render static DV routes into `dist/dv/`.
4. Copy only public release downloads into `dist/dv/downloads/`.
5. Build root site navigation, sitemap, `llms.txt`, and DV feed.
6. Run `make dv-audit`.

## Reproduction Command

```bash
make dv-release
```

## Deployment Decision

Do not merge or deploy as final findings until the research repository supplies verifiable final model artifacts, data hashes, and hypothesis-support rules.
