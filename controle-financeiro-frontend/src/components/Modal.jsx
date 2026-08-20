import { useEffect } from "react";
import { X } from "lucide-react";

// -----------------------------------------------------------------------
// Modal.jsx
//
// Popup genérico usado pelos formulários de "criar" (nova assinatura,
// nova meta, nova categoria, conta manual...). Renderiza por cima da
// tela toda, com fundo escurecido/desfocado atrás. Fecha ao clicar fora,
// apertar Esc ou no X do cabeçalho.
// -----------------------------------------------------------------------
export default function Modal({ aberto, titulo, onFechar, children }) {
  // Fecha com a tecla Esc
  useEffect(() => {
    if (!aberto) return;
    function aoTeclar(e) {
      if (e.key === "Escape") onFechar();
    }
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aberto, onFechar]);

  if (!aberto) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[10vh] bg-black/60 backdrop-blur-sm animate-[fadeIn_.15s_ease-out]"
      onClick={onFechar}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg bg-surface border border-border rounded-card shadow-2xl shadow-black/40 animate-[popIn_.15s_ease-out]"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold">{titulo}</h2>
          <button
            type="button"
            onClick={onFechar}
            aria-label="Fechar"
            className="text-text-muted hover:text-text-primary hover:bg-surface-2 rounded-[var(--radius-control)] p-1 transition-colors"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
