# Regras Implementadas - Escala Gerencial

Ultima atualizacao: 2026-07-09

Este documento consolida as regras atualmente implementadas no sistema Escala de Sobreaviso Gerencial. Ele foi derivado do codigo, testes, README, changelog e baseline OpenSpec arquivada em `openspec/specs/`.

## 1. Escopo do sistema

- O sistema controla a escala gerencial de sobreaviso.
- O ambiente correto do sistema gerencial e `beta.daesung.com.br`.
- `daesung.com.br` e `www.daesung.com.br` pertencem ao sistema Escala VIP e nao devem receber deploy, proxy, aliases ou arquivos da escala gerencial.
- A regra operacional nova comeca em `2026-07-01`.
- O periodo de `2026-01-01` ate `2026-06-30` e historico importado da planilha e deve ser preservado.

## 2. Modelo operacional da escala

- A partir de `2026-07-01`, cada dia que exige cobertura tem apenas um gerente.
- Esse gerente fica em sobreaviso.
- Nao existe mais escala presencial para finais de semana, feriados ou feriadoes.
- Nao existem mais dois gerentes no mesmo dia para a regra futura.
- Os campos internos `s1` e `s2` ainda existem por compatibilidade de banco/modelo.
- Na regra futura, o gerente unico fica gravado em `s1`.
- Na regra futura, `s2` deve ficar vazio.
- Marcadores antigos S1/S2 podem existir apenas no historico importado ate `2026-06-30`.
- Dias comuns de semana, sem feriado e sem feriadao, nao precisam de cobertura automatica.

## 3. Datas que exigem cobertura

O sistema gera cobertura de sobreaviso para:

- sabados;
- domingos;
- feriados ativos;
- feriadoes detectados automaticamente;
- dias de emenda incluidos em feriadoes.

O sistema nao gera escala automatica para dia util comum quando ele nao e feriado, nao e fim de semana e nao faz parte de feriadao.

## 4. Feriados considerados

O sistema considera feriados fixos, feriados moveis e feriados cadastrados no banco.

Feriados nacionais fixos implementados:

- 01/01 - Confraternizacao Universal;
- 21/04 - Tiradentes;
- 01/05 - Dia do Trabalho;
- 07/09 - Independencia do Brasil;
- 12/10 - Nossa Senhora Aparecida;
- 02/11 - Finados;
- 15/11 - Proclamacao da Republica;
- 20/11 - Consciencia Negra;
- 25/12 - Natal.

Feriado estadual do Parana implementado:

- 19/12 - Emancipacao Politica do Parana.

Feriados municipais de Curitiba implementados:

- 29/03 - Aniversario de Curitiba;
- 08/09 - Nossa Senhora da Luz dos Pinhais.

Feriados moveis calculados pela Pascoa:

- Carnaval, segunda-feira;
- Carnaval, terca-feira;
- Sexta-feira Santa;
- Corpus Christi.

Regras adicionais de feriado:

- Feriados manuais ativos cadastrados no banco tambem exigem cobertura.
- Um feriado manual inativo remove a data da lista de feriados ativos daquele ano.
- Feriados recorrentes existem no cadastro, mas a geracao usa a data ativa calculada/cadastrada.

## 5. Regra de feriadao

O sistema detecta feriadoes analisando o mes alvo com uma margem de dias antes e depois.

Um bloco vira feriadao quando:

- ha uma sequencia consecutiva de dias marcados como fim de semana, feriado ou ponte;
- a sequencia tem pelo menos 2 dias;
- a sequencia contem pelo menos um feriado.

Regras de ponte/emenda:

- Se o feriado cair na terca-feira, a segunda-feira anterior entra como ponte.
- Se o feriado cair na quinta-feira, a sexta-feira seguinte entra como ponte.
- Ponte so e marcada quando o dia ainda nao e fim de semana nem feriado.

Classificacao dos blocos:

- Sequencia com feriado e 2 ou mais dias: `FERIADAO`.
- Feriado isolado de 1 dia: `FERIADO`.
- Sabado/domingo sem feriado conectado: `FIM_DE_SEMANA`.
- Fim de semana parcialmente coberto por outro bloco pode aparecer como `FDS Parcial`.

Exemplo implementado: em maio/2026, 01/05 sexta-feira, 02/05 sabado e 03/05 domingo formam feriadao do Dia do Trabalho.

## 6. Cadastro de gerentes

Cada gerente de escala possui:

- usuario Django vinculado, quando existir;
- nome;
- codigo legado;
- lotacao;
- telefone;
- grupo;
- indicador de ativo/inativo;
- contadores historicos iniciais;
- totalizadores calculados pelo sistema.

Somente gerentes ativos entram na geracao automatica.

Gerente inativo:

- nao e candidato na geracao automatica;
- permanece no historico se ja tiver registros antigos;
- pode continuar existindo no banco para auditoria.

## 7. Grupos de escala

- O modelo ainda possui grupos de escala.
- A importacao atual usa grupos A e B para organizar os gerentes.
- A regra futura nao usa grupos para escolher dois gerentes por dia.
- Como agora existe somente um gerente por dia, o grupo funciona como classificacao/cadastro e informacao de relatorio.

## 8. Ferias e bloqueios

O sistema possui bloqueios por periodo, sempre com data inicial e data final inclusivas.

Tipos de bloqueio implementados:

- `FERIAS`;
- `FALTA`;
- `TREINAMENTO`;
- `LICENCA`;
- `AFASTAMENTO`;
- `INDISPONIBILIDADE`;
- `OUTRO`.

Regra principal:

- Se um gerente tem bloqueio cobrindo determinada data, ele nao pode ser escalado naquela data.
- Ferias tambem sao tratadas como indisponibilidade para a geracao.
- Bloqueios reduzem as oportunidades disponiveis do gerente.
- O gerente nao ganha "divida" de escala por ter ficado de ferias ou bloqueado.

## 9. Buffer de fim de semana nas ferias

Quando um gerente tem ferias cadastradas, o sistema cria bloqueios automaticos para fins de semana imediatamente adjacentes:

- nos 2 dias corridos antes do inicio das ferias, se algum desses dias for sabado ou domingo;
- nos 2 dias corridos depois do fim das ferias, se algum desses dias for sabado ou domingo.

Esses dias de buffer:

- aparecem como indisponibilidade automatica;
- impedem o gerente de ser escalado;
- reduzem as oportunidades disponiveis;
- nao geram compensacao futura.

Exemplo: se uma feria comeca em uma segunda-feira, o sabado e domingo imediatamente anteriores sao bloqueados automaticamente. Se termina em uma sexta-feira, o sabado e domingo imediatamente posteriores tambem sao bloqueados automaticamente.

## 10. Redistribuicao apos ferias ou bloqueios

Ao adicionar, editar ou remover bloqueio/ferias que afete periodo futuro:

- o sistema regenera a escala a partir da data afetada;
- quando o bloqueio for ferias, a data afetada considera tambem o primeiro buffer automatico de fim de semana;
- no primeiro mes impactado, dias anteriores a data de inicio sao preservados;
- meses fechados sao pulados;
- a redistribuicao considera o mes atual afetado e os 5 meses seguintes;
- dias manuais sao preservados por padrao;
- se nao houver gerente disponivel, o sistema registra erro/aviso em vez de atribuir gerente invalido.

Exemplo:

- Se uma feria comeca em 15/07, a redistribuicao de julho considera apenas os dias de 15/07 em diante.
- Dias automaticos de 01/07 a 14/07 permanecem como estavam.
- Se agosto ou setembro estiverem fechados, eles sao pulados.

## 11. Distribuicao proporcional

A distribuicao tenta ser equilibrada proporcionalmente aos dias disponiveis de cada gerente.

A regra de equilibrio usa:

- quantidade de plantoes/sobreavisos ja atribuidos;
- quantidade de oportunidades em que o gerente estava disponivel;
- contadores historicos importados ate `2026-06-30`;
- contagem de fins de semana, feriados e feriadoes;
- distancia desde a ultima escala;
- bloqueios e ferias.

Regra mais importante:

- O sistema compara `plantoes / oportunidades`.
- Ferias e bloqueios diminuem oportunidades.
- O gerente que saiu de ferias nao deve ser sobrecarregado depois para "empatar" com os demais em quantidade bruta.
- O que deve ficar equilibrado e a carga proporcional em relacao aos dias em que cada pessoa podia trabalhar.

## 12. Escolha automatica do gerente

Para cada data de cobertura, o sistema:

- lista gerentes ativos;
- remove quem esta bloqueado/indisponivel naquela data;
- remove quem ficaria em dois dias consecutivos;
- calcula uma pontuacao de carga;
- escolhe o menor score;
- desempata de forma deterministica por nome e id.

A pontuacao favorece:

- menor carga proporcional;
- menor total de plantoes;
- menor concentracao em fim de semana, feriado ou feriadao;
- maior intervalo desde a ultima escala;
- gerente que ainda nunca foi escalado no periodo calculado.

A pontuacao penaliza:

- escala no dia anterior ou seguinte;
- escalas muito proximas;
- presenca em uma janela recente de rotacao;
- excesso relativo de plantoes;
- excesso em fins de semana, feriados ou feriadoes.

## 13. Proibicao de dias consecutivos

A mesma pessoa nao pode ficar escalada em dois dias seguidos.

Essa regra vale para:

- geracao automatica;
- redistribuicao apos ferias/bloqueios;
- troca manual de sobreaviso;
- edicao manual validada.

O sistema verifica:

- o dia anterior;
- o dia seguinte;
- atribuicoes temporarias ainda nao gravadas durante a geracao de um bloco.

Se a regra for violada, a operacao deve ser bloqueada ou retornar erro.

## 14. Meses fechados

Um mes fechado fica protegido contra alteracoes automaticas.

Regras:

- Geracao automatica sem forcar nao altera mes fechado.
- Redistribuicao por ferias/bloqueios pula meses fechados.
- Tentativas de regerar mes fechado geram aviso/alerta.
- Ao fechar um mes, os dias de escala daquele mes recebem status `FECHADA`.
- Ao reabrir um mes, o bloqueio do mes e removido e dias com status `FECHADA` voltam para `AUTOMATICA`.
- Fechar e reabrir mes e operacao restrita a administrador/staff.

## 15. Historico de janeiro a junho de 2026

O historico de `2026-01-01` ate `2026-06-30` vem da planilha atual.

Regras:

- O historico e preservado contra a regra nova.
- A regra de um gerente por dia vale somente a partir de `2026-07-01`.
- Marcadores antigos S1/S2 podem contar como plantao historico.
- Os contadores historicos importados entram na distribuicao futura.
- Jan/2026 a Jun/2026 ficam fechados/travados apos importacao.

## 16. Edicao manual de escala

Ao editar manualmente um dia:

- a escala passa a ser marcada como manual;
- o status passa a refletir alteracao manual;
- o usuario que editou e a data/hora da edicao sao registrados;
- o historico de alteracao e gravado;
- a escala manual e preservada por padrao em novas geracoes.

## 17. Troca de sobreaviso

A tela de troca substitui o gerente de sobreaviso de uma data.

Regras:

- A data precisa ter escala cadastrada.
- O gerente destino nao pode estar bloqueado naquela data.
- O gerente destino nao pode gerar repeticao em dias consecutivos.
- A troca deixa `s2` vazio.
- A escala trocada vira manual.
- Os contadores dos usuarios sao recalculados.
- A troca e gravada no historico.

## 18. Limpeza de dia

Quando uma escala de dia e limpa/removida:

- a alteracao e registrada no historico;
- os contadores devem ser atualizados conforme a ausencia daquele sobreaviso;
- a data deixa de exibir gerente ate nova edicao ou regeracao aplicavel.

## 19. Contadores dos gerentes

Os contadores sao recalculados considerando a regra nova.

Regras:

- A partir do corte, apenas `s1` conta como sobreaviso.
- `total_s2` deve ser zero para a regra futura.
- `total_dias_trabalhados` fica zero porque nao ha escala presencial na regra atual.
- `total_dias_sobreaviso` equivale ao total de plantoes/sobreavisos.
- Feriados e feriadoes sao contados separadamente.
- Ultima escala considera a ultima data em que o gerente aparece em `s1`.

## 20. Alertas de desequilibrio

O sistema pode gerar alertas quando:

- encontra gerente escalado em dias consecutivos a partir do corte;
- encontra diferenca relevante de carga proporcional entre gerentes.

A regra de desequilibrio considera:

- diferenca de carga relativa maior que 0,25;
- e diferenca bruta maior que 2 plantoes.

O alerta deixa claro que ferias reduzem dias disponiveis e nao geram divida futura.

## 21. Relatorios

Os relatorios mostram a escala por periodo mensal ou anual.

Devem apresentar:

- total de sobreavisos;
- dias disponiveis;
- percentual de carga;
- sabados;
- domingos;
- feriados;
- feriadoes;
- dias de ferias;
- dias de bloqueio;
- lotacao;
- telefone;
- graficos/indicadores de distribuicao.

Regras dos relatorios:

- A carga e ordenada pelo percentual de carga.
- Ferias e bloqueios aparecem separados dos dias de sobreaviso.
- O relatorio anual de 2026 inclui o historico importado quando aplicavel.
- A leitura deve explicar a proporcionalidade, nao apenas o total bruto.

## 22. Dashboard

O dashboard deve mostrar:

- total de gerentes ativos;
- total de bloqueios ativos/proximos;
- alertas;
- data atual;
- mini calendario do mes atual;
- proximas escalas;
- proximos blocos de cobertura;
- meses fechados;
- acoes rapidas;
- legenda.

Mini calendario:

- dias com sobreaviso devem ter destaque visual;
- ao passar o mouse, deve aparecer o nome do gerente do dia;
- a lista/tabela de proximas escalas fica abaixo ou ao lado, conforme layout responsivo.

## 23. Calendario mensal e visao anual

Regras visuais:

- Futuro deve mostrar somente um gerente por dia.
- O texto deve usar "sobreaviso".
- A interface nao deve mostrar dois gerentes por dia na regra futura.
- A interface nao deve usar S1/S2 como papeis operacionais futuros.
- A interface nao deve indicar "presencial" para fim de semana, feriado ou feriadao.
- Feriado e feriadao devem aparecer com etiqueta explicita quando aplicavel.
- Ferias/bloqueios nao devem aparecer como linhas de escala dentro da celula do calendario como se fossem gerente escalado.

## 24. Exportacoes CSV

Exportacao mensal da escala:

- arquivo `escala_YYYY_MM.csv`;
- colunas: Data, Dia, Tipo, Gerente de Sobreaviso, Grupo, Manual, Observacao;
- tipo pode ser Comum, FDS, Feriado ou Feriadao;
- usa um unico campo de gerente de sobreaviso;
- nao usa colunas futuras de S1/S2.

Exportacao de resumo:

- mensal ou anual;
- colunas: Usuario, Grupo, Total Sobreaviso, Dias Disponiveis, Percentual Carga, Sabados, Domingos, Feriados, Feriadoes, Ferias (dias), Bloqueios (dias).

## 25. Usuarios e acesso

Todas as telas operacionais principais exigem login.

Exigem autenticacao:

- dashboard;
- calendario mensal;
- visao anual;
- usuarios;
- ferias e bloqueios;
- feriados;
- feriadoes;
- relatorios;
- gerar escala;
- trocar sobreaviso;
- exportar;
- administracao.

Administrador:

- deve ser preservado;
- pode executar operacoes administrativas;
- pode fechar e reabrir meses;
- nao deve ser rebaixado pelo comando de sincronizacao de usuarios padrao.

Usuarios padrao:

- existe um usuario padrao para cada gerente ativo;
- sao vinculados ao cadastro do gerente;
- nao sao staff;
- nao sao superusuarios;
- sao ativados no Django;
- seguem username gerado pelo nome do gerente em minusculo, sem acentos e com separador ponto.

## 26. Comandos operacionais

### `python manage.py importar_planilha_atual`

Importa a base CIDIS 2026 atual da escala gerencial.

Regras do comando:

- cria/atualiza feriados;
- mantem ativos apenas os 9 gerentes atuais;
- desativa gerentes fora do roster atual, incluindo Gustavo Theodor, Jefferson Franco e Marcelo;
- grava lotacao, telefone, grupo e contadores historicos;
- sincroniza usuarios padrao dos gerentes;
- recria bloqueios da planilha;
- cria buffers automaticos de fim de semana antes/depois das ferias;
- importa a escala historica ate 09/07/2026;
- trava Jan/2026 a Jun/2026;
- limpa toda escala futura a partir de 10/07/2026;
- gera escala de 10/07/2026 a Dez/2026;
- atualiza contadores.

### `python manage.py sincronizar_usuarios_padrao`

Cria e vincula usuarios Django para gerentes ativos.

Regras do comando:

- gera username a partir do nome do gerente;
- cria usuario se nao existir;
- vincula o usuario ao gerente;
- preserva superusuario existente;
- nao concede staff/superuser para usuario padrao;
- permite informar senha inicial via argumento;
- permite resetar senha de usuarios existentes quando usado com `--reset-password`, exceto superusuarios.

### `python manage.py seed_initial_data`

Regra atual:

- comando legado delega para `importar_planilha_atual`.

## 27. Auditoria e historico

O sistema registra eventos importantes em historico ou alertas.

Eventos registrados incluem:

- edicao manual de dia;
- troca de sobreaviso;
- limpeza/remocao de escala;
- fechamento de mes;
- reabertura de mes;
- regeneracao de escala;
- tentativa de regerar mes fechado;
- meses fechados pulados em redistribuicao.

## 28. Validacoes automatizadas existentes

A suite de testes protege regras como:

- calculo da Pascoa e feriados moveis;
- deteccao de feriadao;
- cobertura de finais de semana, feriados e feriadoes;
- um gerente por dia;
- `s2` vazio na regra futura;
- proibicao de dias consecutivos;
- usuario bloqueado nao ser escalado;
- preservacao de manuais;
- redistribuicao apos ferias;
- proporcionalidade com ferias sem compensacao indevida;
- labels de feriado/feriadao;
- dashboard com mini calendario;
- interface sem S1/S2/presencial na regra futura;
- CSV com terminologia atual;
- sincronizacao de usuarios padrao.

Comandos de validacao usados:

- `npx @fission-ai/openspec@latest validate --all --strict`;
- `python manage.py check`;
- `python manage.py test`.

## 29. OpenSpec como fonte de contrato

O projeto agora usa OpenSpec para controlar mudancas de comportamento.

Specs oficiais atuais:

- `openspec/specs/schedule-generation/spec.md`;
- `openspec/specs/availability-management/spec.md`;
- `openspec/specs/access-control/spec.md`;
- `openspec/specs/user-interface/spec.md`;
- `openspec/specs/operations/spec.md`.

Regra de processo:

- Mudancas futuras que alterem comportamento devem abrir uma change OpenSpec.
- A change deve passar por proposta, design/specs/tasks quando aplicavel.
- Apos implementacao e validacao, a change deve ser arquivada.

## 30. Regras negativas importantes

O sistema nao deve:

- colocar dois gerentes no mesmo dia na escala futura;
- usar S1/S2 como regra operacional futura;
- compensar ferias sobrecarregando o gerente depois;
- escalar gerente bloqueado;
- escalar gerente em fim de semana de buffer automatico de ferias;
- escalar a mesma pessoa em dois dias consecutivos;
- alterar automaticamente mes fechado;
- alterar historico Jan-Jun/2026 pela regra nova;
- tratar final de semana, feriado ou feriadao como presencial;
- substituir a Escala VIP em `daesung.com.br` ou `www.daesung.com.br`.
