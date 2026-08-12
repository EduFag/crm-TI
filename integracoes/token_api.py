"""Geração, hash e autenticação de tokens de API externa."""

from __future__ import annotations

import hashlib
import secrets
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import CustomUser
from integracoes.models import TokenApiExterna

User = get_user_model()

# Tamanho do token em texto claro (bytes → hex = 2x)
TOKEN_BYTES = 32
PREFIXO_LEN = 8


def usuario_pode_token_api(user) -> bool:
    """TI (IT_USER), staff ou superuser ativos podem gerar/usar token de API."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    role = getattr(user, 'role', None)
    return role == CustomUser.RoleChoices.IT_USER


def gerar_token_plaintext() -> str:
    """Gera token aleatório em hex (seguro para header Bearer)."""
    return secrets.token_hex(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """SHA-256 hex do token (armazenamento sem texto claro)."""
    return hashlib.sha256((token or '').encode('utf-8')).hexdigest()


def criar_token(user, nome: str) -> Tuple[TokenApiExterna, str]:
    """
    Cria TokenApiExterna e devolve (instância, token_plaintext).
    O plaintext só deve ser exibido uma vez na UI.
    """
    nome_limpo = (nome or '').strip()
    if not nome_limpo:
        raise ValueError('Informe um nome para o token.')
    if not usuario_pode_token_api(user):
        raise PermissionError('Usuário sem permissão para gerar token de API.')

    plaintext = gerar_token_plaintext()
    obj = TokenApiExterna.objects.create(
        user=user,
        nome=nome_limpo[:120],
        prefixo=plaintext[:PREFIXO_LEN],
        token_hash=hash_token(plaintext),
        ativo=True,
    )
    return obj, plaintext


def _marcar_uso(token_obj: TokenApiExterna) -> None:
    TokenApiExterna.objects.filter(pk=token_obj.pk).update(ultimo_uso=timezone.now())


def autenticar_username_token(
    username: str,
    token: str,
) -> Tuple[Optional[User], Optional[TokenApiExterna], Optional[str]]:
    """
    Valida username + token.
    Retorna (user, token_obj, erro). Em sucesso erro é None.
    """
    username = (username or '').strip()
    token = (token or '').strip()
    if not username or not token:
        return None, None, 'Informe username e token.'

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return None, None, 'Credenciais inválidas.'

    if not user.is_active:
        return None, None, 'Usuário inativo.'
    if not usuario_pode_token_api(user):
        return None, None, 'Usuário sem permissão para API externa.'

    digest = hash_token(token)
    token_obj = (
        TokenApiExterna.objects.filter(user=user, token_hash=digest, ativo=True)
        .select_related('user')
        .first()
    )
    if not token_obj:
        return None, None, 'Credenciais inválidas.'

    # Comparação constante no hash (já filtrado por igualdade; reforço)
    if not secrets.compare_digest(token_obj.token_hash, digest):
        return None, None, 'Credenciais inválidas.'

    _marcar_uso(token_obj)
    return user, token_obj, None


def resolver_user_por_bearer(
    token: str,
) -> Tuple[Optional[User], Optional[TokenApiExterna], Optional[str]]:
    """
    Resolve usuário a partir do token Bearer.
    Retorna (user, token_obj, erro).
    """
    token = (token or '').strip()
    if not token:
        return None, None, 'Token Bearer obrigatório.'

    digest = hash_token(token)
    token_obj = (
        TokenApiExterna.objects.filter(token_hash=digest, ativo=True)
        .select_related('user')
        .first()
    )
    if not token_obj:
        return None, None, 'Token inválido.'

    if not secrets.compare_digest(token_obj.token_hash, digest):
        return None, None, 'Token inválido.'

    user = token_obj.user
    if not user.is_active:
        return None, None, 'Usuário inativo.'
    if not usuario_pode_token_api(user):
        return None, None, 'Usuário sem permissão para API externa.'

    _marcar_uso(token_obj)
    return user, token_obj, None
