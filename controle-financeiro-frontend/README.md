# Controle Financeiro (frontend)

Frontend do projeto de controle financeiro pessoal. Por enquanto só o
**front**, com dados mockados em `src/data/mockData.js` — ainda não tem
backend nem integração real com a Pluggy.

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
| `/contas`          | Contas conectadas (Pluggy) + conta manual               |

Veja **DESIGN.md** pra saber como mexer em cores, espaçamento e ícones.

## O que ainda falta (propositalmente fora desse escopo)

- Não tem backend / API real — tudo em `mockData.js` + estado local (useState)
- Dados de metas/investimentos/assinaturas/gastos diários somem ao dar refresh
  na página (não tem persistência ainda) — isso resolve quando o backend existir
- Login não autentica de verdade, só navega pra `/`
- Sem proteção de rota (dá pra acessar `/` sem passar pelo login)
- Integração com a API da Pluggy

Isso entra na próxima etapa, quando o backend for definido.
