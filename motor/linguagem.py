"""
Dois modos de linguagem para o mesmo julgamento.

- "tribunal": os termos do rito (Conselho de Sentença, Procedente, réplica, ataque FATAL...).
- "natural": as mesmas coisas, em palavras do dia a dia que qualquer pessoa entende ("simples" ainda é aceito).

Só a APRESENTAÇÃO muda: os autos guardam sempre os termos oficiais (validação, Memory Card, `comparar` e
calibração dependem deles). Este dicionário é a única fonte: o Python usa para a ata e o placar, e a sala
recebe o mesmo dicionário embutido.
"""

MODOS = ('tribunal', 'natural')
APELIDOS = {'simples': 'natural'}
PADRAO = 'tribunal'

# chave: (tribunal, natural). No modo tribunal, o texto natural vira a dica ao passar o mouse.
TERMOS = {
    'Procedente': ('Procedente', 'Vale a pena'),
    'Procedente com condições': ('Procedente com condições', 'Vale, se ajustar'),
    'Improcedente': ('Improcedente', 'Não vale'),
    'juiz': ('Juiz(a)', 'Juiz(a)'),
    'juiz_papel': ('juiz', 'conduz e decide'),
    'promotor': ('Promotor(a)', 'Quem procura problemas'),
    'promotor_papel': ('promotor', 'procura problemas'),
    'defesa': ('Defesa', 'Quem defende'),
    'defesa_papel': ('defesa', 'defende a ideia'),
    'perito': ('Perito(a)', 'Quem checa os fatos'),
    'perito_papel': ('perito', 'checa os fatos'),
    'escrivao': ('Escrivão(ã)', 'Quem anota'),
    'escrivao_papel': ('escrivão', 'anota tudo'),
    'voce_papel': ('instância final', 'a palavra final é sua'),
    'jurado': ('jurado(a)', 'pessoa do júri'),
    'sala': ('Sala', 'Todos'),
    'conselho': ('Conselho de Sentença', 'Os 7 que decidem'),
    'conselho_curto': ('Conselho', 'Os 7'),
    'voto_secreto': ('Voto secreto', 'Cada um vota sozinho'),
    'abertura': ('Abertura', 'Começo'),
    'concurso': ('Concurso', 'Ideias competem'),
    'recusas': ('Recusas', 'Jurados retirados'),
    'provas': ('Provas', 'Fatos checados'),
    'acusacao': ('Acusação', 'Problemas'),
    'replica': ('Réplica', 'Resposta da defesa'),
    'deliberacao': ('Deliberação', 'Os 7 conversam'),
    'sentenca': ('Sentença', 'Decisão final'),
    'veredito': ('Veredito', 'Resultado'),
    'confianca': ('confiança', 'certeza'),
    'estabilidade': ('Estabilidade por reamostragem', 'Quão firme é o resultado'),
    'reforco': ('reforço', 'mais gente chamada'),
    'fatal': ('FATAL', 'DERRUBA'),
    'grave': ('GRAVE', 'SÉRIO'),
    'leve': ('LEVE', 'PEQUENO'),
    'concede': ('concede', 'aceita e corrige'),
    'rebate': ('rebate', 'responde com prova'),
    'corrigido': ('corrigido', 'já corrigido'),
    'correcao_proposta': ('correção proposta', 'tem conserto, falta fazer'),
    'rebatido': ('rebatido', 'foi respondido'),
    'de_pe': ('de pé', 'ficou sem resposta'),
    'lacuna': ('LACUNA', 'NÃO DEU PARA CHECAR'),
    'condicoes': ('Condições', 'O que precisa ajustar'),
    'ponto_de_virada': ('Ponto de virada', 'O que mudaria o resultado'),
    'proximo_passo': ('Próximo passo barato', 'O que fazer agora'),
    'criterio_de_abandono': ('Critério de abandono', 'Quando desistir'),
    'voto_vencido': ('Voto vencido', 'O juiz discorda'),
    'acata': ('Acata ou recorre?', 'Concorda ou quer outra rodada?'),
    'acatada': ('ACATADA', 'VOCÊ CONCORDOU'),
    'recurso': ('RECURSO', 'OUTRA RODADA'),
    'status_quo': ('Deixar como está', 'Deixar como está'),
}


def modo_valido(modo):
    modo = APELIDOS.get(modo, modo)
    return modo if modo in MODOS else PADRAO


def t(chave, modo=PADRAO):
    par = TERMOS.get(chave)
    if not par:
        return chave
    return par[1] if modo_valido(modo) == 'natural' else par[0]


def opcao(nome, modo=PADRAO):
    """Nome de uma opção de voto para exibir. Opções que não são as padrão (caminhos, propostas) ficam como estão."""
    return t(nome, modo) if nome in TERMOS else nome


def para_sala():
    """O dicionário que a sala recebe embutido."""
    return {k: list(v) for k, v in TERMOS.items()}


# ------------------------------------------------------------------ versões em linguagem natural

def _pct(x):
    return f'{round(100 * x)}%' if x is not None else '-'


def placar_simples(p, opcoes):
    o = lambda n: opcao(n, 'natural')
    cont = lambda c: ' · '.join(f'{o(k)} **{v}**' for k, v in c.items() if k in opcoes)
    l = [f'**Todos os {p["n1"]} jurados, cada um sozinho:** {cont(p["rodada1"])}', '']
    if p['n2']:
        l += [f'**Os {p["n2"]} que decidem:** {cont(p["rodada2"])}', '']
    e1, e2 = p.get('estabilidade1'), p.get('estabilidade2')
    if e1 and e1.get('n'):
        l += [f'**Quão firme é o resultado:** se a gente sorteasse os votos de novo 2.000 vezes, "{o(e1["opcao"])}" '
              f'ganharia em {_pct(e1["estabilidade"])} das vezes entre todos'
              + (f', e "{o(e2["opcao"])}" em {_pct(e2["estabilidade"])} entre os 7' if e2 and e2.get('n') else '')
              + '. Acima de 90% é firme; perto de 50% é apertado.', '']
    if p['mudancas']:
        l += ['**Quem mudou de ideia depois de ouvir os dois lados:**', '']
        l += [f'- {m["nome"]}: de "{o(m["de"])}" para "{o(m["para"])}". {m["motivo"]}' for m in p['mudancas']]
        l.append('')
    return '\n'.join(l)


def ata_simples(autos, placar, ids):
    """A ata para quem não quer jargão: o que foi perguntado, o resultado, os problemas e o que fazer."""
    caso, s = autos['caso'], autos.get('sentenca') or {}
    ops = autos['caso'].get('opcoes') or ['Procedente', 'Procedente com condições', 'Improcedente']
    o = lambda n: opcao(n, 'natural')
    l = ['## A pergunta', '', caso.get('pergunta', ''), '']
    if caso.get('explicacao'):
        l += [caso['explicacao'], '']
    if s:
        l += ['## O resultado', '', f'**{o(s["veredito"])}** · certeza de {s["confianca"]}%', '']
        if s.get('fundamentacao'):
            l += [s['fundamentacao'], '']
    if autos.get('votos'):
        l += ['## Como votaram', '', placar_simples(placar, ops)]
        falas = [v for v in autos['votos'] if v.get('rodada') == 2 and v.get('motivo')]
        if falas:
            l += ['**O que disseram os 7 que decidem:**', '']
            l += [f'- **{ids[v["jurado"]]["nome"]}**, {ids[v["jurado"]]["idade"]} anos: {o(v["voto"])}. "{v["motivo"]}"'
                  for v in falas if v['jurado'] in ids]
            l.append('')
    teses = (autos.get('acusacao') or {}).get('teses', [])
    if teses:
        resp = {r.get('ataque'): r for r in ((autos.get('defesa') or {}).get('respostas') or [])}
        st = {x.get('ataque'): x.get('status') for x in (s.get('ataques') or [])}
        l += ['## Problemas encontrados', '']
        for x in teses:
            g = t((x.get('gravidade') or '').lower(), 'natural') if x.get('gravidade') else ''
            r = resp.get(x.get('id'))
            fim = ''
            if st.get(x.get('id')):
                fim = f' → {t(st[x["id"]], "natural")}'
            elif r:
                fim = f' → a defesa {t(r.get("tipo", ""), "natural")}'
            l.append(f'- {"**" + g + ":** " if g else ""}{x["texto"]}{fim}')
        l.append('')
    if autos.get('plano'):
        from .autos import plano_md
        l.append(plano_md(autos['plano'], natural=True))
    for chave in ('condicoes', 'proximo_passo', 'ponto_de_virada', 'criterio_de_abandono', 'voto_vencido'):
        v = s.get(chave)
        if isinstance(v, list) and v:
            l += [f'## {t(chave, "natural")}', ''] + [f'- {x}' for x in v] + ['']
        elif v:
            l += [f'## {t(chave, "natural")}', '', v, '']
    ps = [p for p in autos.get('provas', []) if p.get('aceita', True)]
    if ps:
        l += ['## O que foi checado', '']
        l += [f'- {"(não deu para checar) " if p.get("tipo") == "lacuna" else ""}{p.get("descricao", "")}' for p in ps]
        l.append('')
    d = autos.get('decisao_usuario') or {}
    if d.get('acatou') is True:
        l += ['## Sua decisão', '', 'Você concordou com o resultado.' + (f' {d["decisao"]}' if d.get('decisao') else ''), '']
    elif d.get('acatou') is False:
        l += ['## Sua decisão', '', 'Você pediu outra rodada.' + (f' Motivo: {d["recurso"]}' if d.get('recurso') else ''), '']
    l += ['_Termos de tribunal: rode a ata com `--linguagem tribunal`._', '']
    return '\n'.join(l)
