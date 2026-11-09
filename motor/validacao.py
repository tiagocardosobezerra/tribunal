"""
Validação do júri contra casos de desfecho conhecido (validacao/casos.json).

O júri julga cada caso como se fosse antes do lançamento, sem ver o nome do produto nem o gabarito. Cada voto
diz também se a pessoa reconheceu algo parecido ("reconhece"): é a medida de vazamento, porque um modelo pode
lembrar do desfecho de um produto famoso em vez de julgá-lo. O resultado sai com e sem os votos vazados.

    preparar(pasta, casos, lotes)  -> autos e briefings de cada caso, e as chamadas de subagente
    resultado(pasta, casos)        -> acerto, Brier, por modelo e o vazamento
"""

import json
import os

from . import autos as A
from . import juri as J
from . import orquestra as O

POR_LOTE = 5
EXTRA = ('VALIDAÇÃO: em cada objeto inclua também "reconhece": o nome do produto ou empresa real que a pessoa acha '
         'que é este, se achar que já existe; vazio se não reconhecer. Julgue como se estivesse no ano informado, sem '
         'usar o que aconteceu depois.')


def carregar_casos(arq, gabarito=None):
    """Casos com descrição. Na validação cega, o desfecho vem de um arquivo à parte (gabarito), que o
    escritor das descrições nunca viu junto com elas."""
    with open(arq, encoding='utf-8') as f:
        casos = json.load(f)['casos']
    if gabarito:
        with open(gabarito, encoding='utf-8') as f:
            g = {c['id']: c for c in json.load(f)['casos']}
        casos = [dict(c, sucesso=g[c['id']]['sucesso'], nome=g[c['id']].get('nome', '')) for c in casos if c['id'] in g]
    return casos


def linha_de_base(arq_palpites, casos):
    """Um modelo sozinho, numa chamada, lê as descrições e prevê o desfecho: o júri tem de ganhar disto.
    O arquivo traz também o palpite do nome do produto, que mede o quanto as descrições o entregam."""
    with open(arq_palpites, encoding='utf-8') as f:
        p = {x['id']: x for x in json.load(f)['casos']}
    bs, ac, n, ident = [], 0, 0, 0
    for c in casos:
        x = p.get(c['id'])
        if not x:
            continue
        q = float(x.get('p_sucesso', 0.5))
        bs.append((q - c['sucesso']) ** 2)
        if q != 0.5:
            n += 1
            ac += (q > 0.5) == bool(c['sucesso'])
        nome = str(c.get('nome', '')).lower().split(' (')[0].split(',')[0].strip()
        palpite = str(x.get('palpite_produto', '')).lower()
        if nome and nome.split()[0] in palpite:
            ident += 1
    return {'casos': len(bs), 'acerto': ac, 'decididos': n, 'brier': round(sum(bs) / len(bs), 3) if bs else None,
            'identificados': ident}


def preparar(pasta, casos, lotes=2, semente=7):
    dados = J.carregar_foro('brasil')
    chamadas = []
    for n, c in enumerate(casos):
        d = os.path.join(pasta, c['id'])
        os.makedirs(d, exist_ok=True)
        sessao, _, _ = J.convocar(dados, caso=c['id'], tipo='ideia', n=lotes * POR_LOTE, impedimentos=['idade<14'],
                                  semente=semente + n, estado={})
        autos = {'rito': 3, 'caso': {'titulo': f'Validação: {c["id"]}', 'tipo': 'ideia',
                                     'pergunta': 'Vale a pena lançar isto?',
                                     'opcoes': ['Procedente', 'Procedente com condições', 'Improcedente'],
                                     'explicacao': f'Estamos em {c["ano"]}. {c["descricao"]}', 'data': str(c['ano'])},
                 'juri': {'foro': 'brasil', 'sessao': f'validacao-{c["id"]}', 'convocados': sessao['convocados']},
                 'provas': [], 'votos': []}
        arq = os.path.join(d, 'autos.json')
        with open(arq, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(autos, f, ensure_ascii=False, indent=2)
        for k in range(1, lotes + 1):
            txt, destino, _ = O.briefing(arq, 1, k, lotes)
            txt = txt.replace('Não combine votos:', EXTRA + '\nNão combine votos:', 1)
            mod, agente = O.modelo_do_lote(k)
            chamadas.append(O._chamada(agente, f'validação {c["id"]} lote {k} ({mod})', txt, destino,
                                       os.path.join(d, 'briefings'), f'r1-lote{k}'))
    return chamadas


def _p_sucesso(votos):
    """Fração de votos a favor de lançar (Procedente ou com condições)."""
    return sum(v['voto'] != 'Improcedente' for v in votos) / len(votos) if votos else None


def resultado(pasta, casos):
    linhas, brier, acertos, base, indecisos = [], [], 0, [], 0
    brier_limpo, acertos_limpo, n_limpo = [], 0, 0
    por_mod = {}
    vazados_total = votos_total = 0
    for c in casos:
        arq = os.path.join(pasta, c['id'], 'autos.json')
        if not os.path.exists(os.path.join(pasta, c['id'], 'votos')):
            linhas.append({'id': c['id'], 'erro': 'sem votos'})
            continue
        O.juntar(arq)
        votos = [v for v in A.carregar(arq).get('votos', []) if v['rodada'] == 1]
        vazados = [v for v in votos if str(v.get('reconhece') or '').strip()]
        vazados_total += len(vazados)
        votos_total += len(votos)
        p, y = _p_sucesso(votos), c['sucesso']
        brier.append((p - y) ** 2)
        base.append(0.25)
        if p == 0.5:
            indecisos += 1
        else:
            acertos += (p > 0.5) == bool(y)
        limpos = [v for v in votos if v not in vazados]
        p_l = _p_sucesso(limpos)
        if p_l is not None and len(limpos) >= len(votos) / 2:
            brier_limpo.append((p_l - y) ** 2)
            if p_l != 0.5:
                acertos_limpo += (p_l > 0.5) == bool(y)
                n_limpo += 1
        for v in votos:
            por_mod.setdefault(v.get('modelo', '?'), {}).setdefault(c['id'], []).append(v)
        linhas.append({'id': c['id'], 'ano': c['ano'], 'sucesso': y, 'p': round(p, 2), 'acertou': None if p == 0.5 else (p > 0.5) == bool(y),
                       'vazamento': f'{len(vazados)}/{len(votos)}',
                       'reconheceu_como': sorted({str(v['reconhece']).strip() for v in vazados})[:3]})
    mods = {}
    for m, porcaso in por_mod.items():
        bs = [(_p_sucesso(vs) - next(c['sucesso'] for c in casos if c['id'] == cid)) ** 2 for cid, vs in porcaso.items()]
        ac = sum(_p_sucesso(vs) != 0.5 and (_p_sucesso(vs) > 0.5) == bool(next(c['sucesso'] for c in casos if c['id'] == cid)) for cid, vs in porcaso.items())
        mods[m] = {'casos': len(bs), 'acerto': ac, 'brier': round(sum(bs) / len(bs), 3)}
    n = len(brier)
    return {'casos': linhas, 'n': n, 'acerto': acertos, 'indecisos': indecisos, 'brier': round(sum(brier) / n, 3) if n else None,
            'brier_chute': 0.25, 'vazamento': f'{vazados_total}/{votos_total}',
            'sem_vazamento': {'casos': n_limpo, 'acerto': acertos_limpo,
                              'brier': round(sum(brier_limpo) / n_limpo, 3) if n_limpo else None},
            'por_modelo': mods}


def resultado_md(r, base=None):
    l = ['# Validação do júri', '',
         f'**Acerto:** {r["acerto"]} de {r["n"] - r["indecisos"]} casos decididos ({r["indecisos"]} empate(s) em 50%, que não contam) · **Brier:** {r["brier"]} (chute de 50% = 0,25; menor é melhor)', '',
         f'**Vazamento:** {r["vazamento"]} votos reconheceram o produto real. Sem os casos vazados: '
         f'{r["sem_vazamento"]["acerto"]} de {r["sem_vazamento"]["casos"]} · Brier {r["sem_vazamento"]["brier"]}', '',
         '| Caso | Ano | Desfecho | P(lançar) | Acertou | Reconheceram |', '|---|---|---|---|---|---|']
    for c in r['casos']:
        if 'erro' in c:
            l.append(f'| {c["id"]} | | | | {c["erro"]} | |')
            continue
        l.append(f'| {c["id"]} | {c["ano"]} | {"sucesso" if c["sucesso"] else "fracasso"} | {c["p"]} | '
                 f'{"empate" if c["acertou"] is None else ("sim" if c["acertou"] else "não")} | {c["vazamento"]} {", ".join(c["reconheceu_como"])} |')
    l += ['', '_Acerto do modelo conta só casos em que ele não empatou._', '', '| Modelo | Casos | Acerto | Brier |', '|---|---|---|---|']
    l += [f'| {m} | {d["casos"]} | {d["acerto"]} | {d["brier"]} |' for m, d in sorted(r['por_modelo'].items())]
    if base:
        l += ['', '## Linha de base: um modelo sozinho, numa chamada', '',
              f'Acerto: {base["acerto"]} de {base["decididos"]} decididos · Brier: {base["brier"]} · '
              f'produtos identificados pelo nome: {base["identificados"]} de {base["casos"]}']
    return '\n'.join(l) + '\n'
