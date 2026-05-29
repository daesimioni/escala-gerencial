# Escala de Sobreaviso — Gerentes

Sistema web profissional para controle da escala de sobreaviso gerencial, substituindo o controle manual por planilha. Desenvolvido em **Python + Django** com **Bootstrap 5**.

## Funcionalidades

- 📅 **Calendário mensal e anual** com visualização clara de S1, S2, férias e bloqueios
- 🤖 **Geração automática da escala** para finais de semana, feriados e feriadões
- 👥 **Dupla obrigatória Grupo A + Grupo B** — nunca dois do mesmo grupo
- 🔄 **Alternância S1/S2** com balanceamento automático
- 🏖️ **Feriadões** com regra especial: S1 cobre início, S2 cobre final
- 🔁 **Rotação separada** para feriadões (controle de quem foi S1 e S2)
- 🚫 **Férias e bloqueios** — qualquer tipo de indisponibilidade
- ✏️ **Edição manual** com preservação durante regenerações
- 🔀 **Troca de escala** entre usuários com validação de regras
- 📊 **Relatórios** de equilíbrio, plantões, S1, S2, feriadões
- 📤 **Exportação CSV** compatível com Excel
- 🛡️ **Validação de conflitos** e alertas de desequilíbrio
- 📝 **Histórico de alterações** (audit log)
- 🔐 **Autenticação** — login obrigatório para todas as telas
- ⚙️ **Django Admin** completo para gestão de dados

## Regras de Escala Implementadas

| Prioridade | Regra |
|-----------|-------|
| 1 | Nunca escalar usuário em férias ou bloqueado |
| 2 | Dupla sempre Grupo A + Grupo B |
| 3 | Respeitar regra especial de feriadões |
| 4 | Preservar edições manuais |
| 5 | Evitar escala próxima a férias (margem de 3 dias) |
| 6 | Evitar repetição de feriados e feriadões |
| 7 | Equilibrar S1 e S2 |
| 8 | Equilibrar total de plantões |

### Regra de Feriadão

- **2 primeiros dias**: S1 trabalha, S2 de sobreaviso
- **Último dia**: S2 trabalha, S1 de sobreaviso
- **Dias intermediários** (se > 3): distribuídos de forma alternada
- **Rotação**: quem foi S1 em feriadão só repete depois que todos os outros também foram

### Detecção de Feriadões

O sistema detecta automaticamente feriadões (pontes/emendas):
- Feriado na **terça-feira** → segunda vira ponte (4 dias: sáb-dom-seg-ter)
- Feriado na **quinta-feira** → sexta vira ponte (4 dias: qui-sex-sáb-dom)
- Feriado na **sexta-feira** → 3 dias (sex-sáb-dom)
- Feriado na **segunda-feira** → 3 dias (sáb-dom-seg)

## Requisitos

- Python 3.10+
- Django 6.0+
- SQLite (padrão, sem instalação adicional)

## Instalação

```bash
# 1. Acesse a pasta do projeto
cd "C:\Users\Dae Sung Simioni\Downloads\escala_gerencial"

# 2. Crie o ambiente virtual
python -m venv venv

# 3. Ative o ambiente virtual
venv\Scripts\activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Execute as migrations
python manage.py migrate

# 6. Popule os dados iniciais (grupos, usuários, feriados, escala base)
python manage.py seed_initial_data

# 7. Crie um superusuário para acessar o sistema
python manage.py createsuperuser

# 8. Inicie o servidor
python manage.py runserver
```

## Acesso

- **Sistema**: http://127.0.0.1:8000/
- **Admin Django**: http://127.0.0.1:8000/admin/

## Usuários Iniciais

Após rodar `seed_initial_data`, os seguintes gerentes estarão cadastrados:

### Grupo A
| Nome | FER inicial | PL inicial |
|------|-------------|------------|
| Copel 1 | 0 | 14 |
| Copel 2 | 5 | 11 |
| Copel 3 | 16 | 15 |
| Copel 4 | 12 | 11 |
| Copel 5 | 16 | 10 |

### Grupo B
| Nome | FER inicial | PL inicial |
|------|-------------|------------|
| Copel 6 | 19 | 11 |
| Copel 7 | 19 | 15 |
| Copel 8 | 32 | 13 |
| Copel 9 | 25 | 14 |

## Feriados

O sistema inclui automaticamente:
- **Feriados nacionais** fixos (Confraternização Universal, Tiradentes, etc.)
- **Feriados móveis** calculados pela Páscoa (Carnaval, Sexta-feira Santa, Corpus Christi)
- **Feriados estaduais do Paraná** (Emancipação Política)
- **Feriados municipais de Curitiba** (Aniversário de Curitiba, N. Sra. da Luz)

Todos os feriados podem ser editados, desativados ou complementados via interface ou Django Admin.

## Estrutura do Projeto

```
escala_gerencial/
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3                 # Banco de dados (criado após migrate)
├── core/                      # Configuração do projeto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── escalas/                   # App principal
│   ├── models.py              # 9 modelos de dados
│   ├── services.py            # Motor de geração da escala (~500 linhas)
│   ├── views.py               # 25 views
│   ├── forms.py               # Formulários
│   ├── admin.py               # Configuração do Django Admin
│   ├── urls.py                # Rotas do app
│   └── management/commands/
│       └── seed_initial_data.py
├── templates/
│   ├── base.html              # Layout base com navbar
│   ├── registration/login.html
│   └── escalas/               # 15 templates
├── static/
│   ├── css/estilo.css
│   └── js/
└── media/
```

## Principais Telas

| URL | Descrição |
|-----|-----------|
| `/` | Dashboard com resumo e alertas |
| `/calendario/` | Calendário mensal interativo |
| `/calendario/anual/2026/` | Visão anual com mini calendários |
| `/usuarios/` | Lista de gerentes e estatísticas |
| `/bloqueios/` | Gestão de férias e indisponibilidades |
| `/feriados/` | Cadastro e edição de feriados |
| `/feriadoes/` | Feriadões detectados e manuais |
| `/relatorios/` | Relatórios de equilíbrio e estatísticas |
| `/gerar-escala/` | Gerar/regenerar escala de um mês |
| `/trocar-escala/` | Trocar plantão entre usuários |
| `/exportar/` | Exportação de dados |

## Comandos Úteis

```bash
# Regenerar escala de um mês específico
python manage.py shell -c "from escalas.services import gerar_escala_mensal; gerar_escala_mensal(2026, 6, False)"

# Atualizar contadores dos usuários
python manage.py shell -c "from escalas.services import _atualizar_contadores_usuarios; _atualizar_contadores_usuarios()"

# Listar alertas de desequilíbrio
python manage.py shell -c "from escalas.services import get_alertas_desequilibrio; print(get_alertas_desequilibrio())"
```

## Algoritmo de Distribuição

O sistema utiliza um **motor de pontuação (scoring)** para escolher a melhor dupla para cada bloco de cobertura:

1. **PL total** (peso 100): usuários com menos plantões têm prioridade
2. **Balanceamento S1/S2** (peso 50): evita que uma pessoa fique sempre na mesma função
3. **Recência** (peso 250-500): penaliza fortemente quem foi escalado nos últimos 7-14 dias
4. **Feriadão** (peso 300): dentro de feriadões, prioriza quem tem menos feriadões na função
5. **Proximidade de bloqueios** (peso 1000): evita escalar próximo a férias

O par (S1 do Grupo A, S2 do Grupo B) com menor pontuação total é o escolhido.

---

Desenvolvido para substituir planilha manual de escala de sobreaviso. Curitiba, Paraná.
