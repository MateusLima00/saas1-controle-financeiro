# meupluggy-refresher

Serviço isolado (não faz parte do backend principal do Saas1) que
automatiza o "Atualizar" que hoje é feito à mão em cada conexão bancária
no site [meu.pluggy.ai](https://meu.pluggy.ai).

## Por que isso é um serviço separado

O Conector 200 ("MeuPluggy") que usamos pra conectar os bancos no Saas1 é
uma ponte pro meu.pluggy.ai — nosso sync (`PATCH /items/{id}`) não força
esse conector a buscar dado novo na fonte, porque é um conector OAuth: a
[documentação oficial da Pluggy](https://docs.pluggy.ai/docs/updating-an-item)
confirma que conectores com MFA/OAuth só atualizam de verdade com o
usuário abrindo o Pluggy Connect (nesse caso, o próprio meu.pluggy.ai) —
não existe endpoint de API que bypasse isso.

Esse serviço fica separado do backend principal (`Saas1/backend`) de
propósito: ele guarda a senha de app do Gmail (usada pra ler o link de
login por email, já que o login do meu.pluggy.ai é passwordless) — é a
credencial mais sensível de todo o projeto, porque dá acesso de leitura à
caixa de entrada inteira. Isolando num serviço minúsculo, sem nenhuma
rota de dado de usuário, o raio de dano de uma eventual falha de
segurança fica bem menor do que se essa senha estivesse no backend
principal.

## Como funciona

1. `POST /atualizar` (autenticado por `Authorization: Bearer <REFRESH_TOKEN>`)
   dispara a automação em background e responde `202` na hora.
2. A automação: abre o meu.pluggy.ai, pede login por email, lê o link
   mágico via IMAP (Gmail), autentica, e clica em "Atualizar" em cada
   conexão bancária.
3. No final, chama de volta `POST /integrations/meupluggy-refresh-callback`
   no backend principal (autenticado por `SAAS1_CALLBACK_TOKEN`), que
   dispara a sincronização de verdade (`pluggy_sync.sync_all_items`).

## Deploy (Render, ambiente Docker)

Usa a imagem oficial `mcr.microsoft.com/playwright/python` (já vem com
Chromium + todas as dependências do sistema prontas) — o build normal
(`pip install` + `playwright install --with-deps`) quebra no Render
porque o `--with-deps` precisa de `sudo apt-get`, e o ambiente de build
deles não dá permissão de root.

1. Criar um novo **Web Service** no Render.
2. **Root Directory**: `meupluggy-refresher`
3. **Environment**: `Docker` (o Render detecta o `Dockerfile` automaticamente)
4. Configurar as variáveis de ambiente (ver `.env.example`) — gerar um
   `REFRESH_TOKEN` novo, preencher `MEU_PLUGGY_EMAIL`/`MEU_PLUGGY_IMAP_APP_PASSWORD`,
   e o mesmo `SAAS1_CALLBACK_TOKEN` configurado no backend principal
   (variável `MEUPLUGGY_REFRESH_CALLBACK_TOKEN`).

⚠️ Chromium é pesado — o free tier do Render pode não aguentar
confortavelmente. Se o serviço cair/reiniciar toda vez que a automação
rodar, considerar upgrade de plano só pra este serviço (o backend
principal continua no free tier normalmente, já que são serviços
independentes).

## Rodando local (teste manual, sem deploy)

```
cd meupluggy-refresher
py -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
# preencher .env a partir do .env.example
uvicorn main:app --reload
```

Depois, testar com:

```
curl -X POST http://localhost:8000/atualizar -H "Authorization: Bearer <REFRESH_TOKEN>"
```
