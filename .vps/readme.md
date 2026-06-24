# Pasta `.vps/`

Configurações de **produção** (VPS/cloud): PostgreSQL, Gunicorn, Nginx e `.env` de exemplo.

## Arquivos

| Arquivo | Uso |
|---------|-----|
| [DOCUMENTACAO.md](DOCUMENTACAO.md) | Guia completo de deploy |
| [instalar-postgresql.md](instalar-postgresql.md) | Instalar Postgres na VPS (apt → criar banco) |
| [deploy-ti.moneypromotora.com.br.md](deploy-ti.moneypromotora.com.br.md) | Deploy Gunicorn + Nginx + SSL do subdomínio |
| [github-actions-setup.md](github-actions-setup.md) | Autodeploy via GitHub Actions (push na `main`) |
| `deploy.sh` | Script executado na VPS pelo workflow |
| `env.exemple` | Modelo `.env` com `DB_ENGINE=postgresql` |
| `postgres-setup.sql` | Criar banco/usuário no Postgres |
| `gunicorn.service.exemple` | Serviço systemd |
| `nginx.conf.exemple` | Proxy reverso |

## Copiar exemplos → arquivos reais na VPS

Após `git pull` em `/home/edufa/crm-TI`, use estes comandos (ajuste o caminho do projeto se necessário):

| Exemplo no repositório | Arquivo real no servidor | Comando `cp` |
|------------------------|--------------------------|--------------|
| `.vps/gunicorn.service.exemple` | `/etc/systemd/system/crm-ti.service` | `sudo cp /home/edufa/crm-TI/.vps/gunicorn.service.exemple /etc/systemd/system/crm-ti.service` |
| `.vps/nginx.conf.exemple` | `/etc/nginx/sites-available/crm-ti` | `sudo cp /home/edufa/crm-TI/.vps/nginx.conf.exemple /etc/nginx/sites-available/crm-ti` |
| `.vps/env.exemple` | `/home/edufa/crm-TI/.env` | `cp /home/edufa/crm-TI/.vps/env.exemple /home/edufa/crm-TI/.env` *(edite senhas depois; não sobrescreva .env em produção sem backup)* |

**Após copiar gunicorn:**

```bash
sudo systemctl daemon-reload
sudo systemctl restart crm-ti
```

**Após copiar nginx** — use `cp` do exemplo **só na primeira instalação** (sem SSL). Se o certbot já rodou, **não sobrescreva** o arquivo; edite com `nano` ou rode `sudo certbot --nginx -d ti.moneypromotora.com.br` (opção 1 reinstall):

```bash
sudo ln -sf /etc/nginx/sites-available/crm-ti /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**Código Python** (ex.: `helpdesk/views/poll.py`): só `git pull` + reload do Gunicorn:

```bash
cd /home/edufa/crm-TI && git pull
sudo systemctl reload crm-ti
# ou, se reload ainda não configurado:
sudo kill -HUP $(systemctl show -p MainPID --value crm-ti)
```

## Desenvolvimento local com PostgreSQL

1. Instale PostgreSQL e crie o banco (`postgres-setup.sql`).
2. No `.env`, use o **perfil B** descrito em `.env.exemple` (comentar SQLite).
3. `pip install -r requirements.txt`
4. Rode migrações no seu ambiente.

> Arquivos desta pasta não são executados pelo Cursor; são referência para o servidor.
