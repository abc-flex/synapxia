# Status and Types for Inits Module

## HU-Propose Initiative
When saving, request a reviewer (user with ADMINISTRATIVE role) and insert the following records:
- 1 record in inits table with status 'ACTIVATED'
- 1 record in collaborations table for current user with type 'ACTIVATION' and status 'FINISHED'
- 1 record in collaborations table for reviewer user (with ADMINISTRATIVE role) and type 'DIAGNOSIS' and status 'ASSIGNED'
- 1 record in init_permissions table for current user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL
- 1 record in init_permissions table for reviewer user with access_level 'MANAGE' and valid_from = now() AND valid_to = NULL

## HU-Initiative Notifications
- List collaborations for current user grouping by init with **last** status equal to 'ASSIGNED' (bold) or 'NOTIFIED' (not bold and remove option) with type 'DIAGNOSIS'/'MODIFICATION'/'ACCEPTANCE'/'REJECTION'/'DELIVERY'
- When click on an collaboration, show the corresponding user story ('HU-Diagnosis of the Initiative' for 'DIAGNOSIS' type, or 'HU-Modify Initiative' for 'MODIFICATION' type or 'Show Collab' for 'ACCEPTANCE'/'REJECTION'/'DELIVERY' type),
- When click on remove option (collaborations with status 'NOTIFIED'), remove collaboration from the list of notifications and insert a record for the corresponding collaboration with status 'FINISHED'

## HU-My Initiative Requests
- List collaborations for current user grouping by init with status equal to 'ASSIGNED' (bold) or 'NOTIFIED' (no bold) or 'FINISHED' (gray) with type 'DIAGNOSIS'/'MODIFICATION'/'ACCEPTANCE'/'REJECTION'/'DELIVERY'
- For each collaborations with status 'FINISHED' or type 'PUBLICATION'/'REJECTION'/'DELIVERY', show a button for 'HU-Initiative Request Detail' 
- For each of the other collaborations, show a button for the corresponding user story 'HU-Diagnosis of the Initiative' for 'DIAGNOSIS' type or 'HU-Modify Initiative' for 'MODIFICATION' type

### HU-Diagnosis of the Initiative
- Upon entering, if the collaboration status is 'ASSIGNED', remove bold style in the list of notifications and insert the corresponding collaboration with type 'DIAGNOSIS' and status 'NOTIFIED'
- When saving (feedback/accept/reject), insert the corresponding collaboration with type 'DIAGNOSIS' and status 'FINISHED'
- When feedback/accept/reject, update the init status to 'FEEDBACK'/'ACCEPTED'/'REJECTED' respectively
- When feedback/accept/reject, insert a new collaboration for the creator user with type 'MODIFICATION'/'ACCEPTANCE'/'REJECTION' respectively and status 'ASSIGNED'

### HU-Modify Initiative
- Upon entering, if the collaboration status is 'ASSIGNED', remove bold style in the list of notifications and insert the corresponding collaboration with type 'MODIFICATION' and status 'NOTIFIED'
- When saving, remove collaboration from the list of notifications and insert the corresponding collaboration with type 'MODIFICATION' and status 'FINISHED'
- When saving, insert a new collaboration for the reviewer user with type 'REVIEW' and status 'ASSIGNED'

### HU-Initiative Request Detail
- Upon entering, if the collaboration status is 'ASSIGNED', remove bold style in the list of notifications and insert the corresponding collaboration with type 'ACCEPTANCE'/'REJECTION'/'DELIVERY' and status 'NOTIFIED'

## HU-Edit Initiative (Include Delivery / Archiving)
- When saving and including status = 'DELIVERED', insert a new collaboration for the creator user with type 'DELIVERY' and status 'ASSIGNED'
