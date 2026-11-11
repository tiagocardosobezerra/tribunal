"""
Briefings dos papéis de debate (promotor, defesa, réplica, autor de proposta, contraditório do concurso),
gerados dos autos para os agentes enxutos `tribunal-advogado` e `tribunal-autor` (só Ler e Gravar). Como no
briefing dos jurados: o texto sai dos autos, nunca de uma paráfrase do orquestrador, e a resposta vai para
um arquivo em <autos>/debate/. `juntar_debate` põe tudo nos autos.
"""

import glob
import json
import os

from . import autos as A
from . import casos as CS
from . import linguagem as LG
from . import propostas as PR

PAPEIS = ('promotor', 'defesa', 'replica', 'autor', 'contraditorio', 'checagem', 'juiz', 'plano', 'plano_ataque',
          'plano_revisao')
JUIZ_INDEPENDENTE = 'juiz independente'
MAX_RODADAS_PERITO = 2   # depois disso, o que faltar verificar vira hipótese e o plano segue


class DebateRecusado(RuntimeError):
    """O pedido de debate não pode seguir."""


def _arq(caminho):
    return os.path.join(caminho, 'autos.json') if os.path.isdir(caminho) else caminho


def _provas(autos):
    ps = [p for p in autos.get('provas', []) if p.get('aceita', True)]
    return '\n'.join(f'- {p["id"]} ({p.get("tipo", "")}): {p.get("descricao", "")} [fonte: {p.get("fonte", "")}]' for p in ps) or '- (sem provas)'


def _ataques(teses):
    return '\n'.join(f'- {t.get("id", "?")} [{(t.get("gravidade") or "").upper()}] {t["texto"]}'
                     + (f' | onde: {t["onde"]}' if t.get('onde') else '')
                     + (f' | contraexemplo: {t["contraexemplo"]}' if t.get('contraexemplo') else '') for t in teses)


FORMATO = {
    'promotor': '{"teses":[{"id":"A1","gravidade":"fatal|grave|leve","texto":"...","onde":"...","contraexemplo":"...","provas":["P1"]}],"melhor_tese_adversaria":"...","replica":"A melhor tese da defesa é ..."}',
    'defesa': '{"teses":[{"texto":"...","provas":["P1"]}],"condicoes":["sem número na frente: a lista já numera"],"teste_barato":"...","melhor_tese_adversaria":"...","treplica":"A melhor tese da acusação é ..."}',
    'replica': '{"respostas":[{"ataque":"A1","tipo":"concede|rebate","texto":"...","correcao":"... (se concede)"}]}',
    'autor': '{"id":"%s","apelido":"2 ou 3 palavras que um leigo entende (ex.: Fazer à mão primeiro)","titulo":"até 8 palavras","resumo":"2 frases simples","texto":"no máximo 350 palavras"}',
    'checagem': '{"A1":{"veredito":"confirma|rebaixa|derruba","gravidade":"fatal|grave|leve","motivo":"...","como_verifiquei":"a conta refeita ou o trecho exato da prova"}}',
    'plano': '{"recomendacao":"3 a 5 frases para o dono","certeza":{"valor":0,"por_que":"as lacunas pelo nome","sobe_se":"...","desce_se":"..."},"passo_mais_barato":{"o_que":"...","custo":"R$ ou zero","tempo":"horas ou dias"},"cenarios":[{"se":"o que pode acontecer","entao":"o que muda na decisão","certeza":"sobe|desce"}],"ordem":["1. ...","2. ..."],"proximo_passo":"igual ao passo 1","metas":[{"o_que":"...","grupo":"todos ou o grupo","como_medir":"...","meta":"número","prazo":"dias ou data"}],"testes":[{"o_que":"...","entrada":"...","esperado":"..."}],"criterio_de_abandono":"2 ou mais gatilhos, com número e prazo","cobertura":{"1":"em que passo a condição 1 é cumprida"},"hipoteses":["o que não está nas provas e precisa ser confirmado"],"atencao":["tensões com o que já está no ar, que não impedem o plano"],"conflitos":[],"pendencias_do_perito":["o que dá para verificar agora (site público, conta, documento) e ainda não foi verificado"]}',
    'juiz': '{"relatorio":"3 ou 4 frases: o que se julgou e o que aconteceu no processo","veredito":"uma das OPÇÕES, igual","confianca":0,"certeza_em_uma_frase":"por que esta confiança, em palavras simples","ajuste_da_confianca":"de onde veio o número: a sugerida e cada ajuste","fundamentos":[{"titulo":"até 8 palavras","texto":"2 a 4 frases","provas":["P1"],"peso":"decisivo|relevante|menor"}],"alternativas":[{"opcao":"cada opção que NÃO venceu, igual","por_que_nao":"1 a 3 frases, com prova","votos_conselho":0}],"contraditorio":{"caiu":"o que a defesa derrubou, em 1 a 2 frases","de_pe":"o que ficou sem resposta e o peso disso"},"dispositivo":"a decisão em forma de sentença: Julgo ... (a opção), com as condições numeradas abaixo","recomendacao":"2 a 3 frases para o dono, em palavras do dia a dia","fundamentacao":"resumo da fundamentação em 1 parágrafo","condicoes":["..."],"condicoes_origem":{"1":["A1"]},"ponto_de_virada":"...","provas_decisivas":["P1"],"voto_vencido":null,"proximo_passo":"UMA ação curta (até 25 palavras)","criterio_de_abandono":"...","ataques":[{"ataque":"A1","status":"corrigido|correcao_proposta|rebatido|de_pe","nota":"por quê","verificado":"só se corrigido: como se conferiu"}],"ataques_do_juiz":[{"id":"J1","gravidade":"fatal|grave|leve","texto":"falha que a acusação não viu"}]}',
    'plano_ataque': '{"ataques":[{"id":"P1","gravidade":"fatal|grave|leve","onde":"campo e item do plano","texto":"o furo, com a conta refeita se for conta","correcao_sugerida":"..."}]}',
    'contraditorio': '{"X1":{"ataques":[{"id":"X1a","gravidade":"fatal|grave|leve","texto":"...","onde":"...","contraexemplo":"...","provas":[]}],"respostas":[{"ataque":"X1a","tipo":"concede|rebate","texto":"...","correcao":"..."}]}, "X2":{...}}',
}


def _contexto_plano(autos, s):
    st = {x.get('ataque'): x.get('status') for x in s.get('ataques', [])}
    resp = {r.get('ataque'): r for r in (autos.get('defesa') or {}).get('respostas', [])}
    r2 = [v for v in autos.get('votos', []) if v.get('rodada') == 2 and v.get('motivo')]
    l = ['ATAQUES E COMO FICARAM:']
    for t in (autos.get('acusacao') or {}).get('teses', []):
        ch = t.get('checagem') or {}
        l.append(f'- {t.get("id")} [{(t.get("gravidade") or "").upper()}] {t["texto"]} | status: {st.get(t.get("id"), "-")} '
                 f'| correção: {(resp.get(t.get("id")) or {}).get("correcao", "")}'
                 + (f' | CHECAGEM DUPLA: {ch.get("veredito")} (era {str(ch.get("gravidade_original", "")).upper()}): '
                    f'{ch.get("motivo", "")}' if ch else ''))
    l += ['', 'O QUE OS 7 QUE DECIDEM DISSERAM:'] + [f'- {v["voto"]}: {v["motivo"]}' for v in r2]
    l += ['', f'RASCUNHO DO JUIZ: veredito "{s.get("veredito")}", confiança {s.get("confianca")}.', 'CONDIÇÕES (numeradas):']
    l += [f'{i}. {c}' for i, c in enumerate(s.get('condicoes') or [], 1)]
    l += [f'PRÓXIMO PASSO (rascunho): {s.get("proximo_passo", "")}', f'CRITÉRIO DE ABANDONO (rascunho): {s.get("criterio_de_abandono", "")}']
    return l


INSTRUCAO_PLANO = (
    'REGRAS DO PLANO. Ele é para o dono executar amanhã sem adivinhar. Quando houver CHECAGEM DUPLA, ela vale mais '
    'que o texto original do ataque. 1) "recomendacao": de 3 a 5 frases para o dono: a decisão nas palavras dele, o '
    'porquê em fatos das provas e o que fazer primeiro; sem números do processo (votos, placar, firmeza). '
    '2) "certeza": o valor é a confiança do juiz; "por_que" nomeia as lacunas que a seguram; "sobe_se" e "desce_se" '
    'dizem o que a mudaria. 3) "passo_mais_barato": a ação que mais reduz a dúvida pelo menor custo, com custo e '
    'tempo. 4) "ordem": os passos; o passo 1 é o próximo passo; nenhum passo pula uma condição que precisa vir antes. '
    '5) "metas": o que medir, como, o número que decide e o prazo; quando houver grupos (ramos, canais, perfis), uma '
    'meta por grupo e confira se o número fecha com o tamanho do grupo. 6) "testes": pelo menos 6. Se o objeto tem '
    'contas, use entradas reais das provas e calcule o esperado (refaça as contas; inclua arredondamento e casos de '
    'borda); se não tem, verificações observáveis com o que conta como passar. 7) "criterio_de_abandono": 2 ou mais '
    'gatilhos, cada um com número e prazo. 8) "cenarios": de 3 a 5 coisas que mudariam a decisão, pelo menos uma que '
    'leva a não seguir e uma que aumenta a certeza. 9) "cobertura": para CADA condição numerada, em que passo ela é '
    'cumprida. 10) "conflitos": SÓ contradições da sentença consigo mesma que impedem executar os passos na ordem; '
    'tensões com o que já está no ar vão em "atencao"; números que não estão nas provas vão em "hipoteses". '
    '11) "pendencias_do_perito": NENHUM passo pode ser "reconferir", "verificar" ou "checar" algo que dá para checar '
    'agora sem o dono (abrir um site público, refazer uma conta, ler um documento): isso vai para esta lista, e o perito '
    'resolve antes de o plano seguir. Só fica no plano o que depende do dono (testar o app por dentro, falar com '
    'clientes, medir vendas). '
    'Específico e direto: no máximo 900 palavras no total.')


INSTRUCAO_JUIZ = (
    'SEU PAPEL: JUIZ INDEPENDENTE. Você não fez a perícia nem conduziu o processo: decide só com o que está acima. '
    '1) O veredito é a MAIORIA DO CONSELHO (rodada 2), escrito igual a uma das opções. Se você discordar, o veredito '
    'continua o do conselho e a sua posição vai em "voto_vencido". 2) Status de CADA ataque da acusação: "corrigido" '
    'só se a correção JÁ foi feita e conferida nas provas (diga como em "verificado"); "correcao_proposta" se a defesa '
    'concedeu e propôs uma correção ainda não feita; "rebatido" só com prova ou contraexemplo verificável; "de_pe" se '
    'a resposta só insistiu, prometeu sem dizer como ou não existe. Quando houver CHECAGEM DUPLA, ela vale mais que o '
    'texto original. 3) FATAL de pé, ou FATAL só com correção proposta, impede a PRIMEIRA opção. 4) Procure falhas '
    'que a acusação não viu e registre em "ataques_do_juiz"; ninguém as responde, então ficam de pé e cada GRAVE '
    'tira 5 da confiança. 5) Confiança: parta da CONFIANÇA SUGERIDA e justifique '
    'cada ajuste em "ajuste_da_confianca"; mais de 15 pontos acima da firmeza do conselho só com prova forte. '
    'Âncoras: 90+ raro (provas fortes, nada de pé, quase unanimidade); 70 a 89 veredito claro com uma lacuna; 50 a 69 '
    'uma condição ou lacuna pode inverter tudo; abaixo de 50, ninguém provou o bastante. 6) "condicoes": o que tem de '
    'ser verdade para o veredito valer, inclusive cada correção proposta. "ponto_de_virada": o fato que inverteria o '
    'veredito. "proximo_passo": a ação mais barata que mais reduz a dúvida. "criterio_de_abandono": com número e '
    'prazo. 7) "fundamentacao": por que este veredito, citando provas (P1...), o placar e onde o júri se dividiu. '
    'A SENTENÇA TEM TRÊS PARTES, como uma sentença de verdade. RELATÓRIO: o que se julgou e o que aconteceu (quem '
    'votou como, o que a acusação atacou, o que a defesa respondeu), sem opinar. FUNDAMENTOS: de 3 a 6, um por ponto '
    'que decide, do mais pesado ao mais leve, cada um com as provas (P1...) e o peso; não repita o placar como '
    'fundamento, explique POR QUE as pessoas e as provas apontam para lá. ALTERNATIVAS: para CADA opção que não '
    'venceu, por que não ela, com prova e quantos do conselho votaram nela. CONTRADITÓRIO: o que caiu e o que ficou '
    'de pé. DISPOSITIVO: a decisão em forma de sentença. Depois, a RECOMENDAÇÃO ao dono em palavras simples e a '
    'certeza em uma frase. Em "condicoes_origem", para cada condição numerada, os ataques (A1, J1...) que ela '
    'resolve. O "proximo_passo" é UMA ação curta, não um plano. '
    'Não favoreça nenhum lado nem quem conduziu o processo; não invente fato, número ou prova.')


def _contexto_juiz(autos):
    resp = {r.get('ataque'): r for r in (autos.get('defesa') or {}).get('respostas', [])}
    l = ['ATAQUES DA ACUSAÇÃO E RESPOSTAS DA DEFESA:']
    for t in (autos.get('acusacao') or {}).get('teses', []):
        r = resp.get(t.get('id')) or {}
        ch = t.get('checagem') or {}
        l.append(f'- {t.get("id")} [{(t.get("gravidade") or "").upper()}] {t["texto"]}'
                 + (f' | contraexemplo: {t["contraexemplo"]}' if t.get('contraexemplo') else '')
                 + f' | provas: {", ".join(t.get("provas") or []) or "nenhuma (alegação)"}'
                 + (f' | DEFESA {str(r.get("tipo", "")).upper()}: {r.get("texto", "")}' if r else ' | DEFESA: sem resposta')
                 + (f' | correção: {r["correcao"]}' if r.get('correcao') else '')
                 + (f' | CHECAGEM DUPLA: {ch.get("veredito")} (era {str(ch.get("gravidade_original", "")).upper()}): '
                    f'{ch.get("motivo", "")}' if ch else ''))
    d = autos.get('defesa') or {}
    l += ['', 'TESES DA DEFESA:'] + [f'- {x.get("texto", "") if isinstance(x, dict) else x}' for x in d.get('teses') or []]
    l += [f'CONDIÇÕES DA DEFESA: {"; ".join(map(str, d.get("condicoes") or []))}',
          f'TESTE BARATO DA DEFESA: {d.get("teste_barato", "")}']
    l += ['', 'PLACAR:', A.placar_md(A.placar(autos))]
    r2 = [v for v in autos.get('votos', []) if v.get('rodada') == 2]
    l += ['', 'O QUE OS 7 DO CONSELHO DISSERAM:'] + [f'- {v["voto"]}: {v.get("motivo", "")}' for v in r2]
    valor, partes = A.confianca_sugerida(dict(autos, sentenca={}))
    l += ['', f'CONFIANÇA SUGERIDA PELA RUBRICA (antes do status dos ataques): {valor}']
    l += [f'- {n}: {"+" if x >= 0 else ""}{x}' for n, x in partes]
    l.append('Desconte 5 por ataque GRAVE que você deixar de pé.')
    return l


def _teto_do_perito(autos, plano):
    """Depois de MAX_RODADAS_PERITO rodadas, pendência nova vira hipótese "não verificada" e o plano segue."""
    if plano.get('pendencias_do_perito') and autos.get('perito_rodadas', 0) >= MAX_RODADAS_PERITO:
        plano['hipoteses'] = list(plano.get('hipoteses') or []) + ['Não verificado: ' + str(x) for x in plano['pendencias_do_perito']]
        plano['pendencias_do_perito'] = []
    return plano


def briefing(caminho, papel, ident=None):
    if papel not in PAPEIS:
        raise DebateRecusado(f'papel inválido: {papel} (use {", ".join(PAPEIS)})')
    arq = _arq(caminho)
    autos = A.carregar(arq)
    caso = autos['caso']
    pasta = os.path.join(os.path.dirname(os.path.abspath(arq)), 'debate')
    nome = f'autor-{ident}.json' if papel == 'autor' else f'{papel}.json'
    destino = os.path.join(pasta, nome)
    l = [f'CASO: {caso["titulo"]}', f'PERGUNTA AO TRIBUNAL: {caso["pergunta"]}',
         f'OPÇÕES: {" | ".join(A.opcoes(autos))}',
         f'EXPLICAÇÃO: {caso.get("explicacao") or caso.get("descricao") or ""}', '', 'PROVAS ADMITIDAS:', _provas(autos), '']
    if papel == 'promotor':
        l += ['SEU PAPEL: PROMOTOR. Sustente a opção mais cautelosa e ataque o objeto (ou as finalistas). Método: '
              'pré-mortem, inversão, riscos, 2ª ordem, custo de oportunidade, taxa-base. De 3 a 6 ATAQUES, do mais forte '
              'ao mais fraco, cada um com id (A1...), gravidade (fatal: se for verdade, não cumpre o que promete ou causa '
              'dano sério; grave: compromete muito, mas tem conserto; leve: incomoda), o ponto exato ("onde"), um '
              'contraexemplo verificável e as provas (ou lista vazia = alegação). Depois, a melhor tese da defesa numa '
              'frase e a sua réplica.']
    elif papel == 'defesa':
        l += ['SEU PAPEL: DEFESA. Sustente que o objeto deve seguir, com as condições que o salvam. Método: steelman, '
              'potencial, opções escondidas, reversibilidade, o teste mais barato. De 3 a 6 teses com provas, as '
              'condições concretas e o teste barato. Depois, a melhor tese da acusação numa frase e a sua tréplica.']
    elif papel == 'replica':
        teses = (autos.get('acusacao') or {}).get('teses', [])
        if not teses:
            raise DebateRecusado('sem ataques da acusação nos autos: rode o promotor e o juntar-debate antes')
        l += ['ATAQUES DA ACUSAÇÃO:', _ataques(teses), '',
              'SEU PAPEL: RÉPLICA DA DEFESA. Para CADA ataque, "concede" (e diga a correção concreta, que vira condição) '
              'ou "rebate" (com prova ou contraexemplo verificável). Rebater só insistindo deixa o ataque de pé. Seja '
              'honesto: não rebata o que é verdade.']
    elif papel == 'autor':
        p = next((x for x in autos.get('propostas', []) if x.get('id') == ident), None)
        if not p or not p.get('carta'):
            raise DebateRecusado(f'proposta {ident} sem carta nos autos: rode propostas iniciar')
        c = p['carta']
        l += [f'STATUS QUO: {caso.get("status_quo", "")}',
              f'SUA CARTA: modo "{c["modo"]}", fluxo "{c["fluxo"]}", estratégia "{c["estrategia"]}".',
              'SEU PAPEL: AUTOR. Escreva UMA proposta. Use a carta de verdade (resposta genérica com o nome da carta '
              'por cima perde) e não cite a carta. Seja específico: o que muda, passos, prazos e como medir. O que não '
              'está nas provas vira hipótese a testar.']
    elif papel == 'checagem':
        fat = [t for t in (autos.get('acusacao') or {}).get('teses', []) if t.get('gravidade') == 'fatal']
        if not fat:
            raise DebateRecusado('sem ataque FATAL nos autos: não há o que checar')
        l += ['ATAQUES FATAIS A CHECAR:', _ataques(fat), '',
              'SEU PAPEL: VERIFICADOR INDEPENDENTE. Você não acusa nem defende. Para CADA ataque acima, refaça a checagem '
              'você mesmo: refaça as contas com os números das provas, leia o trecho exato que o ataque usa e veja se ele '
              'diz mesmo aquilo. Pergunte: é um defeito do objeto ou só de rótulo, arredondamento, texto? Decida: '
              '"confirma" (continua FATAL), "rebaixa" (é real, mas grave ou leve) ou "derruba" (não procede). '
              'Se a checagem depende de algo que não está nas provas (abrir um site, testar o app), diga isso e rebaixe '
              'para grave até o perito reconferir. Em "como_verifiquei", mostre a conta ou cite o trecho.']
    elif papel == 'juiz':
        conselho = (autos.get('juri') or {}).get('conselho') or []
        r2 = {v['jurado'] for v in autos.get('votos', []) if v.get('rodada') == 2}
        if not conselho or len(r2) < len(conselho):
            raise DebateRecusado('o conselho ainda não votou a rodada 2: rode a deliberação e o juntar antes')
        if autos.get('sentenca'):
            raise DebateRecusado('a sentença já está nos autos')
        l += _contexto_juiz(autos) + ['', INSTRUCAO_JUIZ]
    elif papel in ('plano', 'plano_ataque', 'plano_revisao'):
        s = autos.get('sentenca') or {}
        if not s:
            raise DebateRecusado('sem sentença nos autos: o juiz escreve o rascunho (veredito e condições) antes do plano')
        if papel != 'plano' and not autos.get('plano'):
            raise DebateRecusado('sem plano nos autos: rode debate --papel plano e juntar-debate antes')
        if papel == 'plano_revisao' and not autos.get('plano_ataques'):
            raise DebateRecusado('sem ataques ao plano: rode debate --papel plano_ataque e juntar-debate antes')
        l += _contexto_plano(autos, s)
        if papel == 'plano':
            l += ['', 'SEU PAPEL: REDATOR DO PLANO. ' + INSTRUCAO_PLANO]
        elif papel == 'plano_ataque':
            l += ['', 'PLANO ATUAL (JSON):', json.dumps(autos['plano'], ensure_ascii=False), '',
                  'SEU PAPEL: PROMOTOR DO PLANO. Você não julga a decisão: procura os furos que impedem o dono de executar '
                  'o plano ou de decidir com ele. Refaça as contas dos testes com os números das provas. Procure: conta errada; '
                  'meta que não fecha com o tamanho do grupo; passo que depende de algo que não existe ou não foi decidido; '
                  'critério de abandono que não decide (sem número, sem prazo, ou que nunca dispara); cenário importante que '
                  'falta; condição da sentença esquecida; certeza que não bate com as lacunas. De 3 a 6 ataques (P1...), do '
                  'mais forte ao mais fraco, com gravidade, onde, o furo e a correção sugerida. Não ataque estilo nem tamanho.']
        else:
            l += ['', 'PLANO ATUAL (JSON):', json.dumps(autos['plano'], ensure_ascii=False), '',
                  'ATAQUES AO PLANO:'] + [f'- {x.get("id")} [{(x.get("gravidade") or "").upper()}] {x.get("onde", "")}: {x.get("texto", "")} '
                                          f'| correção sugerida: {x.get("correcao_sugerida", "")}' for x in autos['plano_ataques']] + [
                  '', 'SEU PAPEL: REDATOR DO PLANO, REVISÃO. Para CADA ataque: "concede" e corrige no plano, ou "rebate" com a '
                  'conta ou a prova. Rebater só insistindo não vale. Depois grave o plano COMPLETO revisado (não escreva '
                  '"igual ao anterior"), com as mesmas regras abaixo, mais "respostas".', '', INSTRUCAO_PLANO]
    else:
        ps = [p for p in autos.get('propostas', []) if p.get('texto')]
        if not ps:
            raise DebateRecusado('sem propostas escritas nos autos: rode os autores e o juntar-debate antes')
        l += ['PROPOSTAS:'] + [f'- {p["id"]}: {p["titulo"]}. {p["texto"]}' for p in ps] + [
            '', 'SEU PAPEL: CONTRADITÓRIO DO CONCURSO. Primeiro, como PROMOTOR, faça de 2 a 4 ataques a CADA proposta '
            '(id = id da proposta + letra, gravidade, onde, contraexemplo, provas). Depois, para cada ataque, responda '
            'como o AUTOR daquela proposta: "concede" (com a correção) ou "rebate" (com prova). Seja duro e justo.']
    if papel in ('plano', 'plano_revisao') and autos.get('perito_rodadas', 0) >= MAX_RODADAS_PERITO:
        l.append('O perito já fez as rodadas de verificação permitidas: NÃO abra pendências novas; o que ainda '
                 'faltar verificar vai em "hipoteses".')
    if papel == 'plano_revisao':
        formato = FORMATO['plano'][:-1] + ',"respostas":[{"ataque":"P1","tipo":"concede|rebate","texto":"..."}]}'
    else:
        formato = FORMATO[papel] % ident if papel == 'autor' else FORMATO[papel]
    if LG.modo_valido(CS.linguagem()) == 'natural':
        l += ['', 'LINGUAGEM NATURAL: quem vai ler não conhece jargão. Frases curtas, palavras do dia a dia; nada de '
              '"pré-mortem", "taxa-base", "2ª ordem", "steelman" nem "custo de oportunidade" (diga o que querem dizer).']
    l += ['', 'SAÍDA: grave UM arquivo JSON (UTF-8) em:', destino, f'formato: {formato}',
          'Não invente fatos, números nem fontes. Depois de gravar, responda APENAS: '
          f'"OK {papel}{(" " + ident) if ident else ""}".']
    return '\n'.join(l), destino


def iniciar_propostas(caminho, n=3, semente=None):
    arq = _arq(caminho)
    autos = A.carregar(arq)
    autos['propostas'] = PR.distribuir(n, semente)
    _gravar(arq, autos)
    return [p['id'] for p in autos['propostas']]


def _gravar(arq, autos):
    with open(arq, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(autos, f, ensure_ascii=False, indent=2)
        f.write('\n')


def juntar_debate(caminho):
    """Põe nos autos o que os agentes gravaram em debate/. Devolve a lista do que entrou."""
    arq = _arq(caminho)
    autos = A.carregar(arq)
    pasta = os.path.join(os.path.dirname(os.path.abspath(arq)), 'debate')
    entrou = []

    def ler(nome):
        try:
            with open(A.longo(os.path.join(pasta, nome)), encoding='utf-8-sig') as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    d = ler('promotor.json')
    if d:
        do_juiz = [t for t in (autos.get('acusacao') or {}).get('teses', []) if t.get('do_juiz')]
        autos['acusacao'] = {'teses': d.get('teses', []) + do_juiz, 'replica': d.get('replica')}
        entrou.append('promotor')
    d = ler('defesa.json')
    if d:
        respostas = (autos.get('defesa') or {}).get('respostas')
        autos['defesa'] = {k: d.get(k) for k in ('teses', 'condicoes', 'teste_barato', 'treplica')}
        if respostas:
            autos['defesa']['respostas'] = respostas
        entrou.append('defesa')
    d = ler('replica.json')
    if d:
        autos.setdefault('defesa', {})['respostas'] = d.get('respostas', [])
        entrou.append('replica')
    por_id = {p['id']: p for p in autos.get('propostas', [])}
    for f in sorted(glob.glob(os.path.join(pasta, 'autor-*.json'))):
        d = ler(os.path.basename(f))
        if d and d.get('id') in por_id:
            por_id[d['id']].update({k: d[k] for k in ('apelido', 'titulo', 'resumo', 'texto') if k in d})
            entrou.append(f'autor {d["id"]}')
    d = ler('checagem.json')
    if d:
        por_ataque = {t.get('id'): t for t in (autos.get('acusacao') or {}).get('teses', [])}
        for i, x in d.items():
            t = por_ataque.get(i)
            if not t or not isinstance(x, dict):
                continue
            orig = (t.get('checagem') or {}).get('gravidade_original') or t.get('gravidade')
            nova = x.get('gravidade') if x.get('gravidade') in ('fatal', 'grave', 'leve') else orig
            if x.get('veredito') == 'derruba':
                nova = 'leve'
            t['checagem'] = {'veredito': x.get('veredito'), 'gravidade_original': orig, 'motivo': x.get('motivo'),
                             'como_verifiquei': x.get('como_verifiquei')}
            t['gravidade'] = nova
        entrou.append('checagem')
    d = ler('juiz.json')
    if d and not autos.get('sentenca'):
        d['por'] = JUIZ_INDEPENDENTE
        autos['sentenca'] = d
        entrou.append('sentença do juiz')
    s = autos.get('sentenca') or {}
    if s.get('por') == JUIZ_INDEPENDENTE:
        # as falhas que o juiz achou viram ataques de pé; reaplicado a cada junta, porque o promotor é relido
        s.setdefault('ataques', [])
        teses = autos.setdefault('acusacao', {}).setdefault('teses', [])
        for x in s.get('ataques_do_juiz') or []:
            if isinstance(x, dict) and x.get('id') and x['id'] not in {y.get('id') for y in teses}:
                teses.append({'id': x['id'], 'gravidade': x.get('gravidade') or 'leve', 'texto': x.get('texto', ''),
                              'do_juiz': True})
            if isinstance(x, dict) and x.get('id') and not any(y.get('ataque') == x['id'] for y in s['ataques']):
                s['ataques'].append({'ataque': x['id'], 'status': 'de_pe', 'nota': 'falha apontada pelo juiz'})
    d = ler('plano.json')
    if d and (autos.get('plano') or {}).get('versao', 1) < 2:
        autos['plano'] = _teto_do_perito(autos, d)
        s = autos.get('sentenca')
        if s and d.get('proximo_passo'):
            s['proximo_passo'] = d['proximo_passo']
        if s and d.get('criterio_de_abandono'):
            s['criterio_de_abandono'] = d['criterio_de_abandono']
        entrou.append('plano')
    d = ler('plano_ataque.json')
    if d:
        autos['plano_ataques'] = d.get('ataques', [])
        entrou.append('ataque ao plano')
    d = ler('plano_revisao.json')
    if d and autos.get('plano_ataques'):
        d['versao'] = 2
        autos['plano'] = _teto_do_perito(autos, d)
        s = autos.get('sentenca')
        if s and d.get('proximo_passo'):
            s['proximo_passo'] = d['proximo_passo']
        if s and d.get('criterio_de_abandono'):
            s['criterio_de_abandono'] = d['criterio_de_abandono']
        entrou.append('plano revisado')
    d = ler('contraditorio.json')
    if d:
        for i, x in d.items():
            if i in por_id:
                por_id[i]['ataques'] = x.get('ataques', [])
                por_id[i]['respostas'] = x.get('respostas', [])
        entrou.append('contraditorio')
    _gravar(arq, autos)
    return entrou, A.validar(autos)
