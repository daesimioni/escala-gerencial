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

