"""R2 privado pelo protocolo S3. Sem URL pública, ACL, criação ou listagem de buckets."""
import hashlib
from pathlib import Path
import re
from uuid import uuid4
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from app.services.exceptions import (DocumentStorageError, DocumentFileNotFoundError,
    DocumentTooLargeError, EmptyDocumentError, UnsupportedDocumentFormatError)


class R2DocumentStorage:
    provider = 'r2'

    def __init__(self, bucket, endpoint=None, access_key_id=None, secret_access_key=None,
                 region='auto', max_size=10 * 1024 * 1024, client=None):
        self.bucket, self.endpoint, self.region = bucket, endpoint, region
        self._access_key_id, self._secret_access_key = access_key_id, secret_access_key
        self.max_size, self._client = max_size, client

    @property
    def client(self):
        if self._client is None:
            if not all((self.endpoint, self.bucket, self._access_key_id, self._secret_access_key, self.region)):
                raise DocumentStorageError('Configuração do storage externo indisponível')
            try:
                self._client = boto3.client('s3', endpoint_url=self.endpoint,
                    aws_access_key_id=self._access_key_id, aws_secret_access_key=self._secret_access_key,
                    region_name=self.region, config=Config(signature_version='s3v4',
                        s3={'addressing_style': 'path'}, retries={'total_max_attempts': 1},
                        connect_timeout=10, read_timeout=60,
                        request_checksum_calculation='when_required', response_checksum_validation='when_required'))
            except (BotoCoreError, ClientError, ValueError):
                raise DocumentStorageError('Storage externo temporariamente indisponível') from None
        return self._client

    def _validate_key(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'documentos/[0-9a-f]{32}/[0-9a-f]{64}\.(pdf|png|jpe?g)', key):
            raise UnsupportedDocumentFormatError('Chave de documento inválida')
        return key

    def save(self, source, filename, content_type):
        from app.processing.arquivo_documental import mime_arquivo, validar_arquivo
        mime = mime_arquivo(filename, content_type)
        data = source.read(self.max_size + 1)
        if len(data) > self.max_size:
            raise DocumentTooLargeError('Documento excede o limite de tamanho')
        if not data:
            raise EmptyDocumentError('Arquivo vazio')
        validar_arquivo(data, mime)
        key = f'documentos/{uuid4().hex}/{hashlib.sha256(data).hexdigest()}{Path(filename).suffix.lower()}'
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=mime)
        except (BotoCoreError, ClientError, OSError):
            raise DocumentStorageError('Não foi possível armazenar o documento') from None
        return key

    def read(self, key):
        self._validate_key(key)
        body = None
        try:
            result = self.client.get_object(Bucket=self.bucket, Key=key)
            body = result['Body']
            if result.get('ContentLength', 0) > self.max_size:
                raise DocumentTooLargeError('Documento excede o limite de tamanho')
            data = body.read(self.max_size + 1)
            if len(data) > self.max_size:
                raise DocumentTooLargeError('Documento excede o limite de tamanho')
            return data
        except ClientError as exc:
            code = str(exc.response.get('Error', {}).get('Code', ''))
            if code in {'NoSuchKey', '404', 'NotFound'}:
                raise DocumentFileNotFoundError('Arquivo do documento não encontrado') from None
            raise DocumentStorageError('Não foi possível ler o documento') from None
        except (BotoCoreError, OSError):
            raise DocumentStorageError('Não foi possível ler o documento') from None
        finally:
            if body is not None:
                body.close()

    def delete(self, key):
        self._validate_key(key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError, OSError):
            raise DocumentStorageError('Não foi possível remover o documento') from None
