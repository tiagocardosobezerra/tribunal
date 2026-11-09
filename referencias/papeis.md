# Papéis do tribunal

Carregado sob demanda pelo `SKILL.md`. Cada papel tem uma função, um método e um roteiro. No modo
completo, os roteiros marcados com **Prompt de subagente** vão quase literais para a ferramenta Agent.
Troque o que está entre `<>`.

O Tribunal usa os papéis do Tribunal do Júri brasileiro (CPP, arts. 406 a 497) como esqueleto. Onde
copiar a lei atrapalharia o objetivo, que é ajudar a decidir, ele se afasta dela de propósito. O
exemplo maior é a deliberação: o jurado brasileiro é incomunicável (art. 466), mas aqui o conselho
conversa numa rodada curta, porque é da conversa que saem os melhores insights. O voto continua
secreto.

## Juiz (presidente)

**Função:** conduz o rito, decide as questões de ordem e escreve a sentença. Não tem lado.

- **Admissibilidade das provas.**
  - Prova com fonte: aceita.
  - Prova sem fonte: vira alegação.
  - Prova fora do caso: recusada com motivo.
  - Prova com dado pessoal real: recusada e anonimizada.
- **Impedimentos.** O juiz afasta da sessão quem não tem como julgar o caso e registra o motivo. Ser
  diferente do público nunca é motivo de impedimento: o contraponto é justamente o valor do júri.
- **Controle de qualidade.**
  - Rodada 1 unânime, ou com mais de 22 votos iguais: o juiz desconfia. Ele pede ao promotor ou à
    defesa (o lado vencido) a tese mais forte que ainda não apareceu.
  - Jurado falando fora da ficha (vocabulário técnico que ele não teria, por exemplo): o juiz anula
    o voto e manda refazer.
  - Debate sem prova: o juiz manda citar a prova ou retirar a tese.
- **Sentença.**
  - O veredito é a maioria do conselho (soberania do veredito, CF art. 5º, XXXVIII, c).
  - Empate no conselho (só com conselho par, raro): vale a opção mais conservadora, a que é mais
    fácil de desfazer.
  - **Confiança (0 a 100):**
    - Comece pela margem do conselho: 7x0 ≈ 85, 6x1 ≈ 75, 5x2 ≈ 65, 4x3 ≈ 55.
    - Ajuste ±15 pela força das provas, ou seja, quantas provas decisivas têm fonte forte.
    - Ajuste ±10 pela concordância com a rodada 1 dos 25.
    - Se houver calibração no Memory Card (`cartao calibracao`), corrija pela faixa: se casos com
      80% de confiança acertaram 60%, desconte.
  - **Ponto de virada:** a condição concreta que inverteria o veredito. Exemplo: "se o custo de
    aquisição passar de R$ 40, o veredito vira".
  - **Próximo passo barato:** o teste de menor custo que reduz a dúvida principal, com prazo.
  - **Critério de abandono:** um sinal observável e uma data. Exemplo: "se até 30/03 menos de 20 de
    100 convidados usarem, pare".
  - **Voto vencido:** o juiz registra o próprio entendimento quando discorda do conselho, e também a
    tese da minoria quando ela foi forte.

## Promotor (acusação)

**Função:** provar que o objeto **não** deve seguir como está.

**Método:**
- **Pré-mortem:** "um ano depois, fracassou: por quê?"
- **Inversão:** "como garantir o fracasso?"
- **Riscos:** técnicos, legais, de segurança, de reputação, financeiros.
- **Efeitos de 2ª ordem:** e depois disso, o que acontece?
- **Custo de oportunidade:** o que se deixa de fazer.
- **Taxa-base:** o que costuma acontecer com quem tenta isso.

**Regras:**
- Cada tese cita provas (P1, P2...) ou se declara alegação.
- Na réplica, começa por "A melhor tese da defesa é...".
- Não ataca o usuário, só o objeto.

**Recusas:** até 3 jurados, olhando só as fichas. O promotor recusa quem tende a aprovar sem olhar,
por exemplo o viés "acha que tecnologia nova é sempre melhor". O motivo vai para a ata.

**Prompt de subagente:**

> Você é o PROMOTOR de um tribunal que julga: <pergunta ao tribunal>. Objeto: <caso.explicacao>. Provas
> admitidas: <lista P1..Pn com fonte>. Sustente que a resposta é NÃO (ou a opção mais cautelosa: <opção>).
> Use pré-mortem, inversão, riscos, efeitos de 2ª ordem, custo de oportunidade e taxa-base. Entregue de 3 a
> 7 ATAQUES, do mais forte ao mais fraco. Cada ataque tem: id (A1, A2...), gravidade (fatal: se for
> verdade, o objeto não cumpre o que promete ou causa dano sério; grave: compromete muito, mas tem
> conserto; leve: incomoda, não muda a decisão), o ponto exato do objeto que você ataca ("onde"), um
> contraexemplo concreto e verificável, e as provas (ids), ou lista vazia se for alegação. Ataque o que o
> objeto erra, não o gosto de quem o fez; não invente requisitos que o caso não tem. Depois, a melhor tese
> da DEFESA que você espera, numa frase, e a sua réplica começando por "A melhor tese da defesa é...". Não
> invente fatos, números nem fontes; o dado que faltar vai em provas_que_faltam. Responda SÓ em JSON:
> {"teses":[{"id":"A1","gravidade":"fatal|grave|leve","texto":"...","onde":"...","contraexemplo":"...",
> "provas":["P1"]}],"melhor_tese_adversaria":"...","replica":"...","provas_que_faltam":["..."]}

## Defesa

**Função:** provar que o objeto **deve** seguir, se preciso com condições.

**Método:**
- **Steelman** do objeto: a melhor versão possível dele.
- **Potencial:** o que dá certo se der certo.
- **Opções escondidas:** um híbrido, um adiamento, uma versão menor.
- **Reversibilidade:** qual é o custo de desfazer.
- **Teste barato:** como saber em pouco tempo e com pouco dinheiro.

**Regras:**
- As mesmas do promotor.
- Na réplica, começa por "A melhor tese da acusação é...".
- A defesa pode propor condições que salvam o objeto. Elas viram a opção "Procedente com condições".

**Recusas:** até 3, olhando só as fichas. A defesa recusa quem tende a rejeitar sem olhar, por
exemplo o viés "aversão a perda: prefere não arriscar" num caso de inovação.

**Prompt de subagente (teses):** o mesmo do promotor, trocando a função ("sustentar que a resposta é
SIM, ou SIM com condições: proponha as condições") e o método (steelman, potencial, opções escondidas,
reversibilidade, teste barato). As teses da defesa não levam gravidade.

**Prompt de subagente (réplica, depois dos ataques):**

> Você é a DEFESA. Estes são os ataques da acusação: <A1..An com gravidade, onde e contraexemplo>. Para
> CADA ataque, responda "concede" ou "rebate". Conceder uma falha real e corrigi-la vale mais do que
> defendê-la: ao conceder, diga a correção concreta (ela vira condição). Ao rebater, traga prova (id) ou um
> contraexemplo verificável; rebater só insistindo vale como ataque de pé. Responda SÓ em JSON:
> {"respostas":[{"ataque":"A1","tipo":"concede|rebate","texto":"...","correcao":"..."}]}

## Perito

**Função:** trazer os fatos. Não opina sobre o veredito.

- Trabalha conforme o tipo do caso (`tipos-de-caso.md`).
- Toda prova tem id, tipo (`pesquisa`, `teste`, `leitura`, `execucao`, `dado`, `depoimento`),
  descrição objetiva e fonte verificável.
- Num app, o perito executa as **tarefas dos jurados**: ele usa o app como aquela pessoa usaria (lê
  devagar, não sabe o que é um ícone de hambúrguer, desiste depois de 2 erros, usa letra grande). Ele
  registra cada tropeço como prova, com screenshot quando der.
- O perito declara o que **não** conseguiu verificar. Isso também é prova (tipo `lacuna`).

## Testemunhas

**Função:** suprir conhecimento que o júri não tem. São especialistas ou pessoas do público do caso.

- O juiz as convoca por necessidade: segurança, jurídico, acessibilidade, finanças, saúde, o
  usuário-alvo.
- Depõem com fonte. Não votam.
- Uma testemunha do público (ex.: "dona de restaurante pequeno, 45, usa o sistema há 3 anos") é
  fictícia e declarada como tal na ata. Nunca use uma pessoa real.

## Jurado

**Função:** reagir ao caso como a pessoa da ficha reagiria.

- Fala com o vocabulário, o ritmo e as referências da ficha (campo `voz`).
- Julga pelo que a ficha valoriza (`valores`), teme (`medos`) e repara (`repara_em`), com o viés
  dela (`vies`).
- A personalidade (Big Five, 1 a 5) muda o jeito:
  - abertura alta: curioso
  - amabilidade baixa: direto e crítico
  - estabilidade emocional baixa: ansioso, pensa no pior
  - conscienciosidade alta: confere detalhe
  - extroversão alta: fala muito e se deixa levar pelo grupo
- Não sabe o que a ficha não sabe. Uma pessoa sem internet não conhece "onboarding". Uma criança de
  10 anos não sabe o que é CNPJ.
- Criança com menos de 8 anos: **reação**, não argumento. Exemplo: "aperta o botão colorido, ri,
  larga em 1 minuto", contada pelo responsável da ficha. O voto dela é o que o responsável conclui da
  reação.
- Confiança de 1 (chutei) a 5 (certeza).

**Prompt de subagente:** é gerado pelo `briefing` (não escreva à mão). O modelo abaixo mostra o que ele
contém.

> Você vai interpretar, um de cada vez e de forma independente, 5 pessoas comuns do Brasil que foram
> sorteadas como juradas. Cada uma só sabe o que a ficha dela sabe e fala como ela fala; pode entender
> errado, desconfiar, achar graça, desistir. Não seja o narrador inteligente: seja a pessoa. Criança com
> menos de 8 anos não argumenta: descreva a reação dela, contada pelo responsável, e o voto que o
> responsável tira disso.
>
> O CASO (em linguagem simples): <caso explicado como se explica a um vizinho>
> O QUE O PERITO ENCONTROU: <resumo das provas, em linguagem simples, com ids>
> A PERGUNTA: <pergunta ao tribunal>. OPÇÕES: <opções exatas>.
>
> AS FICHAS: <saída de `python tribunal.py juri ficha ID1 ID2 ID3 ID4 ID5`>
>
> Para cada jurado, responda só em JSON, numa lista: [{"jurado":"BR-xxx","rodada":1,"voto":"<opção
> exata>","confianca":1-5,"motivo":"1 ou 2 frases NA VOZ da pessoa","reparou":"o que ela notou
> primeiro"}]. Não combine votos entre os jurados: cada um é julgado como se os outros não existissem.

## Autor de proposta (concurso)

**Função:** escrever UMA solução para a pergunta aberta, guiada por uma carta (modo de pensar, fluxo e
estratégia).

**Prompt de subagente (um por carta):**

> Escreva uma proposta para: <caso.pergunta>. O caso: <caso.explicacao>. O que existe hoje (status quo):
> <caso.status_quo>. Provas: <P1..Pn>. Sua carta: modo "<modo>", fluxo "<fluxo>", estratégia
> "<estrategia>". Use a carta de verdade: uma resposta genérica com o nome da carta por cima perde. Não
> cite a carta, o tribunal nem outras propostas no texto. Seja específico: passos, números, prazos e como
> medir se deu certo. Não invente fatos: o que não está nas provas vira hipótese a testar. Responda SÓ em
> JSON: {"titulo":"até 8 palavras","resumo":"2 frases em linguagem simples","texto":"a proposta"}

Depois, **um único subagente faz o contraditório** (economia de tokens): primeiro ataca cada proposta, no
formato de ataque do promotor; depois, para cada ataque, responde como o autor daquela proposta
("concede", com a correção, ou "rebate", com prova). Ele grava `{"X1": {"ataques": [...], "respostas":
[...]}, ...}`. O juiz dá o status de cada ataque e as notas da rubrica (`referencias/rubrica.md`).

## Escrivão

**Função:** mantém os autos (`autos.json`) em dia a cada fase e gera a ata (`python tribunal.py ata`).
Antes de cada fase, roda `python tribunal.py validar <autos>`, e depois de cada fase,
`python tribunal.py visualizar <autos>` (a sala ao vivo). Os autos têm de passar sem erro antes da
sentença.

**Prompt de jurado:** nunca escreva à mão. Use `python tribunal.py briefing <autos> --rodada R --lote K
--de N` e passe a saída, sem mudar nada, ao subagente. Ele grava os votos em `votos/` e responde uma
linha. Depois, `python tribunal.py juntar <autos>`.
