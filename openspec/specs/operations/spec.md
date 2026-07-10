# operations Specification

## Purpose
TBD - created by archiving change adopt-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Current spreadsheet import seeds the operational baseline
The system SHALL provide an import command that seeds the real manager list, contacts, initial counters, vacations/blocks, legacy historical assignments through 2026-05-31, fixed imported assignments through 2026-08-02, closed historical/fixed months, and future generated schedules.

The import SHALL replace placeholder Copel users with the provided real manager data.

#### Scenario: Import current spreadsheet data
- **GIVEN** the database is prepared for import
- **WHEN** the current spreadsheet import command runs
- **THEN** real manager records and contacts are present
- **AND** placeholder Copel manager records are no longer the active operational users

#### Scenario: Import generates future schedule
- **GIVEN** current manager and availability data are imported
- **WHEN** the import command completes
- **THEN** future schedules are generated using the post-2026-06-01 single-manager rule

### Requirement: Historical data remains auditable
The system SHALL record important changes and operational events in history or alerts, including generation attempts against closed months and manual schedule changes.

#### Scenario: Blocked closed-month generation
- **GIVEN** a user attempts to regenerate a closed month
- **WHEN** the operation is refused
- **THEN** an alert or history entry records the blocked attempt

#### Scenario: Manual schedule edit
- **GIVEN** an authenticated user changes a schedule day manually
- **WHEN** the change is saved
- **THEN** the change can be audited through recorded history

### Requirement: Test suite protects core rules
The project SHALL maintain automated tests for date rules, long-weekend detection, schedule generation, proportional distribution, vacation redistribution, UI terminology, CSV terminology, and default-user synchronization.

#### Scenario: Core test run
- **GIVEN** the project code is available locally
- **WHEN** the Django test suite runs
- **THEN** tests covering core scheduling and UI rules pass

### Requirement: Production domain boundaries are explicit
The Escala Gerencial application SHALL be operated on beta.daesung.com.br.

Deploys, web server aliases, reverse proxy settings, and static files for this project SHALL NOT replace or point daesung.com.br or www.daesung.com.br, because those domains belong to the separate Escala VIP system.

#### Scenario: Gerencial deploy
- **GIVEN** a deployment is prepared for this project
- **WHEN** domain or web server configuration is reviewed
- **THEN** the target domain is beta.daesung.com.br

#### Scenario: VIP domain protection
- **GIVEN** daesung.com.br or www.daesung.com.br is serving Escala VIP
- **WHEN** Escala Gerencial is deployed
- **THEN** those VIP domains remain mapped to Escala VIP and are not overwritten by Escala Gerencial

### Requirement: CIDIS 2026 import applies current roster and history
The system SHALL import the CIDIS 2026 spreadsheet baseline with only the active roster requested by the business.

The import SHALL keep Samuel Bitelo, Henry William, Jeziel, Pangartte, Juliano Mosko, Marcos Vinicius, Ronaldo Jr, Luiz Roberto, and Dionizio active. The import SHALL deactivate Gustavo Theodor, Jefferson Franco, and Marcelo.

#### Scenario: Former managers are excluded
- **GIVEN** Gustavo Theodor, Jefferson Franco, or Marcelo exist in the system
- **WHEN** the CIDIS 2026 import runs
- **THEN** those manager records are not active scheduling candidates

#### Scenario: Current managers are active
- **GIVEN** the CIDIS 2026 import runs
- **WHEN** users are synchronized
- **THEN** the 9 requested current managers are active with their lotacao and phone data from the spreadsheet

### Requirement: CIDIS 2026 import preserves elapsed history and recalculates future
The system SHALL treat spreadsheet work markings through `2026-08-02` as fixed imported assignments and SHALL recalculate future coverage from `2026-08-03` onward using the current single-manager rule.

Historical `S1` and `S2` markings before `2026-06-01` SHALL count as legacy historical work totals. Spreadsheet `S1` markings from `2026-06-01` through `2026-08-02` SHALL be imported as the single on-call role `S`.

#### Scenario: June and July fixed assignments
- **GIVEN** work markings exist in June and July 2026
- **WHEN** the CIDIS 2026 import runs
- **THEN** those fixed dates are preserved as single-manager manual assignments
- **AND** `s2` is empty for each imported fixed date

#### Scenario: August fixed weekend
- **GIVEN** work markings exist on `2026-08-01` and `2026-08-02`
- **WHEN** the CIDIS 2026 import runs
- **THEN** those two dates are preserved as imported manual assignments
- **AND** automatic generation starts on `2026-08-03`
