"""
O contraditório estruturado: ataques com gravidade, resposta da defesa a cada um e o veredito do juiz sobre
cada ataque. Ideia absorvida do Arena (ataque, defesa, juiz) e adaptada ao rito do Tribunal.

    acusacao.teses[]      {id: "A1", texto, provas, gravidade: fatal|grave|leve, onde, contraexemplo}
    defesa.respostas[]    {ataque: "A1", tipo: concede|rebate, texto, correcao}
    sentenca.ataques[]    {ataque: "A1", status: corrigido|correcao_proposta|rebatido|de_pe, nota, verificado}
    acusacao.teses[].checagem  {veredito: confirma|rebaixa|derruba, gravidade_original, motivo, como_verifiquei}

Regras:
- Rebater só insistindo não vale: o juiz marca "de_pe".
- Conceder e corrigir conta a favor (a correção vira condição).
- Status honesto (rito 2): "corrigido" só quando a correção já foi feita e verificada (campo "verificado" diz
  como); correção só prometida é "correcao_proposta". FATAL de pé OU só com correção proposta trava o veredito
  pleno.
- Checagem dupla (rito 2): todo ataque FATAL é reconferido por um segundo agente antes da sentença.
- Coerência (rito 2): a sentença tem um plano de ação; o plano cobre cada condição e não pode ter conflitos.
- Ataque FATAL de pé trava a opção mais favorável: o veredito não pode ser a primeira opção do caso
  (no padrão, "Procedente"). No concurso de propostas, uma proposta com FATAL de pé não pode ficar à
  frente de uma sem FATAL.
Guia: referencias/papeis.md e referencias/rubrica.md.
"""

GRAVIDADES = ('fatal', 'grave', 'leve')
RESPOSTAS = ('concede', 'rebate')
STATUS = ('corrigido', 'correcao_proposta', 'rebatido', 'de_pe')
ROTULO_STATUS = {'corrigido': 'corrigido', 'correcao_proposta': 'correção proposta', 'rebatido': 'rebatido', 'de_pe': 'DE PÉ'}
PENDENTES = ('de_pe', 'correcao_proposta')     # FATAL nestes status trava o veredito pleno
RITO_ATUAL = 3


def rito(autos):
    return autos.get('rito') or 1


def ataques(autos):
    return [t for t in (autos.get('acusacao') or {}).get('teses', []) if t.get('id')]


def status_dos_ataques(autos):
    return {x.get('ataque'): x.get('status') for x in (autos.get('sentenca') or {}).get('ataques', [])}


def fatais_de_pe(autos):
    st = status_dos_ataques(autos)
    return [t['id'] for t in ataques(autos) if t.get('gravidade') == 'fatal' and st.get(t['id']) == 'de_pe']


def fatais_pendentes(autos):
    st = status_dos_ataques(autos)
    return [t['id'] for t in ataques(autos) if t.get('gravidade') == 'fatal' and st.get(t['id']) in PENDENTES]


def fatais_sem_checagem(autos):
    return [t['id'] for t in ataques(autos)
            if (t.get('gravidade') == 'fatal' or (t.get('checagem') or {}).get('gravidade_original') == 'fatal')
            and not t.get('checagem')]


def validar(autos, opcoes):
    e = []
    ids = [t['id'] for t in ataques(autos)]
    if len(ids) != len(set(ids)):
        e.append('ids de ataque repetidos na acusação')
    for t in ataques(autos):
        g = t.get('gravidade')
        if g is not None and g not in GRAVIDADES:
            e.append(f'ataque {t["id"]}: gravidade inválida {g!r} (use {", ".join(GRAVIDADES)})')
    for r in (autos.get('defesa') or {}).get('respostas', []):
        if r.get('ataque') not in ids:
            e.append(f'defesa responde a ataque inexistente: {r.get("ataque")}')
        if r.get('tipo') not in RESPOSTAS:
            e.append(f'resposta ao ataque {r.get("ataque")}: tipo inválido {r.get("tipo")!r} (use concede ou rebate)')
    s = autos.get('sentenca') or {}
    for x in s.get('ataques', []):
        if x.get('ataque') not in ids:
            e.append(f'sentença julga ataque inexistente: {x.get("ataque")}')
        if x.get('status') not in STATUS:
            e.append(f'ataque {x.get("ataque")}: status inválido {x.get("status")!r} (use {", ".join(STATUS)})')
    fatais = fatais_pendentes(autos) if rito(autos) >= 2 else fatais_de_pe(autos)
    if s and fatais and not autos.get('propostas') and opcoes and s.get('veredito') == opcoes[0]:
        e.append(f'ataque FATAL de pé ou só com correção proposta ({", ".join(fatais)}): o veredito não pode ser "{opcoes[0]}". '
                 'Corrija o objeto (condição) ou mude o veredito')
    if rito(autos) >= 2 and s:
        for x in s.get('ataques', []):
            if x.get('status') == 'corrigido' and not x.get('verificado'):
                e.append(f'ataque {x.get("ataque")}: "corrigido" exige "verificado" (como se conferiu que a correção '
                         'foi feita); se a correção só foi prometida, use "correcao_proposta"')
        sem = fatais_sem_checagem(autos)
        if sem:
            e.append(f'FATAL sem checagem dupla ({", ".join(sem)}): rode debate --papel checagem e juntar-debate')
        e += validar_plano(autos)
    if rito(autos) >= 4 and s and s.get('por') != 'juiz independente':
        e.append('rito 4: a sentença sai do juiz independente (debate --papel juiz e juntar-debate), não de quem '
                 'conduziu o processo')
    return e


def validar_plano(autos):
    """Coerência da sentença: o plano cobre cada condição e não aponta conflitos."""
    s, p = autos.get('sentenca') or {}, autos.get('plano')
    if not p:
        return ['sentença sem plano de ação: rode debate --papel plano e juntar-debate']
    e = []
    cob = {str(k) for k in (p.get('cobertura') or {})}
    falta = [str(i + 1) for i in range(len(s.get('condicoes') or [])) if str(i + 1) not in cob]
    if falta:
        e.append(f'plano não cobre a(s) condição(ões) {", ".join(falta)} da sentença')
    if p.get('conflitos'):
        e.append('plano aponta conflito na sentença: ' + '; '.join(map(str, p['conflitos'])) + ' (corrija e rode o plano de novo)')
    if not p.get('ordem'):
        e.append('plano sem ordem de passos')
    if not p.get('recomendacao'):
        e.append('plano sem recomendação para o dono')
    if not (p.get('passo_mais_barato') or {}).get('o_que'):
        e.append('plano sem o passo mais barato (o que, custo e tempo)')
    if len(p.get('cenarios') or []) < 3:
        e.append('plano com menos de 3 cenários que mudariam a decisão')
    if rito(autos) >= 3:
        if p.get('pendencias_do_perito'):
            e.append('pendências do perito abertas: ' + '; '.join(map(str, p['pendencias_do_perito']))
                     + ' (o perito verifica, junta como prova e o plano roda de novo)')
        c = p.get('certeza') or {}
        if not (c.get('por_que') and c.get('sobe_se')):
            e.append('plano sem a certeza explicada (por_que e sobe_se)')
        if len(p.get('testes') or []) < 3:
            e.append('plano com menos de 3 testes')
        if not any(ch.isdigit() for ch in str(p.get('criterio_de_abandono') or '')):
            e.append('critério de abandono sem número')
        ids = [x.get('id') for x in autos.get('plano_ataques') or []]
        if not ids:
            e.append('plano sem ataque: rode debate --papel plano_ataque e juntar-debate')
        elif p.get('versao', 1) < 2:
            e.append('plano atacado e não revisado: rode debate --papel plano_revisao e juntar-debate')
        else:
            resp = {r.get('ataque') for r in p.get('respostas') or []}
            falta = [i for i in ids if i not in resp]
            if falta:
                e.append(f'revisão do plano sem resposta a: {", ".join(falta)}')
    return e


def ata_md(autos):
    """Seção do contraditório na ata: cada ataque, a resposta e o que o juiz decidiu."""
    ts = ataques(autos)
    if not ts:
        return ''
    resp = {r.get('ataque'): r for r in (autos.get('defesa') or {}).get('respostas', [])}
    st = status_dos_ataques(autos)
    nota = {x.get('ataque'): x.get('nota') for x in (autos.get('sentenca') or {}).get('ataques', [])}
    l = ['## Contraditório', '', '| Ataque | Gravidade | Resposta da defesa | Juiz |', '|---|---|---|---|']
    for t in ts:
        r = resp.get(t['id'])
        rr = f'**{r["tipo"]}**: {r.get("texto", "")}' if r else '_sem resposta_'
        j = ROTULO_STATUS.get(st.get(t['id']), '-')
        ch = t.get('checagem') or {}
        if ch.get('veredito') and ch.get('veredito') != 'confirma':
            j += f' (checagem: {ch["veredito"]}, era {str(ch.get("gravidade_original", "")).upper()})'
        if nota.get(t['id']):
            j += f': {nota[t["id"]]}'
        l.append(f'| {t["id"]} | {(t.get("gravidade") or "-").upper()} | {_cel(rr)} | {_cel(j)} |')
    de_pe = [i for i in st if st[i] == 'de_pe']
    l += ['', f'Ataques de pé: {", ".join(de_pe) if de_pe else "nenhum"}.' +
          (f' FATAL de pé: {", ".join(fatais_de_pe(autos))}.' if fatais_de_pe(autos) else ''), '']
    return '\n'.join(l)


def _cel(t):
    return str(t).replace('|', '\\|').replace('\n', ' ')
