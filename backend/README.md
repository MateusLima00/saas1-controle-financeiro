# Controle Financeiro — backend

API em Python (FastAPI + SQLAlchemy) para o frontend de controle financeiro
pessoal. Uso exclusivo do dono do projeto (login único, sem multiusuário).

## Stack

- FastAPI + Uvicorn
- SQLAlchemy (SQLite por padrão, `DATABASE_URL` troca pra Postgres depois)
- Autenticação por **sessão em cookie httpOnly** (não usa localStorage nem
  JWT) — o navegador guarda só um cookie opaco; a sessão fica na tabela
  `sessions` no banco.

## Como rodar

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
copy .env.example .env         # Windows (cp no Linux/Mac) — ajuste se quiser

python -m app.seed              # cria o banco e popula com os dados do mockData.js
uvicorn app.main:app --reload   # sobe em http://localhost:8000
```

O `seed.py` cria um usuário de login (`SEED_USER_EMAIL`/`SEED_USER_PASSWORD`
do `.env`, padrão `admin@example.com` / `troque-esta-senha`) e os mesmos
dados de `src/data/mockData.js` do frontend, pra comparar visualmente.

Docs interativas (Swagger) em `http://localhost:8000/docs`.

## Autenticação

- `POST /auth/login` — `{ "email": "...", "senha": "..." }`. Em caso de
  sucesso, seta o cookie `session_token` (httpOnly, `SameSite=Lax`, 7 dias).
- `POST /auth/logout` — invalida a sessão e remove o cookie.
- `GET /auth/me` — retorna o usuário logado (401 se não autenticado).
- Todas as rotas de dados exigem essa sessão (`Depends(get_current_user)`).

Como o cookie é httpOnly, o frontend precisa mandar `credentials: "include"`
em todas as chamadas `fetch` (isso já foi levado em conta pro CORS, que
libera só a origem definida em `FRONTEND_ORIGIN` com `allow_credentials=True`).

## Endpoints

| Recurso | Rotas |
|---|---|
| Contas | `GET/POST /accounts`, `PUT/DELETE /accounts/{id}` |
| Categorias | `GET/POST /categories`, `PUT/DELETE /categories/{id}` |
| Transações | `GET/POST /transactions`, `PUT/DELETE /transactions/{id}` |
| Metas | `GET/POST /goals`, `PUT/DELETE /goals/{id}`, `POST /goals/{id}/contributions` |
| Investimentos | `GET/POST /investments`, `PUT/DELETE /investments/{id}` |
| Assinaturas | `GET/POST /subscriptions`, `PUT/DELETE /subscriptions/{id}` |
| Dashboard | `GET /dashboard/resumo`, `GET /dashboard/gastos-por-categoria`, `GET /dashboard/evolucao` |
| Importação de extrato | `POST /accounts/{id}/import` (CSV/OFX) |
| Telegram | `POST /telegram/webhook` |

Os schemas de saída usam os mesmos nomes de campo do `mockData.js`
(`valorAlvo`, `valorAtual`, `ultimaSync`, `proximaCobranca`, etc.) pra
minimizar retrabalho no frontend na Etapa 2.

## Importação de extrato

Não há mais integração automática com banco (a integração via Pluggy/
MeuPluggy foi removida). Toda entrada de transação é manual: pelo formulário,
pelo bot do Telegram, ou por upload de extrato.

- **`POST /accounts/{id}/import`** — upload de extrato em `.csv`, `.ofx` ou
  `.qfx` (multipart/form-data, campo `file`). CSV precisa ter colunas de
  data/descrição/valor (nomes em português ou inglês, ex:
  `data,descricao,valor`). Deduplica lançamentos repetidos via hash de
  conta+data+descrição+valor (CSV) ou `FITID` (OFX), então reimportar o
  mesmo arquivo (ex: extrato do mês, todo mês) não duplica nada — só entram
  os lançamentos novos.

## Notificações por email

Enviadas via Gmail SMTP (`app/services/email_service.py`), exige
`SMTP_EMAIL` + `SMTP_APP_PASSWORD` (App Password gerada em
myaccount.google.com/apppasswords, com 2FA ativado na conta) no `.env`.
Sem essas duas variáveis, notificações só ficam logadas, não quebram
nada. `NOTIFY_EMAIL` é o destinatário (default: o próprio `SMTP_EMAIL`).

Gatilhos implementados (`app/services/notifications.py`):

- **Meta atingida** — ao criar uma contribuição ou editar uma meta que
  cruza o valor alvo (`routers/goals.py`).
- **Dígest diário** — 1 email por dia (job das 06:00), juntando: resumo (saldo total, gasto do mês), contas com saldo abaixo
  de `LOW_BALANCE_THRESHOLD`, assinaturas cobrando nos próximos
  `SUBSCRIPTION_ALERT_DAYS` dias, transações >= `LARGE_TRANSACTION_THRESHOLD`
  desde ontem, e gasto do dia anterior `UNUSUAL_SPEND_MULTIPLIER`x+ acima
  da média diária do mês. Cada seção só aparece se tiver algo a reportar.

## Login com Google (allowlist de 1 email)

Substitui gradualmente o login por senha — os dois convivem por enquanto
(`POST /auth/login` continua funcionando). `POST /auth/google` recebe o
ID token do Google Identity Services (`credential`), valida contra
`GOOGLE_CLIENT_ID` e só aceita se o email bater com `ALLOWED_LOGIN_EMAIL`
(uso pessoal — um único email pode logar). Sem essas duas variáveis,
responde `501`.

Setup (feito uma vez, no Google Cloud Console):
1. Criar projeto em console.cloud.google.com.
2. "OAuth consent screen" — tipo Externo, status **Testing** (não precisa
   publicar, e assim fica restrito de qualquer forma).
3. "Credentials" → "Create Credentials" → "OAuth client ID" → tipo **Web
   application** → em "Authorized JavaScript origins" adicionar
   `http://localhost:5174` (dev) e depois o domínio de produção.
4. Copiar o Client ID gerado pra `GOOGLE_CLIENT_ID` (backend, `.env`) e
   `VITE_GOOGLE_CLIENT_ID` (frontend, `.env`) — é público, não precisa de
   client secret nesse fluxo (o backend só verifica o ID token assinado).
5. Frontend (`Login.jsx`) só mostra o botão do Google se
   `VITE_GOOGLE_CLIENT_ID` estiver setado — sem isso, cai automaticamente
   no form de senha de sempre.

## Telegram (Etapa 4)

- **`POST /telegram/webhook`** — endpoint de produção. Configurar com
  `setWebhook` da API do Telegram apontando pra essa URL depois que a
  hospedagem estiver decidida.
- **`python -m app.telegram_poll`** — long-polling (`getUpdates`) pra testar
  localmente sem expor a porta 8000 na internet. **Atenção**: Telegram não
  permite webhook e polling simultâneos no mesmo bot — se o bot já tiver um
  webhook configurado (ex: reaproveitando um bot de outro projeto), é
  preciso `deleteWebhook` antes de testar e `setWebhook` de volta depois,
  senão o outro projeto para de responder.
- Mensagens são interpretadas por um parser baseado em regras
  (`app/message_parser.py`), não LLM — entende frases como "gastei 30 no
  uber hoje" (valor, tipo débito/crédito por verbos, data relativa
  "hoje"/"ontem", descrição). Categoria é casada automaticamente pela
  `regra` de cada categoria (mesma sintaxe `contém "x", "y"` usada na tela
  Categorias).
- Comando `/resumo` retorna saldo total e gasto do mês (reaproveita a
  mesma lógica do `GET /dashboard/resumo`).
- Só responde a mensagens do `chat_id` configurado em `TELEGRAM_CHAT_ID`
  — qualquer outro chat é ignorado silenciosamente (projeto de uso único).
- `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` só no `.env` do backend, nunca
  expostos ao frontend.

## Observações / simplificações assumidas

- `saldoMesAnterior` e o `saldo` do gráfico de evolução são calculados a
  partir do saldo atual das contas menos/mais as transações registradas
  depois do fim de cada mês — é uma aproximação razoável sem ter um
  snapshot histórico de saldo; pode ser refinado depois se necessário.
- `categoria` em `transactions` é armazenada como `categoria_id` (FK); a
  API devolve também o nome (`categoria`) pronto pra exibição, igual ao
  mock.
- `data` das transações e contribuições de metas é `date` real (ISO), não
  a string `"dd/mm"` do mock — ajuste de formatação fica pro frontend na
  Etapa 2.
- Import CSV/OFX e integração Telegram já estão completos (única forma de
  entrada de transação, além do formulário manual, depois da remoção da
  integração Pluggy).

## CORS

`CORSMiddleware` libera só a origem definida em `FRONTEND_ORIGIN`
(`allow_credentials=True`, já que a auth depende do cookie httpOnly) — não
usa `allow_origins=["*"]`. Em produção, `FRONTEND_ORIGIN` precisa apontar
pro domínio real do frontend deployado.

## Hospedagem

Ainda não decidida. O schema e a API não dependem de nenhuma plataforma
específica — SQLite serve pro uso pessoal atual, mas `DATABASE_URL` já
permite trocar por Postgres sem mudar código. Pontos a decidir quando for
hospedar:

- Onde rodar o backend (precisa ficar sempre no ar pro dígest diário e
  pro webhook do Telegram responderem).
- Trocar SQLite por Postgres se a plataforma escolhida não persistir disco
  local entre deploys.
- Ajustar `FRONTEND_ORIGIN` e o `VITE_API_URL` do frontend pros domínios
  reais.
- Registrar o `setWebhook` do Telegram apontando pra URL de produção
  (hoje só é testado via polling local).
- Setar `SELF_PING_URL` com a própria URL pública do Render assim que
  fizer o primeiro deploy — sem isso o job de keep-alive fica inativo e o
  free tier do Render volta a dormir após 15 min sem tráfego (job
  `keep_alive_ping` em `app/scheduler.py`, roda a cada 8 min, faz `GET
  /health` na própria URL).
