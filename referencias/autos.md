# Os autos (`autos.json`)

Carregado sob demanda pelo `SKILL.md`. Os autos são a fonte de tudo: a ata, o placar e o save no
Memory Card saem deles. Ficam em `./tribunal-autos/<data>-<slug>/autos.json`, na pasta de trabalho do
usuário. Confira com `python tribunal.py validar <autos>`.

Exemplo completo: `exemplos/autos-exemplo.json`.

```json
{
  "caso": {
    "titulo": "App de agendamento do salão",
    "tipo": "app",
    "area": "Beleza",
    "pergunta": "O app deve ser lançado como está?",
    "opcoes": ["Lançar como está", "Lançar depois de corrigir", "Não lançar"],
    "publico": "clientes de salão de bairro, 18 a 70 anos",
    "descricao": "App web onde a cliente escolhe serviço, profissional e horário e paga um sinal por Pix.",
    "data": "2026-11-09",
    "recurso_de": null
  },
  "juri": {
    "foro": "brasil",
    "sessao": "brasil-0001",
    "convocados": ["BR-004", "BR-017"],
    "impedimentos": ["idade<8"],
    "recusas": {
      "acusacao": [{"jurado": "BR-061", "motivo": "viés pró-novidade declarado na ficha"}],
      "defesa":   [{"jurado": "BR-090", "motivo": "não usa internet: o caso é de app"}]
    },
    "conselho": ["BR-017"]
  },
  "provas": [
    {"id": "P1", "tipo": "teste", "descricao": "Pagamento do sinal: 7 telas; o botão Pix fica fora da tela em 360px.",
     "fonte": "screenshot passo 5, viewport 360x740", "aceita": true}
  ],
  "acusacao": {"teses": [{"texto": "Quem usa celular simples não consegue pagar o sinal.", "provas": ["P1"]}]},
  "defesa":   {"teses": [{"texto": "A correção do botão é pequena e o resto do fluxo funciona.", "provas": ["P1"]}]},
  "testemunhas": [
    {"nome": "Especialista em acessibilidade (fictícia)", "especialidade": "WCAG",
     "depoimento": "Alvo de toque de 24px está abaixo dos 44px recomendados (WCAG 2.5.5)."}
  ],
  "votos": [
    {"jurado": "BR-017", "rodada": 1, "voto": "Lançar depois de corrigir", "confianca": 4,
     "motivo": "Achei bonito, mas não achei onde pagava.", "reparou": "o botão sumido"},
    {"jurado": "BR-017", "rodada": 2, "voto": "Lançar depois de corrigir", "confianca": 5,
     "motivo": "Arruma o botão e pronto."}
  ],
  "sentenca": {
    "veredito": "Lançar depois de corrigir",
    "confianca": 72,
    "fundamentacao": "...",
    "condicoes": ["botão Pix visível em telas de 360px", "fonte mínima de 16px"],
    "ponto_de_virada": "Se o teste com 10 clientes reais mostrar menos de 7 conseguindo pagar, o veredito vira para Não lançar.",
    "provas_decisivas": ["P1"],
    "voto_vencido": null,
    "proximo_passo": "Corrigir o botão e testar com 10 clientes do salão em 7 dias.",
    "criterio_de_abandono": "Se em 30 dias menos de 15% das clientes agendarem pelo app, voltar ao WhatsApp."
  },
  "decisao_usuario": {"acatou": true, "recurso": null, "decisao": "Vou corrigir e testar com 10 clientes.", "data": "2026-11-09"}
}
```

## Campos

| Campo | Obrigatório | Regras |
|---|---|---|
| `caso.titulo`, `caso.pergunta` | sim | a pergunta é uma frase decidível |
| `caso.tipo` | sim | `ideia`, `app`, `codigo`, `decisao`, `documento`, `outro` |
| `caso.opcoes` | não | padrão: `Procedente`, `Procedente com condições`, `Improcedente`; no concurso, as finalistas e o status quo |
| `caso.explicacao` | sim, para o júri | o caso em linguagem simples; o `briefing` manda este texto, igual, a todo jurado |
| `caso.aberta` · `caso.status_quo` | não | pergunta aberta: dispara o concurso de propostas; o status quo sempre vira opção |
| `acusacao.teses[]` | sim | `{id: "A1", gravidade: fatal\|grave\|leve, texto, onde, contraexemplo, provas}` |
| `defesa.respostas[]` | sim, se houver ataques | `{ataque: "A1", tipo: concede\|rebate, texto, correcao}` |
| `sentenca.ataques[]` | sim, se houver ataques | `{ataque: "A1", status: corrigido\|correcao_proposta\|rebatido\|de_pe, nota, verificado}`; FATAL de pé (ou só com correção proposta, no rito 2) trava a primeira opção |
| `rito` | casos novos: 2 | rito 2 exige checagem dupla de todo FATAL (`acusacao.teses[].checagem`) e `plano` |
| `plano` | rito 2, depois da sentença | `{ordem, proximo_passo, metas[], testes[], criterio_de_abandono, cobertura, hipoteses, conflitos}` do redator do plano |
| `propostas[]` | no concurso | `{id: "X1", apelido, carta, titulo, resumo, texto, ataques, respostas, status, notas}`; `apelido` = 2 ou 3 palavras que um leigo entende, usado na sala e na conversa |
| `juri.convocados` / `juri.conselho` | sim | ids do foro; o conselho sai dos convocados |
| `juri.recusas` | não | até 3 por lado; `{jurado, motivo}` ou só o id |
| `provas[].id` | sim | único (P1, P2...); teses e sentença só citam ids que existem |
| `provas[].aceita` | não | `false` com `motivo_recusa` |
| `votos[].rodada` | sim | 1 = os 25 convocados; 2 = os 7 do conselho |
| `votos[].voto` | sim | exatamente uma das opções |
| `sentenca.veredito` | sim | uma das opções; a maioria do conselho |
| `sentenca.confianca` | sim | número de 0 a 100 |
| `decisao_usuario.acatou` | não | `true`, `false` (recorreu) ou ausente (ainda não respondeu) |

A ata (`python tribunal.py ata`) mostra só o que estiver preenchido.
