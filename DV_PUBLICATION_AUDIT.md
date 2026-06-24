# DV Publication Audit

## Verification Result

The assertion that all preregistered gender-disparity hypotheses were confirmed could not be verified from the available public release. `dv_publication/hypothesis_verification.csv` contains 14 hypotheses with status `unresolved_required_data_unavailable`.

## Public Result

The generated `/dv/` site is therefore a transparent status and evidence-release page. It does not claim final gender-disparity confirmation.

## Passing Checks

- `make dv-release`
- GitHub Actions PR build: passed
- Main GitHub Pages deployment: passed
- Live URL verification: `https://chrisjvargo.com/dv/` returned HTTP 200
- Unit tests: 8 passed
- Build validation: 87 publication pages plus DV release pages
- Internal link check: 2,053 links checked, 0 errors
- Structured data: 22 JSON-LD blocks parsed, 0 errors
- Privacy scan: 0 findings in `dist/dv/`
- Accessibility smoke: 22 DV pages checked, pass
- Download hash check: pass
