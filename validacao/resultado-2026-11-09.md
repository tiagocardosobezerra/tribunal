# Validação do júri

**Acerto:** 8 de 9 casos decididos (3 empate(s) em 50%, que não contam) · **Brier:** 0.141 (chute de 50% = 0,25; menor é melhor)

**Vazamento:** 6/120 votos reconheceram o produto real. Sem os casos vazados: 9 de 10 · Brier 0.152

| Caso | Ano | Desfecho | P(lançar) | Acertou | Reconheceram |
|---|---|---|---|---|---|
| cartao-app | 2013 | sucesso | 0.5 | empate | 0/10  |
| comida-app | 2011 | sucesso | 0.9 | sim | 0/10  |
| espremedor-conectado | 2016 | fracasso | 0.2 | sim | 1/10 Juicero |
| videos-curtos-premium | 2020 | fracasso | 0.5 | empate | 3/10 Quibi |
| oculos-tela | 2013 | fracasso | 0.2 | sim | 2/10 Google Glass |
| quarto-de-desconhecidos | 2008 | sucesso | 0.4 | não | 0/10  |
| patinete-equilibrio | 2001 | fracasso | 0.4 | sim | 0/10  |
| idiomas-jogo | 2012 | sucesso | 0.6 | sim | 0/10  |
| mercado-30-minutos | 1999 | fracasso | 0.3 | sim | 0/10  |
| pagamento-instantaneo | 2020 | sucesso | 0.8 | sim | 0/10  |
| fotos-quadradas | 2010 | sucesso | 0.5 | empate | 0/10  |
| tv-3d-em-casa | 2010 | fracasso | 0.2 | sim | 0/10  |

_Acerto do modelo conta só casos em que ele não empatou._

| Modelo | Casos | Acerto | Brier |
|---|---|---|---|
| haiku | 12 | 9 | 0.19 |
| sonnet | 12 | 10 | 0.127 |
