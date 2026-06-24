# Escala de Sobreaviso Gerencial

Sistema Django para controle da escala gerencial dos gerentes Copel. O sistema gera e mantem uma escala de sobreaviso com apenas um gerente por dia, respeitando ferias, bloqueios, feriados, feriadoes e distribuicao equilibrada por disponibilidade.

## Ambiente correto

- Escala Gerencial beta: `https://beta.daesung.com.br`
- Escala VIP: `https://www.daesung.com.br`

Este repositorio e da Escala Gerencial. O dominio principal `daesung.com.br` pertence a Escala VIP e nao deve ser apontado para este projeto.

## Regras atuais

- Existe apenas um gerente escalado por dia.
- O gerente do dia fica somente de sobreaviso.
- Nao existe mais separacao operacional entre `S1` e `S2`.
- O corte da regra nova e `2026-07-01`.
- Janeiro a junho/2026 ficam como historico travado.
- Os marcadores antigos `S1` e `S2` de janeiro a junho contam como plantoes historicos.
- Finais de semana, feriados e feriadoes nao tem gerente presencial.
- O mesmo gerente nao pode ser escalado em dois dias consecutivos a partir de `2026-07-01`.
- A distribuicao usa a proporcao entre plantoes e oportunidades disponiveis.
- Ferias e bloqueios impedem escala no periodo cadastrado.
- Ferias reduzem os dias disponiveis do gerente e nao criam divida de compensacao no retorno.
- Meses fechados preservam o historico e nao sao regenerados automaticamente.

## Base da planilha atual

O comando `python manage.py importar_planilha_atual` aplica a planilha usada como base em 2026:

- substitui `Copel 1` a `Copel 9` pelos gerentes reais;
- cadastra codigo legado, lotacao e telefone;
- importa ferias e indisponibilidades da planilha;
- contabiliza o historico de janeiro a junho/2026;
- trava janeiro a junho/2026;
- limpa a escala futura nao manual;
- redistribui de julho/2026 a dezembro/2027.

`seed_initial_data` continua existindo por compatibilidade, mas delega para `importar_planilha_atual`.

## Funcionalidades

- Calendario mensal e visao anual.
- Geracao automatica da escala de sobreaviso.
- Cadastro de lotacao e telefone dos gerentes.
- Cadastro de ferias, faltas, treinamentos, licencas e indisponibilidades.
- Redistribuicao automatica ao adicionar, editar ou remover bloqueios.
- Edicao manual de um dia de escala.
- Troca do gerente de sobreaviso em data especifica.
- Cadastro de feriados e feriadoes manuais.
- Relatorios de distribuicao, dias disponiveis, percentual de carga, ferias, bloqueios, feriados e feriadoes.
- Graficos de carga proporcional, composicao dos sobreavisos e impacto de ferias/bloqueios.
- Exportacao CSV da escala e dos resumos.
- Historico de alteracoes.
- Autenticacao obrigatoria.
- Django Admin para manutencao dos dados.

## Requisitos

- Python 3.12 recomendado.
- Django 6.
- SQLite.
- Gunicorn para execucao no servidor.

Instalacao:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py importar_planilha_atual
python manage.py createsuperuser
python manage.py runserver
```

## Principais URLs

| URL | Descricao |
| --- | --- |
| `/` | Dashboard |
| `/calendario/` | Calendario mensal |
| `/calendario/anual/2026/` | Visao anual |
| `/usuarios/` | Gerentes e totais |
| `/bloqueios/` | Ferias e indisponibilidades |
| `/feriados/` | Feriados |
| `/feriadoes/` | Feriadoes |
| `/gerar-escala/` | Geracao/regeneracao mensal |
| `/trocar-escala/` | Troca de sobreaviso |
| `/relatorios/` | Relatorios |
| `/exportar/` | Exportacoes CSV |
| `/admin/` | Django Admin |

## Estrutura

```text
Escala_Gerencial/
|-- manage.py
|-- requirements.txt
|-- README.md
|-- CHANGELOG.md
|-- core/
|   |-- settings.py
|   |-- urls.py
|   `-- wsgi.py
|-- escalas/
|   |-- models.py
|   |-- services.py
|   |-- views.py
|   |-- forms.py
|   |-- admin.py
|   |-- urls.py
|   |-- tests.py
|   `-- management/commands/
|       |-- importar_planilha_atual.py
|       `-- seed_initial_data.py
|-- templates/
|   |-- base.html
|   |-- registration/login.html
|   `-- escalas/
`-- static/
    |-- css/estilo.css
    `-- js/calendario.js
```

## Validacao

Comandos usados antes de publicar alteracoes:

```bash
python manage.py check
python manage.py test
python manage.py collectstatic --noinput --clear
```

Validacoes esperadas:

- Nenhum registro gerado deve ter `s2` preenchido.
- Nao deve haver gerente repetido em dias consecutivos a partir de `2026-07-01`.
- Ninguem deve estar escalado durante ferias ou bloqueio.
- Todo feriado nacional, estadual do Parana e municipal de Curitiba deve ter gerente de sobreaviso.
- O calendario mensal deve exibir somente o gerente de sobreaviso.
- Ferias e bloqueios nao devem aparecer como pessoas escaladas dentro da celula do calendario.
- `daesung.com.br` deve continuar servindo a Escala VIP.
- `beta.daesung.com.br` deve servir a Escala Gerencial.

## Producao beta

No servidor:

- Projeto: `/opt/escala-beta`
- Servico: `escala-beta.service`
- Gunicorn: `127.0.0.1:8001`
- Nginx: `beta.daesung.com.br`
- Banco: `/opt/escala-beta/db.sqlite3`

Antes de alteracoes no banco do beta, criar backup com formato:

```text
/opt/escala-beta/db.sqlite3.bak_YYYYMMDDHHMMSS
```
