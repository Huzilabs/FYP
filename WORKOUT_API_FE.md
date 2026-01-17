WORKOUT API — Frontend Quick Reference

This file documents the workout-related HTTP API endpoints and example requests/responses for the frontend team.

- Base URL: `http://<HOST>:5000` (example: `http://127.0.0.1:5000`)
- Header: include `X-User-Id: <user_id>` for owner-only operations (dev-only; replace with auth in prod)

Endpoints

1) List templates (global + caller's private templates)
- GET /api/workouts/templates
- Headers: `X-User-Id: <user_id>` (optional)
- Response: 200 { ok: true, templates: [{ id, name, default_count, default_duration_minutes, editable_by_user, owner_id }, ...], total_count }
- `total_count` is the sum of merged counts (COALESCE(user_workouts.count, workout_templates.default_count)) for the templates returned.

Example (curl):

curl -X GET http://127.0.0.1:5000/api/workouts/templates -H "X-User-Id: d086480d-7cf9-4d06-a5ab-e8c4a8118214"

2) Create a private template (owner-only)
- POST /api/users/{user_id}/workout_templates
- Headers: `X-User-Id: {user_id}`
- Body JSON: { "name": "push", "default_count": 10, "default_duration_minutes": 5, "editable_by_user": true }
- Response: 201 { ok: true, template: { id, name, default_count, default_duration_minutes, editable_by_user, owner_id } }

Example (curl):

curl -X POST http://127.0.0.1:5000/api/users/d086480d-7cf9-4d06-a5ab-e8c4a8118214/workout_templates \
  -H "X-User-Id: d086480d-7cf9-4d06-a5ab-e8c4a8118214" \
  -H "Content-Type: application/json" \
  -d '{"name":"push","default_count":10,"default_duration_minutes":5}'

Notes: private templates are created with `owner_id = user_id` and are editable/deletable only by that owner.

3) Update a template (owner-only for private templates)
- PATCH /api/workout_templates/{template_id}
- Headers: `X-User-Id: {user_id}`
- Body JSON: any of { "name":..., "default_count":..., "default_duration_minutes":..., "editable_by_user":... }
- Response: 200 { ok: true, template: {...} }
- Predefined/global templates (owner_id IS NULL) are immutable via the API and will return 403 if attempted to be changed.

4) Delete a private template (owner-only)
- DELETE /api/workout_templates/{template_id}
- Headers: `X-User-Id: {user_id}`
- Response: 200 { ok: true }

5) List user's merged workouts
- GET /api/users/{user_id}/workouts
- Merges global templates with per-user values. Each workout: { template_id, name, user_workout_id|null, count, duration_minutes, editable_by_user, updated_at }
- Response: 200 { ok: true, workouts: [...], total_steps }
- `total_steps` is the sum of the merged `count` values across templates.

6) Get a single merged workout
- GET /api/users/{user_id}/workouts/{template_id}
- Response: 200 { ok: true, workout: {...} }

7) Update (create/change) user's workout values
- PATCH /api/users/{user_id}/workouts/{template_id}
- Headers: `X-User-Id: {user_id}`
- Body JSON: { "count": 123, "duration_minutes": 12 }
- Response: 200 { ok: true, user_workout_id, count, duration_minutes, updated_at, total_steps }
- Behavior: Creates or updates `public.user_workouts` row. For predefined/global templates (owner_id IS NULL) the DB trigger records a history snapshot in `public.workout_history`. User-created templates do NOT generate history snapshots.

8) Get history for a user's template (only applies to predefined/global templates)
- GET /api/users/{user_id}/workouts/{template_id}/history
- Headers: `X-User-Id: {user_id}`
- Response: 200 { ok: true, history: [{ id, count_before, count_after, duration_before, duration_after, changed_at, changed_by, note }, ...] }

Developer notes
- Global templates have `owner_id = NULL`. Private templates have `owner_id = user_id`.
- Field names: `count` / `default_count` (not `step_count`).
- History is only recorded for predefined/global templates by the DB trigger.

If you want this file updated with more examples or TypeScript/React fetch snippets, tell me which flavor and I'll add them.
