import os
import io
from PIL import Image, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile

def optimize_image_to_webp(uploaded_file):
    """
    Recebe um UploadedFile, verifica se é imagem, converte para WEBP otimizado e
    retorna um InMemoryUploadedFile modificado. Caso não seja imagem, retorna o original.
    """
    if not uploaded_file:
        return uploaded_file

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    
    # Somente tenta converter arquivos com extensões comuns de imagem
    if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
        return uploaded_file

    # Preserva GIF animado (conversão WebP perderia os frames)
    if ext == '.gif' or getattr(uploaded_file, 'content_type', '') == 'image/gif':
        return uploaded_file

    try:
        # Abrir imagem
        image = Image.open(uploaded_file)
        
        # Corrigir orientação (EXIF) se necessário
        image = ImageOps.exif_transpose(image)
        
        # Garantir modo de cor compatível com WebP
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGBA')

        # Criar buffer em memória
        output_io = io.BytesIO()
        
        # Salvar em WEBP
        image.save(output_io, format='WEBP', quality=85, optimize=True)
        output_io.seek(0)
        
        # Trocar extensão do nome
        base_name = os.path.splitext(uploaded_file.name)[0]
        new_name = f"{base_name}.webp"
        
        # Gerar o novo UploadedFile
        return InMemoryUploadedFile(
            file=output_io,
            field_name=uploaded_file.field_name,
            name=new_name,
            content_type='image/webp',
            size=output_io.getbuffer().nbytes,
            charset=uploaded_file.charset,
            content_type_extra=uploaded_file.content_type_extra
        )
    except Exception as e:
        # Em caso de qualquer falha (ex: imagem corrompida, não é imagem válida apesar da extensão)
        # retorna o arquivo original para o fluxo normal lidar (que talvez lance ValidationError)
        print(f"Erro ao otimizar imagem para WEBP: {e}")
        # Resetar o ponteiro do arquivo original caso o PIL tenha movido
        uploaded_file.seek(0)
        return uploaded_file
