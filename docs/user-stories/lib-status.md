# Status and Types for Lib Module

## HU-Propose Asset
When saving, request a reviewer (user with ADMINISTRATIVE role) and insert the following records:
- 1 record in assets table with status 'PROPOSED'
- N records in characterizations table for current asset, one for each feature in specifications table
- 1 record in actions table for current user with type 'PROPOSAL' and status 'FINISHED'
- 1 record in actions table for reviewer user (with ADMINISTRATIVE role) and type 'REVIEW' and status 'ASSIGNED'
- 1 record in asset_permissions table for current user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL
- 1 record in asset_permissions table for reviewer user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL

## HU-Asset Notifications
- List actions for current user grouping by asset with **last** status equal to 'ASSIGNED' (bold) or 'NOTIFIED' (not bold and remove option) with type 'REVIEW'/'MODIFICATION'/'PUBLICATION'/'REJECTION'
- When click on an action, show the corresponding user story ('HU-Asset Request Detail' for 'PUBLICATION'/'REJECTION' type, or 'HU-Review Asset Proposal' for 'REVIEW' type or 'HU-Modify Asset Proposal' for 'MODIFICATION' type)
- When click on remove option (actions with status 'NOTIFIED'), remove action from the list of notifications and insert a record for the corresponding action with status 'FINISHED'

## HU-My Asset Requests
- List actions for current user grouping by asset with status equal to 'ASSIGNED' (bold) or 'NOTIFIED' (no bold) or 'FINISHED' (gray) with type 'REVIEW'/'MODIFICATION'/'PUBLICATION'/'REJECTION'
- For each action with status 'FINISHED' or type 'PUBLICATION'/'REJECTION', show a button for 'HU-Asset Request Detail' 
- For each of the other actions, show a button for the corresponding user story 'HU-Review Asset Proposal' for 'REVIEW' type or 'HU-Modify Asset Proposal' for 'MODIFICATION' type

### HU-Review Asset Proposal
- Upon entering, if the action status is 'ASSIGNED', remove bold style in the list of notifications and insert the corresponding action with type 'REVIEW' and status 'NOTIFIED'
- When saving (feedback/approve/reject), insert the corresponding action with type 'REVIEW' and status 'FINISHED'
- When feedback/approve/reject, update the asset status to 'FEEDBACK'/'PUBLISHED'/'REJECTED' respectively
- When feedback/approve/reject, insert a new action for the proposer user with type 'MODIFICATION'/'PUBLICATION'/'REJECTION' respectively and status 'ASSIGNED'

### HU-Modify Asset Proposal
- Upon entering, if the action status is 'ASSIGNED', remove bold style in the list of notifications and insert the corresponding action with type 'MODIFICATION' and status 'NOTIFIED'
- When saving, remove action from the list of notifications and insert the corresponding action with type 'MODIFICATION' and status 'FINISHED'
- When saving, insert a new action for the reviewer user with type 'REVIEW' and status 'ASSIGNED'

### HU-Asset Request Detail
- Upon entering, if the action status is 'ASSIGNED', remove bold style in the list of notifications and insert the corresponding action with type 'PUBLICATION'/'REJECTION' and status 'NOTIFIED'
