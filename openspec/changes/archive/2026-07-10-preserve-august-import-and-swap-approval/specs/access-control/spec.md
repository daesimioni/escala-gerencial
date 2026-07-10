## ADDED Requirements
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
