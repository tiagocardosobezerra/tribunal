"""Compara o lote externo (Qwen 3, via Ollama) com o júri Claude nos 30 casos cegos."""
import json
import math
import os
import sys

val, gab = sys.argv[1], sys.argv[2]
g = {c['id']: c['sucesso'] for c in json.load(open(gab, encoding='utf-8'))['casos']}


def ler(f):
    try:
        return json.load(open(f, encoding='utf-8-sig'))
    except (OSError, ValueError):
        return []


def p(vs):
    vs = [v for v in vs if v.get('voto')]
    return sum(v['voto'] != 'Improcedente' for v in vs) / len(vs) if vs else None


def medir(nome, pegar):
    bs, ac, n, emp, casos = [], 0, 0, 0, 0
    for c, y in sorted(g.items()):
        q = p(pegar(c))
        if q is None:
            continue
        casos += 1
        bs.append((q - y) ** 2)
        if q == 0.5:
            emp += 1
        else:
            n += 1
            ac += (q > .5) == bool(y)
    pv = sum(math.comb(n, k) for k in range(ac, n + 1)) / 2 ** n if n else None
    return f'| {nome} | {casos} | {ac} de {n} | {emp} | {sum(bs) / len(bs):.3f} | {pv:.2f} |'


L = lambda c, k: ler(os.path.join(val, c, 'votos', f'r1-lote{k}.json'))
X = lambda c: ler(os.path.join(val, c, 'externo', 'r1-lote2.json'))
print('| Júri | Casos | Acerto | Empates | Brier | p (acaso) |')
print('|---|---|---|---|---|---|')
print(medir('Qwen 3 4b sozinho (5 jurados)', X))
print(medir('Haiku sozinho (os mesmos 5 jurados)', lambda c: L(c, 2)))
print(medir('Sonnet sozinho', lambda c: L(c, 1)))
print(medir('Opus sozinho', lambda c: L(c, 3)))
print(medir('Júri Claude (Sonnet + Haiku + Opus)', lambda c: L(c, 1) + L(c, 2) + L(c, 3)))
print(medir('Júri misto (Sonnet + Qwen + Opus)', lambda c: L(c, 1) + X(c) + L(c, 3)))
# concordância de votos jurado a jurado entre Qwen e Haiku (mesmas fichas)
iguais = tot = 0
for c in g:
    h = {v['jurado']: v['voto'] for v in L(c, 2)}
    for v in X(c):
        if v.get('jurado') in h:
            tot += 1
            iguais += v.get('voto') == h[v['jurado']]
print(f'\nMesmo voto que o Haiku, mesma ficha: {iguais} de {tot}')
rec = sum(1 for c in g for v in X(c) if str(v.get('reconhece') or '').strip())
print(f'Votos do Qwen que reconheceram o produto: {rec} de {sum(len(X(c)) for c in g)}')
