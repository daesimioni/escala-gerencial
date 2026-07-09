## ADDED Requirements

### Requirement: Required coverage dates have one on-call manager
The system SHALL generate coverage from 2026-07-01 onward with exactly one manager assigned to the `s1` slot for each required coverage date and no manager assigned to `s2`.

Required coverage dates SHALL include weekends, active holidays, and long-weekend days. The generated assignment SHALL represent on-call coverage only, not on-site presence.

#### Scenario: Weekend coverage after cutoff
- **GIVEN** an active future month after 2026-07-01 has a Saturday and Sunday
- **WHEN** the monthly schedule is generated
- **THEN** each weekend date has exactly one on-call manager in `s1`
- **AND** `s2` remains empty for each generated date

#### Scenario: Ordinary business day without coverage need
- **GIVEN** a weekday is not an active holiday and is not part of a long weekend
- **WHEN** the monthly schedule is generated
- **THEN** the system does not create an automatic schedule entry for that date

### Requirement: Consecutive assignments are prevented
The system SHALL prevent the same active manager from being assigned on adjacent calendar dates during automatic generation.

If no eligible manager can satisfy availability and adjacency constraints, the system SHALL report an error for the affected coverage block instead of assigning an invalid manager silently.

#### Scenario: Candidate worked yesterday
- **GIVEN** a manager is already assigned on the previous calendar date
- **WHEN** the generator chooses a manager for the current date
- **THEN** that manager is excluded from candidates for the current date

#### Scenario: No valid candidate exists
- **GIVEN** every active manager is unavailable or would violate adjacent-date assignment
- **WHEN** the generator processes a coverage date
- **THEN** the generator returns an error identifying the block without assigning a blocked or consecutive manager

### Requirement: Workload distribution is proportional to availability
The system SHALL distribute future on-call work by comparing each manager's assigned on-call days against that manager's available opportunities.

Vacation and block days SHALL reduce opportunities instead of creating later compensation debt for the manager.

#### Scenario: Manager has vacation days
- **GIVEN** one manager has vacation during part of the scheduling period
- **WHEN** the generator balances future assignments
- **THEN** the vacation days are excluded from that manager's opportunity count
- **AND** the manager is not overloaded after vacation only to match raw assignment totals

#### Scenario: Multiple candidates are available
- **GIVEN** several managers are eligible for a coverage date
- **WHEN** the generator ranks candidates
- **THEN** the manager with the better relative workload score is preferred, with deterministic tie-breaking by name and id

### Requirement: Historical months remain protected
The system SHALL preserve the imported historical period from 2026-01-01 through 2026-06-30 and apply the new single-manager rule only from 2026-07-01 onward.

Historical S1/S2 markers MAY exist only as imported history and SHALL NOT be used as the future operational model.

#### Scenario: Regeneration starts after cutoff
- **GIVEN** schedules exist for dates before 2026-07-01
- **WHEN** future schedules are regenerated
- **THEN** historical entries before 2026-07-01 are not rewritten by the future generation rule

#### Scenario: Future schedule display
- **GIVEN** a schedule date is on or after 2026-07-01
- **WHEN** the date is displayed or exported
- **THEN** the system presents a single on-call manager rather than S1/S2 operational roles

### Requirement: Month locks prevent automatic modification
The system SHALL prevent automatic schedule changes in closed months unless an explicit forced administrative operation is used.

When a regeneration request spans closed months, the system SHALL skip those months and record an alert or warning.

#### Scenario: Closed month regeneration
- **GIVEN** a month is marked closed
- **WHEN** automatic monthly generation runs without force
- **THEN** the system leaves that month unchanged
- **AND** the operation reports that the month is closed

#### Scenario: Period regeneration crosses closed month
- **GIVEN** a regeneration period includes both closed and open months
- **WHEN** the period regeneration runs
- **THEN** closed months are skipped
- **AND** open months continue to be processed

### Requirement: Manual assignments are preserved by default
The system SHALL preserve manually edited schedule entries during automatic generation unless the operation explicitly chooses not to preserve them.

Regeneration from a specific date inside a month SHALL only remove automatic assignments on or after that date, preserving earlier published dates in the same month.

#### Scenario: Manual date inside regenerated month
- **GIVEN** a manager was manually assigned to a future coverage date
- **WHEN** the monthly generator runs with manual preservation enabled
- **THEN** that manually assigned date remains unchanged

#### Scenario: Mid-month redistribution
- **GIVEN** a vacation is added starting in the middle of an open month
- **WHEN** the system regenerates after the vacation start date
- **THEN** automatic assignments before the start date remain unchanged
- **AND** automatic assignments on or after the start date are recalculated
