## Why
The CIDIS spreadsheet baseline was clarified: S1/S2 was only valid through May 2026. From June 2026 onward the spreadsheet S1 markings represent the single on-call role. June, July, and August 1-2 already have approved assignments and must remain unchanged; automatic redistribution starts after those dates.

Managers also need a controlled trade workflow. A manager can request a swap with another manager's scheduled date, the destination manager must accept, and an administrator must approve before the schedule changes.

## What Changes
- Treat S1/S2 as legacy history only through 2026-05-31.
- Preserve imported single on-call assignments from 2026-06-01 through 2026-08-02.
- Regenerate future automatic assignments from 2026-08-03 onward.
- Add a swap request workflow with destination acceptance and administrator approval.
- Restrict direct vacation, schedule, holiday, and generation mutations to administrators while standard managers use the request workflow.

## Impact
- A database migration adds swap request records.
- The import command will rewrite the CIDIS 2026 baseline using the clarified cutoff.
- Production requires running migrations and the CIDIS import command again.
