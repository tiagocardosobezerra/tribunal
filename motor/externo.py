"""
Jurado de outra família de modelos, por qualquer API compatível com a da OpenAI (OpenRouter, Ollama local, Groq,
LM Studio...). Cópias do mesmo modelo pensam parecido: um lote fora da família Claude dá diversidade de verdade.

É opcional e sai da máquina: o briefing (o caso e as provas) vai para o provedor configurado. Por isso só liga
quando o usuário define as variáveis de ambiente, e nunca guarda a chave nos autos.

    TRIBUNAL_EXTERNO_MODELO   o modelo (ex.: openai/gpt-5-mini no OpenRouter, qwen3:8b no Ollama)  [obrigatório]
    TRIBUNAL_EXTERNO_URL      a base da API (padrão: OpenRouter; Ollama: http://localhost:11434/v1)
    TRIBUNAL_EXTERNO_CHAVE    a chave (ou OPENROUTER_API_KEY); dispensável em servidor local

    configurado()                 -> {'modelo', 'url', 'chave'} ou None
    votar(briefing, destino)      -> quantos votos gravou em destino
"""

import json
import os
import urllib.error
import urllib.request

from . import autos as A

OPENROUTER = 'https://openrouter.ai/api/v1'
SISTEMA = ('Você é um jurado do Tribunal. Você não tem ferramentas: não grava arquivos. Leia o briefing e responda '
           'APENAS com o conteúdo JSON que o briefing manda gravar (a lista de votos), sem texto antes ou depois.')


class ExternoFalhou(RuntimeError):
    """O provedor externo não respondeu ou não devolveu votos válidos."""


def configurado():
    modelo = os.environ.get('TRIBUNAL_EXTERNO_MODELO', '').strip()
    if not modelo:
        return None
    url = os.environ.get('TRIBUNAL_EXTERNO_URL', '').strip().rstrip('/') or OPENROUTER
    chave = os.environ.get('TRIBUNAL_EXTERNO_CHAVE') or os.environ.get('OPENROUTER_API_KEY') or ''
    return {'modelo': modelo, 'url': url, 'chave': chave}


def _json_da_resposta(texto):
    """O primeiro JSON (lista ou objeto) dentro do texto, ignorando cercas de código e comentários."""
    dec = json.JSONDecoder()
    for i, ch in enumerate(texto):
        if ch in '[{':
            try:
                obj, _ = dec.raw_decode(texto[i:])
                return obj
            except ValueError:
                continue
    raise ExternoFalhou('a resposta não tem JSON')


def _pedir(cfg, briefing_txt, tempo=180):
    corpo = json.dumps({'model': cfg['modelo'], 'messages': [{'role': 'system', 'content': SISTEMA},
                                                             {'role': 'user', 'content': briefing_txt}]}).encode('utf-8')
    cab = {'Content-Type': 'application/json'}
    if cfg['chave']:
        cab['Authorization'] = 'Bearer ' + cfg['chave']
    req = urllib.request.Request(cfg['url'] + '/chat/completions', data=corpo, headers=cab, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=tempo) as r:
            d = json.loads(r.read().decode('utf-8'))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ExternoFalhou(f'o provedor não respondeu: {e}') from None
    try:
        return d['choices'][0]['message']['content'] or ''
    except (KeyError, IndexError, TypeError):
        raise ExternoFalhou('resposta fora do formato de chat completions') from None


def votar(briefing, destino, cfg=None):
    cfg = cfg or configurado()
    if not cfg:
        raise ExternoFalhou('defina TRIBUNAL_EXTERNO_MODELO (e a URL e a chave, se precisar)')
    with open(A.longo(briefing), encoding='utf-8') as f:
        txt = f.read()
    obj = _json_da_resposta(_pedir(cfg, txt))
    votos = obj.get('votos') if isinstance(obj, dict) else obj
    if not isinstance(votos, list) or not votos or not all(isinstance(v, dict) and v.get('jurado') for v in votos):
        raise ExternoFalhou('o JSON não é uma lista de votos com "jurado"')
    for v in votos:
        v['modelo'] = 'externo:' + cfg['modelo']
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    with open(A.longo(destino), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(votos, f, ensure_ascii=False, indent=2)
    return len(votos)
