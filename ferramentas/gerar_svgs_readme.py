"""Gera os SVGs animados do README do Tribunal.

Tudo embutido (fontes em subconjunto WOFF, imagem em JPEG), só CSS, sem script:
o GitHub mostra o SVG como <img>, e assim ele anima.
uso: python -I gerar.py <pasta_fontes> <juri-min.json> <sala.jpg> <saida>
"""
import base64, io, json, sys, os
from xml.sax.saxutils import escape
from fontTools.ttLib import TTFont
from fontTools import subset

FD, JURI, SALA, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)

C = dict(bg='#0f0c14', bg2='#130f1a', panel='#16111e', surface='#1e1828', surface2='#271f33', line='#2b2339',
         line2='#3d3252', ink='#f4eee3', muted='#b0a5c0', faint='#7d7290', gold='#e8c15a', gold2='#b8922f',
         acc='#d97757', ok='#5cc26b', no='#e0574f', wood='#3a2618', blue='#6aa7e8')

FONTS = {  # família css -> arquivo
    'I4': 'inter-400.ttf', 'I6': 'inter-600.ttf', 'I8': 'inter-800.ttf', 'PX': 'pixel-700.ttf', 'SF': 'serif-i.ttf'}
_tt = {k: TTFont(os.path.join(FD, v)) for k, v in FONTS.items()}


def width(txt, fam, size, ls=0.0):
    f = _tt[fam]; cmap = f.getBestCmap(); hm = f['hmtx']; upm = f['head'].unitsPerEm
    w = 0
    for ch in txt:
        g = cmap.get(ord(ch)) or cmap.get(ord('?'))
        w += hm[g][0]
    return w * size / upm + ls * len(txt)


def wrap(txt, fam, size, maxw):
    out, cur = [], ''
    for word in txt.split(' '):
        t = (cur + ' ' + word).strip()
        if width(t, fam, size) <= maxw or not cur:
            cur = t
        else:
            out.append(cur); cur = word
    if cur: out.append(cur)
    return out


class SVG:
    def __init__(self, w, h, T, title):
        self.w, self.h, self.T, self.title = w, h, T, title
        self.body, self.css, self.used, self.n = [], [], {k: set() for k in FONTS}, 0

    def id(self, p='a'):
        self.n += 1; return f'{p}{self.n}'

    def add(self, s): self.body.append(s)

    def text(self, x, y, txt, fam='I4', size=16, fill=C['ink'], anchor='start', ls=0, extra=''):
        self.used[fam].update(txt)
        a = f' text-anchor="{anchor}"' if anchor != 'start' else ''
        l = f' letter-spacing="{ls}"' if ls else ''
        return f'<text x="{x:.1f}" y="{y:.1f}" class="{fam}" font-size="{size}" fill="{fill}"{a}{l}{extra}>{escape(txt)}</text>'

    def para(self, x, y, txt, fam, size, maxw, lh, fill):
        lines = wrap(txt, fam, size, maxw)
        return ''.join(self.text(x, y + i * lh, ln, fam, size, fill) for i, ln in enumerate(lines)), len(lines)

    # ---- animação: keyframes por elemento, todos no mesmo ciclo T
    def kf(self, frames, ease='cubic-bezier(.2,.8,.2,1)', extra=''):
        name = self.id('k')
        pts = []
        for t, css in frames:
            pct = max(0, min(100, t / self.T * 100))
            pts.append(f'{pct:.3f}%{{{css}}}')
        self.css.append(f'@keyframes {name}{{{"".join(pts)}}}')
        cls = self.id('c')
        self.css.append(f'.{cls}{{animation:{name} {self.T}s {ease} infinite both;{extra}}}')
        return cls

    def show(self, t, dur=.5, dy=14, sx=None, out=None):
        """aparece em t, fica até o fim do ciclo"""
        T = self.T; out = T - .55 if out is None else out
        hid = f'opacity:0;transform:translate(0,{dy}px)' + (f' scale({sx})' if sx else '')
        vis = 'opacity:1;transform:translate(0,0)' + (' scale(1)' if sx else '')
        return self.kf([(0, hid), (t, hid), (t + dur, vis), (out, vis), (out + .4, 'opacity:0;transform:translate(0,0)' + (' scale(1)' if sx else '')), (T, 'opacity:0')],
                       extra='transform-box:fill-box;transform-origin:center' if sx else '')

    def grow(self, t, dur=1.1, origin='left center'):
        T = self.T
        return self.kf([(0, 'transform:scaleX(0)'), (t, 'transform:scaleX(0)'), (t + dur, 'transform:scaleX(1)'), (T - .55, 'transform:scaleX(1)'), (T - .15, 'transform:scaleX(0)'), (T, 'transform:scaleX(0)')],
                       extra=f'transform-box:fill-box;transform-origin:{origin}')

    def ring(self, cx, cy, r, sw, p, t, label_size=20):
        circ = 2 * 3.14159265 * r; off = circ * (1 - p)
        cls = self.kf([(0, f'stroke-dashoffset:{circ:.1f}'), (t, f'stroke-dashoffset:{circ:.1f}'), (t + 1.4, f'stroke-dashoffset:{off:.1f}'),
                       (self.T - .55, f'stroke-dashoffset:{off:.1f}'), (self.T - .1, f'stroke-dashoffset:{circ:.1f}'), (self.T, f'stroke-dashoffset:{circ:.1f}')])
        return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#1d1627" stroke="{C["line2"]}" stroke-width="{sw}"/>'
                f'<circle class="{cls}" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{C["gold"]}" stroke-width="{sw}" stroke-linecap="butt" '
                f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}" transform="rotate(-90 {cx} {cy})"/>'
                + self.text(cx, cy + label_size * .36, f'{round(p*100)}%', 'I8', label_size, C['ink'], 'middle'))

    def render(self, name):
        faces = []
        fam_css = {'I4': ("'TI4'", 400), 'I6': ("'TI6'", 600), 'I8': ("'TI8'", 800), 'PX': ("'TPX'", 700), 'SF': ("'TSF'", 400)}
        for fam, chars in self.used.items():
            if not chars: continue
            opts = subset.Options(); opts.flavor = 'woff'; opts.layout_features = ['kern']; opts.name_IDs = []; opts.notdef_outline = True
            f = TTFont(os.path.join(FD, FONTS[fam]))
            s = subset.Subsetter(opts); s.populate(text=''.join(chars) + ' '); s.subset(f)
            b = io.BytesIO(); f.flavor = 'woff'; f.save(b)
            faces.append(f"@font-face{{font-family:{fam_css[fam][0]};src:url(data:font/woff;base64,{base64.b64encode(b.getvalue()).decode()}) format('woff')}}")
        cls = ''.join(f".{k}{{font-family:{v[0]},sans-serif;{'font-style:italic;' if k=='SF' else ''}font-variant-ligatures:none;font-feature-settings:'liga' 0}}" for k, v in fam_css.items())
        css = ''.join(faces) + cls + ''.join(self.css) + '@media (prefers-reduced-motion:reduce){*{animation:none!important}}'
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" role="img">'
               f'<title>{escape(self.title)}</title><style>{css}</style>'
               f'<rect width="{self.w}" height="{self.h}" rx="18" fill="{C["bg"]}"/>' + ''.join(self.body) + '</svg>')
        p = os.path.join(OUT, name + '.svg'); open(p, 'w', encoding='utf-8').write(svg)
        print(name, f'{len(svg)//1024} KB')


def card(x, y, w, h, fill=C['panel'], stroke=C['line'], rx=14, extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"{extra}/>'


def avatar(x, y, s, body, hat):
    rows = ['..HHHH..', '.HHHHHH.', '.SSSSSS.', '.SESSES.', '.SSSSSS.', '..SMMS..', '.BBBBBB.', 'BBBBBBBB']
    pal = {'H': hat, 'S': '#f0b48a', 'E': '#1a1220', 'M': '#b5654a', 'B': body}
    r = ''.join(f'<rect x="{x+i*s}" y="{y+j*s}" width="{s}" height="{s}" fill="{pal[c]}"/>' for j, row in enumerate(rows) for i, c in enumerate(row) if c in pal)
    return f'<g shape-rendering="crispEdges">{r}</g>'


# ------------------------------------------------------------------ 1. abertura
def hero():
    W, H, T = 1200, 600, 11
    s = SVG(W, H, T, 'Tribunal: antes de apostar numa ideia, leve-a a julgamento')
    s.add(f'<defs><radialGradient id="luz" cx=".5" cy="0" r=".8"><stop offset="0" stop-color="{C["gold"]}" stop-opacity=".14"/><stop offset="1" stop-color="{C["gold"]}" stop-opacity="0"/></radialGradient>'
          f'<clipPath id="cf"><rect x="640" y="132" width="512" height="320" rx="0"/></clipPath></defs>'
          f'<rect width="{W}" height="{H}" rx="18" fill="url(#luz)"/>')
    # selo
    c = s.show(.1, dy=8)
    s.add(f'<g class="{c}">{card(48, 44, 330, 34, C["panel"], C["line2"], 17)}<rect x="54" y="50" width="62" height="22" rx="11" fill="{C["gold"]}"/>'
          + s.text(85, 66, 'v1.8.2', 'I8', 13, '#1a1220', 'middle') + s.text(126, 66, 'Skill gratuita para o Claude Code', 'I4', 15, C['muted']) + '</g>')
    # título
    for i, (ln, col) in enumerate([('Antes de apostar', C['ink']), ('numa ideia, leve-a', C['ink']), ('a julgamento.', None)]):
        c = s.show(.35 + i * .35, dy=18)
        y = 152 + i * 62
        if col:
            s.add(f'<g class="{c}">' + s.text(48, y, ln, 'PX', 54, col) + '</g>')
        else:
            wa = width('a ', 'PX', 54)
            s.add(f'<g class="{c}">' + s.text(48, y, 'a ', 'PX', 54, C['ink']) + s.text(48 + wa, y, 'julgamento.', 'PX', 54, C['gold']) + '</g>')
            wj = width('julgamento.', 'PX', 54)
            g = s.grow(1.6, .9)
            s.add(f'<rect class="{g}" x="{48+wa:.0f}" y="{y+10}" width="{wj:.0f}" height="6" fill="url(#dash)"/>')
            s.add(f'<defs><pattern id="dash" width="9" height="6" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="{C["gold2"]}"/></pattern></defs>')
    c = s.show(1.5)
    t, n = s.para(48, 346, 'Em vez da opinião de uma IA, um processo: um perito traz provas com fonte, um promotor ataca, a defesa responde e um júri de 100 brasileiros calibrados pelo IBGE vota em segredo. No fim, uma sentença com plano, certeza medida e a hora certa de desistir.', 'I4', 18, 540, 28, C['muted'])
    s.add(f'<g class="{c}">{t}</g>')
    # botões
    c = s.show(2.0)
    bw = width('Assistir a um julgamento', 'I8', 16) + 64
    s.add(f'<g class="{c}"><rect x="48" y="514" width="{bw:.0f}" height="52" rx="10" fill="{C["gold2"]}"/><rect x="48" y="510" width="{bw:.0f}" height="52" rx="10" fill="{C["gold"]}"/>'
          f'<path d="M70 526l13 9-13 9z" fill="#1a1220"/>' + s.text(94, 541, 'Assistir a um julgamento', 'I8', 16, '#1a1220')
          + f'<rect x="{60+bw:.0f}" y="510.5" width="226" height="51" rx="10" fill="none" stroke="{C["line2"]}"/>' + s.text(60 + bw + 113, 541, 'Instalar em 2 comandos', 'I8', 16, C['ink'], 'middle') + '</g>')
    # moldura da sala
    c = s.show(.6, dy=24)
    jpg = base64.b64encode(open(SALA, 'rb').read()).decode()
    live = 'pulsa'
    s.css.append('@keyframes kp{50%{opacity:.25}}.pulsa{animation:kp 1.2s steps(1) infinite}')
    s.add(f'<g class="{c}">' + card(628, 96, 536, 368, C['panel'], C['line2'], 14) + f'<rect x="629" y="97" width="534" height="34" rx="13" fill="{C["bg2"]}"/><rect x="629" y="118" width="534" height="14" fill="{C["bg2"]}"/>'
          + ''.join(f'<circle cx="{648+i*15}" cy="114" r="4.5" fill="{C["line2"]}"/>' for i in range(3))
          + s.text(694, 119, 'Caderneta digital de fiado · voto secreto', 'I4', 12.5, C['faint'])
          + f'<circle class="{live}" cx="1080" cy="114" r="4.5" fill="{C["no"]}"/>' + s.text(1090, 119, 'AO VIVO', 'I8', 12, C['no'], ls=.6)
          + f'<image x="640" y="132" width="512" height="320" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{jpg}" clip-path="url(#cf)"/></g>')
    # malhete batendo 3 vezes
    hits = []
    for k in range(3):
        b = 3.6 + k * .42
        hits += [(b, 'transform:rotate(-34deg)'), (b + .16, 'transform:rotate(6deg)'), (b + .24, 'transform:rotate(0deg)')]
    gv = s.kf([(0, 'opacity:0;transform:rotate(-34deg)'), (3.1, 'opacity:0;transform:rotate(-34deg)'), (3.4, 'opacity:1;transform:rotate(-34deg)')] + hits
              + [(T - .55, 'opacity:1;transform:rotate(0deg)'), (T - .15, 'opacity:0;transform:rotate(0deg)'), (T, 'opacity:0')],
              ease='ease-in', extra='transform-box:fill-box;transform-origin:80% 85%')
    s.add(f'<g transform="translate(596 64) scale(3.6)" shape-rendering="crispEdges"><g class="{gv}"><g transform="rotate(-38 12 12)"><rect x="5" y="4" width="11" height="6" fill="#e8c15a"/>'
          f'<rect x="5" y="4" width="11" height="1" fill="#f6dc8a"/><rect x="4" y="5" width="1" height="4" fill="#b8922f"/><rect x="16" y="5" width="1" height="4" fill="#b8922f"/>'
          f'<rect x="9" y="10" width="3" height="11" fill="#8a5a33"/><rect x="9" y="10" width="1" height="11" fill="#a8703f"/></g></g></g>')
    # cartão da sentença
    c = s.show(4.9, dy=26)
    s.add(f'<g class="{c}">' + card(856, 372, 316, 196, '#1d1627', C['line2'], 14)
          + s.ring(912, 432, 30, 7, .62, 5.1, 17)
          + s.text(958, 424, 'VEREDITO', 'I8', 11.5, C['gold'], ls=1.4) + s.text(958, 448, 'Vale, se ajustar', 'PX', 20, C['ink'])
          + f'<line x1="876" y1="486" x2="1152" y2="486" stroke="{C["line2"]}" stroke-dasharray="4 4"/>'
          + s.text(876, 514, 'Quando desistir:', 'I8', 14.5, C['ink']) + s.text(876 + width('Quando desistir: ', 'I8', 14.5), 514, 'se em 60 dias nenhum', 'I4', 14.5, C['muted'])
          + s.text(876, 536, 'dono aceitar pagar R$ 20 por mês.', 'I4', 14.5, C['muted']) + '</g>')
    st = s.show(5.4, dur=.35, dy=0, sx=1.6)
    s.add(f'<g transform="rotate(4 1110 372)"><g class="{st}"><rect x="1060" y="358" width="100" height="26" rx="5" fill="#8d4a33"/><rect x="1060" y="355" width="100" height="26" rx="5" fill="{C["acc"]}"/>'
          + s.text(1110, 373, 'SENTENÇA', 'PX', 13, '#1a1220', 'middle', ls=1) + '</g></g>')
    s.render('hero')


# ------------------------------------------------------------------ 2. sentença de exemplo
def sentenca():
    W, H, T = 1200, 600, 15
    s = SVG(W, H, T, 'Exemplo: a pergunta e a sentença do Tribunal')
    c = s.show(.2)
    s.add(f'<g class="{c}">' + card(40, 40, 470, 118, C['surface'], C['line2'], 16) + s.text(66, 74, 'VOCÊ', 'I8', 12.5, C['faint'], ls=.8))
    t, _ = s.para(66, 104, 'Leva a julgamento o meu app de caderneta de fiado para mercadinhos de bairro.', 'I4', 20, 420, 30, C['ink'])
    s.add(t + '</g>')
    steps = ['O perito pesquisa e anota as provas, com fonte', '25 jurados são convocados do rodízio', 'A sala vota em segredo, antes do debate',
             'Promotor ataca, defesa responde, o FATAL é reconferido', '7 são sorteados, deliberam e decidem', 'O juiz independente lê a sentença']
    for i, st in enumerate(steps):
        t0 = 1.0 + i * .7; y = 210 + i * 52
        c = s.show(t0, dy=0)
        done = s.kf([(0, 'opacity:0'), (t0 + .55, 'opacity:0'), (t0 + .75, 'opacity:1'), (T - .55, 'opacity:1'), (T - .15, 'opacity:0'), (T, 'opacity:0')])
        s.add(f'<g class="{c}"><rect x="40" y="{y-20}" width="28" height="28" rx="7" fill="{C["surface2"]}" stroke="{C["line2"]}"/>'
              + s.text(54, y - .5, str(i + 1), 'I8', 13, C['gold'], 'middle')
              + f'<rect class="{done}" x="40" y="{y-20}" width="28" height="28" rx="7" fill="{C["gold"]}"/>'
              + f'<path class="{done}" d="M47 {y-6}l5 5 9-10" fill="none" stroke="#1a1220" stroke-width="3"/>'
              + s.text(84, y, st, 'I4', 16.5, C['muted']) + '</g>')
    # cartão da sentença
    X, Y, Wc = 560, 40, 600
    c = s.show(5.3, dy=20)
    s.add(f'<g class="{c}">' + card(X, Y, Wc, 520, '#1b1524', C['line2'], 16)
          + f'<line x1="{X}" y1="{Y+112}" x2="{X+Wc}" y2="{Y+112}" stroke="{C["line"]}"/>'
          + s.ring(X + 62, Y + 56, 34, 8, .62, 5.5, 19)
          + s.text(X + 116, Y + 46, 'SENTENÇA · CERTEZA 62%', 'I8', 12.5, C['gold'], ls=1.4) + s.text(X + 116, Y + 76, 'Vale, se ajustar', 'PX', 27, C['ink']) + '</g>')
    blocks = [('COMECE POR AQUI', 'Protótipo simples (até planilha e WhatsApp) com 5 mercadinhos do bairro por 30 dias.', 'I4'),
              ('O QUE MUDARIA A DECISÃO', 'Menos de 3 dos 5 donos ainda usando depois de 30 dias.', 'I4'),
              ('QUANDO DESISTIR', 'Se em 60 dias nenhum dono aceitar pagar R$ 20 por mês.', 'I4'),
              ('O QUE AS PESSOAS DISSERAM', '“Se vier mensagem de cobrança, como eu sei que é do mercadinho mesmo?”', 'SF')]
    y = Y + 150
    for i, (dt, dd, fam) in enumerate(blocks):
        c = s.show(6.6 + i * .8, dy=10)
        t, n = s.para(X + 32, y + 28, dd, fam, 18 if fam == 'I4' else 19.5, Wc - 64, 27, C['ink'])
        extra = s.text(X + 32, y + 28 + n * 27 + 2, 'ex-caminhoneiro, 59 anos · votou contra', 'I4', 14.5, C['faint']) if fam == 'SF' else ''
        line = f'<line x1="{X+32}" y1="{y-14}" x2="{X+Wc-32}" y2="{y-14}" stroke="{C["line"]}"/>' if i else ''
        s.add(f'<g class="{c}">{line}' + s.text(X + 32, y, dt, 'I8', 12, C['faint'], ls=1.2) + t + extra + '</g>')
        y += 50 + n * 27 + (24 if fam == 'SF' else 0)
    s.render('sentenca')


# ------------------------------------------------------------------ 3. papéis
def papeis():
    W, H, T = 1200, 600, 12
    s = SVG(W, H, T, 'Os oito papéis do Tribunal, cada um com sua regra')
    R = [('Perito', '#3b6a8c', '#6b4a2e', 'Pesquisa, abre o app de verdade e roda o código.', 'prova sem fonte é só alegação'),
         ('Promotor', '#7a2e34', '#2a1f1a', 'Ataca com pré-mortem, inversão e riscos.', 'todo ataque tem gravidade e contraexemplo verificável'),
         ('Verificador', '#4d4a6b', '#c9c2d6', 'Reconfere todo ataque FATAL antes de valer.', 'rótulo, arredondamento ou texto não é fatal'),
         ('Defesa', '#2e4f7a', '#3a2a1a', 'Defende e responde a cada ataque, um por um.', 'rebater só insistindo deixa o ataque de pé'),
         ('Júri', '#5a7a3a', '#d9a24a', 'Reage como gente de verdade. 25 votam antes do debate; 7 decidem.', '3 modelos diferentes no mesmo júri'),
         ('Redator do plano', '#6b5a2e', '#4a3a2a', 'Transforma a sentença em passos, testes e prazos.', 'o plano é atacado e revisado antes de chegar a você'),
         ('Juiz', '#1e1828', '#f4eee3', 'Subagente independente que só lê os autos.', 'não fez a perícia; um FATAL pendente trava o veredito pleno'),
         ('Você', '#d97757', '#e8c15a', 'Instância final: acata, ou recorre a um júri novo.', 'a última palavra é sua')]
    cw, ch, gx, gy, x0, y0 = 266, 248, 18, 20, 40, 41
    for i, (n, b, h, d, r) in enumerate(R):
        x = x0 + (i % 4) * (cw + gx); y = y0 + (i // 4) * (ch + gy)
        c = s.show(.2 + i * .22, dy=16)
        you = i == 7
        fill = '#251a22' if you else C['panel']; stroke = '#6b3d33' if you else C['line']
        # destaque que percorre os cartões
        hl0 = 3.0 + i * .9
        hl = s.kf([(0, 'opacity:0'), (hl0, 'opacity:0'), (hl0 + .25, 'opacity:1'), (hl0 + .9, 'opacity:1'), (hl0 + 1.25, 'opacity:0'), (T, 'opacity:0')])
        bob = s.kf([(0, 'transform:translate(0,0)'), (hl0, 'transform:translate(0,0)'), (hl0 + .15, 'transform:translate(0,-6px)'), (hl0 + .3, 'transform:translate(0,0)'),
                    (hl0 + .45, 'transform:translate(0,-4px)'), (hl0 + .6, 'transform:translate(0,0)'), (T, 'transform:translate(0,0)')], ease='ease-out')
        desc, nd = s.para(x + 22, y + 92, d, 'I4', 15.5, cw - 44, 23, C['muted'])
        rl = wrap('Regra · ' + r, 'I6', 13.5, cw - 64)
        ry = y + 92 + nd * 23 + 6
        rh = 22 + len(rl) * 20
        rule = f'<rect x="{x+22}" y="{ry}" width="{cw-44}" height="{rh}" rx="8" fill="{C["bg2"]}" stroke="{C["line2"]}" stroke-dasharray="4 3"/>'
        for k, ln in enumerate(rl):
            yy = ry + 26 + k * 20
            if k == 0:
                rw = width('Regra · ', 'I8', 13.5)
                rule += s.text(x + 36, yy, 'Regra · ', 'I8', 13.5, C['acc'] if you else C['gold']) + s.text(x + 36 + rw, yy, ln[len('Regra · '):], 'I6', 13.5, C['ink'])
            else:
                rule += s.text(x + 36, yy, ln, 'I6', 13.5, C['ink'])
        s.add(f'<g class="{c}">' + card(x, y, cw, ch, fill, stroke)
              + f'<rect class="{hl}" x="{x}" y="{y}" width="{cw}" height="{ch}" rx="14" fill="none" stroke="{C["acc"] if you else C["gold"]}" stroke-width="2"/>'
              + f'<g class="{bob}">' + avatar(x + 22, y + 24, 5, b, h) + '</g>'
              + s.text(x + 76, y + 55, n, 'PX', 21, C['ink']) + desc + rule + '</g>')
    s.render('papeis')


# ------------------------------------------------------------------ 4. júri
def juri():
    J = json.load(open(JURI, encoding='utf-8'))
    faixa = lambda i: '0 a 14' if i < 15 else '15 a 29' if i < 30 else '30 a 44' if i < 45 else '45 a 59' if i < 60 else '60 ou mais'
    net = lambda x: 'não usa' if x['net'] == 'não usa' else 'celular dos pais' if 'pais' in x['net'] else 'WhatsApp e vídeo' if 'básico' in x['net'] else 'média' if x['net'] == 'médio' else 'avançada'
    DIM = [('Idade', lambda x: faixa(x['i']), ['0 a 14', '15 a 29', '30 a 44', '45 a 59', '60 ou mais'], ['#f6dc8a', '#e8c15a', '#d99a3e', '#b8692f', '#8a4a2a']),
           ('Região', lambda x: x['r'], ['Sudeste', 'Nordeste', 'Sul', 'Centro-Oeste', 'Norte'], ['#e8c15a', '#d97757', '#6aa7e8', '#5cc26b', '#b07ad9']),
           ('Renda', lambda x: x['rd'], ['baixa', 'média-baixa', 'média', 'alta'], ['#8a4a2a', '#c47a3a', '#e8c15a', '#f6eab0']),
           ('Internet', net, ['não usa', 'celular dos pais', 'WhatsApp e vídeo', 'média', 'avançada'], ['#5a4a6a', '#7d6a9a', '#6aa7e8', '#5cc26b', '#e8c15a'])]
    PH = 4.2; T0 = 1.6; T = T0 + PH * 4 + .4
    W, H = 1200, 690
    s = SVG(W, H, round(T, 2), 'Os 100 jurados do Tribunal, coloridos por idade, região, renda e internet')
    T = s.T
    # filtros
    fx = 40
    for k, (nome, *_r) in enumerate(DIM):
        bw = width(nome, 'I6', 15) + 32
        on = s.kf([(0, 'opacity:0'), (T0 + k * PH, 'opacity:0'), (T0 + k * PH + .2, 'opacity:1'), (T0 + (k + 1) * PH, 'opacity:1'), (T0 + (k + 1) * PH + .2, 'opacity:0'), (T, 'opacity:0')], ease='linear')
        s.add(f'<rect x="{fx}" y="36" width="{bw:.0f}" height="36" rx="18" fill="{C["panel"]}" stroke="{C["line2"]}"/>'
              + s.text(fx + bw / 2, 59, nome, 'I6', 15, C['muted'], 'middle')
              + f'<g class="{on}"><rect x="{fx}" y="36" width="{bw:.0f}" height="36" rx="18" fill="{C["gold"]}"/>' + s.text(fx + bw / 2, 59, nome, 'I6', 15, '#1a1220', 'middle') + '</g>')
        # o texto cinza fica embaixo do dourado: reordena
        fx += bw + 8
    # grade (cor por fase; células com a mesma sequência dividem a animação)
    gx0, gy0, cs, gap = 40, 92, 41, 6
    s.add(f'<rect x="{gx0}" y="{gy0}" width="{10*cs+9*gap+28}" height="{10*cs+9*gap+28}" rx="12" fill="{C["wood"]}" stroke="#4a3020"/>'
          f'<rect x="{gx0+4}" y="{gy0+4}" width="{10*cs+9*gap+20}" height="{10*cs+9*gap+20}" rx="9" fill="none" stroke="#2e1d12" stroke-width="4"/>')
    shared = {}
    cells = ''
    for i, x in enumerate(J):
        cols = tuple(d[3][d[2].index(d[1](x))] for d in DIM)
        if cols not in shared:
            fr = [(0, f'fill:{cols[0]}')]
            for k in range(1, 4):
                t = T0 + k * PH
                fr += [(t - .01, f'fill:{cols[k-1]}'), (t + .35, f'fill:{cols[k]}')]
            fr += [(T0 + 4 * PH - .01, f'fill:{cols[3]}'), (T, f'fill:{cols[3]}')]
            shared[cols] = s.kf(fr, ease='linear')
        row, col = divmod(i, 10)
        cx = gx0 + 14 + col * (cs + gap); cy = gy0 + 14 + row * (cs + gap)
        pop = s.show(.15 + row * .09 + col * .02, dur=.3, dy=0, sx=.4, out=T - .45)
        cells += (f'<g class="{pop}"><rect class="{shared[cols]}" x="{cx}" y="{cy}" width="{cs}" height="{cs}" rx="4" fill="{cols[0]}"/>'
                  f'<rect x="{cx}" y="{cy+cs-5}" width="{cs}" height="5" rx="2" fill="#000" opacity=".22"/>'
                  f'<rect x="{cx+11}" y="{cy+14}" width="5" height="5" fill="#0f0c14" opacity=".7"/><rect x="{cx+cs-16}" y="{cy+14}" width="5" height="5" fill="#0f0c14" opacity=".7"/></g>')
    s.add(cells)
    # legendas
    ly = gy0 + 10 * cs + 9 * gap + 28 + 34
    for k, (nome, f, ordem, cores) in enumerate(DIM):
        on = s.kf([(0, 'opacity:0'), (T0 + k * PH, 'opacity:0'), (T0 + k * PH + .3, 'opacity:1'), (T0 + (k + 1) * PH, 'opacity:1'), (T0 + (k + 1) * PH + .2, 'opacity:0'), (T, 'opacity:0')], ease='linear')
        cnt = {v: 0 for v in ordem}
        for x in J: cnt[f(x)] += 1
        lx, row, out = gx0, 0, ''
        for v, cor in zip(ordem, cores):
            lab = f'{v}'; n = str(cnt[v])
            wseg = 22 + width(lab, 'I4', 14.5) + 6 + width(n, 'I4', 14.5) + 22
            if lx + wseg > gx0 + 520: lx, row = gx0, row + 1
            yy = ly + row * 26
            out += f'<rect x="{lx}" y="{yy-12}" width="13" height="13" rx="2" fill="{cor}"/>' + s.text(lx + 22, yy, lab, 'I4', 14.5, C['muted']) + s.text(lx + 22 + width(lab, 'I4', 14.5) + 6, yy, n, 'I4', 14.5, C['faint'])
            lx += wseg
        s.add(f'<g class="{on}">{out}</g>')
    # fichas
    picks = [99, 40]
    curtas = sorted([i for i, x in enumerate(J) if 40 < len(x['q']) < 105 and i not in picks], key=lambda i: abs(J[i]['i'] - 35))
    picks += [curtas[0]]
    curtas = [i for i in curtas if abs(J[i]['i'] - 70) < 15] or curtas[1:]
    picks += [curtas[0] if curtas[0] not in picks else curtas[1]]
    X, Wc = 620, 540
    for k, idx in enumerate(picks):
        x = J[idx]; d = DIM[k]; cor = d[3][d[2].index(d[1](x))]
        t0 = T0 + k * PH + .2
        c = s.kf([(0, 'opacity:0;transform:translate(0,12px)'), (t0, 'opacity:0;transform:translate(0,12px)'), (t0 + .45, 'opacity:1;transform:translate(0,0)'),
                  (t0 + PH - .5, 'opacity:1;transform:translate(0,0)'), (t0 + PH - .2, 'opacity:0;transform:translate(0,-8px)'), (T, 'opacity:0')])
        nome = x['n'] + (f' “{x["a"]}”' if x['a'] and x['a'] != x['n'].split(' ')[0] else '')
        nl = wrap(nome, 'PX', 21, Wc - 124)
        body = card(X, 92, Wc, 492, C['panel'], C['line2'], 16)
        body += f'<rect x="{X+28}" y="120" width="60" height="60" rx="9" fill="{cor}"/><rect x="{X+28}" y="174" width="60" height="6" rx="3" fill="#000" opacity=".22"/><rect x="{X+44}" y="141" width="7" height="7" fill="#0f0c14"/><rect x="{X+65}" y="141" width="7" height="7" fill="#0f0c14"/><rect x="{X+48}" y="158" width="20" height="3" fill="#0f0c14" opacity=".6"/>'
        for j, ln in enumerate(nl):
            body += s.text(X + 106, 140 + j * 26, ln, 'PX', 21, C['ink'])
        sub_y = 140 + len(nl) * 26
        anos = 'ano' if x['i'] == 1 else 'anos'
        body += s.text(X + 106, sub_y, f'{x["i"]} {anos} · {x["c"]}, {x["uf"]} · jurado {idx+1:03d} de 100', 'I4', 14, C['faint'])
        qy = max(sub_y + 46, 222)
        q, nq = s.para(X + 28, qy, f'“{x["q"]}”', 'SF', 21, Wc - 56, 31, C['ink'])
        body += q
        ty = qy + nq * 31 + 6
        tags = [x['o'], f'renda {x["rd"]}', f'internet: {x["net"]}']
        tx, trow = X + 28, 0
        for tg in tags:
            if len(tg) > 46: tg = tg[:44].rstrip(' ,;') + '…'
            tw = width(tg, 'I4', 13.5) + 22
            if tx + tw > X + Wc - 28: tx, trow = X + 28, trow + 1
            yy = ty + trow * 34
            body += f'<rect x="{tx}" y="{yy}" width="{tw:.0f}" height="26" rx="13" fill="{C["bg2"]}" stroke="{C["line"]}"/>' + s.text(tx + 11, yy + 18, tg, 'I4', 13.5, C['muted'])
            tx += tw + 8
        vy = ty + (trow + 1) * 34 + 22
        body += f'<line x1="{X+28}" y1="{vy-22}" x2="{X+Wc-28}" y2="{vy-22}" stroke="{C["line"]}"/>'
        v, _ = s.para(X + 28 + width('Viés: ', 'I8', 15), vy + 4, x['v'], 'I4', 15, Wc - 56 - width('Viés: ', 'I8', 15), 23, C['muted'])
        body += s.text(X + 28, vy + 4, 'Viés:', 'I8', 15, C['gold']) + v
        s.add(f'<g class="{c}">{body}</g>')
        # contorno da célula escolhida
        row, col = divmod(idx, 10)
        cx = gx0 + 14 + col * (cs + gap); cy = gy0 + 14 + row * (cs + gap)
        sel = s.kf([(0, 'opacity:0'), (t0, 'opacity:0'), (t0 + .3, 'opacity:1'), (t0 + PH - .4, 'opacity:1'), (t0 + PH - .2, 'opacity:0'), (T, 'opacity:0')], ease='linear')
        s.add(f'<rect class="{sel}" x="{cx-4}" y="{cy-4}" width="{cs+8}" height="{cs+8}" rx="6" fill="none" stroke="{C["ink"]}" stroke-width="3"/>')
    s.add(f'<line x1="{X+28}" y1="536" x2="{X+Wc-28}" y2="536" stroke="{C["line"]}"/>' + s.text(X + 28, 564, 'Cada jurado representa 1% da população (Censo 2022 e PNAD do IBGE).', 'I4', 14.5, C['faint']))
    s.render('juri')


# ------------------------------------------------------------------ 5. resultados
def resultados():
    W, H, T = 1200, 900, 12
    s = SVG(W, H, T, 'Resultados medidos do Tribunal, inclusive os que não favorecem')

    def bar(x, y, w, frac, gold, t0, lab, val, lw=150, vw=110):
        g = s.grow(t0, 1.2)
        return (s.text(x, y + 10, lab, 'I4', 15.5, C['muted'])
                + f'<rect x="{x+lw}" y="{y-1}" width="{w-lw-vw}" height="14" rx="3" fill="{C["bg2"]}" stroke="{C["line"]}"/>'
                + f'<rect class="{g}" x="{x+lw}" y="{y-1}" width="{(w-lw-vw)*frac:.1f}" height="14" rx="3" fill="{C["gold"] if gold else C["line2"]}"/>'
                + s.text(x + w, y + 11, val, 'I8', 15.5, C['ink'], 'end'))

    # custo
    c = s.show(.2)
    x, y, w = 40, 40, 550
    s.add(f'<g class="{c}">' + card(x, y, w, 256) + s.text(x + 30, y + 42, 'CUSTO', 'I8', 12.5, C['faint'], ls=1.6)
          + s.text(x + 30, y + 78, 'Agentes enxutos, ~6× mais barato.', 'I8', 23, C['ink'])
          + s.text(x + 30, y + 108, 'Tokens por julgamento completo.', 'I4', 15.5, C['muted'])
          + bar(x + 30, y + 140, w - 60, 1, False, .8, 'Versão 1.0', '~650 mil')
          + bar(x + 30, y + 176, w - 60, .4, True, 1.0, 'Hoje', '150–260 mil')
          + s.text(x + 30, y + 228, 'Num caso real: cerca de US$ 1 em subagentes.', 'I4', 15, C['faint']) + '</g>')
    # consistência
    c = s.show(.45)
    x = 610
    t, n = s.para(x + 30, y + 108, 'O mesmo caso, julgado cinco vezes, inclusive com um júri inteiramente novo. Entre duas rodadas, 84% dos jurados repetiram o próprio voto.', 'I4', 15.5, w - 60, 23, C['muted'])
    checks = ''
    for k in range(5):
        cx = x + 30 + k * 56; cy = y + 190
        ck = s.show(1.4 + k * .3, dur=.3, dy=0, sx=.3)
        checks += (f'<rect x="{cx}" y="{cy}" width="44" height="44" rx="8" fill="#14261a" stroke="#2f6b3a"/>'
                   f'<g class="{ck}"><rect x="{cx}" y="{cy}" width="44" height="44" rx="8" fill="#1d3a25" stroke="{C["ok"]}"/><path d="M{cx+12} {cy+23}l7 7 14-15" fill="none" stroke="{C["ok"]}" stroke-width="3.5"/></g>')
    s.add(f'<g class="{c}">' + card(x, y, w, 256) + s.text(x + 30, y + 42, 'CONSISTÊNCIA', 'I8', 12.5, C['faint'], ls=1.6)
          + s.text(x + 30, y + 78, 'Cinco julgamentos, o mesmo veredito.', 'I8', 23, C['ink']) + t + checks + '</g>')
    # torneio
    c = s.show(2.6)
    x, y, w = 40, 316, 1120
    t, n = s.para(x + 30, y + 108, 'Mesma pergunta sobre um SaaS real, avaliada por dois juízes cegos com a rubrica do próprio torneio. O Tribunal traz o que o torneio não traz: como pessoas reais reagiriam e quanto confiar no resultado.', 'I4', 15.5, w - 60, 23, C['muted'])
    by = y + 108 + n * 23 + 20
    s.add(f'<g class="{c}">' + card(x, y, w, by - y + 4 * 34 + 14) + s.text(x + 30, y + 42, 'CONTRA UM TORNEIO DE 16 AGENTES', 'I8', 12.5, C['faint'], ls=1.6)
          + s.text(x + 30, y + 78, '85% da nota com 4% do custo.', 'I8', 23, C['ink']) + t
          + bar(x + 30, by, w - 60, .71, True, 3.2, 'Tribunal · nota', '71', 170)
          + bar(x + 30, by + 34, w - 60, .835, False, 3.35, 'Torneio · nota', '83,5', 170)
          + bar(x + 30, by + 68, w - 60, .038, True, 3.5, 'Tribunal · tokens', '~260 mil', 170)
          + bar(x + 30, by + 102, w - 60, 1, False, 3.65, 'Torneio · tokens', '~6,8 mi', 170) + '</g>')
    # o que não mede
    y2 = by + 4 * 34 + 14 + 20
    c = s.show(5.2)
    s.add(f'<defs><linearGradient id="hg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a1519"/><stop offset=".55" stop-color="{C["panel"]}"/></linearGradient></defs>')
    t, n = s.para(x + 30, y2 + 108, 'No piloto, quem escreveu as descrições já sabia o desfecho. No teste cego, um agente separado escreveu com regras contra pistas. O júri mostra como pessoas comuns reagem, não se o produto vai dar certo.', 'I4', 15.5, w - 60, 23, C['muted'])
    by2 = y2 + 108 + n * 23 + 18
    half = (w - 60 - 16) / 2
    strike = s.grow(6.6, .5)
    num = s.show(7.3, dur=.5, dy=0, sx=.6)
    hh = by2 + 120 + 30 - y2
    s.add(f'<g class="{c}">' + card(x, y2, w, hh, 'url(#hg)', '#5a2a2c') + s.text(x + 30, y2 + 42, 'O QUE O JÚRI NÃO MEDE', 'I8', 12.5, C['no'], ls=1.6)
          + s.text(x + 30, y2 + 78, 'Ele não prevê se um produto vai dar certo.', 'I8', 23, C['ink']) + t
          + card(x + 30, by2, half, 120, C['bg2'], C['line'], 12) + card(x + 46 + half, by2, half, 120, C['bg2'], C['line'], 12)
          + s.text(x + 54, by2 + 32, 'PILOTO · 12 CASOS FAMOSOS', 'I8', 12.5, C['faint'], ls=.8)
          + s.text(x + 54, by2 + 78, '8 de 9', 'I8', 38, C['faint'])
          + f'<rect class="{strike}" x="{x+52}" y="{by2+64}" width="{width("8 de 9","I8",38)+6:.0f}" height="4" fill="{C["no"]}"/>'
          + s.text(x + 54, by2 + 104, 'Inflado pela redação e pela fama dos casos.', 'I4', 14.5, C['muted'])
          + s.text(x + 70 + half, by2 + 32, 'TESTE CEGO · 30 CASOS', 'I8', 12.5, C['faint'], ls=.8)
          + f'<g class="{num}">' + s.text(x + 70 + half, by2 + 78, '18 de 30', 'I8', 38, C['ink']) + '</g>'
          + s.text(x + 70 + half, by2 + 104, 'p = 0,18: não se distingue do acaso.', 'I4', 14.5, C['muted']) + '</g>')
    s.h = int(y2 + hh + 40)
    s.render('resultados')


hero(); sentenca(); papeis(); juri(); resultados()
