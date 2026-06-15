# Appendix — State Machines & Type Catalogs

Reference for the lifecycle **states** and classification **types** that the Library,
Initiatives and Process stories rely on, as seeded in the database (`lists` / `list_items`,
see [`db/sql/`](../../db/sql)).

---

## As seeded in the database

Key catalogs (English labels are the seeded values; some lists are bilingual en/es):

| List code | Type | Used by | Values |
|-----------|------|---------|--------|
| `ASSET_STATUS` | LIST_OF_VALUES | LIB assets | 1-Proposed, 2-Feedback Provided, 3-Published, 4-Rejected, 5-Deprecated, 6-In Use |
| `ACTION_TYPE` | LIST_OF_VALUES | LIB actions (review, vote, comment, …) | Proposal, Review, Modification, Publication, Rejection, Deprecation, Versioning, Usage, Vote, Comment, Question, Answer, Request |
| `RELATION_TYPE` | LIST_OF_VALUES | LIB / INITS / PROC relations | Depends On, Related To, Similar To, Part Of, Used By, Extends, Contains, Inspired By |
| `TARGET_TYPE` | LIST_OF_VALUES | permissions (all modules) | User, Role, Project, Team, Unit, Public |
| `ACCESS_LEVEL` | LIST_OF_VALUES | permissions (all modules) | View, Manage |
| `FEAT_TYPE` | LIST_OF_VALUES | TAXO features | General, Technical, Commercial, Usability, Documentation |
| `INITIATIVE_STATUS` | LIST_OF_VALUES | INITS | 1-Activated, 2-Assessment, 3-Engaging, 4-Delivered, 5-Evolving |
| `EXPECTED_IMPACT` | LIST_OF_VALUES | INITS | Time Reduction, Quality Improvement, Error Reduction, Decision Support, Improved UX, Cost Savings, Revenue Increase, Compliance Enhancement, Risk Reduction, Scalability Improvement, Innovation, Other |
| `PRIORITY_LEVEL` | LIST_OF_VALUES | INITS | High, Medium, Low |
| `COLLAB_TYPE` | LIST_OF_VALUES | INITS collaborations | Activation, Assessment, Exploration, Prototyping, Implementation, Enablement, Improvement, Refactoring, Expansion, Versioning, Deprecation |
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
