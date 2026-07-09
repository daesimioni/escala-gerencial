## Why

O projeto ja possui regras de negocio especificas para escala gerencial, mas ainda nao tinha um contrato OpenSpec para orientar proximas alteracoes. Esta baseline registra o comportamento atual antes de novas mudancas, reduzindo risco de regressao em geracao de escala, ferias, feriados, relatorios, acesso e operacao.

## What Changes

- Adicionar OpenSpec ao repositorio com contexto do projeto e skills locais do Codex gerados pelo CLI.
- Registrar as capacidades atuais do sistema como specs iniciais.
- Arquivar a mudanca inicial para que as specs principais passem a ser a fonte de referencia daqui para frente.
- Nao alterar regras de runtime, banco, templates ou deploy nesta mudanca.

## Capabilities

### New Capabilities

- `schedule-generation`: regras de geracao, redistribuicao, historico, meses fechados e validacao da escala.
- `availability-management`: cadastro de gerentes, ferias, bloqueios, feriados e feriadoes.
- `access-control`: autenticacao, usuarios padrao, administrador e restricoes de operacao.
- `user-interface`: dashboard, calendario, visao anual, relatorios, graficos e exportacoes.
- `operations`: importacao da planilha atual, testes, deploy e limites de dominio.

### Modified Capabilities

Nenhuma. Esta e a primeira baseline OpenSpec do projeto.

## Impact

- Novos artefatos em `openspec/` com specs versionadas.
- Novos skills locais em `.codex/skills/` para fluxo OpenSpec dentro deste repositorio.
- Processo de desenvolvimento passa a exigir change OpenSpec para alteracoes futuras de comportamento.
- Sem impacto esperado em `escala/`, banco de dados, endpoints, usuarios ou producao.
