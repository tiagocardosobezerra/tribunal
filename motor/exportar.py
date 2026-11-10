"""
Exportação dos autos em PDF: o dossiê do julgamento, para mostrar a outras pessoas como base de discussão.

O documento sai dos autos, nunca de uma paráfrase: capa com o veredito, uma página-resumo, o caso, as provas com
fonte, o contraditório, o júri, as vozes do conselho, a sentença, o plano, como ler o documento e, em anexo, os
25 convocados. A capa traz o SHA-256 do autos.json: quem recebe o PDF pode conferir que ele veio daquele arquivo.

O PDF é impresso por um navegador baseado no Chromium (Edge, Chrome, Chromium), em modo headless. Sem navegador,
fica o HTML pronto para "Imprimir > Salvar como PDF".

    html(autos, sha, natural)            -> o documento em HTML (A4, pronto para impressão)
    exportar(caminho, saida, natural)    -> (arquivo gerado, 'pdf' | 'html')
"""

import datetime
import hashlib
import html as H
import os
import re
import shutil
import subprocess
import tempfile

from . import autos as A
from . import contraditorio as CT
from . import juri as J

TIPO_PROVA = {'medicao': 'medição', 'pesquisa': 'pesquisa', 'documento': 'documento', 'depoimento': 'depoimento',
              'lacuna': 'lacuna', 'teste': 'teste', 'execucao': 'execução', 'codigo': 'código'}
COR_OPCAO = ('#c9a23f', '#4f7fb8', '#8c3a48', '#5c9a64', '#7a5a9a')
GRAVIDADE = {'fatal': ('FATAL', '#7d2433', '#fff'), 'grave': ('GRAVE', '#e9b23a', '#2a1a10'),
             'leve': ('LEVE', '#cfdcec', '#1f3550')}
STATUS = {'corrigido': ('corrigido', '#5c9a64'), 'correcao_proposta': ('correção proposta', '#c9a23f'),
          'rebatido': ('rebatido', '#4f7fb8'), 'de_pe': ('de pé', '#7d2433')}

# A balança em pixel art, 16 x 14: a mesma do banner do Tribunal.
BALANCA = ['.......##.......', '......####......', '.......##.......', '################', '.#.....##.....#.',
           '.#.....##.....#.', '#.#....##....#.#', '#.#....##....#.#', '###....##....###', '.......##.......',
           '.......##.......', '.......##.......', '....########....', '...##########...']
OURO = '#e8c15a'


def e(t):
    """Escapa para HTML e escreve datas ISO (2026-12-08) como 08/12/2026."""
    return re.sub(r'\b(\d{4})-(\d{2})-(\d{2})\b', r'\3/\2/\1', H.escape('' if t is None else str(t)))


def _pixel_svg(tamanho=96):
    """A balança do Tribunal, um retângulo por trecho contínuo de pixels de cada linha."""
    rects = []
    for y, linha in enumerate(BALANCA):
        x = 0
        while x < len(linha):
            if linha[x] == '#':
                ini = x
                while x < len(linha) and linha[x] == '#':
                    x += 1
                rects.append(f'<rect x="{ini}" y="{y}" width="{x - ini}" height="1"/>')
            else:
                x += 1
    alt = round(tamanho * 14 / 16)
    return (f'<svg width="{tamanho}" height="{alt}" viewBox="0 0 16 14" shape-rendering="crispEdges" fill="{OURO}" '
            f'aria-hidden="true">{"".join(rects)}</svg>')


def _anel(valor, tamanho=132):
    v = max(0, min(100, int(valor or 0)))
    r, c = 52, 2 * 3.14159 * 52
    return (f'<svg width="{tamanho}" height="{tamanho}" viewBox="0 0 120 120" class="anel">'
            f'<circle cx="60" cy="60" r="{r}" fill="none" stroke="rgba(232,193,90,.18)" stroke-width="10"/>'
            f'<circle cx="60" cy="60" r="{r}" fill="none" stroke="#e8c15a" stroke-width="10" stroke-linecap="butt" '
            f'stroke-dasharray="{c * v / 100:.1f} {c:.1f}" transform="rotate(-90 60 60)"/>'
            f'<text x="60" y="58" text-anchor="middle" class="anel-n">{v}%</text>'
            f'<text x="60" y="78" text-anchor="middle" class="anel-r">confiança</text></svg>')


def _fonte(f):
    partes = [p.strip() for p in str(f or '').split(';') if p.strip()]
    out = []
    for p in partes:
        if p.startswith('http'):
            out.append(f'<a href="{e(p)}">{e(p.split("://", 1)[1].rstrip("/"))}</a>')
        else:
            out.append(e(p))
    return ' · '.join(out) or '—'


def _barras(cont, ops, total=None):
    total = total or sum(cont.values()) or 1
    l = []
    for i, o in enumerate(ops):
        n = cont.get(o, 0)
        l.append(f'<div class="barra"><span class="rot">{e(o)}</span><span class="trilho">'
                 f'<span class="cheio" style="width:{100 * n / total:.1f}%;background:{COR_OPCAO[i % len(COR_OPCAO)]}">'
                 f'</span></span><span class="num">{n}</span></div>')
    return '<div class="barras">' + ''.join(l) + '</div>'


def _selo(g):
    rot, fundo, cor = GRAVIDADE.get(g or '', ('—', '#ddd', '#333'))
    return f'<span class="selo" style="background:{fundo};color:{cor}">{rot}</span>'


def _status(s):
    rot, cor = STATUS.get(s or '', ('—', '#888'))
    return f'<span class="status" style="border-color:{cor};color:{cor}">{e(rot)}</span>'


def _lista(xs, ordenada=False):
    xs = [x for x in (xs or []) if str(x).strip()]
    if not xs:
        return ''
    t = 'ol' if ordenada else 'ul'
    return f'<{t}>' + ''.join(f'<li>{e(x)}</li>' for x in xs) + f'</{t}>'


def html(autos, sha='', natural=False, versao=''):
    caso = autos['caso']
    j = autos.get('juri') or {}
    ids = J.por_id(J.carregar_foro(j.get('foro') or 'brasil'))
    ops = A.opcoes(autos)
    s = autos.get('sentenca') or {}
    p = autos.get('plano') or {}
    pl = A.placar(autos) if autos.get('votos') else None
    st = CT.status_dos_ataques(autos) if autos.get('acusacao') else {}
    resp = {r.get('ataque'): r for r in (autos.get('defesa') or {}).get('respostas', [])}
    nota = {x.get('ataque'): x.get('nota') for x in s.get('ataques', [])}
    teses = (autos.get('acusacao') or {}).get('teses', [])
    r1 = {v['jurado']: v for v in autos.get('votos', []) if v.get('rodada') == 1}
    r2 = [v for v in autos.get('votos', []) if v.get('rodada') == 2]
    d = autos.get('decisao_usuario') or {}
    hoje = datetime.date.today().strftime('%d/%m/%Y')
    T = (lambda trib, nat: nat if natural else trib)

    # ---------------------------------------------------------------- capa
    capa = f'''
<section class="capa">
  <div class="moldura">
    <div class="topo"><span>AUTOS DO TRIBUNAL</span><span>{e(j.get("sessao", ""))}</span></div>
    <div class="malhete">{_pixel_svg(112)}</div>
    <h1>{e(caso.get("titulo"))}</h1>
    <p class="pergunta">{e(caso.get("pergunta"))}</p>
    <div class="veredito-capa">
      {_anel(s.get("confianca")) if s else ""}
      <div>
        <div class="rotulo">{T("Veredito", "Decisão")}</div>
        <div class="veredito">{e(s.get("veredito") or "sem sentença")}</div>
        {f'<div class="decisao">{"Acatado" if d.get("acatou") else "Recorrido"} pelo dono da decisão</div>' if d.get("acatou") is not None else ""}
      </div>
    </div>
    <dl class="ficha">
      <div><dt>Júri</dt><dd>{len(j.get("convocados", []))} convocados · {len(j.get("conselho", []))} no conselho</dd></div>
      <div><dt>Provas</dt><dd>{len([x for x in autos.get("provas", []) if x.get("tipo") != "lacuna"])} com fonte · {len([x for x in autos.get("provas", []) if x.get("tipo") == "lacuna"])} lacuna(s)</dd></div>
      <div><dt>Ataques</dt><dd>{len(teses)} · {sum(1 for x in st.values() if x == "de_pe")} de pé</dd></div>
      <div><dt>Rito</dt><dd>{e(autos.get("rito", 1))}{" · juiz independente" if s.get("por") == "juiz independente" else ""}</dd></div>
    </dl>
    <div class="rodape-capa">
      <div>Gerado em {hoje}{f" · Tribunal {e(versao)}" if versao else ""}</div>
      <div class="hash">SHA-256 do autos.json: {e(sha) or "—"}</div>
    </div>
  </div>
</section>'''

    # ---------------------------------------------------------------- resumo
    falas = sorted(r2, key=lambda v: -len(str(v.get('motivo', ''))))[:3]
    de_pe = [t for t in teses if st.get(t.get('id')) == 'de_pe']
    resumo = f'''
<section class="pagina">
  <h2><span class="num">●</span>{T("Em uma página", "O resumo")}</h2>
  <div class="caixa-veredito">
    <div class="cv-esq"><div class="rotulo">{T("Veredito", "Decisão")}</div><div class="cv-v">{e(s.get("veredito") or "—")}</div>
      <div class="confbar"><span style="width:{int(s.get("confianca") or 0)}%"></span></div>
      <div class="pequeno">Confiança de {e(s.get("confianca", "—"))}%. {e((p.get("certeza") or {}).get("por_que", ""))}</div></div>
  </div>
  {f'<p class="recomendacao">{e(p.get("recomendacao"))}</p>' if p.get("recomendacao") else ""}
  <div class="duas">
    <div><h3>{T("Voto secreto dos convocados", "Como os 25 votaram")}</h3>{_barras(pl["rodada1"], ops) if pl else ""}
         <h3>{T("Conselho de Sentença", "Como os 7 decidiram")}</h3>{_barras(pl["rodada2"], ops) if pl else ""}</div>
    <div><h3>{T("Ponto de virada", "O que mudaria a decisão")}</h3><p>{e(s.get("ponto_de_virada") or "—")}</p>
         <h3>{T("Próximo passo", "Comece por aqui")}</h3><p>{e((p.get("passo_mais_barato") or {}).get("o_que") or s.get("proximo_passo") or "—")}</p>
         <h3>{T("Critério de abandono", "Quando desistir")}</h3><p>{e(p.get("criterio_de_abandono") or s.get("criterio_de_abandono") or "—")}</p></div>
  </div>
  {"<h3>" + T("Ataques que ficaram de pé", "Problemas sem resposta") + "</h3><ul class='compacta'>" + "".join(f"<li>{_selo(t.get('gravidade'))} <b>{e(t.get('id'))}</b> {e(t.get('texto'))}</li>" for t in de_pe) + "</ul>" if de_pe else ""}
  {"<h3>" + T("Vozes que mais pesaram", "O que as pessoas disseram") + "</h3>" + "".join(f"<blockquote>“{e(v.get('motivo'))}”<cite>{e(ids[v['jurado']]['nome'])}, {ids[v['jurado']]['idade']} anos, {e(ids[v['jurado']].get('cidade', ''))} · votou {e(v.get('voto'))}</cite></blockquote>" for v in falas if v['jurado'] in ids) if falas else ""}
</section>'''

    # ---------------------------------------------------------------- 1. caso e provas
    provas = ''.join(f'''<div class="prova{' lacuna' if x.get('tipo') == 'lacuna' else ''}"><div class="p-id">{e(x.get("id"))}</div>
      <div><div class="p-tipo">{e(TIPO_PROVA.get(x.get("tipo"), x.get("tipo")))}</div><div>{e(x.get("descricao"))}</div><div class="p-fonte">Fonte: {_fonte(x.get("fonte"))}</div></div></div>'''
                     for x in autos.get('provas', []) if x.get('aceita', True))
    caso_html = f'''
<section class="pagina">
  <h2><span class="num">1</span>{T("O caso", "A pergunta")}</h2>
  <p class="destaque">{e(caso.get("pergunta"))}</p>
  <p>{e(caso.get("explicacao") or caso.get("descricao") or "")}</p>
  <p class="pequeno"><b>{T("Opções de voto", "Os caminhos em jogo")}:</b> {" · ".join(e(o) for o in ops)}</p>
  <h2><span class="num">2</span>{T("Provas", "Os fatos levantados")}</h2>
  <p class="pequeno">{T("Toda afirmação que pesa é uma prova com fonte. O que não pôde ser verificado aparece como lacuna.", "Cada fato tem de onde veio. O que não deu para conferir aparece como lacuna.")}</p>
  {provas}
</section>'''

    # ---------------------------------------------------------------- 3. contraditório
    linhas = []
    for t in teses:
        r = resp.get(t.get('id')) or {}
        ch = t.get('checagem') or {}
        lado = 'juiz' if t.get('do_juiz') else 'acusação'
        linhas.append(f'''<tr><td class="c-id">{e(t.get("id"))}<div class="pequeno">{lado}</div></td><td>{_selo(t.get("gravidade"))}</td>
          <td>{e(t.get("texto"))}{f'<div class="pequeno">Contraexemplo: {e(t["contraexemplo"])}</div>' if t.get("contraexemplo") else ""}</td>
          <td>{f'<b>{e(r.get("tipo"))}</b>: {e(r.get("texto"))}' if r else ('<span class="pequeno">apontada pelo juiz na sentença</span>' if t.get("do_juiz") else '<span class="pequeno">sem resposta</span>')}
              {f'<div class="pequeno"><b>Checagem independente:</b> {e(ch.get("veredito"))}. {e(ch.get("motivo"))}</div>' if ch.get("veredito") else ""}
              {f'<div class="nota-juiz"><b>Juiz:</b> {e(nota.get(t.get("id")))}</div>' if nota.get(t.get("id")) and not t.get("do_juiz") else ""}</td>
          <td>{_status(st.get(t.get("id")))}</td></tr>''')
    contra = f'''
<section class="pagina">
  <h2><span class="num">3</span>{T("Contraditório", "Os ataques e as respostas")}</h2>
  <p class="pequeno">{T("A acusação ataca com gravidade (FATAL, GRAVE, LEVE) e contraexemplo; a defesa concede ou rebate; todo FATAL passa por uma checagem independente; o juiz dá o status final. Um FATAL de pé impede o veredito pleno.", "Um lado aponta os problemas, do mais grave ao mais leve; o outro admite ou responde com fatos. Os problemas graves são conferidos por alguém de fora. No fim, o juiz diz o que ficou resolvido.")}</p>
  <table class="contra"><thead><tr><th>Id</th><th>Gravidade</th><th>Ataque</th><th>Resposta</th><th>Status</th></tr></thead><tbody>{"".join(linhas)}</tbody></table>
</section>''' if teses else ''

    # ---------------------------------------------------------------- 4. júri
    seg_html = ''
    if pl:
        for campo, rot in (('faixa_etaria', 'Idade'), ('regiao', 'Região'), ('renda', 'Renda'), ('escolaridade', 'Escolaridade')):
            ls = pl['segmentos'].get(campo) or []
            seg_html += f'<div class="seg"><h4>{rot}</h4>'
            for x in ls:
                tot = sum(x['contagem'].values()) or 1
                partes = ''.join(
                    f'<span style="width:{100 * x["contagem"].get(o, 0) / tot:.1f}%;background:{COR_OPCAO[i % len(COR_OPCAO)]}">'
                    f'{x["contagem"].get(o, 0) or ""}</span>' for i, o in enumerate(ops) if x['contagem'].get(o, 0))
                seg_html += (f'<div class="seg-l{" diverge" if x["diverge"] else ""}"><span class="seg-c">{e(x["categoria"])} '
                             f'<span class="pequeno">({x["n"]})</span></span><span class="pilha">{partes}</span></div>')
            seg_html += '</div>'
        legenda = ''.join(f'<span class="leg"><i style="background:{COR_OPCAO[i % len(COR_OPCAO)]}"></i>{e(o)}</span>'
                          for i, o in enumerate(ops))
        seg_html = f'<div class="legenda">{legenda}</div><div class="segs">{seg_html}</div>'
    modelos = ''
    if pl and pl.get('por_modelo1'):
        modelos = ' · '.join(f'{e(m)}: {e(dm.get("maioria"))} ({dm.get("n")})' for m, dm in pl['por_modelo1'].items())
        modelos = f'<p class="pequeno"><b>Por modelo do júri:</b> {modelos}. {"Os modelos concordam." if pl.get("modelos_concordam1") else "Os modelos discordam."}</p>'
    est = ''
    if pl:
        e1 = (pl.get('estabilidade1') or {}).get('estabilidade')
        e2 = (pl.get('estabilidade2') or {}).get('estabilidade')
        est = (f'<p class="pequeno"><b>Firmeza:</b> a maioria dos convocados se mantém em {round(100 * (e1 or 0))}% das reamostragens; '
               f'a do conselho, em {round(100 * (e2 or 0))}%.</p>')
    juri = f'''
<section class="pagina">
  <h2><span class="num">4</span>{T("O júri", "Quem julgou")}</h2>
  <p class="pequeno">{T("Jurados fictícios, sorteados por rodízio de um elenco de 100 calibrado pelo IBGE (Censo 2022 e PNAD 2025). Votam em segredo antes do debate; 7 formam o Conselho de Sentença e votam de novo depois.", "Pessoas fictícias que representam o Brasil, sorteadas de um grupo de 100 montado com dados do IBGE. Votaram sozinhas antes da discussão; 7 delas decidiram depois de ouvir os dois lados.")}</p>
  <div class="duas"><div><h3>{T("Voto secreto", "Primeiro voto")} ({pl["n1"] if pl else 0})</h3>{_barras(pl["rodada1"], ops) if pl else ""}</div>
  <div><h3>{T("Conselho", "Decisão final")} ({pl["n2"] if pl else 0})</h3>{_barras(pl["rodada2"], ops) if pl else ""}</div></div>
  {est}{modelos}
  <h3>{T("Por segmento", "Por grupo")}</h3><p class="pequeno">Em vermelho: o grupo divergiu da maioria geral.</p>
  {seg_html}
</section>'''

    vozes = ''.join(f'''<div class="voz"><div class="v-quem"><b>{e(ids[v["jurado"]]["nome"])}</b>, {ids[v["jurado"]]["idade"]} anos<br>
      <span class="pequeno">{e(ids[v["jurado"]].get("ocupacao", ""))} · {e(ids[v["jurado"]].get("cidade", ""))}</span></div>
      <div class="v-txt"><span class="v-voto">{e(v.get("voto"))}</span>{e(v.get("motivo"))}</div></div>''' for v in r2 if v['jurado'] in ids)
    vozes_html = f'''
<section class="pagina">
  <h2><span class="num">5</span>{T("Vozes do conselho", "O que os 7 disseram")}</h2>
  {vozes}
  {"".join(f'<p class="pequeno"><b>Mudou de voto:</b> {e(m["nome"])}, de {e(m["de"])} para {e(m["para"])}. {e(m["motivo"])}</p>' for m in (pl or {}).get("mudancas", []))}
</section>''' if r2 else ''

    # ---------------------------------------------------------------- 6. sentença e 7. plano
    sent = f'''
<section class="pagina">
  <h2><span class="num">6</span>{T("Sentença", "A decisão")}</h2>
  <div class="caixa-veredito"><div class="cv-esq"><div class="rotulo">{T("Veredito", "Decisão")}</div><div class="cv-v">{e(s.get("veredito"))}</div>
    <div class="pequeno">Confiança {e(s.get("confianca"))}%{" · sentença do juiz independente" if s.get("por") == "juiz independente" else ""}</div></div></div>
  {f'<h3>Fundamentação</h3><p>{e(s.get("fundamentacao"))}</p>' if s.get("fundamentacao") else ""}
  {f'<h3>De onde vem a confiança</h3><p class="pequeno">{e(s.get("ajuste_da_confianca"))}</p>' if s.get("ajuste_da_confianca") else ""}
  {f'<h3>{T("Condições", "O que precisa ser verdade")}</h3>' + _lista(s.get("condicoes"), True) if s.get("condicoes") else ""}
  {f'<h3>{T("Voto vencido", "Opinião contrária do juiz")}</h3><p>{e(s.get("voto_vencido"))}</p>' if s.get("voto_vencido") else ""}
</section>''' if s else ''

    plano = ''
    if p:
        metas = ''.join(f'<tr><td>{e(m.get("o_que"))}</td><td>{e(m.get("grupo", "todos"))}</td><td>{e(m.get("como_medir"))}</td>'
                        f'<td><b>{e(m.get("meta"))}</b></td><td>{e(m.get("prazo"))}</td></tr>' for m in p.get('metas') or [])
        testes = ''.join(f'<tr><td>{e(t.get("o_que"))}</td><td>{e(t.get("entrada"))}</td><td>{e(t.get("esperado"))}</td></tr>' for t in p.get('testes') or [])
        cen = ''.join(f'<tr><td>{e(c.get("se"))}</td><td>{e(c.get("entao"))}</td><td>{e(c.get("certeza"))}</td></tr>' for c in p.get('cenarios') or [])
        passos = ''.join(f'<li>{e(str(x).split(". ", 1)[1] if str(x)[:3].rstrip(". ").isdigit() and ". " in str(x) else x)}</li>' for x in p.get('ordem') or [])
        plano = f'''
<section class="pagina">
  <h2><span class="num">7</span>{T("Plano de ação", "O plano, passo a passo")}</h2>
  {f'<p class="recomendacao">{e(p.get("recomendacao"))}</p>' if p.get("recomendacao") else ""}
  <ol class="passos">{passos}</ol>
  {f'<h3>Metas</h3><table><thead><tr><th>O que medir</th><th>Grupo</th><th>Como medir</th><th>Número que decide</th><th>Prazo</th></tr></thead><tbody>{metas}</tbody></table>' if metas else ""}
  {f'<h3>Testes</h3><table><thead><tr><th>Teste</th><th>Entrada</th><th>Esperado</th></tr></thead><tbody>{testes}</tbody></table>' if testes else ""}
  {f'<h3>{T("Cenários", "Se acontecer...")}</h3><table><thead><tr><th>Se</th><th>Então</th><th>Certeza</th></tr></thead><tbody>{cen}</tbody></table>' if cen else ""}
  <div class="abandono"><b>{T("Critério de abandono", "Quando desistir")}:</b> {e(p.get("criterio_de_abandono"))}</div>
  {f'<h3>Hipóteses a confirmar</h3>' + _lista(p.get("hipoteses")) if p.get("hipoteses") else ""}
  {f'<h3>Atenção</h3>' + _lista(p.get("atencao")) if p.get("atencao") else ""}
</section>'''

    # ---------------------------------------------------------------- como ler e anexo
    ler = f'''
<section class="pagina">
  <h2><span class="num">8</span>Como ler este documento</h2>
  <div class="aviso">
    <p><b>Este documento é uma base de discussão, não uma previsão.</b> Os jurados são simulações feitas por modelos de
    linguagem a partir de perfis calibrados pelo IBGE: mostram como diferentes grupos de pessoas tendem a reagir, não
    garantem como o mercado vai responder. Num teste cego com 30 produtos de desfecho conhecido, o júri acertou 18, perto
    do acaso.</p>
    <p><b>O que dá peso ao documento é o processo:</b> provas com fonte, ataques com contraexemplo e checagem
    independente, uma sentença escrita por um juiz que não fez a perícia e um plano com metas e critério de abandono, que
    testa a ideia no mundo real antes de grandes apostas.</p>
    <p><b>Integridade:</b> o código abaixo é o SHA-256 do arquivo de autos que gerou este PDF. Se alguém alterar o
    arquivo, o código muda.</p>
    <p class="hash">{e(sha)}</p>
  </div>
</section>'''
    anexo_l = ''.join(f'<tr><td>{e(i)}</td><td>{e(ids[i]["nome"])}</td><td>{ids[i]["idade"]}</td><td>{e(ids[i].get("uf", ""))}</td>'
                      f'<td>{e(ids[i].get("escolaridade", ""))}</td><td>{e(ids[i].get("renda", ""))}</td>'
                      f'<td>{e((r1.get(i) or {}).get("voto", "—"))}</td><td class="pequeno">{e((r1.get(i) or {}).get("modelo", ""))}</td>'
                      f'<td>{"●" if i in (j.get("conselho") or []) else ""}</td></tr>' for i in j.get('convocados', []) if i in ids)
    anexo = f'''
<section class="pagina">
  <h2><span class="num">A</span>Anexo: os convocados</h2>
  <table class="anexo"><thead><tr><th>Id</th><th>Nome</th><th>Idade</th><th>UF</th><th>Escolaridade</th><th>Renda</th><th>Voto secreto</th><th>Modelo</th><th>Conselho</th></tr></thead>
  <tbody>{anexo_l}</tbody></table>
</section>''' if anexo_l else ''

    return f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>{e(caso.get("titulo"))} · Autos do Tribunal</title>
<style>{CSS.replace("__TITULO__", e(caso.get("titulo")).replace('"', "'"))}</style></head>
<body>{capa}{resumo}{caso_html}{contra}{juri}{vozes_html}{sent}{plano}{ler}{anexo}</body></html>'''


CSS = '''
@page { size: A4; margin: 18mm 16mm 20mm 16mm;
  @bottom-left { content: "__TITULO__ · Autos do Tribunal"; font: 8pt "Segoe UI", Arial, sans-serif; color: #8a7a68; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt "Segoe UI", Arial, sans-serif; color: #8a7a68; } }
@page capa { margin: 0; @bottom-left { content: none } @bottom-right { content: none } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font-variant-numeric: lining-nums tabular-nums; font: 10.4pt/1.5 Cambria, "Charter", "Source Serif Pro", Georgia, serif; color: #2a2118; background: #fff; }
a { color: #4f5f8a; text-decoration: none; }
h1, h2, h3, h4, .rotulo, .topo, th, .selo, .status, .p-tipo, .num, .v-voto { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; }
.capa { page: capa; height: 297mm; background: #1a1220; color: #efe7d4; padding: 14mm; break-after: page; }
.moldura { height: 100%; border: 3px solid #e8c15a; outline: 3px solid #5d3d2b; outline-offset: 4px; padding: 14mm 14mm 10mm;
  display: flex; flex-direction: column; background:
  repeating-linear-gradient(0deg, rgba(255,255,255,.015) 0 2px, transparent 2px 4px); }
.topo { display: flex; justify-content: space-between; letter-spacing: .3em; font-size: 8pt; color: #e8c15a; }
.malhete { margin: 16mm 0 9mm; }
.capa h1 { font-size: 30pt; line-height: 1.12; margin: 0 0 4mm; color: #fff; font-weight: 700; }
.pergunta { font-size: 13pt; color: #d9ccb3; font-style: italic; margin: 0 0 14mm; }
.veredito-capa { display: flex; gap: 9mm; align-items: center; padding: 7mm; border: 1px solid rgba(232,193,90,.45);
  background: rgba(232,193,90,.06); }
.anel-n { font: 700 24px "Segoe UI", Arial, sans-serif; fill: #fff; }
.anel-r { font: 9px "Segoe UI", Arial, sans-serif; fill: #e8c15a; letter-spacing: .12em; text-transform: uppercase; }
.rotulo { text-transform: uppercase; letter-spacing: .18em; font-size: 7.5pt; color: #b08a2a; }
.capa .rotulo { color: #e8c15a; }
.veredito { font: 700 20pt "Segoe UI", Arial, sans-serif; color: #fff; margin-top: 1mm; }
.decisao { margin-top: 2mm; color: #9fd2a6; font: 9pt "Segoe UI", Arial, sans-serif; }
.ficha { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm 10mm; margin: 12mm 0 0; }
.ficha dt { font: 7.5pt "Segoe UI", Arial, sans-serif; text-transform: uppercase; letter-spacing: .15em; color: #e8c15a; }
.ficha dd { margin: 0; font-size: 11pt; }
.rodape-capa { margin-top: auto; font: 8pt "Segoe UI", Arial, sans-serif; color: #a89a80; }
.hash { font: 7.5pt Consolas, "Courier New", monospace; word-break: break-all; color: #8a7a68; }
.capa .hash { color: #a89a80; margin-top: 1mm; }
.pagina { break-before: page; }
h2 { font-size: 17pt; color: #3f281c; border-bottom: 2px solid #e8c15a; padding-bottom: 2mm; margin: 0 0 4mm; }
h2 .num { display: inline-block; min-width: 9mm; height: 9mm; line-height: 9mm; text-align: center; margin-right: 3mm;
  background: #3f281c; color: #e8c15a; font-size: 11pt; vertical-align: 2px; }
section .pagina h2:not(:first-child), .pagina h2 + * + h2 { margin-top: 8mm; }
h3 { font-size: 10.5pt; color: #5d3d2b; margin: 5mm 0 1.5mm; text-transform: uppercase; letter-spacing: .06em; }
h4 { font-size: 9pt; margin: 3mm 0 1mm; color: #5d3d2b; }
p { margin: 0 0 2.5mm; }
.pequeno { font-size: 8.4pt; color: #6b5d4c; }
.destaque { font-size: 13pt; font-style: italic; color: #3f281c; border-left: 4px solid #e8c15a; padding-left: 4mm; }
.caixa-veredito { background: #1a1220; color: #efe7d4; padding: 6mm 7mm; border-left: 6px solid #e8c15a; margin-bottom: 4mm; break-inside: avoid; }
.caixa-veredito .pequeno { color: #c9bca3; }
.cv-v { font: 700 17pt "Segoe UI", Arial, sans-serif; color: #fff; margin: 1mm 0 3mm; }
.confbar { height: 3mm; background: rgba(232,193,90,.2); margin-bottom: 2mm; }
.confbar span { display: block; height: 100%; background: #e8c15a; }
.recomendacao { font-size: 11pt; background: #f6f1e4; border: 1px solid #e3d6b8; padding: 4mm 5mm; }
.duas { display: grid; grid-template-columns: 1fr 1fr; gap: 8mm; }
.barras { margin: 1mm 0 3mm; }
.barra { display: grid; grid-template-columns: 40% 1fr 7mm; gap: 2mm; align-items: center; font: 8.6pt "Segoe UI", Arial, sans-serif; margin: 1.2mm 0; }
.trilho { height: 3.6mm; background: #efe9dc; display: block; }
.cheio { display: block; height: 100%; }
.num { text-align: right; font-weight: 700; }
.barra .num { text-align: right; }
ul.compacta { padding-left: 4mm; } ul.compacta li { margin-bottom: 1.5mm; }
blockquote { margin: 2mm 0 3mm; padding: 2mm 4mm; border-left: 3px solid #c9a23f; background: #faf7f0; font-style: italic; break-inside: avoid; }
blockquote cite { display: block; font: normal 8pt "Segoe UI", Arial, sans-serif; color: #6b5d4c; margin-top: 1mm; }
.prova { display: grid; grid-template-columns: 11mm 1fr; gap: 3mm; padding: 2.5mm 0; border-bottom: 1px solid #ece4d3; break-inside: avoid; }
.prova.lacuna { background: #fbf3f3; }
.p-id { font: 700 10pt "Segoe UI", Arial, sans-serif; color: #fff; background: #5d3d2b; text-align: center; height: 6mm; line-height: 6mm; }
.prova.lacuna .p-id { background: #7d2433; }
.p-tipo { font-size: 7pt; text-transform: uppercase; letter-spacing: .14em; color: #b08a2a; }
.p-fonte { font-size: 8pt; color: #6b5d4c; margin-top: .8mm; word-break: break-word; }
table { width: 100%; border-collapse: collapse; font-size: 8.6pt; margin: 1mm 0 3mm; }
th { text-align: left; font-size: 7.5pt; text-transform: uppercase; letter-spacing: .08em; color: #5d3d2b; border-bottom: 2px solid #3f281c; padding: 1.5mm 2mm; }
td:last-child { white-space: normal; }
td { border-bottom: 1px solid #ece4d3; padding: 1.8mm 2mm; vertical-align: top; }
tr { break-inside: avoid; }
.contra td:nth-child(3) { width: 38%; } .contra td:nth-child(4) { width: 42%; }
.nota-juiz { font-size: 8.2pt; color: #3f281c; background: #f6f1e4; padding: 1.2mm 2mm; margin-top: 1.5mm; border-left: 2px solid #c9a23f; }
.c-id { font: 700 9pt "Segoe UI", Arial, sans-serif; white-space: nowrap; }
.selo { display: inline-block; font-size: 6.8pt; font-weight: 700; letter-spacing: .08em; padding: .6mm 1.6mm; }
.status { display: inline-block; font-size: 7.4pt; font-weight: 600; border: 1px solid; padding: .4mm 1.6mm; white-space: nowrap; }
.legenda { display: flex; flex-wrap: wrap; gap: 2mm 6mm; font: 8pt "Segoe UI", Arial, sans-serif; margin: 1mm 0 3mm; }
.leg i { display: inline-block; width: 3mm; height: 3mm; margin-right: 1.5mm; vertical-align: -.4mm; }
.segs { display: grid; grid-template-columns: 1fr 1fr; gap: 2mm 8mm; }
.seg { break-inside: avoid; }
.seg-l { display: grid; grid-template-columns: 38% 1fr; gap: 2mm; align-items: center; font: 8pt "Segoe UI", Arial, sans-serif; margin: 1mm 0; }
.seg-l.diverge .seg-c { font-weight: 700; color: #7d2433; }
.pilha { display: flex; height: 4.2mm; background: #efe9dc; }
.pilha span { display: block; color: #fff; font: 700 7pt "Segoe UI", Arial, sans-serif; text-align: center; line-height: 4.2mm; overflow: hidden; }
.voz { display: grid; grid-template-columns: 42mm 1fr; gap: 4mm; padding: 3mm 0; border-bottom: 1px solid #ece4d3; break-inside: avoid; }
.v-voto { display: block; font-size: 7.6pt; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: #b08a2a; margin-bottom: .8mm; }
.passos { padding-left: 6mm; } .passos li { margin-bottom: 2mm; }
.abandono { border: 2px solid #7d2433; background: #fbf3f3; padding: 3mm 4mm; margin: 4mm 0; break-inside: avoid; }
.aviso { background: #f6f1e4; border: 1px solid #e3d6b8; padding: 5mm 6mm; }
.anexo { font-size: 7.8pt; } .anexo td { padding: 1.1mm 1.5mm; } .anexo td:first-child { white-space: nowrap; }
'''


def navegador():
    """O navegador que imprime o PDF: TRIBUNAL_NAVEGADOR, Edge, Chrome ou Chromium."""
    cands = [os.environ.get('TRIBUNAL_NAVEGADOR', '')]
    pf = [os.environ.get(k, '') for k in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA')]
    for base in pf:
        if base:
            cands += [os.path.join(base, 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
                      os.path.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe')]
    cands += ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
              '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
    cands += [shutil.which(n) or '' for n in ('microsoft-edge', 'google-chrome', 'chromium', 'chromium-browser', 'chrome')]
    return next((c for c in cands if c and os.path.exists(c)), None)


def exportar(caminho, saida=None, natural=False, versao=''):
    arq = os.path.join(caminho, 'autos.json') if os.path.isdir(caminho) else caminho
    with open(A.longo(arq), 'rb') as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    autos = A.carregar(arq)
    doc = html(autos, sha, natural, versao)
    saida = saida or os.path.join(os.path.dirname(os.path.abspath(arq)), 'autos.pdf')
    pasta_tmp = tempfile.mkdtemp(prefix='tribunal-pdf-')
    arq_html = os.path.join(pasta_tmp, 'autos.html')
    with open(arq_html, 'w', encoding='utf-8') as f:
        f.write(doc)
    nav = navegador()
    if not saida.lower().endswith('.pdf') or not nav:
        destino = saida if saida.lower().endswith('.html') else os.path.splitext(saida)[0] + '.html'
        shutil.copy(arq_html, destino)
        shutil.rmtree(pasta_tmp, ignore_errors=True)
        return destino, 'html'
    url = 'file:///' + arq_html.replace('\\', '/').lstrip('/')
    cmd = [nav, '--headless=new', '--disable-gpu', '--no-first-run', '--no-pdf-header-footer',
           f'--user-data-dir={os.path.join(pasta_tmp, "perfil")}', f'--print-to-pdf={os.path.abspath(saida)}', url]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    finally:
        shutil.rmtree(pasta_tmp, ignore_errors=True)
    if not os.path.exists(saida):
        raise RuntimeError(f'o navegador não gerou o PDF ({nav})')
    return saida, 'pdf'
