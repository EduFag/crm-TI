"""Versão automática do frontend helpdesk baseada no commit git atual.

Usada em ?v= nos statics e URLs HTMX. Prioridade:
1. HELPDESK_FRONTEND_VERSION no ambiente (override opcional)
2. hash curto do HEAD (`git rev-parse --short HEAD`)
3. arquivo helpdesk/.frontend_git_version (útil se o deploy não tiver pasta .git)
4. fallback 'dev'
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

# Fallback só se git e arquivo de versão estiverem indisponíveis
_FALLBACK = 'dev'


def _ler_arquivo_versao(base_dir: Path) -> str:
    caminho = base_dir / 'helpdesk' / '.frontend_git_version'
    if not caminho.is_file():
        return ''
    try:
        return caminho.read_text(encoding='utf-8').strip()
    except OSError:
        return ''


def _hash_git_curto(base_dir: Path) -> str:
    try:
        resultado = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=str(base_dir),
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if resultado.returncode == 0:
            return (resultado.stdout or '').strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ''


@lru_cache(maxsize=1)
def resolver_versao_frontend(base_dir: str | Path | None = None) -> str:
    """Resolve a versão uma vez por processo (cache)."""
    override = (os.environ.get('HELPDESK_FRONTEND_VERSION') or '').strip()
    if override:
        return override

    raiz = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
    git_hash = _hash_git_curto(raiz)
    if git_hash:
        return git_hash

    arquivo = _ler_arquivo_versao(raiz)
    if arquivo:
        return arquivo

    return _FALLBACK


# Compatibilidade: constante resolvida no import (settings / templates)
HELPDESK_FRONTEND_VERSION = resolver_versao_frontend()
