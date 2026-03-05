---
name: onboard-developer
description: Onboard a new developer to the Lakebase Todo App — adds platform permissions and database access.
trigger: User asks to onboard, add, or invite a new developer or team member.
---

# Onboard Developer

Add a new developer to the project by editing two config files. CI/CD handles the actual provisioning on push to main.

## Steps

1. **Collect info**: Ask for the developer's Databricks email. Ask for access level (`readwrite` or `readonly`, default `readwrite`).

2. **Edit `databricks.yml`** — Add a `permissions:` entry. The block is at the top level of the file:

```yaml
permissions:
  - user_name: existing@databricks.com
    level: CAN_MANAGE
  # Add new entry here, same indent:
  - user_name: NEW_EMAIL
    level: CAN_MANAGE
```

Validate the email isn't already in the `permissions:` block before adding.

3. **Edit `db/roles.yml`** — Append a user entry under `users:`:

```yaml
users:
  - email: existing@databricks.com
    access: readwrite
  # Add new entry here:
  - email: NEW_EMAIL
    access: readwrite  # or readonly
```

Validate the email isn't already in the `users:` list before adding.

4. **Summarize changes** — Show what was added to each file. Remind the developer:
   - Push to `main` for CI to deploy platform permissions (`databricks bundle deploy`) and database roles (`lbctl roles sync`).
   - After CI completes, the new developer follows the onboarding steps:
     1. `make branch-create NAME=dev-{first-last}` (derive from email prefix)
     2. `LAKEBASE_BRANCH_ID=dev-{name} uv run alembic upgrade head`
     3. Enable Data API on their dev branch endpoint via Lakebase UI

## Validation

- No duplicate emails in either file
- Email format: must contain `@`
- Access level must be `readwrite` or `readonly`
- YAML indentation: 2 spaces, list items with `- ` prefix
