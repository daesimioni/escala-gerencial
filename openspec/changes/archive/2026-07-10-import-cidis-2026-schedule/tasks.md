## 1. Data Extraction

- [x] 1.1 Inspect the attached workbook, HTML and PDF references.
- [x] 1.2 Extract the valid CIDIS 2026 roster.
- [x] 1.3 Extract vacation ranges and historical work markings through 2026-07-09.

## 2. Implementation

- [x] 2.1 Add vacation weekend buffer synchronization.
- [x] 2.2 Apply buffer synchronization from block create/edit/delete flows.
- [x] 2.3 Update the current spreadsheet import command with CIDIS 2026 roster, vacations, exclusions and history.
- [x] 2.4 Add tests for vacation buffers and CIDIS import behavior.
- [x] 2.5 Update documentation and changelog.

## 3. Validation And Release

- [x] 3.1 Validate OpenSpec change.
- [x] 3.2 Run Django checks and tests locally.
- [x] 3.3 Run the import command locally and validate generated schedule.
- [x] 3.4 Commit and push to GitHub.
- [x] 3.5 Deploy to beta.daesung.com.br.
- [x] 3.6 Back up production database and run the import command remotely.
- [x] 3.7 Validate production pages and archive the OpenSpec change.
