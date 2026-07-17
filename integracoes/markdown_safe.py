"""Renderização leve e segura de Markdown para o chat de memória."""

from __future__ import annotations

import html
import re

from django.utils.safestring import mark_safe

_RE_BOLD = re.compile(r'\*\*(.+?)\*\*')
_RE_ITALIC = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)')
_RE_CODE = re.compile(r'`([^`]+)`')
_RE_LINK = re.compile(r'\[([^\]]+)\]\((https?://[^)\s]+)\)')


def _inline(texto: str) -> str:
    """Aplica formatação inline em texto já escapado."""
    texto = _RE_CODE.sub(r'<code class="memoria-md-code">\1</code>', texto)
    texto = _RE_LINK.sub(
        r'<a href="\2" class="memoria-md-link" target="_blank" rel="noopener noreferrer">\1</a>',
        texto,
    )
    texto = _RE_BOLD.sub(r'<strong>\1</strong>', texto)
    texto = _RE_ITALIC.sub(r'<em>\1</em>', texto)
    return texto


def render_markdown_leve(texto: str) -> str:
    """
    Converte Markdown simples em HTML seguro (escapa primeiro).
    Suporta: negrito, itálico, código inline, links https, títulos, listas e parágrafos.
    """
    if not texto:
        return ''

    linhas = texto.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    blocos: list[str] = []
    i = 0
    n = len(linhas)

    while i < n:
        linha = linhas[i]
        stripped = linha.strip()

        if not stripped:
            i += 1
            continue

        # Título # ## ###
        m_h = re.match(r'^(#{1,3})\s+(.+)$', stripped)
        if m_h:
            nivel = len(m_h.group(1))
            conteudo = _inline(html.escape(m_h.group(2).strip()))
            blocos.append(f'<h{nivel} class="memoria-md-h">{conteudo}</h{nivel}>')
            i += 1
            continue

        # Lista numerada
        if re.match(r'^\d+\.\s+', stripped):
            itens: list[str] = []
            while i < n:
                s = linhas[i].strip()
                m = re.match(r'^\d+\.\s+(.+)$', s)
                if not m:
                    break
                itens.append(f'<li>{_inline(html.escape(m.group(1).strip()))}</li>')
                i += 1
            blocos.append(f'<ol class="memoria-md-list">{"".join(itens)}</ol>')
            continue

        # Lista com marcadores
        if re.match(r'^[-*•]\s+', stripped):
            itens = []
            while i < n:
                s = linhas[i].strip()
                m = re.match(r'^[-*•]\s+(.+)$', s)
                if not m:
                    break
                itens.append(f'<li>{_inline(html.escape(m.group(1).strip()))}</li>')
                i += 1
            blocos.append(f'<ul class="memoria-md-list">{"".join(itens)}</ul>')
            continue

        # Parágrafo (linhas até linha em branco ou início de outro bloco)
        partes: list[str] = []
        while i < n:
            s = linhas[i].strip()
            if not s:
                break
            if re.match(r'^(#{1,3}\s+|\d+\.\s+|[-*•]\s+)', s):
                break
            partes.append(_inline(html.escape(s)))
            i += 1
        if partes:
            blocos.append(f'<p class="memoria-md-p">{"<br>".join(partes)}</p>')

    return ''.join(blocos) or f'<p class="memoria-md-p">{_inline(html.escape(texto.strip()))}</p>'


def markdown_leve_safe(texto: str):
    """Versão mark_safe para templates Django."""
    return mark_safe(render_markdown_leve(texto or ''))
