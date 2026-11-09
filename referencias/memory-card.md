# Memory Card: o cartão dos casos julgados

Carregado sob demanda pelo `SKILL.md`. É como o memory card de um videogame: cada caso julgado fica
salvo como um "save", com versão e histórico. O save serve como **jurisprudência** para os próximos
casos e, quando o desfecho chega, como **calibração** do tribunal.

**É o mesmo cartão do Vegapunk e do Senku.** O cartão é um repositório git seu no GitHub, privado por
padrão, com uma pasta por solução. Os casos do Tribunal ficam em `saves/tribunal/`. O Tribunal só grava
a própria pasta e o `CATALOGO.md`, e gera o catálogo no mesmo formato das outras soluções. Qual é o seu
cartão fica só nesta instalação, em `local/memory_card.json`, fora do git e do pacote.

## O que é preciso

- O [GitHub CLI](https://cli.github.com/) (`gh`) instalado e autenticado (`gh auth login`). Nenhum
  token fica na skill.
- O `git`.

Numa sandbox, como a do claude.ai, não há `gh` autenticado nem a pasta do cartão. Lá, os comandos
recusam e dizem por quê. Nesse caso, entregue a ata e os autos ao usuário e deixe o envio para o Claude
Code.

## Ligar ao cartão (uma vez)

Ligue ao repositório do cartão:

```bash
python tribunal.py cartao iniciar --repo SEU_USUARIO/memory-card
```

- Se o repositório já existe (o do Vegapunk ou do Senku), ele é usado. Se estiver público, é recusado.
- Se ainda não existe, ele é criado **privado**.
- Se a pasta `~/memory-card` já é um clone dele, o mesmo clone é reaproveitado.
- `--pasta DIR` escolhe outra pasta.
- `--publico` aceita um cartão público. Use só de propósito.
- Sem GitHub, `cartao iniciar --pasta DIR` cria um cartão só local, com git sem remoto.
- As variáveis `TRIBUNAL_MEMORY_CARD_REPO` e `TRIBUNAL_MEMORY_CARD_DIR` têm precedência sobre a
  configuração. `TRIBUNAL_MEMORY_CARD_DIR=-` desliga o cartão.

## Como o cartão é organizado

```
memory-card/
├── CATALOGO.md                        gerado a cada envio
└── saves/
    ├── vegapunk/...  senku/...        (o Tribunal não toca)
    └── tribunal/<categoria>/<secao>/<caso>/
        ├── README.md                  a ata, com a sentença e o desfecho
        ├── ficha.json                 versão, status, veredito, confiança, acatou, júri, desfecho, histórico
        └── autos.json                 os autos completos
```

- **Categoria** é o tipo do caso: Ideias, Apps, Código, Decisões, Documentos ou Outros.
- **Seção** é a área (`caso.area`).
- **Caso** é o título.
- Para mudar qualquer um dos três, use `--categoria`, `--secao` ou `--artigo`.
- **REF** é o caminho do save: `tribunal/<categoria>/<secao>/<caso>`, com os nomes das pastas.
- **Status:**
  - `em-uso`: o usuário já disse se acata ou recorre.
  - `rascunho`: o usuário ainda não respondeu.

## Comandos

Todos rodam da pasta da skill. Os que gravam mostram uma **prévia** primeiro.

| Comando | O que faz |
|---|---|
| `cartao catalogo [--todos] [--json]` | lista os casos do Tribunal (`--todos`: de todas as soluções) |
| `cartao buscar TERMOS` | jurisprudência: procura casos parecidos |
| `cartao enviar AUTOS [--motivo M] [--confirmar]` | salva um caso novo ou uma versão nova (recurso, prova nova) |
| `cartao marcar REF --status em-uso\|rascunho` | muda o status |
| `cartao desfecho REF --resultado acertou\|parcial\|errou [--nota N]` | registra como a decisão terminou na vida real |
| `cartao calibracao` | compara a confiança das sentenças com os desfechos |

### Jurisprudência

Na autuação, rode `cartao buscar` com as palavras do caso. Cite os casos parecidos na abertura:
"Em 03/2026 este tribunal julgou um app parecido: veredito X, desfecho Y".

### Desfecho e calibração

Uma sentença diz "Procedente com condições, confiança 70%". Meses depois, o usuário conta como foi.

1. Registre o resultado com `cartao desfecho`.
2. Com alguns desfechos registrados, rode `cartao calibracao`. Ele mostra o Brier (0 é perfeito; 0,25
   é o mesmo que chutar 50%), o acerto real por faixa de confiança e se o usuário acerta mais quando
   acata ou quando recorre.
3. O juiz usa isso para ajustar a confiança das próximas sentenças.

Na autuação de um caso novo, se houver casos antigos sem desfecho, pergunte por um deles em uma linha.

## Proteções

- **Privado por padrão.** O cartão confere a visibilidade do repositório antes e depois de cada
  commit.
- **Avisos na prévia.** Se os autos têm algo parecido com CPF, e-mail, senha ou chave, a prévia avisa.
- **Só a própria pasta.** O Tribunal faz commit apenas de `saves/tribunal/` e do `CATALOGO.md`.
- **Salvar só com "sim".** O `--confirmar` roda depois do "sim" do usuário à prévia.
