## Design

### Import Cutoffs
The system keeps the operational cutoff in `DATA_CORTE_HISTORICO`, changing it to `2026-06-01`.

Imported workload before that cutoff is folded into `pl_inicial` and `oportunidades_iniciais`. Imported assignments on and after the cutoff are stored as single-manager `EscalaDia` rows with `s2 = NULL`, marked manual so automatic generation preserves them.

The import command preserves CIDIS entries through `2026-08-02` and regenerates from `2026-08-03`.

### Swap Requests
Add `SolicitacaoTroca` with:
- origin schedule date and current origin manager;
- destination schedule date and current destination manager;
- requesting user/manager;
- status;
- destination/admin response metadata.

Approval applies an atomic swap only if both schedule rows still match the stored managers and both resulting assignments satisfy availability and adjacent-day rules. The swap marks both affected dates manual and writes history.

### Authorization
Staff users can edit schedules, vacations/blocks, holidays, long weekends, and generation directly.

Standard manager users can read operational pages and submit/respond to trade requests linked to their own manager record.
