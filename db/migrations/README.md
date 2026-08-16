# Database migrations

**There is no migration runner in this project.** Nothing applies these files
automatically — not the app, not CI, not the container start-up. They are a
hand-maintained history of the schema changes made since the initial schema.

## The canonical schema is `db/schema.sql`

`db/schema.sql` is the source of truth and always describes the *current*
intended shape of the database. A fresh environment is created from it:

```bash
psql "$DATABASE_URL" -f db/schema.sql
psql "$DATABASE_URL" -f db/seed.sql     # reference/lookup data
```

The files in this directory exist so the *reasons* for each change stay
readable. They are not needed to stand up a new database.

## If you add a new migration

1. Create `NNN_short_description.sql` using the **next free number** — files are
   numbered sequentially and numbers must be unique. Look at the highest number
   present and add one.
2. Make the statement idempotent where you reasonably can (`IF NOT EXISTS`,
   `IF EXISTS`), so a re-run against a partially-migrated database is safe.
3. **Apply it to production by hand.** Deploying the code does not change the
   database:
   ```bash
   psql "$DATABASE_URL" -f db/migrations/NNN_short_description.sql
   ```
4. **Update `db/schema.sql` in the same commit** so the canonical schema keeps
   matching reality. This is the step most easily forgotten, and skipping it is
   what makes the two drift apart.

## Known drift

Because the two sides are maintained by hand, production can differ from
`schema.sql` — a migration applied but not folded back in, or folded in but not
applied. When something behaves unexpectedly around the schema, compare the live
database against `schema.sql` before assuming the code is wrong.
