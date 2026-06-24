# GitHub Actions — autodeploy na VPS

Quando houver **push na `main`**, o workflow [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) conecta na VPS por SSH e executa [`.vps/deploy.sh`](deploy.sh).

## O que o deploy faz

1. `git pull --ff-only origin main`
2. `pip install -r requirements.txt`
3. `python manage.py migrate --noinput`
4. `python manage.py collectstatic --noinput`
5. Ajuste de permissões em `staticfiles`
6. `systemctl reload crm-ti` (ou `restart` se reload falhar)

---

## 1. Gerar chave SSH (no seu PC ou na VPS)

```bash
ssh-keygen -t ed25519 -C "github-actions-crm-ti" -f github-actions-crm-ti -N ""
```

Arquivos gerados:

| Arquivo | Uso |
|---------|-----|
| `github-actions-crm-ti` | Chave **privada** → secret `SSH_PRIVATE_KEY` no GitHub |
| `github-actions-crm-ti.pub` | Chave **pública** → `authorized_keys` na VPS |

> **Nunca** commite a chave privada no repositório.

---

## 2. Configurar a VPS

Conecte na VPS como **root** ou **edufa**:

```bash
# Criar usuário de deploy (recomendado) ou usar edufa
# Opção A — usar o usuário edufa (já dono do projeto):
mkdir -p /home/edufa/.ssh
chmod 700 /home/edufa/.ssh
nano /home/edufa/.ssh/authorized_keys
# Cole o conteúdo de github-actions-crm-ti.pub (uma linha)
chmod 600 /home/edufa/.ssh/authorized_keys
chown -R edufa:edufa /home/edufa/.ssh
```

Permitir **sudo sem senha** só para o que o deploy precisa:

```bash
sudo visudo -f /etc/sudoers.d/crm-ti-deploy
```

Conteúdo (usuário `edufa`):

```
edufa ALL=(ALL) NOPASSWD: /bin/systemctl reload crm-ti, /bin/systemctl restart crm-ti, /bin/systemctl is-active crm-ti, /bin/systemctl status crm-ti, /usr/bin/chown, /bin/chmod
```

Tornar o script executável (uma vez):

```bash
chmod +x /home/edufa/crm-TI/.vps/deploy.sh
chown edufa:edufa /home/edufa/crm-TI/.vps/deploy.sh
```

Testar SSH do seu PC:

```bash
ssh -i github-actions-crm-ti edufa@IP_DA_VPS "cd /home/edufa/crm-TI && bash .vps/deploy.sh"
```

---

## 3. Secrets no GitHub (dono do repositório)

Repositório → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | Valor | Exemplo |
|--------|-------|---------|
| `SSH_HOST` | IP ou hostname da VPS | `123.45.67.89` ou `srv810546.hstgr.cloud` |
| `SSH_USER` | Usuário SSH | `edufa` |
| `SSH_PRIVATE_KEY` | Conteúdo completo do arquivo `github-actions-crm-ti` | `-----BEGIN OPENSSH PRIVATE KEY-----` ... |
| `SSH_PORT` | (opcional) Porta SSH | `22` |

O dono (`EduFag`) precisa cadastrar esses secrets — colaboradores não veem secrets existentes.

---

## 4. Git na VPS (pull do GitHub)

O `git pull` na VPS já funciona hoje; mantenha assim:

- **HTTPS:** token de acesso em `git credential` ou `.git-credentials`
- **SSH:** deploy key da VPS em **Settings → Deploy keys** do repo

Sem isso, o script falha no `git pull`.

---

## 5. Disparar deploy manualmente

GitHub → **Actions** → **Deploy VPS** → **Run workflow**

Ou push na `main`:

```bash
git push origin main
```

---

## Troubleshooting

| Erro | Solução |
|------|---------|
| `Permission denied (publickey)` | Conferir `SSH_PRIVATE_KEY` e `authorized_keys` |
| `sudo: a password is required` | Ajustar `/etc/sudoers.d/crm-ti-deploy` |
| `git pull` falha | Credenciais Git na VPS ou deploy key |
| `Not possible to fast-forward` | Na VPS: `git fetch && git reset --hard origin/main` (uma vez) |
| Serviço não sobe | `sudo systemctl status crm-ti` e logs do Gunicorn |
