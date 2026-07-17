# Documentação — Raiz do projeto (`branch-v2`)

CRM web para o setor de TI, construído em **Django 6**. Centraliza login, dashboard inicial e módulos operacionais (helpdesk, chips, e-mails e equipamentos).

## Para que serve esta pasta

É o **BASE_DIR** do projeto: ponto de entrada (`manage.py`), configuração global em `setup/` e os apps Django em pastas irmãs.

## Arquivos na raiz

| Arquivo / pasta | Função |
|-----------------|--------|
| `manage.py` | CLI do Django; define `DJANGO_SETTINGS_MODULE=setup.settings`. |
| `README.md` | Descrição breve do repositório. |
| `LICENSE` | Licença do projeto. |
| `.gitignore` | Arquivos ignorados pelo Git. |
| `.env.exemple` | Modelo `.env`: perfil SQLite (dev) ou PostgreSQL (VPS). |
| `.vps/` | Deploy produção: Postgres, Gunicorn, Nginx. Ver `.vps/DOCUMENTACAO.md`. |
| `requirements.txt` | Django, `psycopg[binary]`, gunicorn. |
| `setup/` | Projeto Django (settings, URLs raiz, WSGI/ASGI). Ver `setup/DOCUMENTACAO.md`. |
| `core/` | Usuários customizados, login e dashboard principal. Ver `core/DOCUMENTACAO.md`. |
| `helpdesk/` | Chamados em Kanban, histórico e SSE. Ver `helpdesk/DOCUMENTACAO.md`. |
| `chips/` | Inventário e movimentação de chips celulares. Ver `chips/DOCUMENTACAO.md`. |
| `emails/` | Domínios e contas de e-mail corporativas. Ver `emails/DOCUMENTACAO.md`. |
| `equipment/` | Patrimônio de equipamentos de TI. Ver `equipment/DOCUMENTACAO.md`. |

## Rotas principais (`setup/urls.py`)

| Prefixo | Módulo |
|---------|--------|
| `/` | `core` — dashboard e autenticação |
| `/usuarios/` | `core` — gestão de usuários (ADMIN) |
| `/admin/` | Django Admin |
| `/helpdesk/` | Helpdesk |
| `/chips/` | Chips |
| `/emails/` | E-mails |
| `/equipment/` | Equipamentos |

## Documentação por subpasta

Cada diretório do repositório possui seu próprio `DOCUMENTACAO.md` com a lista de arquivos e o papel da pasta.
