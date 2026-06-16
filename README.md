# Escala de Sobreaviso Gerencial

Sistema Django para controle da escala gerencial dos gerentes Copel. O sistema gera e mantém uma escala de sobreaviso com apenas um gerente por dia, respeitando férias, bloqueios, feriados, feriadões e distribuição equilibrada.

## Ambiente correto

- Escala Gerencial beta: `https://beta.daesung.com.br`
- Escala VIP: `https://www.daesung.com.br`

Este repositório é da Escala Gerencial. O domínio principal `daesung.com.br` pertence à Escala VIP e não deve ser apontado para este projeto.

## Regras atuais

- Existe apenas um gerente escalado por dia.
- O gerente do dia fica somente de sobreaviso.
- Não existe mais separação operacional entre `S1` e `S2`.
- Finais de semana, feriados e feriadões não têm gerente presencial.
- O mesmo gerente não pode ser escalado em dois dias consecutivos.
- A distribuição deve ser a mais equilibrada possível entre os gerentes disponíveis.
- Férias e bloqueios impedem escala no período cadastrado.
- Férias reduzem os dias disponíveis do gerente e não criam dívida de compensação no retorno.
- Meses fechados preservam o histórico e não são regenerados automaticamente.

## Funcionalidades

- Calendário mensal e visão anual.
- Geração automática da escala de sobreaviso.
- Cadastro de férias, faltas, treinamentos, licenças e indisponibilidades.
- Redistribuição automática ao adicionar, editar ou remover bloqueios.
- Edição manual de um dia de escala.
- Troca do gerente de sobreaviso em data específica.
- Cadastro de feriados e feriadões manuais.
- Relatórios de distribuição, dias disponíveis, férias, bloqueios, feriados e feriadões.
- Exportação CSV da escala e dos resumos.
- Histórico de alterações.
- Autenticação obrigatória.
- Django Admin para manutenção dos dados.

## Requisitos

- Python 3.12 recomendado.
- Django 6.
- SQLite.
- Gunicorn para execução no servidor.

Instalação:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_initial_data
python manage.py createsuperuser
python manage.py runserver
```

## Principais URLs

| URL | Descrição |
| --- | --- |
| `/` | Dashboard |
| `/calendario/` | Calendário mensal |
| `/calendario/anual/2026/` | Visão anual |
| `/usuarios/` | Gerentes e totais |
| `/bloqueios/` | Férias e indisponibilidades |
| `/feriados/` | Feriados |
| `/feriadoes/` | Feriadões |
| `/gerar-escala/` | Geração/regeneração mensal |
| `/trocar-escala/` | Troca de sobreaviso |
| `/relatorios/` | Relatórios |
| `/exportar/` | Exportações CSV |
| `/admin/` | Django Admin |

## Estrutura

```text
Escala_Gerencial/
├── manage.py
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── core/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── escalas/
│   ├── models.py
│   ├── services.py
│   ├── views.py
│   ├── forms.py
│   ├── admin.py
│   ├── urls.py
│   ├── tests.py
│   └── management/commands/seed_initial_data.py
├── templates/
│   ├── base.html
│   ├── registration/login.html
│   └── escalas/
└── static/
    ├── css/estilo.css
    └── js/calendario.js
```

## Validação

Comandos usados antes de publicar alterações:

```bash
python manage.py check
python manage.py test escalas -v 1
python manage.py collectstatic --noinput --clear
```

Validações esperadas:

- Nenhum registro gerado deve ter `s2` preenchido.
- Não deve haver gerente repetido em dias consecutivos.
- O calendário mensal deve exibir somente o gerente de sobreaviso.
- Férias e bloqueios não devem aparecer como pessoas escaladas dentro da célula do calendário.
- `daesung.com.br` deve continuar servindo a Escala VIP.
- `beta.daesung.com.br` deve servir a Escala Gerencial.

## Produção beta

No servidor:

- Projeto: `/opt/escala-beta`
- Serviço: `escala-beta.service`
- Gunicorn: `127.0.0.1:8001`
- Nginx: `beta.daesung.com.br`
- Banco: `/opt/escala-beta/db.sqlite3`

Antes de alterações no banco do beta, criar backup com formato:

```text
/opt/escala-beta/db.sqlite3.bak_YYYYMMDDHHMMSS
```
