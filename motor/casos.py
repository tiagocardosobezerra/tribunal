"""
Onde os casos moram e o que acontece com eles ao longo do rito (melhorias julgadas pelo próprio Tribunal em
2026-11-09, caso "Aprimorar a experiência do próprio Tribunal"):

- pasta fixa: os autos podem morar em ~/tribunal-autos (com o consentimento do usuário, uma vez) em vez da
  pasta da sessão, que pode sumir;
- novo caso: cria a pasta e o esqueleto dos autos;
- último caso: `abrir` sem argumento acha os autos mais recentes;
- fase: carimba a hora de cada fase (métrica de tempo), regera a sala ao vivo e devolve a linha de narração;
- comparar: confere se duas versões de um julgamento chegaram ao mesmo lugar (veredito, confiança e placar
  por segmento), a trava antes de mudar o rito.
"""

import datetime
import glob
import json
import os
import re
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL = os.environ.get('TRIBUNAL_LOCAL') or os.path.join(RAIZ, 'local')   # os testes usam uma pasta temporária
PREFS = os.path.join(LOCAL, 'preferencias.json')
ULTIMO = os.path.join(LOCAL, 'ultimo_caso.json')
PASTA_PADRAO = os.path.join(os.path.expanduser('~'), 'tribunal-autos')

NARRACAO = {
    'autuacao': 'Caso aberto: {titulo}.',
    'convocacao': 'Convocação feita: {n_convocados} jurados entraram na sala.',
    'conselho': 'Recusas feitas e Conselho de Sentença sorteado ({n_conselho}).',
    'propostas': 'Concurso: {n_propostas} propostas escritas.',
    'contraditorio': 'Propostas atacadas e respondidas; finalistas definidas.',
    'pericia': 'O perito juntou {n_provas} provas.',
    'rodada1': 'Voto secreto da sala: {placar1}.',
    'debates': 'Debates: {n_ataques} ataques da acusação ({graves}).',
    'replica': 'Réplica: a defesa concedeu {concede} e rebateu {rebate}.',
    'rodada2': 'Voto final do conselho: {placar2}.',
    'sentenca': 'Sentença: {veredito}, confiança {confianca}%.',
}


class CasoRecusado(RuntimeError):
    """O pedido sobre o caso não pode seguir."""


def _ler_json(caminho, padrao):
    try:
        with open(caminho, encoding='utf-8-sig') as f:
            return json.load(f)
    except (OSError, ValueError):
        return padrao


def _gravar_json(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write('\n')


def agora():
    return datetime.datetime.now().isoformat(timespec='seconds')


def slug(texto):
    t = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii').lower()
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:60] or 'caso'


# ------------------------------------------------------------------ pasta dos casos

def preferencias():
    return _ler_json(PREFS, {})


def linguagem():
    """'tribunal' ou 'simples'; None = o usuário ainda não escolheu (pergunte uma vez)."""
    return preferencias().get('linguagem')


def definir_linguagem(modo):
    p = preferencias()
    p['linguagem'] = modo
    _gravar_json(PREFS, p)
    return modo


def definir_pasta(pasta):
    """pasta = caminho (a pasta fixa) ou None (os autos ficam na pasta de trabalho da sessão)."""
    p = preferencias()
    p['pasta_autos'] = os.path.abspath(os.path.expanduser(pasta)) if pasta else None
    p['perguntado_em'] = agora()
    _gravar_json(PREFS, p)
    return p['pasta_autos']


def _local(cwd=None):
    """A pasta tribunal-autos da pasta de trabalho; se já estamos dentro dela, ela mesma (nada de aninhar)."""
    c = os.path.abspath(cwd or os.getcwd())
    return c if os.path.basename(c) == 'tribunal-autos' else os.path.join(c, 'tribunal-autos')


def pasta_base(cwd=None):
    """(pasta, decidido). decidido=False: ainda não se perguntou ao usuário (pergunte uma vez)."""
    p = preferencias()
    if 'pasta_autos' in p:
        return (p['pasta_autos'] or _local(cwd)), True
    return _local(cwd), False


def novo_caso(titulo, tipo='outro', cwd=None, data=None):
    base, decidido = pasta_base(cwd)
    data = data or datetime.date.today().isoformat()
    pasta = os.path.join(base, f'{data}-{slug(titulo)}')
    arq = os.path.join(pasta, 'autos.json')
    if os.path.exists(arq):
        raise CasoRecusado(f'já existe um caso aqui: {arq}')
    autos = {'rito': 3, 'caso': {'titulo': titulo, 'tipo': tipo, 'pergunta': '', 'explicacao': '', 'data': data},
             'juri': {'foro': 'brasil'}, 'provas': [], 'votos': [],
             'metricas': {'inicio': agora(), 'fases': {}, 'abrir_ok': None, 'comandos_pedidos': 0}}
    _gravar_json(arq, autos)
    lembrar_ultimo(arq)
    return arq, decidido


# ------------------------------------------------------------------ último caso

def lembrar_ultimo(arq):
    _gravar_json(ULTIMO, {'autos': os.path.abspath(arq), 'quando': agora()})


def ultimo_caso(cwd=None):
    """O autos.json mais recente: o lembrado, ou o mais novo na pasta fixa e na pasta de trabalho."""
    lembrado = _ler_json(ULTIMO, {}).get('autos')
    candidatos = [lembrado] if lembrado and os.path.exists(lembrado) else []
    bases = {pasta_base(cwd)[0], _local(cwd), PASTA_PADRAO}
    for b in bases:
        candidatos += glob.glob(os.path.join(b, '*', 'autos.json'))
    candidatos = [c for c in candidatos if c and os.path.exists(c)]
    if not candidatos:
        raise CasoRecusado('nenhum caso encontrado: comece um julgamento (ou passe o caminho dos autos)')
    return max(candidatos, key=os.path.getmtime)


# ------------------------------------------------------------------ fases e métricas

def _placar_curto(autos, rodada):
    from . import autos as A
    p = A.placar(autos)
    cont = p['rodada1'] if rodada == 1 else p['rodada2']
    return ' · '.join(f'{k.split(":")[0]} {v}' for k, v in cont.items() if v) or 'sem votos'


def narracao(autos, fase):
    s = autos.get('sentenca') or {}
    teses = (autos.get('acusacao') or {}).get('teses', [])
    resp = (autos.get('defesa') or {}).get('respostas', [])
    grav = {}
    for t in teses:
        g = (t.get('gravidade') or 'sem gravidade')
        grav[g] = grav.get(g, 0) + 1
    v = {
        'titulo': (autos.get('caso') or {}).get('titulo', ''),
        'n_convocados': len((autos.get('juri') or {}).get('convocados', [])),
        'n_conselho': len((autos.get('juri') or {}).get('conselho', [])),
        'n_propostas': len(autos.get('propostas') or []),
        'n_provas': len(autos.get('provas') or []),
        'n_ataques': len(teses),
        'graves': ', '.join(f'{n} {g}' for g, n in grav.items()) or 'nenhum',
        'concede': sum(1 for r in resp if r.get('tipo') == 'concede'),
        'rebate': sum(1 for r in resp if r.get('tipo') == 'rebate'),
        'veredito': s.get('veredito', ''), 'confianca': s.get('confianca', ''),
    }
    if fase in ('rodada1', 'rodada2') and autos.get('votos'):
        v['placar1'] = _placar_curto(autos, 1)
        v['placar2'] = _placar_curto(autos, 2)
    try:
        return NARRACAO[fase].format(**v)
    except (KeyError, IndexError):
        return f'Fase concluída: {fase}.'


def marcar_fase(arq, fase):
    """Carimba a hora da fase nos autos e devolve a linha de narração para a conversa."""
    from . import autos as A
    autos = A.carregar(arq)
    m = autos.setdefault('metricas', {'inicio': agora(), 'fases': {}, 'abrir_ok': None, 'comandos_pedidos': 0})
    m.setdefault('fases', {})[fase] = agora()
    _gravar_json(arq, autos)
    lembrar_ultimo(arq)
    return narracao(autos, fase)


def registrar_abrir(arq, ok):
    from . import autos as A
    autos = A.carregar(arq)
    m = autos.setdefault('metricas', {'inicio': agora(), 'fases': {}, 'comandos_pedidos': 0})
    if m.get('abrir_ok') is None:            # vale a 1ª tentativa
        m['abrir_ok'] = bool(ok)
    _gravar_json(arq, autos)


def tempo_ate_sentenca(autos):
    m = autos.get('metricas') or {}
    ini, fim = m.get('inicio'), (m.get('fases') or {}).get('sentenca')
    if not ini or not fim:
        return None
    d = datetime.datetime.fromisoformat(fim) - datetime.datetime.fromisoformat(ini)
    return int(d.total_seconds() // 60)


# ------------------------------------------------------------------ comparar duas versões de um julgamento

def comparar(autos_a, autos_b):
    """O que mudou entre dois julgamentos do mesmo caso: veredito, confiança e maioria de cada segmento."""
    from . import autos as A
    sa, sb = autos_a.get('sentenca') or {}, autos_b.get('sentenca') or {}
    pa, pb = A.placar(autos_a), A.placar(autos_b)

    def maiorias(p):
        return {(campo, x['categoria']): x['maioria'] for campo, xs in p['segmentos'].items() for x in xs if x['n'] >= A.MIN_SEGMENTO}

    ma, mb = maiorias(pa), maiorias(pb)
    comuns = [k for k in ma if k in mb]
    iguais = [k for k in comuns if ma[k] == mb[k]]
    return {
        'veredito_igual': sa.get('veredito') == sb.get('veredito'),
        'veredito': (sa.get('veredito'), sb.get('veredito')),
        'confianca': (sa.get('confianca'), sb.get('confianca')),
        'segmentos_comparados': len(comuns),
        'segmentos_iguais': len(iguais),
        'segmentos_diferentes': [(k, ma[k], mb[k]) for k in comuns if ma[k] != mb[k]],
        # virada de verdade: maioria clara nas duas versões, mas outra opção. empate <-> maioria é oscilação
        # comum em grupo pequeno (1 voto decide) e não conta como virada.
        'viradas': [(k, ma[k], mb[k]) for k in comuns if ma[k] != mb[k] and 'empate' not in (ma[k], mb[k])],
    }
