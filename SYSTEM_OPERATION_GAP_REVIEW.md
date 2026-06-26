# System Operation Gap Review

Generated from local inspection on 2026-06-26.

## Status Summary

- `open_gap`: 2
- `pass`: 6

## Current Checks

| ID | Area | Status | Evidence | Next action |
| --- | --- | --- | --- | --- |
| OPS001 | local_build_artifacts | pass | dist/build_report.json present | Keep running `make build` before deploy. |
| OPS002 | cv_pdf_and_html | pass | cv_html_status=pandoc_ok; cv_pdf_status=compiled_with_latexmk; fallback_visible=False | No action needed for local CV generation. |
| OPS003 | homepage_cv_positioning | pass | all required phrases present; forbidden phrases absent | No action needed locally. |
| OPS004 | latex_artifact_hygiene | pass | no root-level Vargo_CV.* artifacts | No action needed. |
| OPS005 | dv_publication_evidence | open_gap | hypothesis_status_counts={'unresolved_required_data_unavailable': 14} | Acquire/verify required case-level data and model artifacts, then regenerate the DV public release. |
| OPS006 | publication_metadata | pass | required_publication_metadata_gaps=0; selected_publication_pages=3/3; metadata_policy_exists=True; optional_missing_abstracts=63; optional_unmatched_preprints=62 | Optional abstract/preprint enrichment remains backlog, not a full-operation blocker. |
| OPS007 | deployment_state | open_gap | working_tree_changes=M Makefile \|  M src/build.py \|  M src/static/site.css \|  M src/templates/index.html \|  M src/validate_build.py \| ?? PUBLICATION_METADATA_POLICY.md \| ?? SYSTEM_OPERATION_GAP_REVIEW.md \| ?? dv_publication/root_cv_screenshot_manifest.csv \| ?? dv_publication/root_cv_visual_qa_report.json \| ?? dv_publication/screenshots/cv-desktop.png \| ?? dv_publication/screenshots/cv-mobile.png \| ?? dv_publication/screenshots/home-desktop.png \| ?? dv_publication/screenshots/home-mobile.png \| ?? src/site_visual_qa.py \| ?? src/system_operation_audit.py \| ?? tests/dv/test_site_shell.py \| ?? tests/dv/test_system_operation_audit.py | Commit, push, and let the GitHub Pages workflow deploy. |
| OPS008 | visual_accessibility_performance_qa | pass | root_cv_visual_status=pass; artifacts=dv_publication/root_cv_visual_qa_report.json; dv_publication/root_cv_screenshot_manifest.csv; dv_publication/screenshot_manifest.csv; DV_ACCESSIBILITY_REPORT.md; DV_PERFORMANCE_REPORT.md | Local root/CV screenshot and smoke accessibility checks are current. |

## Recommended Verification Command

```bash
make cv && make build && make validate && make dv-test && make site-visual-qa && make operation-audit
```
