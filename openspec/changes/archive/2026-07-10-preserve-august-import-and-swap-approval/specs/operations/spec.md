## MODIFIED Requirements
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
