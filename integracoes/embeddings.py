"""Pipeline de embeddings e score híbrido para AssistenteChunk."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from django.utils import timezone

from integracoes.llm import LlmError, MODELO_EMBEDDING_PADRAO, obter_embedding, obter_integracao_embedding

if TYPE_CHECKING:
    from integracoes.models import AssistenteChunk

logger = logging.getLogger(__name__)

# Peso do cosine vs keyword no score híbrido
ALPHA_SEMANTICO = 0.65


def texto_para_embedding(chunk: AssistenteChunk) -> str:
    """Monta o texto indexado (título + categoria + tags + conteúdo)."""
    tags = chunk.tags if isinstance(chunk.tags, list) else []
    tags_txt = ', '.join(str(t) for t in tags if t)
    partes = [
        chunk.titulo or '',
        chunk.categoria_hint or '',
        tags_txt,
        chunk.conteudo or '',
    ]
    return '\n'.join(p for p in partes if p).strip()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similaridade cosseno; 0 se dimensões incompatíveis ou norma zero."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        fx = float(x)
        fy = float(y)
        dot += fx * fy
        na += fx * fx
        nb += fy * fy
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def atualizar_embedding_chunk(chunk: AssistenteChunk) -> bool:
    """Calcula e persiste embedding do chunk. Retorna True se ok; False se falhou/sem provedor."""
    if not obter_integracao_embedding():
        return False
    texto = texto_para_embedding(chunk)
    if not texto:
        return False
    try:
        vetor, modelo = obter_embedding(texto)
    except LlmError as exc:
        logger.warning('embedding falhou chunk=%s: %s', chunk.pk, exc)
        return False
    chunk.embedding = vetor
    chunk.embedding_modelo = (modelo or MODELO_EMBEDDING_PADRAO)[:80]
    chunk.embedding_em = timezone.now()
    chunk.save(update_fields=['embedding', 'embedding_modelo', 'embedding_em', 'atualizado_em'])
    return True


def recalcular_embeddings(
    *,
    so_pendentes: bool = True,
    limite: int = 80,
) -> dict:
    """
    Recalcula embeddings de chunks ativos.
    so_pendentes: só sem vetor ou com modelo diferente do padrão.
    """
    from integracoes.models import AssistenteChunk

    if not obter_integracao_embedding():
        return {
            'ok': False,
            'error': 'Sem integração ChatGPT ativa para embeddings.',
            'ok_count': 0,
            'fail_count': 0,
            'skipped': 0,
        }

    qs = AssistenteChunk.objects.filter(ativo=True).order_by('-atualizado_em')
    if so_pendentes:
        # Sem embedding ou modelo desatualizado
        candidatos = []
        for ch in qs[:400]:
            if not ch.embedding or ch.embedding_modelo != MODELO_EMBEDDING_PADRAO:
                candidatos.append(ch)
            if len(candidatos) >= limite:
                break
    else:
        candidatos = list(qs[:limite])

    ok_count = 0
    fail_count = 0
    for ch in candidatos:
        if atualizar_embedding_chunk(ch):
            ok_count += 1
        else:
            fail_count += 1

    return {
        'ok': True,
        'ok_count': ok_count,
        'fail_count': fail_count,
        'skipped': 0,
        'modelo': MODELO_EMBEDDING_PADRAO,
    }


def score_hibrido(
    keyword_score: float,
    keyword_max: float,
    cosine: float,
    tem_embedding: bool,
    *,
    alpha: float = ALPHA_SEMANTICO,
) -> float:
    """Combina cosine [0..1] com keyword normalizado. Sem embedding, só keyword."""
    kw_norm = 0.0
    if keyword_max > 0:
        kw_norm = min(1.0, max(0.0, keyword_score / keyword_max))
    if not tem_embedding:
        return kw_norm
    cos_n = max(0.0, min(1.0, cosine))
    return alpha * cos_n + (1.0 - alpha) * kw_norm
