WORKOUT API — README

Overview
- The app provides workout templates (global) and per-user workout values.
- Two canonical templates should be seeded: "Morning Walk" and "Evening Run".
- Users can update only allowed templates' `step_count` and `duration_minutes`.
- Every update appends an entry to `workout_history` so previous values are preserved.

Tables (summary)
- workout_templates(id, name, default_step_count, default_duration_minutes, editable_by_user, metadata, ...)
- user_workouts(id, user_id, template_id, step_count, duration_minutes, updated_at, ...)
- workout_history(id, user_workout_id, user_id, template_id, step_count_before, step_count_after, duration_before, duration_after, changed_at, changed_by, note)

Key behavior
- The API returns a merged view: COALESCE(user_workouts.step_count, workout_templates.default_step_count).
- If a user has no `user_workouts` row for a template, the template defaults are shown.
- PATCH to a template creates or updates the `user_workouts` row and writes a `workout_history` record.
- Only templates with `editable_by_user = true` are allowed to be updated by users.

Authentication / Ownership
- The server expects `X-User-Id` header for owner-only actions in local/dev. In production use proper auth (JWT).
- PATCH endpoints check `actor_user_id == user_id` and reject if not the same.

Endpoints (examples)
- List templates
  - GET /api/workouts/templates
  - Response: { templates: [{ id, name, default_step_count, default_duration_minutes, editable_by_user }, ...] }

- List user's merged workouts
  - GET /api/users/{user_id}/workouts
  - Response: { workouts: [{ template_id, name, user_workout_id|null, step_count, duration_minutes, editable_by_user, updated_at }], total_steps }

- Get single merged workout
  - GET /api/users/{user_id}/workouts/{template_id}
  - Response: { workout: { template_id, name, user_workout_id|null, step_count, duration_minutes, editable_by_user, updated_at } }

- Update (create or change) user's workout
  - PATCH /api/users/{user_id}/workouts/{template_id}
  - Headers: X-User-Id: {user_id}
  - Body (JSON): { "step_count": 1500, "duration_minutes": 30, "note": "optional note" }
  - Behavior: If the user row exists, a `workout_history` row is inserted with before/after values and the `user_workouts` row is updated. If no user row exists, a new `user_workouts` row is inserted and a history row with NULL-before values is created.
  - Response: { ok: true, user_workout_id, step_count, duration_minutes, updated_at, total_steps }

- Get history for a user's template
  - GET /api/users/{user_id}/workouts/{template_id}/history
  - Headers: X-User-Id: {user_id}
  - Response: { history: [{ id, step_count_before, step_count_after, duration_before, duration_after, changed_at, changed_by, note }, ...] }

Example curl
- Update user's Morning Walk (replace IDs):
  curl -X PATCH "http://127.0.0.1:5000/api/users/USER_ID/workouts/TEMPLATE_ID" \
    -H "Content-Type: application/json" -H "X-User-Id: USER_ID" \
    -d '{"step_count":1500,"duration_minutes":35,"note":"walked 15min"}'

Database notes and migration
- Ensure `workout_templates` exists before creating `user_workouts` (FK target).
- Add column if missing:
  ALTER TABLE public.workout_templates ADD COLUMN IF NOT EXISTS editable_by_user boolean NOT NULL DEFAULT false;
- Seed templates (example):
  INSERT INTO public.workout_templates (name, default_step_count, default_duration_minutes, metadata, editable_by_user) VALUES ('Morning Walk',1000,30,'{"public":true}'::jsonb,true), ('Evening Run',2000,20,'{"public":true}'::jsonb,true) ON CONFLICT (lower(name)) DO UPDATE SET default_step_count=EXCLUDED.default_step_count, default_duration_minutes=EXCLUDED.default_duration_minutes, metadata=EXCLUDED.metadata, editable_by_user=EXCLUDED.editable_by_user;

Retention & maintenance
- `workout_history` is append-only; consider retention/partitioning if it grows large.
- `total_steps` is computed at read time as the sum of merged step_count values.

Contact / Next steps
- To wire frontend: call GET /api/workouts/templates then GET /api/users/{user}/workouts to render merged values. Use PATCH to update and show history via /history.
- If you want, I can add a migration file under `migrations/` and commit + push this README for you.
