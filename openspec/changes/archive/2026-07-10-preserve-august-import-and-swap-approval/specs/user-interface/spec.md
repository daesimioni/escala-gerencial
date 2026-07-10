## ADDED Requirements
### Requirement: Swap request page guides manager acceptance and admin approval
The swap page SHALL let a manager choose one of their own assigned dates, choose another manager, choose one of that manager's assigned dates, and submit the request.

The page SHALL show pending requests awaiting the current user's response and, for administrators, requests awaiting approval.

#### Scenario: Manager sees destination dates
- **GIVEN** a manager is creating a swap request
- **WHEN** the manager selects another manager
- **THEN** the page offers that manager's assigned future dates as possible swap targets

#### Scenario: Admin sees approval queue
- **GIVEN** a staff administrator opens the swap page
- **WHEN** there are requests accepted by destination managers
- **THEN** the page lists them with approve and reject actions
