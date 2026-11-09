# Rubrica do juiz

Carregado sob demanda pelo `SKILL.md`. Esta rubrica tem duas partes: a confiança da sentença e a nota
das propostas do concurso. Nas duas, **um 7 não é nota de cortesia**: cada nota precisa da evidência que a
âncora pede.

## 1. O contraditório: o status de cada ataque

Para cada ataque da acusação (A1, A2...), o juiz confere a resposta da defesa **no objeto**. Uma promessa
de correção não basta. O ataque recebe um destes status:

| Status | Quando |
|---|---|
| `corrigido` | A correção JÁ foi feita e conferida (campo `verificado` diz como). |
| `correcao_proposta` | A defesa concedeu e propôs uma correção concreta, que ainda não foi feita. Vira condição. |
| `rebatido` | A defesa rebateu **com prova** ou com um contraexemplo verificável. |
| `de_pe` | A resposta só insistiu, prometeu sem dizer como, ou não respondeu. |

**Regras:**
- Rebater só insistindo é `de_pe`.
- Conceder e corrigir conta a favor.
- O juiz também procura falhas que a acusação não viu, e as registra como ataques próprios (J1, J2...).
- **FATAL de pé trava o veredito pleno.** O veredito não pode ser a opção mais favorável (a primeira do
  caso). O `validar` recusa a combinação.

**Gravidade do ataque:**

| Gravidade | Quando |
|---|---|
| **FATAL** | Se for verdade, o objeto não cumpre o que promete, ou causa dano sério. Exemplos: ninguém usaria, é ilegal, vaza dado. |
| **GRAVE** | Compromete muito o resultado, mas tem conserto. |
| **LEVE** | Incomoda, mas não muda a decisão. |

## 2. A confiança da sentença (0 a 100)

| Passo | Ajuste |
|---|---|
| Margem do conselho | 7x0 ≈ 85 · 6x1 ≈ 75 · 5x2 ≈ 65 · 4x3 ≈ 55 |
| Força das provas decisivas | Até +10 se têm fonte primária. Até -15 por cada lacuna que sustenta o veredito. |
| Ataques | -5 por GRAVE de pé. FATAL de pé já trava o veredito pleno. |
| Sala (os 25) | +5 se a maioria da sala concorda com o conselho; -10 se discorda. |
| Calibração | Se `cartao calibracao` mostra que a faixa acertou menos que a confiança, desconte a diferença. |
| Estabilidade | O `placar` mostra em quantas reamostragens a maioria do conselho se mantém. Se a confiança passar dela em mais de 15 pontos, explique por quê: só provas fortes justificam. |

Âncoras da confiança final:

| Confiança | Âncora |
|---|---|
| 90 ou mais | Só com provas fortes, nenhum ataque de pé e sala e conselho quase unânimes. Raro. |
| 70 a 89 | O veredito é claro, mas sobra uma lacuna conhecida. |
| 50 a 69 | Há uma condição ou uma lacuna que pode inverter tudo. O ponto de virada é o centro da sentença. |
| Menos de 50 | Use só quando nenhum dos lados provou o bastante. A sentença diz o que falta provar. |

## 3. As propostas do concurso (0 a 100)

Cada critério recebe uma nota de 0 a 10, e o total é ponderado pelos pesos: `propostas placar` faz a
conta.

| Critério | Peso | 0 a 3 | 4 a 6 | 7 a 8 | 9 a 10 |
|---|---|---|---|---|---|
| **resolve** o problema do caso | 30 | Resolve outro problema. | Resolve parte. | Resolve o centro. | Resolve, e a prova mostra. |
| **viabilidade** com o que o usuário tem | 25 | Exige o que ele não tem. | Exige um esforço grande. | Cabe com algum esforço. | Começa nesta semana. |
| **robustez** aos ataques | 20 | Tem FATAL de pé. | Tem GRAVE de pé. | Só LEVE de pé. | Nenhum ataque de pé. |
| **especificidade** | 15 | Genérica: serve para qualquer caso. | Tem passos, mas sem números. | Tem passos, números e prazos. | Também diz como medir o sucesso. |
| **clareza** | 10 | Confusa. | Entende-se com esforço. | Clara. | Um vizinho entenderia. |

**Regras do concurso:**
- Ordem: proposta sem FATAL de pé vem sempre antes de proposta com FATAL de pé. Depois, a maior nota.
- Desempate: menos ataques de pé; depois, maior nota em "resolve"; depois, a que você entregaria ao
  usuário.
- Não premie tamanho. Um texto longo não vale mais que um claro.
- A proposta que só cola o nome da carta numa resposta genérica perde em especificidade.
- **Finalistas:** as 2 melhores sem FATAL de pé vão ao júri, sempre ao lado do **status quo**: manter
  como está, ou a alternativa que o usuário já tinha. O júri popular decide entre elas, sem saber qual
  carta gerou cada uma.
