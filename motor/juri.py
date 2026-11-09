"""
O júri: o elenco fixo de cada foro, o sorteio do conselho de sentença e a conferência das cotas.

Cada foro (`juri/<foro>.json`) tem 100 jurados fixos. Cada um representa 1% da população daquele lugar,
com as cotas da fonte oficial (no Brasil, o IBGE) em `cotas`. Guia: referencias/juri.md.
"""

import json
import os
import random
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_JURI = os.path.join(RAIZ, 'juri')

# campos que entram na distância entre jurados (diversidade) e nos segmentos do placar
CAMPOS_DIVERSIDADE = ('faixa_etaria', 'sexo', 'cor_raca', 'regiao', 'tipo_local', 'escolaridade', 'vinculo',
                      'renda', 'religiao', 'internet')
SEGMENTOS = ('faixa_etaria', 'sexo', 'regiao', 'cor_raca', 'tipo_local', 'escolaridade', 'renda', 'internet',
             'religiao')
FAIXAS = ((0, 14, '0-14'), (15, 29, '15-29'), (30, 44, '30-44'), (45, 59, '45-59'), (60, 74, '60-74'),
          (75, 200, '75+'))
IDADE_DE_VOZ = 8   # abaixo disso o jurado reage (comportamento observado), quem fala é o responsável


class JuriRecusado(RuntimeError):
    """O pedido ao júri não pode seguir."""


def foros():
    if not os.path.isdir(PASTA_JURI):
        return []
    return sorted(n[:-5] for n in os.listdir(PASTA_JURI) if n.endswith('.json'))


def carregar_foro(foro='brasil'):
    caminho = os.path.join(PASTA_JURI, f'{foro}.json')
    if not os.path.exists(caminho):
        raise JuriRecusado(f'foro não encontrado: {foro} (há: {", ".join(foros()) or "nenhum"})')
    with open(caminho, encoding='utf-8-sig') as f:
        dados = json.load(f)
    for j in dados['jurados']:
        j['faixa_etaria'] = faixa(j['idade'])
    return dados


def faixa(idade):
    for ini, fim, rot in FAIXAS:
        if ini <= idade <= fim:
            return rot
    return '?'


def por_id(dados):
    return {j['id']: j for j in dados['jurados']}


# ------------------------------------------------------------------ filtros do público

_FILTRO = re.compile(r'^\s*([a-z_]+)\s*(>=|<=|!=|=|>|<)\s*(.+?)\s*$')


def _casa(j, filtro):
    m = _FILTRO.match(filtro)
    if not m:
        raise JuriRecusado(f'filtro inválido: {filtro!r} (ex.: idade>=18, regiao=Nordeste, internet!=nao-usa)')
    campo, op, valor = m.groups()
    if campo not in j:
        raise JuriRecusado(f'campo desconhecido no filtro: {campo}')
    v = j[campo]
    if op in ('>=', '<=', '>', '<'):
        try:
            v, alvo = float(v), float(valor)
        except (TypeError, ValueError):
            raise JuriRecusado(f'{campo} não é número: use = ou != no filtro')
        return {'>=': v >= alvo, '<=': v <= alvo, '>': v > alvo, '<': v < alvo}[op]
    opcoes = {x.strip().lower() for x in valor.split(',')}
    casa = str(v).lower() in opcoes or (isinstance(v, bool) and str(v).lower() in opcoes)
    return casa if op == '=' else not casa


def filtrar(jurados, filtros):
    return [j for j in jurados if all(_casa(j, f) for f in filtros)]


# ------------------------------------------------------------------ convocação (25) e conselho (7)
#
# Como no Tribunal do Júri (CPP arts. 447, 468 e 426 §4º): da lista geral de 100 alistados saem 25
# convocados por sessão; acusação e defesa recusam até 3 cada; 7 sorteados formam o Conselho de Sentença.
#
# Rodízio justo: SACO EMBARALHADO. A lista é embaralhada e consumida em ordem; ninguém repete antes de
# todos os 100 servirem (4 sessões cobrem a lista). Anti-clone: um jurado parecido demais com um já
# convocado nesta sessão volta para o topo do saco (não perde a vez, só não cai junto). Impedido (o juiz
# afasta quem não pode julgar o caso) também volta para o topo, sem gastar a vez.

SESSAO_N, CONSELHO_N, RECUSAS_MAX = 25, 7, 3
LIMIAR_CLONE = 3.0      # distância abaixo disso = perfil parecido demais para a mesma sessão
JANELA_CONSELHO = 4     # quem serviu no conselho nas últimas N sessões tem peso menor no sorteio
IMPEDIMENTOS_POR_TIPO = {'codigo': ['idade<12']}


def _distancia(a, b):
    d = sum(a.get(c) != b.get(c) for c in CAMPOS_DIVERSIDADE)
    return d + min(abs(a['idade'] - b['idade']) / 20, 2)


def caminho_estado():
    return os.path.join(RAIZ, 'local', 'convocacoes.json')


def ler_estado():
    c = caminho_estado()
    if not os.path.exists(c):
        return {}
    with open(c, encoding='utf-8-sig') as f:
        return json.load(f)


def gravar_estado(estado):
    os.makedirs(os.path.dirname(caminho_estado()), exist_ok=True)
    with open(caminho_estado(), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
        f.write('\n')


def _impedido(j, impedimentos):
    return any(_casa(j, f) for f in impedimentos)


def convocar(dados, caso='', tipo=None, n=SESSAO_N, impedimentos=(), semente=None, estado=None, excluir=()):
    """Sorteia os `n` convocados da sessão pelo saco embaralhado do foro. Devolve (sessao, estado novo,
    afastados). Não grava: quem chama grava o estado (o `--simular` do CLI não grava)."""
    estado = json.loads(json.dumps(estado if estado is not None else ler_estado()))
    foro = dados['foro']
    ids = por_id(dados)
    st = estado.setdefault(foro, {'saco': [], 'sessoes': []})
    rng = random.Random(semente)
    impedimentos = list(impedimentos) + IMPEDIMENTOS_POR_TIPO.get(tipo or '', [])
    st['saco'] = [i for i in st['saco'] if i in ids]
    # o próximo saco embaralhado entra ATRÁS do atual: o anti-clone sempre tem alternativa, e ninguém do
    # saco novo passa na frente de quem ainda não serviu no saco atual
    while len(st['saco']) < 2 * n:
        novo = [i for i in ids if i not in st['saco']]
        rng.shuffle(novo)
        st['saco'] += novo
    convocados, adiados, afastados = [], [], []
    tentativas = 0
    while len(convocados) < n and st['saco'] and tentativas < 3 * len(ids):
        tentativas += 1
        i = st['saco'].pop(0)
        if i in adiados or any(c['id'] == i for c in convocados):
            continue
        j = ids[i]
        if i in excluir:
            afastados.append((i, 'já julgou este caso (origem do recurso ou sala atual)'))
            adiados.append(i)
            continue
        if _impedido(j, impedimentos):
            afastados.append((i, 'impedido'))
            adiados.append(i)
            continue
        if convocados and min(_distancia(j, c) for c in convocados) < LIMIAR_CLONE and                 len(st['saco']) > n - len(convocados):
            afastados.append((i, 'parecido demais com um convocado: vai para a próxima sessão'))
            adiados.append(i)
            continue
        convocados.append(j)
    st['saco'] = adiados + st['saco']           # adiados e impedidos voltam para o topo: não perdem a vez
    sessao = {'id': f'{foro}-{len(st["sessoes"]) + 1:04d}', 'caso': caso, 'tipo': tipo,
              'convocados': [j['id'] for j in convocados], 'impedimentos': impedimentos,
              'recusas': {}, 'conselho': []}
    st['sessoes'].append(sessao)
    return sessao, estado, afastados


def _sessao(estado, foro, sessao_id):
    for s in (estado.get(foro) or {}).get('sessoes', []):
        if s['id'] == sessao_id:
            return s
    raise JuriRecusado(f'sessão não encontrada: {sessao_id} (rode juri convocar antes)')


def formar_conselho(dados, sessao_id, recusas_acusacao=(), recusas_defesa=(), n=CONSELHO_N, semente=None,
                    estado=None):
    """Aplica as recusas (até 3 por lado) e sorteia o Conselho de Sentença entre os que sobraram. Quem
    serviu no conselho nas últimas sessões tem peso menor. Devolve (conselho, estado novo)."""
    estado = json.loads(json.dumps(estado if estado is not None else ler_estado()))
    foro = dados['foro']
    s = _sessao(estado, foro, sessao_id)
    if s['conselho']:
        raise JuriRecusado(f'a sessão {sessao_id} já tem conselho: {", ".join(s["conselho"])}')
    for lado, rec in (('acusação', recusas_acusacao), ('defesa', recusas_defesa)):
        if len(rec) > RECUSAS_MAX:
            raise JuriRecusado(f'a {lado} recusou {len(rec)}: o máximo é {RECUSAS_MAX}')
        fora = [r for r in rec if r not in s['convocados']]
        if fora:
            raise JuriRecusado(f'recusa de quem não foi convocado: {", ".join(fora)}')
    recusados = set(recusas_acusacao) | set(recusas_defesa)
    restantes = [i for i in s['convocados'] if i not in recusados]
    if len(restantes) < n:
        raise JuriRecusado(f'sobraram {len(restantes)} depois das recusas: faltam jurados para o conselho de {n}')
    anteriores = [x for x in estado[foro]['sessoes'] if x['id'] != sessao_id and x['conselho']][-JANELA_CONSELHO:]
    servicos = {}
    for x in anteriores:
        for i in x['conselho']:
            servicos[i] = servicos.get(i, 0) + 1
    total = {}
    for x in estado[foro]['sessoes']:
        for i in x['conselho']:
            total[i] = total.get(i, 0) + 1
    media = sum(total.get(i, 0) for i in restantes) / len(restantes)
    rng = random.Random(semente)
    conselho = []
    pool = list(restantes)
    while len(conselho) < n:
        # menos peso a quem serviu nas últimas sessões; mais a quem está abaixo da média de serviços
        pesos = [(1 + 2 * max(0.0, media - total.get(i, 0))) / (1 + 2 * servicos.get(i, 0)) for i in pool]
        i = rng.choices(pool, weights=pesos)[0]
        conselho.append(i)
        pool.remove(i)
    s['recusas'] = {'acusacao': list(recusas_acusacao), 'defesa': list(recusas_defesa)}
    s['conselho'] = conselho
    ids = por_id(dados)
    return [ids[i] for i in conselho], estado


def sortear_livre(dados, n, filtros=(), semente=None):
    """Sorteio avulso com diversidade, sem mexer no rodízio (júri especializado, testes)."""
    rng = random.Random(semente)
    pool = filtrar(dados['jurados'], filtros) if filtros else list(dados['jurados'])
    rng.shuffle(pool)
    escolhidos = []
    while pool and len(escolhidos) < n:
        if escolhidos:
            pool.sort(key=lambda j: -min(_distancia(j, e) for e in escolhidos))
            pick = rng.choice(pool[:3])
        else:
            pick = pool[0]
        escolhidos.append(pick)
        pool.remove(pick)
    return escolhidos


# ------------------------------------------------------------------ conferência das cotas

def _marginal(jurados, campo, base=None):
    xs = [j for j in jurados if base is None or base(j)]
    cont = {}
    for j in xs:
        cont[str(j.get(campo))] = cont.get(str(j.get(campo)), 0) + 1
    return {k: 100 * v / len(xs) for k, v in cont.items()} if xs else {}


def conferir(dados):
    """[(dimensão, categoria, meta %, elenco %)] para cada cota do foro. Cada cota pode ter `base`
    ("idade>=25", por exemplo) para as que são de um recorte da população."""
    linhas = []
    for dim, cota in dados.get('cotas', {}).items():
        filtros = [cota['base']] if cota.get('base') else []
        jur = filtrar(dados['jurados'], filtros)
        real = _marginal(jur, cota.get('campo', dim))
        for cat, meta in cota['valores'].items():
            linhas.append((dim, cat, float(meta), real.get(cat, 0.0), len(jur)))
    return linhas


def resumo(j, curto=False):
    """Uma linha (curto) ou a ficha em texto de um jurado, para o prompt de quem vai interpretá-lo."""
    base = (f'{j["id"]} {j["nome"]}, {j["idade"]}, {j["ocupacao"]}, {j["cidade"]}-{j["uf"]} '
            f'({j["tipo_local"]}), {j["cor_raca"]}, renda {j["renda"]}, internet {j["internet"]}')
    if curto:
        return base
    p = j.get('personalidade') or {}
    l = [base,
         f'  escolaridade: {j["escolaridade"]} · vínculo: {j["vinculo"]} · religião: {j["religiao"]} · '
         f'{j.get("estado_civil", "")} · filhos: {j.get("filhos", 0)} · mora com: {j.get("mora_com", "")}',
         f'  dispositivo: {j.get("dispositivo", "")} · deficiência: {j.get("deficiencia") or "nenhuma"} · '
         f'Bolsa Família: {"sim" if j.get("bolsa_familia") else "não"}',
         '  personalidade (1-5): ' + ', '.join(f'{k} {v}' for k, v in p.items()),
         f'  valores: {", ".join(j.get("valores", []))}',
         f'  medos: {", ".join(j.get("medos", []))}',
         f'  viés: {j.get("vies", "")}',
         f'  repara em: {j.get("repara_em", "")}',
         f'  voz: {j.get("voz", "")}']
    if j['idade'] < IDADE_DE_VOZ:
        l.append(f'  ATENÇÃO: criança de {j["idade"]} anos. Não argumenta: o júri registra a REAÇÃO dela '
                 f'(o que faz, onde toca, quando larga), contada por {j.get("responsavel") or "um responsável"}.')
    return '\n'.join(l)
