# Deon Fin assisted tag and meta classification design

Date: 2026-06-22
Project: `/opt/projetos/financas-agent`
Repository: `deon7769/deon-fin`
Runtime host: `minha-vps`

## Context

The app already has the first layer of financial organization in production:

- `budget_buckets` are the six budget pots used by transactions through
  `transactions.bucket_id`.
- `savings_goals` are separate savings objectives and must not be mixed with
  transaction classification.
- `tags` are currently simple labels with `id`, `name`, `color`, and
  `created_at`.
- Each transaction can have one `tag_id`, but there is no `tag_source`, no
  `tag_rules`, and no relationship between a tag and its parent budget bucket.
- Manual bucket edits are protected by `bucket_source='manual'`. Tag edits do
  not have an equivalent source marker yet.

The user clarified the target domain model: inside Meta, the system should have
basic categories, and those categories should have subdivisions represented by
Tags. These Tags should carry the business intelligence that the legacy
category layer had: identifying the merchant type and purchase type, allowing
manual correction, and preserving that manual correction after future syncs.

For this sprint, "Meta" means the six budget pots in `budget_buckets`. Savings
goals remain a separate domain.

## Problem

The current model keeps Meta and Tag as parallel dimensions. This blocks the
next maintenance and dashboard improvements because the app cannot answer
questions such as:

- Which Tags belong under Alimentacao, Saude, Lazer, or another budget pot?
- Which transactions have a manual Tag that must survive sync and
  reclassification?
- Which Tag should be suggested for similar merchants?
- Which maintenance rows need review because they have no translated category,
  no Meta, or no Tag?
- How can category summaries evolve without relying on raw English Pluggy terms
  or literal legacy labels?

The result is a UI that can show tags, categories, and buckets, but does not yet
have a trustworthy classification workflow.

## Considered approaches

### Approach A: tags as budget-bucket subdivisions first (recommended)

Add the missing domain foundation: link each Tag to a parent budget bucket,
track `transactions.tag_source`, learn/apply Tag rules for similar merchants,
and expose the parent Meta and source in the UI/API. Then extend Manutencao
with classification health indicators and review actions.

Trade-off: this is not the full maintenance cockpit yet. It is the safest first
slice because it gives future dashboards and maintenance screens a stable
classification model.

### Approach B: build the Manutencao cockpit first

Keep the current data model and add a richer Manutencao UI for untranslated
categories, untagged transactions, and manual review queues.

Trade-off: this would improve visibility quickly, but it would still sit on a
flat Tag model. The UI would need rework as soon as Tags become subdivisions of
Metas.

### Approach C: replace Pluggy categories with Tags everywhere now

Make Tags the canonical category field in all dashboards, summaries, filters,
and maintenance flows, treating Pluggy categories only as raw import metadata.

Trade-off: this is closer to the long-term product direction, but it touches
many dashboards at once and increases the risk of breaking current summaries.

## Design

Use Approach A for this sprint. The sprint creates the classification
foundation and adds enough UI to make it usable, without replacing all category
dashboards yet.

### Domain rules

- A Tag belongs to zero or one budget bucket through `tags.bucket_id`.
- Existing Tags remain valid if no bucket is assigned yet.
- New default Tags should be seeded with a sensible parent bucket when possible.
- A transaction Tag has a source:
  - `manual`: chosen or corrected by the user.
  - `rule`: applied from a learned merchant/sign rule.
  - `auto`: applied from deterministic category or merchant heuristics.
- `manual` Tags are never overwritten by sync, automatic classification, or
  "apply to similar" operations from another transaction.
- `rule` and `auto` Tags may be recalculated when rules or mappings improve.
- Bucket classification and Tag classification are related but independent:
  changing a Tag does not automatically rewrite the bucket unless a future UI
  action explicitly asks for it.

### Data model

Add one migration after the current latest migration:

- `tags.bucket_id INTEGER NULL REFERENCES budget_buckets(id)`.
- `transactions.tag_source TEXT NULL`.
- `tag_rules` table:
  - `id INTEGER PRIMARY KEY AUTOINCREMENT`
  - `match_key TEXT NOT NULL UNIQUE`
  - `tag_id INTEGER NULL REFERENCES tags(id) ON DELETE SET NULL`
  - `created_at TEXT NOT NULL`
  - `updated_at TEXT NOT NULL`

The `match_key` should reuse the existing merchant/sign logic used by bucket
rules so Pix, card purchases, and refunds can be learned consistently.

The migration should be additive and non-destructive. It must not remove
current Tags, transaction links, category labels, or manual notes.

### Backend behavior

`tags_repo` should support:

- Listing Tags with parent bucket metadata and transaction count.
- Creating and updating Tags with optional `bucket_id`.
- Validating that a provided parent bucket exists.
- Preserving existing custom Tag colors and names when default seed logic runs.

Transaction update flows should support:

- Setting a Tag marks the target transaction as `tag_source='manual'`.
- Applying a Tag to similar transactions creates or updates a `tag_rules` row.
- Similar propagation updates only transactions where `tag_source` is not
  `manual`.
- Clearing a Tag manually marks the target as `manual` so the user can say
  "this merchant should not have a Tag" until they choose otherwise.

Automatic classification should support:

- A deterministic `apply_tags_to_database(db)` routine.
- Rule-based Tag application first.
- Category/merchant heuristic Tag application second.
- Skipping every transaction with `tag_source='manual'`.
- Running after Pluggy sync, categorization, and bucket classification.

The automatic heuristic should stay conservative in this sprint. It may map
known Portuguese category labels and obvious merchant patterns to seeded Tags,
but it should not introduce LLM or probabilistic classification yet.

### API

Extend existing endpoints instead of adding a new category service:

- `GET /api/tags` returns each Tag with `bucket_id`, `bucket_key`, and
  `bucket_name`.
- `POST /api/tags` accepts optional `bucket_id`.
- `PATCH /api/tags/{id}` accepts optional `bucket_id`.
- Transaction responses include `tag_source`.
- `PATCH /api/transactions/{id}` marks Tag changes as manual.
- `POST /api/transactions/{id}/tag` accepts:
  - `tag_id`
  - `apply_to_similar`
- The Tag application response includes `similar_ids`, `rule_key`, and
  `tag_source` so the UI can refresh visible rows.

Existing filter APIs for `tag_ids` and `bucket_ids` remain valid.

### UI

Keep the first UI changes focused and compatible with the current layout:

- Tags page:
  - Show the parent Meta/pote for each Tag.
  - Allow selecting or clearing the parent Meta in the Tag modal.
  - Keep Tag color editing.
- Transacoes:
  - Show Tag source when it helps explain whether a value was manual, rule, or
    automatic.
  - Allow applying a Tag to similar transactions from the current Tag action.
  - Keep existing filters and month behavior.
- Manutencao:
  - Add classification indicators for untranslated categories, transactions
    without Tag, transactions without Meta, and manual-vs-auto coverage.
  - Use translated category labels where available instead of raw Pluggy English
    terms.

Full dashboard redesigns and separate "Meta > Tags" analytical dashboards are
intentionally deferred until the data foundation is in place.

### Sync and preservation

Pluggy sync already skips updating existing transactions when the external id
is already present. This sprint should preserve that behavior.

After sync inserts new transactions, the backend may run categorization,
bucket classification, reference-month fill, and Tag classification. The Tag
classification step must skip manual Tags and manual cleared Tags. This is the
core guarantee that a user correction survives future syncs.

### Error handling

Invalid `bucket_id` on Tag create/update should return a validation error.
Invalid `tag_id` on transaction update should continue returning a validation
error.

If a Tag is deleted:

- Existing transactions should have `tag_id=NULL`.
- Their `tag_source` should be cleared unless the implementation needs a
  manual-cleared sentinel for a later flow.
- Any `tag_rules` pointing to the deleted Tag should be removed or nullified
  consistently with the schema choice.

If automatic classification cannot find a Tag, it should leave the transaction
unchanged rather than inventing a broad "Outros" assignment.

### Testing

Use TDD for implementation. Write each failing test and verify the red state
before production code.

Required backend coverage:

- Migration adds `tags.bucket_id`, `transactions.tag_source`, and `tag_rules`.
- Existing seeded Tags remain idempotent and preserve user edits.
- Tags can be created and updated with a valid parent bucket.
- Invalid Tag parent bucket is rejected.
- Setting a transaction Tag marks it manual.
- Applying a Tag to similar transactions propagates to non-manual rows.
- Applying a Tag to similar transactions does not overwrite manual rows.
- Automatic Tag classification applies rules before heuristics.
- Automatic Tag classification does not overwrite manual Tags.
- Sync/post-sync classification preserves manual Tag edits.

Required frontend coverage:

- Tag modal can select and clear a parent Meta.
- Tags page displays parent Meta information.
- Transaction Tag action can request apply-to-similar behavior.
- UI types include `tag_source` and Tag parent bucket metadata.

Required verification before deploy:

- Full Python test suite.
- Full frontend test suite.
- Frontend lint and build.
- VPS host Python tests.
- `scripts/vps_deploy.sh`.
- Production health smoke through the deploy script.

## Out of scope

This sprint does not implement:

- Multi-tag transactions.
- Per-Tag budget targets.
- Replacing every dashboard category summary with Tag summaries.
- LLM-based classification.
- A complete Manutencao workbench with bulk review queues.
- New savings-goal behavior.
- A destructive migration of existing Pluggy category values.

## Self-review

- No placeholder requirements remain in this spec.
- The word Meta is scoped to `budget_buckets`; `savings_goals` are explicitly
  out of scope.
- The design is additive and preserves current data.
- Manual classification preservation is stated for sync, rules, automatic
  classification, and similar propagation.
- The sprint is narrow enough for one implementation plan and a production
  deploy.
