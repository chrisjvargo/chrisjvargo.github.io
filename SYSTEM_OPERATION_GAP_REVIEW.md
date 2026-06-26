# System Operation Gap Review

Generated from local inspection on 2026-06-26.

## Status Summary

- `open_gap`: 1
- `pass`: 7

## Current Checks

| ID | Area | Status | Evidence | Next action |
| --- | --- | --- | --- | --- |
| OPS001 | local_build_artifacts | pass | dist/build_report.json present | Keep running `make build` before deploy. |
| OPS002 | cv_pdf_and_html | pass | cv_html_status=pandoc_ok; cv_pdf_status=compiled_with_latexmk; fallback_visible=False | No action needed for local CV generation. |
| OPS003 | homepage_cv_positioning | pass | all required phrases present; forbidden phrases absent | No action needed locally. |
| OPS004 | latex_artifact_hygiene | pass | no root-level Vargo_CV.* artifacts | No action needed. |
| OPS005 | dv_publication_evidence | open_gap | hypothesis_status_counts={'unresolved_required_data_unavailable': 14}; gap_register_rows=14; mapped_unresolved_gaps=14/14; release_request_files=15/15; dispatch_rows=20; dispatch_ready_not_sent=20/20; submission_channels=20/20; channels_not_sent=20/20; gap_register_md_exists=True; dispatch_matrix_md_exists=True | Acquire/verify required case-level data and model artifacts using `DV_EVIDENCE_GAP_REGISTER.md`, then regenerate the DV public release. |
| OPS006 | publication_metadata | pass | required_publication_metadata_gaps=0; selected_publication_pages=3/3; metadata_policy_exists=True; optional_missing_abstracts=64; optional_unmatched_preprints=63 | Optional abstract/preprint enrichment remains backlog, not a full-operation blocker. |
| OPS007 | deployment_state | pass | branch=main; working_tree_clean | Verify live site after deployment. |
| OPS008 | visual_accessibility_performance_qa | pass | root_cv_visual_status=pass; artifacts=dv_publication/root_cv_visual_qa_report.json; dv_publication/root_cv_screenshot_manifest.csv; dv_publication/screenshot_manifest.csv; DV_ACCESSIBILITY_REPORT.md; DV_PERFORMANCE_REPORT.md | Local root/CV screenshot and smoke accessibility checks are current. |

## Recommended Verification Command

```bash
make cv && make build && make validate && make dv-test && make site-visual-qa && make operation-audit
```
