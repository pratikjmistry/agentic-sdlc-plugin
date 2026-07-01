# Template: database-guidelines.md

## Required Sections

- **Database technology choice** — name, version, rationale; include cache layer and search index if applicable
- **Naming conventions** — tables: snake_case plural; columns: snake_case; indexes: `idx_<table>_<cols>`; foreign keys: `fk_<table>_<referenced_table>`
- **ID strategy** — UUID v4 / UUID v7 (time-ordered) / auto-increment — must be consistent across all entities; rationale for the choice
- **Migration tooling and versioning** — tool name, file naming convention (`<timestamp>_<description>.<ext>`), how to run, how to roll back
- **Auditing approach** — `created_at` / `updated_at` requirements; soft-delete pattern (`deleted_at TIMESTAMPTZ NULL`) or hard-delete; audit table spec if required
- **Indexing philosophy** — when to add an index, composite index rules, guidance on avoiding over-indexing
- **ORM / query layer** — tool, version, when raw SQL is permitted and how it must be reviewed
- **Multi-tenancy model** — row-level (`tenant_id` on every table) / schema-per-tenant / database-per-tenant / not applicable
- **Soft-delete vs. hard-delete** — project-wide default; document entity-level exceptions
- **Sensitive data handling** — which entities hold PII/PHI/PCI; encryption at rest policy; masking in logs and debug output

## Example Structure

```markdown
# Database Guidelines — [Project Name]

## Technology
- Primary DB: [e.g., PostgreSQL 16]
- Cache: [e.g., Redis 7]
- ORM: [e.g., Prisma 5]

## Naming Conventions
- Tables: snake_case, plural (e.g., `user_profiles`)
- Columns: snake_case (e.g., `created_at`, `tenant_id`)
- Indexes: `idx_<table>_<col(s)>` (e.g., `idx_orders_tenant_id_created_at`)
- Foreign keys: `fk_<table>_<referenced_table>` (e.g., `fk_orders_users`)

## ID Strategy
UUID v7 (time-ordered) for all primary keys. Never auto-increment for public-facing IDs.

## Migration Tooling
Tool: [name]. File naming: `<timestamp>_<description>.sql`. All migrations must include a rollback.

## Auditing
Every table: `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
Soft-delete: `deleted_at TIMESTAMPTZ NULL` (NULL = active). Hard-delete only with explicit justification per entity.

## Multi-tenancy
Model: Row-level isolation. Every tenant-scoped table must have `tenant_id UUID NOT NULL`.

## Sensitive Data
PII entities: [list]. Encrypted at rest using [approach]. Never logged or included in debug output.
```
