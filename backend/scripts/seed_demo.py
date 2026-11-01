"""Seed manual de manutenção, via DATABASE_URL, sem servidor, HTTP ou chamadas IA.

python scripts/seed_demo.py --ambiente-demo
Use --cenario ensaio-2 para uma nova conta/ordem sem apagar histórico.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from unicodedata import combining, normalize

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
API = '/api/v1'
FIXTURES = Path(__file__).resolve().parents[1] / 'demo/cenarios_documentais.json'


def listar(client, resource):
    rows = []
    offset = 0
    while True:
        response = client.get(f'{API}/{resource}', params={'offset': offset, 'limit': 100})
        response.raise_for_status()
        page = response.json()
        rows.extend(page)
        if resource == 'unidades_consumidoras' or len(page) < 100:
            return rows
        offset += 100


def norm(value):
    return ' '.join(''.join(c for c in normalize('NFD', value or '') if not combining(c)).casefold().split())


def localidade(client, ensure, municipio, codigo):
    matches = [r for r in listar(client, 'localidades')
               if norm(r['municipio']) == norm(municipio) and norm(r['estado']) == 'pe']
    # Bases antigas já podem ter localidades equivalentes. Reutiliza a primeira,
    # sem apagar ou mesclar registros e sem criar outra duplicata.
    if matches:
        return min(matches, key=lambda r: r['id_localidade'])
    return ensure('localidades', 'id_localidade', {'codigo_localidade': codigo},
                  estado='PE', municipio=municipio, regiao='Nordeste')


def contexto_demo(client, ensure, users, scenario):
    prefixes = {}
    for city, code in [('Recife', 'REC-DEMO'), ('Paulista', 'PAU-DEMO')]:
        loc = localidade(client, ensure, city, f'DEMO-{city.upper()}')
        p = ensure('prefixos', 'id_prefixo', {'codigo_prefixo': code},
                   nome=f'Unidade fictícia DEMO {city}', tipo_prefixo='agencia',
                   situacao='ativo', id_localidade=loc['id_localidade'])
        if p['id_localidade'] != loc['id_localidade'] or p['situacao'] != 'ativo':
            raise RuntimeError(f'{code}: cadastro existente incompatível; nenhuma correção automática')
        prefixes[code] = p
    utilities = {}
    # Raiz zero sintética; dígitos verificadores válidos. Sem identidade fiscal real.
    for service, name, cnpj in [('energia', 'ENERGIA DEMO PE', '00000000000191'),
                                ('agua', 'AGUA DEMO PE', '00000000000272')]:
        matches = [r for r in listar(client, 'concessionarias')
                   if norm(name) in (norm(r['razao_social']), norm(r.get('nome_fantasia')))
                   or r['cnpj'] == cnpj]
        if matches and (len(matches) != 1 or matches[0]['cnpj'] != cnpj or
                        matches[0]['razao_social'] != name or matches[0]['tipo_servico'] != service):
            raise RuntimeError(f'{name}: correspondência conflitante; cadastro preservado')
        utilities[service] = ensure('concessionarias', 'id_concessionaria', {'cnpj': cnpj},
            razao_social=name, nome_fantasia=name, tipo_servico=service)
        for code, p in prefixes.items():
            unit = ensure('unidades_consumidoras', 'id_unidade_consumidora',
                {'id_concessionaria': utilities[service]['id_concessionaria'],
                 'unidade_consumidora': f'UC-{code.split("-")[0]}-{service.upper()}-DEMO-001'},
                id_prefixo=p['id_prefixo'], ativo=True,
                endereco_referencia='Endereço fictício DEMO; sem validade cadastral')
            if unit['id_prefixo'] != p['id_prefixo'] or not unit['ativo']:
                raise RuntimeError('Unidade DEMO existente incompatível; cadastro preservado')
    for role, name, code in [('maker-paulista', 'Maker Paulista DEMO', 'PAU-DEMO'),
                              ('maker-multi', 'Maker Multi-Prefixo DEMO', 'REC-DEMO')]:
        users[role] = ensure('usuarios', 'id_usuario', {'matricula': f'DEMO-{role}'},
            nome=name, funcao='maker', situacao='ativo', id_prefixo=prefixes[code]['id_prefixo'],
            id_alcada=users['maker']['id_alcada'])
    assignments = {'maker': ['REC-DEMO'], 'maker-paulista': ['PAU-DEMO'],
                   'maker-multi': ['REC-DEMO', 'PAU-DEMO'],
                   'checker': ['REC-DEMO', 'PAU-DEMO'], 'limite-baixo': ['REC-DEMO']}
    for role, codes in assignments.items():
        user = users[role]
        if user['situacao'] != 'ativo':
            raise RuntimeError(f'{role}: usuário existente inativo; cadastro preservado')
        url = f'{API}/usuarios/{user["id_usuario"]}/prefixos'
        response = client.get(url)
        response.raise_for_status()
        links = response.json()['vinculos']
        changed = False
        for code in codes:
            pid = prefixes[code]['id_prefixo']
            link = next((l for l in links if l['id_prefixo'] == pid), None)
            if link and not link['ativo']:
                raise RuntimeError(f'{role}/{code}: vínculo inativo preservado; confira manualmente')
            if link is None:
                links.append(dict(id_prefixo=pid, ativo=True, principal=False))
                changed = True
        if changed:
            response = client.put(url, json={'vinculos': links})
            response.raise_for_status()
        print(f'vínculos DEMO: {user["matricula"]} -> {", ".join(codes)} (anteriores preservados)')

    cases = json.loads(FIXTURES.read_text())
    results = {}
    for case in cases:
        p = prefixes[case['prefixo']]
        reading = case['leitura']
        service = 'agua' if reading['tipo_documento'] == 'CONTA_AGUA' else 'energia'
        account = ensure('contas_consumo', 'id_conta',
            {'numero_conta': f'DEMO-DOC-{scenario}-{case["nome"]}'},
            competencia='2026-10', data_vencimento='2026-10-20', valor_original='123.45',
            categoria=service, situacao='pendente', id_prefixo=p['id_prefixo'],
            id_concessionaria=utilities[service]['id_concessionaria'])
        document = ensure('documentos', 'id_documento',
            {'id_conta': account['id_conta'], 'origem': 'DEMO estruturada sem IA'},
            tipo_documento='DEMO simulada', formato='json',
            caminho_arquivo='demo/cenarios_documentais.json', data_recebimento='2026-10-01T12:00:00')
        existing = [r for r in listar(client, 'extracoes_inteligentes')
                    if r['id_documento'] == document['id_documento']]
        if not existing:
            response = client.post(f'{API}/documentos/{document["id_documento"]}/interpretacao', json={
                'leitura': reading, 'contexto': {'id_usuario': users[case['usuario']]['id_usuario'],
                                               'id_prefixo': p['id_prefixo']}})
            response.raise_for_status()
            existing = [response.json()]
        result = existing[-1]['resultado_validacao_documental']
        if result != case['esperado']:
            raise RuntimeError(f'{case["nome"]}: {result}, esperado {case["esperado"]}; histórico preservado')
        results[case['nome']] = result
        print(f'DEMO {case["nome"]}: {result}')
    return dict(usuarios=users, prefixos=prefixes, concessionarias=utilities, resultados=results)


def prepare(client, scenario):
    def ensure(resource, key, match, **payload):
        rows = listar(client, resource)
        found = [row for row in rows if all(row.get(k) == v for k, v in match.items())]
        if len(found) > 1:
            raise RuntimeError(f'{resource}: correspondência ambígua; confira os registros manualmente')
        if found:
            row = found[0]
            action = 'encontrado'
        else:
            response = client.post(f'{API}/{resource}', json={**payload, **match})
            response.raise_for_status()
            row = response.json()
            action = 'criado'
        print(f'{resource}: {key}={row[key]} ({action})', flush=True)
        return row

    locality = localidade(client, ensure, 'Recife', 'DEMO-REC')
    prefix = ensure('prefixos', 'id_prefixo', {'codigo_prefixo': 'DEMO'},
                    nome='Unidade fictícia Recife', tipo_prefixo='agencia', situacao='ativo',
                    id_localidade=locality['id_localidade'])
    utility = ensure('concessionarias', 'id_concessionaria', {'cnpj': '00000000000000'},
                     razao_social='Energia Fictícia Demonstração', tipo_servico='energia')
    account = ensure('contas_consumo', 'id_conta', {'numero_conta': f'DEMO-{scenario}'},
                     competencia='2026-10', data_vencimento='2026-10-20', valor_original='123.45',
                     categoria='energia', situacao='pendente', id_prefixo=prefix['id_prefixo'],
                     id_concessionaria=utility['id_concessionaria'])
    rule = ensure('regras_calculo', 'id_regra', {'nome_regra': 'DEMO sem acréscimos', 'versao': 'demo-1'},
                  categoria='energia', data_inicio_vigencia='2026-10-01', situacao='ativa')
    for code, name, strategy, params in [
        ('DEMO-COEF', 'Prefixo Energia Coeficiente', 'COEFICIENTE', {'coeficiente': '0.85'}),
        ('DEMO-PREDIAL', 'Prefixo Energia Predial / Composição', 'COMPOSICAO_DETALHADA', {}),
        ('DEMO-INTEGRAL', 'Prefixo Valor Integral', 'VALOR_INTEGRAL', {}),
    ]:
        operational_prefix = ensure('prefixos', 'id_prefixo', {'codigo_prefixo': code},
            nome=name, tipo_prefixo='predial' if code == 'DEMO-PREDIAL' else 'agencia',
            situacao='ativo', id_localidade=locality['id_localidade'])
        operational_rule = ensure('regras_calculo', 'id_regra',
            {'nome_regra': f'DEMO {strategy}', 'versao': '6a-1'}, categoria='energia',
            data_inicio_vigencia='2026-01-01', situacao='ativa')
        ensure('perfis_processamento', 'id_perfil',
            {'id_prefixo': operational_prefix['id_prefixo'], 'data_inicio_vigencia': '2026-01-01'},
            tipo_servico='energia', estrategia=strategy, id_regra=operational_rule['id_regra'],
            id_concessionaria=utility['id_concessionaria'], situacao='ativo', parametros=params)
        if strategy == 'COMPOSICAO_DETALHADA':
            for position, (kind, operation, required) in enumerate([
                ('TUSD', 'SOMAR', True), ('TE', 'SOMAR', True),
                ('BANDEIRA', 'SOMAR', False), ('DESCONTO', 'DESCONTO', False),
            ]):
                ensure('itens_regra', 'id_item_regra',
                    {'id_regra': operational_rule['id_regra'], 'nome_item': kind},
                    tipo_item=operation, ordem_aplicacao=position, obrigatorio=required,
                    descricao='Configuração fictícia técnica; não representa fórmula bancária')
        ensure('contas_consumo', 'id_conta', {'numero_conta': f'{code}-{scenario}'},
            competencia='2026-09', data_vencimento='2026-10-20', valor_original='736.53',
            categoria='energia', situacao='pendente', id_prefixo=operational_prefix['id_prefixo'],
            id_concessionaria=utility['id_concessionaria'])
    system = ensure('sistemas_pagamento', 'id_sistema', {'nome': 'DEMO local fictício'},
                    descricao='Somente cadastro; sem envio de pagamento', situacao='ativo')
    users = {}
    for role, limit in [('maker', '1000.00'), ('checker', '1000.00'), ('limite-baixo', '100.00')]:
        level = ensure('alcadas', 'id_alcada', {'nome_nivel': f'DEMO {limit}'},
                       limite_financeiro=limit, data_inicio_vigencia='2026-10-01')
        users[role] = ensure('usuarios', 'id_usuario', {'matricula': f'DEMO-{role}'},
                             nome=f'Pessoa fictícia {role}', funcao=role, situacao='ativo',
                             id_prefixo=prefix['id_prefixo'], id_alcada=level['id_alcada'])
    calculation = ensure('calculos', 'id_calculo', {'id_conta': account['id_conta'], 'id_regra': rule['id_regra']},
                         data_calculo='2026-10-06T12:00:00', valor_inicial='123.45',
                         valor_calculado='123.45', situacao='validado')
    order = ensure('ordens_pagamento', 'id_ordem', {'id_calculo': calculation['id_calculo']},
                   data_criacao='2026-10-06T13:00:00', data_prevista_pagamento='2026-10-20',
                   valor_total='123.45', situacao='pendente', id_sistema=system['id_sistema'],
                   id_usuario_criador=users['maker']['id_usuario'])
    ensure('itens_pagamento', 'id_item_pagamento', {'id_ordem': order['id_ordem'], 'codigo_evento': 'DEMO'},
           descricao_evento='Energia fictícia sem validade para pagamento', valor='123.45')
    context = contexto_demo(client, ensure, users, scenario)
    print(f"Conta: #/contas/{account['id_conta']} | Ordem: #/ordens/{order['id_ordem']} | situação: {order['situacao']}")
    print('Cálculo e ordem são cadastros manuais preparados, não resultados automáticos da validação.')
    print('Interpretações DEMO estruturadas validadas pelo backend; sem IA, upload ou aprovação.')
    return {**context, 'ordem': order}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cenario', default='apresentacao', help='Identificador da conta fictícia (padrão: apresentacao)')
    parser.add_argument('--ambiente-demo', action='store_true', required=True,
                        help='Confirma uso exclusivo em base local de demonstração, nunca produção')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,40}', args.cenario):
        parser.error('--cenario deve conter 1 a 40 letras minúsculas, números ou hífens')
    from app.core.config import settings
    if not settings.demo_auth_enabled:
        parser.error('O seed exige DEMO_MODE=true e --ambiente-demo')
    from app.core.database import SessionLocal
    from scripts.seed_client import MaintenanceSeedClient
    try:
        with SessionLocal() as session:
            prepare(MaintenanceSeedClient(session),args.cenario)
    except Exception:
        # Exceções de banco podem carregar SQL e valores; não imprimir repr/URL.
        parser.exit(1, 'Preparação interrompida. Confira configuração e cadastros; registros já criados foram preservados.\n')


if __name__ == '__main__':
    main()
