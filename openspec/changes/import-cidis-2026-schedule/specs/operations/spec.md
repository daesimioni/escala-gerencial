## ADDED Requirements

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
The system SHALL treat spreadsheet work markings through `2026-07-09` as elapsed history and SHALL recalculate future coverage from `2026-07-10` onward using the current single-manager rule.

Historical `S1` and `S2` markings before `2026-07-01` SHALL count as historical work totals. Future spreadsheet `S1` and `S2` markings after `2026-07-09` SHALL NOT be kept as operational assignments.

#### Scenario: July elapsed history
- **GIVEN** work markings exist on `2026-07-04` and `2026-07-05`
- **WHEN** the CIDIS 2026 import runs
- **THEN** those elapsed dates are preserved as imported history

#### Scenario: Future S1/S2 discarded
- **GIVEN** the spreadsheet has S1 or S2 markings after `2026-07-09`
- **WHEN** the CIDIS 2026 import runs
- **THEN** those future markings are ignored for assignment
- **AND** the generated schedule contains only one on-call manager per required future date
