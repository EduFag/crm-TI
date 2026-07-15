"""Criptografia Fernet para credenciais de IA (at-rest)."""

from __future__ import annotations

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    """Deriva chave Fernet estável a partir do SECRET_KEY do Django."""
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    chave = base64.urlsafe_b64encode(digest)
    return Fernet(chave)


def encrypt_credentials(data: dict) -> str:
    """Serializa dict em JSON e criptografa."""
    bruto = json.dumps(data, ensure_ascii=False).encode('utf-8')
    return _fernet().encrypt(bruto).decode('utf-8')


def decrypt_credentials(blob: str) -> dict:
    """Descriptografa blob e devolve dict (vazio se inválido)."""
    if not blob:
        return {}
    try:
        bruto = _fernet().decrypt(blob.encode('utf-8'))
        return json.loads(bruto.decode('utf-8'))
    except (InvalidToken, json.JSONDecodeError, TypeError, ValueError):
        return {}


def mascarar_token(hint: str) -> str:
    """Exibe token mascarado com dica dos últimos caracteres."""
    hint = (hint or '').strip()
    if not hint:
        return '••••••••'
    return f'••••••••{hint}'
