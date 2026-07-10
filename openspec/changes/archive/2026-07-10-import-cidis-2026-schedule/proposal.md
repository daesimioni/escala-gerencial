## Why

A planilha CIDIS 2026 recebida passa a ser a referencia mais atual para historico, ferias e redistribuicao da escala gerencial. O sistema precisa importar essa base, remover ex-gerentes da COPEL e aplicar a nova regra de bloqueio dos fins de semana imediatamente adjacentes as ferias.

## What Changes

- Importar os 9 gerentes validos da planilha CIDIS 2026 e desativar Gustavo Theodor, Jefferson Franco e Marcelo.
- Considerar as marcacoes `S1` e `S2` apenas como historico de trabalho ate a data atual da importacao.
- Gerar a escala futura usando apenas um gerente de sobreaviso por dia.
- Criar bloqueios automaticos para sabados/domingos nos 2 dias anteriores ao inicio das ferias e nos 2 dias posteriores ao fim das ferias.
- Redistribuir o restante de 2026 a partir de `2026-07-10`.
- Manter o dominio correto de producao em `beta.daesung.com.br`.

## Capabilities

### New Capabilities

- Nenhuma capacidade nova. A mudanca amplia capacidades existentes.

### Modified Capabilities

- `availability-management`: ferias passam a gerar bloqueios automaticos de fim de semana adjacente.
- `operations`: importacao da planilha atual passa a usar a base CIDIS 2026, excluir ex-gerentes e preservar historico ate `2026-07-09`.
- `schedule-generation`: redistribuicao futura passa a iniciar apos o historico ja ocorrido em julho/2026.

## Impact

- `escalas/services.py`: regra de buffer de ferias.
- `escalas/views.py`: sincronizacao de buffer ao adicionar, editar ou remover ferias.
- `escalas/management/commands/importar_planilha_atual.py`: dados CIDIS 2026 e nova rotina de importacao.
- `escalas/tests.py`: cobertura da regra de buffer e da importacao atualizada.
- Banco de producao em `beta.daesung.com.br`: usuarios, ferias/bloqueios e escala futura serao atualizados pelo comando de importacao.
