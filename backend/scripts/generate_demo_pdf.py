"""Gera PDFs inteiramente fictícios, sem acessar banco ou rede."""
from pathlib import Path

import pymupdf


def main():
    destination = Path(__file__).resolve().parents[1] / 'demo'
    destination.mkdir(exist_ok=True)
    lines = [
        'DEMONSTRACAO FICTICIA', 'SEM VALIDADE PARA PAGAMENTO', '',
        'Energia Ficticia Demonstracao - Recife/PE', 'Conta: DEMO - sem dados reais', '',
        'Competência: 10/2026', 'Vencimento: 20/10/2026',
        'Valor total: R$ 123,45', 'Consumo: 100,500 kWh',
        'Código de barras: ' + '0' * 44, '',
        'Codigo sem validade. Nenhum pagamento sera enviado.',
    ]
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((40, 60), '\n'.join(lines), fontsize=12)
        document.save(destination / 'conta_demo.pdf', deflate=True)
        image = page.get_pixmap(dpi=200)
        with pymupdf.open() as scan:
            scan.new_page(width=page.rect.width, height=page.rect.height).insert_image(
                page.rect, stream=image.tobytes('png'))
            scan.save(destination / 'conta_demo_ocr.pdf', deflate=True)
    for path in sorted(destination.glob('conta_demo*.pdf')):
        print(f'{path}: {path.stat().st_size} bytes')


if __name__ == '__main__':
    main()
