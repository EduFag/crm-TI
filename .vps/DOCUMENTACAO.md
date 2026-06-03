# Documentação — `.vps/`

Arquivos de referência para **deploy em VPS** com **PostgreSQL**, Gunicorn e Nginx.

## Para que serve

Não substitui o `.env` da raiz: aqui ficam modelos e scripts que você copia/adapta no servidor Linux.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `readme.md` | Visão geral da pasta |
| `env.exemple` | `.env` de produção com `DB_ENGINE=postgresql` |
| `postgres-setup.sql` | Cria usuário `crm_ti` e banco `crm_ti` no PostgreSQL |
| `gunicorn.service.exemple` | Unit do systemd apontando para `setup.wsgi` |
| `nginx.conf.exemple` | Proxy reverso, `/static/` e `/media/` |

## Fluxo de deploy (resumo)

1. Instalar no servidor: Python 3.12+, PostgreSQL, Nginx.
2. Clonar o projeto em `/var/www/branch-v2` (exemplo).
3. `python -m venv venv && source venv/bin/activate`
4. `pip install -r requirements.txt` (inclui `psycopg[binary]`).
5. Copiar `.vps/env.exemple` → `.env` na raiz e preencher senhas/hosts.
6. Executar `postgres-setup.sql` (ajustar senha antes).
7. Rodar migrações e `collectstatic` (comandos Django no servidor).
8. Configurar `gunicorn.service` e `nginx.conf`, reiniciar serviços.

## Variáveis PostgreSQL (`.env`)

| Variável | Exemplo | Descrição |
|----------|---------|-----------|
| `DB_ENGINE` | `postgresql` | Obrigatório na VPS |
| `DB_NAME` | `crm_ti` | Nome do database |
| `DB_USER` | `crm_ti` | Usuário do Postgres |
| `DB_PASSWORD` | — | Senha (obrigatória se `DEBUG=False`) |
| `DB_HOST` | `127.0.0.1` | Host do Postgres |
| `DB_PORT` | `5432` | Porta |
| `DB_CONN_MAX_AGE` | `600` | Pool de conexões (segundos) |
| `DB_SSLMODE` | `prefer` | Opcional (`disable`, `require`, etc.) |

Configuração lida em `setup/settings.py`.
