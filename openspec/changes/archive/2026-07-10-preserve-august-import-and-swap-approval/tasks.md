## 1. Import Rules
- [x] Update historical cutoff constants and documentation.
- [x] Extend CIDIS imported single on-call assignments through 2026-08-02.
- [x] Regenerate automatic future coverage from 2026-08-03.
- [x] Add tests for preserved June/July/August assignments.

## 2. Swap Workflow
- [x] Add swap request model, migration, and admin registration.
- [x] Add forms, views, URLs, and responsive template for request/accept/admin approval.
- [x] Add swap validation and application service.
- [x] Restrict direct mutation pages to staff.
- [x] Add workflow tests.

## 3. Validation And Release
- [x] Run Django checks, migrations, tests, import command, and data validation locally.
- [x] Update docs/changelog.
- [x] Validate OpenSpec, archive the completed change, commit, push, and deploy to beta.
