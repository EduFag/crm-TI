# Pasta `.vps/`

Configurações de **produção** (VPS/cloud): PostgreSQL, Gunicorn, Nginx e `.env` de exemplo.

## Arquivos

| Arquivo | Uso |
|---------|-----|
| [DOCUMENTACAO.md](DOCUMENTACAO.md) | Guia completo de deploy |
| [instalar-postgresql.md](instalar-postgresql.md) | Instalar Postgres na VPS (apt → criar banco) |
| [deploy-ti.moneypromotora.com.br.md](deploy-ti.moneypromotora.com.br.md) | Deploy Gunicorn + Nginx + SSL do subdomínio |
| `env.exemple` | Modelo `.env` com `DB_ENGINE=postgresql` |
| `postgres-setup.sql` | Criar banco/usuário no Postgres |
| `gunicorn.service.exemple` | Serviço systemd |
| `nginx.conf.exemple` | Proxy reverso |

## Desenvolvimento local com PostgreSQL

1. Instale PostgreSQL e crie o banco (`postgres-setup.sql`).
2. No `.env`, use o **perfil B** descrito em `.env.exemple` (comentar SQLite).
3. `pip install -r requirements.txt`
4. Rode migrações no seu ambiente.

> Arquivos desta pasta não são executados pelo Cursor; são referência para o servidor.
