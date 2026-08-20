import Modal from "./Modal";

// -----------------------------------------------------------------------
// ConfirmDialog.jsx
//
// Popup de confirmação genérico, usado antes de qualquer exclusão
// (meta, investimento, assinatura, categoria, conta...). Evita apagar
// algo sem querer com um clique errado.
// -----------------------------------------------------------------------
export default function ConfirmDialog({ aberto, titulo = "Confirmar exclusão", mensagem, onConfirmar, onCancelar }) {
  return (
    <Modal aberto={aberto} titulo={titulo} onFechar={onCancelar}>
      <p className="text-sm text-text-secondary mb-5">{mensagem}</p>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancelar}
          className="text-sm px-4 py-1.5 rounded-[var(--radius-control)] text-text-secondary hover:bg-surface-2 transition-colors"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={onConfirmar}
          className="bg-danger text-white rounded-[var(--radius-control)] px-4 py-1.5 text-sm hover:opacity-90 transition-opacity"
        >
          Excluir
        </button>
      </div>
    </Modal>
  );
}
