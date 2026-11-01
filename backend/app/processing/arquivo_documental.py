"""Lista fechada de formatos, tamanho e conteúdo verificado antes do envio externo."""
from io import BytesIO
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from app.core.config import settings
from app.services.exceptions import UnsupportedDocumentFormatError, DocumentTooLargeError, EmptyDocumentError, InvalidPdfError

MIMES = {'.pdf':'application/pdf', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.png':'image/png'}


def mime_arquivo(filename, content_type):
    expected = MIMES.get(Path(filename).suffix.lower())
    if expected is None or (content_type != expected and not (expected == 'application/pdf' and content_type == 'application/octet-stream')):
        raise UnsupportedDocumentFormatError('Extensão/MIME não suportados ou incompatíveis')
    return expected


def validar_arquivo(data, mime_type, verificar_pdf=False):
    if len(data) > settings.document_max_size_bytes:
        raise DocumentTooLargeError('Documento excede o limite de tamanho')
    if not data:
        raise EmptyDocumentError('Arquivo vazio')
    if mime_type == 'application/pdf':
        if not data.startswith(b'%PDF-'):
            raise InvalidPdfError('Assinatura PDF inválida')
        if verificar_pdf:
            try:
                reader = PdfReader(BytesIO(data))
                if reader.is_encrypted or not len(reader.pages):
                    raise ValueError('PDF protegido ou vazio')
            except Exception:
                raise InvalidPdfError('PDF inválido, protegido ou sem páginas') from None
    elif mime_type in ('image/jpeg', 'image/png'):
        try:
            with Image.open(BytesIO(data)) as image:
                expected = 'JPEG' if mime_type == 'image/jpeg' else 'PNG'
                if image.format != expected or image.width*image.height > 40_000_000:
                    raise ValueError('Conteúdo incompatível')
                image.verify()
        except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
            raise UnsupportedDocumentFormatError('Imagem inválida ou excede limite de pixels') from None
    else:
        raise UnsupportedDocumentFormatError('Somente PDF, JPG, JPEG e PNG são aceitos')
