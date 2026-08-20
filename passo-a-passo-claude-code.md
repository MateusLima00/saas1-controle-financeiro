# Passo a passo — Controle Financeiro pessoal (adaptação do frontend + backend + Telegram)

> Instruções para o Claude Code executar. Projeto pessoal, uso exclusivo do
> dono, sem necessidade de suportar múltiplos usuários.

## Contexto

- O **frontend já existe** (React + Vite + Tailwind v4 + Recharts + React
  Router), com 9 telas prontas e navegáveis usando dados mockados em
  `src/data/mockData.js`: Login, Dashboard, Extrato, GastosDiarios, Metas,
  Investimentos, Assinaturas, Categorias, Contas.
- Falta: persistência real, autenticação real, proteção de rota, e
  integração com a API da Pluggy (via Conector 200 / Meu Pluggy).
- O **backend será novo**, em **Python (FastAPI + SQLAlchemy)**, com
  **PostgreSQL no Neon.tech**, deploy no **Render**.
- Sincronização Pluggy é diária (~1x/dia, sem webhook no plano gratuito).
  Fallback: import manual de CSV/OFX.
- Integração com o **bot Telegram do Nero já existe do lado do Nero**
  (`worker.js`, função `enviarTransacaoParaSaas1`): o LLM do Nero já
  detecta gastos/receitas em texto livre e tenta mandar pro backend
  financeiro via `POST /integrations/nero/transactions`, com fallback
  pra KV local se falhar. Falta só implementar esse endpoint no backend
  financeiro (Etapa 4).

## Etapa 0 — Segurança (obrigatória, transversal a todas as etapas)

> Não é uma etapa isolada a ser feita no fim — cada etapa abaixo deve ser
> implementada já respeitando estes pontos. Dados financeiros pessoais
> estão em jogo.

1. **Nenhum segredo no frontend.**
   - `PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET`, `NERO_INTEGRATION_TOKEN`
     (compartilhado com o Worker do Nero, onde é `SAAS1_INTEGRATION_TOKEN`),
     `SESSION_SECRET`, connection string do banco — tudo isso só existe
     como variável de ambiente do **backend**, nunca em código do React,
     nunca em `.env` commitado, nunca em variável `VITE_*` (essas vão
     pro bundle do navegador, são públicas).
   - O frontend só conhece `VITE_API_URL` (endereço do backend).
2. **Backend só expõe o necessário.**
   - CORS restrito à origem exata do frontend (não usar `*`).
   - Todas as rotas de dados (accounts, transactions, categories, goals,
     investments, subscriptions) exigem autenticação — nenhuma rota
     pública além de `/auth/login`.
   - Rate limiting básico nas rotas de auth e no webhook do Telegram
     (evitar força bruta / spam).
3. **Login seguro.**
   - Senha nunca em texto puro: hash com `bcrypt` ou `argon2` (nunca MD5
     ou SHA simples sem salt).
   - JWT com expiração curta + refresh token, ou sessão server-side com
     cookie `HttpOnly`, `Secure`, `SameSite=Strict`.
   - Bloqueio/backoff após N tentativas de login incorretas.
4. **Contra SQL Injection e afins.**
   - Usar exclusivamente ORM (SQLAlchemy) com queries parametrizadas —
     nunca montar SQL por concatenação/f-string com input do usuário.
   - Validar e tipar todo input de entrada com Pydantic (schemas) antes
     de tocar no banco.
   - Sanitizar/validar o parser de mensagens do Telegram antes de
     qualquer persistência (é a rota mais exposta a input "livre").
5. **Outros pontos básicos de hardening.**
   - HTTPS obrigatório em produção (sem exceção, mesmo sendo uso único).
   - Headers de segurança (`Content-Security-Policy`,
     `X-Content-Type-Options`, `X-Frame-Options`) no backend.
   - Nunca logar dados sensíveis (senha, token, número de conta) em
     logs de aplicação.
   - `.env` no `.gitignore` desde o primeiro commit do backend.
   - Validar em `/integrations/nero/transactions` o header
     `Authorization: Bearer <NERO_INTEGRATION_TOKEN>` em toda chamada —
     sem token correto, `401` imediato, sem processar nada.

## Etapa 1 — Backend base (FastAPI)

### 1.1 Estrutura de pastas

```
backend/
  .env                  # nunca commitado (ver Etapa 0)
  .env.example
  .gitignore
  requirements.txt
  app/
    main.py             # cria app, registra routers, middlewares, CORS
    config.py           # lê variáveis de ambiente (pydantic-settings)
    database.py         # engine, SessionLocal, Base
    models.py           # SQLAlchemy models
    schemas.py          # Pydantic schemas (request/response)
    security.py         # hash de senha, JWT, dependências de auth
    deps.py             # get_db, get_current_user (Depends)
    routers/
      auth.py
      accounts.py
      transactions.py
      categories.py
      goals.py
      investments.py
      subscriptions.py
      pluggy.py         # troca client_id/secret por apiKey, sync
      integrations.py   # endpoint chamado pelo Worker do Nero
    services/
      pluggy_client.py  # wrapper das chamadas à API da Pluggy
```

### 1.2 Modelos de dados (SQLAlchemy)

`users`, `accounts`, `categories`, `transactions`, `goals`,
`goal_contributions`, `investments`, `subscriptions` — schema já
validado nas conversas anteriores, campos alinhados com `mockData.js`
do frontend.

### 1.3 Autenticação

- Login único (email/senha, um só registro em `users`).
- Hash de senha com `bcrypt` (via `passlib`).
- **Decisão: sessão com cookie `HttpOnly` + `Secure` + `SameSite=Strict`**
  (não JWT). Motivo: cookie `HttpOnly` não é acessível via JavaScript,
  reduzindo a superfície de um XSS roubar a sessão; e um app de uso
  único não precisa da complexidade de refresh token/blacklist que só
  compensa com múltiplos serviços validando o mesmo token.
- Sessão guardada no backend (tabela `sessions` ou store em memória/
  Redis se houver), cookie carrega só o `session_id` opaco.
- `deps.get_current_user`: dependency do FastAPI que lê o cookie,
  busca a sessão, valida expiração.
- Expiração da sessão configurável (ex. 7 dias, renovando a cada uso).

### 1.4 Endpoints por router (todos exigem auth, exceto `/auth/login`)

- `auth.py`: `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`
- `accounts.py`: `GET /accounts`, `GET /accounts/{id}`
- `transactions.py`: `GET /transactions` (com filtros de data/categoria),
  `POST /transactions` (lançamento manual), `PATCH /transactions/{id}`
- `categories.py`: `GET/POST/PATCH/DELETE /categories`
- `goals.py`: `GET/POST/PATCH /goals`, `POST /goals/{id}/contributions`
- `investments.py`: `GET/POST/PATCH /investments`
- `subscriptions.py`: `GET/POST/PATCH/DELETE /subscriptions`
- `pluggy.py`: `POST /pluggy/sync` (dispara sync manual — botão
  "atualizar agora"), `GET /pluggy/status`
- `integrations.py`: `POST /integrations/nero/transactions` (chamado
  pelo Worker do Nero, autenticado por `NERO_INTEGRATION_TOKEN` — ver
  Etapa 4)

### 1.5 Setup local

Subir com PostgreSQL (local ou Neon — ver Etapa 3.5), rodar uma seed
com os mesmos dados de `mockData.js` para comparar visualmente com o
frontend antes de plugar dado real.

## Etapa 2 — Adaptar o frontend para consumir a API real

1. Criar `src/api/client.js` com um wrapper de fetch (baseURL via
   variável de ambiente `VITE_API_URL`, `credentials: 'include'` pra
   enviar o cookie de sessão em toda requisição, tratamento de erro
   padronizado).
2. Para cada página que hoje importa de `src/data/mockData.js`
   (Dashboard, Extrato, Metas, Investimentos, Assinaturas, Categorias,
   Contas, GastosDiarios), substituir o import estático por um
   `useEffect` + `useState` que busca da API — mantendo os mesmos nomes
   de campo pra não precisar reescrever o JSX das telas.
3. Adicionar estados de loading e erro em cada tela (hoje não existem,
   já que os dados eram síncronos).
4. Implementar `RotaPrivada.jsx` de verdade: hoje só existe o componente,
   mas não bloqueia nada — precisa checar a sessão (ex. chamando
   `GET /auth/me`) e redirecionar pro `/login` se não autenticado.
5. Fazer o `Login.jsx` autenticar de verdade contra `POST /auth/login`
   do backend (hoje só navega pra `/`) — o cookie de sessão é setado
   automaticamente pelo backend na resposta, nada pra guardar
   manualmente no frontend.
6. CORS do backend precisa permitir `credentials: true` e a origem
   exata do frontend (cookie cross-origin exige isso).

## Etapa 3 — Integração Pluggy

Credenciais já obtidas: `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET`
(dashboard.pluggy.ai), guardadas só no `.env` do backend.

1. `services/pluggy_client.py`:
   - Padrão de dois tokens confirmado na documentação oficial: o backend
     troca `CLIENT_ID` + `CLIENT_SECRET` por uma **API key** de curta
     duração (`POST /auth` da Pluggy) — essa API key é o único segredo
     usado nas chamadas seguintes (`X-API-KEY` header), e nunca sai do
     servidor.
   - Cachear a API key em memória com controle de expiração (renovar
     quando expirar, não gerar uma nova a cada request).
2. `routers/pluggy.py` → `POST /pluggy/sync`: usa a API key pra buscar
   contas/transações via API da Pluggy (Conector 200) e faz
   upsert em `accounts` e `transactions`.
3. Job diário (APScheduler ou cron do SO) chamando `sync()`
   automaticamente 1x/dia.
4. Botão "atualizar agora" no frontend (tela Contas) chama
   `POST /pluggy/sync` sob demanda — testar na prática se isso força
   sync fora do ciclo diário (pendência já identificada).
5. Fallback de import manual de CSV/OFX: endpoint de upload + parsing
   simples, populando `transactions` (mesmo formato de saída do sync
   da Pluggy, pra não duplicar lógica de exibição no frontend).

## Etapa 3.5 — Banco de dados e hospedagem (decidido)

- **Banco: PostgreSQL desde já** (não SQLite) — hospedado no
  **Neon.tech** (Postgres serverless gratuito).
- **Backend: deploy no Render** (free tier).
- Free tier do Render "dorme" após período de inatividade — por isso
  entra um keep-alive.

Passos concretos:

1. Criar conta no **Render**.
2. Criar banco no **Neon.tech**, copiar a connection string.
3. Trocar `DATABASE_URL` do backend (`.env` local e variável de
   ambiente no Render) pra apontar pro Postgres do Neon — nunca commitar
   essa string (ela contém usuário/senha do banco).
4. Deploy do backend no Render, apontando pro repositório do backend.
5. Endpoint `GET /health` (simples, sem autenticação, só retorna 200)
   + configurar **UptimeRobot** ou **cron-job.org** batendo nesse
   endpoint a cada 10–14 min, pra evitar o backend dormir no free tier.

Isso substitui o SQLite mencionado na Etapa 1.5 — usar Postgres desde
o ambiente local também (via Neon ou um Postgres local), pra não ter
divergência de dialeto SQL entre dev e produção.



## Etapa 4 — Integração com o bot do Nero (já implementada do lado do Nero)

Descoberta importante: o Nero (`nero-backend`, Cloudflare Worker) **já
tem essa integração pronta do seu lado**, sob o nome interno "Saas1".
Não precisa mexer no `worker.js` — só implementar o endpoint que ele já
espera, no backend financeiro.

### 4.1 Como já funciona no Nero (não mudar)

- Quando você fala algo tipo "gastei 30 no uber" pro bot, o LLM do Nero
  (mesmo mecanismo que já usa pra criar tarefas) gera uma tag
  `[GASTO:descrição|valor|categoria]` ou `[RECEITA:...]` na resposta.
- `parseCommands()` intercepta essa tag e chama
  `enviarTransacaoParaSaas1()`, que faz o `POST` pro backend financeiro.
- **Detecção é por LLM (texto livre), não comando fixo** — decisão já
  tomada e implementada do lado do Nero; não há necessidade de criar
  `/gasto` como comando dedicado.
- Se a chamada falhar (backend fora do ar, env var não configurada), o
  Nero guarda o lançamento na própria KV local (`state.transactions`)
  como fallback, sem perder o dado — e você recategoriza/importa depois.
- Fonte única de verdade continua sendo o backend financeiro; a KV do
  Nero é só um buffer de contingência.

### 4.2 Contrato exato que o backend financeiro precisa implementar

| Item | Valor |
|---|---|
| Endpoint | `POST /integrations/nero/transactions` |
| Auth | Header `Authorization: Bearer <NERO_INTEGRATION_TOKEN>` |
| Body recebido | `{ descricao: string, valor: number, tipo: "debit" \| "credit" }` |
| Resposta esperada (200) | JSON contendo pelo menos `{ categoria: string }` — usado na mensagem de confirmação no chat |
| Erro | Qualquer status != 2xx faz o Nero cair no fallback de KV local |

`routers/telegram.py` (ou um `routers/integrations.py` mais genérico,
já que tecnicamente não é tráfego do Telegram, é Worker-para-API):

1. `POST /integrations/nero/transactions`:
   - Validar `Authorization: Bearer <token>` contra `NERO_INTEGRATION_TOKEN`
     (env var do backend financeiro) — sem esse header correto, `401`.
   - Validar `descricao`, `valor`, `tipo` com Pydantic (`tipo` restrito
     ao enum `debit`/`credit`).
   - Aplicar `categories.regras` na `descricao` pra achar a categoria
     (mesmo mecanismo usado nas telas de Categorias do frontend); sem
     match, cai em "Outros".
   - Criar a `transaction` com origem `"nero"`.
   - Retornar `{ categoria }` (nome da categoria encontrada).

### 4.3 Variáveis de ambiente (nomes já fixados pelo `wrangler.toml` do Nero)

- No Nero (Cloudflare Worker secrets):
  - `SAAS1_API_URL` → URL pública do backend financeiro no Render
    (ex. `https://<nome>.onrender.com`).
  - `SAAS1_INTEGRATION_TOKEN` → **mesmo valor** do token abaixo.
- No backend financeiro (`.env` / env var no Render):
  - `NERO_INTEGRATION_TOKEN` → gerado uma vez (ex. `openssl rand -hex 32`),
    nunca commitado, nunca no frontend — é só backend-a-backend.

### 4.4 Passos concretos

1. Gerar `NERO_INTEGRATION_TOKEN` (string aleatória longa).
2. Configurar no Render: variável `NERO_INTEGRATION_TOKEN` com esse valor.
3. Configurar no Cloudflare (via `wrangler secret put SAAS1_API_URL` e
   `wrangler secret put SAAS1_INTEGRATION_TOKEN`): a URL do backend no
   Render e o **mesmo** token gerado no passo 1.
4. Implementar `POST /integrations/nero/transactions` no backend
   financeiro conforme o contrato da tabela acima.
5. Testar: mandar "gastei 20 no ifood" pro bot do Nero, confirmar que a
   transação aparece no backend financeiro (e depois no frontend) com a
   categoria certa.
6. Comando `/resumo` no Nero (se quiser) pode futuramente consultar o
   backend financeiro em vez da KV local — não é bloqueante, fica pra
   depois.

## Etapa 4.5 — Revisão do código já escrito (achados, a corrigir)

Revisão feita em cima do estado real do projeto (backend FastAPI +
frontend já parcialmente migrados pelo Claude Code). Resumo: a base está
sólida — sem SQL cru em lugar nenhum, sessão via cookie `HttpOnly` com
tabela `Session` no banco, `hmac.compare_digest` na validação do token
do Nero, todos os routers de dados protegidos por
`dependencies=[Depends(get_current_user)]` no nível do router. Pontos
a corrigir antes de seguir:

### 4.5.1 Segurança — corrigir antes de ir pra produção

1. **Falta `.gitignore` na pasta `backend/`**, e existe um `.env` real
   (com secrets) do lado do `.env.example`. Prioridade máxima: criar o
   `.gitignore` (`.env`, `__pycache__/`, `*.db`, `venv/`) **antes** de
   qualquer `git init`/`git add` nessa pasta — se já rodou `git add .`
   em algum momento, rodar `git rm --cached .env` também.
2. **Cookie de sessão sem `secure=True`** em `create_session()`
   (`app/auth.py`) — ajustar pra `secure=True` (só funciona sobre
   HTTPS; em produção no Render isso é garantido, em dev local por
   `http://localhost` o cookie `Secure` não é enviado — usar
   `secure=not DEBUG` ou equivalente, condicionado a env).
3. **Rate limit de login só existe no frontend** (`Login.jsx`,
   contador `tentativas`) — é cosmético; `POST /auth/login` chamado
   direto (fora da tela) não tem limite nenhum hoje. Implementar
   bloqueio server-side (ex: contar tentativas falhas por email/IP na
   tabela ou em memória, com backoff), mantendo a mensagem genérica que
   já existe.

### 4.5.2 Consolidar Telegram: só o Nero (decisão tomada)

O backend acabou ganhando **dois canais Telegram** durante o
desenvolvimento: um bot próprio e independente (`telegram.py`,
`telegram_service.py`, `message_parser.py`, `telegram_client.py`,
`telegram_poll.py`, com parser regex) **além** da integração via Nero
(`integrations.py`). Decisão: manter só a via Nero, remover o bot
próprio — evita duplicidade e um segundo bot/token pra manter.

1. Remover do backend: `app/routers/telegram.py`,
   `app/telegram_service.py`, `app/message_parser.py`,
   `app/telegram_client.py`, `app/telegram_poll.py`.
2. Remover o `include_router(telegram.router)` e o import de
   `telegram` em `app/main.py`.
3. Remover `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` do `.env` /
   `.env.example` do backend financeiro (não são mais usados aqui —
   continuam existindo normalmente do lado do Nero, que é quem fala
   com o Telegram).
4. Manter: `app/routers/integrations.py` (o `/integrations/nero/
   transactions`) — é o único canal de lançamento por mensagem daqui
   pra frente.
5. Se algum teste manual já foi feito com o bot próprio, não precisa
   desfazer nada nos dados — as transações criadas ficam como estão
   (`origem="telegram"`), só o canal deixa de receber novas.



1. Variáveis de ambiente documentadas em `.env.example` (backend e
   frontend).
2. `README.md` do backend com passo a passo de setup local.
3. Revisar CORS do FastAPI para aceitar apenas a origem do frontend.
4. Hospedagem: backend no Render (free tier + keep-alive via
   UptimeRobot/cron-job.org), banco no Neon.tech — ver Etapa 3.5.

## Etapa 6 — Melhorias de frontend (independentes do backend)

Achados de revisão do frontend (zip mais recente, já com `Extrato.jsx`
migrado pra API real). Todos os itens abaixo dá pra fazer sem esperar
nada do backend — é só React/Tailwind.

### 6.1 Responsividade mobile — prioridade, contradiz o README atual

O `README.md` do projeto promete "acessível por navegador, desktop e
mobile", mas hoje **não existe nenhuma classe responsiva** (`sm:`,
`md:`, `lg:`) em nenhum arquivo do frontend. Pontos concretos:

1. `Sidebar.jsx` é fixa, sem versão colapsável/drawer pra tela pequena
   — em mobile ela deveria virar um menu hambúrguer ou bottom nav.
2. `Dashboard.jsx` usa `grid-cols-3` e `grid-cols-2` fixos — em tela de
   celular isso espreme os cards de métrica até ficar ilegível. Trocar
   por algo como `grid-cols-1 sm:grid-cols-3` (empilha em telas
   pequenas, 3 colunas a partir de `sm`).
3. `Extrato.jsx` é uma `<table>` sem scroll horizontal nem versão em
   cards — tabela sempre quebra em mobile. Duas opções: `overflow-x-auto`
   no container (mínimo esforço) ou uma versão em lista de cards
   abaixo de `md` (melhor experiência, mais trabalho).
4. Aplicar o mesmo raciocínio (grid fixo → responsivo) nas outras
   telas com grid: `Metas.jsx`, `Investimentos.jsx`, `Assinaturas.jsx`
   — checar cada uma antes de assumir que só Dashboard/Extrato têm
   esse problema.

### 6.2 Extrato — falta o que a aba "fluxo" do Meu Pluggy tem

1. **Filtro por data** (hoje só tem categoria + busca por texto) —
   adicionar seletor de período (mês atual, mês anterior, intervalo
   customizado), passando como query param pro backend
   (`GET /transactions?de=...&ate=...`) em vez de filtrar só no front,
   já que o histórico real da Pluggy pode ter muitos meses.
2. **Filtro por conta** — com múltiplos bancos conectados, hoje não dá
   pra ver o extrato de só um deles. Precisa de um seletor de conta
   (dropdown com as contas de `GET /accounts`) + filtro
   `?conta_id=...` no backend.
3. **Coluna "conta"** na tabela — hoje só mostra categoria, não dá pra
   saber de qual banco veio a transação.
4. **Saldo corrente (running balance)** por linha — é o que dá a
   sensação de "fluxo" que o Meu Pluggy tem; calculável no front a
   partir do saldo inicial da conta + soma acumulada, ou vindo pronto
   do backend.
5. **Paginação** — sem isso, meses de histórico real da Pluggy deixam
   a tabela pesada. Paginação simples (`?page=&limit=`) já resolve.

### 6.3 UX menor

1. `Dashboard.jsx`: cards de Investimentos/Assinaturas não mostram
   tendência (só o de saldo/gasto tem "+8% vs mês passado"), mesmo os
   dados existindo pra calcular.
2. Falta modal de detalhe/edição de transação individual — hoje a
   única forma de trocar a categoria de um lançamento é indo na tela
   de Categorias, não direto no extrato clicando na linha.
3. Garantir que toda tela que busca da API (não só Extrato) tenha os
   três estados: carregando, erro, vazio — checar se `Metas.jsx`,
   `Investimentos.jsx`, `Assinaturas.jsx`, `Categorias.jsx`, `Contas.jsx`
   e `GastosDiarios.jsx` já foram migrados e se seguem o mesmo padrão
   de `Extrato.jsx` (`carregando`/`erro`/`useEffect`+`api.get`).



1. Etapa 1 (backend base) — sem isso nada mais funciona.
2. Etapa 2 (frontend consumindo API real) — já valida o backend
   visualmente nas telas existentes.
3. Etapa 3 (Pluggy) — dado real substituindo o seed.
3.5. Etapa 3.5 (banco Neon + deploy Render) — pode ser feita em
   paralelo à 1/2, já que define onde tudo vai rodar.
4. Etapa 4 (Telegram) — canal alternativo de lançamento manual.
4.5. Etapa 4.5 (revisão de segurança + consolidação do Telegram) — fazer
   logo após a 4, antes de deploy em produção.
5. Etapa 5 (polimento).
6. Etapa 6 (melhorias de frontend) — não depende de backend, pode ser
   feita em paralelo com qualquer uma das etapas acima.
