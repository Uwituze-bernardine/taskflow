# TaskFlow — Task Management System

Scaffold generated from the provided SRS (96 functional requirements across
15 modules). Django REST Framework backend + React/TypeScript frontend.

## Structure

```
taskflow/
├── backend/     Django project (DRF, JWT auth, SQLite by default)
│   ├── taskflow/        settings, urls
│   ├── users/           FR-001–007  accounts, roles, permissions
│   ├── projects/        FR-008–014  projects, members, progress
│   ├── tasks/            FR-015–042  tasks, priority, workflow, subtasks, dependencies
│   ├── comments/         FR-043–048  comments, mentions
│   ├── attachments/      FR-049–053  file uploads
│   ├── notifications/    FR-054–060  notifications, preferences
│   └── audit/             FR-085–089  audit trail (auto-logged via signals)
└── frontend/    React + TypeScript (Vite)
    └── src/
        ├── api/          axios client + typed API calls
        ├── context/      auth context (JWT session)
        ├── pages/        Login, Dashboard, Projects, Tasks, detail views
        └── components/   layout, route guards
```

## User management (FR-001 – FR-007)

| Requirement | Where |
|---|---|
| FR-001 sign up | `POST /api/auth/register/` · `/register` page. Always creates a **Team Member**; the request cannot choose a role. |
| FR-002 log in / out | `POST /api/auth/login/`, `POST /api/auth/logout/` (revokes the refresh token) · `/login` |
| FR-003 edit own profile | `GET/PATCH /api/users/me/`, `POST /api/users/me/change-password/` · `/profile` |
| FR-004 create / deactivate / reactivate | `POST /api/users/`, `POST /api/users/{id}/deactivate/`, `.../reactivate/` · `/admin/users`. Deactivating ends the person's sessions immediately. Accounts are never deleted, so task history stays intact. |
| FR-005 roles | System Administrator, Project Manager, Team Leader, Team Member. Admins change roles from `/admin/users`. |
| FR-006 role-based access | Backend: DRF permission classes (authoritative). Frontend: `RequireRole` route guard and `lib/roles.ts` hide controls a role can't use. |
| FR-007 reset / manage access | `POST /api/users/{id}/reset-password/` generates a one-time temporary password and ends the user's sessions. |

Notes:
- `python manage.py createsuperuser` now creates a System Administrator automatically.
- Any signed-in user can list users (for assignee dropdowns), but non-admins only get
  id / username / name / role for *active* users. Email, phone and status are admin-only.
- An admin cannot deactivate or demote their own account.
- Run the backend tests with `python manage.py test users`.

## Projects, tasks and assignment (FR-008 – FR-031)

**Who can do what** (enforced by the API; the UI hides the rest using flags the server sends):

| | Admin | Project Manager | Team Leader | Team Member |
|---|---|---|---|---|
| Create a project | yes | yes | no | no |
| Edit / close / archive a project, manage its members | any project | own projects | no | no |
| See a project | all | own + member of | member of | member of |
| Create a task | anywhere | in their projects | in projects they belong to | no |
| Edit, assign / reassign, archive a task | any | in own projects | in projects they belong to | no |
| Change a task's status | any | in own projects | same, plus tasks assigned to them | only tasks assigned to them |
| Permanently delete a task | yes | no | no | no |

The role lists live in one place: `backend/projects/access.py` (`PROJECT_CREATOR_ROLES`, `TASK_CREATOR_ROLES`).

Rules worth knowing:
- A task's assignee must be an active member (or the manager) of its project. Standalone tasks (no project) can go to anyone.
- Progress = completed / all top-level tasks that are not archived or cancelled (FR-013).
- Closed and archived projects, and their tasks, are read-only until the project is reopened. Projects are never deleted.
- A member with unfinished tasks in a project cannot be removed from it until those are reassigned or done.
- Task status changes only go through `POST /api/tasks/{id}/status/` (so history + notifications always fire);
  archiving through `/archive/` and `/restore/`. `DELETE` also archives; admins can add `?permanent=true`.
- History (FR-025): `GET /api/tasks/{id}/history/` returns field-level before/after values with who and when.
- `GET /api/tasks/mine/` (FR-029) and `GET /api/tasks/team/` (FR-030: a PM's team = members of projects they manage,
  a team leader's = members of projects they belong to, admins see all).
- People appear to others only as id / username / name / role, never email or phone.

Run the whole backend suite with `python manage.py test`.

## Task status, workflow, subtasks and dependencies (FR-032 – FR-042)

- **Statuses (FR-032/033):** the six predefined statuses (To Do, In Progress, Blocked, Under Review, Completed,
  Cancelled) always apply. `GET /api/tasks/workflow/` lists every status a task can move to, in order; changing
  status goes through `POST /api/tasks/{id}/status/` with either `{"status": "..."}` or `{"custom_status": id}`.
- **History (FR-034):** `GET /api/tasks/{id}/status-history/` is the status-only log (who, when, from → to, including
  custom status names). The general change log from the previous round (`/history/`) also picks up status moves.
- **Custom statuses (FR-035):** `backend/tasks/models.py: CustomTaskStatus` — administrator-only via
  `/api/tasks/statuses/` (UI: **Task statuses**, admins only). Each one has a `category`, one of the six predefined
  statuses it behaves like, so progress/completion/dependency rules never need to know about it by name. A status
  in use can be deactivated but not deleted.
- **Completion rules (FR-036):** a task can't be completed while unassigned or with open subtasks
  (`tasks/workflow.py: completion_problems`). The task page shows why under "Not ready to complete".
- **Progress (FR-037):** 100% once completed; otherwise the share of counted subtasks that are completed; 0%
  with no subtasks. Cancelled/archived subtasks are not counted.
- **Subtasks (FR-038/039/040):** one level deep, always in the parent's project, assigned independently of the
  parent. `POST /api/tasks/{id}/subtasks/` creates one; `GET` lists them. Cancelling a task cancels its unfinished
  subtasks. Completing a task with open subtasks is refused (see FR-036).
- **Dependencies (FR-041/042):** `depends_on` is per-task and opt-in (`enforce_dependencies`). Predecessors must be
  in the same project, not archived, not the task itself or its own parent/subtasks, and adding one that would loop
  back is rejected (`tasks/dependencies.py`). `POST/DELETE /api/tasks/{id}/dependencies/` (and
  `.../dependency-candidates/` for the picker). When enforced, a task can't move into progress/review/completed
  while a predecessor is unfinished; `is_blocked_by_dependencies` and `blocked_by` on the task tell the UI why.

Run `python manage.py test tasks.tests_workflow` for just this part, or `python manage.py test` for everything.

## Comments and attachments (FR-043 – FR-053)

- **Visibility (FR-043/049):** comments and attachments are only visible - and only postable -
  on tasks the current user can already see (same rule as tasks themselves). Trying to comment
  on or upload to a task you can't see, or one in a closed/archived project, is rejected.
- **Chronological order (FR-044):** comments are always returned oldest-first
  (`comments/models.py: Meta.ordering`).
- **Mentions (FR-045/046):** write `@username` in a comment body; the server resolves it against
  people who can actually see the task (`comments/mentions.py`) and notifies each one. Typing
  `@` for someone who can't see the task is silently ignored rather than erroring. Editing a
  comment re-resolves mentions and only notifies newly-added ones.
- **Discussion history (FR-047):** deleting a comment soft-deletes it - the row and its original
  body stay in the database, but the API shows "This comment was deleted." to everyone. There is
  no hard-delete for comments.
- **Edit/delete permissions (FR-048):** only the author can edit a comment. Deleting is the
  author, the task's manager, or an administrator (moderation), and only on a task that isn't
  read-only.
- **Metadata (FR-051):** filename, uploader, upload date and size are recorded and shown.
- **Restrictions (FR-052):** `attachments/models.py: AttachmentSettings` is a single
  admin-configurable row (`GET/PATCH /api/attachments/settings/`) for the allowed extensions and
  max size, defaulting to a common office/image/archive list and 25MB. The upload form shows the
  current limits.
- **Downloads (FR-050):** the API never returns a raw file URL - only `POST .../attachments/` for
  upload and `GET /api/attachments/{id}/download/` for download, both permission-checked on every
  call, not just at upload time. **Known dev-mode caveat:** Django's `runserver` with `DEBUG=True`
  also serves everything under `MEDIA_ROOT` as static files with no auth at all (this is a Django
  development convenience, not something this app enables) - so on a developer machine, someone
  who already knows or guesses an attachment's storage path could fetch it directly, bypassing the
  API. This does not happen with `DEBUG=False`, and a real deployment should keep `DEBUG=False`
  and put attachments behind a proper storage backend (S3 with signed URLs, etc.) rather than
  local `MEDIA_ROOT`.
- **Removal (FR-053):** the uploader, the task's manager, or an administrator; deletes the file
  from storage, not just the database row.

Run `python manage.py test comments attachments` for just this part.

## Notifications, reminders and calendar (FR-054 – FR-065)

- **Notifications (FR-054/055/056):** every notification carries a `category` -
  `assigned`, `status_changed`, `mentioned`, `due_soon`, `overdue` - set at the point it's
  created (`notifications/models.py: Category`).
- **Deadline reminders (FR-057/058) need a scheduled job**, not a web request - there's no
  user action that corresponds to "a day passed". Run periodically (daily is enough):
  ```bash
  python manage.py send_deadline_reminders            # 2-day "due soon" window by default
  python manage.py send_deadline_reminders --due-soon-days=3
  ```
  Wire it into cron, a systemd timer, or Celery beat in a real deployment. Each task is
  reminded at most once per category, so re-running it daily is safe.
- **Preferences (FR-059):** `GET/PATCH /api/notifications/preferences/`, one boolean per
  category, defaulting to on; unknown keys are rejected. UI: the **Notification preferences**
  panel on the profile page. `notify()` checks the recipient's preference before creating
  anything, so muting a category stops it at the source, not just in the UI.
- **History (FR-060):** `GET /api/notifications/` (filterable by `is_read`/`category`), plus
  `unread_count`, `mark_read` and `mark-all-read`. UI: the bell in the top bar (polls every
  60s) and a full **Notifications** page.
- **Calendar (FR-061/062/065):** `GET /api/tasks/calendar/?start=&end=&project=&status=&assigned_to=`
  reuses the task list's own visibility and filters, restricted to tasks with a due date in
  range. UI: a month-grid **Calendar** page.
- **Changing task dates (FR-063)** uses the existing task edit endpoint/form - dates are
  ordinary editable task fields, so no separate endpoint was needed.
- **Recurring tasks (FR-064):** a task can repeat `DAILY`/`WEEKLY`/`MONTHLY`/`YEARLY` (every
  N units, optionally until an end date) - only top-level tasks with a due date
  (`tasks/recurrence.py`). Completing one creates the next occurrence (fresh status, same
  title/project/assignee/priority/tags), linked via `recurrence_of` back to the series' first
  task; the API response's `next_occurrence` carries the new task so the UI can show it
  immediately. Subtasks cannot repeat.

Run `python manage.py test notifications tasks.tests_calendar_recurrence` for just this part.

## Dashboard, reports, audit trail and administration (FR-071 – FR-096)

- **Dashboard (FR-071–077):** `GET /api/dashboard/` (`backend/dashboard/`) - one call returns the
  signed-in user's task counts (FR-072–074), their projects' progress (FR-075), and - for
  project managers, team leaders and admins - team-level stats (FR-076): totals by status,
  current overdue count, and workload per team member. Status/priority badges throughout the
  UI are the visual indicators for FR-077.
- **Reports (FR-078–084):** `GET /api/reports/summary/?start=&end=&project=` (manager/admin
  only, `backend/reports/`) returns tasks created/completed in the date range (FR-078/082),
  current overdue tasks (FR-079), project progress (FR-080), workload by employee (FR-081),
  and the breakdown metrics in FR-084 (by priority, by status, average completion time).
  `GET /api/reports/export/` returns the same report as a CSV download (FR-083). UI: **Reports**.
  **Note on date ranges:** only "created" and "completed" counts are bounded by `[start, end]`;
  overdue, current status/workload and project progress are inherently a snapshot of *now*, not
  something that happened within a date range - both the API response and the UI label these
  separately so they aren't misread as range-filtered.
- **Audit trail (FR-085–089):** unchanged from earlier rounds, now with a UI -
  `GET /api/audit/` (admin-only) at **Administration → Audit log**, read-only everywhere
  including the Django admin.
- **Administration (FR-090–096):**
  - FR-090/091 manage users and roles → **Administration → Users** (built earlier). There's no
    permission model beyond the four fixed roles - "manage permissions" here means assigning a
    role, not editing a permission matrix.
  - FR-092 task statuses → **Administration → Task statuses** (built earlier).
  - FR-093 priorities → `CustomPriority` (`backend/tasks/models.py`), same pattern as custom
    statuses: a name that refines one of the four base levels, so sorting/validation never need
    to know about it specifically. **Administration → Priorities**.
  - FR-094 task categories/tags → `TaskTag` is an administrator-curated *suggestion* list
    (**Administration → Tags**); a task's own tags stay freeform strings - the registry doesn't
    constrain them, only what the UI offers to autocomplete.
  - FR-095 notification settings → `NotificationSettings.due_soon_days` (`backend/notifications/`),
    the threshold `send_deadline_reminders` uses by default. **Administration → System settings**,
    which also hosts FR-052's attachment size/type limits since both are "system configuration".
  - FR-096 view audit logs → covered above.

Run `python manage.py test dashboard reports` for just this part.

### A bug worth knowing about if you extend this further

`visible_tasks()` (and anything built on it, like a manager's "team" queryset) is a single Q
object OR-ing several joined conditions (project manager/members, assignee, creator, ...).
`.distinct()` makes plain row fetches correct, but **running `.values(...).annotate(Count(...))`
directly on top of it is not reliable** - leftover joins from the unrelated conditions can
corrupt the `GROUP BY`, even with `Count(..., distinct=True)`. This showed up anyway while
building the dashboard (confirmed with `.query` inspection in the shell) and is why
`dashboard/views.py` and `reports/metrics.py` both avoid `.values().annotate()` on these
querysets - they either re-query by a plain id list first, or tally in Python after a normal
`.distinct()` row fetch. Keep that pattern for any new aggregate built on `visible_tasks()`,
`visible_projects()`, or `team_queryset()`.

## Frontend tests

```bash
cd frontend
npm install
npm test          # vitest + React Testing Library + jsdom, ~63 tests
```

These render the real pages and components (real hooks, effects, conditionals) against a fake
API built with `axios-mock-adapter` (`src/test/fixtures.ts` holds data shaped like the backend's
serializers; `src/test/harness.tsx` renders as a logged-in user the way `ProtectedRoute` does).
They cover every page, the forms, the shared panels, and the token-refresh interceptor
(`src/api/client.ts`: refresh on 401, rotated refresh token, one shared refresh for simultaneous
401s, logout when refresh fails).

**What this is not:** a real browser. They do not check how anything looks (CSS, the modal
overlay, the calendar grid, responsive layout), file downloads (`createObjectURL` isn't in
jsdom, so `downloadAttachment`/`exportReport` are untested), or behaviour across browsers.
Before relying on this, click through the main flows once yourself.

## Colours and theme

All accent colours are tokens at the top of `frontend/src/styles.css` (`:root`), sampled from the login
photo: `--accent` (gold, button fills) with `--accent-ink` (text on it), `--accent-strong` (deep gold for
links, active tab, progress bars - gold itself is too pale to read on white), and `--accent-soft*`
(pale-gold highlights). Change those and the whole app follows. Status/priority badge colours
(green, red, amber, ...) are separate on purpose, so their meaning doesn't shift with the theme.

## Not yet built out (left as follow-ups)

- Calendar view (FR-061–065)
- Dedicated reporting/analytics endpoints and charts (FR-078–084)
- Full admin-configuration UI (FR-090–096) — currently covered by Django admin
- Real-time notification delivery (currently polled via REST, no websockets)
- Tests

## Running the backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
API available at `http://localhost:8000/api/`. Auth: `POST /api/auth/login/`
returns `{ access, refresh, user }`; send `Authorization: Bearer <access>`
on subsequent requests.

## Running the frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
App available at `http://localhost:5173`, proxies `/api` to the backend.

## Key design notes

- Roles: System Administrator, Project Manager, Team Leader, Team Member (FR-005),
  enforced via DRF permission classes (FR-006).
- Task status changes go through a dedicated endpoint (`POST /tasks/{id}/status/`)
  so history (FR-034) and notifications (FR-055) fire consistently, and
  completion is blocked when required fields are missing (FR-036).
- Dependencies (FR-041/042) are modeled as a self-referential M2M (`depends_on`);
  enforcement is opt-in per task via `enforce_dependencies`.
- Every task/status change is logged to `AuditLog` via Django signals (FR-085–087),
  and audit records are read-only everywhere, including the admin site (FR-089).
