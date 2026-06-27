# Appendix — State Machines & Type Catalogs

Reference for the **workflows**, lifecycle **states** and classification **types** that the
Library and Initiatives stories rely on. The workflow matrices come from the *Action Status*
and *Collab Status* sheets of `Control H de U.xlsx`; the catalog values are as seeded in the
database (`lists` / `list_items`, see [`db/sql/`](../../db/sql)).

---

## Asset contribution & review workflow (actions)

The asset workflow is driven by the `actions` table's `type` and `workflow_status` columns
(`WORKFLOW_STATUS` = `ASSIGNED` → `NOTIFIED` → `FINISHED`). Each cell names the user story
that **inserts** a record with that `(type, workflow_status)`. The right column is the user
the action is assigned to.

### Contribution workflow

| `type` | ASSIGNED | NOTIFIED | FINISHED | Assigned to |
|--------|----------|----------|----------|-------------|
| PROPOSAL | — | — | HU-Propose | Proposer |
| REVIEW | HU-Propose | HU-Notifications | HU-Review | Reviewer |
| MODIFICATION | HU-Review | HU-Notifications | HU-Modify | Proposer |
| PUBLICATION | HU-Review | HU-Notifications | HU-Show Action | Proposer |
| REJECTION | HU-Review | HU-Notifications | HU-Show Action | Proposer |
| VERSIONING | — | — | HU-Versioning | User |
| DEPRECATION | — | — | HU-Versioning | User |

### Community layer

| `type` | Created by | Assigned to |
|--------|------------|-------------|
| USAGE | HU-Details | User |
| VOTE | HU-Vote | User |
| COMMENT | HU-Comment | User |
| QUESTION | HU-Question | User |
| ANSWER | HU-Answer | User |

> Records for a single user story are inserted simultaneously. The workflow story names map
> to the board as: HU-Propose → [HU-LI02](04-lib.md#hu-li02---propose), HU-Notifications →
> [HU-LI11](04-lib.md#hu-li11--notifications), HU-Review → [HU-LI12](04-lib.md#hu-li12---review),
> HU-Show Action → [HU-LI13](04-lib.md#hu-li13---show-action), HU-Modify →
> [HU-LI14](04-lib.md#hu-li14---modify), HU-Versioning → [HU-LI09](04-lib.md#hu-li09---versioning-include-deprecation),
> HU-Details/Vote/Comment/Question/Answer → [HU-LI03–HU-LI06](04-lib.md#hu-li03---details-include-report-usage).

---

## Initiative collaboration workflow (collaborations)

The initiative workflow mirrors the asset one over the `collaborations` table's `type` and
`workflow_status` columns.

### Contribution workflow

| `type` | ASSIGNED | NOTIFIED | FINISHED | Assigned to |
|--------|----------|----------|----------|-------------|
| ACTIVATION | — | — | HU-Activate | Proposer |
| DIAGNOSIS | HU-Activate | HU-Notifications | HU-Diagnosis | Reviewer |
| ACCEPTANCE | HU-Diagnosis | HU-Notifications | HU-Show Collab | Proposer |
| REJECTION | HU-Diagnosis | HU-Notifications | HU-Show Collab | Proposer |
| DELIVERY | HU-Delivery | HU-Notifications | HU-Show Collab | Proposer |
| VERSIONING | — | — | HU-Versioning | User |
| ARCHIVING | — | — | HU-Versioning | User |

### Community layer

| `type` | Created by | Assigned to |
|--------|------------|-------------|
| VOTE | HU-Vote | User |
| COMMENT | HU-Comment | User |
| QUESTION | HU-Question | User |
| ANSWER | HU-Answer | User |

> Workflow story names map to the board as: HU-Activate → [HU-IN03](05-inits.md#hu-in03---propose-activation),
> HU-Notifications → [HU-IN12](05-inits.md#hu-in12--notifications), HU-Diagnosis →
> [HU-IN13](05-inits.md#hu-in13---diagnosis), HU-Show Collab → [HU-IN14](05-inits.md#hu-in14---show-collab),
> HU-Delivery → [HU-IN04](05-inits.md#hu-in04---details-include-delivery).

---

## As seeded in the database

Key catalogs (English labels are the seeded values; some lists are bilingual en/es):

| List code | Type | Used by | Values |
|-----------|------|---------|--------|
| `ASSET_STATUS` | LIST_OF_VALUES | LIB assets | Proposed, Feedback Provided, Published, Rejected, Deprecated |
| `ACTION_TYPE` | LIST_OF_VALUES | LIB actions | Proposal, Review, Modification, Publication, Rejection, Versioning, Deprecation, Usage, Vote, Comment, Question, Answer |
| `WORKFLOW_STATUS` | LIST_OF_VALUES | LIB actions / INITS collaborations | Assigned, Notified, Finished |
| `RELATION_TYPE` | LIST_OF_VALUES | LIB / INITS / PROC relations | Depends On, Related To, Similar To, Part Of, Used By, Extends, Contains, Inspired By |
| `TARGET_TYPE` | LIST_OF_VALUES | permissions (all modules) | User, Role, Project, Team, Unit, Public |
| `ACCESS_LEVEL` | LIST_OF_VALUES | permissions (all modules) | View, Manage |
| `FEAT_TYPE` | LIST_OF_VALUES | TAXO features | General, Technical, Commercial, Usability, Documentation |
| `INITIATIVE_STATUS` | LIST_OF_VALUES | INITS | Activated, Accepted, Rejected, In Progress, Delivered, Archived |
| `INITIATIVE_TYPE` | LIST_OF_VALUES | INITS | Exploration, …, Implementation |
| `COLLAB_TYPE` | LIST_OF_VALUES | INITS collaborations | Activation, Diagnosis, Acceptance, Rejection, Delivery, Versioning, Archiving, Vote, Comment, Question, Answer |
| `EXPECTED_IMPACT` | LIST_OF_VALUES | INITS | Time Reduction, Quality Improvement, Error Reduction, Decision Support, Improved UX, Cost Savings, Revenue Increase, Compliance Enhancement, Risk Reduction, Scalability Improvement, Innovation, Other |
| `PRIORITY_LEVEL` | LIST_OF_VALUES | INITS | High, Medium, Low |
| `CLARITY_MATURITY`, `SUPPORT_OBJECTIVE`, `COMPLEXITY`, `DATA_INTEGRATIONS`, `RISK_IMPACT`, `SUSTAINABILITY` | CRITERIA | INITS diagnostics | 1–3 scale (en/es) per criterion |
| `DASHBOARD_TYPE` | LIST_OF_VALUES | ANA | Dashboard, Report, Scorecard, KPI View, Analytical View |
| `SOURCE_TYPE` | LIST_OF_VALUES | ANA | Internal Page, Power BI, Looker Studio, Tableau, Qlik Sense, Metabase, Superset, Custom Iframe |
| `DASHBOARD_STATUS` | LIST_OF_VALUES | ANA | Draft, Published, Archived, Retired |
| `PARAM_TYPE` | LIST_OF_VALUES | ANA parameters | String, Number, Boolean, Date |
| `EXECUTION_STATUS` | LIST_OF_VALUES | ANA executions | Success, Failed, Cancelled, Timeout, Unauthorized |
| `PROCESS_TYPE` | LIST_OF_VALUES | PROC | Primary, Support *(Porter's value chain)* |
| `PROCESS_STATUS` | LIST_OF_VALUES | PROC | 1-Draft, 2-Review, 3-Published, 4-Deprecated |
| `PROJECT_STATUS` | LIST_OF_VALUES | COLLAB projects | Planned, In Progress, On Hold, Completed |
| `DIMENSIONS_UNIT` | LIST_OF_VALUES | COLLAB dimensions | Percentage, Units, Count, Hours, Days |
| `GENAI_DEV_ADOPTION`, `GENAI_QA_ADOPTION` | SCALE | COLLAB metrics | 5-level adoption scales (en/es) |

> Source of truth for these values is `db/sql/*.sql`. When a list changes there, update this
> table.
