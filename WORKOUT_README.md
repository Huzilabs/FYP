````markdown
WORKOUT API — README

Overview

- The app provides workout templates (global) and per-user workout values.
- Two canonical templates should be seeded: "Morning Walk" and "Evening Run".

Simplified fields

Tables (summary)

Key behavior

- If a user has no `user_workouts` row for a template, the template defaults are shown.
- PATCH to a template creates or updates the `user_workouts` row. For predefined/global templates (owner_id IS NULL) updates are recorded in `workout_history_templates`. For user-created workouts, updates are saved but do not generate history snapshots.
- Only templates with `editable_by_user = true` are allowed to be updated by users when applicable.

```markdown
WORKOUT API — README

Overview

- The app provides workout templates (global) and per-user workout values.
- Two canonical templates should be seeded: "Morning Walk" and "Evening Run".

Fields

- `name`: the workout name (e.g., "push", "squat", "run").
- `step_count`: integer — how many repetitions/occurrences the user did (formerly "count").
- `duration_minutes`: integer — how long the workout took (minutes).

Tables (summary)

- `workout_templates` (id, name, default_step_count, default_duration_minutes, editable_by_user, metadata, owner_id)
- `user_workouts` (id, user_id, template_id, step_count, duration_minutes, updated_at, ...)
- `workout_history` (id, user_workout_id, user_id, template_id, step_count_before, step_count_after, duration_before, duration_after, changed_at, changed_by, note)

Key behavior

- The API returns a merged view: COALESCE(user_workouts.step_count, workout_templates.default_step_count).
- If a user has no `user_workouts` row for a template, the template defaults are shown.
- PATCH to a template creates or updates the `user_workouts` row. For predefined/global templates (templates with `owner_id IS NULL`) updates are recorded in `public.workout_history` (DB trigger). For user-created templates, updates are saved but do not generate history snapshots.
- Users may update their own per-user values (`step_count`, `duration_minutes`) for any template (actor must match `user_id`). Users cannot rename or delete predefined/global templates.
- Users may create, update, and delete private templates they own (`owner_id = user_id`).

Authentication / Ownership

- The server expects `X-User-Id` header for owner-only actions in local/dev. In production use proper auth (JWT).
- PATCH endpoints check `actor_user_id == user_id` and reject if not the same.

Endpoints (examples)

- List templates
  - GET /api/workouts/templates
  - Response: { templates: [{ id, name, default_count, default_duration_minutes, editable_by_user, owner_id }, ...] }

- List user's merged workouts
  - GET /api/users/{user_id}/workouts
  - Response: { workouts: [{ template_id, name, user_workout_id|null, count, duration_minutes, editable_by_user, updated_at }], total_steps }

- Get single merged workout
  - GET /api/users/{user_id}/workouts/{template_id}
  - Response: { workout: { template_id, name, user_workout_id|null, count, duration_minutes, editable_by_user, updated_at } }

- Update (create or change) user's workout values
  - PATCH /api/users/{user_id}/workouts/{template_id}
  - Headers: X-User-Id: {user_id}
  - Body (JSON): { "count": 1500, "duration_minutes": 30 }
  - Behavior: If the user row exists, the `user_workouts` row is updated. If no user row exists, a new `user_workouts` row is inserted. History snapshots are only recorded for updates to predefined/global templates.
  - Response: { ok: true, user_workout_id, count, duration_minutes, updated_at }

- Create a private template
  - POST /api/users/{user_id}/workout_templates
  - Headers: X-User-Id: {user_id}
  - Body: { "name": "My Workout", "default_count": 10, "default_duration_minutes": 5 }

- Update/delete a private template
  - PATCH /api/workout_templates/{template_id} (owner only)
  - DELETE /api/workout_templates/{template_id} (owner only)

- Get history for a user's template (only for predefined templates)
  - GET /api/users/{user_id}/workouts/{template_id}/history
  - Headers: X-User-Id: {user_id}
  - Response: { history: [{ id, count_before, count_after, duration_before, duration_after, changed_at, changed_by, note }, ...] }

Database notes and migration

- Ensure `workout_templates` exists before creating `user_workouts` (FK target).
  -- The migration `migrations/20260117_add_owner_to_workout_templates.sql` adds `owner_id`, `default_count`, and a trigger that writes to `public.workout_history` only for predefined templates.

Retention & maintenance

- `workout_history` is append-only; consider retention/partitioning if it grows large.
  -- `total_steps` is computed at read time as the sum of merged `count` values.

Contact / Next steps

- To wire frontend: call GET /api/workouts/templates then GET /api/users/{user}/workouts to render merged values. Use PATCH to update. History is available only for predefined templates via the /history endpoint.
- If you want, I can commit and push the migration and README updates to `feature/faceauth`.
```
````

Endpoints (examples)
