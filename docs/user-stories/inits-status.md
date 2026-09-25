# Status and Types for Inits Module

> **Note.** Implemented by `specs/004-initiative-management` (Edit Initiative) and
> `specs/005-explore-initiatives` (Propose, Notifications, My Initiative Requests, Diagnosis,
> Modify, Acknowledgment). The workflow uses the two-state `WORKFLOW_STATUS` model
> (`PENDING` / `HANDLED`) that `lib` also uses, since both domains share the same list.

## HU-Propose Initiative
When saving, request a reviewer (same rule as Propose an asset: ADMINISTRATOR / ADMINISTRATIVE / REVIEWER or superuser; a non-admin proposer cannot review their own proposal; auto-assigned when none is chosen) and insert the following records in ONE transaction:
- 1 record in inits table with status 'ACTIVATED'
- 1 record in collaborations table for current user with type 'ACTIVATION' and status 'HANDLED'
- 1 record in collaborations table for reviewer user (with ADMINISTRATIVE role) and type 'DIAGNOSIS' and status 'PENDING'
- 1 record in init_permissions table for current user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL
- 1 record in init_permissions table for reviewer user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL
- 1 record in diagnostics per active criterion with the proposer's creator_score (and optional rationale)
- 1 record in asset_inits per related asset staged in the wizard

## HU-Initiative Notifications
- List, for the current user, only the collaborations still awaiting THEM: grouped by init, latest status 'PENDING', type 'DIAGNOSIS'/'MODIFICATION'/'ACCEPTANCE'/'REJECTION' ('DELIVERY' raises no notice — spec 004)
- Anything waiting on somebody else is excluded — it belongs on 'HU-My Initiative Requests', which this panel links to
- When click on an collaboration, show the corresponding user story ('HU-Diagnosis of the Initiative' for 'DIAGNOSIS' type, or 'HU-Modify Initiative' for 'MODIFICATION' type or 'Show Collab' for 'ACCEPTANCE'/'REJECTION' type),
- There is NO remove/dismiss option — an entry leaves this list by being resolved and by nothing else

## HU-My Initiative Requests
- List everything the current user has taken part in: collaborations directed at them AND initiatives they proposed ('ACTIVATION'), grouped by init
- **One entry per initiative**, never one per collaboration
- Split into two views: still in motion, and closed
- Each in-motion entry states whose action is awaited — the user's own, or somebody else's
- For each entry awaiting the user, show a button for the corresponding user story: 'HU-Diagnosis of the Initiative' for 'DIAGNOSIS' type, 'HU-Modify Initiative' for 'MODIFICATION' type, or an acknowledge action for 'ACCEPTANCE'/'REJECTION'

### HU-Diagnosis of the Initiative
- Upon entering, record NOTHING — viewing is not deciding, and the assignment stays 'PENDING' until an actual decision is made
- When saving (feedback/accept/reject), insert the corresponding collaboration with type 'DIAGNOSIS' and status 'HANDLED'
- When feedback/accept/reject, update the init status to 'FEEDBACK'/'ACCEPTED'/'REJECTED' respectively
- When feedback/accept/reject, insert a new collaboration for the creator user with type 'MODIFICATION'/'ACCEPTANCE'/'REJECTION' respectively and status 'PENDING'

### HU-Modify Initiative
- Upon entering, record NOTHING — viewing is not resubmitting, and the assignment stays 'PENDING' until the changes are sent back
- When saving, insert the corresponding collaboration with type 'MODIFICATION' and status 'HANDLED'
- When saving, insert a new collaboration for the reviewer user with type 'DIAGNOSIS' and status 'PENDING'

### HU-User Acknowledgment of Initiative Notification
- Upon entering, record NOTHING — reading is not acknowledging. The notice becomes 'HANDLED' only when the user explicitly acknowledges it

## HU-Edit Initiative (Include Delivery / Archiving)
> Implemented by `specs/004-initiative-management`.
- The status can only change ACCEPTED → IN_PROGRESS / DELIVERED / ARCHIVED, IN_PROGRESS → DELIVERED / ARCHIVED, and DELIVERED → ARCHIVED; every other change is refused (the propose / diagnose / modify workflow owns the rest)
- When saving with a new status, insert ONE collaboration for the current user in the same transaction: type 'KICKOFF' (→ IN_PROGRESS), 'DELIVERY' (→ DELIVERED) or 'ARCHIVING' (→ ARCHIVED), with status 'HANDLED'
- No pending notice is raised for the creator or anyone else — the change is visible in the initiative's History only (same as deprecation on the asset side)
