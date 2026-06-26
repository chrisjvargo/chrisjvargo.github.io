# Publication Metadata Policy

The publication system treats citation metadata as required and narrative enrichment as optional.

Required for full operation:

- Publication detail page exists for each parsed CV publication.
- `citation_title`, `citation_author`, and `citation_publication_date` metadata are present.
- Canonical URLs resolve to the generated page.
- Local PDF links, when present, have a matching `citation_pdf_url` and copied PDF file.
- Homepage-selected publication links resolve to generated detail pages.

Optional enrichment:

- Narrative abstracts.
- Author preprints where no verified public manuscript is available.
- Code, data, and materials links.

Missing optional enrichment is reported as backlog, not as a site-operation failure. A publication may show
`Abstract not currently available on this page` when no abstract has been verified or intentionally supplied.
The build validator fails only when required citation metadata or declared local assets are missing.
