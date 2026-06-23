# Category Translation Tags Design

Date: 2026-06-23
Project: `deon-fin`

## Context

The app has three classification layers:

- `transactions.category` is the raw category received from Pluggy or another importer.
- `transactions.category_label` is the translated display label from the maintenance `categorias_pt` de/para.
- `transactions.tag_id` is the editable subfilter used by the new UI.

The user validated the next direction: translated categories can become Tags. This preserves the useful category summaries while making the same concepts editable, filterable, and able to grow over time.

## Decision

Use the maintenance category translation map as the first automatic source for granular Tags.

Examples:

- `food delivery` -> translated label `Delivery` -> Tag `Delivery`.
- `taxi and ride-hailing` -> translated label `Táxi/App` -> Tag `Táxi/App`.
- `digital services` -> translated label `Serviços digitais` -> Tag `Serviços digitais`.

The raw Pluggy category is not overwritten. It remains available for audit, fixes, and future reclassification.

## Behavior

Automatic Tag classification now follows this order:

1. Apply learned `tag_rules` by merchant/sign match.
2. If there is no rule, use `categorias_pt` to resolve the raw category into a translated Tag name.
3. If the raw category also exists in `CATEGORY_BUCKET_MAP`, attach the created Tag to the matching parent Meta (`budget_buckets`).
4. If the category is explicitly blocked as transfer, card payment, income, or financial movement, leave it untagged.
5. If the category is not translated, fall back to conservative merchant heuristics.

Manual Tags remain protected: rows with `tag_source='manual'` are skipped by automatic classification.

## Scope

Implemented in this slice:

- Automatic creation/reuse of translated category Tags.
- Parent Meta assignment for known category-to-bucket mappings.
- Statistics reporting `created_tags`.
- Tests covering granular translated Tags and manual preservation.

Deferred:

- Bulk maintenance actions for assigning missing translations.
- Full classification health cockpit with untagged/no-Meta queues.
- Replacing every category summary with Tag summaries.
- Multi-tag transactions.

## Verification Contract

Required checks for this slice:

- `tests/test_agent_tags.py` proves translated category Tags are created and linked to parent Meta.
- Tag rules still override category heuristics.
- Manual Tag assignments are not overwritten.
- Credit card payments remain untagged.

