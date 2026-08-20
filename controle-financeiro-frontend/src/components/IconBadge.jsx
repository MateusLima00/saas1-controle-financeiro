import { IconeDinamico } from "./IconPicker";

// -----------------------------------------------------------------------
// IconBadge.jsx
//
// Quadradinho colorido com o ícone dentro — o mesmo padrão visual que
// aparecia copiado em Metas.jsx, Investimentos.jsx e Assinaturas.jsx.
// -----------------------------------------------------------------------
export default function IconBadge({ nome, cor, size = 18, tamanho = "w-8 h-8" }) {
  return (
    <span
      className={`${tamanho} shrink-0 rounded-[var(--radius-control)] flex items-center justify-center`}
      style={{ backgroundColor: "var(--color-surface-2)", color: cor }}
    >
      <IconeDinamico nome={nome} size={size} />
    </span>
  );
}
