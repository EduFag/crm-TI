"""
Conversão local de anexos → texto (sem IA multimodal).

Usado quando a integração ativa (ex.: DeepSeek) não lê imagem/PDF:
- Imagens: OCR (RapidOCR / onnxruntime)
- PDFs: texto embutido (pypdf) e, se vazio, render + OCR (PyMuPDF)
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_ocr_engine: Any = None
_ocr_falhou_init = False

# Limite de páginas OCR em PDF escaneado (custo de CPU)
_MAX_PAGINAS_OCR_PDF = 5
_MAX_CHARS = 12000


def _limpar_texto(texto: str) -> str:
    texto = (texto or '').replace('\x00', ' ')
    texto = re.sub(r'[ \t]+\n', '\n', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    texto = re.sub(r'[ \t]{2,}', ' ', texto)
    return texto.strip()


def _truncar(texto: str, limite: int = _MAX_CHARS) -> str:
    texto = _limpar_texto(texto)
    if len(texto) <= limite:
        return texto
    return texto[: limite - 30].rstrip() + '\n\n[…texto truncado…]'


def _obter_ocr():
    """Lazy-init do RapidOCR (modelo onnx — sem tesseract no SO)."""
    global _ocr_engine, _ocr_falhou_init
    if _ocr_engine is not None:
        return _ocr_engine
    if _ocr_falhou_init:
        return None
    try:
        from rapidocr_onnxruntime import RapidOCR

        _ocr_engine = RapidOCR()
        logger.info('OCR local RapidOCR inicializado.')
        return _ocr_engine
    except Exception:
        logger.exception('Falha ao inicializar RapidOCR')
        _ocr_falhou_init = True
        return None


def _ocr_numpy(img_array) -> str:
    engine = _obter_ocr()
    if engine is None:
        raise RuntimeError(
            'OCR local indisponível (instale rapidocr-onnxruntime).'
        )
    result, _elapse = engine(img_array)
    if not result:
        return ''
    # Cada item: [box, text, score]
    linhas = []
    for item in result:
        if not item or len(item) < 2:
            continue
        txt = str(item[1] or '').strip()
        if txt:
            linhas.append(txt)
    return _limpar_texto('\n'.join(linhas))


def _pil_para_numpy(img):
    import numpy as np

    return np.array(img.convert('RGB'))


def extrair_texto_imagem_bytes(raw: bytes) -> str:
    """OCR em bytes de imagem (qualquer formato suportado pelo Pillow)."""
    from PIL import Image

    if not raw:
        return ''
    img = Image.open(io.BytesIO(raw))
    if getattr(img, 'n_frames', 1) > 1:
        img.seek(0)
    img = img.convert('RGB')
    # OCR fica mais estável em resoluções moderadas
    max_lado = 2000
    w, h = img.size
    if max(w, h) > max_lado:
        img.thumbnail((max_lado, max_lado), Image.Resampling.LANCZOS)
    return _truncar(_ocr_numpy(_pil_para_numpy(img)))


def extrair_texto_pdf_bytes(raw: bytes) -> tuple[str, str]:
    """
    Extrai texto de PDF.
    Retorna (texto, metodo) onde metodo é 'pdf_texto' | 'pdf_ocr' | 'vazio'.
    """
    if not raw:
        return '', 'vazio'

    texto_nativo = _texto_pdf_nativo(raw)
    # Heurística: PDF “com texto” vs escaneado
    if len(re.sub(r'\s+', '', texto_nativo)) >= 40:
        return _truncar(texto_nativo), 'pdf_texto'

    texto_ocr = _texto_pdf_via_ocr(raw)
    if texto_ocr:
        # Combina nativo residual + OCR se houver pouco nativo
        if texto_nativo.strip():
            combinado = texto_nativo.strip() + '\n\n' + texto_ocr
            return _truncar(combinado), 'pdf_ocr'
        return _truncar(texto_ocr), 'pdf_ocr'

    if texto_nativo.strip():
        return _truncar(texto_nativo), 'pdf_texto'
    return '', 'vazio'


def _texto_pdf_nativo(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning('pypdf não instalado')
        return ''

    try:
        reader = PdfReader(io.BytesIO(raw))
        partes = []
        for i, page in enumerate(reader.pages):
            if i >= 30:
                partes.append('[…demais páginas omitidas…]')
                break
            try:
                partes.append(page.extract_text() or '')
            except Exception:
                continue
        return _limpar_texto('\n\n'.join(partes))
    except Exception:
        logger.exception('Falha ao extrair texto nativo do PDF')
        return ''


def _texto_pdf_via_ocr(raw: bytes) -> str:
    """Renderiza páginas do PDF e aplica OCR (PDFs escaneados)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning('pymupdf não instalado — OCR de PDF escaneado indisponível')
        return ''

    try:
        doc = fitz.open(stream=raw, filetype='pdf')
    except Exception:
        logger.exception('Falha ao abrir PDF com PyMuPDF')
        return ''

    partes: list[str] = []
    try:
        n = min(len(doc), _MAX_PAGINAS_OCR_PDF)
        for i in range(n):
            page = doc[i]
            # 2x zoom melhora OCR de prints/scans
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            png_bytes = pix.tobytes('png')
            try:
                trecho = extrair_texto_imagem_bytes(png_bytes)
            except Exception:
                logger.exception('OCR falhou na página %s do PDF', i + 1)
                continue
            if trecho:
                partes.append(f'--- Página {i + 1} ---\n{trecho}')
        if len(doc) > _MAX_PAGINAS_OCR_PDF:
            partes.append(
                f'[OCR limitado às primeiras {_MAX_PAGINAS_OCR_PDF} páginas '
                f'de {len(doc)}.]'
            )
    finally:
        doc.close()

    return _limpar_texto('\n\n'.join(partes))


def formatar_resultado_ocr(texto: str, *, origem: str = 'imagem') -> str:
    """Monta texto pronto para o contexto do Assistente / DeepSeek."""
    texto = _limpar_texto(texto)
    if not texto:
        return (
            f'[OCR local] Nenhum texto legível encontrado neste {origem}. '
            'Use título, descrição e categoria do chamado. '
            'Se o sistema não estiver claro, pergunte MoneyConsig vs Discador JoyTec.'
        )
    rotulo = {
        'imagem': 'Texto extraído do print (OCR local, sem IA de visão)',
        'pdf_texto': 'Texto extraído do PDF (camada de texto)',
        'pdf_ocr': 'Texto extraído do PDF (OCR local em páginas escaneadas)',
    }.get(origem, f'Texto extraído ({origem})')
    dica = ''
    low = texto.lower()
    if any(x in low for x in ('joytec', 'ramal web', 'campanha', 'disponibilidade', 'em chamada')):
        dica = (
            '\n[Indício OCR: parece Discador JoyTec — não assuma MoneyConsig sem confirmação.]'
        )
    elif any(x in low for x in ('moneypromotora', 'moneyconsig', 'ranking inss')):
        dica = '\n[Indício OCR: parece MoneyConsig.]'
    return f'{rotulo}:\n{texto}{dica}'
