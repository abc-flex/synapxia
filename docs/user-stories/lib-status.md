# Status and Types for Lib Module

## HU-Propose ()
When saving, request a reviewer (user with ADMINISTRATIVE role) and insert the following records:
- 1 record in assets table with status 'PROPOSED'
- N records in characterizations table for current asset, one for each feature in specifications table
- 1 record in actions table for current user with type 'PROPOSAL' and status 'FINISHED'
- 1 record in actions table for reviewer user (with ADMINISTRATIVE role) and type 'REVIEW' and status 'ASSIGNED'
- 1 record in asset_permissions table for current user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL
- 1 record in asset_permissions table for reviewer user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL

## HU-Notifications ()
- List actions for current user grouping by asset with last status equal to 'ASSIGNED' (bold) or 'NOTIFIED' (not bold and remove option)
  with type 'REVIEW'/'MODIFICATION'/'PUBLICATION'/'REJECTION'/'QUESTIONS'/'ANSWER'
- When click on an action, show the corresponding user story ('HU-Show Action' for 'PUBLICATION'/'REJECTION'/'ANSWER' type,
  and 'HU-Review'/'HU-Modify'/'HU-Reply' for 'REVIEW'/'MODIFICATION'/'QUESTIONS' type respectively),
  if action status is 'ASSIGNED', insert a record for the corresponding action with status 'NOTIFIED'
- When click on remove option (actions with status 'NOTIFIED'), insert a record for the corresponding action with status 'FINISHED'

## HU-Review ()
- When saving (feedback/approve/reject), insert the corresponding action with type 'REVIEW' and status 'FINISHED'
- When feedback/approve/reject, update the asset status to 'FEEDBACK'/'PUBLISHED'/'REJECTED' respectively
- When feedback/approve/reject, insert a new action for the proposer user
  with type 'MODIFICATION'/'PUBLICATION'/'REJECTION' respectively and status 'ASSIGNED'

## HU-Show Action ()
- Upon entering, if the action status is 'ASSIGNED', remove bold style in the list of notifications
  and insert the corresponding action with type 'PUBLICATION'/'REJECTION'/'ANSWER' and status 'NOTIFIED'

## HU-Modify ()
- When saving, insert the corresponding action with type 'MODIFICATION' and status 'FINISHED'
- When saving, insert a new action for the reviewer user with type 'REVIEW' and status 'ASSIGNED'

## HU-Reply ()
- When saving, insert the corresponding action with type 'QUESTIONS' and status 'FINISHED'
- When saving, insert a new action for the respondent user with type 'ANSWER' and status 'ASSIGNED'
