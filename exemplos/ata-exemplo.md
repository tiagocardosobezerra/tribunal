# Caderneta digital de fiado

## O caso

**Pergunta ao tribunal:** Devo construir um app de caderneta de fiado para mercadinhos de bairro?

EXEMPLO FICTÍCIO, para mostrar o formato. O dono do comércio anota no celular o que cada cliente leva fiado; o cliente recebe pelo WhatsApp o saldo e o lembrete, e paga por Pix.

- **Tipo:** Ideias
- **Área:** Pequeno comércio
- **Público:** donos de mercadinho, bar e venda de bairro e os clientes que compram fiado
- **Opções de voto:** Procedente, Procedente com condições, Improcedente

## O júri

Foro **Brasil**, sessão `brasil-0001`: 25 convocados, 7 no Conselho de Sentença.
- Recusas da acusação: Bianca Rocha Nunes (BR-026): viés de aprovar tudo que é digital
- Recusas da acusação: Rodrigo Kowalski Andrade (BR-052): dono de empresa com sistema próprio, longe do público
- Recusas da defesa: Edson Prado Gruber (BR-080): auditor fiscal, tende a ver só o risco regulatório
- Recusas da defesa: Heloísa Kunzler (BR-094): engenheira exigente, julga como projeto técnico

**Conselho de Sentença:**

- BR-083 Reinaldo Batista, 59, ex-caminhoneiro, parou de trabalhar depois de um infarto e aguarda perícia do INSS, Rondonópolis-MT (interior), parda, renda média-baixa, internet básico (WhatsApp e vídeo)
- BR-079 Geraldo Antunes, 55, cozinheiro CLT num restaurante self-service perto de uma fábrica, Betim-MG (região metropolitana), branca, renda baixa, internet básico (WhatsApp e vídeo)
- BR-048 Priscila Fontes Rezende, 33, agente comunitária de saúde concursada, Divinópolis-MG (interior), branca, renda média, internet médio
- BR-100 Antônia Joaquina de Jesus, 100, aposentada rural, ex-agricultora e rendeira, Crato-CE (interior), parda, renda baixa, internet não usa
- BR-045 Francilene Tavares Batista, 31, dona de casa numa comunidade ribeirinha, zona rural de Parintins-AM (rural), parda, renda média-baixa, internet básico (WhatsApp e vídeo)
- BR-062 Claudinei Ribeiro, 42, repositor de mercadorias num atacarejo, no turno da noite, com carteira assinada, Curitiba-PR (capital), parda, renda baixa, internet básico (WhatsApp e vídeo)
- BR-034 Gleiciane Souza Barbosa, 23, vende salgado frito e geladinho por encomenda no WhatsApp e de porta em porta, sem CNPJ, Luziânia-GO (interior), parda, renda baixa, internet básico (WhatsApp e vídeo)

## Provas

| Id | Tipo | Prova | Fonte | Aceita |
|---|---|---|---|---|
| P1 | depoimento | O usuário conta que 6 donos de mercadinho do bairro usam caderno de papel para o fiado. | depoimento do usuário (exemplo fictício) | sim |
| P2 | lacuna | Não há número verificado de quanto o pequeno comércio perde com fiado não pago. | pesquisa sem resultado confiável | sim |
| P3 | leitura | Saldo de fiado de uma pessoa identificada é dado pessoal: a LGPD se aplica. | Lei 13.709/2018, art. 5º, I | sim |
| P4 | dado | Cobrança falsa é golpe comum no WhatsApp. | alegação da acusação, sem fonte | não: sem fonte: fica como alegação |

## Acusação (promotor)

1. Fiado é relação de confiança; tirar do olho no olho pode constranger o cliente e afastá-lo. _(provas: P1)_
2. Cobrança pelo WhatsApp se confunde com golpe: o cliente desconfiado não paga (alegação).
3. Dado de dívida é dado pessoal: um vazamento expõe o cliente e o dono responde pela LGPD. _(provas: P3)_
4. Não há prova de que a perda com fiado seja grande o bastante para alguém pagar por isso. _(provas: P2)_

## Defesa

1. O caderno some, molha e gera briga; um saldo visível para os dois lados reduz conflito. _(provas: P1)_
2. Funcionar sem internet e sincronizar depois atende quem só tem sinal à noite.
3. Teste barato: 5 mercadinhos, 30 dias, de graça, medindo quantos clientes pagam em dia. _(provas: P1, P2)_

## Testemunhas

- **Advogada de proteção de dados (fictícia)** (LGPD): O registro do fiado tem base na execução de contrato; exige segurança mínima e não expor o saldo a terceiros (LGPD, arts. 7º, V, e 46).

## Placar

**Voto secreto dos 25 convocados:** Procedente **8** · Procedente com condições **12** · Improcedente **5**

**Voto final do Conselho de Sentença (7):** Procedente **1** · Procedente com condições **4** · Improcedente **2**

**Onde o júri se dividiu** (segmentos com maioria diferente da geral):

- faixa etaria = 15-29 (7): maioria **Procedente** · Procedente **5** · Procedente com condições **1** · Improcedente **1**
- sexo = M (10): maioria **Procedente** · Procedente **5** · Procedente com condições **3** · Improcedente **2**
- regiao = Sudeste (8): maioria **Procedente** · Procedente **4** · Procedente com condições **3** · Improcedente **1**
- cor raca = branca (9): maioria **Procedente** · Procedente **5** · Procedente com condições **3** · Improcedente **1**
- religiao = sem religião (3): maioria **Procedente** · Procedente **2** · Improcedente **1**

**Quem mudou de voto no debate:**

- Priscila Fontes Rezende (BR-048): Improcedente → Procedente com condições. Se funcionar sem internet e tiver cópia guardada, aí eu mudo. Era isso que me preocupava.
- Francilene Tavares Batista (BR-045): Improcedente → Procedente com condições. A moça disse que dá pra anotar sem internet e mandar depois. Aí serve, né?

**Votos do conselho:**

- **Reinaldo Batista** (59): Improcedente. "Continuo com medo de golpe. Se vier mensagem de cobrança, como eu sei que é do mercadinho mesmo?"
- **Geraldo Antunes** (55): Procedente. "Tô dentro, sô. Se o dono gostar, todo mundo usa."
- **Priscila Fontes Rezende** (33): Procedente com condições. "Se funcionar sem internet e tiver cópia guardada, aí eu mudo. Era isso que me preocupava."
- **Antônia Joaquina de Jesus** (100): Improcedente. "Pra mim, fiado é olho no olho. Mas se o neto disser que é bom, eu acredito."
- **Francilene Tavares Batista** (31): Procedente com condições. "A moça disse que dá pra anotar sem internet e mandar depois. Aí serve, né?"
- **Claudinei Ribeiro** (42): Procedente com condições. "Se o piá instalar e for igual ao caderno, beleza."
- **Gleiciane Souza Barbosa** (23): Procedente com condições. "Sem taxa pra mim e sem gastar crédito, eu uso. Se cobrar, desisto."

## Sentença

**Veredito: Procedente com condições** · confiança 62%

O conselho decidiu por 5 a 2 que a ideia procede com condições, e a maioria dos 25 também. A resistência veio de quem teme golpe e de quem depende de internet ruim; as duas objeções viraram condições. A falta de dado sobre o tamanho da perda (P2) segura a confiança.

**Condições:**

- funcionar sem internet e sincronizar depois
- o cliente reconhecer a cobrança como legítima (nome e foto do comércio, sem link estranho)
- sem taxa para o cliente
- cópia de segurança automática

**Ponto de virada:** Se no teste menos de 3 dos 5 donos continuarem usando depois de 30 dias, o veredito vira para Improcedente.

**Provas decisivas:** P1, P2, P3

**Voto vencido:** A minoria (golpe e confiança) é forte entre os idosos: mantenha o caderno como opção do cliente.

**Próximo passo barato:** Protótipo simples (até planilha + WhatsApp) com 5 mercadinhos do bairro por 30 dias.

**Critério de abandono:** Se em 60 dias nenhum dono aceitar pagar R$ 20 por mês, pare.

## Instância final

O usuário **acatou** a sentença.
Decisão: Vou fazer o teste com 5 mercadinhos.
