## ADDED Requirements

### Requirement: Vacation weekend buffers make adjacent weekends unavailable
The system SHALL automatically make a manager unavailable on Saturday or Sunday dates that fall within the 2 calendar days immediately before a vacation starts or within the 2 calendar days immediately after a vacation ends.

These buffer dates SHALL reduce scheduling opportunities in the same way as other blocks and SHALL NOT create later compensation debt.

#### Scenario: Weekend before vacation
- **GIVEN** a manager has vacation starting on a Monday
- **WHEN** vacation buffers are synchronized
- **THEN** the immediately preceding Saturday and Sunday are blocked for that manager
- **AND** the manager is not eligible for on-call assignment on those dates

#### Scenario: Weekend after vacation
- **GIVEN** a manager has vacation ending on a Friday
- **WHEN** vacation buffers are synchronized
- **THEN** the immediately following Saturday and Sunday are blocked for that manager
- **AND** the manager is not eligible for on-call assignment on those dates

#### Scenario: Non-weekend adjacent dates
- **GIVEN** one of the 2 adjacent dates is a weekday
- **WHEN** vacation buffers are synchronized
- **THEN** that weekday is not added as an automatic vacation buffer
