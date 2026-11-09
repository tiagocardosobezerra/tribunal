# O rito, fase a fase

Carregado sob demanda pelo `SKILL.md`. Para cada fase: entrada, quem faz, saída nos autos e o **ponto
de controle** do juiz, que precisa passar antes da fase seguinte.

| Fase | Quem | Saída nos autos | Ponto de controle |
|---|---|---|---|
| 0. Autuação | juiz | `caso` | a pergunta é decidível; as opções são exaustivas e excludentes; `caso.explicacao` existe |
| 0b. Concurso (pergunta aberta) | autores, promotor, juiz | `propostas`, `caso.opcoes` | cartas sem repetir; cada ataque com status; finalistas sem FATAL de pé, mais o status quo |
| 1. Convocação | `juri convocar` | `juri.sessao`, `juri.convocados` | 25 convocados; impedimentos com motivo |
| 1b. Recusas | promotor, defesa | `juri.recusas` | até 3 por lado, com motivo, olhando só as fichas |
| 1c. Conselho | `juri conselho` | `juri.conselho` | 7 sorteados entre os que sobraram |
| 2. Instrução | perito | `provas` | toda prova com fonte; lacunas declaradas |
| 3. Rodada 1 | os 25 | `votos` (rodada 1) | 25 votos, cada um na voz da ficha, nenhum fora das opções |
| 4. Debates | promotor, defesa, testemunhas | `acusacao`, `defesa`, `testemunhas` | todo ataque com id, gravidade, onde e contraexemplo; toda tese cita prova ou se declara alegação |
| 4b. Réplica | defesa | `defesa.respostas` | um "concede" ou "rebate" para cada ataque |
| 5. Deliberação e rodada 2 | os 7 | `votos` (rodada 2) | 7 votos; quem mudou diz por quê |
| 4b. Checagem do FATAL (rito 2) | verificador (`tribunal-advogado`) | `acusacao.teses[].checagem` | junto com a réplica; confirma, rebaixa ou derruba cada FATAL |
| 6. Sentença | juiz | `sentenca`, `sentenca.ataques` | `validar` sem erro; status honesto de cada ataque; FATAL pendente não deixa dar o veredito pleno |
| 6b. Plano (rito 2) | redator (`tribunal-advogado`) | `plano` | cobre cada condição, sem conflito; o passo 1 vira o próximo passo |
| 7. Instância final | usuário | `decisao_usuario` | acatou ou recorreu, nas palavras do usuário |

## Modo completo (subagentes)

O roteiro abaixo serve para quando a ferramenta Agent existe. Rode antes `python tribunal.py plano` para
saber o custo.

1. **Fases 0, 1 e 2 neste contexto.** A perícia de app e código precisa das ferramentas da sessão
   (navegador, terminal).
2. **Concurso de propostas (só para pergunta aberta):**
   - Um subagente por carta escreve uma proposta (`propostas cartas`, 3 por padrão).
   - **Um** subagente faz o contraditório: ataca todas e depois responde como cada autor.
   - O juiz dá as notas, e `propostas placar` define as finalistas.
3. **Recusas:** neste contexto, como promotor e como defesa. Cada lado olha só as fichas curtas.
4. **Rodada 1:**
   - Gere os prompts com `briefing --rodada 1 --lote K --de 5` e passe cada um, literal, a um subagente
     com `model: "sonnet"`. Jurados só interpretam fichas. Os 5 rodam em paralelo.
   - Cada subagente grava `votos/r1-loteK.json` e responde uma linha.
   - Rode `juntar`.
   - **Lote que falhou roda de novo.** Nunca preencha um voto que falta.
5. **Debates:** 2 subagentes em paralelo, promotor (ataques estruturados) e defesa (teses). Depois, 1
   subagente de réplica da defesa, com os ataques à vista.
6. **Rodada 2:** `briefing --rodada 2 --lote 1 --de 1` para um subagente `sonnet`, e depois `juntar`. A
   deliberação, quando narrada, sai dos motivos de quem mudou de voto.
7. **Sentença, ata, sala e cartão:** neste contexto.

Contexto limpo: os subagentes gravam em disco e respondem uma linha. O orquestrador não lê o que não
precisa.

## Modo rápido (um contexto)

O rito e os comandos são os mesmos, inclusive o `briefing`: use a saída dele como roteiro de cada lote. Para a rodada 1, interprete os 25 em sequência. Antes de cada
jurado, releia a ficha dele, e escreva o voto antes de passar ao próximo. Não volte para ajustar votos
anteriores. Na entrega, diga que o caso foi julgado no modo rápido: os votos são menos independentes.

## Plenário (todos os 100)

Use só a pedido: "quero ouvir os 100", "plebiscito". Os 100 dão só a reação rápida (voto, confiança e
1 frase), em 10 subagentes de 10. Não há conselho nem debate: o resultado é uma **distribuição**, que
serve para ver como cada segmento reage. A sentença sai como "parecer do plenário", com a ressalva.
`juri listar` dá as fichas curtas, e `juri ficha` as completas.

## Recurso

Quando o usuário recorre:

1. Registre o motivo em `decisao_usuario.recurso`.
2. Abra autos novos, com `caso.recurso_de` apontando para o caso anterior (a REF no cartão ou a pasta
   dos autos).
3. Nova convocação com `juri convocar --autos <autos novos>`: quem já julgou o caso de origem (convocados,
   reforço e conselho) fica de fora e volta para o topo do saco, sem perder a vez.
4. Junte a prova nova que motivou o recurso e as provas antigas que continuam valendo.
5. O novo julgamento corre inteiro. No cartão, ele é salvo como nova versão do mesmo caso:
   `--motivo "recurso: <motivo>"`.
