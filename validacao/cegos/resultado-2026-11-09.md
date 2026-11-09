# Validação cega do júri (2026-11-09)

**Como foi feita.**
- 30 produtos com desfecho conhecido: 15 deram certo e 15 fracassaram, muitos deles brasileiros e menos famosos que os do piloto.
- Um agente separado escreveu as descrições. Ele recebeu só o nome e o ano, com a regra de não antecipar o desfecho, de manter o mesmo tom em todas e de citar forças e riscos em todas.
- O gabarito ficou num arquivo à parte (`gabarito.json`), que o júri nunca viu.
- Cada caso teve 3 lotes de 5 jurados, um lote por modelo (Sonnet, Haiku e Opus), num total de 450 votos.
- A linha de base é um modelo sozinho, no papel de analista, que leu as 30 descrições numa chamada.

**Conclusão.** O júri **não prevê desfecho melhor que o acaso.**
- Acertou 18 de 30. A chance de acertar 18 ou mais chutando é p = 0.18.
- O Brier foi 0,227, contra 0,25 do chute de 50%.
- Sem os votos que reconheceram o produto, o Brier foi 0,277, pior que o chute.
- O piloto de 12 casos famosos (8 de 9 acertos) estava inflado por vazamento e pela redação das descrições.

**A linha de base não serve de régua.**
- O analista identificou 27 dos 30 produtos pelo nome, então o 26 de 27 dele é memória.
- Ou seja, as descrições ainda entregam os produtos a quem lê como especialista.
- Os jurados, no papel de pessoas leigas, reconheceram o produto em só 8% dos votos (37 de 450).
- A persona contém a memória do modelo, mas não acrescenta poder de previsão.

**O que isto quer dizer.**
- O júri do Tribunal mede **como pessoas comuns reagem a uma ideia**, e não **se a ideia vai dar certo no mercado**.
- Muitos destes casos eram B2B ou de nicho (agenda online, automação de tarefas, pagamentos para lojistas), produtos que o público leigo do júri não avalia bem.
- O veredito do Tribunal não deve ser lido como previsão de sucesso. O que o valida é a qualidade do processo: provas, contraditório e plano com critério de abandono.

**Diferença entre modelos.** Haiku e Opus tiveram Brier 0,237; Sonnet, 0,292. Com 30 casos, a diferença é ruído e inverte o piloto, em que o Sonnet foi melhor.

---


**Acerto:** 18 de 30 casos decididos (0 empate(s) em 50%, que não contam) · **Brier:** 0.227 (chute de 50% = 0,25; menor é melhor)

**Vazamento:** 37/450 votos reconheceram o produto real. Sem os casos vazados: 15 de 25 · Brier 0.277

| Caso | Ano | Desfecho | P(lançar) | Acertou | Reconheceram |
|---|---|---|---|---|---|
| c01 | 2013 | fracasso | 0.33 | sim | 0/15  |
| c02 | 2011 | sucesso | 0.73 | sim | 5/15 Dafiti, Netshoes |
| c03 | 2013 | sucesso | 0.73 | sim | 1/15 tipo OLX, só que pra aluguel |
| c04 | 2017 | fracasso | 0.4 | sim | 0/15  |
| c05 | 2013 | fracasso | 0.27 | sim | 1/15 Coin |
| c06 | 2015 | sucesso | 0.6 | sim | 2/15 Shopee, Skyhub, acho, já vi gente falando no fórum de algo parecido |
| c07 | 2019 | sucesso | 0.4 | não | 0/15  |
| c08 | 2013 | sucesso | 0.6 | sim | 1/15 Canva |
| c09 | 2012 | sucesso | 0.6 | sim | 5/15 Cielo, Cielo, Redecard |
| c10 | 2012 | fracasso | 0.53 | não | 0/15  |
| c11 | 2012 | sucesso | 0.47 | não | 1/15 Lending Club |
| c12 | 2016 | fracasso | 0.27 | sim | 1/15 Nespresso |
| c13 | 2018 | fracasso | 0.67 | não | 3/15 Bird, Lime / Bird, Yellow |
| c14 | 2016 | fracasso | 0.33 | sim | 2/15 AirPods |
| c15 | 2011 | fracasso | 0.53 | não | 0/15  |
| c16 | 2015 | fracasso | 0.53 | não | 1/15 Domino's |
| c17 | 2012 | sucesso | 0.53 | sim | 1/15 Gympass |
| c18 | 2009 | sucesso | 0.27 | não | 1/15 o corretor do Word |
| c19 | 2013 | fracasso | 0.2 | sim | 0/15  |
| c20 | 2011 | sucesso | 0.53 | sim | 1/15 Mailchimp |
| c21 | 2014 | fracasso | 0.2 | sim | 4/15 Secret, WhatsApp |
| c22 | 2014 | fracasso | 0.27 | sim | 0/15  |
| c23 | 2011 | sucesso | 0.47 | não | 1/15 IFTTT |
| c24 | 2011 | fracasso | 0.6 | não | 0/15  |
| c25 | 2009 | sucesso | 0.4 | não | 1/15 Strava |
| c26 | 2012 | sucesso | 0.33 | não | 0/15  |
| c27 | 2015 | fracasso | 0.4 | sim | 2/15 GoPro, Lily Camera |
| c28 | 2013 | sucesso | 0.53 | sim | 2/15 Calendly, Doodle |
| c29 | 2011 | sucesso | 0.53 | sim | 1/15 ClickBank |
| c30 | 2014 | fracasso | 0.73 | não | 0/15  |

_Acerto do modelo conta só casos em que ele não empatou._

| Modelo | Casos | Acerto | Brier |
|---|---|---|---|
| haiku | 30 | 18 | 0.237 |
| opus | 30 | 18 | 0.237 |
| sonnet | 30 | 16 | 0.292 |

## Linha de base: um modelo sozinho, numa chamada

Acerto: 26 de 27 decididos · Brier: 0.128 · produtos identificados pelo nome: 27 de 30
