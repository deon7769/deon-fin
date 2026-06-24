# Classification Production Audit - 2026-06-24

## Context

Read-only audit for the operational QA sprint. The VPS database at
`/opt/projetos/financas-agent/data/financas.db` was inspected in read-only mode.
No production data was changed.

## Production Snapshot

- Transactions: 1,776
- Distinct raw categories: 51
- Missing category translations: 0
- Missing Tag: 406
- Missing Meta/bucket: 631

## Source Breakdown

### Tags

| Source | Count |
| --- | ---: |
| auto | 1,355 |
| none | 405 |
| manual | 13 |
| rule | 2 |
| manual-cleared | 1 |

### Meta/Bucket

| Source | Count |
| --- | ---: |
| auto | 1,028 |
| none | 631 |
| rule | 95 |
| manual | 22 |

## Top Missing Tag Categories

| Category | Count |
| --- | ---: |
| Same person transfer | 146 |
| Transfer - PIX | 115 |
| Transfers | 79 |
| Credit card payment | 34 |
| Uncategorised/empty | 32 |

## Top Missing Meta Categories

| Category | Count |
| --- | ---: |
| Same person transfer | 135 |
| Proceeds interests and dividends | 130 |
| Transfer - PIX | 116 |
| Transfers | 40 |
| Uncategorised/empty | 38 |

## Findings

- Category translation is not the current production bottleneck. The current data already has translations for all seen raw categories.
- The maintenance UI still exposes several raw/legacy fields too directly:
  - Category translation editor still uses generic source/translation rows.
  - Missing translation table shows raw category labels.
  - Learned rules and audit show raw `match_key` as the primary label.
- Manual classifications are already modeled with `tag_source='manual'` and `bucket_source='manual'`.
- Automatic reprocessing already skips manual Tag/Meta rows.
- Similar propagation exists on transaction classification methods and returns affected IDs/counts, but it is not surfaced clearly in the maintenance workflow.
- `classification_audit_log` is empty on the VPS despite existing bucket rules and rule-sourced transactions, so the current audit table cannot be treated as complete history.

## Worker A Recommendations

- Prioritize structured suggestions for missing Tag and Meta rather than category translations.
- Treat transfers, card payments, investments, and financial movements as policy-sensitive rows so the UI does not present all missing Tag/Meta rows as ordinary manual work.
- Keep raw Pluggy literals as secondary technical context; show Portuguese labels, Tag, and Meta names as the primary UI.
- When applying a classification to similar transactions, display the affected count and refresh maintenance/audit/transactions without a full reload.
- Add tests before implementation for:
  - suggestion grouping by raw category plus translated label;
  - similar propagation response and manual-row preservation;
  - frontend rendering of structured Tag/Meta controls and affected-count feedback.
