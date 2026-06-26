# DV Evidence Gap Register

Generated from `data/dv_public_release/public_tables/hypothesis_data_resolution.csv`.

## Summary

- Hypotheses tracked: 14
- Unresolved for required data/model artifacts: 14
- Unresolved hypotheses with mapped request files: 14/14

## Support Status Counts

- `unresolved_required_data_unavailable`: 14

## Analysis Readiness Counts

- `aggregate_context_only`: 1
- `no`: 10
- `partial_descriptive_only`: 1
- `partial_process_context_only`: 1
- `policy_context_only`: 1

## Hypothesis-Level Gaps

| Hypothesis | Readiness | Minimum unit | Required denominator | Missing fields | Request targets | Current answer |
| --- | --- | --- | --- | --- | --- | --- |
| H0 | no | event-party | all qualifying domestic-related event-parties, including no-arrest and no-report-only events | party sex/gender, suspect/victim/caller roles, pre-decision evidence, relationship, injury, weapons, scene presence, probable-cause facts, outcome by party | Boulder PD, BCSO, Longmont, Lafayette, Louisville, Erie, CUPD, Boulder County Communications | unresolved for confirmatory inference |
| H1 | partial_descriptive_only | linked person-stage records | stage-specific linked counts from call/event-party through court disposition | stable person/case join keys, arrest/referral/filing/count/disposition/sentence by recorded sex | all law-enforcement agencies, Twentieth Judicial District Attorney, Colorado Judicial Branch, municipal courts | public data support only descriptive male-majority context, not funnel-transition testing |
| H2 | no | event-party | all qualifying event-parties with pre-decision facts | party sex/gender, probable cause, injury, conduct, self-defense, opposing complaints, prior calls, protection orders, witnesses, officer decision | law-enforcement CAD/RMS custodians | unresolved for confirmatory inference |
| H3 | no | party nested within incident | incidents with opposing complaints or independently codable bidirectional conduct | opposing complaints, party-specific allegations/evidence, statutory predominant-aggressor factors, arrest outcome by party | law-enforcement CAD/RMS plus narratives/evidence sample | unresolved for confirmatory inference |
| H4 | partial_process_context_only | investigative action item within event | all relevant and feasible investigative-action opportunities in sampled records | separate interviews, photos, 911/bodycam review, protection-order checks, self-defense review, witnesses, feasibility, recorded sex/gender | law-enforcement agencies; 46-case audit crosswalk custodians | unresolved for sex-specific confirmatory inference |
| H5 | no | event-party | independently coded civil-only event-parties | narratives/evidence, legal-panel civil-only classification, sex/gender, criminal/DV classification, arrest/referral | law-enforcement agencies and legal-review sample records | unresolved for confirmatory inference |
| H6 | no | event-party | independently coded probable-cause event-parties | narratives/evidence, legal-panel probable-cause classification, sex/gender, report-only/civil/no-enforcement outcomes | law-enforcement agencies and legal-review sample records | unresolved for confirmatory inference |
| H7 | no | case-defendant and charge count | all referred/filed/resolved DV-related counts with sex/gender and stage outcomes | Action extract, count-level original/amended/final charges, no-file/dismissal reasons, pleas, convictions, sentences, treatment | Twentieth Judicial District Attorney, Colorado Judicial Branch, municipal courts | unresolved for confirmatory inference |
| H8 | no | event-party with agency identifier | agency-specific comparable event-party cohorts | agency-specific CAD/RMS schemas, sex/gender, pre-decision facts, outcomes | all Boulder County law-enforcement agencies | unresolved for confirmatory inference |
| H9 | aggregate_context_only | event-party by agency | matched Colorado agency incident-level cohorts with comparable fields | comparison-agency case-level fields and data-completeness metrics | CBI and empirically selected comparison agencies after matching frame is finalized | unresolved for confirmatory inference |
| H10 | no | call/event-party | calls/events with caller role/sex, reporting role/sex, scene presence, and outcomes | caller role, caller sex/gender, reporting party, party presence, nonresponse/no-report outcomes | Boulder County Communications and agency CAD/RMS custodians | unresolved for confirmatory inference |
| H11 | policy_context_only | event or investigative item over time | pre/post cohorts around verified implementation dates with stable measurement | policy versions, implementation dates, training records, pre/post case-level completeness outcomes | Boulder PD and other agency policy/training custodians | unresolved for confirmatory inference |
| H12 | no | event-party/case/count with actor identifiers | case-level cohorts with pseudonymous actor IDs and outcomes | pseudonymous officer, supervisor, prosecutor, judge IDs; linked outcomes; disclosure controls | law-enforcement agencies, DA, Judicial Branch | unresolved for confirmatory inference |
| H13 | no | event-party/case/count | legally and ethically releasable group fields with adequate cell sizes | group fields in DV event-party records, reliability metadata, small-cell disclosure review | law-enforcement agencies, DA, Judicial Branch, municipal courts | unresolved for confirmatory inference |

## Interpretation

This register is an acquisition and verification control sheet. It does not convert public aggregate context into confirmatory findings.
A hypothesis remains unresolved until the required denominator, unit-level records, and model artifacts are present and regenerated through the release pipeline.
