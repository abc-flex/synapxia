# Status and Types for Lib Module

## HU-Propose Asset
When saving, request a reviewer (user with ADMINISTRATIVE role) and insert the following records:
- 1 record in assets table with status 'PROPOSED'
- N records in characterizations table for current asset, one for each feature in specifications table
- 1 record in actions table for current user with type 'PROPOSAL' and status 'HANDLED'
- 1 record in actions table for reviewer user (with ADMINISTRATIVE role) and type 'REVIEW' and status 'PENDING'
- 1 record in asset_permissions table for current user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL
- 1 record in asset_permissions table for reviewer user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL

## HU-Asset Notifications
- List, for the current user, only the actions still awaiting THEM: grouped by asset, latest status 'PENDING', type 'REVIEW'/'MODIFICATION'/'PUBLICATION'/'REJECTION'
- Anything waiting on somebody else (an asset the user proposed, say) is deliberately excluded — nothing is being asked of them, so it belongs on 'HU-My Asset Requests', which this panel links to
- Cap the panel at 5 entries and report the outstanding total so it can show that more exist
- When click on an action, show the corresponding user story ('HU-User Acknowledgment of Asset Notification' for 'PUBLICATION'/'REJECTION' type, or 'HU-Review Asset Proposal' for 'REVIEW' type or 'HU-Modify Asset Proposal' for 'MODIFICATION' type)
- There is NO remove/dismiss option. An entry leaves this list by being resolved and by nothing else — the old remove inserted the same terminal row that means "already decided", which silently revoked the assignee's turn

## HU-My Asset Requests
- List everything the current user has taken part in: actions directed at them ('REVIEW'/'MODIFICATION'/'PUBLICATION'/'REJECTION') AND assets they proposed ('PROPOSAL'), grouped by asset
- **One entry per asset**, never one per action — an asset the user proposed and whose outcome they later acknowledged must appear once, not twice
- Split into two views: still in motion, and closed
- Each in-motion entry states whose action is awaited — the user's own, or somebody else's. 'PENDING' describes the request, not an obligation on the viewer
- For each entry awaiting the user, show a button for the corresponding user story: 'HU-Review Asset Proposal' for 'REVIEW' type, 'HU-Modify Asset Proposal' for 'MODIFICATION' type, or an acknowledge action for 'PUBLICATION'/'REJECTION'

### HU-Review Asset Proposal
- Upon entering, record NOTHING — viewing is not deciding, and the assignment stays 'PENDING' until an actual decision is made
- When saving (feedback/approve/reject), insert the corresponding action with type 'REVIEW' and status 'HANDLED'
- When feedback/approve/reject, update the asset status to 'FEEDBACK'/'PUBLISHED'/'REJECTED' respectively
- When feedback/approve/reject, insert a new action for the proposer user with type 'MODIFICATION'/'PUBLICATION'/'REJECTION' respectively and status 'PENDING'
- After deciding, return the reviewer to 'HU-My Asset Requests' so they see the item they just resolved

### HU-Modify Asset Proposal
- Upon entering, record NOTHING — viewing is not resubmitting, and the assignment stays 'PENDING' until the changes are sent back
- When saving, insert the corresponding action with type 'MODIFICATION' and status 'HANDLED'
- When saving, insert a new action for the reviewer user with type 'REVIEW' and status 'PENDING'

### HU-User Acknowledgment of Asset Notification
- Upon entering, record NOTHING — reading is not acknowledging
- The notice becomes 'HANDLED' only when the user explicitly acknowledges it, so an outcome can never pass unregistered. The cost is that a user who ignores notices keeps a lit indicator; acknowledgement is therefore a single click, offered on the requests list as well as here
