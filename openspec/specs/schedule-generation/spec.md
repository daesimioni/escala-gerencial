# schedule-generation Specification

## Purpose
TBD - created by archiving change adopt-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Required coverage dates have one on-call manager
The system SHALL generate coverage from 2026-06-01 onward with exactly one manager assigned to the `s1` slot for each required coverage date and no manager assigned to `s2`.

Required coverage dates SHALL include weekends, active holidays, and long-weekend days. The generated assignment SHALL represent on-call coverage only, not on-site presence.

#### Scenario: Weekend coverage after cutoff
- **GIVEN** an active future month after 2026-06-01 has a Saturday and Sunday
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
The system SHALL preserve the imported legacy historical period from 2026-01-01 through 2026-05-31 and apply the new single-manager rule from 2026-06-01 onward.

Historical S1/S2 markers MAY exist only as imported legacy history and SHALL NOT be used as the operational model from June 2026 onward.

#### Scenario: Regeneration starts after fixed import window
- **GIVEN** schedules exist for imported fixed dates through `2026-08-02`
- **WHEN** future schedules are regenerated after CIDIS import
- **THEN** imported entries before `2026-08-03` are not rewritten by automatic generation

#### Scenario: Future schedule display
- **GIVEN** a schedule date is on or after `2026-06-01`
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

### Requirement: Future redistribution starts after imported fixed assignments
When the CIDIS 2026 import is applied, the system SHALL regenerate future assignments starting on `2026-08-03` while preserving imported fixed assignments through `2026-08-02`.

The generated remainder of 2026 SHALL continue to prevent consecutive assignments and balance workload proportionally to availability.

#### Scenario: Import regenerates after fixed assignments
- **GIVEN** the CIDIS 2026 import has loaded fixed assignments through `2026-08-02`
- **WHEN** future generation runs
- **THEN** automatic assignments before `2026-08-03` remain unchanged
- **AND** required coverage dates from `2026-08-03` onward are generated by the current algorithm

#### Scenario: Remainder of year remains balanced
- **GIVEN** all current managers and vacations from the CIDIS 2026 import are available to the generator
- **WHEN** the remainder of 2026 is generated
- **THEN** the resulting schedule has no same-manager consecutive days
- **AND** no active manager is assigned while on vacation or vacation buffer
