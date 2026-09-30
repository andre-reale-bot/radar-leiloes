# Radar de Leilões de Veículos: contexto completo do projeto

Documento de passagem de contexto. Objetivo: permitir que um novo chat do Claude continue o projeto do zero, sem perguntar nada que já foi decidido. Estado registrado em **30/09/2026, 00:30 (Brasília)**, ao fim da sessão que começou em 29/09 e cobriu os **Passos 1 a 28**.

Resumo em 5 linhas: o robô (`radar.py`) roda todo dia às 06:00 no GitHub Actions, lê **26 fontes** (4 órgãos públicos, a Copart, a agenda Leilões Brasil e 20 leiloeiros), filtra leilões de veículos dos próximos 15 dias, confere cada site na base oficial da FENAJU, calcula distância/tempo de carro a partir de BH e publica uma página em **https://andre-reale-bot.github.io/radar-leiloes/**. A página tem lista única ordenada por proximidade de BH (MG em amarelo), faixa vermelha de alertas quando uma fonte quebra, e faixa de "página desatualizada". Última execução: 30/09 00:11, **134 leilões, 23 em MG**. Próximo passo técnico: **Passo 29**.

---

## 1. Quem é o usuário e como trabalhar com ele

- **André**, mora em **Belo Horizonte/MG**. Iniciante em leilões de automóveis; o plano é arrematar, restaurar (com um sócio mecânico em BH) e revender. Não é programador.
- Projeto do Claude "André | Leilão de Carros": só se fala de **leilões de automóveis**. Não misturar com outros assuntos ou projetos, e não levar conteúdo deste projeto para outros chats/projetos.
- **Estilo exigido:** respostas curtas e objetivas (idealmente até 10 linhas), sem preâmbulo, sem enchimento, **sem travessão** (usar vírgula, ponto e vírgula, parênteses ou dois pontos). Fechar decisões com recomendação clara e o motivo. Discordar com transparência quando algo prejudicar o objetivo dele. Não afirmar números sem fonte; dizer "não sei" quando for o caso; declarar o nível de confiança.
- **Postura exigida (dita por ele várias vezes em 29 e 30/09):** "atenção máxima aos detalhes", "nunca tenha pressa", "zelo pela eficiência", "não deixe o código perder qualidade nem completude". Ele elogiou a estratégia de fazer em lotes pequenos e testar tudo; pediu para continuar assim.
- **Ele cobra certeza e honestidade.** Já perguntou "tem certeza absoluta?", "pode estar alucinando?", "como você leu meu GitHub?". Responder mostrando **de onde veio cada dado** (arquivo, commit, log) e os **limites reais** da verificação. Quando possível, dar a ele um jeito de conferir sozinho (ex.: abrir `snapshots/verificacao.json` e buscar um domínio).
- **Forma de guiar tarefas técnicas:** passo a passo, **numerados sequencialmente** (último usado: **Passo 28**; o próximo é o **29**). Ele manda prints ou cola logs; o Claude confere e só então dá o próximo passo.
- **Nível de detalhe dos passos (reclamação dele em 29/09: "você está pulando etapas"):** descrever **cada clique desde a entrada no GitHub**, com o nome exato de cada botão e onde ele fica. Roteiros-padrão completos na seção 11.
- Ele não quer gastar a cota do plano do Claude com IA dentro da automação. A API da Anthropic é cobrada à parte, mas a decisão foi **não usar IA na automação**.
- **Ao final de cada chat (pedido do usuário em 30/09):** atualizar este markdown e **lembrar André de subir a nova versão no GitHub** (Add file > Upload files, mesmo nome `contexto-radar-leiloes.md`, que substitui a anterior). Nunca encerrar uma sessão sem esse lembrete.
- **Não repetir sugestões que ele recusou:** remover CPFs de nomes de pátio do Detran-MG (ele considera irrelevante); regenerar os códigos de recuperação da conta GitHub (ele recusou; ver seção 4).

---

## 2. O que o usuário pediu (requisitos originais)

Automação que, diariamente:
1. Examine as listas dos agregadores gratuitos de leilões.
2. Examine os sites dos leiloeiros do painel da FENAJU (anunciado como "2.800+").
3. Examine sistemas da Receita Federal, receitas estaduais e Detrans.
4. Examine plataformas usadas por leiloeiros (SOLEON, Leilão PRO, Leiloar, Superbid Exchange etc.).
5. Verifique se os sites são falsos ou verdadeiros (anti-golpe).
6. Mostre todos os leilões de veículos do Brasil nos **próximos 15 dias** com: **site oficial e seguro (link clicável), UF (ênfase em MG), nome do leilão, datas**.

Perguntas que ele fez e respostas dadas:
- "Existe base unificada?" **Não existe base oficial.** Existem agregadores privados, nenhum com 100%.
- "São ~60 leilões por dia?" **Não confirmado** por nenhuma fonte; tratar como estimativa.
- "A ferramenta terá 100% de cobertura?" Em relação às fontes lidas, perto de 100% quando o coletor funciona. Em relação a uma busca manual independente, **não há percentual honesto antes de medir**. Plano: medir (ver seção 10).
- "Receita e Detrans exigem login gov.br, não seria melhor buscar no DOU ou em notícias?" **Não é necessário:** as listagens de Detran-MG, Detran-RS e Receita (SLE) foram lidas **sem login**; o gov.br só é exigido para dar lance/proposta. Detrans (órgãos estaduais) publicam no Diário Oficial do Estado, não no DOU; 27 diários em PDF, custo alto para pouco ganho. Portais de notícia chegam atrasados. Usar Diário Oficial só como plano B para estado com portal fechado.


---

## 3. Decisões de arquitetura (e por quê)

| Decisão | Motivo |
|---|---|
| Rodar em **nuvem gratuita**: GitHub Actions (execução) + GitHub Pages (página) | Roda sozinho, sem PC ligado, custo zero. Repositório **público** para Actions e Pages grátis e ilimitados. Consequência: código, capturas e página são públicos (não guardar segredos no repositório). |
| **Sem IA** na coleta | Pedido do usuário. Leitores (parsers) por regras fixas. |
| **FENAJU como base anti-golpe**, não como lista a varrer diariamente | Varrer ~2.000 sites heterogêneos todo dia é caro e a maioria nem leiloa veículos. |
| Fontes priorizadas: órgãos públicos + organizadoras + leiloeiros relevantes + (v2) agregadores e plataformas | Um leitor por plataforma cobre vários sites (ex.: Top e Sampaio usam a mesma plataforma e o mesmo leitor). |
| **Método "reconhecimento primeiro"** | O sandbox do Claude não acessa os sites de leilão. O workflow de diagnóstico abre cada fonte num navegador real no GitHub, salva texto, HTML, prints, respostas JSON (APIs internas) e, desde o Passo 23, **todo o tráfego de rede** (`rede.json.gz`); o Claude lê essas capturas via `git clone` e escreve leitores exatos, testando offline. |
| **Adicionar fontes em lotes pequenos** (Passos 21 a 25) | Cada site tem formato próprio; poucos por vez facilita achar o culpado se algo quebrar. Ordem: MG primeiro, depois plataformas compartilhadas, depois o resto. Aprovado e elogiado pelo usuário. |
| **Garantia de não regressão a cada entrega** | Antes de entregar um `radar.py`, o Claude roda a versão anterior e a nova nas mesmas capturas e prova que as fontes antigas geram **exatamente os mesmos leilões**; também mostra quantas linhas foram removidas do código (normalmente nenhuma ou só as substituídas). O usuário exige isso. |
| **Ubuntu fixado em `ubuntu-24.04`** nos dois workflows (Passos 14 e 16) | `ubuntu-latest` passa sozinho para o Ubuntu 26 em **19/10/2026**, e o `playwright install --with-deps` instala bibliotecas específicas de cada versão; o Playwright costuma demorar a suportar versões novas. **Migrar para o 26 só depois, de forma controlada e testada.** (Pedido explícito do usuário para constar aqui.) |
| **Distância de BH via OpenStreetMap (OSRM)**, não Google | Escolha do usuário: gratuito, sem conta e sem cartão. Google Distance Matrix exige conta com cartão; copiar do site do Maps viola os termos (descartado). **Regra do usuário: tempo do OSM sempre +10%** (`FATOR_TEMPO = 1.10`). Sem trânsito. |
| Coordenadas pela base pública de municípios (IBGE, compilada no GitHub `kelvins/municipios-brasileiros`) | O robô baixa o CSV a cada execução e casa cidade+UF (sede do município). Uma consulta à API `table` do OSRM traz todas as distâncias. Desde o Passo 27 há **cópia de segurança** das coordenadas e distâncias. |
| **Lista única ordenada por proximidade de BH** (Passo 19) | Pedido do usuário: mais perto de BH primeiro, **MG em amarelo**, sem distância no fim; botões **"Por distância" (padrão)** e **"Por data"** reordenam na página; filtro de UF funciona com os dois. |
| **Data de Brasília** em todo o robô (Passo 22) | O servidor do GitHub usa UTC; sem a correção, execuções após 21:00 pulavam um dia. `HOJE = (agora UTC - 3 h).date()`. |
| **Contingências na própria página** (Passos 24 e 27) | Faixa vermelha no topo quando uma fonte quebra (ver seção 9.4) e faixa de "página desatualizada" calculada pelo navegador. O histórico fica em `saude.json`, publicado junto com a página e lido na execução seguinte (sem precisar de permissão de escrita no repositório). |
| **Filtro de veículos rígido** | Leilões de prefeituras e varas sem menção clara a veículo ficam de fora (ex.: Túlio "Leilão de Prefeitura", Freire). Preferência por não poluir a lista. Marcas/modelos (`MARCAS`) contam como veículo em Kleiber, Vinco, Cardoso, Top e Sampaio. |
| Não contornar paywall | Almanaque do Leilão expõe a agenda completa via Supabase, mas o público vê só 3 dias; **não usar**. |
| Não contornar barreiras anti-robô | Sites com Cloudflare/"Um momento…" ficam de fora (ou entram via agregadores na v2). |
| Ícone da página: **📡** (Passo 25) | Escolha do usuário; SVG embutido (data URI), sem arquivo extra. |

---

## 4. Infraestrutura (GitHub)

- Conta: **andre-reale-bot**. **Verificação em duas etapas ativada em 30/09/2026** (app autenticador; Passo 28). Os **códigos de recuperação** estão guardados, por decisão do usuário, na **memória do projeto no Claude** (arquivo "github-conta"). **Nunca colocá-los neste markdown nem no repositório** (o repositório é público). O Claude recomendou gerar códigos novos, já que foram colados no chat; o usuário recusou; não insistir.
- Repositório: **https://github.com/andre-reale-bot/radar-leiloes** (público).
- Página: **https://andre-reale-bot.github.io/radar-leiloes/** (mesmo endereço desde o início; favorito do usuário). Arquivos publicados: `index.html`, `leiloes.json`, `saude.json`.
- Settings > Pages > Source: **GitHub Actions**. Settings > Actions > General > Workflow permissions: **Read and write**.

Estrutura do repositório (commit ce72d29, 30/09 00:02):
```
.github/workflows/diagnostico.yml   # reconhecimento manual das fontes
.github/workflows/radar.yml         # execucao diaria + publicacao da pagina
diagnostico.py                      # 161 linhas; lista de sites da ultima investigacao (Passo 23)
radar.py                            # 1310 linhas; 26 fontes + contingencias (Passo 27)
snapshots/                          # capturas do diagnostico (73 pastas, datas variadas; .gz)
README.md
```
(A cópia deste markdown no repositório está pendente: Passo 29, ver seção 10.)

Histórico de commits relevante: a6aaf8c (inicial) · e19b841/325c224/89da9cc (diagnóstico) · 2f7118a e f31ae6a (radar v1) · 8048d9b (Passo 14) · 82a8c9d (15) · 58c2923 (16) · 8317e4c (18) · 5754ee9 (19) · fa133f0 (20, diagnóstico com a lista do usuário) · e0a8a06 (resultado do diagnóstico, com `verificacao.json`) · 1bdef0b (21) · 15340e9 (22) · d7097e0 (23, radar + diagnóstico) · ff35229 (resultado do diagnóstico do Passo 23) · e49b5e2 (24) · e8aac9f (25) · d58312b (26) · **ce72d29 (27, versão atual)**.

Como o Claude lê o estado atual (a partir do sandbox):
- **Melhor caminho:** `git clone -q https://github.com/andre-reale-bot/radar-leiloes.git` (repositório público; não precisa de login). Clone completo dá também o histórico (`git log`, `git show <hash>:arquivo`).
- Conferir um upload: `curl https://raw.githubusercontent.com/andre-reale-bot/radar-leiloes/<hash>/radar.py | diff - arquivo_entregue` (o `main` no raw pode ter cache; usar `?nc=$RANDOM` ou o hash).
- Capturas: `snapshots/<pasta>/{info.json, texto.txt.gz, pagina.html.gz, apis.json.gz, rede.json.gz, tela.png}`; `snapshots/resumo.json` (só da última execução do diagnóstico); `snapshots/verificacao.json` e `snapshots/fenaju_base_*.json.gz` (do Passo 20). Nome da pasta = URL em minúsculas com não alfanuméricos trocados por "-", até 90 caracteres.
- **Explicado ao usuário:** o Claude não tem acesso à conta; lê só o que é público e não consegue alterar nada.

Limitações do sandbox do Claude:
- **Consegue:** `github.com` (clone), `raw.githubusercontent.com`, `api.github.com` (sem token, limite de 60 req/h; costuma falhar), PyPI/npm. Tem Python, Playwright e Chromium para testar a página localmente (`file://`).
- **Não consegue:** sites de leilão, FENAJU, Registro.br, `*.github.io`, OSRM. A ferramenta `web_fetch` do chat só abre URLs que o usuário colou ou que vieram de busca. Para ver a página ou logs, pedir print ou texto ao usuário.
- O runner do GitHub roda nos EUA; alguns sites brasileiros bloqueiam esse IP (Cloudflare, "Um momento…", 403/429).

---

## 5. Workflows

### 5.1 `.github/workflows/diagnostico.yml` (manual; versão atual, Passo 16; não mudou até o Passo 28)
```yaml
name: Diagnostico das fontes
on:
  workflow_dispatch:
permissions:
  contents: write
jobs:
  diagnostico:
    runs-on: ubuntu-24.04
    timeout-minutes: 40
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Instalar navegador
        run: |
          pip install playwright
          python -m playwright install --with-deps chromium
      - name: Visitar fontes
        run: python diagnostico.py
      - name: Salvar resultados
        run: |
          git config user.name "radar-bot"
          git config user.email "radar-bot@users.noreply.github.com"
          git add snapshots
          git commit -m "Diagnostico $(date -u +%F)" || echo "sem mudancas"
          git pull --rebase
          git push
```

### 5.2 `.github/workflows/radar.yml` (diário, 09:00 UTC = 06:00 Brasília, e manual; versão atual, Passo 14; não mudou até o Passo 28)
```yaml
name: Radar de leiloes
on:
  schedule:
    - cron: "0 9 * * *"
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  radar:
    runs-on: ubuntu-24.04
    timeout-minutes: 60
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Instalar navegador
        run: |
          pip install playwright
          python -m playwright install --with-deps chromium
      - name: Rodar radar
        run: python radar.py
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - id: deploy
        uses: actions/deploy-pages@v4
```

Aviso que ainda aparece (não quebra nada hoje): **Node.js 20 depreciado** nas actions `checkout@v4`, `setup-python@v5`, `deploy-pages@v4` e `upload-artifact@v4` (o GitHub já as força a rodar no Node 24).

Tempo de execução: radar ~3,5 a 4 min com 26 fontes (execução total ~4 a 6 min incluindo instalação do navegador, que leva ~1,5 min por rodada); diagnóstico do Passo 20 (58 sites) levou 7m12s.

Horário e agendamento (explicado ao usuário):
- Topo da página: "Atualizado em dd/mm/aaaa HH:MM (Brasília, execução automática/manual) · janela · N leilões · base FENAJU". Em Actions, a execução automática aparece como "Scheduled".
- **Não será exatamente 06:00:** o GitHub atrasa agendamentos (minutos, às vezes mais de 1 h). Entre 06:05 e 07:00 é normal.
- Execução manual sobrescreve a página. Execuções manuais à tarde ainda mostram leilões de hoje já encerrados (o filtro é por data, não por hora).
- **Risco:** o GitHub desativa agendamentos em repositórios públicos após **60 dias sem atividade**. Contingência: faixa de página desatualizada (seção 9.4).

---

## 6. Histórico do que foi feito (cronológico)

### 6.1 Até o Passo 19 (29/09, até ~17:00)
1. Orientação inicial: e-CAC > Outros > "Participar de leilão eletrônico da Receita Federal" abre o **Sistema de Leilão Eletrônico (SLE)**. No SLE, os números ao lado dos filtros (ex.: MG 9) contam **lotes**, não leilões. Em MG havia um edital aberto: **0600100/0000005/2026 Belo Horizonte**, propostas até 30/09/2026 21:00, lances 01/10/2026 10:00, 12 lotes.
2. Detran-MG: leilões em **leilao.detran.mg.gov.br** (também leilao.transito.mg.gov.br). Cadastro do arrematante tem análise de até 5 dias úteis.
3. Pesquisa de mercado (ver seção 8) e desenho da solução.
4. Criação da conta, repositório, Pages e permissões (Passos 1 a 4).
5. Diagnóstico (Passos 5 a 10):
   - Execução #1 **falhou no push**: GitHub Push Protection bloqueou porque `snapshots/www-sodresantoro-com-br/pagina.html` (linha 164) contém uma **chave técnica (Elastic API key) embutida no site da Sodré Santoro**. Decisão: **não** usar o link "allow the secret" (publicaria chave de terceiros). Solução proposta: salvar capturas compactadas (.gz).
   - O usuário usou "Re-run jobs" na execução #1, que reexecuta o commit antigo (325c224); falhou com push rejeitado ("fetch first") porque o repositório já tinha a edição nova. Lição: **sempre usar "Run workflow", nunca "Re-run"** após mudar código.
   - Execução #2 (commit 89da9cc) **teve sucesso** e salvou capturas **sem compressão** (nessa visita a chave da Sodré não apareceu). O problema foi resolvido depois (item 13 abaixo).
6. Análise das capturas, escrita do `radar.py`, testes offline nas capturas (35 leilões extraídos no teste).
7. Upload do `radar.py` e criação do `radar.yml` (Passos 11 e 12).
8. **Primeira execução real do radar: sucesso** (Passo 13). Página de 29/09/2026 12:17 (Brasília), janela 29/09 a 14/10: **93 leilões, 16 em MG**, base FENAJU com **1.948 leiloeiros**. Por fonte: Detran-MG 13, Detran-RS 2, Receita Federal 5, Copart 45, Sodré Santoro 14, Leilo 8, Freitas 3, Leilões Brasil 3, Parque dos Leilões 0 (correto, sem eventos no período).
9. Conversa sobre ampliação de fontes e alertas por modelo (decisões na seção 10).
10. **Passo 14:** `radar.yml` com `runs-on: ubuntu-24.04`. Radar execução **#2** (commit 8048d9b): **sucesso**, 4m13s; aviso do Ubuntu sumiu. Endereço da página não mudou.
11. **Passo 15:** novo `diagnostico.py` (versão gzip) enviado por upload (commit 82a8c9d); conferido idêntico ao entregue.
12. **Passo 16:** `diagnostico.yml` com `ubuntu-24.04` e `git pull --rebase` antes do `git push`; conferido no repositório.
13. **Passo 17:** Diagnóstico execução **#3** (commit 58c2923): **sucesso**, 2m10s. Push aceito com a Sodré incluída (sem bloqueio de chave). Resultado gravado no commit 1332227 ("Diagnostico 2026-09-29"): 78 arquivos .gz, nenhum arquivo antigo sem compressão; 26 fontes com o mesmo padrão de antes (ver 8.2).
14. Pergunta sobre como confirmar a execução das 06:00 (ver seção 5) e pedido de coluna de distância de BH. Usuário escolheu OpenStreetMap com tempo +10% e pediu fazer as duas melhorias antes da v2.
15. **Passo 18:** novo `radar.py` (distância de BH + tipo de execução), testado offline com as capturas de hoje (todas as 16 cidades de MG reconhecidas; 69 de 92 leilões com cidade identificada) e com resposta OSRM simulada. Upload (commit 8317e4c) conferido idêntico. Radar execução **#3**: **sucesso**, 3m21s. Página de 29/09/2026 15:36 (execução manual): **91 leilões, 16 em MG, 69 de 91 com distância**; OSRM respondeu no GitHub. Valores coerentes (ex.: Betim 36 km/42 min, São João del-Rei 184 km/3h21, Belo Horizonte "Em BH").
16. Variação do total entre execuções (93 → 92 → 91) veio das fontes, não do código: a Sodré caiu de 14 para 12 (leilões realizados ou retirados do site dela; causa exata não verificável do sandbox). Por fonte na #3: Detran-MG 13, Detran-RS 2, Receita 5, Copart 45, Sodré 12, Leilo 8, Freitas 3, Leilões Brasil 3, Parque 0.
17. Claude apontou que CPFs de donos de pátio (pessoa física) aparecem na página pública. **Decisão do usuário: irrelevante, não corrigir.** Não voltar a propor.
18. Pedido de lista única por proximidade de BH. Escolhas do usuário: juntar tudo numa lista só, MG em cor diferente; incluir botão distância/data, padrão distância.
19. **Passo 19:** novo `radar.py` (lista única ordenada). Testado offline e **no navegador (Playwright)**: ordem por distância, ordem por data, volta à ordem original e filtro MG corretos. O usuário reclamou que o passo pulou etapas; o Claude refez com todos os cliques. Upload (commit 5754ee9) conferido idêntico. Radar execução **#4**: **sucesso**, 3m50s. Página de 29/09/2026 17:01 (execução manual): **94 leilões, 15 em MG**; prints confirmaram os dois modos de ordenação (distância: BH, Betim 36 km, Cláudio 144 km...; data: 29/09 primeiro, MG em amarelo).
20. Variações explicadas ao usuário: MG 16 → 15 porque o leilão de Mutum encerrava 29/09 às 17:00 e a página foi gerada às 17:01 (provável que o Detran-MG já não o liste como "Publicado"; não confirmado); total 91 → 94 por mudança nas fontes.

### 6.2 Passos 20 a 28 (29/09 à noite e madrugada de 30/09)

21. **Lista de leiloeiros do usuário (Passo 20).** André mandou 37 links de leiloeiros "principais e relevantes" e pediu: verificar quais são verdadeiros/seguros e quais são falsos; dizer quais já estão no radar; incluir os demais. Ele suspeitou de `joaoemilio.com.br` e `www.joaoemilio.com.br` (um seria falso): **é o mesmo domínio**, o "www" é só prefixo; não é indício de golpe. O Claude entregou um `diagnostico.py` com os sites novos mais uma verificação: baixa **toda a base da FENAJU** (com e sem o parâmetro `origem`) e consulta o **Registro.br (RDAP)** de cada domínio (titular e data de registro). Diagnóstico execução **#4** (fa133f0 → e0a8a06): sucesso, 7m12s.
22. **Resultado da verificação:** **nenhum site da lista é falso.** Os 32 domínios distintos pertencem a leiloeiros em situação **Regular** na FENAJU ou às empresas deles; dois são `.gov.br`. Kron e Mafra não têm o domínio na ficha FENAJU, mas o **titular do domínio é o próprio leiloeiro regular** (evidência indireta, porém forte). A FENAJU retornou **1.948 registros com e sem `origem`** (pendência antiga resolvida: o parâmetro não muda nada). Tabela completa na seção 8.4.
23. O usuário questionou: "como ter certeza só com um print?", "como o workflow testou?", "pode estar alucinando?", "você tem acesso ao meu GitHub?". Resposta: o Claude clonou o repositório público e leu `verificacao.json` e a base FENAJU; limites declarados (valida domínios exatos, não "segurança para pagar"; sem teste de malware/certificado; base FENAJU autodeclarada). Houve um falso positivo na busca automática ("ricoleiloes" casou com "ericoleiloes"), percebido e descartado. O usuário colou o log completo do diagnóstico; o Claude conferiu que batia (commit, contagem FENAJU, status de cada site) e ressalvou que o log não imprime os detalhes de titulares.
24. **Passo 21 (lote MG):** Palácio dos Leilões (Juatuba), Saraiva (BH), GP (BH) e Leilões MG (governo, Seplag). Captura ganhou suporte a **consulta POST extra** (agenda completa da GP). Corrigido falso positivo "motores" = "moto". Radar **#5** (1bdef0b): sucesso; Palácio 6, Saraiva 4, GP 7 (a consulta extra funcionou), Leilões MG 0; **113 leilões, 23 em MG**. O print revelou o bug do fuso (página de 29/09 22:46 com janela começando em 30/09).
25. **Passo 22:** Kleiber (Cuiabá/MT; o Claude supôs que usava a plataforma da Saraiva, **não usa**; leitor próprio; admitido com transparência) e **correção do fuso** (data de Brasília). Kron, Mafra e Monzon ficaram de fora (plataforma Superbid respondeu "Não foram encontrados resultados"). Radar **#6** (15340e9): sucesso, 14 fontes, 110 leilões (janela voltou um dia), Kleiber 1.
26. **Passo 23:** E-Leilões (SP) e **correção do horário da Copart**, apontada pelo usuário com prints do calendário da Copart (Betim é sempre sexta às **12:00**; o radar mostrava 15:00). A API tem `startTime` em UTC e `saleTime` ("120000") já em Brasília; passou a usar `saleTime`. Conferidos **21 horários** contra os prints: todos batem. Novo `diagnostico.py` direcionado (agendas de Pestana, Vinco, Norte, WR, Leiloeiro Público, Túlio, Savoy, Sumaré; Kron/Mafra/Monzon/Superbid) com **log de rede** e **rolagem**. O usuário perguntou se o radar novo "não exclui nada": o Claude comparou com o do repositório (54 linhas acrescentadas, 1 removida, a do horário) e provou nas capturas que as 14 fontes geravam os mesmos leilões. Uma confusão: o primeiro print ainda era da página antiga (cache); com Ctrl+F5 apareceu a versão nova (23:13, 112 leilões, Betim 12:00, E-Leilões 2). Radar **#7** e diagnóstico **#5** (d7097e0 → ff35229).
27. **Contingência pedida pelo usuário ("importantíssima"):** avisar em destaque quando o site de um leiloeiro deixar de existir ou mudar, para ele procurar o novo site. Aprovou os 4 sinais (seção 9.4).
28. **Resultado do diagnóstico do Passo 23:** Pestana (agenda com 49 leilões em 5 páginas de 12), Vinco (cards só aparecem com rolagem), Norte (API paginada), WR, Leiloeiro Público (API), Túlio (GraphQL), Savoy (API Supabase) acessíveis; **Sumaré `/leiloes` = 404**; Kron/Mafra/Monzon: barreira **Cloudflare** (`cdn-cgi/challenge-platform`; o `style.config.json` volta HTML e o app chama `/undefined`, por isso a busca vem vazia); Superbid 403.
29. **Passo 24:** Pestana (o robô clica **"Próximo" 4 vezes** e junta as páginas), WR (Detrans AC/AM/RR) e a **contingência de saúde das fontes**. Radar **#8** (e49b5e2): sucesso, 17 fontes, 119 leilões; Pestana 5 (contra 3 no teste só da 1ª página: prova de que os cliques funcionaram), WR 2; nenhuma faixa vermelha (correto: histórico começando). O usuário perguntou se "clicar em Próximo" vale para todos: não; só para sites com lista cortada, cada um pagina de um jeito.
30. **Passo 25 (último bloco):** Norte, Leiloeiro Público, Túlio, Savoy, Vinco, Cardoso, Freire, Top/Pizzolatti e Sampaio; ícone 📡. Radar **#9** (e8aac9f): sucesso, **26 fontes, 131 leilões**; números idênticos ao teste. O Claude notou no Top/Pizzolatti o leilão **SEA/SC de 05/10** com Agrale Marruá: o usuário confirmou que **é o leilão dos Marruás** que ele estuda em outro chat do projeto (Leilão 559/2026, lotes 66, 226, 342) e pediu atenção assim sempre.
31. **Varredura de código pedida pelo usuário** (erros, inconsistências, ineficiências). Achados corrigidos no **Passo 26** (aprovados só os itens 1 a 4): (1) filtro de veículo por palavra inteira, excluindo motosserra, motobomba, motoniveladora, motogerador, motorista, carroceria, carrinho, carretel; (2) deduplicação por nome completo + link (antes, só 60 caracteres); (3) troca de titular do domínio: aviso por uma semana e depois adota o novo titular (antes o alerta ficaria eterno); (4) `datetime.utcnow()` obsoleto trocado. Limitação explicada: fontes que normalmente têm 0 nunca disparam "layout mudou". Mantidas por decisão: reinstalar o navegador a cada execução e visitar sites em fila (otimizar complicaria e aumentaria risco de bloqueio). Radar **#10** (d58312b): 131 leilões, idêntico. O `diagnostico.py` não precisou mudar.
32. **Contingências futuras (6, aprovadas todas; Passo 27):** página desatualizada; 2FA; cópias de segurança; volume/horário anormal; execução lenta; cópia do markdown no repositório (seção 9.4 e 10). Radar **#11** (ce72d29): 30/09 00:11, **134 leilões, 23 em MG**, janela 30/09 a 15/10 (virada do dia correta; 1ª praça da moto da GP de 29/09 saiu). **Detran-RS: FALHOU** (tempo esgotado de 60 s; funcionou em todas as execuções anteriores, provável instabilidade do site). Sem faixa vermelha, pela regra de dois dias.
33. **Passo 28:** 2FA ativada. O usuário colou os códigos de recuperação no chat e pediu para salvar na memória do projeto; o Claude recomendou não salvar e gerar novos; ele recusou e reiterou; o Claude salvou na memória do projeto e registrou o risco uma vez.

---

## 7. Bugs, pendências técnicas e riscos conhecidos

Resolvidos (mantidos aqui como histórico curto): diagnóstico sem gzip (Passos 15 a 17); JSON truncado no diagnóstico; fuso da data (Passo 22); horário da Copart (Passo 23); parâmetro `origem` da FENAJU (não muda nada, Passo 20); fonte zerada em silêncio (coberto pela contingência, Passo 24); falsos positivos de moto/carro, deduplicação por 60 caracteres, titular eterno, `utcnow` (Passo 26); dependências sem cópia (Passo 27).

Abertos:
1. **Detran-RS falhou por tempo esgotado** em 30/09 00:11. Ver na execução automática das 06:00; se falhar de novo, a faixa vermelha aparece. Se persistir, aumentar o tempo limite dessa fonte ou investigar bloqueio.
2. **Sumaré Leilões** (lista do usuário) não entrou: `/leiloes` dá 404 e a capa não lista leilões (há links do tipo `/leiloes/5424`). Precisa de novo diagnóstico.
3. **Kron, Mafra e Monzon** (plataforma Superbid Exchange) bloqueados por Cloudflare; Superbid.net também 403. Rota: agregadores na v2.
4. **Visual:** a coluna "Data" quebra em três linhas ("01/10 / qui / 10:00") desde que a tabela ficou mais cheia. Ajuste simples (`white-space: nowrap`). Anotado, não feito (fora do escopo aprovado).
5. **Filtro não reconhece "carreta"** (semirreboque) como veículo. Já era assim; decidir se deve entrar.
6. **Receita Federal:** editais mistos; entram todos, marcados "Misto: verificar se há veículos".
7. **Detran-MG:** a data é o **encerramento dos lances**. Nome do pátio pode conter CPF: decisão do usuário, **não remover e não propor de novo**.
8. **Links genéricos** (sem página do leilão específico): Sodré, Copart, Leilões Brasil, Palácio (5 de 6 têm link direto; o de 1 lote não), Kleiber, Pestana, Savoy, Túlio, Cardoso, Freire, Leilo, Freitas.
9. **UF/local:** Sodré "Online" sem UF; Leilões Brasil quase sempre sem UF; Leilo e Freitas usam UF padrão fixa (GO e SP) quando o texto não traz; GP e E-Leilões sem cidade em parte dos leilões. Distância "?" para pátios com nome de bairro ("PÁTIO UTINGA", "PÁTIO STA. BÁRBARA"), Copart "Pátio Porto Seguro" (pátio em SP, não a cidade da BA) e Leilo "PATIO BENEVIDES" com UF errada. Ideia: tabela de apelidos de pátio.
10. **Leilões Brasil:** o filtro deixa passar eventos industriais ("Máquinas Pesadas... Vale").
11. **Parque dos Leilões:** endpoint só traz o mês corrente.
12. **Verificação anti-golpe** só por domínio; site legítimo sem domínio na ficha FENAJU aparece como "não verificado".
13. **Cobertura parcial conhecida:** Pestana lê até 5 páginas (49 leilões hoje); Norte até 4 páginas de 12; GP até 60 itens; Top/Sampaio pedem 300 lotes (resposta com limite alto não confirmada; se ignorado, vale o que a página carrega); Vinco depende da rolagem; Túlio pede 12 itens.
14. **Datas em "Z" que já são de Brasília:** Túlio (GraphQL) e Top/Sampaio mandam "2026-10-21T14:00:00Z" mas o site mostra 14:00; o robô usa o valor como está. Savoy manda UTC real ("+00:00") e o robô subtrai 3 h. Se algum horário parecer errado, conferir essa regra.
15. **Fontes com 0 normal** (Parque, Leilões MG, Túlio, Freire, Sampaio): não disparam o alerta de "layout mudou"; só fora do ar/redirecionamento.
16. **Aba Security and quality** do repositório com **2 alertas** não investigados (possivelmente a chave da Sodré da execução #1 do diagnóstico).
17. **Aviso Node.js 20** nas actions (não quebra hoje).
18. `snapshots/` público, com datas misturadas; pode ser limpo um dia.
19. **Leilões de hoje já encerrados** aparecem em execuções manuais à tarde (filtro por data).

---

## 8. Descobertas da pesquisa e do reconhecimento

### 8.1 Mercado e fontes
- **Agregadores** (declarações próprias, não verificadas): ChaveLeilão (~120 mil lotes, +1.000 leiloeiros), Carro do Bairro / leiloesdecarro.com.br (foco veículos, "120+ leiloeiros"), Mapa do Leilão (pago: R$ 74,90/mês ou R$ 499,70/ano), Leiloverso, LeilôAI ("716.998 lotes abertos"), AutoLeilãoBR (fora do ar no teste: erro 530 Cloudflare Tunnel), Almanaque do Leilão (agenda de veículos, só 3 dias grátis), agendadeleiloes.com.br (blog de notícias), leiloeirosdobrasil.com.br (revista online).
- **FENAJU** (Federação Nacional das Juntas Comerciais) centraliza as 27 Juntas; é a fonte oficial para conferir leiloeiro. Não existe leiloeiro oficial fora desse cadastro. Organizadoras como **Copart, VIP Leilões e Loop** não têm ficha única (usam leiloeiros diferentes por estado) e são legítimas.
- **Sites falsos conhecidos:** `loopleiloes.org` (o oficial é loopleiloes.com.br); na pesquisa apareceu `jucemg-gov-br.org` imitando a JUCEMG (o oficial é jucemg.mg.gov.br). A JUCEMG orienta consultar leiloeiros só no site oficial dela.
- **Domínio `.leilao.br`** (e `.lel.br`) é usado por leiloeiros oficiais; o radar trata como sinal positivo.
- **Plataformas de software de leilão** (white label, um coletor pode cobrir vários sites): SOLEON, Leilão PRO, Plataforma Leiloar, Superbid Exchange (Leilões Web), Leilotech, NC Brasil, EBL.
- Detran-RS publica calendário com o **site do leiloeiro** de cada leilão (ex.: cargneluttileiloes.com.br, qleilao.lel.br), o que ajuda a descobrir leiloeiros.


### 8.2 Resultado dos reconhecimentos
- **Diagnóstico #3 (29/09, 26 fontes):** acessíveis FENAJU, ChaveLeilão, Carro do Bairro, Mapa do Leilão, Leiloverso, LeilôAI, Almanaque, agendadeleiloes, leiloeirosdobrasil, Detran-MG, Detran-RS, Receita SLE, Leilo, Freitas, Sodré, Copart, VIP, Mega, Superbid, Leilões Brasil, Parque. Bloqueadas: Loop (429 Vercel), MGL (403), João Emilio (403), AutoLeilãoBR (530).
- **Diagnóstico #4 (30/09, 58 URLs, Passo 20):** 21 sites novos abriram (HTTP 200), dos quais Kron, Mafra e Monzon depois se mostraram vazios por barreira Cloudflare (ver seção 6, item 28); bloqueados (403 "Um momento…"/Cloudflare ou tempo esgotado): João Emílio, MGL, AMT, Aragão, Leiloei, Universo dos Leilões, Daniel Garcia, Rico, Bruno Niewinski, Lance Já, Leilão Público PR. Mudanças: **Superbid passou a 403**, **Almanaque recusou conexão** (ERR_CONNECTION_CLOSED).
- **Diagnóstico #5 (30/09, 14 URLs, Passo 23):** ver item 28 da seção 6.

### 8.3 Endpoints e estruturas encontrados
- **FENAJU:** `GET https://www.fenaju.org.br/api/public/leiloeiros?page=N&origem=fenaju` → `{data:[...], limit:20, page, total:1948, totalPages:98}`; campos: `nome, email, dominio, dominio_url, situacao ("Regular"), juntaSigla, juntaUF, matricula, matriculas[{matricula, status, junta{sigla,uf}}]`. Ficha: `/api/public/leiloeiros/{id}`. Juntas: `/api/public/juntas`.
- **Copart:** `GET https://www.copart.com.br/public/data/auctionsCalendarList` → `data.saleList[]` com `saleName` ("Cidade - UF"), `auctionDate.dateAsInt` (AAAAMMDD), `startTime`, `auctioneerName` (com matrícula na Junta).
- **Sodré Santoro:** `GET https://prd-api.sodresantoro.com.br/api/v1/auctions?limit=N` (e `?status=online`) → `data[]` com `name, dates[].value, segments[].name, quantity, location`. Busca de lotes: `POST https://www.sodresantoro.com.br/api/search-lots`.
- **Leilo:** `api.leilo.com.br/v1/leiloes/lista-site` (trouxe leilões passados), `v1/lote/busca-elastic` (POST, lotes). A agenda em texto (`leilo.com.br/agenda`) é o que o radar usa.
- **Parque dos Leilões:** `GET https://www.parquedosleiloes.com.br/eventos` → `{data:{"AAAA-MM-DD":[{name,type}]}}`.
- **Superbid:** `https://store-query.superbid.net/stores/?portalId=[2,15]&filter=hasOpenedOffers:true&pageSize=300...` → 141 lojas/leiloeiros com ofertas abertas. **Endpoint de eventos ainda não descoberto.**
- **Carro do Bairro:** `https://api.leiloesdecarro.com.br/api/v1/anuncio-leilao/em-leilao-hoje?limite=12`, `.../destaques`, `.../catalogo-leilao/ufs` (MG tinha 228 anúncios). Campos do lote: `url` (site do leiloeiro), `dataHoraFinal`, `cidadeAnuncio`, `ufAnuncio`, `leiloeiroNome`, `modalidadeLeilao`. **Endpoint de listagem paginada ainda não descoberto** (a página `/leiloes` não foi capturada).
- **Leiloverso:** `/api/vehicles` e `/api/properties` (lotes, com `site`, `detailsUrl`, `city`, `state`, `auctionDate` às vezes nulo). Nível lote.
- **LeilôAI:** `/api/home/oportunidades`, `/api/stats/urgency`. Nível lote, foco em nota de oportunidade.
- **Detran-MG:** HTML com cards; município em `class="capa-municipio"`, pátio em `<b>`, texto "Encerramento: dd/mm/aaaa hh:mm", status "Publicado"/"Finalizado", link `/lotes/lista-lotes/{id}/{ano}`. 30 cards, sem paginação visível.
- **Detran-RS:** texto com blocos "Edital EMAV", "Data do Leilão", "Local do Leilão: <url do leiloeiro>", "Leiloeiro Oficial", "Cidade:". Abas "Confirmados" e "Previstos" (só Confirmados é lido).
- **Receita SLE:** portal público `https://www25.receita.fazenda.gov.br/sle-sociedade/portal`; tabelas "Próximos Editais" e "Aberto para Proposta" em texto separado por tabulação: edital + cidade, órgão, propostas até, lances, nº de lotes.
- **Leilões Brasil:** tabela "Data, Horário, Categoria, Tipo, Nome, Onde"; categoria "VEICULO"; inclui eventos de terceiros (Copart, Superbid).
- **Almanaque:** agenda via Supabase `agenda_publica` (não usar, ver seção 3).

Novos (Passos 21 a 25):
- **Copart (horário):** `saleTime` "HHMMSS" em Brasília (usar); `startTime`/`displayTime` em UTC.
- **Palácio dos Leilões:** capa com seções "30 de Setembro / Quarta-Feira / título / 'juatuba 112 cajamar 15 ...'" (lotes por pátio e por tipo; total = soma/2); link `site/?leilao_pesquisa={id}` achado após "oferece <span>N</span> lotes". Pátios: Juatuba (MG), Cajamar (SP), Salvador (BA), externo.
- **Saraiva (plataforma "Suporte Leilões"):** blocos "COD. 576 / 60/2026 33 lotes", status, título, "Data do encerramento / dd/mm/aaaa / A partir das / HH:MM" por praça; links `/eventos/leilao/{cod}/...`.
- **GP:** `POST https://www.gpleiloes.com.br/gp-api/index/inicio/{pagina}/{tamanho}` com `{"filtro":null}` → `value.content[]` (`codigoLeilao, titulo, descricao, data, hora, data2, hora2, tipoDescricao, numeroDeLotes, comitente, lote.localizacao`); link `https://www.gpleiloes.com.br/#leilao/{cod}`.
- **Leilões MG (Seplag):** `https://www.leiloes.mg.gov.br/`; hoje "Não existe nenhum leilão disponível no momento". Formato com leilão aberto ainda desconhecido (o leitor gera um aviso para conferir no site).
- **Kleiber:** blocos "164/2026 / tipo / comitente / título / DATA: / 06/10/2026 - 09H00 / status / modo / N LOTE(S)"; links levam a sites de leiloeiros parceiros.
- **E-Leilões:** lista "tipo / status / título / N lotes / Encerramento em 6 de Outubro"; horários nos "Destaques" ("06/10/2026 · 10h00"); links `/eventos/leilao/{id}/{slug}`.
- **Pestana:** `/agenda-de-leiloes` renderizada no servidor, 12 por página, paginação por botão "Próximo" (sem URL); blocos ": 433 lotes / ONLINE / título / 30/09/2026 QUA - 10:00".
- **WR:** `/agenda-de-leiloes`; " 30/09/2026 às 09:00 / título / modo / status"; links `https://www.wrleiloes.com.br/leilao/{id}/{slug}`.
- **Norte:** `https://www.sistema.norteleiloes.com.br/index/leiloes2?pagina=N&porPagina=12&&api=true` → `dados[]` (`LEI_ID, LEI_NOME, LED_DIA, LED_DIA_F` com hora "10h00", `LRL_NOME` local, `LEI_QTD_LOTES`, `LEI_SITE_SITUACAO`, `urlLeilao`), `dadosPaginacao` (37 itens, 4 páginas); também `index/calendario?api=true`.
- **Leiloeiro Público:** `GET https://api-lances.leiloeiropublico.com.br/leilao/agenda/ativos/todos` → lista (`id` "26.101", `titulo` "Automóvel: Xaxim (SC)", `status`, `dataHora1`, `dataHora2`, `resumo`, `vendaDireta`); link `ListagemLote.aspx?Leilao={id}`.
- **Túlio (plataforma Leilotech):** `POST https://tulioleiloes.com.br/go/graphql`, operação "Agenda" (`items[].data, pracaOrdem, leilao{title, description, location{city,uf}, comitente, lotesCount}`).
- **Savoy (Supabase):** `https://api.savoyleiloes.com.br/rest/v1/auctions?...` com `title, subtitle, auction_phases[end_date UTC, completed], lots_count`; lotes em `/rest/v1/lots` com categoria.
- **Vinco:** capa com cards "ID: 483 / título / Data: Qua, 30/Set/2026, 10h00" ou "1ª Praça: ..."; só aparecem após rolar a página; link `leilao.php?idLeilao={id}`. `pesquisa.php` (POST) só traz filtros.
- **Cardoso:** capa com "título / 1º Leilão: dd/mm/aaaa às HH:MM / 2º Leilão: ...".
- **Freire:** capa com "comitente / dd/mm/aaaa às HH:MM / modo / status / local / - Cidade - UF".
- **Top/Pizzolatti e Sampaio (mesma plataforma):** `POST {site}/app/lotes` e `/app/agenda` com `{"botao":"AGENDA DE LEILÕES", "mes":"AAAA-MM-DD", "limite":58, "dom":"pizzolatti"|"sampaio", ...}` → `lotes[]` (`nome, local, leilao, id, status, data, vara, url`).
- **Kron/Mafra/Monzon (Superbid Exchange "faststore"):** Cloudflare challenge; sem API capturada.
- **Sumaré:** `/leiloes` 404; links `/leiloes/{id}` existem.

### 8.4 Verificação da lista de leiloeiros do usuário (Passo 20)

Links recebidos (37): norteleiloes, kronleiloes (busca Superbid), sampaioleiloes/home, joaoemilio (com e sem www), wrleiloes, parquedosleiloes, cardosoleiloes, leiloesfreire, mgl.com.br/online/1/4/, amtleiloes, aragaoleiloes, leilao.detran.mg.gov.br, palaciodosleiloes/site/index.php, saraivaleiloes, leiloes.mg.gov.br, leiloeiropublico, gpleiloes/#/, leiloei.com/felipe-nunes-gomes-teixeira-bignardi, universodosleiloes, danielgarcialeiloes, topleiloes/home, ricoleiloes, sumareleiloes, tulioleiloes, brunoniewinskileiloes, cav.receita.fazenda.gov.br (login do e-CAC; o radar já lê a Receita pelo portal público), lanceja, e-leiloes, kleiberleiloes, savoyleiloes, vincoleiloes, mafraleiloes (busca Superbid), monzonleiloes (busca Superbid), leilaopublico.paas.pr.gov.br, pestanaleiloes, copart.com.br.

| Domínio | Registro | Titular (Registro.br) | Leiloeiro Regular na FENAJU (junta, matrícula) |
|---|---|---|---|
| norteleiloes.com.br | 2008-07-01 | Sandro de Oliveira | Sandro de Oliveira (JUCEAC 25) |
| kronleiloes.com.br | 2023-10-18 | Helcio Kronberg | domínio não consta; titular = Helcio Kronberg, Regular (JUCEPAR 653) |
| sampaioleiloes.com.br | 2018-06-28 | João Paulo Sampaio Damiani | João Paulo Sampaio Damiani (JUCESC AARC/379) |
| joaoemilio.com.br | 1997-08-25 | NTL Sistemas Integrados Ltda. | João Emilio de Oliveira Filho (JUCERJA 45) |
| wrleiloes.com.br | 2018-07-04 | Wesley Ramos | Wesley Silva Ramos (JUCEAC 18) |
| parquedosleiloes.com.br | 1998-06-19 | Gian Roberto Cagni Braggio | Gian Roberto Cagni Braggio (JUCIS 51); Ozias Pereira Tavares (JUCIS 30) |
| cardosoleiloes.com.br | 2014-03-19 | Emerson Lopes Cardoso | Emerson Lopes Cardoso (JUCESP 939) |
| leiloesfreire.com.br | 2000-08-29 | Koisas Usadas Ltda | 4 leiloeiros (JUCEAL, JUCEPE, JUCESE), ex.: Osman Sobral e Silva (JUCESE 110) |
| mgl.com.br | 2017-07-09 | MGL.com.br Leilões Ltda | Lucas e Jonas Antunes Moreira (JUCEMG 637 e 638) e mais 1 |
| amtleiloes.com.br | 2012-02-06 | Álvaro Marques Teixeira | Álvaro Marques Teixeira (JUCISRS 274) |
| aragaoleiloes.com.br | 2015-10-21 | Cesar Augusto Aragão Pereira | Cesar Augusto Aragão Pereira (JUCEPE 26700000471) |
| palaciodosleiloes.com.br | 1998-08-14 | Rogério Lopes Ferreira | Rogério Lopes Ferreira (JUCEMG 394) e mais 4 leiloeiros (JUCEMG) com o mesmo domínio |
| saraivaleiloes.com.br | 2010-08-10 | Saraiva Leilões | Angela Saraiva Portes Souza (JUCEMG 441; também JUCEB) |
| leiloeiropublico.com.br | 2010-04-15 | Rodolfo Rosa Schöntag | Rodolfo da Rosa Schöntag (JUCESC AARC 263) |
| gpleiloes.com.br | 2006-02-09 | Gustavo Costa Aguiar Oliveira | Gustavo Costa Aguiar Oliveira (JUCEMG 507) e mais 2 |
| leiloei.com | 2014-03-28 | (não informado no RDAP .com) | Felipe Nunes Gomes Teixeira Bignardi (JUCESP 950; e-mail @leiloei.com) |
| universodosleiloes.com.br | 2019-10-02 | Alexsander Pretti Domingos | Alexsander Pretti Domingos (JUCEMG 1221) |
| danielgarcialeiloes.com.br | 2019-03-19 | Daniel Elias Garcia | Daniel Elias Garcia (JUCESC AARC/306) |
| topleiloes.com.br | 2016-03-14 | Paulo Pizzolatti Neto | Paulo Pizzolatti Neto (JUCESC AARC/19) |
| ricoleiloes.com.br | 2021-03-27 | Daniel Almeida da Silva | 11 leiloeiros JUCESP com e-mail @ricoleiloes.com.br (ex.: Sabrina de Andrade Verrone, 1052) |
| sumareleiloes.com.br | 2002-07-10 | Atena Prep. de Leilões e Gestão de Pátios Ltda | Gustavo Henrique Gontijo Genu (JUCIS 242) |
| tulioleiloes.com.br | 2020-10-18 | Marcos Antonio Tulio | Marcos Antonio Tulio (JUCEPAR 20/326-L) |
| brunoniewinskileiloes.com.br | 2024-04-22 | Bruno Coletto Niewinski | Bruno Coletto Niewinski (JUCISRS 482) |
| lanceja.com.br | 2009-03-19 | Lance Já Cons. e Asse. Gestão de Negócios | Cristiane Borguetti Moraes Lopes (JUCESP 661) |
| e-leiloes.com.br | 2019-12-17 | Marcos Roberto Torres Junior | Marilaine Borges de Paula (JUCESP 601; e-mail @e-leiloes.com.br) |
| kleiberleiloes.com.br | 2011-12-26 | Kleiber Leite Pereira | Kleiber Leite Pereira (JUCEMAT 4) |
| savoyleiloes.com.br | 2009-07-23 | Arnold Strass | Arnold Strass (JUCESP 384) e mais 1 |
| vincoleiloes.com.br | 2025-04-04 | Victor Alberto Severino Frazão | Victor Alberto Severino Frazão (JUCESP 806) e mais 1 |
| mafraleiloes.com.br | 2024-03-19 | Marcos Roberto Fracasso | domínio não consta; titular = Marcos Roberto Fracasso, Regular (JUCESC 593, e-mail Gmail) |
| monzonleiloes.com.br | 2018-05-22 | Joacir Monzon Pouey | Joacir Monzon Pouey (JUCEPAR 18/295-L) |
| pestanaleiloes.com.br | 2011-04-12 | Liliamar Pestana Gomes | Liliamar F. P. Pestana Marques Gomes (JUCISRS 168; JUCEPAR) e mais 6 leiloeiros com o mesmo domínio |
| copart.com.br | 2011-08-05 | Copart do Brasil Organização de Leilões Ltda. | organizadora (lista confiável) |
| leilao.detran.mg.gov.br, leiloes.mg.gov.br, leilaopublico.paas.pr.gov.br | - | - | órgãos públicos (.gov.br) |

Conclusão: **nenhum falso**. Situação de cada um no radar:
- **Já estavam no radar:** Detran-MG, Parque dos Leilões, Copart (e Receita pelo portal público).
- **Incluídos no radar (Passos 21 a 25), 17:** Palácio dos Leilões, Saraiva, GP e Leilões MG (lote MG), Kleiber, E-Leilões, Pestana, WR, Norte, Leiloeiro Público, Túlio, Savoy, Vinco, Cardoso, Freire, Top/Pizzolatti, Sampaio.
- **Fora por bloqueio anti-robô (rota: agregadores na v2):** João Emílio, MGL, AMT, Aragão, Leiloei, Universo dos Leilões, Daniel Garcia, Rico, Bruno Niewinski, Lance Já, Leilão Público PR (tempo esgotado), Kron, Mafra, Monzon.
- **Fora, a investigar:** Sumaré.

---

## 9. Como o `radar.py` funciona (versão atual, 1310 linhas, commit ce72d29)

### 9.1 Fluxo da execução (`main`)
1. Marca a hora de início; carrega `saude.json` publicado na execução anterior (`carrega_saude`, via `https://andre-reale-bot.github.io/radar-leiloes/saude.json`; na primeira vez não existe e começa vazio).
2. `carrega_fenaju()`: percorre as 98 páginas da API da FENAJU e monta os domínios de leiloeiros "Regular" (campos `dominio`, `dominio_url` e domínio do e-mail, exceto e-mails genéricos). Se vier com menos de 500 domínios e houver cópia, usa a **cópia salva** (`fenaju_copia`) e gera alerta; se vier completa, atualiza a cópia.
3. Para cada fonte em `FONTES` (em fila): `captura()` abre a página no Chromium, espera carregar, guarda **texto, HTML, respostas JSON, status HTTP e URL final**, e executa os extras da fonte: GET extra, POST extra (`{"url","post"}`), **cliques de paginação** (`{"clicar":"Próximo","vezes":4}`, junta o texto de cada página) ou **rolagem** (`{"rolar":5}`).
4. Chama o leitor da fonte; filtra a janela **hoje até hoje+15 (data de Brasília)**; registra OK/FALHOU e a quantidade; roda `avalia_saude` (alertas da fonte).
5. Deduplica por (data, hora, nome completo normalizado, cidade, link) e classifica o link com `verifica()` (✔ órgão público .gov.br; ✔ FENAJU: nome (junta matrícula); ✔ lista confiável: Copart, VIP, Loop, Superbid; ✔ domínio .leilao.br/.lel.br; senão ⚠ não verificado).
6. `calcula_distancias(unicos, saude["cache_distancias"])`: base de municípios + OSRM (origem BH, lotes de até 80 destinos), tempo × 1,10. Se a base ou o OSRM falharem, usa a cópia (coordenadas por "CIDADE|UF" e distâncias por coordenada). BH = "Em BH"; "Online" = "Online"; sem cidade identificada = "?".
7. `verifica_dominios_semanal()`: a cada 7 dias consulta o Registro.br de cada domínio das fontes (exceto .gov.br): domínio vencido ou titular diferente geram alerta (aviso de troca por uma semana; depois adota o novo titular).
8. Se a execução passou de 40 min, alerta.
9. Gera `site/index.html`, `site/saude.json` e `site/leiloes.json`; o workflow publica no GitHub Pages.

Campos de cada leilão: `data, hora, nome, fonte, link, cidade, uf, obs, ver, ver_txt, km, tempo`.

### 9.2 Filtros e utilitários
- `eh_veiculo()`: palavras-chave (VEICUL, CARRO, MOTO, CAMINH, PESADO, SUCATA, UTILITAR, SEGURADORA, AUTOMOV, AUTOMOTOR, FROTA, ONIBUS, RECUPERAD, PICK, CAMIONET, REBOQUE, TRATOR, "VAN "), depois de remover **falsos** por palavra inteira (`FALSOS_VEICULO`: motor(es), motorista(s), motosserra(s), motobomba(s), motoniveladora(s), motogerador(es), carroceria(s), carrinho(s), carretel/carretéis). Exclui imóveis/aeronaves sem menção a veículo.
- `MARCAS`: regex de marcas/modelos (FIAT, VW, VOLKSWAGEN, FORD, CHEVROLET, GM, TOYOTA, HONDA, HYUNDAI, RENAULT, NISSAN, MITSUBISHI, MMC, JEEP, PEUGEOT, CITROEN, STRADA, DUSTER, L200, TRITON, HILUX, S10, GOL, UNO, PALIO, SAVEIRO, AMAROK, RANGER), usada por Kleiber, Vinco, Cardoso, Top e Sampaio.
- `MESES` (nomes completos) e `MESES3` (Jan, Fev...), `slug_texto`, `data_br`, `hora_de`, `acha_uf`, `dominio_base` (3 rótulos em .com.br/.gov.br).

### 9.3 As 26 fontes (ordem de execução)

| # | Fonte | URL aberta | Extra | Leitor | Observações |
|---|---|---|---|---|---|
| 0 | FENAJU (só valida) | API `leiloeiros?page=N&origem=fenaju` | todas as páginas | `carrega_fenaju` | 1.948 leiloeiros |
| 1 | Detran-MG | `https://leilao.detran.mg.gov.br/` | não | `p_detran_mg` | cards "Publicado"; data = encerramento |
| 2 | Detran-RS | `https://pcsdetran.rs.gov.br/consulta-calendario-leilao` | não | `p_detran_rs` | aba "Confirmados" |
| 3 | Receita Federal (SLE) | `https://www25.receita.fazenda.gov.br/sle-sociedade/portal` | não | `p_receita` | editais mistos |
| 4 | Copart | `https://www.copart.com.br/` | não | `p_copart` | horário por `saleTime` (Brasília) |
| 5 | Sodré Santoro | `https://www.sodresantoro.com.br/` | GET `prd-api.../auctions?limit=200` | `p_sodre` | segmento Veículos |
| 6 | Leilo | `https://leilo.com.br/agenda` | não | `p_leilo` | agenda genérica, UF padrão GO |
| 7 | Freitas | `https://www.freitasleiloeiro.com.br/Leiloes/Agenda` | não | `p_freitas` | agenda genérica, UF padrão SP |
| 8 | Leilões Brasil | `https://www.leiloesbrasil.com.br/agenda` | não | `p_leiloesbrasil` | categoria VEICULO, ignora Copart |
| 9 | Parque dos Leilões | `https://www.parquedosleiloes.com.br/` | não | `p_parque` | JSON `/eventos` (mês corrente) |
| 10 | Palácio dos Leilões | `https://www.palaciodosleiloes.com.br/site/index.php` | não | `p_palacio` | Juatuba/MG; lotes por pátio |
| 11 | Saraiva | `https://saraivaleiloes.com.br/` | não | `p_saraiva` (`p_suporteleiloes`) | 1º/2º/3º leilão |
| 12 | GP | `https://www.gpleiloes.com.br/` | POST `gp-api/index/inicio/1/60` | `p_gp` | 1ª e 2ª praça |
| 13 | Leilões MG (Seplag) | `https://www.leiloes.mg.gov.br/` | não | `p_leiloes_mg` | hoje sem leilões; gera aviso se aparecer |
| 14 | Kleiber | `https://kleiberleiloes.com.br/` | não | `p_kleiber` | MT; usa `MARCAS` |
| 15 | E-Leilões | `https://www.e-leiloes.com.br/` | não | `p_eleiloes` | data = encerramento; DETRAN conta como veículo |
| 16 | Pestana | `https://www.pestanaleiloes.com.br/agenda-de-leiloes` | clica "Próximo" 4x | `p_pestana` | 5 páginas de 12 |
| 17 | WR | `https://wrleiloes.com.br/agenda-de-leiloes` | não | `p_wr` | Detrans AC/AM/RR |
| 18 | Norte | `https://www.norteleiloes.com.br/leiloes` | GET API `leiloes2` páginas 2 a 4 | `p_norte` | ignora cancelado/suspenso/realizado |
| 19 | Leiloeiro Público | `https://www.leiloeiropublico.com.br/Agenda.aspx` | não (API capturada) | `p_leiloeiropublico` | SC/PR; link por leilão |
| 20 | Túlio | `https://tulioleiloes.com.br/agenda` | não (GraphQL capturado) | `p_tulio` (`p_leilotech`) | PR |
| 21 | Savoy | `https://www.savoyleiloes.com.br/agenda` | não (API capturada) | `p_savoy` | SP; UTC - 3 h |
| 22 | Vinco | `https://www.vincoleiloes.com.br/` | rola 5x | `p_vinco` | ignora Encerrado/Sustado |
| 23 | Cardoso | `https://www.cardosoleiloes.com.br/` | não | `p_cardoso` | ignora imóveis |
| 24 | Freire | `https://www.leiloesfreire.com.br/` | não | `p_freire` | AL/PE/SE; quase sempre 0 (filtro rígido) |
| 25 | Top/Pizzolatti | `https://topleiloes.com.br/home` | POST `app/lotes` (limite 300) | `p_top` (`p_astavero`) | agrupa lotes por leilão; ignora "Teste" |
| 26 | Sampaio | `https://sampaioleiloes.com.br/home` | POST `app/lotes` (limite 300) | `p_sampaio` (`p_astavero`) | idem |

Contagens na última execução (30/09 00:11): Detran-MG 13, Detran-RS FALHOU (0), Receita 6, Copart 46, Sodré 17, Leilo 6, Freitas 2, Leilões Brasil 4, Parque 0, Palácio 6, Saraiva 4, GP 7, Leilões MG 0, Kleiber 1, E-Leilões 3, Pestana 5, WR 2, Norte 2, Leiloeiro Público 2, Túlio 0, Savoy 2, Vinco 3, Cardoso 1, Freire 0, Top 2, Sampaio 0. Total 134 (23 MG); 82 com distância.

Não estão no radar (só no diagnóstico ou bloqueados): ChaveLeilão, Carro do Bairro, Mapa do Leilão, Leiloverso, LeilôAI, AutoLeilãoBR, Almanaque, agendadeleiloes, leiloeirosdobrasil, VIP, Loop, Mega, Superbid, MGL, João Emílio, os bloqueados da seção 8.4 e Sumaré.

### 9.4 Contingências (saúde das fontes e da página)
Faixa vermelha no topo da página, com fonte e motivo, pedindo ao usuário para procurar o site novo quando for o caso:
1. **Fora do ar:** erro sem texto ou HTTP ≥ 400 em **dois dias diferentes** seguidos (o primeiro dia só registra `falha_desde`).
2. **Redirecionamento para outro domínio** (compara `dominio_base` da URL final com a original).
3. **Fonte zerada:** 0 leilões hoje, mas a mediana dos últimos 7 dias (mínimo 2 dias de histórico) é ≥ 1 (layout provavelmente mudou).
4. **Volume anormal:** mais que o triplo da mediana (com ≥ 3 dias e mediana ≥ 2).
5. **Horário fora do comum:** leilão com hora fora de 06:00 a 22:59.
6. **Domínio vencido ou titular diferente** no Registro.br (semanal).
7. **FENAJU indisponível** (usa a cópia salva e avisa).
8. **Execução acima de 40 min** (limite do GitHub: 60).
9. **Página desatualizada:** JavaScript na própria página compara a hora de geração (UTC embutida) com o relógio do navegador; acima de **26 h** mostra faixa vermelha dizendo para olhar a aba Actions. Funciona mesmo com o robô parado.

`saude.json` guarda: `fontes` (por fonte: `qtds` por data, últimos 14 dias; `falha_desde`), `rdap` (titular e vencimento por domínio), `rdap_data`, `rdap_alertas`, `fenaju_copia` (data, total, domínios), `cache_distancias` (`coords`, `dist`). Histórico começou em 29/09 à noite; alertas que dependem dele passam a valer nos dias seguintes.

### 9.5 Como testar (sandbox do Claude)
- Leitores: montar `cap = {"texto","html","apis":[{"url","corpo"}]}` a partir de `snapshots/<pasta>` (gz) e chamar o leitor.
- Regressão: carregar a versão anterior e a nova como módulos e comparar, fonte a fonte, a saída dos leitores nas mesmas capturas (`json.dumps` igual); comparar também o diff de código (linhas removidas).
- Distância: simular `baixa_texto` com o CSV local de municípios (baixar de `raw.githubusercontent.com/kelvins/...`) e resposta OSRM falsa.
- Página e JavaScript: gerar `index.html`, abrir com Playwright via `file://`, clicar em botões, conferir ordem e filtros, tirar print. Para a faixa de desatualização, trocar a data embutida por uma de 30 h atrás.
- Recursos de captura (cliques, rolagem): testar com um HTML local simples.

---

## 10. O que falta fazer (roadmap)

### Já feito antes da v2 (29 e 30/09)
Tipo de execução e distância de BH (18); lista única por proximidade (19); 17 leiloeiros da lista do usuário (21 a 25); correções de fuso, horário da Copart e filtros (22, 23, 26); contingências de fontes e da página (24, 27); ícone 📡 (25); 2FA (28).

### Imediato
1. **Passo 29: cópia deste markdown no repositório** (6ª contingência aprovada; a partir daí, repetir ao fim de toda sessão). O usuário sobe o arquivo `contexto-radar-leiloes.md` com **Add file > Upload files**. Atenção: o repositório é público; o markdown não tem segredos (códigos da 2FA ficam só na memória do projeto), mas tem o primeiro nome e a cidade do usuário.
2. Conferir a execução automática das 06:00 de 30/09 (primeira com todas as contingências): Detran-RS voltou? Faixa vermelha correta?
3. Usar a página por alguns dias anotando o que faltar (leilão conhecido que não apareceu, link errado, UF vazia).

### Pequenos ajustes já identificados (não aprovados ainda)
- Coluna "Data" sem quebra de linha.
- "Carreta"/semirreboque como veículo.
- Sumaré (novo diagnóstico).
- Esconder leilões de hoje com horário já passado.

### Como ampliar fontes (ordem de ganho por esforço, apresentada ao usuário)
1. Agregadores (Carro do Bairro, Leiloverso): um coletor cobre dezenas/centenas de leiloeiros. 2. Plataformas white label (Superbid, SOLEON, Leilão PRO, Leiloar, Leilotech): um parser serve a vários sites. 3. Detrans de outros estados (SP, RJ, ES, GO, BA primeiro). 4. Grandes organizadoras fora do radar (VIP, Mega; Loop, MGL, João Emilio, Superbid e os sites da plataforma Superbid, como Kron, Mafra e Monzon, bloqueiam o robô; alternativa via agregadores). 5. Varredura semanal dos leiloeiros FENAJU que nunca aparecem. Princípio: **medir cobertura antes de crescer**, para não gastar esforço em fontes redundantes.

### Versão 2 (próxima, recomendada nesta ordem)
1. ~~Consertar o `diagnostico.py`~~ **feito (Passos 15 a 17).**
2. **Agregadores:** Carro do Bairro e Leiloverso primeiro (nível lote; agrupar lotes por domínio do leiloeiro + data para virar "leilão"). Descobrir endpoints de listagem paginada capturando as páginas internas (`/leiloes`, filtros por UF). **Recomendado começar por aqui** (maior cobertura por coletor escrito).
   - **Alertas por modelo de veículo (pedido do usuário, fazer junto com os agregadores):** André mantém um arquivo simples no GitHub (ex.: `modelos.txt`, um modelo por linha) e a página ganha a seção "Seus alertas" com leilão, lote, link e data onde o modelo aparece. Exige ler o nível **lote**; fontes com listas de lotes já identificadas: Detran-MG (`/lotes/lista-lotes/{id}/{ano}`), Sodré (`search-lots`), Leilo (`busca-elastic`), Carro do Bairro, Leiloverso; Copart e Receita exigem investigação. Cuidados: tempo de execução (limite de 60 min; começar por MG) e variações de nome (ex.: "MARRUA", "AM 200"), cadastradas no próprio arquivo.
3. **Detrans de outros estados**, começando pelos vizinhos de MG: **SP, RJ, ES, GO, BA**; depois os demais. Para cada um: achar a URL pública de leilões, incluir no diagnóstico, escrever parser.
4. **Superbid** (descobrir API de eventos), **VIP Leilões**, **Mega Leilões**.
5. Contornar bloqueios de Loop, MGL e João Emilio, se possível, ou buscar esses leilões via agregadores.
6. Corrigir as pendências da seção 7 (links específicos por leilão, UF faltante, filtro industrial). O alerta de fonte zerada já foi feito (Passo 24). CPF em nome de pátio: **não fazer** (decisão do usuário).

### Melhorias de negócio no nível lote (pedido do usuário em 29/09: implementar todas com o tempo)
Crítica que originou a lista: o radar responde "onde tem leilão", mas quem vive de arrematar, consertar e revender precisa saber **qual lote dá lucro**; o valor está no nível do lote. Em ordem de valor:
1. **Lance vs. FIPE:** % do lance inicial abaixo da tabela FIPE, com ordenação pelos maiores descontos (há API pública não oficial e gratuita da FIPE; confirmar disponibilidade antes de usar).
2. **Classificação de risco:** origem (financeira/retomada = mais segura; seguradora = sinistrado), monta (pequena/média/grande), sucata ou circulação, documentação e débitos; com filtro para esconder o que ele não compra.
3. **Custo total e lance máximo:** lance + comissão do leiloeiro (normalmente 5%) + taxas de pátio + frete (usar o km já calculado) + débitos; ele informa a margem desejada e o radar mostra o lance máximo.
4. **Histórico de arremates:** gravar o preço final quando o site divulgar; com o tempo, gráfico "preço final/FIPE por modelo" (ativo exclusivo, que nenhum agregador oferece).
5. **Prazo de visitação** (vistoria presencial) exibido no leilão/lote.
6. **Visual:** foto em miniatura do lote e mapa de MG com os pátios.
7. **Aviso diário no Telegram** só com lotes que passem nos filtros dele.
Ordem recomendada (aceita): itens 1, 2 e 3 na v2, junto com agregadores e alertas por modelo (usam os mesmos dados de lote); item 4 logo depois (só gera valor com o tempo); 5 a 7 na sequência.

### Medição de cobertura (prometida ao usuário)
Após alguns dias de uso: buscar manualmente ~20 leilões de veículos em fontes independentes, contar quantos estão na lista, calcular o percentual real, identificar tipos de fonte faltantes e transformar cada falha em fonte nova. Repetir mensalmente.

### Fase "leiloeiros restantes" (sem IA)
Verificação **semanal** da página inicial dos leiloeiros FENAJU que nunca aparecem nas fontes: procurar "veículo" + datas; o que as regras não souberem ler vai para uma seção **"Revisar manualmente"** na página.

### Ideias de melhoria
- Aviso diário por e-mail ou Telegram (ver melhorias de negócio, item 7).
- Alertas por tipo de veículo (viaturas, utilitários), extensão dos alertas por modelo.
- Filtro por raio de distância (ex.: até 300 km).
- Histórico de leilões que apareceram e sumiram.
- Atualizar actions para versões com Node 24.
- Abas "Previstos" do Detran-RS e datas de visitação.
- Plano B para Detrans com portal fechado: Diário Oficial do Estado.
- Visitar as fontes em paralelo e guardar o navegador em cache (hoje dispensável: minutos grátis e menor risco de bloqueio em fila).

---

## 11. Protocolo para evoluir o robô

1. Claude atualiza a lista `FONTES` do `diagnostico.py` com as URLs a investigar (agendas, APIs). A lista atual é a do Passo 23 (Pestana, Vinco x2, Norte, WR, Leiloeiro Público, Túlio, Savoy, Sumaré, Kron x2, Mafra, Monzon, Superbid); `VERIFICAR = []` (a verificação FENAJU/RDAP só roda se a lista tiver domínios). O diagnóstico agora rola a página 5 vezes e grava `rede.json.gz` (todas as respostas com status).
2. Usuário sobe o arquivo e roda **Actions > Diagnostico das fontes > Run workflow** (nunca "Re-run").
3. Claude clona o repositório, lê `snapshots/resumo.json` e as pastas, identifica APIs/estruturas e escreve os leitores, testando offline.
4. Claude entrega o novo `radar.py` com o teste de regressão feito; usuário sobe (**Add file > Upload files**) e roda **Actions > Radar de leiloes > Run workflow**.
5. Usuário manda print do topo e de "Fontes consultadas"; Claude confere número por número com o teste e explica qualquer diferença.

Boas práticas adotadas:
- **Fim de cada sessão:** atualizar este markdown e lembrar o usuário de subi-lo no repositório (substitui o anterior; não mexer em `radar.py`/`diagnostico.py` nesse upload).
- Conferir no repositório, a cada upload, se o arquivo ficou idêntico ao entregue (hash do commit aparece nos prints do Actions).
- Reler linha por linha e testar antes de entregar; em mudanças de código antigo, provar que nada se perdeu.
- Ao explicar diferenças de contagem entre execuções, separar "mudou o site" de "mudou o código".
- Quando o usuário mandar print que parece antigo, suspeitar de cache (pedir Ctrl+F5 ou aba anônima).
- Ser transparente quando uma suposição do Claude se mostrar errada (ex.: Kleiber não era da plataforma da Saraiva).
- Dois arquivos podem ser enviados juntos no mesmo upload; radar e diagnóstico podem rodar ao mesmo tempo.

Roteiros-padrão com todos os cliques (usar sempre neste nível de detalhe):
- *Subir arquivo:* 1) baixar o arquivo da mensagem (Downloads); 2) GitHub: avatar (canto superior direito) > **Your repositories** > **radar-leiloes**; 3) botão **Add file**, ao lado do botão verde **Code**; 4) **Upload files**; 5) arrastar o arquivo (ou **choose your files**); 6) esperar aparecer listado e clicar no botão verde **Commit changes**.
- *Rodar o robô:* 1) **Actions** no menu superior; 2) coluna esquerda: **Radar de leiloes** (ou **Diagnostico das fontes**); 3) **Run workflow** e o botão verde **Run workflow**; 4) aguardar o círculo verde (radar ~4 a 6 min; diagnóstico 2 a 8 min).
- *Conferir a página:* link azul no quadro "radar" da execução (ou favorito); **Ctrl+F5** se vier layout antigo.
- *Editar arquivo pequeno (YAML):* abrir o arquivo, ícone de lápis, Ctrl+A, colar, **Commit changes**.
- *2FA/recuperação:* avatar > **Settings** > **Password and authentication**.

---

## 12. Estado atual em uma frase

O radar está no ar em **https://andre-reale-bot.github.io/radar-leiloes/** com **26 fontes** (Detran-MG, Detran-RS, Receita Federal, Leilões MG, Copart, Leilões Brasil e 20 leiloeiros), 134 leilões na última execução (30/09 00:11, 23 em MG), distância de BH, lista por proximidade, ícone 📡, verificação FENAJU, e contingências completas (faixa vermelha por fonte com problema, página desatualizada, cópias de segurança, alertas de volume/horário/tempo e checagem semanal de domínios); conta GitHub com 2FA. **Próximos movimentos:** Passo 29 (cópia deste markdown no repositório), conferir a execução das 06:00 (Detran-RS), usar a página alguns dias e então começar a v2 pelos agregadores + alertas por modelo + melhorias de lote (FIPE, risco, custo).
