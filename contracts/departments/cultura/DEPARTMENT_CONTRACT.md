# Cultura and Research department contract

Owner: Cultura / Research.
Consumer: the MAK Hub on port 8900, offline research parsers and optional
source providers.

Use this area for artistic ideas, curation, source extraction, Fondart
opportunities, triangulation and proposal drafts. Start with fixtures or
public manifests. Preserve source URL, timestamp and hash.

Search in both Spanish and English ASCII. Research supports Cultura; it does
not replace the artistic decision. Provider APIs are optional boundaries, not
the local source of truth. Never include provider credentials in reports.

Validation order: parser/import test, offline fixture, then explicitly bounded
live fetch. A proposal draft is not a submitted application.

Rollback: keep the source manifest and generated report; revert only the
derived output, never the source corpus or historical WIN evidence.
