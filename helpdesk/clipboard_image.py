"""Baixa imagens/GIFs colados via URL (Win+. Tenor, Google, etc.)."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from django.core.files.uploadedfile import SimpleUploadedFile

MAX_BYTES = 5 * 1024 * 1024

# Hosts comuns de GIF/emoji picker e busca de imagens
_HOST_SUFFIXES = (
    'tenor.com',
    'giphy.com',
    'googleusercontent.com',
    'ggpht.com',
    'google.com',
    'gstatic.com',
    'imgur.com',
    'discordapp.com',
    'discord.com',
    'discordapp.net',
    'twimg.com',
    'pinimg.com',
    'media.tenor.cn',
)


def _host_permitido(hostname: str) -> bool:
    h = (hostname or '').lower().rstrip('.')
    if not h:
        return False
    for suffix in _HOST_SUFFIXES:
        if h == suffix or h.endswith('.' + suffix):
            return True
    return False


def _ip_publico(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolver_host_publico(hostname: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError('Não foi possível resolver o host da imagem.') from exc
    if not infos:
        raise ValueError('Host da imagem sem endereço.')
    for info in infos:
        if not _ip_publico(info[4][0]):
            raise ValueError('Host da imagem não permitido.')


def _ext_e_content_type(content_type: str, url: str) -> tuple[str, str]:
    ct = (content_type or '').split(';')[0].strip().lower()
    mapa = {
        'image/gif': ('.gif', 'image/gif'),
        'image/png': ('.png', 'image/png'),
        'image/jpeg': ('.jpg', 'image/jpeg'),
        'image/jpg': ('.jpg', 'image/jpeg'),
        'image/webp': ('.webp', 'image/webp'),
        'image/bmp': ('.bmp', 'image/bmp'),
    }
    if ct in mapa:
        return mapa[ct]
    path = urlparse(url).path.lower()
    for ext, mime in (
        ('.gif', 'image/gif'),
        ('.png', 'image/png'),
        ('.jpg', 'image/jpeg'),
        ('.jpeg', 'image/jpeg'),
        ('.webp', 'image/webp'),
    ):
        if path.endswith(ext):
            return (ext if ext != '.jpeg' else '.jpg', mime)
    return ('.gif', 'image/gif')


def baixar_imagem_remota(url: str) -> SimpleUploadedFile:
    """
    Baixa imagem/GIF de URL https de hosts conhecidos.
    Levanta ValueError com mensagem amigável em falha.
    """
    url = (url or '').strip()
    if not url or len(url) > 2048:
        raise ValueError('URL da imagem inválida.')

    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        raise ValueError('Use uma URL HTTPS de imagem válida.')

    if not _host_permitido(parsed.hostname):
        raise ValueError('Origem da imagem não suportada para cola automática.')

    _resolver_host_publico(parsed.hostname)

    try:
        with httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            max_redirects=3,
            headers={'User-Agent': 'CRM-Helpdesk-GIF/1.0'},
        ) as client:
            with client.stream('GET', url) as resp:
                if resp.status_code >= 400:
                    raise ValueError('Não foi possível baixar a imagem.')
                # Valida redirects para hosts permitidos
                for r in resp.history:
                    host = urlparse(str(r.url)).hostname
                    if host and not _host_permitido(host):
                        raise ValueError('Redirecionamento para origem não suportada.')
                final_host = urlparse(str(resp.url)).hostname
                if final_host and not _host_permitido(final_host):
                    raise ValueError('Origem final da imagem não suportada.')
                if final_host:
                    _resolver_host_publico(final_host)

                content_type = resp.headers.get('content-type', '')
                if content_type and not content_type.lower().startswith('image/'):
                    raise ValueError('O link não aponta para uma imagem.')

                chunks: list[bytes] = []
                total = 0
                for chunk in resp.iter_bytes():
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError('A imagem excede o limite de 5MB.')
                    chunks.append(chunk)
                data = b''.join(chunks)
    except httpx.HTTPError as exc:
        raise ValueError('Falha ao baixar a imagem da internet.') from exc

    if not data:
        raise ValueError('Imagem vazia.')

    ext, mime = _ext_e_content_type(content_type, url)
    nome = f'gif_colado_{abs(hash(url)) % 10_000_000}{ext}'
    return SimpleUploadedFile(nome, data, content_type=mime)
