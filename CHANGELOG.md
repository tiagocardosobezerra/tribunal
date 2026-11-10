# Changelog

Todas as mudanças relevantes do Tribunal. O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e as versões seguem o [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.7.0] — 2026-11-10

### Novo
- **Dossiê em PDF** (`tribunal.py exportar <autos>`), para levar o julgamento a uma discussão. Traz:
  - capa com o veredito, a confiança e o malhete em pixel art;
  - resumo de uma página;
  - o caso e as provas com fonte;
  - o contraditório, com gravidade, checagem e status;
  - o júri, com barras por segmento e por modelo;
  - as vozes do conselho, a sentença e o plano;
  - uma página "Como ler este documento", que diz o que o júri mede e o que não mede;
  - em anexo, os convocados.
  A capa traz o **SHA-256 do autos.json**, para quem recebe conferir que o PDF veio daquele arquivo. O PDF é impresso
  por Edge, Chrome ou Chromium em modo headless; sem navegador, sai o HTML pronto para imprimir.

### Mudou
- O lote externo tenta até 3 vezes quando o modelo erra o JSON, aceita o modo de pensar do Qwen 3 e espera até
  15 minutos (`TRIBUNAL_EXTERNO_TEMPO`), para rodar em CPU.

## [1.6.0] — 2026-11-09

### Novo
- **Jurado de outra família de modelos** (`motor/externo.py`, `tribunal.py externo`). Com
  `TRIBUNAL_EXTERNO_MODELO` definido, o lote 2 do júri roda em qualquer API compatível com a da OpenAI: OpenRouter
  (GPT, Gemini, Llama...), Ollama local ou Groq. A `onda` devolve esse lote como comando, ao lado dos subagentes.
  É opcional e desligado por padrão, porque o briefing sai da máquina; a chave nunca vai para os autos.
- **Modelo de issue "Conte o desfecho"**: quem usou o Tribunal conta como a decisão terminou, e esses casos calibram
  a confiança.

### Corrigido
- O Memory Card contava 0 jurados nos casos convocados com `juri convocar --autos`.

## [1.5.0] — 2026-11-09

A versão que mede de verdade, mesmo quando o número não ajuda.

### Novo
- **Juiz independente (rito 4, casos novos).** A sentença sai de um subagente que só lê os autos e não fez a
  perícia (`debate --papel juiz`, fase "Sentença" da `onda`). As falhas que ele acha (J1...) entram como ataques de
  pé. O `validar` recusa, no rito 4, sentença escrita por quem conduziu o processo.
- **Validação cega** (`validacao/cegos/`): 30 produtos, descrições escritas por um agente separado, gabarito em
  arquivo à parte (`--gabarito`) e uma linha de base de um modelo sozinho (`--base`). **Resultado: o júri acertou 18
  de 30, Brier 0,227, perto do acaso.** O piloto de 1.4.0 (8 de 9) estava inflado. O README agora diz que o veredito
  não é previsão de sucesso.
- **Custo de ponta a ponta medido** num caso real: 279 mil tokens nos subagentes (cerca de US$ 1) e a orquestração,
  que pesa mais e cresce com a conversa (`validacao/custo-caso-real-2026-11-09.md`).
- **`perito-feito`** registra uma rodada do perito e apaga o plano; no máximo 2 rodadas, depois o que faltar vira
  hipótese.

### Corrigido (achado no caso real)
- As falhas do juiz eram tratadas como ataques sem réplica e travavam o rito.
- O `juntar-debate` apagava as falhas do juiz ao reler o promotor.
- Caminhos com mais de 260 caracteres quebravam no Windows.
- As pendências do perito podiam abrir rodadas sem fim.

## [1.4.0] — 2026-11-09

A versão que responde às três críticas mais duras: júri de um modelo só, validade nunca medida e orquestração
pesada.

### Novo
- **Júri com 3 modelos.** Cada lote de jurados roda num modelo diferente (Sonnet, Haiku e Opus, alternados), com
  os agentes `tribunal-jurado-haiku` e `tribunal-jurado-opus`. O `placar` mostra a maioria de cada modelo e avisa
  quando eles discordam; a confiança sugerida cai 10 pontos nesse caso.
- **Firmeza por lote.** Além da reamostragem por voto, o placar sorteia lotes inteiros: votos da mesma chamada não
  são independentes, e essa firmeza é a mais honesta das duas.
- **Validação contra a realidade** (`tribunal.py validacao preparar|resultado`): 12 produtos de desfecho
  conhecido, descritos como eram antes do lançamento e sem o nome. Mede acerto, Brier e **vazamento** (quantos
  jurados reconheceram o produto real). Primeiro resultado: 8 de 9 casos decididos, Brier 0,141 contra 0,25 do
  chute, 5% dos votos com reconhecimento (`validacao/resultado-2026-11-09.md`).
- **`tribunal.py onda`.** Uma fase com subagentes vira um comando: os briefings são gravados e as chamadas saem
  prontas (tipo de agente e prompt com caminhos absolutos). `onda --juntar` junta votos e debate, aplica a parada
  antecipada e avisa o reforço.

## [1.3.0] — 2026-11-09

A versão que transforma a sentença em plano. Medida em um julgamento real contra um torneio de 16 agentes
(veja "Resultados" no README).

### Novo
- **Rito 3** (casos novos nascem nele):
  - **Redator do plano.** A sentença vira passos numerados, metas por grupo, pelo menos 6 testes com o resultado
    esperado calculado, critério de abandono com 2 ou mais gatilhos e a certeza explicada pelas lacunas.
  - **Plano atacado e revisado.** Um promotor do plano procura furos (contas, metas que não fecham, passos
    impossíveis) e o redator responde a cada um antes de o plano chegar ao usuário.
  - **Pendências do perito.** O que dá para verificar agora (um site público, uma conta, um documento) nunca vira
    tarefa do usuário: o perito resolve antes de o plano seguir.
- **Checagem dupla do FATAL.** Todo ataque fatal é reconferido por um verificador independente, que confirma,
  rebaixa ou derruba. Rótulo, arredondamento ou texto não é fatal.
- **Status honesto.** "Corrigido" só quando a correção já foi feita e conferida; o que foi só prometido é
  "correção proposta". FATAL pendente trava o veredito pleno.
- **Coerência da sentença.** O `validar` recusa a sentença cujo plano não cobre cada condição ou aponta
  contradição.
- **`tribunal.py entrega`.** A resposta final montada direto dos autos; `--enxuta` deixa só decisão, plano,
  riscos e condições.
- **Duas linguagens.** "Tribunal" (os termos do rito) e "Natural" (palavras do dia a dia), com um dicionário
  único para conversa, ata, placar e sala. Os autos guardam sempre os termos oficiais.
- **Sala:** seletor de linguagem; linha do tempo com todas as fases desde o início; plateia simétrica com
  corredor central e porta no fundo; o reforço entra, vota de pé junto ao gradil e sai; a aba Júri separa
  convocados e reforço.

### Mudou
- O reforço do júri só é chamado com a sala firme em menos de **80%** (antes, 90%). Nos casos medidos, entre 80%
  e 90% o reforço só confirmou o líder.
- No recurso, quem julgou o caso de origem fica fora do júri novo; o reforço nunca repete quem já está na sala.
- `juri convocar --autos` e `juri conselho --autos` gravam a sessão, os convocados, as recusas e o conselho
  direto nos autos; `--json` devolve JSON.
- O custo do advogado enxuto agora é medido (~13 mil tokens por chamada).

### Corrigido
- `reforco` e `parar` não quebram mais quando recebem a pasta do caso.
- `novo` não cria uma pasta dentro da outra quando roda de dentro de `tribunal-autos`.
- Os autos aceitam `id` onde o esperado era `jurado` (recusas) ou `ataque` (sentença).
- Ficha do jurado com maiúscula e ponto; apelidos como "Dona Cleo" e "Seu Ed" não viram só "Dona" e "Seu".

## [1.1.0] — 2026-11-09

### Novo
- **Agentes enxutos** (`tribunal-jurado`, `tribunal-advogado`, `tribunal-autor`): só Ler e Gravar, ~84% menos
  tokens por chamada que um agente completo.
- **Parada antecipada** da rodada 1 e **reforço** do júri quando o placar fica apertado.
- **Firmeza por reamostragem** (2.000 sorteios) e **confiança sugerida** pela rubrica.
- **Concurso de propostas** para perguntas abertas, com cartas de estratégia sem repetição.
- **Modo rápido**, sem subagentes, para decisões pequenas e reversíveis.
- `tribunal.py comparar` para medir dois julgamentos do mesmo caso.

## [1.0.0] — 2026-11-09

Primeira versão: perito, promotor, defesa, júri de 100 brasileiros fictícios calibrados pelo IBGE, voto
secreto dos 25, conselho de 7, sentença com confiança, sala em pixel art com o malhete e o Memory Card.

[1.7.0]: https://github.com/tiagocardosobezerra/tribunal/releases/tag/v1.7.0
[1.6.0]: https://github.com/tiagocardosobezerra/tribunal/releases/tag/v1.6.0
[1.5.0]: https://github.com/tiagocardosobezerra/tribunal/releases/tag/v1.5.0
[1.4.0]: https://github.com/tiagocardosobezerra/tribunal/releases/tag/v1.4.0
[1.3.0]: https://github.com/tiagocardosobezerra/tribunal/releases/tag/v1.3.0
