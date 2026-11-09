#!/usr/bin/env python3
"""
Gera o ESQUELETO demográfico dos 100 jurados do foro Brasil, com as cotas exatas do IBGE.

Cada jurado = 1% da população. As cotas (em número de jurados) saem das fontes em
referencias/populacao-brasil.md, arredondadas pelo maior resto. As correlações (idade x escolaridade,
região x cor, escolaridade x renda, idade x internet...) vêm de uma nota socioeconômica latente com
ruído: cada cota é preenchida por ordem dessa nota, então a cota bate exata e o perfil fica plausível.

O esqueleto não tem nome nem personalidade escrita: isso é feito depois (ver referencias/juri.md).
Uso: python ferramentas/gerar_esqueleto.py [--semente N] -o juri/fonte/esqueleto.json
"""

import argparse
import json
import random

IDADES = [('0-4', 0, 4, 6), ('5-9', 5, 9, 7), ('10-14', 10, 14, 7), ('15-19', 15, 19, 7), ('20-24', 20, 24, 8),
          ('25-29', 25, 29, 7), ('30-39', 30, 39, 15), ('40-49', 40, 49, 15), ('50-59', 50, 59, 12),
          ('60-69', 60, 69, 9), ('70-79', 70, 79, 5), ('80+', 80, 99, 2)]
UFS = {'Sudeste': [('SP', 22), ('MG', 10), ('RJ', 8), ('ES', 2)],
       'Nordeste': [('BA', 7), ('PE', 4), ('CE', 4), ('MA', 3), ('PB', 2), ('PI', 2), ('RN', 2), ('AL', 2), ('SE', 1)],
       'Sul': [('PR', 6), ('RS', 5), ('SC', 4)],
       'Norte': [('PA', 4), ('AM', 2), ('RO', 1), ('TO', 1)],
       'Centro-Oeste': [('GO', 4), ('MT', 2), ('DF', 1), ('MS', 1)]}
SES_REGIAO = {'Sudeste': 0.35, 'Sul': 0.45, 'Centro-Oeste': 0.3, 'Nordeste': -0.45, 'Norte': -0.35}
BRANCA_REGIAO = {'Sul': 1.3, 'Sudeste': 0.45, 'Centro-Oeste': 0.1, 'Nordeste': -0.55, 'Norte': -0.75}


def tomar(xs, k, chave, rev=True):
    """Os k primeiros de xs pela chave (com a ordem já embaralhada para desempatar)."""
    return sorted(xs, key=chave, reverse=rev)[:k]


def gerar(semente):
    rng = random.Random(semente)
    J = []
    for rot, ini, fim, n in IDADES:
        for k in range(n):
            # idades espalhadas dentro da faixa (não aglomeradas)
            idade = max(1, ini) + round((k + rng.random()) * (fim - max(1, ini) + 1) / n - 0.5)
            J.append({'idade': max(ini, min(fim, idade)), 'faixa_ibge': rot})
    J[0]['idade'] = 1                      # do 1 ...
    J[-1]['idade'] = 100                   # ... aos 100 anos (ambos dentro da cota da faixa)
    rng.shuffle(J)

    # sexo: 51 F; mulheres mais frequentes nas faixas idosas
    for j in tomar(J, 51, lambda j: rng.random() + (0.35 if j['idade'] >= 60 else 0)):
        j['sexo'] = 'F'
    for j in J:
        j.setdefault('sexo', 'M')

    # região e UF
    regioes = [(r, uf) for r, ufs in UFS.items() for uf, n in ufs for _ in range(n)]
    rng.shuffle(regioes)
    for j, (r, uf) in zip(J, regioes):
        j['regiao'], j['uf'] = r, uf

    # cor/raça (Censo 2022): parda 45, branca 44, preta 10, indígena 1, amarela 0 (0,42% arredonda para 0)
    resto = list(J)
    ind = tomar(resto, 1, lambda j: (j['regiao'] == 'Norte') * 2 + rng.random())
    for j in ind:
        j['cor_raca'] = 'indígena'
    resto = [j for j in resto if j not in ind]
    for j in tomar(resto, 44, lambda j: BRANCA_REGIAO[j['regiao']] + rng.gauss(0, 0.9)):
        j['cor_raca'] = 'branca'
    resto = [j for j in resto if 'cor_raca' not in j]
    for j in tomar(resto, 10, lambda j: (0.4 if j['uf'] in ('BA', 'RJ', 'MA') else 0) + rng.random()):
        j['cor_raca'] = 'preta'
    for j in J:
        j.setdefault('cor_raca', 'parda')

    # local: 13 rurais (mais no Norte e Nordeste), 23 em capitais (DF sempre)
    for j in tomar(J, 13, lambda j: (0.6 if j['regiao'] in ('Nordeste', 'Norte') else 0) + rng.random()):
        j['tipo_local'] = 'rural'
    for j in J:
        if j['uf'] == 'DF':
            j['tipo_local'] = 'capital'
    urb = [j for j in J if 'tipo_local' not in j]
    for j in tomar(urb, 23 - sum(j.get('tipo_local') == 'capital' for j in J), lambda j: rng.random()):
        j['tipo_local'] = 'capital'
    for j in tomar([j for j in J if 'tipo_local' not in j], 20, lambda j: (j['uf'] in ('SP', 'RJ', 'MG')) + rng.random()):
        j['tipo_local'] = 'região metropolitana'
    for j in J:
        j.setdefault('tipo_local', 'interior')

    # nota socioeconômica latente
    for j in J:
        ses = SES_REGIAO[j['regiao']] + rng.gauss(0, 1)
        ses += {'capital': 0.45, 'região metropolitana': 0.15, 'interior': 0, 'rural': -0.7}[j['tipo_local']]
        ses += 0.35 if j['cor_raca'] == 'branca' else -0.1
        j['_ses'] = ses

    # escolaridade 25+ (PNAD 2025): 20 / 8 / 23 / 14; mais velhos com menos estudo
    adultos = [j for j in J if j['idade'] >= 25]
    def nota_esc(j):
        return j['_ses'] - 0.03 * max(0, j['idade'] - 35)
    ordem = sorted(adultos, key=nota_esc, reverse=True)
    for faixa, n in (('superior completo', 14), ('médio completo', 23), ('fundamental completo', 8),
                     ('fundamental incompleto ou sem instrução', 20)):
        for j in ordem[:n]:
            j['escolaridade'] = faixa
        ordem = ordem[n:]
    for j in J:
        if j['idade'] < 25:
            i = j['idade']
            if i < 4:
                j['escolaridade'] = 'criança (fora da escola ou creche)'
            elif i < 6:
                j['escolaridade'] = 'pré-escola'
            elif i < 15:
                j['escolaridade'] = 'ensino fundamental (cursando)'
            elif i < 18:
                j['escolaridade'] = 'ensino médio (cursando)' if j['_ses'] > -1.2 else 'fundamental incompleto ou sem instrução'
            else:
                j['escolaridade'] = rng.choice(['médio completo', 'superior (cursando)']) if j['_ses'] > 0.3 else \
                    rng.choice(['médio completo', 'fundamental completo', 'médio completo'])
        j['_ses'] += {'superior completo': 1.0, 'superior (cursando)': 0.5, 'médio completo': 0.2}.get(j['escolaridade'], -0.2)

    # renda domiciliar per capita: 10 por decil (PNAD 2025, valores médios do decil)
    medias = [268, 568, 791, 1027, 1311, 1560, 1913, 2494, 3590, 9117]
    ordem = sorted(J, key=lambda j: j['_ses'] + rng.gauss(0, 0.4))
    for d in range(10):
        for j in ordem[d * 10:(d + 1) * 10]:
            j['decil'] = d + 1
            j['renda_pc'] = round(medias[d] * rng.uniform(0.8, 1.2), -1)
            j['renda'] = ('baixa' if d < 3 else 'média-baixa' if d < 6 else 'média' if d < 9 else 'alta')

    # trabalho (14+): 48 ocupados, 3 desocupados, resto fora da força
    def em_idade_ativa(j):
        return 18 <= j['idade'] <= 64
    for j in J:
        i = j['idade']
        if i < 14:
            j['vinculo'] = 'criança' if i < 10 else 'estudante'
    aposentaveis = sorted([j for j in J if j['idade'] >= 50 and 'vinculo' not in j],
                          key=lambda j: j['idade'] + rng.gauss(0, 5), reverse=True)
    for j in aposentaveis[:14]:                       # 13,8% recebem aposentadoria ou pensão
        j['vinculo'] = 'aposentado(a)'
    aposentados_que_trabalham = [j for j in aposentaveis[:14] if j['idade'] < 70][:2]
    for j in aposentados_que_trabalham:
        j['vinculo'] = 'aposentado(a) que ainda trabalha'
    livres = [j for j in J if 'vinculo' not in j]
    ocup = tomar(livres, 48 - len(aposentados_que_trabalham),
                 lambda j: (1.2 if em_idade_ativa(j) else -1.5 if j['idade'] < 18 else 0) + rng.gauss(0, 0.8)
                 - (0.6 if j['sexo'] == 'F' else 0))
    desoc = tomar([j for j in livres if j not in ocup and 18 <= j['idade'] <= 59], 3, lambda j: -j['_ses'] + rng.random())
    for j in desoc:
        j['vinculo'] = 'desempregado(a)'
    # posição na ocupação: CLT 18, conta própria 12 (9 sem CNPJ), sem carteira 6, empregador 2,
    # servidor 6, doméstico 3, auxiliar familiar 1  (aposentados que trabalham contam como conta própria)
    ocup_sorted = sorted(ocup, key=lambda j: j['_ses'] + rng.gauss(0, 0.6), reverse=True)
    posicoes = (['empregador(a)'] * 2 + ['servidor(a) público(a)'] * 6 + ['CLT'] * 18 +
                ['conta própria com CNPJ'] * (3 - 0) + ['conta própria sem CNPJ'] * (9 - len(aposentados_que_trabalham)) +
                ['empregado(a) sem carteira'] * 6 + ['trabalhador(a) doméstico(a)'] * 3 + ['auxiliar familiar'] * 1)
    # ordem de status: empregador/servidor no topo, informais na base (com ruído)
    pos_por_nota = sorted(posicoes, key=lambda p: ['empregador(a)', 'servidor(a) público(a)', 'conta própria com CNPJ',
                                                   'CLT', 'empregado(a) sem carteira', 'conta própria sem CNPJ',
                                                   'auxiliar familiar', 'trabalhador(a) doméstico(a)'].index(p) + rng.gauss(0, 1.3))
    for j, p in zip(ocup_sorted, pos_por_nota):
        j['vinculo'] = p
    for j in J:
        if 'vinculo' not in j:
            if j['idade'] < 25:
                j['vinculo'] = 'estudante'
            elif j['sexo'] == 'F' and rng.random() < 0.7:
                j['vinculo'] = 'do lar'
            else:
                j['vinculo'] = 'fora da força de trabalho'
    # setor dos ocupados: comércio 9, saúde/educação/adm pública 9, serviços profissionais/TI/finanças 6,
    # indústria 6, agro 4, doméstico 3, alimentação/alojamento 2, construção/transporte/outros 9
    setores = (['comércio'] * 9 + ['serviços profissionais, TI ou finanças'] * 6 + ['indústria'] * 6 + ['agro'] * 4 +
               ['alimentação e alojamento'] * 2 + ['construção, transporte ou outros serviços'] * 9)
    trab = [j for j in J if j['vinculo'] in posicoes or j['vinculo'] == 'aposentado(a) que ainda trabalha']
    for j in trab:
        if j['vinculo'] == 'servidor(a) público(a)':
            j['setor'] = 'administração pública, educação ou saúde'
        elif j['vinculo'] == 'trabalhador(a) doméstico(a)':
            j['setor'] = 'serviços domésticos'
    publicos_extra = 9 - sum(j.get('setor') == 'administração pública, educação ou saúde' for j in trab)
    sem = [j for j in trab if 'setor' not in j]
    for j in tomar(sem, publicos_extra, lambda j: (j['escolaridade'] == 'superior completo') + rng.random()):
        j['setor'] = 'administração pública, educação ou saúde'   # saúde e educação privadas
    sem = [j for j in trab if 'setor' not in j]
    rurais = [j for j in sem if j['tipo_local'] == 'rural']
    for j in rurais[:4]:
        j['setor'] = 'agro'
        setores.remove('agro')
    sem = [j for j in trab if 'setor' not in j]
    prof = tomar(sem, 6, lambda j: j['_ses'] + rng.gauss(0, 0.5))
    for j in prof:
        j['setor'] = 'serviços profissionais, TI ou finanças'
        setores.remove('serviços profissionais, TI ou finanças')
    sem = [j for j in trab if 'setor' not in j]
    rng.shuffle(setores)
    for j, s in zip(sem, setores):
        j['setor'] = s

    # Bolsa Família: ~20 pessoas em domicílio beneficiário (17,2% dos domicílios; domicílios maiores),
    # todas nos decis 1 a 3
    for j in tomar([j for j in J if j['decil'] <= 3], 20, lambda j: (j['idade'] < 18) * 0.5 - j['decil'] + rng.random()):
        j['bolsa_familia'] = True
    for j in J:
        j.setdefault('bolsa_familia', False)

    # religião (10+; Censo 2022): católica 49, evangélica 23, sem religião 8, outras 4, espírita 2, matriz africana 1
    dez = [j for j in J if j['idade'] >= 10]
    rel = {}
    for j in tomar(dez, 1, lambda j: (j['uf'] in ('BA', 'RJ', 'RS')) + rng.random()):
        rel[id(j)] = 'umbanda ou candomblé'
    for j in tomar([j for j in dez if id(j) not in rel], 2, lambda j: j['_ses'] + rng.random()):
        rel[id(j)] = 'espírita'
    for j in tomar([j for j in dez if id(j) not in rel], 8,
                   lambda j: (j['idade'] < 35) * 0.8 + (j['regiao'] in ('Sudeste', 'Sul')) * 0.3 + rng.random()):
        rel[id(j)] = 'sem religião'
    for j in tomar([j for j in dez if id(j) not in rel], 23,
                   lambda j: (j['regiao'] in ('Norte', 'Centro-Oeste')) * 0.5 + (j['decil'] <= 5) * 0.4
                   + (j['idade'] < 60) * 0.2 + rng.random()):
        rel[id(j)] = 'evangélica'
    for j in tomar([j for j in dez if id(j) not in rel], 4, lambda j: rng.random()):
        rel[id(j)] = rng.choice(['outra (judaica, budista, testemunha de Jeová, mórmon...)', 'religiosidade própria, sem igreja'])
    for j in dez:
        j['religiao'] = rel.get(id(j), 'católica')
    for j in J:
        j.setdefault('religiao', 'a da família (criança)')

    # internet (10+): 8 não usam (9,5%), sobretudo 60+ de baixa renda e rurais
    for j in tomar(dez, 8, lambda j: (j['idade'] >= 60) * 1.5 + (j['tipo_local'] == 'rural') * 0.8 - j['_ses'] * 0.5
                   + rng.random()):
        j['internet'] = 'não usa'
    for j in J:
        if 'internet' in j:
            continue
        if j['idade'] < 10:
            j['internet'] = 'vídeos no celular dos pais' if j['idade'] >= 2 else 'não usa'
            continue
        nota = j['_ses'] - 0.025 * max(0, j['idade'] - 40) + rng.gauss(0, 0.6) + (0.5 if j['idade'] < 30 else 0)
        j['internet'] = 'avançado' if nota > 1.2 else 'médio' if nota > 0.1 else 'básico (WhatsApp e vídeo)'

    # deficiência: 9 (8,9% de 2+), quase metade 60+
    for j in tomar([j for j in J if j['idade'] >= 2], 9, lambda j: (j['idade'] >= 60) * 0.45 + (j['idade'] >= 40) * 0.25 + rng.random()):
        j['deficiencia'] = rng.choice(['visual (enxerga pouco mesmo de óculos)', 'auditiva', 'motora (anda com dificuldade)',
                                       'motora (cadeira de rodas)', 'intelectual', 'visual (baixa visão)'])
    for j in J:
        j.setdefault('deficiencia', None)

    # mora sozinho: 7 (adultos, mais idosos)
    for j in tomar([j for j in J if j['idade'] >= 22], 7, lambda j: (j['idade'] >= 60) * 0.8 + rng.random()):
        j['mora_sozinho'] = True
    for j in J:
        j.setdefault('mora_sozinho', False)

    # LGBT+ declarado: 1 adulto (PNS 2019: 1,8% dos adultos; muitos não declaram)
    for j in tomar([j for j in J if 18 <= j['idade'] <= 45], 1, lambda j: rng.random()):
        j['orientacao'] = 'bissexual' if rng.random() < 0.4 else ('gay' if j['sexo'] == 'M' else 'lésbica')

    # personalidade (Big Five, 1 a 5) bem espalhada
    for j in J:
        j['personalidade'] = {k: max(1, min(5, round(rng.gauss(3, 1.15)))) for k in
                              ('abertura', 'conscienciosidade', 'extroversão', 'amabilidade', 'estabilidade emocional')}

    J.sort(key=lambda j: j['idade'])
    for n, j in enumerate(J, 1):
        j['id'] = f'BR-{n:03d}'
        del j['_ses']
    return [{k: j[k] for k in ['id'] + [x for x in j if x != 'id']} for j in J]


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--semente', type=int, default=2022)
    p.add_argument('-o', default='juri/fonte/esqueleto.json')
    a = p.parse_args()
    js = gerar(a.semente)
    with open(a.o, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(js, f, ensure_ascii=False, indent=1)
    print(f'{len(js)} jurados em {a.o}')
