# Appendix — State Machines & Type Catalogs

Reference for the **workflows**, the **tab behavior matrices**, and the lifecycle **states** and
classification **types** that the AI Library and Initiatives stories rely on.

Workflow and tab matrices come from the *Action Status*, *Collab Status*, *Asset Detail* and
*Init Detail* sheets of `Control H de U.xlsx`; catalog values are as seeded in the database
(`lists` / `list_items`, see [`db/sql/`](../../db/sql)).

---

## Asset Action Workflows (Actions Table)

Every asset event is a **new row** in `actions` — nothing is updated in place. A row carries
the asset, the acting or assigned user, a `type` (→ `ACTION_TYPE`) and, for workflow events, a
`workflow_status` (→ `WORKFLOW_STATUS`: `PENDING` → `HANDLED`).

There are exactly two states. A row is `PENDING` while it still awaits its recipient's action
and `HANDLED` once it no longer does. There is deliberately no "seen/notified" state: that
recorded only that a user had *looked* at an item, which is read state rather than work state.
Mixing the two meant a notification could be cleared in a way that silently revoked the
assignee's turn. Read state now lives in the client, per device, and is never recorded here.

### Contribution workflow

Each cell names the user story that **inserts** a row with that `(type, workflow_status)`.

| `type` | PENDING | HANDLED | Assigned to |
|--------|---------|---------|-------------|
| `PROPOSAL` | — | Propose Asset | Proposer |
| `REVIEW` | Propose Asset | Review Asset Proposal | Reviewer |
| `MODIFICATION` | Review Asset Proposal | Modify Asset Proposal | Proposer |
| `PUBLICATION` | Review Asset Proposal | My Asset Requests (acknowledge) | Proposer |
| `REJECTION` | Review Asset Proposal | My Asset Requests (acknowledge) | Proposer |
| `VERSIONING` | — | Edit Asset | User |
| `DEPRECATION` | — | Edit Asset | User |

Types with no `PENDING` cell are written already terminal — they record that something
happened rather than that somebody owes an action, so nobody is ever waiting on them.

`PUBLICATION` and `REJECTION` are informational: the recipient has nothing to do but take
note, and the notice becomes `HANDLED` only when they explicitly acknowledge it. Opening it is
not acknowledging it, so an outcome can never pass unread.

### Community layer

These carry **no** `workflow_status` — they are facts, not assignments.

| `type` | Created by | Attributed to |
|--------|------------|---------------|
| `USAGE` | [Asset Tab] Characteristics | User |
| `VOTE` | Explore Category / Asset Detail | User |
| `COMMENT` | [Asset Tab] Discussion | User |
| `QUESTION` | [Asset Tab] Discussion | User |
| `ANSWER` | [Asset Tab] Discussion | User |

> All the rows a single user story produces are inserted in **one transaction**.

**Story codes:** [Propose Asset → HU-LI04](04-lib.md#hu-li04---propose-asset) ·
[Edit Asset → HU-LI03](04-lib.md#hu-li03---edit-asset-include-versioning--deprecation) ·
[Asset Notifications → HU-LI14](04-lib.md#hu-li14--notifications-asset-notifications) ·
[Review Asset Proposal → HU-LI16](04-lib.md#hu-li16---review-asset-proposal) ·
[Modify Asset Proposal → HU-LI17](04-lib.md#hu-li17---modify-asset-proposal) ·
[User Acknowledgment of Asset Notification → HU-LI18](04-lib.md#hu-li18---user-acknowledgment-of-asset-notification) ·
[Characteristics → HU-LI07](04-lib.md#hu-li07--asset-tab-characteristics-include-report-usage) ·
[Discussion → HU-LI11](04-lib.md#hu-li11--asset-tab-discussion)

### Asset status transitions

| From | Event | To |
|------|-------|----|
| — | Propose Asset | `PROPOSED` |
| `PROPOSED` | Review → approve | `PUBLISHED` |
| `PROPOSED` | Review → reject | `REJECTED` |
| `PROPOSED` | Review → request changes | `FEEDBACK` |
| `FEEDBACK` | Modify → resubmit | `PROPOSED` |
| `PUBLISHED` | Edit Asset → deprecate | `DEPRECATED` |

---

## Asset tab options by user story

The same eight tabs back every asset surface; the parent story decides what each one does.
(*Options for each User Story related to Asset Requests*.)

| Asset Tab | New Asset *(Asset Management)* | Edit Asset *(Asset Management)* | Propose Asset *(Explore Category)* | Asset Detail *(Explore Category)* |
|-----------|-------------------------------|---------------------------------|------------------------------------|-----------------------------------|
| Core Fields | Save | Save core fields | Characteristics › | Unified in Detail tab |
| Characteristics | Save | Save new version | Related assets › | Unified in Detail tab |
| Related Assets | Save | Save related assets | Related inits › | Read-only |
| Related Inits | Save | Save related inits | Request asset review | Read-only |
| Permissions | Save | Save permissions | Not applicable | Not applicable |
| Discussion | Not applicable | Multiple options | Not applicable | Multiple options |
| History | Not applicable | Read-only | Not applicable | Read-only |
| Versioning | Not applicable | Read-only | Not applicable | Read-only |

- **Save** — the whole modal is persisted at once (create flow).
- **Save …** — only that tab's slice is persisted; only *Save new version* bumps the version.
- **›** — a wizard step: the button advances to the next tab; the last one submits.
- **Multiple options** — post, ask, answer, vote or delete one's own entries.

---

## Initiative Collaboration Workflows (Collaborations Table)

The initiative workflow mirrors the asset one over `collaborations`, with `type` (→
`COLLAB_TYPE`) and the same `workflow_status` ladder.

### Activation & diagnosis workflow

| `type` | PENDING | HANDLED | Assigned to |
|--------|---------|---------|-------------|
| `ACTIVATION` | — | Propose Initiative | Proposer |
| `DIAGNOSIS` | Propose Initiative | Diagnosis of the Initiative | Reviewer |
| `MODIFICATION` | Diagnosis of the Initiative | Modify Initiative | Proposer |
| `ACCEPTANCE` | Diagnosis of the Initiative | User Acknowledgment of Initiative Notification | Proposer |
| `REJECTION` | Diagnosis of the Initiative | User Acknowledgment of Initiative Notification | Proposer |
| `KICKOFF` | — | Edit Initiative | User |
| `DELIVERY` | — | Edit Initiative | User |
| `ARCHIVING` | — | Edit Initiative | User |

`inits` shares the `WORKFLOW_STATUS` list with `lib`, so the two-state model applies here too.
`KICKOFF` / `DELIVERY` / `ARCHIVING` are written by Initiative Management
(`specs/004-initiative-management`) as completed log rows (`HANDLED`, attributed to whoever
made the change) — they raise **no** pending notice, same as `DEPRECATION` on the asset side.
The propose / diagnose / modify rows are still seed data only (those stories are not built yet).

### Community layer

| `type` | Created by | Attributed to |
|--------|------------|---------------|
| `VOTE` | Explore Initiatives / Initiative Detail | User |
| `COMMENT` | [Initiative Tab] Discussion | User |
| `QUESTION` | [Initiative Tab] Discussion | User |
| `ANSWER` | [Initiative Tab] Discussion | User |

> All the rows a single user story produces are inserted in **one transaction**.

**Story codes:** [Propose Initiative → HU-IN05](05-inits.md#hu-in05---propose-initiative) ·
[Edit Initiative → HU-IN03](05-inits.md#hu-in03---edit-initiative-include-delivery--archiving) ·
[Initiative Notifications → HU-IN13](05-inits.md#hu-in13--notifications-initiative-notifications) ·
[Diagnosis of the Initiative → HU-IN15](05-inits.md#hu-in15---diagnosis-of-the-initiative) ·
[Modify Initiative → HU-IN16](05-inits.md#hu-in16---modify-initiative) ·
[User Acknowledgment of Initiative Notification → HU-IN17](05-inits.md#hu-in17---user-acknowledgment-of-initiative-notification) ·
[Discussion → HU-IN11](05-inits.md#hu-in11--initiative-tab-discussion)

### Initiative status transitions

| From | Event | To |
|------|-------|----|
| — | Propose Initiative | `ACTIVATED` |
| `ACTIVATED` | Diagnosis → accept | `ACCEPTED` |
| `ACTIVATED` | Diagnosis → reject | `REJECTED` |
| `ACTIVATED` | Diagnosis → request changes | `FEEDBACK` |
| `FEEDBACK` | Modify → resubmit | `ACTIVATED` |
| `ACCEPTED` | Edit Initiative → kick off (`KICKOFF`) | `IN_PROGRESS` |
| `ACCEPTED` / `IN_PROGRESS` | Edit Initiative → deliver (`DELIVERY`) | `DELIVERED` |
| `ACCEPTED` / `IN_PROGRESS` / `DELIVERED` | Edit Initiative → archive (`ARCHIVING`) | `ARCHIVED` |

Only these six owner moves are possible from Initiative Management; the server refuses every
other status change there (400). `ACTIVATED`, `FEEDBACK` and `REJECTED` initiatives cannot be
archived from Edit Initiative.

---

## Initiative tab options by user story

(*Options for each User Story related to Initiative Requests*.)

| Initiative Tab | Edit Initiative *(Initiative Management)* | Propose Initiative *(Explore Initiatives)* | Initiative Detail *(Explore Initiatives)* |
|----------------|------------------------------------------|--------------------------------------------|-------------------------------------------|
| Core Fields | Save core fields | Go to diagnosis questions | Read-only |
| Diagnosis Questions | Read-only | Request diagnosis | Read-only |
| Related Assets | Save related assets | Not applicable | Read-only |
| Permissions | Save permissions | Not applicable | Not applicable |
| Discussion | Read-only | Not applicable | Multiple options |
| History | Read-only | Not applicable | Read-only |

---

## As seeded in the database

English labels are the seeded values; lists marked *(en/es)* are bilingual.

| List code | Type | Used by | Values |
|-----------|------|---------|--------|
| `LIST_TYPE` | LIST_OF_VALUES | ADMIN lists *(en/es)* | List of Values, Scale, Feature, Criteria |
| `OPTION_TYPE` | LIST_OF_VALUES | ADMIN options *(en/es)* | Content, Form, Report, Card Gallery |
| `BIZ_UNIT_TYPE` | LIST_OF_VALUES | ADMIN business units *(en/es)* | Business Unit, Department, Area, Division |
| `FEAT_TYPE` | LIST_OF_VALUES | TAXO features | General, Technical, Commercial, Usability, Documentation |
| `PROJECT_STATUS` | LIST_OF_VALUES | COLLAB projects | Planned, In Progress, On Hold, Completed |
| `DIMENSIONS_UNIT` | LIST_OF_VALUES | COLLAB dimensions | Percentage, Units, Count, Hours, Days |
| `GENAI_DEV_ADOPTION`, `GENAI_QA_ADOPTION` | SCALE | COLLAB metrics *(en/es)* | 5-level adoption scales |
| `ASSET_STATUS` | LIST_OF_VALUES | LIB assets | Proposed, Feedback Provided, Published, Rejected, Deprecated |
| `ACTION_TYPE` | LIST_OF_VALUES | LIB actions | Proposal, Review, Modification, Publication, Rejection, Versioning, Deprecation, Usage, Vote, Comment, Question, Answer |
| `WORKFLOW_STATUS` | LIST_OF_VALUES | LIB actions / INITS collaborations | Assigned, Notified, Finished |
| `RELATION_TYPE` | LIST_OF_VALUES | LIB / INITS / PROC relations | Depends On, Related To, Similar To, Part Of, Used By, Extends, Contains, Inspired By |
| `TARGET_TYPE` | LIST_OF_VALUES | permissions (all modules) | Users, Roles, Projects, Teams, Units, Public |
| `ACCESS_LEVEL` | LIST_OF_VALUES | permissions (all modules) | View, Manage |
| `INITIATIVE_STATUS` | LIST_OF_VALUES | INITS | Activated, Feedback Provided, Accepted, Rejected, In Progress, Delivered, Archived |
| `INITIATIVE_TYPE` | LIST_OF_VALUES | INITS | Exploration, Prototyping, Implementation |
| `COLLAB_TYPE` | LIST_OF_VALUES | INITS collaborations | Activation, Diagnosis, Modification, Acceptance, Rejection, Kickoff, Delivery, Archiving, Vote, Comment, Question, Answer |
| `EXPECTED_IMPACT` | LIST_OF_VALUES | INITS | Time Reduction, Quality Improvement, Error Reduction, Decision Support, Improved User Experience, Cost Savings, Revenue Increase, Compliance Enhancement, Risk Reduction, Scalability Improvement, Innovation, Other |
| `PRIORITY_LEVEL` | LIST_OF_VALUES | INITS | High, Medium, Low |
| `CLARITY_MATURITY`, `SUPPORT_OBJECTIVE`, `COMPLEXITY`, `DATA_INTEGRATIONS`, `RISK_IMPACT`, `SUSTAINABILITY` | CRITERIA | INITS diagnostics *(en/es)* | 1–3 scale per criterion |
| `DASHBOARD_TYPE` | LIST_OF_VALUES | ANA | Dashboard, Report, Scorecard, KPI View, Analytical View |
| `SOURCE_TYPE` | LIST_OF_VALUES | ANA | Internal Page, Power BI, Looker Studio, Tableau, Qlik Sense, Metabase, Superset, Custom Iframe |
| `DASHBOARD_STATUS` | LIST_OF_VALUES | ANA | Draft, Published, Archived, Retired |
| `PARAM_TYPE` | LIST_OF_VALUES | ANA parameters | String, Number, Boolean, Date |
| `EXECUTION_STATUS` | LIST_OF_VALUES | ANA executions | Success, Failed, Cancelled, Timeout, Unauthorized |
| `PROCESS_TYPE` | LIST_OF_VALUES | PROC *(en/es)* | Primary, Support *(Porter's value chain)* |
| `PROCESS_STATUS` | LIST_OF_VALUES | PROC *(en/es)* | Draft, Review, Published, Deprecated |

> The source of truth for these values is `db/sql/*.sql`. When a list changes there, update
> this table.
