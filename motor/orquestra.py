"""
Orquestração do rito, com ideias absorvidas do Arena:

- briefing idêntico: o prompt de cada lote de jurados é GERADO dos autos, nunca parafraseado pelo
  orquestrador. A ordem das opções é embaralhada por lote (contra o viés de posição).
- respostas em disco: cada subagente grava seus votos em <autos>/votos/r<rodada>-lote<k>.json e responde
  uma linha; `juntar` confere e junta nos autos. O orquestrador nunca vota no lugar de um jurado: lote que
  falhar roda de novo.
- proximo: diz a próxima fase e o comando exato (retomar depois de compactação).
- plano: estima quantos subagentes o caso vai usar, antes de começar.
"""

import glob
import json
import math
import os
import random

from . import autos as A
from . import juri as J


class OrquestraRecusada(RuntimeError):
    """O pedido de orquestração não pode seguir."""


def pasta_dos_autos(caminho):
    return caminho if os.path.isdir(caminho) else os.path.dirname(os.path.abspath(caminho))


def arquivo_dos_autos(caminho):
    return os.path.join(caminho, 'autos.json') if os.path.isdir(caminho) else caminho


def _votantes(autos, rodada):
    j = autos.get('juri') or {}
    return list(j.get('convocados') or []) + list(j.get('reforco') or []) if rodada == 1 else list(j.get('conselho') or [])


def lote_de(ids, lote, de):
    if not 1 <= lote <= de:
        raise OrquestraRecusada(f'lote {lote} fora de 1..{de}')
    k = math.ceil(len(ids) / de)
    return ids[(lote - 1) * k: lote * k]


def briefing(caminho, rodada, lote, de):
    autos = A.carregar(arquivo_dos_autos(caminho))
    dados = J.carregar_foro((autos.get('juri') or {}).get('foro') or 'brasil')
    ids = J.por_id(dados)
    votantes = _votantes(autos, rodada)
    if not votantes:
        raise OrquestraRecusada('sem jurados para esta rodada: ' +
                                ('rode juri convocar' if rodada == 1 else 'rode juri conselho'))
    meus = lote_de(votantes, lote, de)
    caso = autos['caso']
    sessao = (autos.get('juri') or {}).get('sessao', '')
    ops = list(A.opcoes(autos))
    random.Random(f'{sessao}-{rodada}-{lote}').shuffle(ops)
    destino = os.path.join(pasta_dos_autos(caminho), 'votos', f'r{rodada}-lote{lote}.json')
    provas = [p for p in autos.get('provas', []) if p.get('aceita', True)]
    l = ['Você vai interpretar, um de cada vez e de forma independente, pessoas comuns do Brasil sorteadas como '
         'juradas de um tribunal. Cada uma só sabe o que a ficha dela sabe e fala como ela fala; pode entender '
         'errado, desconfiar, achar graça, desistir. Não seja o narrador inteligente: seja a pessoa. Criança com '
         'menos de 8 anos não argumenta: descreva a reação dela, contada pelo responsável. Quem não usa internet '
         'está ouvindo alguém explicar o caso em voz alta.', '',
         f'O CASO: {caso.get("explicacao") or caso.get("descricao") or caso["titulo"]}', '']
    if provas:
        l.append('O QUE O PERITO ENCONTROU:')
        l += [f'- {p["id"]}{" (LACUNA)" if p.get("tipo") == "lacuna" else ""}: {p.get("descricao", "")}' for p in provas]
        l.append('')
    if autos.get('propostas') and rodada:
        l.append('AS PROPOSTAS FINALISTAS:')
        for p in autos['propostas']:
            if any(o.startswith(p['id'] + ':') for o in ops):
                l.append(f'- {p["id"]}: {p["titulo"]}. {p.get("resumo") or p.get("texto", "")[:400]}')
        l.append('')
    if rodada == 2:
        l.append('O QUE A ACUSAÇÃO DISSE:')
        l += [f'- {t.get("id", "")} [{(t.get("gravidade") or "").upper()}] {t["texto"]}'
              for t in (autos.get('acusacao') or {}).get('teses', [])]
        l.append('O QUE A DEFESA DISSE:')
        l += [f'- {t["texto"]}' for t in (autos.get('defesa') or {}).get('teses', [])]
        l += [f'- resposta a {r["ataque"]} ({r["tipo"]}): {r.get("texto", "")}'
              for r in (autos.get('defesa') or {}).get('respostas', [])]
        l.append('')
    l += [f'A PERGUNTA: {caso["pergunta"]}', 'OPÇÕES (copie exatamente uma): ' + ' | '.join(f'"{o}"' for o in ops), '',
          'AS FICHAS:', '']
    for i in meus:
        l.append(J.resumo(ids[i]))
        if rodada == 2:
            v1 = next((v for v in autos.get('votos', []) if v['jurado'] == i and v['rodada'] == 1), None)
            if v1:
                l.append(f'  NA SALA, ESTA PESSOA VOTOU: {v1["voto"]} ("{v1.get("motivo", "")}"). Ela pode manter ou '
                         'mudar; se mudar, diga o que a fez mudar.')
        l.append('')
    l += ['SAÍDA: grave UM arquivo JSON (UTF-8) em:', destino,
          f'com uma lista de {len(meus)} objetos: [{{"jurado":"BR-xxx","rodada":{rodada},"voto":"<opção exata>",'
          '"confianca":1-5,"motivo":"1 ou 2 frases NA VOZ da pessoa","reparou":"o que ela notou primeiro"}]',
          'Não combine votos: cada jurado é julgado como se os outros não existissem. Depois de gravar, responda '
          f'APENAS: "OK r{rodada} lote {lote}: {len(meus)} votos".']
    return '\n'.join(l), destino, meus


def juntar(caminho, arquivos=None):
    """Junta os votos gravados pelos subagentes nos autos. Devolve (n juntados, faltando por rodada, erros)."""
    arq = arquivo_dos_autos(caminho)
    autos = A.carregar(arq)
    arquivos = arquivos or sorted(glob.glob(os.path.join(pasta_dos_autos(caminho), 'votos', '*.json')))
    if not arquivos:
        raise OrquestraRecusada('nenhum arquivo de votos encontrado em votos/')
    novos, erros = [], []
    for f in arquivos:
        try:
            with open(f, encoding='utf-8-sig') as h:
                lista = json.load(h)
        except (OSError, ValueError) as x:
            erros.append(f'{os.path.basename(f)}: não li o JSON ({x})')
            continue
        for v in lista if isinstance(lista, list) else []:
            if not all(k in v for k in ('jurado', 'rodada', 'voto', 'motivo')):
                erros.append(f'{os.path.basename(f)}: voto incompleto {v}')
                continue
            novos.append({k: v[k] for k in ('jurado', 'rodada', 'voto', 'confianca', 'motivo', 'reparou') if k in v})
    chaves = {(v['jurado'], v['rodada']) for v in novos}
    autos['votos'] = [v for v in autos.get('votos', []) if (v['jurado'], v['rodada']) not in chaves] + novos
    erros += A.validar(autos)
    if any('fora das opções' in e or 'sem estar no conselho' in e or 'sem ter sido convocado' in e for e in erros):
        return 0, {}, erros
    with open(arq, 'w', encoding='utf-8', newline='\n') as h:
        json.dump(autos, h, ensure_ascii=False, indent=2)
        h.write('\n')
    faltando = {}
    for r in (1, 2):
        ja = {v['jurado'] for v in autos['votos'] if v['rodada'] == r}
        f = [i for i in _votantes(autos, r) if i not in ja]
        if f and ja and not (r == 1 and (autos.get('juri') or {}).get('rodada1_parada')):   # só rodada começada e não encerrada antes
            faltando[r] = f
    return len(novos), faltando, erros


def proximo(caminho):
    """A próxima fase do rito e o comando exato, lidos dos autos."""
    arq = arquivo_dos_autos(caminho)
    if not os.path.exists(arq):
        return 'Autuação', ['crie os autos com caso.titulo, tipo, pergunta e opções (referencias/autos.md)']
    autos = A.carregar(arq)
    j = autos.get('juri') or {}
    caso = autos.get('caso') or {}
    t = f'"{caso.get("titulo", "")}"'
    if caso.get('aberta') and not autos.get('propostas'):
        return 'Concurso de propostas', ['python tribunal.py propostas cartas --n 3',
                                         'um subagente por carta escreve a proposta (referencias/rito.md)']
    if autos.get('propostas') and not caso.get('opcoes'):
        return 'Finalistas', [f'python tribunal.py propostas placar {arq}', 'copie as opções sugeridas para caso.opcoes']
    if not j.get('convocados'):
        return 'Convocação', [f'python tribunal.py juri convocar --autos {arq} [--impedir "idade<8"]',
                              'grava a sessão e os 25 nos autos; num recurso, quem julgou o caso de origem fica de fora']
    if not j.get('conselho'):
        return 'Recusas e conselho', [f'python tribunal.py juri conselho {j.get("sessao", "SESSAO")} --acusacao IDS --defesa IDS --autos {arq}',
                                      'depois escreva o motivo de cada recusa em juri.recusas']
    if not autos.get('provas'):
        return 'Instrução (perícia)', ['o perito levanta as provas com fonte (referencias/tipos-de-caso.md)']
    votos = autos.get('votos', [])
    if len({v['jurado'] for v in votos if v['rodada'] == 1}) < len(j['convocados']) and not j.get('rodada1_parada'):
        return 'Rodada 1 (voto secreto)', [f'python tribunal.py briefing {arq} --rodada 1 --lote K --de 5  (lotes 1 a 3 primeiro, em paralelo)',
                                           f'python tribunal.py juntar {arq}',
                                           f'python tribunal.py parar {arq}  (se disser PARE, pule os lotes 4 e 5)']
    if not (autos.get('acusacao') or {}).get('teses') or not (autos.get('defesa') or {}).get('teses'):
        return 'Debates', ['promotor e defesa em paralelo, com ataques estruturados (referencias/papeis.md)']
    ids_atq = [x['id'] for x in (autos.get('acusacao') or {}).get('teses', []) if x.get('id')]
    respondidos = {r['ataque'] for r in (autos.get('defesa') or {}).get('respostas', [])}
    if ids_atq and set(ids_atq) - respondidos:
        return 'Réplica', ['a defesa concede ou rebate cada ataque: ' + ', '.join(sorted(set(ids_atq) - respondidos))]
    novo_rito = (autos.get('rito') or 1) >= 2
    fat = [t['id'] for t in (autos.get('acusacao') or {}).get('teses', []) if t.get('gravidade') == 'fatal' and not t.get('checagem')]
    if novo_rito and fat:
        return 'Checagem do FATAL', [f'python tribunal.py debate {arq} --papel checagem  (tribunal-advogado; pode rodar junto com a réplica)',
                                     f'python tribunal.py juntar-debate {arq}']
    if len({v['jurado'] for v in votos if v['rodada'] == 2}) < len(j['conselho']):
        return 'Deliberação e rodada 2', [f'python tribunal.py briefing {arq} --rodada 2 --lote 1 --de 1',
                                          f'python tribunal.py juntar {arq}']
    if not autos.get('sentenca'):
        return 'Sentença', [f'python tribunal.py placar {arq}', 'juiz: veredito, confiança pela rubrica, status de cada ataque']
    if novo_rito and not autos.get('plano'):
        return 'Plano de ação', [f'python tribunal.py debate {arq} --papel plano  (tribunal-advogado, com o rascunho da sentença)',
                                 f'python tribunal.py juntar-debate {arq}', f'python tribunal.py validar {arq}']
    if (autos.get('rito') or 1) >= 3 and (autos.get('plano') or {}).get('pendencias_do_perito'):
        return 'Pendências do perito', ['o perito verifica cada item de plano.pendencias_do_perito agora e junta o resultado como prova',
                                        'apague o plano (e debate/plano*.json) e rode debate --papel plano de novo']
    if (autos.get('rito') or 1) >= 3 and autos.get('plano') and not autos.get('plano_ataques'):
        return 'Ataque ao plano', [f'python tribunal.py debate {arq} --papel plano_ataque  (tribunal-advogado)',
                                   f'python tribunal.py juntar-debate {arq}']
    if (autos.get('rito') or 1) >= 3 and autos.get('plano_ataques') and (autos.get('plano') or {}).get('versao', 1) < 2:
        return 'Revisão do plano', [f'python tribunal.py debate {arq} --papel plano_revisao  (tribunal-advogado)',
                                    f'python tribunal.py juntar-debate {arq}', f'python tribunal.py validar {arq}',
                                    f'python tribunal.py entrega {arq}  (o que se mostra ao usuário)']
    if (autos.get('decisao_usuario') or {}).get('acatou') is None:
        return 'Instância final', ['pergunte ao usuário: acata ou recorre?']
    return 'Encerrado', [f'python tribunal.py ata {arq} -o ata.md', f'python tribunal.py visualizar {arq} --abrir',
                         f'python tribunal.py cartao enviar {arq}  (prévia; --confirmar depois do "sim")']


# Cada subagente paga um custo fixo de entrada (instruções e ferramentas do Claude Code) antes de trabalhar.
# Medido nos casos de 2026-11-09: 63 a 85 mil tokens por subagente, quase todo de entrada. Por isso o custo
# cresce com o NÚMERO de subagentes, não com o tamanho do trabalho.
TOKENS_POR_SUBAGENTE = 70_000   # general-purpose: medido de 63 a 85 mil (2026-11-09)
TOKENS_JURADO = 11_000          # agente tribunal-jurado (só Ler e Gravar, sonnet): medido de 10,6 a 10,9 mil
TOKENS_ADVOGADO = 13_000        # tribunal-advogado / tribunal-autor (só Ler e Gravar): medido de 10,4 a 15 mil (2026-11-09)
MODELO_JURADOS = 'tribunal-jurado (sonnet)'
MODELO_ADVOGADOS = 'tribunal-advogado / tribunal-autor (modelo da conversa)'
PROPOSTAS_PADRAO = 3


def plano(modo='completo', propostas=0, lotes=5):
    """[(etapa, subagentes, modelo)], total de subagentes e tokens estimados. O rápido roda tudo num contexto só."""
    if modo == 'rapido':
        return [('tudo nesta conversa, sem subagentes', 0, 'o da conversa')], 0, 0
    itens = []
    if propostas:
        itens += [(f'autores das propostas ({propostas} cartas)', propostas, MODELO_ADVOGADOS),
                  ('contraditório das propostas (ataques e respostas)', 1, MODELO_ADVOGADOS)]
    itens += [(f'rodada 1: até {lotes} lotes de jurados (3 se a parada antecipada valer)', lotes, MODELO_JURADOS),
              ('promotor e defesa', 2, MODELO_ADVOGADOS), ('réplica da defesa', 1, MODELO_ADVOGADOS),
              ('checagem dupla do FATAL (só se houver)', 1, MODELO_ADVOGADOS), ('redator do plano', 1, MODELO_ADVOGADOS),
              ('ataque e revisão do plano', 2, MODELO_ADVOGADOS),
              ('rodada 2: o conselho', 1, MODELO_JURADOS)]
    total = sum(n for _, n, _ in itens)
    tokens = sum(n * {MODELO_JURADOS: TOKENS_JURADO, MODELO_ADVOGADOS: TOKENS_ADVOGADO}.get(m, TOKENS_POR_SUBAGENTE)
                 for _, n, m in itens)
    return itens, total, tokens


def sugerir_modo(reversivel=None, impacto=None):
    """Triagem: decisão pequena e reversível não precisa de 10 subagentes. Devolve (modo, motivo)."""
    if impacto == 'alto':
        return 'completo', 'impacto alto: vale o voto independente'
    if reversivel is False:
        return 'completo', 'difícil de desfazer: vale o voto independente'
    if reversivel and impacto in ('baixo', None):
        return 'rapido', 'reversível e de impacto baixo: o modo rápido basta'
    return 'completo', 'impacto médio: o completo com jurados enxutos custa pouco'
