"""
Os autos do caso: o registro de tudo o que aconteceu no julgamento (a fonte da ata e do save).

    caso            título, tipo, área, pergunta, opções de voto, público, descrição
    juri            foro, sessão, convocados (25), recusas, conselho (7)
    provas          o que o perito trouxe (pesquisa, teste, leitura de código, dado), aceita ou não pelo juiz
    acusacao        teses do promotor, cada uma com as provas que a sustentam
    defesa          teses da defesa, idem
    testemunhas     especialistas ouvidos
    votos           rodada 1: voto secreto dos 25 convocados; rodada 2: voto final dos 7 do conselho
    sentenca        veredito, confiança, fundamentação, condições, ponto de virada, próximo passo...
    decisao_usuario a instância final: o usuário acata ou recorre

Formato completo: referencias/autos.md.
"""

import json
import os
import re

from . import contraditorio as CT
from . import juri as J
from . import propostas as PR

TIPOS = {'ideia': 'Ideias', 'app': 'Apps', 'codigo': 'Código', 'decisao': 'Decisões', 'documento': 'Documentos',
         'outro': 'Outros'}
OPCOES_PADRAO = ['Procedente', 'Procedente com condições', 'Improcedente']


def carregar(caminho):
    if os.path.isdir(caminho):
        caminho = os.path.join(caminho, 'autos.json')
    with open(caminho, encoding='utf-8-sig') as f:
        return normalizar(json.load(f))


def normalizar(autos):
    """Aceita os nomes que se escrevem sem pensar: recusa com "id" vira "jurado"; status de ataque na sentença
    com "id" vira "ataque". Assim a validação não recusa os autos por um apelido de campo."""
    for lado in ((autos.get('juri') or {}).get('recusas') or {}).values():
        for r in lado if isinstance(lado, list) else []:
            if isinstance(r, dict) and 'jurado' not in r and 'id' in r:
                r['jurado'] = r.pop('id')
    for x in ((autos.get('sentenca') or {}).get('ataques') or []):
        if isinstance(x, dict) and 'ataque' not in x and 'id' in x:
            x['ataque'] = x.pop('id')
    return autos


def opcoes(autos):
    return autos.get('caso', {}).get('opcoes') or OPCOES_PADRAO


def validar(autos):
    """Lista de erros (vazia = autos válidos)."""
    e = []
    caso = autos.get('caso') or {}
    if not caso.get('titulo'):
        e.append('caso.titulo vazio')
    if caso.get('tipo') not in TIPOS:
        e.append(f'caso.tipo inválido: {caso.get("tipo")!r} (use {", ".join(TIPOS)})')
    if not caso.get('pergunta'):
        e.append('caso.pergunta vazia: o que o tribunal decide?')
    ops = opcoes(autos)
    j = autos.get('juri') or {}
    try:
        dados = J.carregar_foro(j.get('foro') or 'brasil')
    except J.JuriRecusado as x:
        return e + [str(x)]
    ids = J.por_id(dados)
    convocados = j.get('convocados') or []
    conselho = j.get('conselho') or []
    for i in convocados + conselho:
        if i not in ids:
            e.append(f'jurado desconhecido: {i}')
    if any(i not in convocados for i in conselho):
        e.append('há jurado no conselho que não foi convocado')
    provas = {p.get('id') for p in autos.get('provas', [])}
    for lado in ('acusacao', 'defesa'):
        for t in (autos.get(lado) or {}).get('teses', []):
            for p in t.get('provas', []):
                if p not in provas:
                    e.append(f'{lado} cita prova inexistente: {p}')
    vistos = set()
    for v in autos.get('votos', []):
        if v.get('rodada') not in (1, 2):
            e.append(f'voto com rodada inválida: {v}')
            continue
        if v.get('voto') not in ops:
            e.append(f'voto de {v.get("jurado")} fora das opções: {v.get("voto")!r}')
        if v.get('rodada') == 2 and v.get('jurado') not in conselho:
            e.append(f'{v.get("jurado")} votou na rodada 2 sem estar no conselho')
        if v.get('rodada') == 1 and convocados and v.get('jurado') not in convocados + (j.get('reforco') or []):
            e.append(f'{v.get("jurado")} votou na rodada 1 sem ter sido convocado')
        chave = (v.get('jurado'), v.get('rodada'))
        if chave in vistos:
            e.append(f'voto duplicado: {chave}')
        vistos.add(chave)
    s = autos.get('sentenca')
    if s:
        if s.get('veredito') not in ops:
            e.append(f'sentenca.veredito fora das opções: {s.get("veredito")!r}')
        c = s.get('confianca')
        if not isinstance(c, (int, float)) or not 0 <= c <= 100:
            e.append('sentenca.confianca deve ser um número de 0 a 100')
        for p in s.get('provas_decisivas', []):
            if p not in provas:
                e.append(f'sentença cita prova inexistente: {p}')
    e += CT.validar(autos, ops)
    e += PR.validar(autos)
    return e


# ------------------------------------------------------------------ placar

def _contar(votos, ops):
    c = {o: 0 for o in ops}
    for v in votos:
        c[v['voto']] = c.get(v['voto'], 0) + 1
    return c


def _maioria(cont):
    if not cont or not sum(cont.values()):
        return None
    top = max(cont.values())
    vencedores = [k for k, v in cont.items() if v == top]
    return vencedores[0] if len(vencedores) == 1 else 'empate'


MIN_SEGMENTO = 5          # segmento com menos jurados que isso oscila com 1 voto: não entra em "onde se dividiu"
MARGEM_SEGMENTO = 2       # e a maioria do segmento precisa vencer a opção geral por 2 votos ou mais.
# Medido em 2026-11-09: a mesma versão, rodada 2 vezes, repetiu 19 de 25 votos e virou 3 segmentos de 5+ pessoas.
REAMOSTRAS = 2000
PARAR_MINIMO, PARAR_LIMIAR = 15, 0.95
REFORCO_LIMIAR = 0.80     # abaixo desta estabilidade, a sala ganha mais 25 jurados. Era 0,90: nos 2 casos reais
                          # (79% e 82%) o reforço só confirmou o líder; entre 80% e 90% ele não muda o veredito


def estabilidade(votos, ops, reamostras=REAMOSTRAS, semente=2026):
    """Reamostragem (bootstrap): sorteia, com reposição, conjuntos do mesmo tamanho e conta em quantos a
    maioria continua a mesma. É a estabilidade estatística do resultado, sem gastar token."""
    import random
    if not votos:
        return {'opcao': None, 'estabilidade': None, 'n': 0}
    alvo = _maioria(_contar(votos, ops))
    if alvo in (None, 'empate'):
        return {'opcao': alvo, 'estabilidade': 0.0, 'n': len(votos)}
    rng = random.Random(semente)
    vs = [v['voto'] for v in votos]
    iguais = 0
    for _ in range(reamostras):
        amostra = [rng.choice(vs) for _ in vs]
        c = {o: 0 for o in ops}
        for x in amostra:
            c[x] = c.get(x, 0) + 1
        iguais += _maioria(c) == alvo
    return {'opcao': alvo, 'estabilidade': iguais / reamostras, 'n': len(votos)}


def parar_cedo(autos, minimo=PARAR_MINIMO, limiar=PARAR_LIMIAR):
    """Parada antecipada da rodada 1: com pelo menos `minimo` votos e a maioria estável em `limiar` das
    reamostragens, os lotes restantes não mudariam a liderança: dá para pular. Devolve (pode, info)."""
    r1 = [v for v in autos.get('votos', []) if v.get('rodada') == 1]
    e = estabilidade(r1, opcoes(autos))
    return (e['n'] >= minimo and (e['estabilidade'] or 0) >= limiar), e


def confianca_sugerida(autos):
    """A confiança da rubrica, calculada (referencias/rubrica.md). O juiz parte deste número e justifica o ajuste.
    Devolve (valor, [(parcela, pontos)])."""
    ops = opcoes(autos)
    r1 = [v for v in autos.get('votos', []) if v.get('rodada') == 1]
    r2 = [v for v in autos.get('votos', []) if v.get('rodada') == 2]
    c2 = sorted(_contar(r2, ops).values(), reverse=True) + [0, 0]
    if not r2:
        return None, []
    vantagem = c2[0] - c2[1]
    base = {0: 50, 1: 55, 2: 60, 3: 65, 4: 70, 5: 75, 6: 80, 7: 85}.get(vantagem, 85)
    partes = [(f'margem do conselho ({c2[0]} x {c2[1]})', base)]
    m1, m2 = _maioria(_contar(r1, ops)), _maioria(_contar(r2, ops))
    if r1:
        partes.append(('sala concorda com o conselho' if m1 == m2 else 'sala discorda do conselho', 5 if m1 == m2 else -10))
    lac = sum(1 for p in autos.get('provas', []) if p.get('tipo') == 'lacuna' and p.get('aceita', True))
    if lac:
        partes.append((f'{lac} lacuna(s) nas provas', -min(15, 5 * lac)))
    st = {x.get('ataque'): x.get('status') for x in (autos.get('sentenca') or {}).get('ataques', [])}
    graves = sum(1 for t in (autos.get('acusacao') or {}).get('teses', [])
                 if t.get('gravidade') == 'grave' and st.get(t.get('id')) == 'de_pe')
    if graves:
        partes.append((f'{graves} ataque(s) GRAVE de pé', -5 * graves))
    valor = sum(p for _, p in partes)
    e2 = estabilidade(r2, ops)['estabilidade']
    if e2 is not None and valor > 100 * e2 + 15:
        partes.append(('teto: estabilidade do conselho + 15', round(100 * e2 + 15) - valor))
        valor = round(100 * e2 + 15)
    return max(5, min(95, valor)), partes


# Jargão que uma pessoa sem estudo, ou uma criança, dificilmente usaria: sinal de que o modelo "vazou" a voz dele.
JARGAO = ('mvp', 'funil', 'métrica', 'metrica', 'kpi', 'onboarding', 'churn', 'roi', 'stakeholder', 'framework',
          'pitch', 'feature', 'benchmark', 'concierge', 'backlog', 'insight', 'engajamento', 'lead', 'conversão',
          'escalável', 'escalar', 'disrupt', 'ux', 'ui ', 'b2b', 'b2c', 'saas', 'go-to-market', 'product-market')
ESCOLARIDADE_BAIXA = ('fundamental incompleto ou sem instrução', 'fundamental completo', 'criança (fora da escola ou creche)',
                      'pré-escola', 'ensino fundamental (cursando)')


def fidelidade(autos):
    """[(jurado, rodada, termo)] para votos com jargão vindo de quem a ficha diz que não o usaria."""
    import re
    dados = J.carregar_foro((autos.get('juri') or {}).get('foro') or 'brasil')
    ids = J.por_id(dados)
    achados = []
    for v in autos.get('votos', []):
        j = ids.get(v.get('jurado'))
        if not j or not (j['escolaridade'] in ESCOLARIDADE_BAIXA or j['idade'] < 15):
            continue
        texto = ' ' + str(v.get('motivo', '')).lower() + ' '
        for termo in JARGAO:
            if re.search(r'(?<![a-zà-ú])' + re.escape(termo.strip()) + r'(?![a-zà-ú])', texto):
                achados.append((v['jurado'], v['rodada'], termo.strip()))
    return achados


def placar(autos):
    """Rodada 1 (os 25) no total e por segmento, rodada 2 (o conselho), e quem do conselho mudou de voto."""
    dados = J.carregar_foro((autos.get('juri') or {}).get('foro') or 'brasil')
    ids = J.por_id(dados)
    ops = opcoes(autos)
    r1 = [v for v in autos.get('votos', []) if v.get('rodada') == 1 and v.get('jurado') in ids]
    r2 = [v for v in autos.get('votos', []) if v.get('rodada') == 2 and v.get('jurado') in ids]
    total1 = _contar(r1, ops)
    geral = _maioria(total1)
    segmentos = {}
    for campo in J.SEGMENTOS:
        grupos = {}
        for v in r1:
            grupos.setdefault(str(ids[v['jurado']].get(campo)), []).append(v)
        linhas = []
        for cat, vs in sorted(grupos.items()):
            cont = _contar(vs, ops)
            m = _maioria(cont)
            linhas.append({'categoria': cat, 'n': len(vs), 'contagem': cont, 'maioria': m,
                           'diverge': (len(vs) >= MIN_SEGMENTO and m not in (geral, 'empate', None)
                                       and cont.get(m, 0) - cont.get(geral, 0) >= MARGEM_SEGMENTO)})
        segmentos[campo] = linhas
    antes = {v['jurado']: v for v in r1}
    mudancas = []
    for v in r2:
        a = antes.get(v['jurado'])
        if a and a['voto'] != v['voto']:
            mudancas.append({'jurado': v['jurado'], 'nome': ids[v['jurado']]['nome'], 'de': a['voto'],
                             'para': v['voto'], 'motivo': v.get('motivo', '')})
    return {'opcoes': ops, 'rodada1': total1, 'maioria1': geral, 'n1': len(r1),
            'rodada2': _contar(r2, ops), 'maioria2': _maioria(_contar(r2, ops)), 'n2': len(r2),
            'segmentos': segmentos, 'mudancas': mudancas,
            'estabilidade1': estabilidade(r1, ops), 'estabilidade2': estabilidade(r2, ops),
            'parada': (autos.get('juri') or {}).get('rodada1_parada'),
            'confianca_sugerida': confianca_sugerida(autos) if r2 else None,
            'fidelidade': fidelidade(autos)}


def placar_md(p):
    l = []
    fmt = lambda c: ' · '.join(f'{k} **{v}**' for k, v in c.items())
    l += [f'**Voto secreto dos {p["n1"]} convocados:** {fmt(p["rodada1"])}', '']
    if p['n2']:
        l += [f'**Voto final do Conselho de Sentença ({p["n2"]}):** {fmt(p["rodada2"])}', '']
    pct = lambda e: f'{round(100 * e["estabilidade"])}%' if e and e.get('estabilidade') is not None else '-'
    e1, e2 = p.get('estabilidade1'), p.get('estabilidade2')
    if e1 and e1['n']:
        l += [f'**Estabilidade por reamostragem** ({REAMOSTRAS} sorteios): a maioria da sala ({e1["opcao"]}) se '
              f'mantém em **{pct(e1)}**' + (f'; a do conselho ({e2["opcao"]}), em **{pct(e2)}**' if e2 and e2['n'] else '')
              + '.', '']
    if p.get('confianca_sugerida'):
        v, partes = p['confianca_sugerida']
        l += [f'**Confiança sugerida: {v}%** (' + '; '.join(f'{k} {"+" if n > 0 else ""}{n}' for k, n in partes)
              + '). O juiz parte daqui e justifica qualquer ajuste.', '']
    if p.get('fidelidade'):
        l += ['**Confira, pode estar fora do personagem** (jargão de quem a ficha diz que não usaria; se não for '
              'citação do que ouviu, rode o lote de novo): '
              + ', '.join(f'{j} r{r} "{t}"' for j, r, t in p['fidelidade']), '']
    if p.get('parada'):
        l += [f'_Rodada 1 encerrada antes, com {p["parada"]["n"]} votos: a liderança já era estável em '
              f'{round(100 * p["parada"]["estabilidade"])}% das reamostragens._', '']
    div = [(campo, x) for campo, xs in p['segmentos'].items() for x in xs if x['diverge']]
    if div:
        l += [f'**Onde o júri se dividiu** (segmentos com {MIN_SEGMENTO} ou mais jurados cuja maioria vence a geral por '
              f'{MARGEM_SEGMENTO}+ votos; segmento é indício, não prova: varia entre julgamentos):', '']
        l += [f'- {campo.replace("_", " ")} = {x["categoria"]} ({x["n"]}): maioria **{x["maioria"]}** · '
              + fmt({k: v for k, v in x['contagem'].items() if v}) for campo, x in div]
        l.append('')
    if p['mudancas']:
        l += ['**Quem mudou de voto no debate:**', '']
        l += [f'- {m["nome"]} ({m["jurado"]}): {m["de"]} → {m["para"]}. {m["motivo"]}' for m in p['mudancas']]
        l.append('')
    elif p['n2']:
        l += ['Ninguém do conselho mudou de voto no debate.', '']
    return '\n'.join(l)


# ------------------------------------------------------------------ ata

def ata_md(autos):
    """A ata do julgamento em Markdown: o corpo do save no Memory Card e o que se entrega ao usuário."""
    caso = autos['caso']
    j = autos.get('juri') or {}
    dados = J.carregar_foro(j.get('foro') or 'brasil')
    ids = J.por_id(dados)
    l = ['## O caso', '', f'**Pergunta ao tribunal:** {caso["pergunta"]}', '']
    if caso.get('descricao'):
        l += [caso['descricao'], '']
    l += [f'- **Tipo:** {TIPOS.get(caso["tipo"], caso["tipo"])}']
    if caso.get('area'):
        l.append(f'- **Área:** {caso["area"]}')
    if caso.get('publico'):
        l.append(f'- **Público:** {caso["publico"]}')
    l += [f'- **Opções de voto:** {", ".join(opcoes(autos))}', '']
    if autos.get('propostas'):
        l.append(PR.placar_md(autos))
    l += ['## O júri', '']
    l.append(f'Foro **{dados.get("nome", j.get("foro"))}**, sessão `{j.get("sessao", "-")}`: '
             f'{len(j.get("convocados", []))} convocados, {len(j.get("conselho", []))} no Conselho de Sentença.')
    rec = j.get('recusas') or {}
    for lado, rot in (('acusacao', 'Recusas da acusação'), ('defesa', 'Recusas da defesa')):
        for r in rec.get(lado, []):
            rid = r['jurado'] if isinstance(r, dict) else r
            mot = r.get('motivo', '') if isinstance(r, dict) else ''
            l.append(f'- {rot}: {ids[rid]["nome"]} ({rid}){": " + mot if mot else ""}')
    if j.get('conselho'):
        l += ['', '**Conselho de Sentença:**', '']
        l += [f'- {J.resumo(ids[i], curto=True)}' for i in j['conselho']]
    l.append('')
    if autos.get('provas'):
        l += ['## Provas', '', '| Id | Tipo | Prova | Fonte | Aceita |', '|---|---|---|---|---|']
        for p in autos['provas']:
            l.append(f'| {p["id"]} | {p.get("tipo", "")} | {_cel(p.get("descricao", ""))} | {_cel(p.get("fonte", ""))} | '
                     f'{"sim" if p.get("aceita", True) else "não: " + _cel(p.get("motivo_recusa", ""))} |')
        l.append('')
    for lado, tit in (('acusacao', 'Acusação (promotor)'), ('defesa', 'Defesa')):
        teses = (autos.get(lado) or {}).get('teses', [])
        if teses:
            l += [f'## {tit}', '']
            l += [f'{n}. ' + (f'**{t["id"]}** ' if t.get('id') else '') +
                  (f'[{t["gravidade"].upper()}] ' if t.get('gravidade') else '') + t['texto'] +
                  (f' _(provas: {", ".join(t["provas"])})_' if t.get('provas') else '') +
                  (f' Contraexemplo: {t["contraexemplo"]}' if t.get('contraexemplo') else '')
                  for n, t in enumerate(teses, 1)]
            l.append('')
    contra = CT.ata_md(autos)
    if contra:
        l.append(contra)
    if autos.get('testemunhas'):
        l += ['## Testemunhas', '']
        l += [f'- **{t["nome"]}** ({t.get("especialidade", "")}): {t.get("depoimento", "")}' for t in autos['testemunhas']]
        l.append('')
    if autos.get('votos'):
        l += ['## Placar', '', placar_md(placar(autos))]
        falas = [v for v in autos['votos'] if v.get('rodada') == 2 and v.get('motivo')]
        if falas:
            l += ['**Votos do conselho:**', '']
            l += [f'- **{ids[v["jurado"]]["nome"]}** ({ids[v["jurado"]]["idade"]}): {v["voto"]}. "{v["motivo"]}"'
                  for v in falas]
            l.append('')
    s = autos.get('sentenca')
    if s:
        l += ['## Sentença', '', f'**Veredito: {s["veredito"]}** · confiança {s["confianca"]}%', '']
        if s.get('fundamentacao'):
            l += [s['fundamentacao'], '']
        pares = [('Condições', s.get('condicoes')), ('Ponto de virada', s.get('ponto_de_virada')),
                 ('Provas decisivas', ', '.join(s.get('provas_decisivas', [])) or None),
                 ('Voto vencido', s.get('voto_vencido')), ('Próximo passo barato', s.get('proximo_passo')),
                 ('Critério de abandono', s.get('criterio_de_abandono'))]
        for k, v in pares:
            if isinstance(v, list):
                if v:
                    l += [f'**{k}:**', ''] + [f'- {x}' for x in v] + ['']
            elif v:
                l += [f'**{k}:** {v}', '']
    if autos.get('plano'):
        l.append(plano_md(autos['plano']))
    d = autos.get('decisao_usuario') or {}
    if d.get('acatou') is not None:
        l += ['## Instância final', '']
        l.append('O usuário **acatou** a sentença.' if d['acatou'] else
                 f'O usuário **recorreu**: {d.get("recurso") or "sem motivo registrado"}')
        if d.get('decisao'):
            l.append(f'Decisão: {d["decisao"]}')
        l.append('')
    return '\n'.join(l).rstrip('\n') + '\n'


def plano_md(p, natural=False):
    """O plano de ação (rito 2): passos, metas, testes e critério de abandono."""
    if not p:
        return ''
    l = ['## ' + ('O plano, passo a passo' if natural else 'Plano de ação'), '']
    if p.get('recomendacao'):
        l += [('**O que eu faria:** ' if natural else '**Recomendação:** ') + str(p['recomendacao']), '']
    c = p.get('certeza') or {}
    if c.get('por_que'):
        l += [('**Por que essa certeza:** ' if natural else '**Certeza:** ') + str(c['por_que'])
              + (f' Sobe se {c["sobe_se"]}' if c.get('sobe_se') else '') + (f' Desce se {c["desce_se"]}' if c.get('desce_se') else ''), '']
    b = p.get('passo_mais_barato') or {}
    if b.get('o_que'):
        l += [('**Comece por aqui:** ' if natural else '**Passo mais barato:** ') + str(b['o_que'])
              + (' (' + '; '.join(f'{k}: {b[k]}' for k in ('custo', 'tempo') if b.get(k)) + ')' if b.get('custo') or b.get('tempo') else ''), '']
    l += [f'{x}' if str(x)[:2].strip().rstrip('.').isdigit() else f'- {x}' for x in p.get('ordem') or []]
    if p.get('metas'):
        l += ['', '| ' + ('O que medir' if natural else 'Meta') + ' | Grupo | Como medir | Número que decide | Prazo |', '|---|---|---|---|---|']
        l += [f'| {_cel(m.get("o_que", ""))} | {_cel(m.get("grupo", "todos"))} | {_cel(m.get("como_medir", ""))} | {_cel(m.get("meta", ""))} | {_cel(m.get("prazo", ""))} |'
              for m in p['metas']]
    if p.get('testes'):
        l += ['', '| ' + ('O que testar' if natural else 'Teste') + ' | Entrada | Esperado |', '|---|---|---|']
        l += [f'| {_cel(t.get("o_que", ""))} | {_cel(t.get("entrada", ""))} | {_cel(t.get("esperado", ""))} |' for t in p['testes']]
    if p.get('cenarios'):
        l += ['', '| ' + ('Se acontecer' if natural else 'Cenário') + ' | ' + ('O que muda' if natural else 'Efeito na decisão') + ' | Certeza |', '|---|---|---|']
        l += [f'| {_cel(c.get("se", ""))} | {_cel(c.get("entao", ""))} | {_cel(c.get("certeza", ""))} |' for c in p['cenarios']]
    if p.get('criterio_de_abandono'):
        l += ['', ('**Quando desistir:** ' if natural else '**Critério de abandono:** ') + str(p['criterio_de_abandono'])]
    if p.get('atencao'):
        l += ['', '**Atenção:**', ''] + [f'- {x}' for x in p['atencao']]
    if p.get('hipoteses'):
        l += ['', ('**A confirmar (não está nas provas):**' if natural else '**Hipóteses a confirmar:**'), '']
        l += [f'- {h}' for h in p['hipoteses']]
    l.append('')
    return '\n'.join(l)


def entrega_md(autos, natural=False, enxuta=False):
    """O que se mostra ao usuário no fim: decisão, plano e problemas, montados direto dos autos (sem colagem à
    mão). A ata completa continua sendo o registro do processo. enxuta=True deixa só decisão, plano, riscos e
    condições: sem status do contraditório, sem vozes do júri e sem rodapé."""
    from . import linguagem as LG
    modo = 'natural' if natural else 'tribunal'
    caso, s, p = autos['caso'], autos.get('sentenca') or {}, autos.get('plano') or {}
    if not s:
        return '# ' + caso.get('titulo', '') + '\n\nAinda sem sentença.\n'
    l = [f'# {caso.get("titulo", "")}', '', f'_{caso.get("pergunta", "")}_', '',
         f'**{LG.t("veredito", modo)}: {LG.opcao(s["veredito"], modo)}** · {LG.t("confianca", modo)} {s.get("confianca")}%', '']
    if p:
        l.append(plano_md(p, natural=natural))
    else:
        for k in ('proximo_passo', 'criterio_de_abandono'):
            if s.get(k):
                l += [f'**{LG.t(k, modo)}:** {s[k]}', '']
    teses = (autos.get('acusacao') or {}).get('teses', [])
    if teses:
        st = {x.get('ataque'): x.get('status') for x in s.get('ataques', [])}
        resp = {r.get('ataque'): r for r in (autos.get('defesa') or {}).get('respostas', [])}
        l += ['## ' + ('Problemas encontrados' if natural or enxuta else 'Ataques e como ficaram'), '']
        for t in teses:
            g = LG.t((t.get('gravidade') or '').lower(), modo)
            ch = t.get('checagem') or {}
            reb = (f' (era {LG.t(str(ch.get("gravidade_original", "")).lower(), modo)}; a checagem dupla rebaixou)'
                   if ch.get('veredito') in ('rebaixa', 'derruba') else '')
            stt = LG.t(st.get(t.get('id'), ''), modo) if st.get(t.get('id')) else ''
            cor = (resp.get(t.get('id')) or {}).get('correcao')
            if enxuta:
                l.append(f'- **{g}**: {(ch.get("motivo") if reb and ch.get("motivo") else t["texto"])}' + (f' Correção: {cor}' if cor else ''))
            else:
                l.append(f'- **{g}**{reb}: {t["texto"]}' + (f' → {stt}' if stt else '') + (f'. Correção: {cor}' if cor else ''))
        l.append('')
    if s.get('condicoes'):
        l += ['## ' + LG.t('condicoes', modo), ''] + [f'{i}. {c}' for i, c in enumerate(s['condicoes'], 1)] + ['']
    falas, vistos = [], set()
    for v in autos.get('votos', []):
        if v.get('rodada') == 2 and v.get('motivo') and v.get('voto') not in vistos:
            vistos.add(v['voto']); falas.append(v)
    if falas and not enxuta:
        l += ['## ' + ('O que as pessoas disseram' if natural else 'Vozes do conselho'), '']
        l += [f'- {LG.opcao(v["voto"], modo)}: "{v["motivo"]}"' for v in falas[:3]] + ['']
    if not enxuta:
        l.append('_Processo completo (júri, placar, provas): `python tribunal.py ata`._')
    return '\n'.join(l).rstrip() + '\n'


def _cel(t):
    return str(t).replace('|', '\\|').replace('\n', ' ')


_CPF = re.compile(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b')
_EMAIL = re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.]+\b')
_SEGREDO = re.compile(r'(?i)\b(api[_-]?key|token|senha|password|secret)\b\s*[:=]')


def avisos_de_privacidade(texto):
    a = []
    if _CPF.search(texto):
        a.append('os autos têm algo com cara de CPF')
    if _EMAIL.search(texto):
        a.append('os autos têm algo com cara de e-mail')
    if _SEGREDO.search(texto):
        a.append('os autos têm algo com cara de senha ou chave: confira antes de salvar')
    return a
