# user-interface Specification

## Purpose
TBD - created by archiving change adopt-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Dashboard summarizes current status and upcoming coverage
The dashboard SHALL show high-level counts, the current date, a mini calendar for the current month, upcoming schedule entries, upcoming coverage blocks, closed months, quick actions, and a legend.

The mini calendar SHALL distinguish days with scheduled coverage and SHALL expose the assigned manager name on hover or equivalent accessible interaction.

#### Scenario: Current month mini calendar
- **GIVEN** the dashboard is opened
- **WHEN** the current month has future schedule entries
- **THEN** the mini calendar marks those dates differently from unscheduled dates
- **AND** the assigned manager name is available for each scheduled date

#### Scenario: Upcoming schedule list
- **GIVEN** future schedule entries exist
- **WHEN** the dashboard is opened
- **THEN** the dashboard lists upcoming assignments below or near the mini calendar

### Requirement: Calendar views show a single on-call manager
The monthly and annual calendar views SHALL present future schedule entries as a single on-call manager per date.

The UI SHALL NOT present future entries as two daily managers or as S1/S2 operational roles.

#### Scenario: Monthly calendar after cutoff
- **GIVEN** a generated date after 2026-06-01 has one manager assigned
- **WHEN** the user opens the monthly calendar
- **THEN** the date shows one on-call manager only

#### Scenario: Annual view after cutoff
- **GIVEN** annual schedule data exists after 2026-06-01
- **WHEN** the user opens the annual view
- **THEN** each scheduled future date represents one on-call assignment

### Requirement: UI language matches sobreaviso rule
Visible future-facing labels SHALL use on-call/sobreaviso terminology and SHALL NOT imply on-site presencial coverage for weekends, holidays, or long weekends.

#### Scenario: Weekend label
- **GIVEN** a weekend assignment exists
- **WHEN** it is displayed in the user interface
- **THEN** the label communicates sobreaviso/on-call coverage
- **AND** it does not communicate presencial coverage

#### Scenario: Legend
- **GIVEN** a user views a calendar legend
- **WHEN** future schedule colors are explained
- **THEN** the legend includes sobreaviso and availability states relevant to the current rule

### Requirement: Reports explain distribution and availability
The reports view SHALL show workload distribution, coverage counts, availability effects, vacation/block days, weekend/holiday/long-weekend counts, and visual charts that help explain fairness.

#### Scenario: Report includes vacation impact
- **GIVEN** a manager has vacation days in the reporting period
- **WHEN** the report is generated
- **THEN** the manager's vacation days are shown separately from assigned on-call days

#### Scenario: Report charts load
- **GIVEN** report data exists
- **WHEN** the user opens the reports page
- **THEN** charts render with the workload and coverage summaries

### Requirement: Exports use current terminology
CSV exports SHALL use current single-manager sobreaviso terminology for future schedules and SHALL avoid future S1/S2 role labels.

#### Scenario: Export future month
- **GIVEN** a future month is exported
- **WHEN** the CSV is generated
- **THEN** each scheduled date contains a single on-call manager field
- **AND** no future S1/S2 operational column is required

### Requirement: Swap request page guides manager acceptance and admin approval
The swap page SHALL let a manager choose one of their own assigned dates, choose another manager, choose one of that manager's assigned dates, and submit the request.

The page SHALL show pending requests awaiting the current user's response and, for administrators, requests awaiting approval.

#### Scenario: Manager sees destination dates
- **GIVEN** a manager is creating a swap request
- **WHEN** the manager selects another manager
- **THEN** the page offers that manager's assigned future dates as possible swap targets

#### Scenario: Admin sees approval queue
- **GIVEN** a staff administrator opens the swap page
- **WHEN** there are requests accepted by destination managers
- **THEN** the page lists them with approve and reject actions
