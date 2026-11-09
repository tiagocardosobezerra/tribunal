# O júri

Carregado sob demanda pelo `SKILL.md`.

## O elenco fixo (lista geral)

`juri/brasil.json` tem 100 jurados fictícios. Cada um representa **1% da população brasileira**,
cerca de 2 milhões de pessoas. As cotas saem do IBGE e de outras fontes oficiais
(`populacao-brasil.md`): idade (de 1 a 100 anos), sexo, região e UF, cor ou raça, rural ou urbano,
capital, escolaridade, decil de renda, Bolsa Família, trabalho, religião, uso de internet e
deficiência. `python tribunal.py juri cotas` mostra a meta e o elenco lado a lado.

**Pessoas comuns, não personagens.** Ninguém ali é "o hacker", "a influencer" ou "o gênio". São a
caixa de supermercado de Feira de Santana, o aposentado da zona rural, a estudante de Curitiba, o
bebê de 1 ano no colo da mãe. A diversidade vem da população, não da caricatura.

Cada jurado tem duas camadas:

1. **Demografia**, gerada por `ferramentas/gerar_esqueleto.py`. Cada cota é preenchida por uma nota
   socioeconômica latente com ruído, o que dá correlações plausíveis: idade com escolaridade, região
   com cor e renda, idade com internet.
2. **A pessoa**: nome, cidade, ocupação, casa, aparelho, história, valores, medos, viés, o que ela
   repara e a voz. Foi escrita sobre a demografia, sem contrariá-la. A personalidade (Big Five, de
   1 a 5) foi sorteada antes.

`ferramentas/montar_foro.py` junta as duas camadas no foro final.

## O rodízio (convocação)

Em cada sessão:

1. **Saco embaralhado.** A lista dos 100 é embaralhada e consumida em ordem. Ninguém repete antes de
   todos servirem, e 4 sessões cobrem a lista inteira. Quando o saco acaba, ele é embaralhado de novo,
   sem os que acabaram de servir.
2. **Anti-clone.** Um jurado parecido demais com um já convocado na sessão (distância menor que 3 em
   faixa etária, sexo, cor, região, local, escolaridade, vínculo, renda, religião e internet) volta
   para o topo do saco. Ele não perde a vez: só não cai junto com o parecido.
3. **Impedimento.** O juiz afasta quem não pode julgar o caso. Em caso de código, os menores de 12
   são afastados automaticamente. O impedido também volta para o topo do saco.
4. **Recusas.** Acusação e defesa recusam até 3 cada, olhando só as fichas (CPP art. 468).
5. **Conselho.** 7 sorteados entre os que sobraram. Quem serviu no conselho nas últimas 4 sessões
   tem peso menor no sorteio, como o afastamento de quem serviu nos últimos 12 meses (CPP art. 426
   §4º).

O estado do rodízio fica em `local/convocacoes.json`, que não sai na distribuição. Apagar o arquivo
reinicia o rodízio. Use `--simular` para sortear sem gravar.

## Júri especial

`juri especial --n N --filtro F` sorteia, com diversidade, um júri só de um recorte. Exemplo: 60 anos
ou mais que usam internet. O júri especial fica fora do rodízio e é registrado na ata. Use só a pedido
do usuário. Na maior parte dos casos, o júri popular com testemunhas do público é melhor, porque
mostra quem fica de fora.

## Criar um foro novo (outro país)

1. Pesquise as cotas oficiais do país e escreva `referencias/populacao-<foro>.md` com as fontes.
2. Copie `ferramentas/gerar_esqueleto.py` e troque as tabelas de cotas: idades, regiões, cor ou
   etnia, escolaridade e o resto.
3. Gere o esqueleto, escreva as pessoas e monte `juri/<foro>.json` com o bloco `cotas`.
4. Rode `python tribunal.py juri cotas --foro <foro>` e confira os desvios.
5. Use com `--foro <foro>` em todos os comandos do júri.

## Formato do jurado

```json
{
  "id": "BR-042", "idade": 37, "faixa_ibge": "30-39", "sexo": "F", "regiao": "Nordeste", "uf": "BA",
  "cor_raca": "parda", "tipo_local": "interior", "escolaridade": "médio completo", "decil": "3",
  "renda_pc": 780, "renda": "baixa", "vinculo": "conta própria sem CNPJ", "setor": "comércio",
  "bolsa_familia": true, "religiao": "evangélica", "internet": "básico (WhatsApp e vídeo)",
  "deficiencia": null, "mora_sozinho": false,
  "personalidade": {"abertura": 3, "conscienciosidade": 4, "extroversão": 2, "amabilidade": 4, "estabilidade emocional": 3},
  "nome": "...", "apelido": "...", "cidade": "...", "ocupacao": "...", "estado_civil": "...", "filhos": 2,
  "mora_com": "...", "dispositivo": "...", "responsavel": "", "historia": "...",
  "valores": ["..."], "medos": ["..."], "vies": "...", "repara_em": "...", "voz": "..."
}
```

Os campos `faixa_etaria`, `rural`, `em_capital`, `religiao_grupo`, `usa_internet`, `tem_deficiencia` e
`aposentado` são derivados e servem às cotas e ao placar.
