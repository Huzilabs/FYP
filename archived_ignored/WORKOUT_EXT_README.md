````markdown
User-Created Workouts — Design & API

Goal

- Allow users to create and manage private templates for themselves (name, count, duration_minutes).
- Keep global templates (shared) separate; templates with `owner_id IS NULL` are predefined/global.
- Save per-user workout values (`count`, `duration_minutes`) for lookups; do not keep history for user-created workouts.
- Only record history snapshots for updates to predefined/global templates.

DB design (summary)

- `workout_templates` (global + private templates)
  - Fields: `id`, `name`, `default_count`, `default_duration_minutes`, `metadata`, `created_at`, `updated_at`, `editable_by_user`, `owner_id` (NULL for global templates).
  - Semantics: `owner_id=NULL` means global template; `owner_id=<user_id>` means private template owned by that user.
- `user_workouts` (per-user current values)
  - Fields: `id`, `user_id`, `template_id`, `count`, `duration_minutes`, `updated_at`.
  - These rows store the user's last-performed values for the template.
- `workout_history_templates` (new)
  - Purpose: store snapshots of updates only for predefined/global templates.
  - Fields: `id`, `user_id`, `user_workout_id`, `template_id`, `before_count`, `after_count`, `before_duration_minutes`, `after_duration_minutes`, `changed_at`.

Behavior notes

- When a user creates a private template, a row is inserted into `workout_templates` with `owner_id = user_id` and `editable_by_user = true`.
- When a user performs or updates a workout (PATCH to `/api/users/{user_id}/workouts/{template_id}`), the `user_workouts` row is created/updated. No history is recorded for user-created templates.
- When a user updates a predefined/global template (owner_id IS NULL), the change is recorded in `workout_history_templates` for auditing and analysis.

API Endpoints

- GET /api/workouts/templates
  - Returns all global templates + user's private templates when `X-User-Id` provided.

- POST /api/users/{user_id}/workout_templates
  - Create a new private template for the user.
  - Body: { "name": "My Workout", "default_count": 10, "default_duration_minutes": 5 }
  - Response: 201 { id, name, default_count, default_duration_minutes, owner_id }

- PATCH /api/workout_templates/{template_id}
  - Update template name/default values. Only owner may update if owner_id is not NULL; admins may update global templates.

- DELETE /api/workout_templates/{template_id}
  - Delete a private template (owner-only). For global templates, restrict to admin or deny.

```markdown
User-Created Workouts — Design & API

Goal

Allow users to create and manage private templates for themselves (name, default_count, default_duration_minutes).

- Fields: `id`, `name`, `default_count`, `default_duration_minutes`, `metadata`, `created_at`, `updated_at`, `editable_by_user`, `owner_id` (NULL for global templates).
- Body: { "name": "My Workout", "default_count": 10, "default_duration_minutes": 5 }
- Response: 201 { id, name, default_count, default_duration_minutes, owner_id }
- Adds `default_count` / `default_duration_minutes` to templates.
  Body: partial { "name": "New Name", "default_count": 1200 }

- `workout_templates` (global + private templates)
  - Fields: `id`, `name`, `default_step_count`, `default_duration_minutes`, `metadata`, `created_at`, `updated_at`, `editable_by_user`, `owner_id` (NULL for global templates).
  - Semantics: `owner_id=NULL` means global template; `owner_id=<user_id>` means private template owned by that user.
- `user_workouts` (per-user current values)
  - Fields: `id`, `user_id`, `template_id`, `step_count`, `duration_minutes`, `updated_at`.
  - These rows store the user's last-performed values for the template.
- `workout_history` (existing)
  - Purpose: store snapshots of updates only for predefined/global templates.
  - Fields: `id`, `user_workout_id`, `user_id`, `template_id`, `step_count_before`, `step_count_after`, `duration_before`, `duration_after`, `changed_at`, `changed_by`, `note`.

Behavior notes

- When a user creates a private template, a row is inserted into `workout_templates` with `owner_id = user_id` and `editable_by_user = true`.
- When a user performs or updates a workout (PATCH to `/api/users/{user_id}/workouts/{template_id}`), the `user_workouts` row is created/updated. No history is recorded for user-created templates.
- When a user updates a predefined/global template (owner_id IS NULL), the change is recorded in `workout_history` for auditing and analysis (triggered by DB trigger).

API Endpoints

- GET /api/workouts/templates
  - Returns all global templates + user's private templates when `X-User-Id` provided.

- POST /api/users/{user_id}/workout_templates
  - Create a new private template for the user.
  - Body: { "name": "My Workout", "default_step_count": 10, "default_duration_minutes": 5 }
  - Response: 201 { id, name, default_step_count, default_duration_minutes, owner_id }

- PATCH /api/workout_templates/{template_id}
  - Update template name/default values. Only owner may update if owner_id is not NULL.

- DELETE /api/workout_templates/{template_id}
  - Delete a private template (owner-only). For global templates, restrict to admin or deny.

- PATCH /api/users/{user_id}/workouts/{template_id}
  - Create/update per-user workout values. Body: { "step_count": N, "duration_minutes": M }
  - Behavior: For predefined templates, a history row is created in `workout_history` by the DB trigger.

CORS Fix

- Ensure the server sets `Access-Control-Allow-Methods` to include `PATCH` and answers `OPTIONS` preflight requests.

Supabase / SQL migration

- See `migrations/20260117_add_owner_to_workout_templates.sql`. It:
  - Adds `owner_id` to `workout_templates`.
  - Adds `default_step_count` / `default_duration_minutes` to templates.
  - Adds `step_count` and `duration_minutes` columns to `user_workouts` if missing.
  - Creates a trigger that records history into `public.workout_history` only for predefined templates.

Notes & recommendations

- Keep `user_workouts` referencing `workout_templates` as is. When a user creates a private template, they become owner and can manage it.
- For history retention, only the `workout_history` table needs retention/partitioning considerations.
- If you prefer soft-delete for templates, implement `deleted_at` rather than hard DELETE.

Review

- Review these docs; once approved I will commit and push the migration and README updates to the repo/branch you prefer.
```
````

- Body: partial { "name": "New Name", "default_step_count": 1200 }
