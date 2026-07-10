# access-control Specification

## Purpose
TBD - created by archiving change adopt-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Users must authenticate before accessing the system
The system SHALL require authentication for the dashboard, calendar, annual view, manager management, vacations, holidays, long weekends, reports, generation, swaps, export, and administration pages.

#### Scenario: Anonymous page request
- **GIVEN** a visitor is not authenticated
- **WHEN** the visitor requests a protected system page
- **THEN** the system requires login before showing operational data

#### Scenario: Authenticated page request
- **GIVEN** a user is authenticated
- **WHEN** the user requests a protected page permitted to that user type
- **THEN** the system displays the requested page

### Requirement: Administrator account is retained
The system SHALL retain an administrative user capable of managing the system and staff-only operations.

Staff-only operations SHALL include closing and reopening months.

#### Scenario: Staff user closes month
- **GIVEN** an authenticated staff administrator
- **WHEN** the administrator closes an open month
- **THEN** the month becomes protected against automatic regeneration

#### Scenario: Standard user attempts staff operation
- **GIVEN** an authenticated non-staff user
- **WHEN** the user attempts a staff-only month operation
- **THEN** the system denies the operation

### Requirement: Standard users exist for each manager
The system SHALL support creating and synchronizing one standard Django user for each active manager while preserving the administrator user.

Standard manager users SHALL NOT receive staff or superuser privileges by default.

#### Scenario: Missing manager login
- **GIVEN** an active manager has no linked Django user
- **WHEN** the default-user synchronization command runs
- **THEN** the system creates a standard login for that manager
- **AND** links the login to the manager record

#### Scenario: Existing administrator
- **GIVEN** the administrator user already exists
- **WHEN** standard manager users are synchronized
- **THEN** the administrator remains available and is not downgraded

### Requirement: Standard managers request swaps instead of directly editing schedules
The system SHALL allow standard manager users to request a swap involving one of their own on-call dates and one date assigned to another active manager.

The requested destination manager SHALL accept or reject the request before it can be reviewed by an administrator. The schedule SHALL change only after administrator approval.

#### Scenario: Manager submits swap request
- **GIVEN** manager A is assigned to one date and manager B is assigned to another date
- **WHEN** manager A requests a swap with manager B's date
- **THEN** a pending request is created
- **AND** the schedule itself is not changed yet

#### Scenario: Destination accepts then admin approves
- **GIVEN** a swap request is pending destination response
- **WHEN** the destination manager accepts and an administrator approves
- **THEN** the two schedule dates are swapped
- **AND** the changed dates are marked manual and auditable

#### Scenario: Request rejected
- **GIVEN** a swap request is pending destination or admin response
- **WHEN** the destination manager or administrator rejects it
- **THEN** the request status records the rejection
- **AND** the schedule remains unchanged

### Requirement: Direct operational mutations are staff-only
The system SHALL reserve direct schedule edits, schedule clearing, vacation/block changes, holiday changes, long-weekend changes, month locking, and automatic generation for staff administrators.

#### Scenario: Standard manager attempts direct mutation
- **GIVEN** a standard authenticated manager
- **WHEN** the manager requests a direct mutation endpoint
- **THEN** the system denies the operation

#### Scenario: Staff administrator mutates schedule or availability
- **GIVEN** an authenticated staff administrator
- **WHEN** the administrator edits vacation, blocks, or a schedule day
- **THEN** the operation is allowed subject to business validations

