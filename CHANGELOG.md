# Changelog

## 2026-06-24 - Planilha atual e redistribuicao proporcional

### Dados

- Substituidos os usuarios genericos `Copel 1` a `Copel 9` pelos gerentes reais da planilha.
- Adicionados ao cadastro do gerente: codigo legado, lotacao, telefone e oportunidades historicas ate 30/06/2026.
- O historico de janeiro a junho/2026 passou a ser a base da distribuicao futura.
- Os marcadores antigos `S1` e `S2` de janeiro a junho contam como plantao historico.
- A agenda futura ignora os marcadores antigos de julho em diante e e redistribuida pela regra nova.

### Regras

- O corte operacional da regra nova ficou definido em `2026-07-01`.
- De `2026-07-01` em diante, cada dia tem somente um gerente em sobreaviso.
- A pontuacao usa `plantoes / oportunidades disponiveis`.
- Ferias e indisponibilidades reduzem oportunidades e nao geram compensacao futura.
- A validacao de dias consecutivos passa a ser aplicada na escala futura, a partir do corte.

### Importacao

- Criado o comando idempotente `python manage.py importar_planilha_atual`.
- O comando atualiza usuarios reais e contatos, recria bloqueios da planilha, importa 57 dias historicos, trava jan-jun/2026, limpa a escala futura nao manual e gera jul/2026 a dez/2027.
- O comando legado `seed_initial_data` agora delega para `importar_planilha_atual`.

### Validacao local

- `python manage.py check`: OK.
- `python manage.py test`: 24 testes OK.
- Base local apos importacao: `s2_count = 0`, `consecutivos_futuro = 0`, `escalado_bloqueado = 0`, `future_days = 178`.
- Carga anual 2026 ficou entre 15,7% e 17,8%.

## 2026-06-15 - Regra de um gerente de sobreaviso

### Regra de negócio

- Removida a regra operacional de dois gerentes por dia.
- A escala agora considera apenas um gerente de sobreaviso por dia.
- O campo legado `s1` continua sendo usado internamente como o gerente do dia.
- O campo legado `s2` fica vazio para todas as escalas geradas, editadas ou trocadas.
- Finais de semana, feriados e feriadões não têm gerente presencial.
- O mesmo gerente não pode ser escalado em dois dias consecutivos.
- Férias e bloqueios reduzem a disponibilidade do gerente, mas não criam dívida de compensação no retorno.

### Algoritmo

- O gerador passou a escolher um único gerente por dia.
- A pontuação de distribuição passou a considerar a proporção entre trabalhos realizados e oportunidades disponíveis.
- Dias de férias/bloqueio são removidos das oportunidades do gerente.
- A validação de dia passou a bloquear:
  - gerente em férias ou bloqueio;
  - gerente já escalado no dia anterior ou no dia seguinte.

### Interface

- Telas e formulários foram ajustados para "Gerente de sobreaviso".
- Menu "Trocar Escala" foi renomeado para "Trocar Sobreaviso".
- Relatórios e exportações CSV removem colunas e textos de `S1`/`S2`.
- Calendário mensal mostra somente `Sobreaviso Copel X` em cada dia.
- Férias e indisponibilidades não aparecem mais como linhas `F Copel...` ou `N Copel...` dentro das células do calendário.
- Férias e bloqueios continuam disponíveis na tela "Férias & Bloqueios" e nos relatórios.
- CSS mobile corrigido para evitar overflow horizontal.
- CSS/JS versionados no template base para reduzir cache antigo no navegador.

### Produção e deploy

- Beta correto: `https://beta.daesung.com.br`.
- O domínio `https://www.daesung.com.br` pertence à Escala VIP e foi restaurado para o stack original.
- O serviço Django criado por engano para produção (`escala-prod`) foi parado, desabilitado e removido.
- O beta foi atualizado em `/opt/escala-beta`.
- Backups relevantes criados no beta:
  - `/opt/escala-beta/db.sqlite3.bak_20260615124949`
  - `/opt/escala-beta/db.sqlite3.bak_20260615125528`
- Backup de Nginx usado para restaurar a Escala VIP:
  - `/var/backups/escala/nginx-daesung-escala-20260615123912.conf`

### Validação

- `python manage.py check`: OK.
- `python manage.py test escalas -v 1`: 24 testes OK.
- `collectstatic`: OK.
- Banco do beta:
  - `s2_count = 0`;
  - `consecutivos = 0`;
  - `dias_com_s1 = 199`.
- HTML autenticado de `https://beta.daesung.com.br/calendario/2026/6/` validado sem `F Copel`, sem `N Copel`, sem `S1/S2` visível e sem "presencial".
- `https://www.daesung.com.br/` validado como "Escala VIP".
- `https://beta.daesung.com.br/login/` validado como "Login - Escala de Sobreaviso".
