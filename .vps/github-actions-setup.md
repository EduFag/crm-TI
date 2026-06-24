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

Conteúdo (usuário `edufa`) — copie de [`.vps/crm-ti-deploy.sudoers.exemple`](crm-ti-deploy.sudoers.exemple):

```bash
sudo visudo -f /etc/sudoers.d/crm-ti-deploy
# Cole o conteúdo do arquivo crm-ti-deploy.sudoers.exemple
sudo chmod 440 /etc/sudoers.d/crm-ti-deploy
```

Validar **como edufa** (não como root):

```bash
su - edufa -c 'bash /home/edufa/crm-TI/.vps/verify-deploy-permissions.sh'
```

Instalar o unit com **ExecReload** (uma vez, como root):

```bash
sudo bash /home/edufa/crm-TI/.vps/install-crm-ti-service.sh
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

## 4. Git na VPS (usuário `edufa`)

O deploy roda como **edufa**. O `git fetch` que funciona como **root** não vale para o Actions — cada usuário usa sua própria chave SSH.

### Configurar deploy key (recomendado)

Na VPS, **como edufa**:

```bash
cd /home/edufa/crm-TI
git pull origin main   # se ainda não tiver os scripts .vps/, faça pull como root uma vez e ajuste dono:
# sudo chown -R edufa:edufa /home/edufa/crm-TI

bash .vps/setup-git-deploy-key.sh
```

Copie a chave pública exibida e cadastre em:

**GitHub → crm-TI → Settings → Deploy keys → Add deploy key**

| Campo | Valor |
|-------|--------|
| Title | `vps-edufa-crm-ti-deploy` |
| Key | conteúdo de `~/.ssh/crm_ti_github_deploy.pub` |
| Write access | **desmarcado** (só leitura) |

Teste:

```bash
ssh -T git@github.com
# Esperado: "Hi EduFag/crm-TI! You've successfully authenticated..."

cd /home/edufa/crm-TI && git fetch origin main
bash .vps/verify-deploy-permissions.sh
```

### Alternativa: HTTPS com token

Se o `origin` for HTTPS (`https://github.com/EduFag/crm-TI.git`):

```bash
git config --global credential.helper store
git fetch origin main
# Username: EduFag
# Password: <Personal Access Token com escopo repo>
```

> **Não** use senha da conta GitHub — só PAT.

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
| `git@github.com: Permission denied (publickey)` como edufa | Rodar `bash .vps/setup-git-deploy-key.sh` como edufa e cadastrar Deploy key no GitHub |
| `Permission denied (publickey)` SSH Actions | Conferir `SSH_PRIVATE_KEY` e `authorized_keys` do usuário `edufa` |
| `sudo: a password is required` | Atualizar `/etc/sudoers.d/crm-ti-deploy` (modelo em `crm-ti-deploy.sudoers.exemple`) |
| Action falha mas manual como root funciona | Actions usa `edufa`; rode `verify-deploy-permissions.sh` como edufa, não como root |
| `git pull` falha | Credenciais Git na VPS ou deploy key |
| `Not possible to fast-forward` | Na VPS: `git fetch && git reset --hard origin/main` (uma vez) |
| Serviço não sobe | `sudo systemctl status crm-ti` e logs do Gunicorn |
