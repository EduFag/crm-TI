#!/usr/bin/env bash
# Diagnóstico do serviço crm-ti — rode na VPS:
#   bash /home/edufa/crm-TI/.vps/diagnose-crm-ti.sh
# Como root (journal completo):
#   sudo bash /home/edufa/crm-TI/.vps/diagnose-crm-ti.sh

set -euo pipefail

APP_DIR="/home/edufa/crm-TI"
VENV="${APP_DIR}/myvenv"
SERVICE="crm-ti"
PORT=9001

echo "=== Diagnóstico ${SERVICE} ==="
echo "Data: $(date)"
echo

echo "--- Status systemd ---"
systemctl status "${SERVICE}" --no-pager 2>/dev/null || sudo systemctl status "${SERVICE}" --no-pager || true
echo

echo "--- Journal (últimas 60 linhas) ---"
journalctl -u "${SERVICE}" -n 60 --no-pager 2>/dev/null \
    || sudo journalctl -u "${SERVICE}" -n 60 --no-pager || true
echo

echo "--- Porta ${PORT} ---"
ss -tlnp 2>/dev/null | grep ":${PORT} " || sudo ss -tlnp | grep ":${PORT} " || echo "(porta livre ou ss indisponível)"
echo

echo "--- Django check ---"
cd "${APP_DIR}"
# shellcheck source=/dev/null
source "${VENV}/bin/activate"
python manage.py check
echo

echo "--- Teste Gunicorn (5s, porta ${PORT}) ---"
echo "Se falhar, o erro abaixo indica a causa do serviço não subir:"
timeout 5 "${VENV}/bin/gunicorn" setup.wsgi:application \
    --bind "127.0.0.1:${PORT}" \
    --workers 1 \
    --timeout 30 \
    --preload 2>&1 || true

echo
echo "=== Fim do diagnóstico ==="
