# Deploy — ti.moneypromotora.com.br

## 1. DNS (painel do domínio)

| Tipo | Nome | Valor        |
|------|------|--------------|
| A    | ti   | IP da VPS    |

Aguarde propagar (minutos a algumas horas). Teste: `ping ti.moneypromotora.com.br`

---

## 2. `.env` na VPS (`/home/edufa/crm-TI/.env`)

**Produção** — não use `DEBUG=True` nem só `127.0.0.1` nos hosts públicos:

```env
DJANGO_SECRET_KEY=chave-gerada-no-servidor
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=ti.moneypromotora.com.br,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://ti.moneypromotora.com.br
DJANGO_LANGUAGE_CODE=pt-br
DJANGO_TIME_ZONE=America/Sao_Paulo
DJANGO_STATIC_URL=static/
DJANGO_STATIC_ROOT=staticfiles

DB_ENGINE=postgresql
DB_NAME=crm_ti
DB_USER=crm_ti
DB_PASSWORD=SUA_SENHA
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=600
DB_SSLMODE=prefer
```

Gerar `DJANGO_SECRET_KEY`:

```bash
cd /home/edufa/crm-TI
source venv/bin/activate
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Dev local** (no seu PC) pode manter:

```env
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1,http://localhost
```

---

## 3. Django (no servidor)

```bash
cd /home/edufa/crm-TI
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

---

## 4. Gunicorn (systemd)

```bash
sudo cp /home/edufa/crm-TI/.vps/gunicorn.service.exemple /etc/systemd/system/crm-ti.service
sudo systemctl daemon-reload
sudo systemctl enable crm-ti
sudo systemctl start crm-ti
sudo systemctl status crm-ti
```

---

## 5. Nginx

Use **apenas** `crm-ti` (não duplique com `ti.moneypromotora.com.br`):

```bash
sudo cp /home/edufa/crm-TI/.vps/nginx.conf.exemple /etc/nginx/sites-available/crm-ti
sudo rm -f /etc/nginx/sites-enabled/ti.moneypromotora.com.br
sudo ln -sf /etc/nginx/sites-available/crm-ti /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Se existir `/etc/nginx/sites-available/ti.moneypromotora.com.br`, desative o symlink em `sites-enabled` (pode manter o arquivo como backup).

---

## 6. HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ti.moneypromotora.com.br
```

Confirme no `.env`:

```env
DJANGO_CSRF_TRUSTED_ORIGINS=https://ti.moneypromotora.com.br
```

Reinicie o Gunicorn após alterar `.env`:

```bash
sudo systemctl restart crm-ti
```

### Restart lento / página carregando infinitamente

Causas comuns neste projeto:

1. **SSE do helpdesk** (dashboard/kanban) mantém workers do Gunicorn ocupados. Com poucos workers, o restart espera essas conexões encerrarem.
2. **Sem `--preload`**, cada worker recarrega o Django inteiro após o restart (lento em VPS com pouca RAM).
3. **Nginx** sem `proxy_connect_timeout` baixo deixa o navegador esperando minutos com o Gunicorn fora do ar.

**Correção** — atualize os arquivos no servidor e recarregue:

```bash
cd /home/edufa/crm-TI && git pull   # ou copie as alterações manualmente
sudo cp /home/edufa/crm-TI/.vps/gunicorn.service.exemple /etc/systemd/system/crm-ti.service
sudo cp /home/edufa/crm-TI/.vps/nginx.conf.exemple /etc/nginx/sites-available/crm-ti
sudo systemctl daemon-reload
sudo systemctl restart crm-ti
sudo nginx -t && sudo systemctl reload nginx
```

**Deploy de código** (Python/templates, sem alterar `.env`): prefira reload suave em vez de restart completo:

```bash
sudo systemctl reload crm-ti
```

> `reload` só funciona se o unit tiver `ExecReload` (já incluso em `gunicorn.service.exemple`). Após atualizar o `.service`, rode `sudo systemctl daemon-reload` uma vez.

Se `reload` não estiver configurado ainda, use o sinal HUP direto no master do Gunicorn:

```bash
sudo kill -HUP $(systemctl show -p MainPID --value crm-ti)
```

**Alterou `.env`?** Use `sudo systemctl restart crm-ti` — variáveis de ambiente só são relidas no start.

### DisallowedHost em `ti.moneypromotora.com.br`

Se a página de erro mostrar **outro projeto** no `Python Path` (ex.: `/home/capitalcredito/...` em vez de `/home/edufa/crm-TI/`), o **Nginx está mandando o tráfego para o Gunicorn errado** — não basta alterar `ALLOWED_HOSTS` no capitalcredito.

**Causa frequente:** existe bloco só na porta **80** para `ti.moneypromotora.com.br`, mas **não existe bloco na 443**. O navegador acessa HTTPS e o Nginx usa o `default_server` de outro site (capitalcredito/moneylinkpro).

Confirme:

```bash
sudo nginx -T 2>/dev/null | grep -n "ti.moneypromotora.com.br"
curl -sI http://ti.moneypromotora.com.br/    # deve dar 302 → /login/
curl -sI https://ti.moneypromotora.com.br/   # se der erro de outro app, falta SSL do crm-ti
```

Crie/renove o HTTPS **só** para o subdomínio `ti`:

```bash
sudo certbot --nginx -d ti.moneypromotora.com.br
# Se já existir certificado: escolha opção 1 (reinstall)
sudo nginx -T 2>/dev/null | grep -A35 "server_name ti.moneypromotora.com.br"
# No bloco listen 443, proxy_pass deve ser http://127.0.0.1:9001
sudo nginx -t && sudo systemctl reload nginx
```

> **Não** rode `cp nginx.conf.exemple` depois que o certbot já configurou SSL — isso apaga o bloco `:443`. Use `certbot --nginx -d ti.moneypromotora.com.br` (opção 1 reinstall) para recriar o HTTPS.

Se o certbot criar `return 404` na porta 80, troque por redirect:

```nginx
server {
    listen 80;
    server_name ti.moneypromotora.com.br;
    return 301 https://$host$request_uri;
}
```

**Diagnóstico no servidor:**

```bash
# CRM TI deve estar ativo na 9001
sudo systemctl status crm-ti
curl -sI -H "Host: ti.moneypromotora.com.br" http://127.0.0.1:9001/

# Qual config atende o subdomínio (porta 80 e 443)
sudo nginx -T 2>/dev/null | grep -A30 "server_name ti.moneypromotora.com.br"

# Conferir symlinks (só um site para ti)
ls -la /etc/nginx/sites-enabled/ | grep -E 'crm-ti|ti\.'
```

O bloco `location /` de **ti.moneypromotora.com.br** (HTTP **e** HTTPS) deve ter:

```nginx
proxy_pass http://127.0.0.1:9001;
```

**Correção:**

```bash
sudo cp /home/edufa/crm-TI/.vps/nginx.conf.exemple /etc/nginx/sites-available/crm-ti
# Edite o bloco SSL (443) se o certbot criou proxy_pass para outra porta:
sudo nano /etc/nginx/sites-available/crm-ti
sudo rm -f /etc/nginx/sites-enabled/ti.moneypromotora.com.br
sudo ln -sf /etc/nginx/sites-available/crm-ti /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

No `.env` do CRM TI (`/home/edufa/crm-TI/.env`):

```env
DJANGO_ALLOWED_HOSTS=ti.moneypromotora.com.br,127.0.0.1,localhost
```

Após mudar `.env`: `sudo systemctl restart crm-ti`

---

## 7. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Não abra a porta **5432** (Postgres) na internet.

---

## Fluxo

```
Browser → ti.moneypromotora.com.br (443)
       → Nginx (static/media + proxy)
       → Gunicorn 127.0.0.1:9001
       → Django
       → PostgreSQL 127.0.0.1:5432
```
