# DBBSA Architecture — Precise Reference

Last updated: 2026-05-31

Purpose
- This file is the single-source architecture reference for the repository.
- It is the authoritative blueprint for portal routing, roles, data models, deployment, and operational behavior.
- Update this file whenever portal route structure, domain mapping, role mapping, or deployment topology changes.

Audience
- Developers, architects, DevOps, SREs, security reviewers.

High-level goals
- Single codebase with strong modular separation.
- Exact portal route mapping for student, instructor, parent, school, and admin.
- Local development mirrors production host routing using `lvh.me` aliases.
- Admin paths remain host-agnostic and exempt from portal-only redirects.
- CBT resilience with 30-second auto-save and silent token refresh.

Table of contents
- System context
- Domains and host routing
- Portal route map
- Role mapping and access
- Data model summary
- Middleware and auth
- CBT autosave and refresh
- Admin/system exclusivity
- Deployment & infra
- CI/CD and testing
- Runbook and operational notes

-----------------------------

System context
- The system is a Django monolith under `neural_village/`.
- Public-facing portals are served from the portal host domain.
- Admin / school admin and system admin can be reached from safe hosts and are exempt from portal redirects.

Domain and host routing
- Canonical portal hosts:
  - `portal.lvh.me` (local development portal host)
  - `portal.neuralvillage.com` (production portal host)
- System host:
  - `sys.neuralvillage.com` (super admin / system services)
- Admin host:
  - `admin.dbbsa.com` (school admin) unless school admin also uses the portal host for shared school tools.
- Public marketing host:
  - `www.neuralvillage.com` or `dbbsa.com` for landing and awareness.

Host routing rules
- Requests to `/portal/*` should only be served on the portal host.
- Requests to `/admin/` and `/superadmin/` are exempt from portal-only redirect behavior.
- Staff / superuser users may access `/admin/` from any trusted host.
- School admin can use the portal host for `/portal/school/` in addition to `admin.dbbsa.com` for dedicated admin UX.

Portal route map

Shared public portal routes
- `GET /` — marketing landing page.
- `GET /auth/login/` — shared login page.
- `POST /auth/login/` — authenticate and route by role.
- `POST /auth/logout/` — shared logout.

Student portal
- `GET /portal/student/` — student dashboard.
- `GET /portal/student/courses/` — enrolled courses & modules.
- `GET /portal/student/live-class/` — live class access.
- `GET /portal/student/live-quizzes/` — active quizzes and CBT list.
- `GET /portal/student/results/` — completed results and progress.

Instructor portal
- `GET /portal/instructor/` — instructor dashboard.
- `GET /portal/instructor/cohorts/` — cohort list.
- `GET /portal/instructor/cohort/<uuid:cohort_id>/` — cohort detail.
- `GET /portal/instructor/students/` — student roster.
- `GET /portal/instructor/insights/` — analytics and insights.
- `GET /portal/instructor/school/` — school overview and tools.
- `POST /portal/instructor/log-event/` — instructor event telemetry.

Parent portal
- `GET /portal/parent/` — parent dashboard.
- `GET /portal/parent/students/` — linked children roster.
- `GET /portal/parent/progress/` — child progress and attendance.

School portal
- `GET /portal/school/` — school admin home.
- `GET /portal/school/cohorts/` — cohort management.
- `GET /portal/school/hardware/` — device inventory and registration.
- `GET /portal/school/onboarding/` — student and instructor onboarding.

Admin and system routes
- `GET /admin/` — Django admin UI.
- `GET /superadmin/` — system admin dashboard.
- `GET /health/` — health check.
- `GET /metrics/` — metrics endpoint.

Role mapping and UX enforcement

Canonical roles
- `student`
- `instructor`
- `parent`
- `school_admin`
- `super_admin`
- `staff`

Role behavior
- `student`: only `/portal/student/*`.
- `instructor`: `/portal/instructor/*` and limited `/portal/school/*` for school-level tools where permitted.
- `parent`: only `/portal/parent/*`.
- `school_admin`: `/portal/school/*` and shared `/portal/instructor/*` school tools when needed.
- `super_admin` / `staff`: admin dashboards and system tooling; not portal-bound.

Authentication and authorization
- Primary web auth uses Django `Auth`.
- JWT is used for CBT / API token handling.
- `User_Profile.role` is the canonical role source.
- `is_staff` / `is_superuser` is used for Django admin and system-level access.
- `school_admin` and `super_admin` flows require 2FA in this architecture.
- Session cookies should be `Secure`, `HttpOnly`, and `SameSite=Lax`.

Data model summary

Core identity models
- `User` (Django auth user)
  - `username`
  - `email`
  - `first_name`
  - `last_name`
  - `is_active`
  - `is_staff`
  - `is_superuser`
  - `last_login`

- `User_Profile`
  - `user` (OneToOne -> User)
  - `role`
  - `phone`
  - `school`
  - `timezone`
  - `locale`

Academic models
- `School`
  - `uuid`, `name`, `location`, `partner`, `capacity`, `is_verified`, `status`
- `Cohort`
  - `uuid`, `school`, `name`, `track`, `start_date`, `end_date`, `status`, `instructor`
- `Student`
  - `user`, `school`, `cohort`, `track`, `enrollment_date`, `is_active`
- `Instructor`
  - `user`, `school`, `can_grade`, `can_deploy_cbt`
- `Parent`
  - `user`, `children` (M2M -> Student)

CBT models
- `Module`
  - `uuid`, `title`, `summary`, `duration_minutes`, `is_active`
- `CBT_Quiz`
  - `module`, `name`, `duration_seconds`, `auto_save_interval_seconds`, `max_attempts`
- `CBT_Session`
  - `student`, `quiz`, `started_at`, `ended_at`, `status`, `auto_saved_answers`, `jwt_token`, `token_expires_at`, `last_autosave_at`
- `AttendanceSession`
  - `uuid`, `cohort`, `started_at`, `ended_at`
- `AttendanceRecord`
  - `session`, `student`, `status`, `recorded_at`
- `HardwareAsset`
  - `uuid`, `device_tag`, `school`, `is_online`, `override_active_until`, `last_seen_at`

Middleware and auth
- `DomainRoutingMiddleware` maps hostnames to portal behavior.
- `/admin/` is exempt from portal redirect.
- School admin is allowed on portal host and `admin.dbbsa.com`.
- `RoleBasedAccessMiddleware` enforces nested role-specific page access.
- `require_role` decorator protects views by role.
- `require_domain` decorator protects host-specific views.
- `SilentTokenRefreshMiddleware` proactively refreshes CBT session tokens before expiry.

CBT autosave and refresh
- Student CBT clients autosave every 30 seconds.
- `CBT_Session` stores `jwt_token` and `token_expires_at`.
- If `token_expires_at` is within the refresh threshold, the backend issues a new token transparently.
- Endpoints:
  - `POST /cbt/sessions/`
  - `POST /cbt/sessions/{id}/autosave/`
  - `POST /cbt/sessions/{id}/submit/`
  - `POST /cbt/refresh-token/`
- Clients must persist the latest returned token and retry transient failures with backoff.

Admin/system exclusivity
- `super_admin` access is guarded by host, role, and optional IP whitelist.
- `/admin/` remains accessible regardless of portal host for staff and superusers.
- `/portal/school/` supports both school admin and instructor school-level visibility.

Deployment & infra
- Environments: `local`, `staging`, `production`.
- App servers behind load balancer / reverse proxy.
- PostgreSQL primary + replicas.
- Redis for cache and Celery broker.
- S3-compatible storage for static/media.
- Optional CDN for static assets.
- Production host names:
  - `portal.neuralvillage.com`
  - `admin.dbbsa.com`
  - `sys.neuralvillage.com`
  - `www.neuralvillage.com`

CI/CD and testing
- GitHub Actions or GitLab CI:
  - lint, mypy, flake8, black
  - unit tests
  - integration tests
  - build and deploy
- End-to-end smoke tests for student/instructor/parent/school/admin flows.
- CBT-specific tests for token lifecycle, autosave, and submission.

Runbook and operational notes
- Backups: daily PostgreSQL snapshots + WAL archiving.
- Restore test: restore snapshot, point app servers to recovered DB.
- Token incident: reset any stuck CBT session and notify affected student.
- Admin incident: verify `/admin/` path access and host bypass rules.

Exact blueprint enforcement
- This file is the authoritative architecture source for portal routing, role map, and deployment behavior.
- Only update this file when the core portal architecture changes.
