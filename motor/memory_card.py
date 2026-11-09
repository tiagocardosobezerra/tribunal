"""
Memory Card: o cartão de memória dos casos julgados.

Como o memory card de um videogame, cada caso julgado fica salvo (um "save"), com versão e histórico,
para ser carregado de novo quando precisar. É o mesmo cartão do Vegapunk e do Senku: um repositório git
do usuário no GitHub, privado por padrão, com uma pasta por solução. A do Tribunal é `saves/tribunal/`:

    saves/tribunal/<categoria>/<secao>/<caso>/
        README.md                 a ata com a sentença (o GitHub mostra ao abrir a pasta)
        ficha.json                versão, status, veredito, confiança, desfecho, relacionados, histórico
        autos.json                os autos do caso (a fonte de tudo)
    CATALOGO.md                   gerado a cada envio: por solução, categoria e seção (o mesmo do Vegapunk)

O Tribunal só grava a própria pasta (`saves/tribunal/`) e o `CATALOGO.md`: nunca toca nos saves de
outras soluções. A ficha segue o formato do Vegapunk (solução, categoria, seção, artigo, versão, status,
relacionados, histórico), para todos lerem o mesmo catálogo. Qual é o cartão fica só nesta instalação
(`local/memory_card.json`, fora do git e do pacote). Guia: referencias/memory-card.md.
"""

import datetime
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVES = 'saves'
SOLUCAO = 'Tribunal'
PASTA_SOLUCAO = 'tribunal'
INSTANCIA = 'tribunal'        # o `conferir` do Vegapunk pula os saves de instância que ele não tem
STATUS = ('rascunho', 'em-uso')
DESFECHOS = ('acertou', 'parcial', 'errou')
CORPO_INI, CORPO_FIM = '<!-- corpo -->', '<!-- /corpo -->'
_REPO = re.compile(r'^[\w.-]+/[\w.-]+$')
ENV_REPO, ENV_DIR = 'TRIBUNAL_MEMORY_CARD_REPO', 'TRIBUNAL_MEMORY_CARD_DIR'

README_DO_CARTAO = """# Memory Card

Cartão de memória das soluções: cada entrega pronta fica salva aqui, com versão e histórico.

Cada save fica em `saves/<solucao>/<categoria>/<secao>/<artigo>/`. A solução é a ferramenta que gerou a
entrega (o Vegapunk, o Senku, o Tribunal ou outra). Em cada pasta, o `README.md` é o artigo e o
`ficha.json` guarda versão, status, relacionados e histórico.

O [CATALOGO.md](CATALOGO.md) lista os saves por solução, categoria e seção. É gerado a cada envio: não
edite à mão. Cada mudança num save sobe a versão e exige um motivo, que entra no histórico e no commit.
"""

ONDE_FUNCIONA = ('o Memory Card só funciona onde há o `git`, o GitHub CLI (`gh`) autenticado e a pasta do '
                 'cartão: o Claude Code (ou um terminal) na máquina do usuário. Numa sandbox, como a do '
                 'claude.ai, ele não está disponível.')
OUTRA_MAQUINA = ('este Memory Card foi configurado em outra máquina (a pasta do cartão, {pasta}, não existe aqui). '
                 'Daqui não dá para ler nem enviar: entregue a ata e os autos e diga que salvar é pelo '
                 'Claude Code na máquina do cartão. Não rode `iniciar` para "consertar": isso criaria outro cartão.')


class CartaoRecusado(RuntimeError):
    """O comando do cartão não pode seguir."""


# ------------------------------------------------------------------ configuração

def caminho_config():
    return os.path.join(RAIZ, 'local', 'memory_card.json')


def _ler(caminho):
    if not caminho or not os.path.exists(caminho):
        return None
    with open(caminho, encoding='utf-8-sig') as f:
        return f.read()


def _gravar(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
        f.write(texto if texto.endswith('\n') else texto + '\n')


def configurado():
    """True quando esta instalação tem um cartão (não confere a pasta nem a rede)."""
    if os.environ.get(ENV_DIR) == '-':
        return False
    return bool(os.environ.get(ENV_REPO) or os.environ.get(ENV_DIR) or os.path.exists(caminho_config()))


def config():
    """{'repo', 'pasta', 'publico'} do cartão. `repo` None: cartão só local (git sem remoto)."""
    if not configurado():
        raise CartaoRecusado('nenhum Memory Card configurado nesta instalação. Ligue ao cartão que já existe com: '
                             'python tribunal.py cartao iniciar --repo SEU_USUARIO/memory-card')
    c = json.loads(_ler(caminho_config()) or '{}')
    repo = os.environ.get(ENV_REPO) or c.get('repo')
    if repo == '-':                                  # TRIBUNAL_MEMORY_CARD_REPO=-: cartão só local (os testes usam)
        repo = None
    pasta = os.environ.get(ENV_DIR) or c.get('pasta')
    if not pasta:
        if not repo:
            raise CartaoRecusado(f'configuração do cartão sem repositório nem pasta: {caminho_config()}')
        pasta = os.path.join(os.path.expanduser('~'), repo.split('/')[1])
    return {'repo': repo, 'pasta': os.path.abspath(pasta), 'publico': bool(c.get('publico'))}


def _pasta_e_desta_maquina(pasta):
    if re.match(r'^[A-Za-z]:[\\/]', pasta or '') and os.name != 'nt':
        return False
    return os.path.isdir(os.path.dirname(os.path.abspath(pasta)))


def disponivel():
    """(True, '') se o cartão funciona aqui; senão (False, motivo). Não usa a rede."""
    try:
        c = config()
    except CartaoRecusado as e:
        return False, str(e)
    if not os.path.isdir(os.path.join(c['pasta'], '.git')):
        if not _pasta_e_desta_maquina(c['pasta']):
            return False, OUTRA_MAQUINA.format(pasta=c['pasta'])
        return False, f'a pasta do cartão ainda não foi clonada nesta máquina ({c["pasta"]})'
    if shutil.which('git') is None:
        return False, '`git` não encontrado. ' + ONDE_FUNCIONA
    if c['repo'] and shutil.which('gh') is None:
        return False, 'GitHub CLI (`gh`) não encontrado. ' + ONDE_FUNCIONA
    return True, ''


def _rodar(args, cwd=None):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    except FileNotFoundError:
        raise CartaoRecusado(f'`{args[0]}` não encontrado. ' + ONDE_FUNCIONA)
    if r.returncode != 0:
        raise CartaoRecusado(f'{" ".join(args[:3])} falhou: {(r.stderr or r.stdout).strip()}')
    return r.stdout


def _exigir_gh():
    if shutil.which('gh') is None:
        raise CartaoRecusado('GitHub CLI (`gh`) não encontrado. ' + ONDE_FUNCIONA)
    if subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode != 0:
        raise CartaoRecusado('o `gh` não está autenticado (rode `gh auth login`). ' + ONDE_FUNCIONA)


def _visibilidade(repo):
    return json.loads(_rodar(['gh', 'repo', 'view', repo, '--json', 'visibility']))['visibility']


def conferir_privado():
    """Recusa se o cartão não for privado no GitHub (a não ser que tenha sido ligado com --publico)."""
    c = config()
    if not c['repo']:
        return
    _exigir_gh()
    vis = _visibilidade(c['repo'])
    if vis != 'PRIVATE' and not c['publico']:
        raise CartaoRecusado(f'{c["repo"]} está {vis}: o Memory Card só aceita envio com o repositório PRIVATE')


def _remoto_de(pasta):
    try:
        return _rodar(['git', 'remote', 'get-url', 'origin'], cwd=pasta).strip()
    except CartaoRecusado:
        return ''


def iniciar(repo=None, pasta=None, publico=False, substituir=False):
    """Liga esta instalação ao cartão (o mesmo do Vegapunk e do Senku): usa o repositório se ele existe
    (recusa se público), cria privado se não existe, e reaproveita um clone que já está na máquina. Sem
    `repo`, cria um cartão só local em `pasta` (git sem remoto). Só com o pedido do usuário."""
    if os.path.exists(caminho_config()) and not substituir:
        atual = json.loads(_ler(caminho_config()) or '{}')
        raise CartaoRecusado(f'esta instalação já tem um Memory Card ({atual.get("repo") or "local"}, pasta '
                             f'{atual.get("pasta")}). Para trocar, só com o pedido do usuário: iniciar ... --substituir')
    if repo:
        if not _REPO.match(repo):
            raise CartaoRecusado(f'repositório inválido: {repo!r} (use DONO/NOME)')
        _exigir_gh()
        existe = subprocess.run(['gh', 'repo', 'view', repo, '--json', 'name'], capture_output=True).returncode == 0
        if not existe:
            _rodar(['gh', 'repo', 'create', repo, '--public' if publico else '--private',
                    '--description', 'Memory Card: as entregas salvas pelas soluções (Vegapunk, Senku, Tribunal...)'])
        vis = _visibilidade(repo)
        if vis != 'PRIVATE' and not publico:
            raise CartaoRecusado(f'{repo} já existe e está {vis}: use um repositório privado '
                                 '(ou --publico, se for de propósito)')
        pasta = os.path.abspath(pasta or os.path.join(os.path.expanduser('~'), repo.split('/')[1]))
        if os.path.isdir(os.path.join(pasta, '.git')):
            remoto = _remoto_de(pasta).lower()
            if repo.lower() not in remoto:
                raise CartaoRecusado(f'a pasta {pasta} já é um clone de outro repositório ({remoto or "sem remoto"})')
        else:
            if os.path.exists(pasta) and os.listdir(pasta):
                raise CartaoRecusado(f'a pasta já existe e não está vazia: {pasta}')
            _rodar(['gh', 'repo', 'clone', repo, pasta])
    else:
        if not pasta:
            raise CartaoRecusado('sem --repo, diga a pasta do cartão local: --pasta DIR')
        pasta = os.path.abspath(pasta)
        if not os.path.isdir(os.path.join(pasta, '.git')):
            os.makedirs(pasta, exist_ok=True)
            _rodar(['git', 'init', '-q'], cwd=pasta)
    _gravar(caminho_config(), json.dumps({'repo': repo, 'pasta': pasta, 'publico': bool(publico)},
                                         ensure_ascii=False, indent=2))
    if not os.path.exists(os.path.join(pasta, 'README.md')):
        _gravar(os.path.join(pasta, 'README.md'), README_DO_CARTAO)
        _gravar(os.path.join(pasta, 'CATALOGO.md'), gerar_catalogo_md([]))
        _rodar(['git', 'add', 'README.md', 'CATALOGO.md'], cwd=pasta)
        _rodar(['git', '-c', 'user.name=Tribunal', '-c', 'user.email=tribunal@localhost', 'commit', '-q',
                '-m', 'Memory Card'] if not _tem_identidade(pasta) else ['git', 'commit', '-q', '-m', 'Memory Card'],
               cwd=pasta)
        if repo:
            _rodar(['git', 'branch', '-M', 'main'], cwd=pasta)
            _rodar(['git', 'push', '-q', '-u', 'origin', 'main'], cwd=pasta)
    return {'repo': repo, 'pasta': pasta, 'publico': bool(publico)}


def _tem_identidade(pasta):
    return subprocess.run(['git', 'config', 'user.email'], cwd=pasta, capture_output=True).returncode == 0


def preparar_pasta(atualizar=True):
    c = config()
    pasta = c['pasta']
    if not os.path.isdir(os.path.join(pasta, '.git')):
        if not _pasta_e_desta_maquina(pasta):
            raise CartaoRecusado(OUTRA_MAQUINA.format(pasta=pasta))
        if not c['repo']:
            raise CartaoRecusado(f'a pasta do cartão local não existe: {pasta}')
        _exigir_gh()
        _rodar(['gh', 'repo', 'clone', c['repo'], pasta])
    elif atualizar and c['repo']:
        try:
            _rodar(['git', 'pull', '--ff-only', '--quiet'], cwd=pasta)
        except CartaoRecusado as e:
            print(f'AVISO: não consegui atualizar o cartão ({e}); usando a cópia local.', file=sys.stderr)
    return pasta


def publicar(pasta, mensagem):
    """Gera o catálogo, faz o commit só da pasta do Tribunal e do catálogo e envia (privado antes e depois)."""
    c = config()
    conferir_privado()
    _gravar(os.path.join(pasta, 'CATALOGO.md'), gerar_catalogo_md(ler_catalogo(pasta)))
    alvo = [f'{SAVES}/{PASTA_SOLUCAO}', 'CATALOGO.md']
    _rodar(['git', 'add', '-A', '--'] + alvo, cwd=pasta)
    ident = [] if _tem_identidade(pasta) else ['-c', 'user.name=Tribunal', '-c', 'user.email=tribunal@localhost']
    _rodar(['git'] + ident + ['commit', '-q', '-m', mensagem, '--'] + alvo, cwd=pasta)
    if c['repo']:
        conferir_privado()
        _rodar(['git', 'push', '-q'], cwd=pasta)


# ------------------------------------------------------------------ fichas e catálogo (formato do Vegapunk)

def slug(texto):
    t = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii').lower()
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    if not t:
        raise CartaoRecusado(f'nome vazio depois de normalizar: {texto!r}')
    return t[:80].strip('-')


def _agora():
    return datetime.datetime.now().isoformat(timespec='seconds')


def normalizar_ficha(f):
    """Os mesmos padrões do Vegapunk: todos leem o mesmo catálogo e geram o mesmo CATALOGO.md."""
    f.setdefault('solucao', 'Vegapunk')
    f.setdefault('instancia', 'egghead')
    f.setdefault('versao', 1)
    f.setdefault('status', 'rascunho')
    f.setdefault('relacionados', [])
    f.setdefault('colunas', [])
    f.setdefault('historico', [{'versao': 1, 'data': f.get('criado_em', ''), 'motivo': 'Primeira versão'}])
    return f


def pasta_do_save(pasta, ref):
    return os.path.join(pasta, SAVES, *ref.strip('/').split('/'))


def ler_ficha(pasta, ref):
    texto = _ler(os.path.join(pasta_do_save(pasta, ref), 'ficha.json'))
    if texto is None:
        raise CartaoRecusado(f'save não encontrado: {ref}')
    return normalizar_ficha(json.loads(texto))


def gravar_ficha(pasta, ref, ficha):
    f = {k: v for k, v in ficha.items() if k != 'ref'}
    _gravar(os.path.join(pasta_do_save(pasta, ref), 'ficha.json'), json.dumps(f, ensure_ascii=False, indent=2))


def ler_catalogo(pasta):
    """Fichas de todos os saves (de todas as soluções), com `ref`, na ordem do catálogo."""
    fichas = []
    raiz = os.path.join(pasta, SAVES)
    for d, _, arqs in os.walk(raiz):
        if 'ficha.json' in arqs:
            ficha = normalizar_ficha(json.loads(_ler(os.path.join(d, 'ficha.json'))))
            ficha['ref'] = os.path.relpath(d, raiz).replace(os.sep, '/')
            fichas.append(ficha)
    return sorted(fichas, key=lambda x: (x['solucao'].lower(), x['categoria'].lower(), x['secao'].lower(),
                                         x['artigo'].lower()))


def gerar_catalogo_md(fichas):
    """Igual ao do Vegapunk, linha por linha: quem enviar por último não reescreve o catálogo do outro."""
    linhas = ['# Catálogo', '', 'Gerado pelo envio. Não edite à mão.', '']
    sol = cat = sec = None
    for f in fichas:
        if linhas[-1] and (f['solucao'] != sol or f['categoria'] != cat or f['secao'] != sec):
            linhas.append('')
        if f['solucao'] != sol:
            sol, cat, sec = f['solucao'], None, None
            linhas += [f'## {sol}', '']
        if f['categoria'] != cat:
            cat, sec = f['categoria'], None
            linhas += [f'### {cat}', '']
        if f['secao'] != sec:
            sec = f['secao']
            linhas += [f'#### {sec}', '']
        desc = f' — {f["descricao"]}' if f.get('descricao') else ''
        quebrado = ' · **conferir: schema mudou**' if (f.get('conferencia') or {}).get('ok') is False else ''
        linhas.append(f'- [{f["artigo"]}]({SAVES}/{f["ref"]}/){desc} · v{f["versao"]} · {f["status"]}{quebrado}')
    por_tabela = {}
    for f in fichas:
        for t in f.get('tabelas', []):
            por_tabela.setdefault(t, []).append(f)
    if por_tabela:
        linhas += ['', '## Por tabela', '']
        for t in sorted(por_tabela):
            linhas.append(f'- `{t}`: ' + ', '.join(f'[{f["artigo"]}]({SAVES}/{f["ref"]}/)' for f in por_tabela[t]))
    if len(linhas) > 4:
        linhas.append('')
    return '\n'.join(linhas) + '\n'


def corpo_do_readme(texto):
    if not texto or CORPO_INI not in texto:
        return None
    return texto.split(CORPO_INI, 1)[1].split(CORPO_FIM, 1)[0].strip('\n')


def _link(de_ref, para_ref):
    return '../' * len(de_ref.split('/')) + para_ref + '/'


# ------------------------------------------------------------------ o artigo (a ata)

def gerar_readme(ficha, ref, corpo, titulos):
    l = [f'# {ficha["artigo"]}', '',
         f'{ficha["solucao"]} › {ficha["categoria"]} › {ficha["secao"]} · versão {ficha["versao"]} · '
         f'{ficha["status"]}', '']
    if ficha.get('descricao'):
        l += [f'> {ficha["descricao"]}', '']
    l += [CORPO_INI, corpo.strip('\n'), CORPO_FIM, '']
    d = ficha.get('desfecho')
    l += ['## Desfecho', '']
    if d:
        l.append(f'**{d["resultado"]}** em {d["data"][:10]}: {d.get("nota") or "sem nota"}')
    else:
        l.append('Ainda sem desfecho. Volte aqui quando souber como foi: '
                 f'`python tribunal.py cartao desfecho {ref} --resultado acertou|parcial|errou --nota "..."`')
    if ficha['relacionados']:
        l += ['', '## Relacionados', '']
        l += [f'- [{titulos.get(r, r)}]({_link(ref, r)})' for r in ficha['relacionados']]
    l += ['', '## Histórico', '', '| Versão | Data | Motivo |', '|---|---|---|']
    l += [f'| {h["versao"]} | {h["data"][:10]} | {h["motivo"]} |' for h in reversed(ficha['historico'])]
    return '\n'.join(l) + '\n'


def _diff(antes, depois, nome):
    return ''.join(difflib.unified_diff((antes or '').splitlines(True), depois.splitlines(True),
                                        f'{nome} (no cartão)', f'{nome} (novo)'))


# ------------------------------------------------------------------ envio

def montar_envio(caminho_autos, pasta, categoria=None, secao=None, artigo=None, descricao=None,
                 motivo=None, status=None, relacionados=()):
    from . import autos as A
    autos = A.carregar(caminho_autos)
    erros = A.validar(autos)
    if erros:
        raise CartaoRecusado('os autos têm erro(s): ' + '; '.join(erros) +
                             f'. Corrija e rode python tribunal.py validar {caminho_autos}')
    if not autos.get('sentenca'):
        raise CartaoRecusado('o caso ainda não tem sentença: o cartão guarda casos julgados')
    if status and status not in STATUS:
        raise CartaoRecusado(f'status inválido: {status} (use {" ou ".join(STATUS)})')
    caso = autos['caso']
    categoria = (categoria or A.TIPOS.get(caso.get('tipo'), 'Outro')).strip()
    secao = (secao or caso.get('area') or 'Geral').strip()
    artigo = (artigo or caso['titulo']).strip()
    ref = '/'.join([PASTA_SOLUCAO] + [slug(x) for x in (categoria, secao, artigo)])
    destino = pasta_do_save(pasta, ref)
    anterior = ler_ficha(pasta, ref) if os.path.exists(os.path.join(destino, 'ficha.json')) else None
    if anterior and not (motivo or '').strip():
        raise CartaoRecusado(f'{ref} já existe (versão {anterior["versao"]}): diga o motivo da mudança com --motivo '
                             '(um recurso, uma prova nova, um novo julgamento)')
    catalogo = ler_catalogo(pasta)
    refs = {f['ref']: f for f in catalogo}
    for r in relacionados:
        if r == ref:
            raise CartaoRecusado('um save não se relaciona com ele mesmo')
        if r not in refs:
            raise CartaoRecusado(f'save não encontrado: {r}')
    corpo = A.ata_md(autos)
    agora = _agora()
    versao = anterior['versao'] + 1 if anterior else 1
    s = autos['sentenca']
    dec = autos.get('decisao_usuario') or {}
    ficha = {
        'solucao': SOLUCAO, 'instancia': INSTANCIA,
        'categoria': categoria, 'secao': secao, 'artigo': artigo,
        'descricao': (descricao if descricao is not None else
                      (anterior or {}).get('descricao') or str(caso.get('pergunta') or '')).strip(),
        'status': status or ('em-uso' if dec.get('acatou') is not None else 'rascunho'),
        'versao': versao,
        'caso': {k: caso.get(k) for k in ('titulo', 'tipo', 'area', 'pergunta')},
        'veredito': s.get('veredito'),
        'confianca': s.get('confianca'),
        'acatou': dec.get('acatou'),
        'juri': {'foro': autos['juri'].get('foro'), 'modo': autos['juri'].get('modo'),
                 'n': len(autos['juri'].get('jurados') or autos['juri'].get('convocados') or [])},
        'desfecho': (anterior or {}).get('desfecho'),
        'arquivos': {'autos': 'autos.json'},
        'relacionados': sorted(set((anterior or {}).get('relacionados', [])) | set(relacionados)),
        'criado_em': anterior['criado_em'] if anterior else agora, 'atualizado_em': agora,
        'historico': (anterior or {}).get('historico', []) + [
            {'versao': versao, 'data': agora, 'motivo': (motivo or 'Primeira versão').strip()}],
    }
    titulos = {f['ref']: f['artigo'] for f in catalogo}
    readme = gerar_readme(ficha, ref, corpo, titulos)
    autos_txt = json.dumps(autos, ensure_ascii=False, indent=2)
    avisos = A.avisos_de_privacidade(autos_txt)
    if dec.get('acatou') is None:
        avisos.append('o usuário ainda não disse se acata a sentença: vai como rascunho')
    return {'ref': ref, 'destino': destino, 'ficha': ficha, 'readme': readme, 'autos': autos_txt,
            'substitui': anterior is not None, 'avisos': avisos,
            'diff_readme': _diff(_ler(os.path.join(destino, 'README.md')), readme, 'README.md') if anterior else '',
            'novos_relacionados': [r for r in ficha['relacionados'] if r not in (anterior or {}).get('relacionados', [])]}


def gravar_envio(envio, pasta):
    d = envio['destino']
    if os.path.isdir(d):
        shutil.rmtree(d)                          # o save é a versão de agora: arquivo que sumiu sai junto
    os.makedirs(d)
    _gravar(os.path.join(d, 'autos.json'), envio['autos'])
    gravar_ficha(pasta, envio['ref'], envio['ficha'])
    _gravar(os.path.join(d, 'README.md'), envio['readme'])
    titulos = {f['ref']: f['artigo'] for f in ler_catalogo(pasta)}
    for r in envio['ficha']['relacionados']:       # a ligação vale nos dois sentidos
        outra = ler_ficha(pasta, r)
        if envio['ref'] not in outra['relacionados']:
            outra['relacionados'] = sorted(outra['relacionados'] + [envio['ref']])
            gravar_ficha(pasta, r, outra)
            if r.startswith(PASTA_SOLUCAO + '/'):
                _regravar_readme(pasta, r, outra, titulos)
    fi = envio['ficha']
    publicar(pasta, f'save: {fi["solucao"]} / {fi["categoria"]} / {fi["secao"]} / {fi["artigo"]} '
                    f'(v{fi["versao"]}): {fi["historico"][-1]["motivo"]}')


def _regravar_readme(pasta, ref, ficha, titulos=None):
    d = pasta_do_save(pasta, ref)
    corpo = corpo_do_readme(_ler(os.path.join(d, 'README.md'))) or ''
    titulos = titulos or {f['ref']: f['artigo'] for f in ler_catalogo(pasta)}
    _gravar(os.path.join(d, 'README.md'), gerar_readme(ficha, ref, corpo, titulos))


def _exigir_meu(ref):
    if not ref.startswith(PASTA_SOLUCAO + '/'):
        raise CartaoRecusado(f'{ref} é de outra solução: o Tribunal só mexe nos saves do Tribunal')


def marcar(pasta, ref, status):
    if status not in STATUS:
        raise CartaoRecusado(f'status inválido: {status} (use {" ou ".join(STATUS)})')
    _exigir_meu(ref)
    ficha = ler_ficha(pasta, ref)
    ficha['status'] = status
    gravar_ficha(pasta, ref, ficha)
    _regravar_readme(pasta, ref, ficha)
    publicar(pasta, f'save: {ficha["solucao"]} / {ficha["categoria"]} / {ficha["secao"]} / {ficha["artigo"]}: '
                    f'status {status}')


def desfecho(pasta, ref, resultado, nota=''):
    """Registra como a decisão foi na vida real. É o que alimenta a calibração."""
    if resultado not in DESFECHOS:
        raise CartaoRecusado(f'resultado inválido: {resultado} (use {", ".join(DESFECHOS)})')
    _exigir_meu(ref)
    ficha = ler_ficha(pasta, ref)
    ficha['desfecho'] = {'resultado': resultado, 'nota': (nota or '').strip(), 'data': _agora()}
    gravar_ficha(pasta, ref, ficha)
    _regravar_readme(pasta, ref, ficha)
    publicar(pasta, f'desfecho: {ficha["artigo"]}: {resultado}')
    return ficha


def calibracao(pasta):
    """Quanto a confiança das sentenças bateu com o desfecho. Só casos do Tribunal com desfecho.
    Brier: 0 é perfeito, 0,25 é o mesmo que chutar 50%. Acatou ou não: o usuário acerta mais que o juiz?"""
    pontos = {'acertou': 1.0, 'parcial': 0.5, 'errou': 0.0}
    casos = [f for f in ler_catalogo(pasta) if f['solucao'] == SOLUCAO and f.get('desfecho')
             and isinstance(f.get('confianca'), (int, float))]
    if not casos:
        return {'n': 0}
    faixas = {}
    brier = 0.0
    for f in casos:
        p = max(0.0, min(1.0, f['confianca'] / 100))
        y = pontos[f['desfecho']['resultado']]
        brier += (p - y) ** 2
        faixa = min(int(p * 10) * 10, 90)
        b = faixas.setdefault(faixa, [0, 0.0])
        b[0] += 1
        b[1] += y
    seguiu = [f for f in casos if f.get('acatou') is True]
    recorreu = [f for f in casos if f.get('acatou') is False]
    taxa = lambda xs: (sum(pontos[x['desfecho']['resultado']] for x in xs) / len(xs)) if xs else None
    return {'n': len(casos), 'brier': brier / len(casos),
            'faixas': {k: {'n': v[0], 'acerto': v[1] / v[0]} for k, v in sorted(faixas.items())},
            'acerto_quando_acatou': taxa(seguiu), 'acerto_quando_recorreu': taxa(recorreu)}


# ------------------------------------------------------------------ busca

_PARADAS = set('a o as os de da do das dos e em no na nos nas um uma para por com sem que ao aos the of and '
               'caso casos julgar julgamento tribunal'.split())


def _tokens(texto):
    t = unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode('ascii').lower()
    out = set()
    for w in re.findall(r'[a-z0-9]+', t):
        if w in _PARADAS or len(w) < 2:
            continue
        for fim in ('oes', 'aes', 'ais', 'eis', 'es', 's'):
            if len(w) > 4 and w.endswith(fim):
                w = w[:-len(fim)]
                break
        out.add(w)
    return out


def buscar(pasta, termos, limite=10, cobertura_minima=0.5):
    """[(pontos, ficha)] em todos os saves do cartão: artigo e descrição valem 3, solução, categoria, seção e
    veredito 2, o texto do artigo 1. Só entra o save que cobre pelo menos metade dos termos."""
    alvo = sorted(_tokens(' '.join(termos)))
    if not alvo:
        return []
    achados = []
    for f in ler_catalogo(pasta):
        d = pasta_do_save(pasta, f['ref'])
        campos = [(3, _tokens(f'{f["artigo"]} {f.get("descricao", "")}')),
                  (2, _tokens(f'{f["solucao"]} {f["categoria"]} {f["secao"]} {f.get("veredito") or ""}')),
                  (1, _tokens(corpo_do_readme(_ler(os.path.join(d, 'README.md'))) or ''))]
        pontos = cobertos = 0
        for t in alvo:
            p = sum(peso for peso, toks in campos if t in toks)
            pontos += p
            cobertos += bool(p)
        if pontos and cobertos / len(alvo) >= cobertura_minima:
            achados.append((pontos, f))
    return sorted(achados, key=lambda x: (-x[0], x[1]['ref']))[:limite]


def lembrete(texto):
    print(f'LEMBRETE: {texto}', file=sys.stderr)
