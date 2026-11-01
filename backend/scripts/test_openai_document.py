#!/usr/bin/env python3
"""Avaliação REAL, manual e com custo de API. Nunca importado pela suíte."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings
from app.document_ai.base import DocumentAIError
from app.document_ai.factory import get_document_ai_provider
from app.processing.arquivo_documental import MIMES, validar_arquivo
from app.services.exceptions import DocumentError, ContextoOperacionalError, EntityNotFoundError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arquivo', type=Path)
    parser.add_argument('--id-usuario', type=int)
    parser.add_argument('--id-prefixo', type=int)
    parser.add_argument('--esperado', type=Path, help='JSON parcial de referência, protegido pelo operador')
    parser.add_argument('--relatorio', type=Path, help='JSON de avaliação com dados sensíveis; use diretório privado fora do repo')
    args = parser.parse_args()
    if args.id_prefixo and not args.id_usuario:
        parser.error('--id-prefixo exige --id-usuario')
    try:
        mime = MIMES.get(args.arquivo.suffix.lower())
        with args.arquivo.open('rb') as source:
            data = source.read(settings.document_max_size_bytes+1)
        validar_arquivo(data, mime, verificar_pdf=True)
        # Resolver contexto antes do envio pago. Nunca passá-lo ao provider.
        session = None
        if args.id_usuario:
            from app.core.database import SessionLocal
            from app.services.contexto_operacional import ContextoOperacionalService
            session = SessionLocal()
            try:
                prefix = ContextoOperacionalService(session).resolver(args.id_usuario, args.id_prefixo)
            except Exception:
                session.close()
                raise
        try:
            result = get_document_ai_provider().interpretar_documento(data, mime)
            fields = result.leitura.model_dump(mode='json', exclude_none=True)
            output = {k:v for k,v in fields.items() if k not in {'codigo_barras','endereco_unidade','numero_documento','unidade_consumidora'}}
            unit = fields.get('unidade_consumidora')
            output['unidade_consumidora'] = ('***'+unit[-4:]) if unit and len(unit)>4 else ('***' if unit else None)
            output['metadados'] = result.metadados
            if session:
                from app.services.validacao_documental import ValidacaoDocumentalService
                status, reason, _ = ValidacaoDocumentalService(session).avaliar(
                    result.leitura.dados_canonicos(), args.id_usuario, prefix.id_prefixo)
                output['resultado_documental'], output['motivo_documental'] = status, reason
            else:
                output['resultado_documental'] = 'EVIDENCIA_INSUFICIENTE'
                output['motivo_documental'] = 'Contexto não informado; somente interpretação'
            report = dict(extraido=fields, metadados=result.metadados,
                          resultado_documental=output['resultado_documental'])
            if args.esperado:
                expected = json.loads(args.esperado.read_text())
                report.update(esperado=expected, acerto_por_campo={k:fields.get(k)==v for k,v in expected.items()})
            if args.relatorio:
                # Opt-in explícito: pode conter unidade/endereço/barcode; permissão restrita.
                fd = os.open(args.relatorio, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as target:
                    json.dump(report, target, ensure_ascii=False, indent=2)
            print(json.dumps(output, ensure_ascii=False, indent=2))
        finally:
            if session:
                session.close()
    except DocumentAIError as exc:
        print(json.dumps({'erro':exc.codigo,'metadados':exc.metadados}, ensure_ascii=False), file=sys.stderr)
        return 1
    except (DocumentError, ContextoOperacionalError, EntityNotFoundError, OSError, ValueError):
        print('Arquivo, referência ou contexto inválido/indisponível. Nenhum conteúdo foi logado.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
