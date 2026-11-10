# Jurado de outra família de modelos no teste cego (2026-11-10)

## Como foi feito

- **O modelo:** Qwen 3 com 4 bilhões de parâmetros (Alibaba), rodando localmente pelo Ollama, só no processador, sem placa de vídeo.
- **O que ele julgou:** os mesmos 30 casos do teste cego, com os **mesmos 5 jurados** do lote do Haiku e o mesmo briefing.
- **Quanto levou:** cerca de 140 segundos por caso.
- **Uma falha:** em 1 caso (c26), o modelo não devolveu votos válidos em 3 tentativas.
- **Os votos:** estão em `externo/`.
- **Para refazer a análise:** `python ferramentas/analise_externo.py <pasta da validação> validacao/cegos/gabarito.json`.

## Resultado

| Júri | Casos | Acerto | Brier (chute = 0,25) | Chance de ser acaso |
|---|---|---|---|---|
| Qwen 3 4b sozinho (5 jurados) | 29 | 16 de 29 | 0,264 | 0,36 |
| Haiku sozinho (os mesmos 5 jurados) | 30 | 18 de 30 | 0,237 | 0,18 |
| Sonnet sozinho | 30 | 16 de 30 | 0,292 | 0,43 |
| Opus sozinho | 30 | 18 de 30 | 0,237 | 0,18 |
| Júri Claude (Sonnet + Haiku + Opus) | 30 | 18 de 30 | 0,227 | 0,18 |
| Júri misto (Sonnet + Qwen + Opus) | 29 decididos | 17 de 29 | 0,239 | 0,23 |

- **Nenhum júri prevê o desfecho melhor que o acaso.** Isso vale para cada modelo sozinho e para as duas misturas.
- **A diversidade é real.** Com a mesma ficha de jurado, o Qwen votou diferente do Haiku em **38% dos votos** (55 de 145). Um modelo de outra família muda a opinião da sala.
- **A diversidade não trouxe acerto.** Trocar o Haiku pelo Qwen deixou o júri igual ou um pouco pior.
- **Vazamento baixo:** 5 dos 145 votos do Qwen reconheceram o produto real.

## O que isso quer dizer

O jurado externo serve para o que foi pensado: ouvir uma opinião que não é do Claude, e com isso medir se o veredito
depende do modelo. Ele não serve para acertar mais. O resultado reforça o teste cego: o Tribunal vale pelo processo
(provas, contraditório, juiz independente, plano com critério de abandono), não como previsão de mercado.
