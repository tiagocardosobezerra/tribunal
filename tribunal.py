#!/usr/bin/env python3
"""
Tribunal: leve qualquer coisa a julgamento (ideia, app, código, decisão, documento).

Comandos:
    status      o que há nesta cópia: foros, rodízio do júri, Memory Card
    juri        convocar (25 do rodízio), conselho (recusas + 7), ficha, listar, cotas, especial
    validar     confere os autos do caso
    placar      placar das rodadas, por segmento, e quem mudou de voto
    ata         gera a ata em Markdown a partir dos autos
    briefing    o prompt exato de um lote de jurados (gerado dos autos; ordem das opções embaralhada)
    juntar      junta nos autos os votos que os subagentes gravaram em votos/
    proximo     a próxima fase do rito e o comando exato (retomar depois de compactação)
    plano       quantos subagentes e tokens o caso vai usar; --reversivel e --impacto sugerem o modo
    pendencias  casos sem desfecho no Memory Card (pergunte por eles: é o que calibra a confiança)
    propostas   concurso de propostas: cartas (sem repetir) e placar pela rubrica
    abrir       abre a sala do caso no navegador (sem argumento: o último caso; nada para digitar)
    novo        cria a pasta e os autos de um caso novo (na pasta fixa, se o usuário escolheu)
    pasta       onde os casos ficam: --fixa (~/tribunal-autos) ou --sessao
    validacao   mede o júri contra casos de desfecho conhecido (acerto, Brier, vazamento)
    onda        a fase atual em um comando: briefings, chamadas de subagente e --juntar
    exportar    o dossiê do julgamento em PDF (capa, resumo, provas, contraditório, júri, sentença, plano)
    externo     um lote de jurados num modelo de fora da família Claude (opcional; envia o briefing ao provedor)
    perito-feito  o perito resolveu as pendências do plano: apaga o plano e conta a rodada (teto de 2)
    entrega     o que se mostra ao usuário no fim: decisão, plano, problemas (montado dos autos)
    linguagem   termos de tribunal ou linguagem natural (vale para ata, placar e sala; os autos não mudam)
    fase        fim de fase: carimbo de hora, sala ao vivo e uma linha de narração para a conversa
    debate      o prompt exato de promotor, defesa, réplica, autor ou contraditório (para os agentes enxutos)
    juntar-debate  junta nos autos o que os agentes de debate gravaram
    reforco     caso apertado (sala estável em menos de 80%): mais 25 jurados na rodada 1
    parar       parada antecipada da rodada 1 (liderança estável por reamostragem: dispensa os lotes restantes)
    comparar    compara dois julgamentos do mesmo caso: veredito, confiança e segmentos
    visualizar  a sala do tribunal em pixel art, animada a partir dos autos (com o som do malhete)
    cartao      Memory Card: procura, salva, versiona, registra desfecho e mede a calibração

Exemplos:
    python tribunal.py juri convocar --caso "App de delivery" --tipo app
    python tribunal.py juri conselho brasil-0001 --acusacao BR-012,BR-040 --defesa BR-077
    python tribunal.py juri ficha BR-012 BR-033
    python tribunal.py placar autos.json
    python tribunal.py ata autos.json -o ata.md
    python tribunal.py cartao buscar delivery app
    python tribunal.py cartao enviar autos.json [--motivo M] [--confirmar]
    python tribunal.py cartao desfecho tribunal/apps/geral/app-de-delivery --resultado acertou --nota "..."

Guia: SKILL.md. Sem dependências: só Python 3.8+.
"""

import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from motor import autos as A          # noqa: E402
from motor import casos as CS         # noqa: E402
from motor import debate as DB        # noqa: E402
from motor import juri as J           # noqa: E402
from motor import linguagem as LG     # noqa: E402
from motor import memory_card as MC   # noqa: E402
from motor import orquestra as O      # noqa: E402
from motor import propostas as PR     # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

VERSAO = '1.8.1'


def _lista(x):
    return [i.strip() for i in (x or '').split(',') if i.strip()]


# ------------------------------------------------------------------ status

def cmd_status(a):
    print(f'Tribunal {VERSAO}')
    for f in J.foros():
        d = J.carregar_foro(f)
        st = J.ler_estado().get(f) or {}
        sess = st.get('sessoes', [])
        print(f'Foro {f}: {d.get("nome", f)} · {len(d["jurados"])} alistados · {len(sess)} sessões · '
              f'{len(st.get("saco", []))} ainda no saco do rodízio')
    if MC.configurado():
        ok, motivo = MC.disponivel()
        if ok:
            meus = [x for x in MC.ler_catalogo(MC.config()['pasta']) if x['solucao'] == MC.SOLUCAO]
            com = [x for x in meus if x.get('desfecho')]
            print(f'Memory Card: {MC.config()["repo"] or "local"} · {len(meus)} casos · {len(com)} com desfecho')
        else:
            print(f'Memory Card: configurado, mas NÃO funciona aqui ({motivo})')
    else:
        print('Memory Card: não configurado (python tribunal.py cartao iniciar --repo SEU_USUARIO/memory-card)')


# ------------------------------------------------------------------ júri

def _ja_julgaram(caminho):
    """Convocados, reforço e conselho de um caso: quem já julgou não volta no recurso."""
    j = A.carregar(caminho).get('juri') or {}
    return set(j.get('convocados') or []) | set(j.get('reforco') or []) | set(j.get('conselho') or [])


def _origem(autos_arq, autos):
    r = (autos.get('caso') or {}).get('recurso_de')
    if not r:
        return None
    base = os.path.dirname(os.path.dirname(os.path.abspath(_arq_autos(autos_arq))))
    for c in (r, os.path.join(base, r)):
        if os.path.exists(_arq_autos(c)):
            return c
    return None


def _arq_autos(c):
    return os.path.join(c, 'autos.json') if os.path.isdir(c) else c


def cmd_juri(a):
    dados = J.carregar_foro(a.foro)
    if a.acao == 'convocar':
        autos = A.carregar(a.autos) if a.autos else None
        excluir = set()
        origem = a.recurso_de or (_origem(a.autos, autos) if autos else None)
        if origem:
            excluir |= _ja_julgaram(origem)
        caso = a.caso or ((autos or {}).get('caso') or {}).get('titulo') or ''
        tipo = a.tipo or ((autos or {}).get('caso') or {}).get('tipo')
        sessao, estado, afastados = J.convocar(dados, caso=caso, tipo=tipo, n=a.n,
                                               impedimentos=a.impedir or [], semente=a.semente, excluir=excluir)
        if not a.simular:
            J.gravar_estado(estado)
            if autos is not None:
                jj = autos.setdefault('juri', {})
                jj.update({'sessao': sessao['id'], 'convocados': sessao['convocados'],
                           'impedimentos': sessao['impedimentos']})
                _gravar_autos(a.autos, autos)
        ids = J.por_id(dados)
        if a.json:
            print(json.dumps({'sessao': sessao['id'], 'convocados': sessao['convocados'],
                              'afastados': [{'id': i, 'motivo': m} for i, m in afastados],
                              'gravado_nos_autos': bool(autos is not None and not a.simular)}, ensure_ascii=False, indent=2))
            return
        print(f'SESSÃO {sessao["id"]}{" (simulada: o rodízio não foi gravado)" if a.simular else ""}')
        print(f'Caso: {sessao["caso"] or "-"} · tipo: {sessao["tipo"] or "-"} · '
              f'impedimentos: {", ".join(sessao["impedimentos"]) or "nenhum"}')
        print(f'\n{len(sessao["convocados"])} convocados:')
        for i in sessao['convocados']:
            print('  ' + J.resumo(ids[i], curto=True))
        if afastados:
            print('\nVoltaram para o topo do saco (não perdem a vez):')
            for i, motivo in afastados:
                print(f'  {i} {ids[i]["nome"]}: {motivo}')
        if autos is not None and not a.simular:
            print(f'\nGravado nos autos: juri.sessao e os {len(sessao["convocados"])} convocados'
                  + (f' ({len(excluir)} que já julgaram o caso de origem ficaram de fora)' if excluir else '') + '.')
        print(f'\nPróximo: promotor e defesa recusam até {J.RECUSAS_MAX} cada; depois '
              f'python tribunal.py juri conselho {sessao["id"]} --acusacao IDS --defesa IDS')
    elif a.acao == 'conselho':
        if not a.alvo:
            raise J.JuriRecusado('diga a sessão: juri conselho SESSAO --acusacao IDS --defesa IDS')
        conselho, estado = J.formar_conselho(dados, a.alvo[0], _lista(a.acusacao), _lista(a.defesa),
                                             n=a.n if a.n != J.SESSAO_N else J.CONSELHO_N, semente=a.semente)
        if not a.simular:
            J.gravar_estado(estado)
            if a.autos:
                autos = A.carregar(a.autos)
                jj = autos.setdefault('juri', {})
                antigas = {r.get('jurado'): r.get('motivo', '') for lado in (jj.get('recusas') or {}).values()
                           for r in lado if isinstance(r, dict)}
                jj['recusas'] = {lado: [{'jurado': i, 'motivo': antigas.get(i, '')} for i in _lista(ids_)]
                                 for lado, ids_ in (('acusacao', a.acusacao), ('defesa', a.defesa))}
                jj['conselho'] = [j['id'] for j in conselho]
                _gravar_autos(a.autos, autos)
                print('Gravado nos autos: recusas e conselho (escreva o motivo de cada recusa em juri.recusas).\n')
        print(f'CONSELHO DE SENTENÇA da sessão {a.alvo[0]} ({len(conselho)}):\n')
        for j in conselho:
            print(J.resumo(j) + '\n')
    elif a.acao == 'ficha':
        ids = J.por_id(dados)
        for i in a.alvo:
            if i not in ids:
                raise J.JuriRecusado(f'jurado não encontrado: {i}')
            print(json.dumps(ids[i], ensure_ascii=False, indent=2) if a.json else J.resumo(ids[i]) + '\n')
    elif a.acao == 'listar':
        xs = J.filtrar(dados['jurados'], a.filtro or [])
        for j in xs:
            print(J.resumo(j, curto=True))
        print(f'\n{len(xs)} de {len(dados["jurados"])}')
    elif a.acao == 'especial':
        xs = J.sortear_livre(dados, a.n if a.n != J.SESSAO_N else J.CONSELHO_N, a.filtro or [], a.semente)
        print(f'JÚRI ESPECIAL ({len(xs)}, fora do rodízio, filtros: {", ".join(a.filtro or []) or "nenhum"}):\n')
        for j in xs:
            print(J.resumo(j) + '\n')
    elif a.acao == 'cotas':
        linhas = J.conferir(dados)
        pior = 0
        dim0 = None
        for dim, cat, meta, real, n in linhas:
            if dim != dim0:
                print(f'\n{dim} (base: {n} jurados)')
                dim0 = dim
            dif = real - meta
            pior = max(pior, abs(dif))
            print(f'  {cat:<38} meta {meta:5.1f}%  elenco {real:5.1f}%  {dif:+5.1f}')
        print(f'\nMaior desvio: {pior:.1f} ponto(s) percentual(is)')


# ------------------------------------------------------------------ autos

def cmd_validar(a):
    erros = A.validar(A.carregar(a.autos))
    if erros:
        print(f'{len(erros)} erro(s):')
        for e in erros:
            print(f'  - {e}')
        return 1
    print('autos válidos')


def _modo(a):
    return LG.modo_valido(getattr(a, 'linguagem', None) or CS.linguagem() or LG.PADRAO)


def cmd_placar(a):
    autos = A.carregar(a.autos)
    p = A.placar(autos)
    if a.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
    elif _modo(a) == 'natural':
        print(LG.placar_simples(p, A.opcoes(autos)))
    else:
        print(A.placar_md(p))


def cmd_ata(a):
    autos = A.carregar(a.autos)
    erros = A.validar(autos)
    if erros:
        print('autos com erro: ' + '; '.join(erros), file=sys.stderr)
        return 1
    if _modo(a) == 'natural':
        ids = J.por_id(J.carregar_foro((autos.get('juri') or {}).get('foro') or 'brasil'))
        md = f'# {autos["caso"]["titulo"]}\n\n' + LG.ata_simples(autos, A.placar(autos) if autos.get('votos') else None, ids)
    else:
        md = f'# {autos["caso"]["titulo"]}\n\n' + A.ata_md(autos)
    if a.o:
        with open(a.o, 'w', encoding='utf-8', newline='\n') as f:
            f.write(md)
        print(f'ata gravada em {a.o}')
    else:
        print(md)
    if autos.get('sentenca') and MC.disponivel()[0]:
        MC.lembrete(f'caso julgado: ofereça salvar no Memory Card. Prévia: python tribunal.py cartao enviar {a.autos}')


def gerar_sala(caminho, destino=None):
    """Gera a sala do tribunal em pixel art (HTML único) a partir dos autos. Sem sentença, a página fica AO VIVO:
    recarrega sozinha a cada 6 s e continua de onde parou. Devolve (destino, ao_vivo) ou levanta CasoRecusado."""
    caminho = caminho if not os.path.isdir(caminho) else os.path.join(caminho, 'autos.json')
    autos = A.carregar(caminho)
    erros = [e for e in A.validar(autos) if 'sentenca' not in e and 'pergunta vazia' not in e]
    if erros:
        raise CS.CasoRecusado('autos com erro: ' + '; '.join(erros))
    dados = J.carregar_foro((autos.get('juri') or {}).get('foro') or 'brasil')
    ids = J.por_id(dados)
    usados = []
    for i in (autos.get('juri') or {}).get('convocados', []) + [v['jurado'] for v in autos.get('votos', [])]:
        if i in ids and i not in usados:
            usados.append(i)
    payload = {
        'id': MC.slug(autos['caso']['titulo']) + '-' + str((autos.get('juri') or {}).get('sessao', '')),
        'ao_vivo': not autos.get('sentenca'),
        'autos': autos,
        'jurados': [ids[i] for i in usados],
        'placar': A.placar(autos) if autos.get('votos') else None,
        'termos': LG.para_sala(),
        'linguagem': LG.modo_valido(CS.linguagem() or LG.PADRAO),
    }
    with open(os.path.join(RAIZ, 'visual', 'tribunal.html'), encoding='utf-8') as f:
        modelo = f.read()
    js = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
    html = modelo.replace('__DADOS__', js, 1)
    destino = destino or os.path.join(os.path.dirname(os.path.abspath(caminho)), 'tribunal.html')
    with open(destino, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)
    CS.lembrar_ultimo(caminho)
    return destino, payload['ao_vivo']


def _abrir_no_navegador(destino):
    """Abre a sala numa janela própria do Edge/Chrome com o som liberado (perfil separado, para a regra valer mesmo
    com o navegador já aberto): o malhete toca sozinho, inclusive depois das recargas do modo ao vivo. Sem
    Edge/Chrome, usa o navegador padrão."""
    import pathlib
    import subprocess
    import tempfile
    import webbrowser
    from motor import exportar as EXP
    url = pathlib.Path(destino).resolve().as_uri()
    nav = EXP.navegador()
    if nav and os.environ.get('TRIBUNAL_SALA_NAVEGADOR_PADRAO') != '1':
        perfil = os.path.join(tempfile.gettempdir(), 'tribunal-sala')
        try:
            subprocess.Popen([nav, f'--app={url}', '--autoplay-policy=no-user-gesture-required', f'--user-data-dir={perfil}',
                              '--no-first-run', '--no-default-browser-check', '--window-size=1440,900'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            pass
    try:
        return bool(webbrowser.open(url))
    except webbrowser.Error:
        return False


def cmd_visualizar(a):
    destino, ao_vivo = gerar_sala(a.autos, a.o)
    print(f'sala gravada em {destino}{" (ao vivo: recarrega sozinha até a sentença)" if ao_vivo else ""}')
    if a.abrir:
        _abrir_no_navegador(destino)


def cmd_abrir(a):
    """Abre a sala do caso (sem argumento: o último caso). O usuário nunca precisa digitar um caminho."""
    caminho = a.autos or CS.ultimo_caso()
    destino, ao_vivo = gerar_sala(caminho)
    ok = _abrir_no_navegador(destino)
    CS.registrar_abrir(caminho if not os.path.isdir(caminho) else os.path.join(caminho, 'autos.json'), ok)
    print(f'{"Sala aberta no navegador" if ok else "Não consegui abrir o navegador"}: '
          f'{"ao vivo, " if ao_vivo else ""}{destino}')
    if not ok:
        print('Abra este arquivo no navegador: ' + destino)
        return 1


def cmd_novo(a):
    arq, decidido = CS.novo_caso(a.titulo, a.tipo)
    print(f'caso criado: {arq}')
    if not decidido:
        print(f'PERGUNTE AO USUÁRIO (uma vez só): "Guardo seus casos em {CS.PASTA_PADRAO}? (s/n)". '
              'Depois rode: python tribunal.py pasta --fixa  (sim)  ou  python tribunal.py pasta --sessao  (não)')


def cmd_validacao(a):
    from motor import validacao as V
    casos = V.carregar_casos(a.casos or os.path.join(RAIZ, 'validacao', 'casos.json'), a.gabarito)
    if a.so:
        casos = [c for c in casos if c['id'] in a.so.split(',')]
    if a.acao == 'preparar':
        ch = V.preparar(a.pasta, casos, lotes=a.lotes)
        print(json.dumps(ch, ensure_ascii=False, indent=2) if a.json else
              '\n'.join(f'- comando: {c["comando"]}' if c.get('comando') else
                        f'- {c["subagent_type"]} | {c["description"]}\n  {c["prompt"]}' for c in ch))
        print(f'{len(ch)} chamada(s); depois: python tribunal.py validacao resultado --pasta {a.pasta}', file=sys.stderr)
    else:
        r = V.resultado(a.pasta, casos)
        md = V.resultado_md(r, V.linha_de_base(a.base, casos) if a.base else None)
        with open(os.path.join(a.pasta, 'resultado.md'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(md)
        print(md)


def cmd_onda(a):
    if a.juntar:
        for linha in O.onda_juntar(a.autos):
            print(linha)
        return 0
    fase, chamadas, passos = O.onda(a.autos)
    if a.json:
        print(json.dumps({'fase': fase, 'chamadas': chamadas, 'passos': passos}, ensure_ascii=False, indent=2))
        return 0
    print(f'FASE: {fase}')
    if not chamadas:
        print('Sem subagentes nesta fase. Faça você:')
        for x in passos:
            print(f'  {x}')
        return 0
    print(f'{len(chamadas)} chamada(s), lance todas juntas numa mensagem (Agent, em paralelo):')
    for c in chamadas:
        if c.get('comando'):
            print(f'- comando (modelo externo, rode junto com os subagentes): {c["comando"]}')
            continue
        print(f'- subagent_type: {c["subagent_type"]} | description: {c["description"]}')
        print(f'  prompt: {c["prompt"]}')
    print(f'Quando todas responderem: python tribunal.py onda {a.autos} --juntar')


def cmd_exportar(a):
    from motor import exportar as EXP
    try:
        arq, tipo = EXP.exportar(a.autos, a.o, natural=_modo(a) == 'natural', versao=VERSAO)
    except RuntimeError as e:
        print(f'ERRO: {e}')
        return 1
    sem_nav = tipo == 'html' and not (a.o or '').lower().endswith('.html')
    print(f'{tipo.upper()} gerado: {arq}'
          + ('  (sem Edge/Chrome/Chromium: abra no navegador e use Imprimir > Salvar como PDF)' if sem_nav else ''))


def cmd_externo(a):
    from motor import externo as EX
    try:
        n = EX.votar(a.briefing, a.destino)
    except EX.ExternoFalhou as e:
        print(f'ERRO: {e}')
        return 1
    print(f'OK externo: {n} votos ({EX.configurado()["modelo"]})')


def cmd_perito_feito(a):
    from motor import debate as DB
    n = O.pendencias_resolvidas(a.autos)
    print(f'rodada {n} do perito registrada; plano apagado. Rode a onda de novo.'
          + (' Daqui em diante, o redator não abre pendências novas.' if n >= DB.MAX_RODADAS_PERITO else ''))


def cmd_entrega(a):
    autos = A.carregar(a.autos)
    md = A.entrega_md(autos, natural=_modo(a) == 'natural', enxuta=a.enxuta)
    if a.o:
        with open(a.o, 'w', encoding='utf-8', newline='\n') as f:
            f.write(md)
        print(f'entrega gravada em {a.o}')
    else:
        print(md)


def cmd_linguagem(a):
    if a.modo:
        CS.definir_linguagem(LG.modo_valido(a.modo))
        print(f'linguagem: {LG.modo_valido(a.modo)} (ata, placar e sala; a sala também tem o botão para trocar na hora)')
    else:
        m = CS.linguagem()
        print(f'linguagem: {LG.modo_valido(m)}' if m else 'linguagem: tribunal (o usuário ainda não escolheu: pergunte uma vez)')


def cmd_pasta(a):
    if a.fixa or a.sessao:
        p = CS.definir_pasta(CS.PASTA_PADRAO if a.fixa else None)
        print(f'casos novos em: {p}' if p else 'casos novos na pasta de trabalho de cada sessão (tribunal-autos/)')
    else:
        base, decidido = CS.pasta_base()
        print(f'casos em: {base}' + ('' if decidido else ' (o usuário ainda não escolheu)'))


def cmd_fase(a):
    """Carimba a hora da fase, regera a sala ao vivo e imprime a linha de narração para a conversa."""
    linha = CS.marcar_fase(a.autos, a.fase)
    try:
        gerar_sala(a.autos)
    except CS.CasoRecusado:
        pass
    print(linha)


def cmd_parar(a):
    """Parada antecipada da rodada 1: se a liderança já é estável, registra e dispensa os lotes restantes."""
    autos = A.carregar(a.autos)
    pode, e = A.parar_cedo(autos)
    pct = round(100 * (e['estabilidade'] or 0))
    if not pode:
        print(f'CONTINUE: {e["n"]} votos, liderança de {e["opcao"]} estável em {pct}% das reamostragens '
              f'(precisa de {A.PARAR_MINIMO}+ votos e {round(100 * A.PARAR_LIMIAR)}%). Rode os lotes restantes.')
        return 3
    autos.setdefault('juri', {})['rodada1_parada'] = {'n': e['n'], 'estabilidade': e['estabilidade'], 'opcao': e['opcao']}
    _gravar_autos(a.autos, autos)
    print(f'PARE: {e["n"]} votos bastam; {e["opcao"]} lidera, estável em {pct}% das reamostragens. '
          'Os lotes restantes estão dispensados (registrado nos autos). Siga para os debates.')


def _gravar_autos(caminho, autos):
    if os.path.isdir(caminho):
        caminho = os.path.join(caminho, 'autos.json')
    with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(autos, f, ensure_ascii=False, indent=2)
        f.write('\n')


def cmd_reforco(a):
    """Caso apertado: se a maioria da sala é estável em menos de 80% das reamostragens, convoca mais 25 jurados
    do rodízio (lotes 6 a 10, com --de 10). Com o jurado enxuto, custa uns 55 mil tokens."""
    autos = A.carregar(a.autos)
    j = autos.setdefault('juri', {})
    if j.get('reforco'):
        print(f'o reforço já foi convocado ({len(j["reforco"])} jurados): rode os lotes 6 a 10 com --de 10')
        return
    r1 = [v for v in autos.get('votos', []) if v.get('rodada') == 1]
    e = A.estabilidade(r1, A.opcoes(autos))
    pct = round(100 * (e['estabilidade'] or 0))
    if not a.forcar and (e['estabilidade'] or 0) >= A.REFORCO_LIMIAR:
        print(f'SEM REFORÇO: a liderança de {e["opcao"]} é estável em {pct}% das reamostragens '
              f'({round(100 * A.REFORCO_LIMIAR)}% ou mais dispensa).')
        return
    dados = J.carregar_foro(j.get('foro') or 'brasil')
    sessao, estado, _ = J.convocar(dados, caso=autos['caso']['titulo'] + ' (reforço)', tipo=autos['caso'].get('tipo'),
                                   impedimentos=[x.split(' ')[0] for x in j.get('impedimentos', [])], semente=a.semente,
                                   excluir=set(j.get('convocados') or []))
    novos = [i for i in sessao['convocados'] if i not in (j.get('convocados') or [])]
    J.gravar_estado(estado)
    j['reforco'] = novos
    _gravar_autos(a.autos, autos)
    print(f'REFORÇO: {len(novos)} jurados novos (sala estável em só {pct}%). Rode os lotes 6 a 10: '
          f'python tribunal.py briefing {a.autos} --rodada 1 --lote K --de 10  (K = 6..10), depois juntar.')


def cmd_debate(a):
    texto, destino = DB.briefing(a.autos, a.papel, a.id)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    print(texto)
    print(f'\n[o agente grava em {destino}]', file=sys.stderr)


def cmd_juntar_debate(a):
    entrou, erros = DB.juntar_debate(a.autos)
    print('juntado: ' + (', '.join(entrou) or 'nada (a pasta debate/ está vazia?)'))
    for e in erros:
        print(f'ERRO: {e}')
    return 1 if erros else 0


def cmd_comparar(a):
    r = CS.comparar(A.carregar(a.autos_a), A.carregar(a.autos_b))
    print(f'Veredito: {r["veredito"][0]}  →  {r["veredito"][1]}  ({"igual" if r["veredito_igual"] else "MUDOU"})')
    print(f'Confiança: {r["confianca"][0]}  →  {r["confianca"][1]}')
    print(f'Segmentos (n ≥ {A.MIN_SEGMENTO}): {r["segmentos_iguais"]} de {r["segmentos_comparados"]} com a mesma maioria')
    viradas = {k for k, _, _ in r['viradas']}
    for (campo, cat), x, y in r['segmentos_diferentes']:
        print(f'  {"VIROU " if (campo, cat) in viradas else "oscilou"} {campo} = {cat}: {x}  →  {y}')
    print(f'Viradas de verdade (maioria clara → outra maioria clara): {len(r["viradas"])}. '
          'Empate ↔ maioria em grupo pequeno é oscilação, não virada.')
    return 0 if r['veredito_igual'] else 3


# ------------------------------------------------------------------ orquestração (ideias do Arena)

def cmd_briefing(a):
    texto, destino, meus = O.briefing(a.autos, a.rodada, a.lote, a.de)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    print(texto)
    print(f'\n[{len(meus)} jurados neste lote; o subagente grava em {destino}]', file=sys.stderr)


def cmd_juntar(a):
    n, faltando, erros = O.juntar(a.autos, a.arquivos or None)
    for e in erros:
        print(f'ERRO: {e}')
    if n == 0 and erros:
        print('nada foi juntado: corrija os arquivos (ou rode o lote de novo) e repita')
        return 1
    print(f'{n} voto(s) juntado(s) nos autos')
    for r, ids in faltando.items():
        print(f'faltam {len(ids)} na rodada {r}: {", ".join(ids)} (rode o lote de novo; nunca vote no lugar)')


def cmd_proximo(a):
    fase, passos = O.proximo(a.autos)
    print(f'PRÓXIMA FASE: {fase}')
    for x in passos:
        print(f'  {x}')


def cmd_plano(a):
    modo = a.modo
    if a.reversivel or a.impacto:
        modo, motivo = O.sugerir_modo({'sim': True, 'nao': False}.get(a.reversivel), a.impacto)
        print(f'Sugestão: modo {modo} ({motivo}).' + ('' if not a.modo or a.modo == modo else f' Você pediu {a.modo}.'))
        modo = a.modo or modo
    modo = modo or 'completo'
    itens, total, tokens = O.plano(modo, a.propostas, a.lotes)
    for rot, n, modelo in itens:
        print(f'  {n:>2}  {rot}  [{modelo}]')
    if total:
        print(f'Total: {total} subagente(s), cerca de {tokens // 1000} mil tokens (jurado ~{O.TOKENS_JURADO // 1000} mil, '
              f'medido; advogado e autor ~{O.TOKENS_ADVOGADO // 1000} mil, medido). Sem os agentes enxutos instalados, '
              f'cada subagente custa ~{O.TOKENS_POR_SUBAGENTE // 1000} mil. Modo rápido: 0 subagentes.')
    else:
        print('Total: 0 subagentes. Os votos ficam menos independentes: diga isso na entrega.')


def cmd_pendencias(a):
    """Casos do Tribunal no Memory Card ainda sem desfecho: pergunte por eles (é o que calibra a confiança)."""
    ok, motivo = MC.disponivel()
    if not ok:
        print(f'Memory Card indisponível: {motivo}')
        return 1
    import datetime
    hoje = datetime.date.today()
    casos = [f for f in MC.ler_catalogo(MC.preparar_pasta(atualizar=False))
             if f['solucao'] == MC.SOLUCAO and not f.get('desfecho')]
    if not casos:
        print('Nenhum caso esperando desfecho.')
        return
    for f in sorted(casos, key=lambda x: x.get('criado_em', '')):
        dias = (hoje - datetime.date.fromisoformat(f.get('criado_em', hoje.isoformat())[:10])).days
        print(f'- {f["artigo"]} · {dias} dia(s) · {f.get("veredito") or "-"} ({f.get("confianca", "-")}%) · {f["ref"]}')
    print(f'{len(casos)} caso(s) sem desfecho. Pergunte ao usuário como terminou e registre com: '
          'python tribunal.py cartao desfecho REF --resultado acertou|parcial|errou --nota "..."')


def cmd_propostas(a):
    if a.acao == 'iniciar':
        if not a.autos:
            raise PR.PropostaRecusada('diga os autos: propostas iniciar AUTOS')
        ids = DB.iniciar_propostas(a.autos, a.n, a.semente)
        print(f'cartas gravadas nos autos: {", ".join(ids)}. Um tribunal-autor por proposta: '
              f'python tribunal.py debate {a.autos} --papel autor --id X1')
        return
    if a.acao == 'cartas':
        for c in PR.distribuir(a.n, a.semente):
            k = c['carta']
            print(f'{c["id"]}\n  modo: {k["modo"]}\n  fluxo: {k["fluxo"]}\n  estratégia: {k["estrategia"]}\n')
    else:
        if not a.autos:
            raise PR.PropostaRecusada('diga os autos: propostas placar AUTOS')
        autos = A.carregar(a.autos)
        print(PR.placar_md(autos, a.finalistas) or 'os autos não têm propostas')



# ------------------------------------------------------------------ Memory Card

def cmd_cartao(a):
    if a.acao == 'iniciar':
        r = MC.iniciar(repo=a.repo, pasta=a.pasta, publico=a.publico, substituir=a.substituir)
        print(f'Memory Card ligado: {r["repo"] or "local"} em {r["pasta"]}')
        return
    ok, motivo = MC.disponivel()
    if not ok:
        raise MC.CartaoRecusado(motivo)
    pasta = MC.preparar_pasta(atualizar=a.acao in ('enviar', 'marcar', 'desfecho'))
    if a.acao == 'catalogo':
        fichas = [f for f in MC.ler_catalogo(pasta) if a.todos or f['solucao'] == MC.SOLUCAO]
        if a.json:
            print(json.dumps(fichas, ensure_ascii=False, indent=2))
            return
        for f in fichas:
            d = f.get('desfecho') or {}
            print(f'{f["ref"]} · v{f["versao"]} · {f.get("veredito") or "-"} ({f.get("confianca", "-")}%) · '
                  f'{d.get("resultado", "sem desfecho")}')
        print(f'\n{len(fichas)} save(s)')
    elif a.acao == 'buscar':
        achados = MC.buscar(pasta, a.termos, limite=a.limite)
        for pts, f in achados:
            print(f'[{pts}] {f["ref"]} · {f.get("veredito") or f.get("descricao", "")}')
        if not achados:
            print('nada no cartão para esses termos')
    elif a.acao == 'enviar':
        envio = MC.montar_envio(a.autos, pasta, categoria=a.categoria, secao=a.secao, artigo=a.artigo,
                                descricao=a.descricao, motivo=a.motivo, status=a.status,
                                relacionados=a.relacionado or [])
        print(f'DESTINO: saves/{envio["ref"]} · versão {envio["ficha"]["versao"]}'
              f'{" (substitui)" if envio["substitui"] else " (novo)"}')
        for x in envio['avisos']:
            print(f'AVISO: {x}')
        if envio['substitui']:
            print('\n--- diff do README ---\n' + (envio['diff_readme'] or '(sem mudança)'))
        else:
            print('\n--- README ---\n' + envio['readme'])
        print('--- ficha ---\n' + json.dumps(envio['ficha'], ensure_ascii=False, indent=2))
        if a.confirmar:
            MC.gravar_envio(envio, pasta)
            print(f'\nSALVO: saves/{envio["ref"]}')
        else:
            print('\nPRÉVIA: nada foi gravado. Repita com --confirmar depois do "sim" do usuário.')
    elif a.acao == 'marcar':
        MC.marcar(pasta, a.ref, a.status)
        print(f'{a.ref}: status {a.status}')
    elif a.acao == 'desfecho':
        f = MC.desfecho(pasta, a.ref, a.resultado, a.nota)
        print(f'{a.ref}: desfecho {f["desfecho"]["resultado"]}')
    elif a.acao == 'calibracao':
        c = MC.calibracao(pasta)
        if not c['n']:
            print('nenhum caso com desfecho ainda: registre com cartao desfecho REF --resultado ...')
            return
        print(f'{c["n"]} caso(s) com desfecho · Brier {c["brier"]:.3f} (0 = perfeito; 0.250 = chutar 50%)')
        for faixa, v in c['faixas'].items():
            print(f'  confiança {faixa}-{faixa + 9}%: {v["n"]} caso(s), acerto real {v["acerto"] * 100:.0f}%')
        for rot, k in (('quando acatou a sentença', 'acerto_quando_acatou'),
                       ('quando recorreu', 'acerto_quando_recorreu')):
            if c[k] is not None:
                print(f'  acerto {rot}: {c[k] * 100:.0f}%')


# ------------------------------------------------------------------ CLI

def main(argv=None):
    p = argparse.ArgumentParser(prog='tribunal', description='Tribunal: leve qualquer coisa a julgamento.')
    p.add_argument('--version', action='version', version=VERSAO)
    sub = p.add_subparsers(dest='cmd', required=True)

    sub.add_parser('status').set_defaults(f=cmd_status)

    j = sub.add_parser('juri')
    j.add_argument('acao', choices=['convocar', 'conselho', 'ficha', 'listar', 'cotas', 'especial'])
    j.add_argument('alvo', nargs='*', help='sessão (conselho) ou ids (ficha)')
    j.add_argument('--foro', default='brasil')
    j.add_argument('--caso')
    j.add_argument('--tipo', choices=list(A.TIPOS))
    j.add_argument('--n', type=int, default=J.SESSAO_N)
    j.add_argument('--impedir', action='append', help='filtro de impedimento, ex.: "idade<8" (pode repetir)')
    j.add_argument('--filtro', action='append', help='ex.: idade>=60, regiao=Nordeste (pode repetir)')
    j.add_argument('--acusacao', help='ids recusados pela acusação, separados por vírgula')
    j.add_argument('--defesa', help='ids recusados pela defesa, separados por vírgula')
    j.add_argument('--semente', type=int)
    j.add_argument('--simular', action='store_true', help='não grava o rodízio')
    j.add_argument('--json', action='store_true')
    j.add_argument('--autos', help='grava sessão e convocados (convocar) ou recusas e conselho (conselho) nos autos')
    j.add_argument('--recurso-de', dest='recurso_de', help='autos do caso de origem: quem já julgou fica de fora')
    j.set_defaults(f=cmd_juri)

    for nome, f in (('validar', cmd_validar), ('placar', cmd_placar), ('ata', cmd_ata)):
        x = sub.add_parser(nome)
        x.add_argument('autos')
        if nome == 'placar':
            x.add_argument('--json', action='store_true')
        if nome in ('placar', 'ata'):
            x.add_argument('--linguagem', choices=list(LG.MODOS) + list(LG.APELIDOS))
        if nome == 'ata':
            x.add_argument('-o')
        x.set_defaults(f=f)

    x = sub.add_parser('briefing', help='o prompt exato de um lote de jurados, gerado dos autos')
    x.add_argument('autos')
    x.add_argument('--rodada', type=int, choices=[1, 2], required=True)
    x.add_argument('--lote', type=int, default=1)
    x.add_argument('--de', type=int, default=5)
    x.set_defaults(f=cmd_briefing)
    x = sub.add_parser('juntar', help='junta nos autos os votos gravados pelos subagentes')
    x.add_argument('autos')
    x.add_argument('arquivos', nargs='*')
    x.set_defaults(f=cmd_juntar)
    x = sub.add_parser('proximo', help='a próxima fase do rito e o comando exato')
    x.add_argument('autos')
    x.set_defaults(f=cmd_proximo)
    x = sub.add_parser('plano', help='quantos subagentes o caso vai usar')
    x.add_argument('--modo', choices=['completo', 'rapido'])
    x.add_argument('--reversivel', choices=['sim', 'nao'], help='a decisão é fácil de desfazer?')
    x.add_argument('--impacto', choices=['baixo', 'medio', 'alto'])
    x.add_argument('--propostas', type=int, default=0)
    x.add_argument('--lotes', type=int, default=5)
    x.set_defaults(f=cmd_plano)
    x = sub.add_parser('pendencias', help='casos do Tribunal no Memory Card ainda sem desfecho')
    x.set_defaults(f=cmd_pendencias)
    x = sub.add_parser('propostas', help='concurso de propostas: cartas e placar')
    x.add_argument('acao', choices=['cartas', 'iniciar', 'placar'])
    x.add_argument('autos', nargs='?')
    x.add_argument('--n', type=int, default=O.PROPOSTAS_PADRAO)
    x.add_argument('--semente', type=int)
    x.add_argument('--finalistas', type=int, default=2)
    x.set_defaults(f=cmd_propostas)

    x = sub.add_parser('visualizar', help='a sala do tribunal em pixel art, a partir dos autos')
    x.add_argument('autos')
    x.add_argument('-o')
    x.add_argument('--abrir', action='store_true', help='abre no navegador')
    x.set_defaults(f=cmd_visualizar)
    x = sub.add_parser('abrir', help='abre a sala do caso no navegador (sem argumento: o último caso)')
    x.add_argument('autos', nargs='?')
    x.set_defaults(f=cmd_abrir)
    x = sub.add_parser('novo', help='cria a pasta e os autos de um caso novo')
    x.add_argument('titulo')
    x.add_argument('--tipo', choices=list(A.TIPOS), default='outro')
    x.set_defaults(f=cmd_novo)
    x = sub.add_parser('validacao', help='mede o júri contra casos de desfecho conhecido (validacao/casos.json)')
    x.add_argument('acao', choices=['preparar', 'resultado'])
    x.add_argument('--pasta', required=True)
    x.add_argument('--casos')
    x.add_argument('--so', help='ids separados por vírgula')
    x.add_argument('--gabarito', help='desfechos em arquivo à parte (validação cega)')
    x.add_argument('--base', help='palpites de um modelo sozinho, para comparar com o júri')
    x.add_argument('--lotes', type=int, default=2)
    x.add_argument('--json', action='store_true')
    x.set_defaults(f=cmd_validacao)
    x = sub.add_parser('onda', help='a fase atual: briefings prontos e as chamadas de subagente; --juntar junta tudo')
    x.add_argument('autos')
    x.add_argument('--juntar', action='store_true')
    x.add_argument('--json', action='store_true')
    x.set_defaults(f=cmd_onda)
    x = sub.add_parser('exportar', help='o dossiê do julgamento em PDF, para mostrar a outras pessoas')
    x.add_argument('autos')
    x.add_argument('-o', help='arquivo de saída (.pdf ou .html; padrão: autos.pdf na pasta do caso)')
    x.add_argument('--linguagem', choices=['tribunal', 'natural', 'simples'])
    x.set_defaults(f=cmd_exportar)

    x = sub.add_parser('externo', help='um lote de jurados num modelo de outra família (TRIBUNAL_EXTERNO_MODELO)')
    x.add_argument('briefing')
    x.add_argument('destino')
    x.set_defaults(f=cmd_externo)

    x = sub.add_parser('perito-feito', help='o perito resolveu as pendências do plano: apaga o plano e conta a rodada')
    x.add_argument('autos')
    x.set_defaults(f=cmd_perito_feito)

    x = sub.add_parser('entrega', help='o que se mostra ao usuário no fim, montado dos autos')
    x.add_argument('autos')
    x.add_argument('-o')
    x.add_argument('--linguagem', choices=list(LG.MODOS) + list(LG.APELIDOS))
    x.add_argument('--enxuta', action='store_true', help='só decisão, plano, riscos e condições (sem o processo)')
    x.set_defaults(f=cmd_entrega)
    x = sub.add_parser('linguagem', help='termos de tribunal ou linguagem natural')
    x.add_argument('modo', nargs='?', choices=list(LG.MODOS) + list(LG.APELIDOS))
    x.set_defaults(f=cmd_linguagem)
    x = sub.add_parser('pasta', help='onde os casos ficam: pasta fixa (~/tribunal-autos) ou a da sessão')
    x.add_argument('--fixa', action='store_true')
    x.add_argument('--sessao', action='store_true')
    x.set_defaults(f=cmd_pasta)
    x = sub.add_parser('fase', help='marca o fim de uma fase: carimbo de hora, sala ao vivo e uma linha de narração')
    x.add_argument('autos')
    x.add_argument('fase', choices=list(CS.NARRACAO))
    x.set_defaults(f=cmd_fase)
    x = sub.add_parser('reforco', help='caso apertado: mais 25 jurados do rodízio na rodada 1')
    x.add_argument('autos')
    x.add_argument('--forcar', action='store_true')
    x.add_argument('--semente', type=int)
    x.set_defaults(f=cmd_reforco)
    x = sub.add_parser('debate', help='o prompt exato de promotor, defesa, réplica, autor ou contraditório')
    x.add_argument('autos')
    x.add_argument('--papel', required=True, choices=list(DB.PAPEIS))
    x.add_argument('--id', help='a proposta, para o papel autor (X1, X2...)')
    x.set_defaults(f=cmd_debate)
    x = sub.add_parser('juntar-debate', help='junta nos autos o que os agentes gravaram em debate/')
    x.add_argument('autos')
    x.set_defaults(f=cmd_juntar_debate)
    x = sub.add_parser('parar', help='parada antecipada da rodada 1, se a liderança já é estável')
    x.add_argument('autos')
    x.set_defaults(f=cmd_parar)
    x = sub.add_parser('comparar', help='compara dois julgamentos do mesmo caso (veredito, confiança, segmentos)')
    x.add_argument('autos_a')
    x.add_argument('autos_b')
    x.set_defaults(f=cmd_comparar)

    c = sub.add_parser('cartao')
    cs = c.add_subparsers(dest='acao', required=True)
    x = cs.add_parser('iniciar')
    x.add_argument('--repo')
    x.add_argument('--pasta')
    x.add_argument('--publico', action='store_true')
    x.add_argument('--substituir', action='store_true')
    x = cs.add_parser('catalogo')
    x.add_argument('--todos', action='store_true', help='inclui os saves das outras soluções')
    x.add_argument('--json', action='store_true')
    x = cs.add_parser('buscar')
    x.add_argument('termos', nargs='+')
    x.add_argument('--limite', type=int, default=10)
    x = cs.add_parser('enviar')
    x.add_argument('autos')
    for k in ('categoria', 'secao', 'artigo', 'descricao', 'motivo'):
        x.add_argument(f'--{k}')
    x.add_argument('--status', choices=MC.STATUS)
    x.add_argument('--relacionado', action='append')
    x.add_argument('--confirmar', action='store_true')
    x = cs.add_parser('marcar')
    x.add_argument('ref')
    x.add_argument('--status', required=True, choices=MC.STATUS)
    x = cs.add_parser('desfecho')
    x.add_argument('ref')
    x.add_argument('--resultado', required=True, choices=MC.DESFECHOS)
    x.add_argument('--nota', default='')
    cs.add_parser('calibracao')
    c.set_defaults(f=cmd_cartao)

    a = p.parse_args(argv)
    try:
        return a.f(a) or 0
    except (J.JuriRecusado, MC.CartaoRecusado, O.OrquestraRecusada, PR.PropostaRecusada, CS.CasoRecusado, DB.DebateRecusado) as e:
        print(f'RECUSADO: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
