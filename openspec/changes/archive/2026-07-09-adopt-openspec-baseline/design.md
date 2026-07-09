## Context

Este projeto e um sistema Django em beta.daesung.com.br para controlar a escala gerencial de sobreaviso. O codigo ja implementa as regras atuais de escala unica por dia, historico ate 2026-06-30, ferias/bloqueios, feriados, feriadoes, relatorios, exportacoes e usuarios padrao.

A mudanca e retrospectiva: ela nao muda runtime. O objetivo tecnico e transformar o comportamento atual em contratos OpenSpec versionados para orientar manutencao futura.

## Goals / Non-Goals

**Goals:**

- Inicializar OpenSpec no repositorio.
- Registrar uma baseline fiel ao comportamento atual do sistema.
- Arquivar a baseline para que `openspec/specs/` vire a referencia principal.
- Manter os skills locais do Codex gerados pelo CLI para o fluxo OpenSpec.

**Non-Goals:**

- Alterar modelos, views, templates, comandos, banco de dados ou deploy.
- Migrar dados de producao.
- Ajustar regras de escala ou UI nesta mudanca.
- Fazer deploy em beta.daesung.com.br, pois nao ha alteracao de runtime.

## Decisions

- Usar uma change chamada `adopt-openspec-baseline`.
  - Rationale: o projeto nao tinha specs anteriores; uma change unica cria a baseline inicial e deixa historico do processo.
  - Alternative considered: criar specs diretamente em `openspec/specs/`; foi evitado porque nao exercitaria o fluxo de proposal/design/spec/tasks/archive solicitado.

- Separar a baseline em cinco capacidades.
  - Rationale: `schedule-generation`, `availability-management`, `access-control`, `user-interface` e `operations` refletem limites reais do codigo e facilitam mudancas futuras menores.
  - Alternative considered: uma unica spec grande; foi evitada porque misturaria regras de dominio, UI e operacao.

- Documentar comportamento existente, nao implementacao linha a linha.
  - Rationale: OpenSpec deve proteger requisitos observaveis. Detalhes como nomes de funcoes podem mudar sem alterar contrato.
  - Alternative considered: especificar funcoes internas; foi evitado para nao tornar refactors simples mais caros.

- Manter portugues sem acentos nos artefatos novos.
  - Rationale: reduz risco de mojibake em PowerShell, servidor e arquivos historicamente mistos.
  - Alternative considered: portugues com acentos; foi evitado nesta baseline para preservar consistencia tecnica.

## Risks / Trade-offs

- Baseline incompleta -> mitigacao: a baseline foi derivada do README, CHANGELOG, models, services, views, comandos e testes.
- Specs muito amplas -> mitigacao: cada capacidade foi separada por area funcional e pode ser refinada em changes futuras.
- OpenSpec virar documentacao esquecida -> mitigacao: `openspec/config.yaml` define a convencao de documentar mudancas comportamentais antes da implementacao.
- Mudanca sem deploy parecer incompleta -> mitigacao: esta baseline afeta processo e documentacao; validacoes de CLI e testes Django verificam que o runtime continua intacto.

## Migration Plan

1. Criar a change OpenSpec de baseline.
2. Preencher proposal, design, specs e tasks.
3. Validar a change em modo strict.
4. Arquivar a change, promovendo os requisitos para `openspec/specs/`.
5. Validar todas as specs arquivadas.
6. Rodar checks/testes Django.
7. Versionar e enviar ao repositorio Git.

Rollback: remover os arquivos `openspec/` e `.codex/skills/openspec-*` do commit se a equipe decidir nao adotar OpenSpec.

## Open Questions

Nenhuma para esta baseline. Mudancas futuras de regra devem abrir nova change OpenSpec antes da implementacao.
