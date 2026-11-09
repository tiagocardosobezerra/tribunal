"""Testes do Tribunal. Rode da pasta da skill: python -m unittest discover -s testes"""

import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
LOCAL_TESTE = tempfile.mkdtemp(prefix='tribunal-local-')
os.environ['TRIBUNAL_LOCAL'] = LOCAL_TESTE        # nunca escrever no local/ de verdade

from motor import autos as A          # noqa: E402
from motor import casos as CS         # noqa: E402
from motor import juri as J           # noqa: E402
from motor import memory_card as MC   # noqa: E402
from motor import orquestra as O      # noqa: E402
from motor import propostas as PR     # noqa: E402
from motor import debate as DB        # noqa: E402
from motor import linguagem as LG     # noqa: E402

EXEMPLO = os.path.join(RAIZ, 'exemplos', 'autos-exemplo.json')


class Elenco(unittest.TestCase):
    def setUp(self):
        self.d = J.carregar_foro('brasil')

    def test_100_jurados_unicos_e_completos(self):
        js = self.d['jurados']
        self.assertEqual(len(js), 100)
        self.assertEqual(len({j['id'] for j in js}), 100)
        self.assertEqual(len({j['nome'].split()[0] for j in js}), 100, 'primeiro nome repetido')
        for j in js:
            for c in ('nome', 'cidade', 'ocupacao', 'historia', 'voz', 'vies', 'repara_em'):
                self.assertTrue(j.get(c), f'{j["id"]} sem {c}')
            self.assertEqual(len(j['valores']), 3, j['id'])
            if j['idade'] < J.IDADE_DE_VOZ:
                self.assertTrue(j['responsavel'], f'{j["id"]}: criança sem responsável')

    def test_de_1_a_100_anos(self):
        idades = [j['idade'] for j in self.d['jurados']]
        self.assertEqual((min(idades), max(idades)), (1, 100))

    def test_cotas_do_ibge(self):
        pior = max(abs(real - meta) for _, _, meta, real, _ in J.conferir(self.d))
        self.assertLess(pior, 1.5, f'desvio de {pior:.1f} pp contra o IBGE')


class Rodizio(unittest.TestCase):
    def setUp(self):
        self.d = J.carregar_foro('brasil')
        self.ids = J.por_id(self.d)

    def test_convocacao_justa_e_sem_clones(self):
        est, cont = {}, collections.Counter()
        for s in range(40):
            ses, est, _ = J.convocar(self.d, caso=f'c{s}', tipo='app', semente=s, estado=est)
            conv = ses['convocados']
            self.assertEqual(len(set(conv)), J.SESSAO_N)
            cont.update(conv)
            menor = min(J._distancia(self.ids[a], self.ids[b]) for a in conv for b in conv if a < b)
            self.assertGreaterEqual(menor, J.LIMIAR_CLONE)
        self.assertEqual(len(cont), 100, 'alguém nunca foi convocado')
        self.assertLessEqual(max(cont.values()) - min(cont.values()), 6, 'rodízio desequilibrado')

    def test_impedimento_de_codigo(self):
        ses, _, _ = J.convocar(self.d, tipo='codigo', semente=1, estado={})
        self.assertTrue(all(self.ids[i]['idade'] >= 12 for i in ses['convocados']))

    def test_recusas_e_conselho(self):
        ses, est, _ = J.convocar(self.d, semente=3, estado={})
        c = ses['convocados']
        with self.assertRaises(J.JuriRecusado):
            J.formar_conselho(self.d, ses['id'], c[:4], [], estado=est)
        with self.assertRaises(J.JuriRecusado):
            J.formar_conselho(self.d, ses['id'], ['BR-999'], [], estado=est)
        conselho, est = J.formar_conselho(self.d, ses['id'], c[:3], c[3:6], semente=3, estado=est)
        ids = [j['id'] for j in conselho]
        self.assertEqual(len(set(ids)), J.CONSELHO_N)
        self.assertFalse(set(ids) & set(c[:6]), 'recusado entrou no conselho')
        self.assertTrue(set(ids) <= set(c))


class Autos(unittest.TestCase):
    def test_exemplo_valido_e_placar(self):
        autos = A.carregar(EXEMPLO)
        self.assertEqual(A.validar(autos), [])
        p = A.placar(autos)
        self.assertEqual(p['n1'], 25)
        self.assertEqual(p['n2'], 7)
        self.assertEqual(p['maioria2'], autos['sentenca']['veredito'])
        self.assertEqual(len(p['mudancas']), 2)
        self.assertIn('## Sentença', A.ata_md(autos))

    def test_erros_detectados(self):
        autos = A.carregar(EXEMPLO)
        autos['votos'][0]['voto'] = 'Talvez'
        autos['sentenca']['provas_decisivas'] = ['P99']
        autos['juri']['conselho'].append('BR-001')
        erros = ' | '.join(A.validar(autos))
        for trecho in ('fora das opções', 'prova inexistente', 'não foi convocado'):
            self.assertIn(trecho, erros)


@unittest.skipIf(shutil.which('git') is None, 'sem git')
class Cartao(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix='tribunal-cartao-')
        subprocess.run(['git', 'init', '-q'], cwd=self.pasta, check=True)
        self.env = dict(os.environ, TRIBUNAL_MEMORY_CARD_REPO='-', TRIBUNAL_MEMORY_CARD_DIR=self.pasta)
        os.environ.update(TRIBUNAL_MEMORY_CARD_REPO='-', TRIBUNAL_MEMORY_CARD_DIR=self.pasta)

    def tearDown(self):
        for k in ('TRIBUNAL_MEMORY_CARD_REPO', 'TRIBUNAL_MEMORY_CARD_DIR'):
            os.environ.pop(k, None)
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_salvar_versionar_desfecho_calibrar(self):
        envio = MC.montar_envio(EXEMPLO, self.pasta)
        MC.gravar_envio(envio, self.pasta)
        ref = envio['ref']
        self.assertTrue(ref.startswith('tribunal/'))
        with self.assertRaises(MC.CartaoRecusado):
            MC.montar_envio(EXEMPLO, self.pasta)          # versão nova exige motivo
        v2 = MC.montar_envio(EXEMPLO, self.pasta, motivo='recurso: prova nova')
        self.assertEqual(v2['ficha']['versao'], 2)
        MC.gravar_envio(v2, self.pasta)
        self.assertEqual(MC.buscar(self.pasta, ['fiado'])[0][1]['ref'], ref)
        MC.desfecho(self.pasta, ref, 'acertou', 'deu certo')
        c = MC.calibracao(self.pasta)
        self.assertEqual(c['n'], 1)
        self.assertAlmostEqual(c['brier'], (0.62 - 1) ** 2)
        with open(os.path.join(self.pasta, 'CATALOGO.md'), encoding='utf-8') as f:
            self.assertIn('Caderneta digital de fiado', f.read())


class CLI(unittest.TestCase):
    def rodar(self, *args):
        r = subprocess.run([sys.executable, os.path.join(RAIZ, 'tribunal.py')] + list(args), capture_output=True,
                           text=True, encoding='utf-8', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        return r.returncode, r.stdout + r.stderr

    def test_comandos_basicos(self):
        for args in (['status'], ['juri', 'cotas'], ['juri', 'ficha', 'BR-100'], ['validar', EXEMPLO],
                     ['placar', EXEMPLO], ['juri', 'convocar', '--caso', 'x', '--simular', '--semente', '1'],
                     ['juri', 'listar', '--filtro', 'idade>=80']):
            code, out = self.rodar(*args)
            self.assertEqual(code, 0, f'{args}: {out}')
        self.assertIn('simulada', self.rodar('juri', 'convocar', '--simular')[1])


class Estatistica(unittest.TestCase):
    OPS = ['A', 'B', 'C']

    def votos(self, *pares):
        return [{'voto': o} for o, n in pares for _ in range(n)]

    def test_estabilidade(self):
        self.assertEqual(A.estabilidade(self.votos(('A', 7)), self.OPS)['estabilidade'], 1.0)
        self.assertEqual(A.estabilidade(self.votos(('A', 3), ('B', 3)), self.OPS)['estabilidade'], 0.0)
        apertado = A.estabilidade(self.votos(('A', 4), ('B', 3)), self.OPS)['estabilidade']
        folgado = A.estabilidade(self.votos(('A', 20), ('B', 5)), self.OPS)['estabilidade']
        self.assertLess(apertado, 0.8)
        self.assertGreater(folgado, 0.99)
        self.assertEqual(apertado, A.estabilidade(self.votos(('A', 4), ('B', 3)), self.OPS)['estabilidade'])  # determinístico

    def test_parada_antecipada(self):
        a = {'caso': {'opcoes': self.OPS}, 'votos': [dict(v, rodada=1) for v in self.votos(('A', 13), ('B', 2))]}
        self.assertTrue(A.parar_cedo(a)[0])
        a['votos'] = [dict(v, rodada=1) for v in self.votos(('A', 8), ('B', 7))]
        self.assertFalse(A.parar_cedo(a)[0])
        a['votos'] = [dict(v, rodada=1) for v in self.votos(('A', 10))]
        self.assertFalse(A.parar_cedo(a)[0])                               # menos de 15 votos

    def test_segmento_minimo(self):
        p = A.placar(A.carregar(EXEMPLO))
        self.assertTrue(all(x['n'] >= A.MIN_SEGMENTO for xs in p['segmentos'].values() for x in xs if x['diverge']))
        self.assertIn('estabilidade1', p)


class Confiabilidade(unittest.TestCase):
    def test_confianca_sugerida_segue_a_rubrica(self):
        a = A.carregar(EXEMPLO)                                   # conselho 4 x 2 x 1, sala concorda, 1 lacuna
        v, partes = A.confianca_sugerida(a)
        self.assertEqual(partes[0][1], 60)                       # vantagem de 2 votos
        self.assertEqual(v, 60 + 5 - 5)
        self.assertIsNone(A.confianca_sugerida({'caso': {}, 'votos': []})[0])

    def test_fidelidade_pega_jargao_de_quem_nao_usaria(self):
        a = A.carregar(EXEMPLO)
        baixo = next(j['id'] for j in J.carregar_foro('brasil')['jurados'] if j['escolaridade'].startswith('fundamental incompleto') and j['idade'] > 20)
        a['votos'] = [{'jurado': baixo, 'rodada': 1, 'voto': 'Procedente', 'motivo': 'O funil de conversão tá bom.'},
                      {'jurado': baixo, 'rodada': 2, 'voto': 'Procedente', 'motivo': 'Gostei do bolo.'}]
        termos = {t for _, _, t in A.fidelidade(a)}
        self.assertEqual(termos, {'funil', 'conversão'})


class Debate(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix='tribunal-debate-')
        self.arq = os.path.join(self.pasta, 'autos.json')
        shutil.copy(EXEMPLO, self.arq)

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_briefings_e_juntar(self):
        texto, destino = DB.briefing(self.arq, 'promotor')
        self.assertIn('PROVAS ADMITIDAS', texto)
        self.assertTrue(destino.endswith(os.path.join('debate', 'promotor.json')))
        os.makedirs(os.path.dirname(destino))
        with open(destino, 'w', encoding='utf-8') as f:
            json.dump({'teses': [{'id': 'A1', 'gravidade': 'grave', 'texto': 'x', 'provas': ['P1']}]}, f)
        self.assertIn('promotor', DB.juntar_debate(self.arq)[0])
        texto, destino = DB.briefing(self.arq, 'replica')
        self.assertIn('A1 [GRAVE]', texto)
        with open(destino, 'w', encoding='utf-8') as f:
            json.dump({'respostas': [{'ataque': 'A1', 'tipo': 'concede', 'texto': 'ok'}]}, f)
        entrou, erros = DB.juntar_debate(self.arq)
        self.assertIn('replica', entrou)
        self.assertEqual(A.carregar(self.arq)['defesa']['respostas'][0]['ataque'], 'A1')
        with self.assertRaises(DB.DebateRecusado):
            DB.briefing(self.arq, 'autor', 'X9')

    def test_propostas_iniciar_e_autor(self):
        self.assertEqual(DB.iniciar_propostas(self.arq, 3, semente=1), ['X1', 'X2', 'X3'])
        texto, destino = DB.briefing(self.arq, 'autor', 'X2')
        self.assertIn('SUA CARTA', texto)
        self.assertTrue(destino.endswith('autor-X2.json'))

    def test_reforco_entra_na_rodada_1(self):
        a = A.carregar(self.arq)
        livre = next(j['id'] for j in J.carregar_foro('brasil')['jurados'] if j['id'] not in a['juri']['convocados'])
        a['juri']['reforco'] = [livre]
        a['votos'].append({'jurado': livre, 'rodada': 1, 'voto': 'Procedente', 'motivo': 'x'})
        self.assertEqual(A.validar(a), [])
        self.assertIn(livre, O._votantes(a, 1))


class Contraditorio(unittest.TestCase):
    def autos(self):
        a = A.carregar(EXEMPLO)
        a['acusacao']['teses'] = [{'id': 'A1', 'gravidade': 'fatal', 'texto': 'x', 'provas': []},
                                  {'id': 'A2', 'gravidade': 'leve', 'texto': 'y', 'provas': []}]
        a['defesa']['respostas'] = [{'ataque': 'A1', 'tipo': 'concede', 'texto': 'corrijo'},
                                    {'ataque': 'A2', 'tipo': 'rebate', 'texto': 'P1'}]
        a['sentenca']['ataques'] = [{'ataque': 'A1', 'status': 'corrigido'}, {'ataque': 'A2', 'status': 'rebatido'}]
        return a

    def test_valido_e_ata(self):
        a = self.autos()
        self.assertEqual(A.validar(a), [])
        self.assertIn('## Contraditório', A.ata_md(a))

    def test_fatal_de_pe_trava_veredito_pleno(self):
        a = self.autos()
        a['sentenca']['ataques'][0]['status'] = 'de_pe'
        a['sentenca']['veredito'] = A.opcoes(a)[0]
        self.assertTrue(any('FATAL de pé' in e for e in A.validar(a)))
        a['sentenca']['veredito'] = A.opcoes(a)[1]
        self.assertFalse(any('FATAL de pé' in e for e in A.validar(a)))

    def test_respostas_e_status_invalidos(self):
        a = self.autos()
        a['defesa']['respostas'].append({'ataque': 'A9', 'tipo': 'talvez'})
        erros = ' | '.join(A.validar(a))
        self.assertIn('ataque inexistente', erros)
        self.assertIn('tipo inválido', erros)


class Propostas(unittest.TestCase):
    def test_cartas_sem_repetir(self):
        cs = PR.distribuir(8, semente=3)
        for parte in ('modo', 'fluxo', 'estrategia'):
            self.assertEqual(len({c['carta'][parte] for c in cs}), 8)
        self.assertEqual(PR.distribuir(4, semente=9), PR.distribuir(4, semente=9))
        with self.assertRaises(PR.PropostaRecusada):
            PR.distribuir(50)

    def test_ranking_fatal_e_status_quo(self):
        def p(i, notas, fatal=False):
            return {'id': i, 'titulo': 't' + i, 'notas': notas,
                    'ataques': [{'id': 'a', 'gravidade': 'fatal' if fatal else 'leve'}],
                    'status': [{'ataque': 'a', 'status': 'de_pe'}]}
        alto = dict(resolve=10, viabilidade=10, robustez=10, especificidade=10, clareza=10)
        medio = dict(resolve=6, viabilidade=6, robustez=6, especificidade=6, clareza=6)
        autos = {'caso': {'status_quo': 'caderno'},
                 'propostas': [p('X1', alto, fatal=True), p('X2', medio), p('X3', alto)]}
        self.assertEqual([x['id'] for x in PR.classificar(autos['propostas'])], ['X3', 'X2', 'X1'])
        self.assertEqual(PR.total(autos['propostas'][1]), 60.0)
        self.assertEqual(PR.opcoes_sugeridas(autos, 2), ['X3: tX3', 'X2: tX2', 'Status quo: caderno'])


class Orquestra(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix='tribunal-autos-')
        self.arq = os.path.join(self.pasta, 'autos.json')
        shutil.copy(EXEMPLO, self.arq)

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def gravar(self, nome, conteudo):
        os.makedirs(os.path.join(self.pasta, 'votos'), exist_ok=True)
        with open(os.path.join(self.pasta, 'votos', nome), 'w', encoding='utf-8') as f:
            json.dump(conteudo, f, ensure_ascii=False)

    def test_briefing_deterministico_e_lotes(self):
        t1, dest, ids = O.briefing(self.arq, 1, 2, 5)
        self.assertEqual(t1, O.briefing(self.arq, 1, 2, 5)[0])
        self.assertEqual(len(ids), 5)
        self.assertTrue(dest.endswith(os.path.join('votos', 'r1-lote2.json')))
        todos = sum((O.briefing(self.arq, 1, k, 5)[2] for k in range(1, 6)), [])
        self.assertEqual(sorted(todos), sorted(A.carregar(self.arq)['juri']['convocados']))

    def test_juntar_substitui_e_recusa_voto_invalido(self):
        alvo = A.carregar(self.arq)['juri']['conselho'][0]
        self.gravar('r2-lote1.json', [{'jurado': alvo, 'rodada': 2, 'voto': 'Improcedente', 'confianca': 5, 'motivo': 'mudei'}])
        n, _, _ = O.juntar(self.arq)
        self.assertEqual(n, 1)
        v = [v for v in A.carregar(self.arq)['votos'] if v['jurado'] == alvo and v['rodada'] == 2]
        self.assertEqual([x['motivo'] for x in v], ['mudei'])
        self.gravar('r2-lote1.json', [{'jurado': alvo, 'rodada': 2, 'voto': 'Talvez', 'motivo': 'x'}])
        n, _, erros = O.juntar(self.arq)
        self.assertEqual(n, 0)
        self.assertTrue(any('fora das opções' in e for e in erros))

    def test_proximo(self):
        self.assertEqual(O.proximo(self.arq)[0], 'Encerrado')
        autos = A.carregar(self.arq)
        autos['votos'] = [v for v in autos['votos'] if v['rodada'] == 1][:3]
        del autos['sentenca']
        with open(self.arq, 'w', encoding='utf-8') as f:
            json.dump(autos, f, ensure_ascii=False)
        self.assertEqual(O.proximo(self.arq)[0], 'Rodada 1 (voto secreto)')

    def test_plano(self):
        self.assertEqual(O.plano('rapido')[1:], (0, 0))
        itens, total, tokens = O.plano('completo', propostas=3)
        self.assertEqual(total, 3 + 1 + 5 + 2 + 1 + 2 + 2 + 1)
        self.assertEqual(tokens, 11 * O.TOKENS_ADVOGADO + 6 * O.TOKENS_JURADO)
        self.assertEqual(O.sugerir_modo(True, 'baixo')[0], 'rapido')
        self.assertEqual(O.sugerir_modo(True, 'alto')[0], 'completo')
        self.assertEqual(O.sugerir_modo(False, 'baixo')[0], 'completo')
        self.assertTrue(all(m == O.MODELO_JURADOS for r, _, m in itens if 'jurados' in r or 'conselho' in r))
        self.assertEqual(O.PROPOSTAS_PADRAO, 3)


class Casos(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp(prefix='tribunal-cwd-')
        for f in (CS.PREFS, CS.ULTIMO):
            if os.path.exists(f):
                os.remove(f)

    def tearDown(self):
        shutil.rmtree(self.cwd, ignore_errors=True)

    def test_novo_pasta_e_ultimo(self):
        self.assertFalse(CS.pasta_base(self.cwd)[1])                    # ainda não perguntou
        arq, decidido = CS.novo_caso('Meu caso de teste', 'ideia', cwd=self.cwd, data='2030-01-01')
        self.assertFalse(decidido)
        self.assertTrue(arq.startswith(os.path.join(self.cwd, 'tribunal-autos')))
        self.assertEqual(CS.ultimo_caso(self.cwd), os.path.abspath(arq))
        with self.assertRaises(CS.CasoRecusado):
            CS.novo_caso('Meu caso de teste', cwd=self.cwd, data='2030-01-01')
        fixa = os.path.join(self.cwd, 'fixa')
        self.assertEqual(CS.definir_pasta(fixa), os.path.abspath(fixa))
        self.assertEqual(CS.pasta_base(self.cwd), (os.path.abspath(fixa), True))

    def test_fase_metricas_e_narracao(self):
        arq = os.path.join(self.cwd, 'autos.json')
        shutil.copy(EXEMPLO, arq)
        self.assertIn('Voto secreto da sala', CS.marcar_fase(arq, 'rodada1'))
        self.assertIn('Sentença:', CS.marcar_fase(arq, 'sentenca'))
        autos = A.carregar(arq)
        self.assertIn('sentenca', autos['metricas']['fases'])
        self.assertEqual(CS.tempo_ate_sentenca(autos), 0)
        CS.registrar_abrir(arq, True)
        CS.registrar_abrir(arq, False)                                  # vale a 1ª tentativa
        self.assertTrue(A.carregar(arq)['metricas']['abrir_ok'])

    def test_comparar(self):
        a = A.carregar(EXEMPLO)
        r = CS.comparar(a, a)
        self.assertTrue(r['veredito_igual'])
        self.assertEqual(r['segmentos_iguais'], r['segmentos_comparados'])
        b = json.loads(json.dumps(a))
        b['sentenca']['veredito'] = 'Improcedente'
        self.assertFalse(CS.comparar(a, b)['veredito_igual'])


class Visual(unittest.TestCase):
    def test_sala_gerada_com_dados(self):
        pasta = tempfile.mkdtemp(prefix='tribunal-sala-')
        try:
            destino = os.path.join(pasta, 'sala.html')
            r = subprocess.run([sys.executable, os.path.join(RAIZ, 'tribunal.py'), 'visualizar', EXEMPLO, '-o', destino],
                               capture_output=True, text=True, encoding='utf-8',
                               env=dict(os.environ, PYTHONIOENCODING='utf-8'))
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(destino, encoding='utf-8') as f:
                html = f.read()
            self.assertNotIn('__DADOS__', html)
            bloco = html.split('<script id="dados" type="application/json">')[1].split('</script>')[0]
            dados = json.loads(bloco)
            self.assertEqual(len(dados['jurados']), 25)
            self.assertFalse(dados['ao_vivo'])
            self.assertIn('batida(', html)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)


class RodadaReal(unittest.TestCase):
    """Bugs achados no julgamento real de 2026-11-09."""

    def setUp(self):
        self.cwd = tempfile.mkdtemp(prefix='tribunal-real-')

    def tearDown(self):
        shutil.rmtree(self.cwd, ignore_errors=True)

    def rodar(self, *args):
        r = subprocess.run([sys.executable, os.path.join(RAIZ, 'tribunal.py')] + list(args), capture_output=True,
                           text=True, encoding='utf-8', cwd=self.cwd, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        return r.returncode, r.stdout + r.stderr

    def test_apelidos_de_campo_sao_aceitos(self):
        a = A.normalizar({'juri': {'recusas': {'acusacao': [{'id': 'BR-001', 'motivo': 'x'}]}},
                          'sentenca': {'ataques': [{'id': 'A1', 'status': 'corrigido'}]}})
        self.assertEqual(a['juri']['recusas']['acusacao'][0]['jurado'], 'BR-001')
        self.assertEqual(a['sentenca']['ataques'][0]['ataque'], 'A1')

    def test_novo_dentro_de_tribunal_autos_nao_aninha(self):
        dentro = os.path.join(self.cwd, 'tribunal-autos')
        os.makedirs(dentro)
        self.assertEqual(CS._local(dentro), os.path.abspath(dentro))
        self.assertEqual(CS._local(self.cwd), os.path.join(os.path.abspath(self.cwd), 'tribunal-autos'))

    def test_convocar_exclui_quem_ja_julgou(self):
        d = J.carregar_foro('brasil')
        fora = {j['id'] for j in d['jurados'][:60]}
        s, _, _ = J.convocar(d, excluir=fora, semente=3, estado={})
        self.assertEqual(len(s['convocados']), 25)
        self.assertFalse(fora & set(s['convocados']))

    def test_convocar_conselho_e_reforco_gravam_nos_autos(self):
        os.makedirs(os.path.join(self.cwd, 'tribunal-autos'))
        orig = os.path.join(self.cwd, 'tribunal-autos', 'origem')
        os.makedirs(orig)
        with open(os.path.join(orig, 'autos.json'), 'w', encoding='utf-8') as f:
            json.dump({'caso': {'titulo': 'o', 'pergunta': 'p?'}, 'juri': {'convocados': ['BR-050', 'BR-051']}}, f)
        rec = os.path.join(self.cwd, 'tribunal-autos', 'recurso')
        os.makedirs(rec)
        with open(os.path.join(rec, 'autos.json'), 'w', encoding='utf-8') as f:
            json.dump({'caso': {'titulo': 'r', 'tipo': 'ideia', 'pergunta': 'p?', 'recurso_de': 'origem'},
                       'juri': {'foro': 'brasil'}, 'provas': [], 'votos': []}, f)
        code, out = self.rodar('juri', 'convocar', '--autos', rec, '--json', '--semente', '5')
        self.assertEqual(code, 0, out)
        res = json.loads(out)
        self.assertTrue(res['gravado_nos_autos'])
        a = A.carregar(rec)
        self.assertEqual(a['juri']['convocados'], res['convocados'])
        self.assertFalse({'BR-050', 'BR-051'} & set(a['juri']['convocados']))
        c = a['juri']['convocados']
        code, out = self.rodar('juri', 'conselho', a['juri']['sessao'], '--acusacao', c[0], '--defesa', c[1],
                               '--autos', rec, '--semente', '1')
        self.assertEqual(code, 0, out)
        a = A.carregar(rec)
        self.assertEqual(len(a['juri']['conselho']), 7)
        self.assertEqual(a['juri']['recusas']['acusacao'][0]['jurado'], c[0])
        # reforço pela pasta (era o bug do PermissionError) e sem repetir a sala
        a['votos'] = [{'jurado': i, 'rodada': 1, 'voto': ['Procedente', 'Improcedente'][k % 2]} for k, i in enumerate(c)]
        with open(os.path.join(rec, 'autos.json'), 'w', encoding='utf-8') as f:
            json.dump(a, f)
        code, out = self.rodar('reforco', rec)
        self.assertEqual(code, 0, out)
        a = A.carregar(rec)
        self.assertEqual(len(a['juri']['reforco']), 25)
        self.assertFalse(set(a['juri']['reforco']) & set(c))

    def test_limiar_do_reforco(self):
        self.assertEqual(A.REFORCO_LIMIAR, 0.80)


class Linguagem(unittest.TestCase):
    def rodar(self, *args):
        r = subprocess.run([sys.executable, os.path.join(RAIZ, 'tribunal.py')] + list(args), capture_output=True,
                           text=True, encoding='utf-8', env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        return r.returncode, r.stdout + r.stderr

    def test_dicionario(self):
        self.assertEqual(LG.opcao('Procedente com condições', 'natural'), 'Vale, se ajustar')
        self.assertEqual(LG.opcao('Procedente com condições', 'tribunal'), 'Procedente com condições')
        self.assertEqual(LG.opcao('X1: outra coisa', 'natural'), 'X1: outra coisa')
        self.assertEqual(LG.t('conselho', 'natural'), 'Os 7 que decidem')
        self.assertEqual(LG.modo_valido('xyz'), 'tribunal')
        self.assertEqual(LG.modo_valido('natural'), 'natural')
        for k, (a, b) in LG.TERMOS.items():
            self.assertTrue(a and b, k)

    def test_ata_e_placar_simples_sem_mexer_nos_autos(self):
        def ler():
            with open(EXEMPLO, encoding='utf-8') as f:
                return f.read()
        antes = ler()
        code, out = self.rodar('ata', EXEMPLO, '--linguagem', 'natural')
        self.assertEqual(code, 0, out)
        self.assertIn('## O resultado', out)
        self.assertNotIn('Conselho de Sentença', out)
        code, out = self.rodar('placar', EXEMPLO, '--linguagem', 'natural')
        self.assertEqual(code, 0, out)
        self.assertIn('Os 7 que decidem', out)
        code, out = self.rodar('ata', EXEMPLO, '--linguagem', 'tribunal')
        self.assertIn('Conselho de Sentença', out)
        self.assertEqual(ler(), antes)

    def test_preferencia(self):
        self.assertEqual(self.rodar('linguagem', 'natural')[0], 0)
        self.assertEqual(CS.linguagem(), 'natural')
        self.assertIn('Os 7 que decidem', self.rodar('placar', EXEMPLO)[1])
        self.rodar('linguagem', 'tribunal')
        self.assertEqual(CS.linguagem(), 'tribunal')


class Rito2(unittest.TestCase):
    """Depois do duelo com a Arena: status honesto, checagem dupla do FATAL, plano e coerência."""

    def autos(self):
        with open(EXEMPLO, encoding='utf-8') as f:
            a = json.load(f)
        a['rito'] = 2
        a['acusacao'] = {'teses': [{'id': 'A1', 'gravidade': 'fatal', 'texto': 'conta errada'},
                                   {'id': 'A2', 'gravidade': 'grave', 'texto': 'caro'}]}
        a['defesa'] = dict(a.get('defesa') or {}, respostas=[{'ataque': 'A1', 'tipo': 'concede', 'texto': 'ok', 'correcao': 'arrumar'},
                                                             {'ataque': 'A2', 'tipo': 'rebate', 'texto': 'prova'}])
        a['sentenca'] = dict(a['sentenca'], veredito=A.opcoes(a)[1], condicoes=['arrumar a conta', 'testar preço'],
                             ataques=[{'ataque': 'A1', 'status': 'correcao_proposta'}, {'ataque': 'A2', 'status': 'rebatido'}])
        return a

    def test_exige_checagem_e_plano(self):
        e = ' '.join(A.validar(self.autos()))
        self.assertIn('checagem dupla', e)
        self.assertIn('sem plano', e)

    def test_corrigido_exige_verificado_e_fatal_pendente_trava_pleno(self):
        a = self.autos()
        a['sentenca']['ataques'][0]['status'] = 'corrigido'
        self.assertTrue(any('exige "verificado"' in x for x in A.validar(a)))
        a = self.autos()
        a['sentenca']['veredito'] = A.opcoes(a)[0]
        self.assertTrue(any('FATAL de pé ou só com correção proposta' in x for x in A.validar(a)))

    def test_checagem_e_plano_pelo_juntar(self):
        pasta = tempfile.mkdtemp(prefix='tribunal-rito2-')
        try:
            arq = os.path.join(pasta, 'autos.json')
            with open(arq, 'w', encoding='utf-8') as f:
                json.dump(self.autos(), f, ensure_ascii=False)
            self.assertIn('VERIFICADOR', DB.briefing(arq, 'checagem')[0])
            self.assertIn('REDATOR DO PLANO', DB.briefing(arq, 'plano')[0])
            os.makedirs(os.path.join(pasta, 'debate'))
            with open(os.path.join(pasta, 'debate', 'checagem.json'), 'w', encoding='utf-8') as f:
                json.dump({'A1': {'veredito': 'rebaixa', 'gravidade': 'grave', 'motivo': 'é rótulo', 'como_verifiquei': '4,10/0,8'}}, f)
            with open(os.path.join(pasta, 'debate', 'plano.json'), 'w', encoding='utf-8') as f:
                json.dump({'ordem': ['1. arrumar', '2. testar'], 'proximo_passo': '1. arrumar', 'cobertura': {'1': '1'}, 'conflitos': []}, f)
            entrou, erros = DB.juntar_debate(arq)
            self.assertIn('checagem', entrou)
            a = A.carregar(arq)
            self.assertEqual(a['acusacao']['teses'][0]['gravidade'], 'grave')
            self.assertEqual(a['acusacao']['teses'][0]['checagem']['gravidade_original'], 'fatal')
            self.assertEqual(a['sentenca']['proximo_passo'], '1. arrumar')
            self.assertTrue(any('condição(ões) 2' in x for x in erros), erros)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_plano_completo_e_ata(self):
        a = self.autos()
        for t in a['acusacao']['teses']:
            t['checagem'] = {'veredito': 'confirma', 'gravidade_original': t['gravidade']}
        a['plano'] = {'ordem': ['1. a', '2. b'], 'cobertura': {'1': '1', '2': '2'}, 'conflitos': [],
                      'recomendacao': 'Siga, mas arrume a conta antes.',
                      'passo_mais_barato': {'o_que': 'trocar o texto', 'custo': 'zero', 'tempo': '1 hora'},
                      'cenarios': [{'se': 'x', 'entao': 'não lançar', 'certeza': 'desce'}] * 2}
        self.assertTrue(any('menos de 3 cenários' in x for x in A.validar(a)))
        a['plano']['cenarios'] *= 2
        self.assertFalse([x for x in A.validar(a) if 'plano' in x], A.validar(a))
        md = A.plano_md(a['plano'])
        self.assertIn('Recomendação:', md)
        self.assertIn('(custo: zero; tempo: 1 hora)', md)
        self.assertIn('Comece por aqui', A.plano_md(a['plano'], natural=True))

    def test_caso_antigo_continua_valido(self):
        a = self.autos()
        a.pop('rito')
        self.assertFalse([x for x in A.validar(a) if 'checagem' in x or 'plano' in x])


class Rito3(unittest.TestCase):
    """Plano atacado e revisado, certeza explicada, testes, abandono com número e o comando entrega."""

    def test_fluxo_do_plano_e_entrega(self):
        with open(EXEMPLO, encoding='utf-8') as f:
            a = json.load(f)
        a['rito'] = 3
        a['acusacao'] = {'teses': [{'id': 'A1', 'gravidade': 'grave', 'texto': 'conta errada'}]}
        a['defesa'] = dict(a.get('defesa') or {}, respostas=[{'ataque': 'A1', 'tipo': 'concede', 'texto': 'ok', 'correcao': 'arrumar'}])
        a['sentenca'] = dict(a['sentenca'], veredito=A.opcoes(a)[1], condicoes=['arrumar a conta'],
                             ataques=[{'ataque': 'A1', 'status': 'correcao_proposta'}])
        base = {'recomendacao': 'Siga.', 'passo_mais_barato': {'o_que': 'x', 'custo': 'zero', 'tempo': '1 h'},
                'cenarios': [{'se': 'a', 'entao': 'b', 'certeza': 'sobe'}] * 3, 'ordem': ['1. a'], 'cobertura': {'1': '1'},
                'conflitos': [], 'certeza': {'por_que': 'lacuna X', 'sobe_se': 'pagarem'},
                'testes': [{'o_que': 't', 'entrada': '1', 'esperado': '2'}] * 6, 'criterio_de_abandono': 'menos de 20% em 30 dias'}
        pasta = tempfile.mkdtemp(prefix='tribunal-rito3-')
        try:
            arq = os.path.join(pasta, 'autos.json')
            deb = os.path.join(pasta, 'debate')
            os.makedirs(deb)
            with open(arq, 'w', encoding='utf-8') as f:
                json.dump(a, f, ensure_ascii=False)
            with self.assertRaises(DB.DebateRecusado):
                DB.briefing(arq, 'plano_ataque')
            with open(os.path.join(deb, 'plano.json'), 'w', encoding='utf-8') as f:
                json.dump(base, f)
            erros = DB.juntar_debate(arq)[1]
            self.assertTrue(any('plano sem ataque' in x for x in erros), erros)
            self.assertIn('PROMOTOR DO PLANO', DB.briefing(arq, 'plano_ataque')[0])
            with open(os.path.join(deb, 'plano_ataque.json'), 'w', encoding='utf-8') as f:
                json.dump({'ataques': [{'id': 'P1', 'gravidade': 'grave', 'onde': 'testes', 'texto': 'conta'}]}, f)
            erros = DB.juntar_debate(arq)[1]
            self.assertTrue(any('não revisado' in x for x in erros), erros)
            self.assertIn('"respostas"', DB.briefing(arq, 'plano_revisao')[0])
            rev = dict(base, respostas=[{'ataque': 'P1', 'tipo': 'concede', 'texto': 'ok'}], proximo_passo='1. a revisado')
            with open(os.path.join(deb, 'plano_revisao.json'), 'w', encoding='utf-8') as f:
                json.dump(rev, f)
            entrou, erros = DB.juntar_debate(arq)
            self.assertIn('plano revisado', entrou)
            self.assertFalse(erros, erros)
            a2 = A.carregar(arq)
            self.assertEqual(a2['plano']['versao'], 2)
            self.assertEqual(a2['sentenca']['proximo_passo'], '1. a revisado')
            md = A.entrega_md(a2, natural=True)
            self.assertIn('Comece por aqui', md)
            self.assertIn('Quando desistir', md)
            self.assertIn('Problemas encontrados', md)
            self.assertNotIn('reamostr', md)
            enx = A.entrega_md(a2, enxuta=True)
            self.assertNotIn('Vozes do conselho', enx)
            self.assertNotIn('tribunal.py ata', enx)
            self.assertIn('Problemas encontrados', enx)
            a2['plano']['pendencias_do_perito'] = ['abrir o site e ver a frase']
            self.assertTrue(any('pendências do perito' in x for x in A.validar(a2)))
            self.assertIn('pendencias_do_perito', DB.briefing(arq, 'plano')[0])
        finally:
            shutil.rmtree(pasta, ignore_errors=True)


class Versao14(unittest.TestCase):
    """Júri com 3 modelos, comando onda e validação contra casos de desfecho conhecido."""

    def test_modelos_e_blocos(self):
        ops = ['Procedente', 'Procedente com condições', 'Improcedente']
        self.assertEqual([O.modelo_do_lote(k)[0] for k in (1, 2, 3, 4)], ['sonnet', 'haiku', 'opus', 'sonnet'])
        vs = ([{'voto': 'Procedente', 'modelo': 'sonnet', 'lote': 1}] * 5 + [{'voto': 'Procedente', 'modelo': 'haiku', 'lote': 2}] * 5
              + [{'voto': 'Improcedente', 'modelo': 'opus', 'lote': 3}] * 5)
        det, concordam = A.por_modelo(vs, ops)
        self.assertFalse(concordam)
        self.assertEqual(det['opus']['maioria'], 'Improcedente')
        b = A.estabilidade_blocos(vs, ops)
        self.assertLess(b, A.estabilidade(vs, ops)['estabilidade'])
        self.assertIsNone(A.estabilidade_blocos(vs[:10], ops))

    def test_onda_e_juntar_marcam_modelo(self):
        pasta = tempfile.mkdtemp(prefix='tribunal-onda-')
        try:
            with open(EXEMPLO, encoding='utf-8') as f:
                a = json.load(f)
            a['votos'] = []
            for k in ('acusacao', 'defesa', 'sentenca'):
                a.pop(k, None)
            arq = os.path.join(pasta, 'autos.json')
            with open(arq, 'w', encoding='utf-8') as f:
                json.dump(a, f, ensure_ascii=False)
            fase, ch, _ = O.onda(arq)
            self.assertTrue(fase.startswith('Rodada 1'))
            self.assertEqual([c['subagent_type'] for c in ch], ['tribunal-jurado', 'tribunal-jurado-haiku', 'tribunal-jurado-opus'])
            self.assertTrue(os.path.exists(os.path.join(pasta, 'briefings', 'r1-lote2.txt')))
            _, _, meus = O.briefing(arq, 1, 2, 5)
            with open(os.path.join(pasta, 'votos', 'r1-lote2.json'), 'w', encoding='utf-8') as f:
                json.dump([{'jurado': i, 'rodada': 1, 'voto': 'Procedente', 'motivo': 'ok'} for i in meus], f)
            linhas = O.onda_juntar(arq)
            self.assertTrue(any('PRÓXIMA FASE' in x for x in linhas))
            v = [x for x in A.carregar(arq)['votos'] if x['rodada'] == 1]
            self.assertTrue(v and all(x['modelo'] == 'haiku' and x['lote'] == 2 for x in v))
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_validacao(self):
        from motor import validacao as V
        pasta = tempfile.mkdtemp(prefix='tribunal-val-')
        try:
            casos = V.carregar_casos(os.path.join(RAIZ, 'validacao', 'casos.json'))[:2]
            ch = V.preparar(pasta, casos, lotes=2)
            self.assertEqual(len(ch), 4)
            for c, votos in zip(casos, (['Procedente'] * 4 + ['Improcedente'], ['Improcedente'] * 5)):
                arq = os.path.join(pasta, c['id'], 'autos.json')
                for k in (1, 2):
                    _, _, meus = O.briefing(arq, 1, k, 2)
                    with open(os.path.join(pasta, c['id'], 'votos', f'r1-lote{k}.json'), 'w', encoding='utf-8') as f:
                        json.dump([{'jurado': i, 'rodada': 1, 'voto': v, 'motivo': 'x', 'reconhece': ''} for i, v in zip(meus, votos)], f)
            r = V.resultado(pasta, casos)
            self.assertEqual(r['n'], 2)
            self.assertIn('Validação do júri', V.resultado_md(r))
        finally:
            shutil.rmtree(pasta, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
