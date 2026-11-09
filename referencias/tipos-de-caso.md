# Tipos de caso

Carregado sob demanda pelo `SKILL.md`. Para cada tipo: o que o perito faz, as opções de voto mais
comuns, como explicar o caso ao júri e quem costuma ser testemunha.

Regra geral: **o júri popular julga o efeito do objeto na vida das pessoas**. Ele não julga a técnica.
A técnica entra pela perícia e pelas testemunhas, e o perito a traduz para o júri em linguagem simples.

## ideia

Um produto, um negócio, uma feature, uma campanha ou um projeto que ainda não existe.

- **Perícia:**
  - Pesquisa na web: concorrentes, preço praticado, tamanho do público, casos de quem tentou.
  - Taxa-base: quantos negócios desse tipo sobrevivem? Quanto custa adquirir um cliente?
  - Exigências legais do setor.
  - Toda prova com URL. Se a pesquisa não achou, registre como `lacuna`.
- **Opções:** `Procedente` (siga), `Procedente com condições`, `Improcedente` (não siga).
- **Ao júri:** "Fulano quer abrir/lançar X, que faz Y, por Z reais. Você usaria? Pagaria? Indicaria?"
- **Testemunhas comuns:** alguém do público-alvo, alguém do setor, um especialista jurídico ou
  financeiro.

## app

Um app, site ou sistema que já existe, publicado ou em ambiente de teste.

- **Perícia, com o app de verdade:**
  - Abra no navegador embutido ou no Chrome do usuário, conforme o pedido. Se for app de celular,
    peça a URL web, um build de teste ou screenshots.
  - Defina de 3 a 5 **tarefas** centrais. Exemplos: cadastrar, achar um produto, pagar, cancelar,
    pedir ajuda.
  - Para cada jurado do conselho, cumpra as tarefas **como aquela pessoa**:
    - celular simples e tela pequena: viewport mobile
    - baixa visão: zoom e contraste
    - pouca experiência digital: não adivinha ícone, lê tudo, desiste depois de 2 erros
    - pressa: só vê o topo da tela
    - deficiência motora: alvos pequenos são problema
  - Prova = tropeço ou acerto, com o passo e um screenshot ou a referência do elemento.
  - Meça o básico: tempo de carga percebido, quantidade de passos por tarefa, mensagens de erro,
    contraste e tamanho de fonte. Rode um check de acessibilidade se der.
  - **Nunca** use credencial real, nunca pague de verdade e nunca envie formulário que tenha efeito
    real. Em ambiente local ou de teste, use dados fictícios. Em produção, pare antes de qualquer
    ação irreversível e registre a lacuna.
- **Opções:** `Lançar como está`, `Lançar depois de corrigir`, `Não lançar` (ou as opções padrão).
- **Ao júri:** mostre o que o perito viu, tarefa por tarefa, em linguagem simples ("para pagar, são 7
  telas; na 4ª, o botão some se a letra estiver grande").
- **Testemunhas comuns:** especialista em acessibilidade, em segurança, em UX.

## codigo

Um código, PR, diff, script, consulta ou arquitetura.

- **Impedimento automático:** menores de 12 anos.
- **Perícia:**
  - Leia o código e cite arquivo e linha.
  - Rode testes, lint, type check e build, se houver. A prova é a saída do comando.
  - Procure falhas de correção, segurança (injeção, segredo no código, permissão), desempenho e
    manutenção.
  - Se o projeto tiver as skills de review, use-as como perito auxiliar (`/code-review`,
    `/security-review`). O resultado entra como prova com a fonte.
- **Câmara técnica:** o juiz convoca de 2 a 3 testemunhas técnicas, por exemplo dev sênior da
  stack, segurança e quem vai manter o código. Elas dão laudo com arquivo e linha. Não votam.
- **Opções:** `Aprovar`, `Aprovar com correções`, `Rejeitar`.
- **Ao júri:** traduza para efeito na vida real. "Se isso for ao ar, o que pode acontecer com quem
  usa? O cadastro de 1 em cada 100 pessoas pode sumir. A página fica 2 segundos mais lenta. Um
  estranho pode ver o pedido de outra pessoa."
- O júri decide se o risco é aceitável **para as pessoas**. A câmara técnica diz qual é o risco.

## decisao

Uma escolha pessoal ou profissional: mudar de emprego, cidade ou fornecedor, investir tempo num
projeto, contratar alguém.

- **Perícia:**
  - Os fatos do usuário: pergunte o que falta, sem passar de 3 perguntas.
  - Taxa-base pesquisada: o que costuma acontecer com quem faz essa escolha.
  - Os números: custo, salário, prazo.
- **Opções:** os caminhos ("Aceitar a proposta", "Ficar", "Negociar e decidir em 30 dias"). Sempre
  inclua a opção escondida mais sensata, se o usuário não a trouxe.
- **Ao júri:** "Uma pessoa de <idade, situação> precisa escolher entre A e B. O que você faria no
  lugar dela? E o que diria a ela?"
- **Cuidado:** o tribunal não substitui um profissional em saúde, direito ou finanças pessoais. Se a
  decisão depende disso, a sentença diz qual profissional ouvir. Também não dá recomendação de
  investimento.

## documento

Um texto, proposta, contrato, política, apresentação, e-mail importante ou currículo.

- **Perícia:** leitura com citação de trechos; clareza (frases longas, jargão); coerência; conferência
  de fatos citados.
- **Opções:** `Enviar como está`, `Enviar depois de ajustar`, `Reescrever`.
- **Ao júri:** leia o trecho principal como ele seria lido pelo destinatário. "Você entendeu o que
  estão pedindo? Assinaria? Confiaria?"

## outro

Qualquer coisa que não caiba nos tipos acima: um nome de marca, uma logo, uma regra de condomínio,
uma ação social. Use as opções padrão e a perícia que fizer sentido. Diga ao usuário qual perícia
escolheu e por quê.
