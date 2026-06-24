# Status and Types for Inits Module

## HU-Activate ()
When saving, request a reviewer (user with ADMINISTRATIVE role) and insert the following records:
- 1 record in inits table with status 'ACTIVATED'
- 1 record in collaborations table for current user with type 'ACTIVATION' and status 'FINISHED'
- 1 record in collaborations table for reviewer user (with ADMINISTRATIVE role) and type 'DIAGNOSIS' and status 'ASSIGNED'
- 1 record in init_permissions table for current user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL
- 1 record in init_permissions table for reviewer user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL

## HU-Notifications ()
- List collaborations for current user grouping by init with last status equal to 'ASSIGNED' (bold)
  or 'NOTIFIED' (not bold and remove option) with type 'DIAGNOSIS'/'ACCEPTANCE'/'REJECTION'/'DELIVERY'
- When click on an collaboration, show the corresponding user story ('HU-Diagnosis' for 'DIAGNOSIS' type,
  or 'Show Collab' for 'ACCEPTANCE'/'REJECTION'/'DELIVERY' type),
- When click on remove option (collaborations with status 'NOTIFIED'), remove collaboration from the list of notifications
  and insert a record for the corresponding collaboration with status 'FINISHED'

## HU-Diagnosis ()
- Upon entering, if the collaboration status is 'ASSIGNED', remove bold style in the list of notifications
  and insert the corresponding collaboration with type 'DIAGNOSIS' and status 'NOTIFIED'
- When saving (accept/reject), insert the corresponding collaboration with type 'DIAGNOSIS' and status 'FINISHED'
- When accept/reject, update the init status to 'ACCEPTED'/'REJECTED' respectively
- When accept/reject, insert a new collaboration for the proposer user
  with type 'ACCEPTANCE'/'REJECTION' respectively and status 'ASSIGNED'

## HU-Show Collab ()
- Upon entering, if the collaboration status is 'ASSIGNED', remove bold style in the list of notifications
  and insert the corresponding collaboration with type 'ACCEPTANCE'/'REJECTION'/'DELIVERY' and status 'NOTIFIED'

## HU-Delivery ()
- When saving, insert a new collaboration for the proposer user with type 'DELIVERY' and status 'ASSIGNED'
