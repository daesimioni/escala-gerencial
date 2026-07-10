## Context

O sistema ja trabalha com um gerente unico em sobreaviso a partir de `2026-07-01`. A nova planilha tem historico de janeiro ate o inicio de julho, ferias marcadas e nomes que nao devem mais participar da escala. A aplicacao precisa continuar usando o algoritmo proporcional existente, mas com uma base de disponibilidade mais correta.

## Goals / Non-Goals

**Goals:**

- Importar dados CIDIS 2026 de forma idempotente.
- Desativar ex-gerentes sem apagar historico de auditoria.
- Preservar historico ja ocorrido ate `2026-07-09`.
- Recalcular a escala de `2026-07-10` ate o fim de 2026.
- Bloquear fins de semana adjacentes as ferias quando estiverem nos 2 dias antes/depois.
- Validar localmente e publicar no beta.

**Non-Goals:**

- Reintroduzir S1/S2 como regra operacional.
- Alterar o dominio `daesung.com.br`.
- Criar nova tabela para buffers de ferias.
- Importar Gustavo Theodor, Jefferson Franco ou Marcelo como gerentes ativos.

## Decisions

- Usar bloqueios `INDISPONIBILIDADE` com motivo padronizado para buffers de ferias.
  - Rationale: evita migracao de banco, reutiliza a regra de disponibilidade existente e fica visivel como bloqueio operacional.
  - Alternative considered: criar novo tipo/modelo de bloqueio; foi evitado por ser desnecessario para o comportamento.

- Sincronizar buffers por usuario, nao por bloco individual.
  - Rationale: evita duplicidade quando duas ferias diferentes geram o mesmo fim de semana bloqueado.
  - Alternative considered: criar um buffer por ferias; poderia duplicar linhas em ferias proximas.

- Importar julho ate `2026-07-09` como historico manual.
  - Rationale: os dias ja ocorridos nao devem ser apagados por redistribuicao, mas julho ainda precisa continuar aberto para o restante do mes.
  - Alternative considered: fechar julho inteiro; bloquearia a redistribuicao pedida.

- Manter `2026-07-01` como corte da regra nova.
  - Rationale: a regra de um gerente por dia ja comeca em julho; o novo historico de 04/07 e 05/07 fica dentro da regra nova.

## Risks / Trade-offs

- Ferias antigas tambem geram buffers historicos -> mitigacao: isso afeta oportunidades e relatorios, mas meses fechados preservam escala passada.
- Buffers aparecem como indisponibilidade, nao como uma cor preta especifica -> mitigacao: o sistema ja usa bloqueios para disponibilidade; a agenda nao e uma planilha matricial.
- Redistribuicao pode alterar escalas futuras antigas da planilha -> mitigacao: isso e desejado pelo pedido, porque S1/S2 futuro foi extinto.

## Migration Plan

1. Atualizar comando de importacao e regra de buffer.
2. Rodar testes locais.
3. Executar importacao local e validar escala de Jul-Dez/2026.
4. Commitar e enviar ao GitHub.
5. Fazer deploy no `beta.daesung.com.br`.
6. Fazer backup do banco remoto antes da importacao.
7. Rodar `importar_planilha_atual` no servidor.
8. Validar com checks remotos e paginas principais.
