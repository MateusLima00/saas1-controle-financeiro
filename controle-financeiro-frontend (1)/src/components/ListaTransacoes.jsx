// -----------------------------------------------------------------------
// ListaTransacoes.jsx
//
// Lista simples de transações (data, descrição, valor).
// Usado tanto no Dashboard (versão resumida) quanto no Extrato (completa).
//
// Props:
//  - transacoes: array de transações (ver formato em mockData.js)
// -----------------------------------------------------------------------
export default function ListaTransacoes({ transacoes }) {
  return (
    <div className="flex flex-col">
      {transacoes.map((t, index) => (
        <div
          key={t.id}
          className={`flex justify-between text-sm py-2 ${
            index !== transacoes.length - 1 ? "border-b border-border" : ""
          }`}
        >
          <span className="text-text-primary">{t.descricao}</span>
          <span className={t.tipo === "credit" ? "text-success" : "text-danger"}>
            {t.tipo === "credit" ? "+" : "-"}R$ {Math.abs(t.valor).toLocaleString("pt-BR")}
          </span>
        </div>
      ))}
    </div>
  );
}
