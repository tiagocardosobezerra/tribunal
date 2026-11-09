---
name: tribunal
description: "Leva qualquer coisa a julgamento ou busca a melhor solução: ideia, app, código, decisão, documento. Pergunta aberta vira concurso de propostas (cartas de estratégia, ataques, rubrica). Um perito traz provas reais (pesquisa, teste do app, execução do código), o promotor ataca com gravidade (FATAL, GRAVE, LEVE), a defesa concede ou rebate e um júri de 25 brasileiros fictícios, em rodízio de 100 calibrados pelo IBGE (1 a 100 anos), vota em segredo; 7 dão o veredito. Sentença com confiança, placar por segmento, ponto de virada, próximo passo e critério de abandono; o usuário acata ou recorre. Abre a sala em pixel art com o malhete. Memory Card e calibração. Use para: 'leva a julgamento', 'tribunal', 'o que o povo acharia', 'devo fazer X ou Y?', 'como resolvo X?', 'essa ideia é boa?', 'testa meu app', 'esse código vai pra produção?'. Não use para nota em rubrica (O Crítico) nem para escrever o artefato."
---

# Tribunal

O Tribunal não opina: ele **instrui um processo**. Há provas, acusação, defesa, um júri popular que vota
em segredo e uma sentença fundamentada. Quando a pergunta é aberta, ele primeiro **gera e põe à prova
várias soluções**, e o júri escolhe entre as finalistas. A última palavra é sempre do usuário.

Rode os comandos da pasta da skill: `python tribunal.py ...` (sem `python`, use `python3`, sem perguntar).
**Nunca peça ao usuário para digitar um comando.** Você roda e mostra o resultado. Perdeu o fio? Rode
`python tribunal.py proximo <autos>`.

## Regras que valem sempre

1. **Rito completo**, mesmo no modo rápido. Nunca dê o veredito antes das provas e do voto.
2. **Prova tem fonte** (URL, arquivo e linha, saída de comando, depoimento do usuário). Sem fonte, é
   alegação. Nunca invente dado, citação ou resultado de teste.
3. **O júri é o elenco** de `juri/brasil.json`, convocado pelo `juri convocar`. Nunca invente, troque ou
   altere um jurado. Cada um julga só com o que a ficha dele sabe.
4. **O orquestrador nunca vota.** O prompt dos jurados sai do `briefing`, literal. Os votos entram pelo
   `juntar`. Se um lote falhar, ele roda de novo.
5. **Jurado fala como a pessoa da ficha.** Criança com menos de 8 anos reage, não argumenta.
6. **O voto da rodada 1 é secreto** e acontece antes dos debates.
7. **Contraditório estruturado.**
   - Cada ataque tem id, gravidade (FATAL, GRAVE, LEVE), o ponto atacado e um contraexemplo.
   - A defesa concede ou rebate cada ataque. Rebater só insistindo deixa o ataque de pé.
   - **FATAL de pé trava o veredito pleno.** No rito 2, FATAL só com correção proposta também trava.
   - **Todo FATAL tem checagem dupla** (`debate --papel checagem`): outro agente refaz a conta ou relê a prova
     e confirma, rebaixa ou derruba. Rótulo, arredondamento ou texto não é FATAL.
8. **Sem bajulação.** Se a rodada 1 sair unânime, o juiz manda apertar a tese que faltou.
9. **O usuário é a instância final**: acata ou recorre. O recurso vai a um júri novo.
10. **Privacidade e "sim".** Os autos não guardam senha, token, CPF nem dado pessoal real. O Memory Card só
    grava com `--confirmar`, depois do "sim".

## Modos e custo

Um subagente `general-purpose` custa cerca de 70 mil tokens, quase tudo custo fixo de entrada. O
`tribunal-jurado` custa cerca de 11 mil (medido). O custo cresce com o **número** de subagentes, não com o
tamanho do trabalho.

- **completo** (padrão), com **agentes enxutos** (só Ler e Gravar; custam uma fração de um `general-purpose`):
  - jurados em até 5 lotes, **um modelo por lote** (sonnet, haiku, opus alternados: `tribunal-jurado`,
    `tribunal-jurado-haiku`, `tribunal-jurado-opus`). O `placar` mostra se os modelos concordam;
  - promotor, defesa, réplica e contraditório no `tribunal-advogado`; autores no `tribunal-autor`. O prompt
    sai de `debate <autos> --papel P [--id X1]`, literal, e a resposta entra com `juntar-debate`;
  - sem os agentes instalados, use `general-purpose` com o `model` do lote;
  - **`python tribunal.py onda <autos>`** faz cada fase com subagentes de uma vez: grava os briefings e lista
    as chamadas prontas (tipo de agente e prompt). Lance todas juntas; depois `onda <autos> --juntar` junta
    votos e debate, aplica parada antecipada e avisa o reforço;
  - **reforço:** se, com os 25 votos, `reforco <autos>` disser REFORÇO (sala estável em menos de 80%),
    rode os lotes 6 a 10 com `--de 10`;
  - **parada antecipada:** rode os lotes 1 a 3; se `parar` disser PARE, os lotes 4 e 5 são dispensados;
  - promotor, defesa e réplica com o modelo da conversa;
  - concurso com 3 propostas e um subagente só para o contraditório (ataques e respostas).
- **rápido**: zero subagentes, tudo nesta conversa. Os votos ficam menos independentes: diga isso na
  entrega.

Antes de começar, rode `python tribunal.py plano --reversivel sim|nao --impacto baixo|medio|alto
[--propostas 3]`. Ele sugere o modo (decisão reversível e pequena vai para o rápido). Diga em uma linha o
modo, os subagentes e os tokens.

## O rito

Detalhes:
- Fases e modos: `referencias/rito.md`.
- Papéis e prompts: `referencias/papeis.md`.
- Perícia por tipo de caso: `referencias/tipos-de-caso.md`.
- Rubrica e confiança: `referencias/rubrica.md`.
- Formato dos autos: `referencias/autos.md`.

**Narração:** ao fim de cada fase, rode `python tribunal.py fase <autos> <fase>`. O comando carimba a hora
(é a métrica de tempo), atualiza a sala ao vivo e imprime **uma linha**, que você repete na conversa.
Assim o usuário nunca espera no escuro.

### 0. Autuação

1. **Caso novo:** rode `python tribunal.py novo "<título>" --tipo <tipo>`. Se ele pedir, pergunte **uma
   vez** se os casos podem ficar em `~/tribunal-autos` e rode `pasta --fixa` (sim) ou `pasta --sessao`
   (não).
2. **Preencha os autos.**
   - Pergunta: uma frase decidível.
   - Opções de voto. O padrão é `Procedente`, `Procedente com condições`, `Improcedente`.
   - `caso.explicacao`: o caso explicado como a um vizinho. É o texto que todo jurado recebe.
   - Pergunta aberta: `caso.aberta: true` e `caso.status_quo`.
   - No máximo 3 perguntas ao usuário.
3. **Jurisprudência e desfechos:** rode `cartao buscar <termos>` e `pendencias`. Se houver caso antigo sem
   desfecho, pergunte em uma linha como terminou. É o que calibra a confiança.

### 0b. Concurso de propostas (pergunta aberta)

1. Rode `propostas cartas` (3 cartas, sem repetir nenhuma parte entre elas). Um subagente por carta escreve
   uma proposta.
2. **Um** subagente faz o contraditório: ataca cada proposta e depois responde como cada autor (concede ou
   rebate).
3. O juiz dá o status de cada ataque e as notas da rubrica. Rode `propostas placar`.
4. As 2 melhores sem FATAL de pé, mais o status quo, viram `caso.opcoes`. Cada proposta tem um `apelido`
   de 2 ou 3 palavras: na sala e na conversa, fale sempre pelo apelido ("Fazer à mão primeiro"), nunca só
   pelo código (X2). O status quo é "Deixar como está".

### 1. Convocação, recusas e conselho

1. Convoque: `juri convocar --autos <autos> [--impedir "idade<8"]` (grava sessão e convocados nos autos). Saem 25 do rodízio,
   sem repetir antes de os 100 servirem e sem perfis parecidos na mesma sessão. Impedimento só com motivo.
   Em caso de código, menores de 12 já são impedidos.
2. **Abra a sala:** `python tribunal.py abrir` (sem argumento, abre o último caso). Diga ao usuário:
   "A sala abriu no seu navegador; clique em Abrir a sessão para ligar o som". Ela fica ao vivo até a
   sentença.
3. Recusas: promotor e defesa recusam até 3 cada, olhando só as fichas, com motivo. Depois:
   `juri conselho <sessão> --acusacao IDS --defesa IDS --autos <autos>`, que sorteia os 7 e grava; escreva os
   motivos em `juri.recusas`.

### 2. Instrução

O perito levanta as provas conforme o tipo do caso:
- **app:** usa o app como os jurados usariam.
- **código:** roda testes e lint.
- **ideia ou decisão:** pesquisa mercado e taxa-base.

O que ele não conseguiu verificar entra como `lacuna`. O juiz aceita ou recusa cada prova, com motivo.

### 3. Rodada 1: voto secreto dos 25

1. `onda <autos>` gera os lotes 1 a 3 (um modelo por lote) e lista as chamadas; lance em paralelo.
2. `onda <autos> --juntar`. Se o `placar` sinalizar voto fora do personagem que não seja citação, refaça o lote.
   - **PARE:** a liderança já é estável em 95% ou mais das reamostragens, com 15 votos ou mais. Os
     lotes 4 e 5 ficam dispensados, e isso é registrado nos autos.
   - **CONTINUE:** rode os lotes 4 e 5 e junte.

### 4. Debates e réplica

- **Acusação:** ataques estruturados, com pré-mortem, inversão, riscos, 2ª ordem e taxa-base.
- **Defesa:** steelman, potencial, opções escondidas e o teste mais barato.
- Os dois rodam em paralelo.
- **Réplica:** depois, a defesa concede (com a correção) ou rebate (com prova) cada ataque.
- **Testemunhas:** entram quando falta conhecimento técnico. Não votam.

### 5. Rodada 2

Rode `briefing <autos> --rodada 2 --lote 1 --de 1` para um subagente `sonnet`, depois `juntar`. Quem
mudar de voto diz por quê.

### 6. Sentença: o juiz independente

**Rito 4** (casos novos): você não escreve a sentença. A `onda` chama o **juiz independente** (`debate --papel
juiz`), um subagente que só lê os autos e não fez a perícia. Ele dá o veredito (a maioria do conselho; se discordar,
`voto_vencido`), o status de cada ataque, as falhas que a acusação não viu (J1...), a confiança a partir da
sugerida, condições, ponto de virada, próximo passo e critério de abandono. O `validar` recusa, no rito 4, uma
sentença que não veio dele. Nunca edite a sentença; se ela estiver errada, rode o juiz de novo com os autos corrigidos.

Depois, o **redator do plano** (`--papel plano`) transforma a sentença em passos, metas por grupo, pelo menos 6
testes, critério de abandono e certeza explicada. Um promotor do plano o ataca (`--papel plano_ataque`) e o redator
revisa (`--papel plano_revisao`). O que dá para verificar agora vira `pendencias_do_perito`: o perito resolve, junta
como prova e roda `perito-feito <autos>`. No máximo 2 rodadas; depois, o que faltar vira hipótese.

### 7. Instância final

1. Entregue a resposta (formato abaixo) e registre `decisao_usuario`.
2. Gere a ata: `ata <autos> -o <pasta>/ata.md`.
3. Rode `fase <autos> sentenca`. A sala termina com o malhete; se o navegador bloquear o som, ela pausa
   num botão "Bater o malhete".
4. Ofereça o Memory Card: `cartao enviar` (prévia) e `--confirmar` depois do "sim".
5. Recurso: júri novo (com `caso.recurso_de`, o `convocar --autos` deixa de fora quem já julgou), versão nova do caso.
6. Desfecho: `cartao desfecho`, quando o usuário souber como terminou.

## O que entregar ao usuário (no máximo 5 blocos)

1. **Veredito e confiança.**
2. **Placar** (25 e 7) e onde o júri se dividiu.
3. **Próximo passo.**
4. **Critério de abandono**, em uma linha.
5. **"Acata ou recorre?"**, com o link da ata. Nota de 1 a 5, opcional, na mesma linha.

Falas dos jurados, ataques e condições ficam na ata e na sala. A entrega sai pronta de
`python tribunal.py entrega <autos>` (`--enxuta`: só decisão, plano, riscos e condições). Mostre esse texto.

## Linguagem: tribunal ou natural

No primeiro caso, se `python tribunal.py linguagem` disser que o usuário não escolheu, pergunte uma vez: "Prefere
termos de tribunal ou linguagem natural?" e grave com `linguagem tribunal|natural`. "Linguagem natural" ou "modo tribunal"
na conversa trocam a qualquer hora. O rito, a sala e o juiz de peruca não mudam; só as palavras. No modo natural:
- entregue com o dicionário de `motor/linguagem.py`: Vale a pena / Vale, se ajustar / Não vale; os 7 que decidem;
  problema que derruba, sério ou pequeno; certeza; "Concorda ou quer outra rodada?";
- escreva fundamentação, condições e próximo passo sem jargão; `ata` e `placar` já saem no modo escolhido;
- os autos guardam sempre os termos oficiais (validação, Memory Card e calibração dependem deles).

## Mudanças no rito

Mudança no rito só vale depois de julgar de novo 2 casos já decididos, na versão antiga e na nova. Compare
com `python tribunal.py comparar <autos_antigo> <autos_novo>`. Se o veredito ou os segmentos mudarem, a
mudança volta.

## Comandos

| Comando | O que faz |
|---|---|
| `status` · `plano --modo completo\|rapido [--propostas N]` | situação do rodízio e do cartão; custo em subagentes e tokens |
| `novo "título" --tipo X` · `pasta --fixa\|--sessao` | cria o caso; onde os casos ficam |
| `abrir [autos]` | abre a sala (sem argumento: o último caso) |
| `fase AUTOS FASE` | carimbo de hora, sala ao vivo e uma linha de narração |
| `proximo AUTOS` | a próxima fase e o comando exato |
| `propostas cartas` · `propostas placar AUTOS` | concurso de propostas |
| `juri convocar\|conselho\|ficha\|listar\|cotas\|especial` | o júri |
| `briefing AUTOS --rodada R --lote K --de N` · `juntar AUTOS` | prompt literal dos jurados; votos de volta |
| `validar` · `placar` · `ata AUTOS -o ARQ` · `visualizar AUTOS` | autos, placar (com a estabilidade), ata, sala |
| `parar AUTOS` · `reforco AUTOS` | parada antecipada; mais 25 jurados em caso apertado |
| `debate AUTOS --papel P [--id X]` · `juntar-debate AUTOS` | prompt literal dos advogados e autores; respostas de volta |
| `pendencias` | casos sem desfecho no Memory Card |
| `comparar AUTOS_A AUTOS_B` | se dois julgamentos chegaram ao mesmo lugar |
| `cartao iniciar\|catalogo\|buscar\|enviar\|marcar\|desfecho\|calibracao` | Memory Card |

Referências: `rito.md`, `papeis.md`, `rubrica.md`, `tipos-de-caso.md`, `autos.md`, `juri.md`,
`populacao-brasil.md` e `memory-card.md`, todas em `referencias/`.
