#!/usr/bin/env python3
"""
Junta o esqueleto demográfico (gerar_esqueleto.py) com as narrativas (juri/fonte/lote-*.json) e grava
o foro final `juri/brasil.json`, com as cotas do IBGE para o `juri cotas` conferir.

Uso: python ferramentas/montar_foro.py
"""

import glob
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPOS_NARRATIVA = ['nome', 'apelido', 'cidade', 'ocupacao', 'estado_civil', 'filhos', 'mora_com', 'dispositivo',
                    'responsavel', 'historia', 'valores', 'medos', 'vies', 'repara_em', 'voz']

# Cotas em % (a meta), com a base de cada uma. Fontes: referencias/populacao-brasil.md
COTAS = {
    'faixa etária (Censo 2022)': {'campo': 'faixa_ibge', 'valores': {
        '0-4': 6.26, '5-9': 6.77, '10-14': 6.73, '15-19': 7.08, '20-24': 7.62, '25-29': 7.62, '30-39': 15.58,
        '40-49': 14.63, '50-59': 11.90, '60-69': 8.78, '70-79': 4.78, '80+': 2.26}},
    'sexo (Censo 2022)': {'campo': 'sexo', 'valores': {'F': 51.48, 'M': 48.52}},
    'região (Censo 2022)': {'campo': 'regiao', 'valores': {
        'Sudeste': 41.78, 'Nordeste': 26.91, 'Sul': 14.74, 'Norte': 8.55, 'Centro-Oeste': 8.02}},
    'cor ou raça (Censo 2022)': {'campo': 'cor_raca', 'valores': {
        'parda': 45.34, 'branca': 43.46, 'preta': 10.17, 'indígena': 0.60, 'amarela': 0.42}},
    'rural (Censo 2022)': {'campo': 'rural', 'valores': {'sim': 12.6, 'não': 87.4}},
    'mora em capital (Censo 2022)': {'campo': 'em_capital', 'valores': {'sim': 22.89, 'não': 77.11}},
    'escolaridade, 25 anos ou mais (PNAD 2025)': {'campo': 'escolaridade', 'base': 'idade>=25', 'valores': {
        'fundamental incompleto ou sem instrução': 30.7, 'fundamental completo': 12.1, 'médio completo': 36.0,
        'superior completo': 21.4}},
    'decil de renda domiciliar per capita (PNAD 2025)': {'campo': 'decil', 'valores': {
        str(d): 10.0 for d in range(1, 11)}},
    'religião, 10 anos ou mais (Censo 2022)': {'campo': 'religiao_grupo', 'base': 'idade>=10', 'valores': {
        'católica': 56.75, 'evangélica': 26.85, 'sem religião': 9.28, 'outras': 4.01, 'espírita': 1.84,
        'umbanda ou candomblé': 1.05}},
    'não usa internet, 10 anos ou mais (PNAD TIC 2025)': {'campo': 'usa_internet', 'base': 'idade>=10',
                                                           'valores': {'não': 9.5, 'sim': 90.5}},
    'com deficiência, 2 anos ou mais (PNAD 2022)': {'campo': 'tem_deficiencia', 'base': 'idade>=2',
                                                     'valores': {'sim': 8.9, 'não': 91.1}},
    'recebe aposentadoria ou pensão (PNAD 2025)': {'campo': 'aposentado', 'valores': {'sim': 13.8, 'não': 86.2}},
}


def derivados(j):
    """Campos usados só pelas cotas, calculados dos campos do jurado."""
    j['rural'] = 'sim' if j['tipo_local'] == 'rural' else 'não'
    j['em_capital'] = 'sim' if j['tipo_local'] == 'capital' else 'não'
    r = j['religiao']
    j['religiao_grupo'] = 'outras' if r.startswith(('outra', 'religiosidade')) else r
    j['usa_internet'] = 'não' if j['internet'] == 'não usa' else 'sim'
    j['tem_deficiencia'] = 'sim' if j['deficiencia'] else 'não'
    j['aposentado'] = 'sim' if j['vinculo'].startswith('aposentado') else 'não'
    j['decil'] = str(j['decil'])


def main():
    esq = json.load(open(os.path.join(RAIZ, 'juri', 'fonte', 'esqueleto.json'), encoding='utf-8'))
    narr = {}
    for arq in sorted(glob.glob(os.path.join(RAIZ, 'juri', 'fonte', 'lote-*.json'))):
        for n in json.load(open(arq, encoding='utf-8-sig')):
            narr[n['id']] = n
    faltam = [j['id'] for j in esq if j['id'] not in narr]
    if faltam:
        sys.exit(f'faltam narrativas para: {", ".join(faltam)}')
    erros = []
    jurados = []
    nomes = {}
    for j in esq:
        n = narr[j['id']]
        for c in CAMPOS_NARRATIVA:
            if c not in n:
                erros.append(f'{j["id"]}: falta {c}')
        primeiro = n.get('nome', '').split()[0].lower() if n.get('nome') else ''
        nomes.setdefault(primeiro, []).append(j['id'])
        x = dict(j)
        x.update({c: n.get(c) for c in CAMPOS_NARRATIVA})
        if j['idade'] >= 8:
            x['responsavel'] = ''
        derivados(x)
        jurados.append(x)
    repetidos = {k: v for k, v in nomes.items() if len(v) > 1}
    if repetidos:
        print('AVISO: primeiro nome repetido: ' + '; '.join(f'{k} ({", ".join(v)})' for k, v in repetidos.items()))
    if erros:
        sys.exit('\n'.join(erros))
    foro = {
        'foro': 'brasil',
        'nome': 'Brasil',
        'descricao': '100 jurados fictícios; cada um representa 1% da população brasileira.',
        'fontes': 'referencias/populacao-brasil.md',
        'cotas': COTAS,
        'jurados': jurados,
    }
    destino = os.path.join(RAIZ, 'juri', 'brasil.json')
    with open(destino, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(foro, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(f'{len(jurados)} jurados em {destino}')


if __name__ == '__main__':
    main()
