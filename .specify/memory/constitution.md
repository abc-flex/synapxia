<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Modified principles:
	- [PRINCIPLE_1_NAME] -> I. Modular Monolith Boundaries
	- [PRINCIPLE_2_NAME] -> II. API-First Contract Stability
	- [PRINCIPLE_3_NAME] -> III. Risk-Based Testing Discipline
	- [PRINCIPLE_4_NAME] -> IV. Security and Secret Hygiene
	- [PRINCIPLE_5_NAME] -> V. Performance and Operability Baselines
- Added sections:
	- Compatibility and Deployment Rules
	- Engineering Workflow and Delivery Gates
- Removed sections:
	- None
- Templates requiring updates:
	- ✅ .specify/templates/plan-template.md
	- ✅ .specify/templates/spec-template.md
	- ✅ .specify/templates/tasks-template.md
	- ✅ .specify/templates/commands/*.md (directory not present; no updates required)
- Follow-up TODOs:
	- None
-->

# SynapxIA Constitution

## Core Principles

### I. Modular Monolith Boundaries
The backend MUST remain a modular monolith organized by bounded domains under
`api/app` (`admin`, `catalog`, `collab`, `auth`, and planned `genai`, `inits`,
`insights`, `workflows`). New features MUST be implemented inside the owning
domain module with routes in `routes/`, data access in `internal/`, and shared
cross-domain dependencies only in `api/app/internal`. Duplicating connection or
auth plumbing per module is prohibited unless there is a documented exception.
Rationale: the codebase already enforces central dependencies and domain folders;
maintaining these boundaries prevents tight coupling and regressions.

### II. API-First Contract Stability
All externally consumed behavior MUST be exposed through documented FastAPI
contracts and remain backward compatible for existing UI consumers in `ui/src/lib`
and `ui/src/types`. Existing endpoints, request keys, and response keys MUST NOT
be removed or renamed in-place; incompatible changes require a versioned route,
migration strategy, and UI adaptation plan. List endpoints MUST keep explicit
pagination/filter semantics (`skip`, `limit`, or equivalent bounded query inputs).
Rationale: the Astro UI is tightly coupled to current REST contracts and typed
interfaces; preserving contract stability avoids coordinated breakages.

### III. Risk-Based Testing Discipline
Every change MUST include verifiable tests proportional to risk. At minimum,
contributors MUST run service health checks (`make test`) and validate affected
paths through API docs or scripted calls. For backend contract, auth, migration,
or permission changes, automated tests (integration/contract or equivalent)
MUST be added or updated in the feature branch; manual-only verification is not
sufficient for those risk classes. For UI-only copy/layout changes, documented
manual verification is acceptable.
Rationale: the repository currently has strong smoke checks but limited automated
coverage, so testing rigor must scale with impact instead of remaining optional.

### IV. Security and Secret Hygiene
Authentication MUST remain JWT Bearer-based with bcrypt-hashed passwords; plain
password storage is forbidden. Production deployments MUST provide explicit
`SECRET_KEY` and restricted `CORS_ORIGINS`; insecure defaults are allowed only in
local development. Secrets and credentials MUST come from environment variables,
MUST NOT be committed in source files, and MUST be masked in logs. Access control
changes MUST preserve `is_active` and `is_superuser` semantics and domain role
constraints.
Rationale: security-critical behavior is already implemented in auth and DB
layers and must be consistently enforced across future changes.

### V. Performance and Operability Baselines
Database operations MUST use managed sessions/engines from centralized internal
dependencies and avoid unbounded queries or N+1 access patterns. Services MUST
remain runnable through Docker Compose and Make targets, and each deployable
surface (API, DB, UI) MUST keep a health/boot validation path. Logging MUST stay
structured enough to diagnose startup, authentication, and DB failures without
leaking secrets.
Rationale: current operations depend on containerized local parity, health checks,
and reusable DB/session wiring for reliability and performance.

## Compatibility and Deployment Rules

- Runtime stack is normative: FastAPI + SQLModel (Python >=3.12 managed by `uv`),
	Astro + Bun UI, PostgreSQL, Docker Compose orchestration.
- Database evolution MUST be additive and migration-driven through `db/sql` with
	ordered scripts; destructive changes require explicit rollback instructions.
- Compose service contracts (default ports, service names, and startup order) MUST
	remain compatible unless change notes update Make targets and docs in the same PR.
- Environment-driven configuration is required for hostnames, credentials, CORS,
	app environment, and token settings.

## Engineering Workflow and Delivery Gates

- Every feature spec and plan MUST include a Constitution Check that maps design
	decisions to the five core principles before implementation starts.
- Tasks MUST explicitly include work for: contract compatibility, migration impact,
	security review (auth/secrets/CORS), and performance/operability validation when
	the feature touches those concerns.
- Code review MUST block merges that violate any MUST rule unless an approved,
	time-boxed exception is documented with owner, risk, and rollback plan.
- Release readiness requires: green smoke tests, updated docs for changed behavior,
	and explicit confirmation that deployment commands (`make up`, `make test`) still
	function for the modified scope.

## Governance

This constitution supersedes local habits and ad hoc process notes. Amendments
require: (1) a documented proposal, (2) impact analysis across plan/spec/tasks
templates and operational docs, and (3) approval by project maintainers.

Versioning policy (semantic):
- MAJOR: Removes or redefines a principle in a backward-incompatible way.
- MINOR: Adds a new principle/section or materially expands governance scope.
- PATCH: Clarifications, wording improvements, and non-semantic refinements.

Compliance review policy:
- Each implementation plan performs a pre-design constitution gate review.
- Each pull request confirms ongoing compliance or records a justified exception.
- Periodic audits MAY sample recent features for drift and trigger template sync.

**Version**: 1.0.0 | **Ratified**: 2026-03-25 | **Last Amended**: 2026-03-25
