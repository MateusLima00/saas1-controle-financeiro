import { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, XCircle, X } from "lucide-react";

// -----------------------------------------------------------------------
// ToastProvider.jsx
//
// Notificação toda simples (canto inferior direito) pra dar feedback
// visual em ações como "meta criada", "assinatura removida" etc — coisas
// que antes só mudavam a lista silenciosamente, sem confirmação nenhuma
// pro usuário de que a ação realmente aconteceu.
//
// Uso: const { mostrarToast } = useToast(); mostrarToast("Meta criada!");
// -----------------------------------------------------------------------
const ToastContext = createContext(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast precisa estar dentro de <ToastProvider>");
  return ctx;
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const mostrarToast = useCallback((mensagem, tipo = "sucesso") => {
    const id = Date.now() + Math.random();
    setToasts((atual) => [...atual, { id, mensagem, tipo }]);
    setTimeout(() => {
      setToasts((atual) => atual.filter((t) => t.id !== id));
    }, 3200);
  }, []);

  function fechar(id) {
    setToasts((atual) => atual.filter((t) => t.id !== id));
  }

  return (
    <ToastContext.Provider value={{ mostrarToast }}>
      {children}

      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-full max-w-xs">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="bg-surface border border-border rounded-card shadow-xl shadow-black/30 p-3 flex items-start gap-2 animate-[popIn_.15s_ease-out]"
          >
            {t.tipo === "erro" ? (
              <XCircle size={16} className="text-danger shrink-0 mt-0.5" />
            ) : (
              <CheckCircle2 size={16} className="text-success shrink-0 mt-0.5" />
            )}
            <span className="text-sm flex-1">{t.mensagem}</span>
            <button
              onClick={() => fechar(t.id)}
              aria-label="Fechar notificação"
              className="text-text-muted hover:text-text-primary"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
