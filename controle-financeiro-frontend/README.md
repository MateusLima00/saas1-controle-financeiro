# Controle Financeiro (frontend)

Frontend do projeto de controle financeiro pessoal. `src/data/mockData.js`
tem dados falsos usados só como referência de formato; o app consome a API
real do backend. Não há integração automática com banco — transações entram
via lançamento manual, bot do Telegram, ou importação de extrato (CSV/OFX).

## Stack

- React + Vite
- Tailwind CSS v4 (via `@tailwindcss/vite`, sem `tailwind.config.js`)
- Recharts (gráfico de categorias)
- React Router (navegação entre as telas)

## Como rodar

Pré-requisito: Node.js instalado (18+ recomendado).

```bash
# 1. instalar as dependências
npm install

# 2. rodar em modo desenvolvimento
npm run dev
```

Isso abre em `http://localhost:5173`. Qualquer alteração nos arquivos
recarrega a página automaticamente (hot reload).

## Estrutura de pastas

```
src/
  components/       componentes reutilizáveis (Sidebar, cards, gráfico, etc)
  pages/            uma tela por arquivo (Login, Dashboard, Extrato, Categorias, Contas)
  data/mockData.js  dados falsos pra navegar sem backend
  App.jsx           rotas do app
  index.css         tema de cores (dark mode) + import do Tailwind
```

## Telas disponíveis

| Rota               | Tela                                                  |
|--------------------|--------------------------------------------------------|
| `/login`           | Login (mostrar/ocultar senha, manter conectado)        |
| `/`                | Dashboard (métricas, metas, investimentos, assinaturas) |
| `/extrato`         | Extrato completo com filtros                            |
| `/gastos-diarios`  | Lançamento rápido de gasto do dia a dia                |
| `/metas`           | Metas de poupança e planos de viagem, com aportes      |
| `/investimentos`   | Investimentos, com rendimento calculado                 |
| `/assinaturas`     | Assinaturas recorrentes, total mensal                   |
| `/categorias`      | Gerenciamento de categorias e regras                    |
| `/contas`          | Contas (cadastro manual) + importação de extrato        |

Veja **DESIGN.md** pra saber como mexer em cores, espaçamento e ícones.

