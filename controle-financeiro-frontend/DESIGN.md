# Guia de design

Todo o visual do app é controlado por **variáveis CSS** em `src/index.css`
(bloco `@theme`). As telas (`.jsx`) só usam classes Tailwind que leem essas
variáveis — nunca cor "hardcoded" direto no componente.

## Trocar a paleta inteira

Edite `src/index.css`:

```css
--color-accent: #7f77dd;   /* cor de destaque em todo o app */
--color-bg: #0d1117;       /* fundo geral */
--color-surface: #161b22;  /* fundo dos cards */
```

Salvou, o hot reload já mostra a mudança em todas as telas ao mesmo tempo.

## Trocar o visual de UMA tela só

Vá no arquivo da tela em `src/pages/NomeDaTela.jsx` e mexa nas classes
Tailwind do JSX. Não tem CSS separado por componente — é tudo classe
inline, então editar o `.jsx` já resolve.

Cola comuns:
- `bg-surface` `bg-surface-2` `bg-bg` → fundos
- `text-text-primary` `text-text-secondary` `text-text-muted` → textos
- `text-accent` `bg-accent` `border-accent` → destaque
- `text-danger` `text-success` `text-warning` → estados
- `rounded-card` → cards, `rounded-control` (classe `--radius-control` via `rounded-[var(--radius-control)]`) → inputs/botões
- `p-4` `gap-3` `mb-5` → espaçamento (escala Tailwind: cada unidade = 4px)

## Ícones

Usamos a lib `lucide-react`. Pra trocar o ícone de qualquer coisa:

```jsx
import { PiggyBank } from "lucide-react";
<PiggyBank size={18} className="text-accent" />
```

Lista completa e pesquisável de ícones: https://lucide.dev/icons

## Cores de categoria

Pra metas, investimentos, gráficos etc., use as variáveis `--color-cat-1`
até `--color-cat-6` (já mapeadas em `src/index.css`) em vez de inventar
hex novo — assim tudo fica consistente e fácil de re-temizar depois.
