"""
Concurso de propostas: quando a pergunta é aberta ("como resolver X?") ou a defesa precisa de caminhos,
o tribunal gera propostas diferentes, cada uma nascida de uma CARTA (modo de pensar + fluxo + estratégia),
distribuída sem repetir nenhuma parte entre propostas. A acusação ataca cada proposta, o autor concede ou
rebate, o juiz pontua pela rubrica e as finalistas (mais o status quo) viram as opções de voto do júri.

Ideia absorvida do Arena (cartas de estratégia, ataque e defesa, rubrica com âncoras, comparação cega com a
alternativa atual) e adaptada: em vez de um chaveamento de 100 agentes, poucas propostas bem atacadas e
um júri popular que decide entre as finalistas.

    propostas[]  {id: "X1", carta: {modo, fluxo, estrategia}, titulo, texto,
                  ataques: [{id, gravidade, texto, onde, contraexemplo}],
                  respostas: [{ataque, tipo: concede|rebate, texto}],
                  status: [{ataque, status: corrigido|rebatido|de_pe}],
                  notas: {resolve, viabilidade, robustez, especificidade, clareza}}
Guia: referencias/rubrica.md e referencias/rito.md.
"""

import json
import os
import random

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PESOS = {'resolve': 30, 'viabilidade': 25, 'robustez': 20, 'especificidade': 15, 'clareza': 10}


class PropostaRecusada(RuntimeError):
    """O pedido sobre as propostas não pode seguir."""


def cartas_disponiveis():
    with open(os.path.join(RAIZ, 'motor', 'cartas.json'), encoding='utf-8') as f:
        return json.load(f)


def distribuir(n, semente=None):
    """n cartas sem repetir modo, fluxo nem estratégia entre si (até o tamanho da menor lista)."""
    c = cartas_disponiveis()
    limite = min(len(c['modos']), len(c['fluxos']), len(c['estrategias']))
    if not 1 <= n <= limite:
        raise PropostaRecusada(f'de 1 a {limite} propostas (sem repetir nenhuma parte da carta)')
    rng = random.Random(semente)
    m, f, e = (rng.sample(c[k], n) for k in ('modos', 'fluxos', 'estrategias'))
    return [{'id': f'X{i + 1}', 'carta': {'modo': m[i], 'fluxo': f[i], 'estrategia': e[i]}} for i in range(n)]


def total(p):
    notas = p.get('notas') or {}
    return round(sum(PESOS[k] * float(notas.get(k, 0)) / 10 for k in PESOS), 1)


def fatal_de_pe(p):
    st = {x.get('ataque'): x.get('status') for x in p.get('status', [])}
    return any(a.get('gravidade') == 'fatal' and st.get(a.get('id')) == 'de_pe' for a in p.get('ataques', []))


def de_pe(p):
    return sum(1 for x in p.get('status', []) if x.get('status') == 'de_pe')


def classificar(propostas):
    """Ordem: sem FATAL de pé antes; depois maior nota; desempate: menos ataques de pé, maior 'resolve'."""
    return sorted(propostas, key=lambda p: (fatal_de_pe(p), -total(p), de_pe(p),
                                            -float((p.get('notas') or {}).get('resolve', 0))))


def validar(autos):
    e = []
    ps = autos.get('propostas') or []
    ids = [p.get('id') for p in ps]
    if len(ids) != len(set(ids)):
        e.append('ids de proposta repetidos')
    for p in ps:
        if not p.get('titulo'):
            e.append(f'proposta {p.get("id")} sem título')
        for k, v in (p.get('notas') or {}).items():
            if k not in PESOS:
                e.append(f'proposta {p.get("id")}: critério desconhecido {k!r} (use {", ".join(PESOS)})')
            elif not isinstance(v, (int, float)) or not 0 <= v <= 10:
                e.append(f'proposta {p.get("id")}: nota de {k} deve ir de 0 a 10')
        atk = {a.get('id') for a in p.get('ataques', [])}
        for r in p.get('respostas', []) + p.get('status', []):
            if r.get('ataque') not in atk:
                e.append(f'proposta {p.get("id")}: resposta ou status de ataque inexistente {r.get("ataque")}')
    return e


def opcoes_sugeridas(autos, finalistas=2):
    """As finalistas viram opções de voto; o status quo entra sempre (comparação com o que já existe)."""
    ps = classificar(autos.get('propostas') or [])
    fin = [p for p in ps if not fatal_de_pe(p)][:finalistas]
    ops = [f'{p["id"]}: {p["titulo"]}' for p in fin]
    sq = (autos.get('caso') or {}).get('status_quo')
    ops.append(f'Status quo: {sq}' if sq else 'Status quo: manter como está')
    return ops


def placar_md(autos, finalistas=2):
    ps = classificar(autos.get('propostas') or [])
    if not ps:
        return ''
    l = ['## Concurso de propostas', '',
         '| # | Proposta | Carta | Nota | Ataques de pé | FATAL de pé |', '|---|---|---|---|---|---|']
    for i, p in enumerate(ps, 1):
        c = p.get('carta') or {}
        carta = ' · '.join(x for x in (c.get('modo'), c.get('fluxo'), c.get('estrategia')) if x)
        l.append(f'| {i} | **{p["id"]}** {p.get("titulo", "")} | {carta} | {total(p)} | {de_pe(p)} | '
                 f'{"sim" if fatal_de_pe(p) else "não"} |')
    l += ['', 'Rubrica: resolve 30 · viabilidade 25 · robustez 20 · especificidade 15 · clareza 10 '
              '(notas de 0 a 10, ver referencias/rubrica.md).', '',
          '**Opções levadas ao júri:** ' + ' · '.join(opcoes_sugeridas(autos, finalistas)), '']
    return '\n'.join(l)
