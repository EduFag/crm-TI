#!/usr/bin/env bash
# Configura chave SSH do usuário edufa para git fetch/pull no repositório GitHub.
# O GitHub Actions conecta como edufa — o deploy precisa de git funcionando para esse usuário.
#
# Rodar COMO edufa (não como root):
#   su - edufa -c 'bash /home/edufa/crm-TI/.vps/setup-git-deploy-key.sh'

set -euo pipefail

if [[ "$(whoami)" != "edufa" ]]; then
    echo "ERRO: execute como edufa, não como $(whoami)."
    echo "  su - edufa -c 'bash /home/edufa/crm-TI/.vps/setup-git-deploy-key.sh'"
    exit 1
fi

SSH_DIR="${HOME}/.ssh"
KEY="${SSH_DIR}/crm_ti_github_deploy"
CONFIG="${SSH_DIR}/config"
MARKER="# crm-ti deploy key"

mkdir -p "${SSH_DIR}"
chmod 700 "${SSH_DIR}"

if [[ ! -f "${KEY}" ]]; then
    echo "[setup-git] Gerando chave ${KEY} ..."
    ssh-keygen -t ed25519 -C "vps-edufa-crm-ti-deploy" -f "${KEY}" -N ""
    chmod 600 "${KEY}"
    chmod 644 "${KEY}.pub"
else
    echo "[setup-git] Chave já existe: ${KEY}"
fi

if [[ ! -f "${CONFIG}" ]] || ! grep -q "${MARKER}" "${CONFIG}" 2>/dev/null; then
    echo "[setup-git] Configurando ${CONFIG} ..."
    cat >> "${CONFIG}" <<EOF

Host github.com
    ${MARKER}
    HostName github.com
    User git
    IdentityFile ${KEY}
    IdentitiesOnly yes
EOF
    chmod 600 "${CONFIG}"
else
    echo "[setup-git] ${CONFIG} já contém entrada para github.com"
fi

echo ""
echo "=================================================================="
echo "1) Copie a chave pública abaixo"
echo "2) GitHub → repositório crm-TI → Settings → Deploy keys → Add deploy key"
echo "   Título: vps-edufa-crm-ti-deploy"
echo "   Marque só leitura (Allow read access) — o deploy só faz pull"
echo "=================================================================="
echo ""
cat "${KEY}.pub"
echo ""
echo "=================================================================="
echo "3) Teste (como edufa):"
echo "   ssh -T git@github.com"
echo "   cd /home/edufa/crm-TI && git fetch origin main"
echo "   bash /home/edufa/crm-TI/.vps/verify-deploy-permissions.sh"
echo "=================================================================="
