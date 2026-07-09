# availability-management Specification

## Purpose
TBD - created by archiving change adopt-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Active managers are the scheduling pool
The system SHALL schedule only active manager records. Each manager record SHALL store name, optional legacy code, location, phone, group, activity flag, initial historical counters, and a linked Django user when available.

#### Scenario: Inactive manager
- **GIVEN** a manager is marked inactive
- **WHEN** automatic generation selects candidates
- **THEN** that manager is not eligible for assignment

#### Scenario: Manager contact display
- **GIVEN** a manager has phone and location data
- **WHEN** the manager is listed in the system
- **THEN** the system can display the manager's operational contact information

### Requirement: Vacations and blocks make managers unavailable
The system SHALL support date-range blocks for vacations and other unavailability reasons. A manager with a block covering a date SHALL be unavailable for that date.

Adding, editing, or removing a block that affects future schedules SHALL trigger redistribution from the affected date while respecting closed months.

#### Scenario: Vacation overlaps assigned date
- **GIVEN** a manager is assigned on a future date
- **WHEN** an administrator adds vacation covering that date
- **THEN** the manager becomes unavailable for that date
- **AND** the future schedule is redistributed from the vacation start date

#### Scenario: Block removed
- **GIVEN** a manager had a future block
- **WHEN** the block is removed
- **THEN** future open months are eligible for redistribution using the manager's restored availability

### Requirement: Block impact is visible before or during changes
The system SHALL be able to analyze how a vacation or block affects existing assignments, including affected days, affected blocks, skipped closed months, and warnings when no other manager is available.

#### Scenario: Vacation has affected assignments
- **GIVEN** a vacation period overlaps existing assignments for the selected manager
- **WHEN** impact is analyzed
- **THEN** the system reports how many assigned days must be redistributed

#### Scenario: Vacation is inside a closed month
- **GIVEN** a vacation period overlaps a closed month
- **WHEN** impact is analyzed
- **THEN** the system reports that the closed month will not be changed automatically

### Requirement: Holidays include national, Parana, Curitiba, and custom records
The system SHALL consider fixed national holidays, Parana state holidays, Curitiba municipal holidays, movable holidays derived from Easter, and active custom holiday records.

Inactive custom holidays SHALL NOT require coverage.

#### Scenario: Active holiday
- **GIVEN** a date is an active holiday
- **WHEN** coverage blocks are calculated
- **THEN** the date requires one on-call manager

#### Scenario: Inactive custom holiday
- **GIVEN** a custom holiday exists but is inactive
- **WHEN** coverage blocks are calculated
- **THEN** that custom record does not make the date require coverage

### Requirement: Long weekends are detected as coverage blocks
The system SHALL identify consecutive runs that include at least one holiday and at least two consecutive coverage days as long weekends.

Long weekends SHALL be labeled separately from ordinary weekend blocks in summaries, reports, and dashboard coverage blocks.

#### Scenario: Friday holiday followed by weekend
- **GIVEN** a Friday holiday is followed by Saturday and Sunday
- **WHEN** coverage blocks are calculated
- **THEN** the three-day run is classified as a long weekend

#### Scenario: Ordinary Saturday and Sunday
- **GIVEN** Saturday and Sunday do not connect to a holiday
- **WHEN** coverage blocks are calculated
- **THEN** the two-day run is classified as an ordinary weekend block

