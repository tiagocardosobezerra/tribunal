# Custo medido de um julgamento completo (2026-11-09)

Caso: o modelo de negócio do próprio Tribunal, uma decisão real entre 3 caminhos. Rito 4, completo:
- júri misto;
- juiz independente;
- checagem do FATAL;
- plano atacado e revisado.

## Subagentes

25 chamadas, somando **279 mil tokens**:

| Papel | Chamadas | Tokens | Modelo |
|---|---|---|---|
| Jurados da rodada 1 | 5 lotes | 63 mil | 2 Sonnet, 2 Haiku, 1 Opus |
| Conselho (rodada 2) | 3 lotes | 41 mil | Sonnet, Haiku, Opus |
| Promotor, defesa, réplica, checagem | 4 | 46 mil | modelo da conversa (Opus) |
| Juiz independente | 1 | 22 mil | Opus |
| Plano (3 rodadas, por causa das pendências do perito), ataque e revisão | 5 | 111 mil | Opus |

Pelos preços oficiais (Sonnet US$ 2/M de entrada, Opus US$ 4/M, Haiku US$ 0,10/M), os subagentes custaram **cerca de US$ 1,00**.

## Orquestrador (a conversa principal)

- 70 respostas do modelo.
- **14,9 milhões de tokens relidos do cache.**
- 93 mil tokens de contexto novo.
- 34 mil tokens de saída.
- **Cerca de US$ 4,10** em Opus: cache lido a US$ 0,20/M, escrita a US$ 5/M, saída a US$ 20/M.

O número está inflado. O caso rodou no fim de uma sessão longa, com cerca de 210 mil tokens de contexto relidos a cada passo, e no meio houve correção de 4 bugs que o caso revelou. Numa sessão nova, com cerca de 40 mil tokens de contexto, os mesmos 70 passos releriam perto de 3 milhões de tokens, **cerca de US$ 0,60**.

## Conclusões

- **O "~260 mil tokens" do README conta só os subagentes.** Em tokens processados, a orquestração na conversa principal custa mais que eles, e cresce com o tamanho da conversa.
- **O júri misto ficou mais barato, não mais caro.** Haiku custa 1/20 do Sonnet, e o Opus custa o dobro.
- **Bugs que o caso revelou e que foram corrigidos:**
  - as falhas apontadas pelo juiz eram tratadas como ataques sem réplica e travavam o rito;
  - o `juntar-debate` apagava essas falhas;
  - caminhos acima de 260 caracteres quebravam no Windows;
  - as pendências do perito podiam abrir rodadas sem fim.
