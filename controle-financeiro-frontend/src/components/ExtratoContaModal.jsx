import { useEffect, useMemo, useState } from "react";
import { Upload } from "lucide-react";
import Modal from "./Modal";
import { api } from "../api/client";
import { formatDateShort, formatCurrency } from "../utils/format";

// -----------------------------------------------------------------------
// ExtratoContaModal.jsx
//
// Popup com o extrato de UMA conta (aberto a partir do card na tela
// Contas) — mesmo filtro de período do Extrato.jsx completo, só que já
// vem com essa conta fixada, pra ver rapidinho o que veio da Pluggy sem
// sair da tela de Contas.
// -----------------------------------------------------------------------

function primeiroDiaDoMes(data) {
  return new Date(data.getFullYear(), data.getMonth(), 1);
}

function ultimoDiaDoMes(data) {
  return new Date(data.getFullYear(), data.getMonth() + 1, 0);
}

function paraIso(data) {
  return data.toISOString().slice(0, 10);
}

const PERIODOS = [
  { valor: "mes-atual", label: "Mês atual" },
  { valor: "mes-anterior", label: "Mês anterior" },
  { valor: "personalizado", label: "Período personalizado" },
  { valor: "tudo", label: "Todo o histórico" },
];

export default function ExtratoContaModal({ conta, onFechar, onImportar }) {
  const [periodo, setPeriodo] = useState("mes-atual");
  const [de, setDe] = useState(paraIso(primeiroDiaDoMes(new Date())));
  const [ate, setAte] = useState(paraIso(ultimoDiaDoMes(new Date())));
  const [transacoes, setTransacoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    const hoje = new Date();
    if (periodo === "mes-atual") {
      setDe(paraIso(primeiroDiaDoMes(hoje)));
      setAte(paraIso(ultimoDiaDoMes(hoje)));
    } else if (periodo === "mes-anterior") {
      const mesAnterior = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
      setDe(paraIso(primeiroDiaDoMes(mesAnterior)));
      setAte(paraIso(ultimoDiaDoMes(mesAnterior)));
    } else if (periodo === "tudo") {
      setDe("");
      setAte("");
    }
  }, [periodo]);

  useEffect(() => {
    if (!conta) return;
    let ativo = true;
    setCarregando(true);
    setErro("");

    const params = new URLSearchParams({ conta_id: conta.id });
    if (de) params.set("de", de);
    if (ate) params.set("ate", ate);

    api
      .get(`/transactions?${params.toString()}`)
      .then((data) => ativo && setTransacoes(data))
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar o extrato."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, [conta, de, ate]);

  const total = useMemo(
    () => transacoes.reduce((soma, t) => soma + (t.tipo === "credit" ? t.valor : -Math.abs(t.valor)), 0),
    [transacoes]
  );

  return (
    <Modal aberto={!!conta} titulo={`Extrato — ${conta?.banco ?? ""}`} onFechar={onFechar} largo>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <select
          value={periodo}
          onChange={(e) => setPeriodo(e.target.value)}
          className="bg-surface-2 border border-border rounded-md px-2 py-1.5 text-sm outline-none"
        >
          {PERIODOS.map((p) => (
            <option key={p.valor} value={p.valor}>
              {p.label}
            </option>
          ))}
        </select>

        {periodo === "personalizado" && (
          <>
            <input
              type="date"
              value={de}
              onChange={(e) => setDe(e.target.value)}
              className="bg-surface-2 border border-border rounded-md px-2 py-1.5 text-sm outline-none"
            />
            <span className="text-text-muted text-sm">até</span>
            <input
              type="date"
              value={ate}
              onChange={(e) => setAte(e.target.value)}
              className="bg-surface-2 border border-border rounded-md px-2 py-1.5 text-sm outline-none"
            />
          </>
        )}

        <span className="ml-auto text-sm text-text-secondary">
          Total do período:{" "}
          <span className={total < 0 ? "text-danger" : "text-success"}>{formatCurrency(total)}</span>
        </span>

        {onImportar && (
          <button
            onClick={onImportar}
            className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1.5"
          >
            <Upload size={14} />
            Importar CSV/OFX
          </button>
        )}
      </div>

      {carregando && <div className="text-sm text-text-muted py-4">Carregando...</div>}
      {erro && <div className="text-sm text-danger py-4">{erro}</div>}

      {!carregando && !erro && (
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="max-h-[50vh] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface z-10">
                <tr className="text-text-secondary text-xs border-b border-border">
                  <th className="text-left font-normal px-3 py-2">Data</th>
                  <th className="text-left font-normal px-3 py-2">Descrição</th>
                  <th className="text-left font-normal px-3 py-2">Categoria</th>
                  <th className="text-right font-normal px-3 py-2">Valor</th>
                </tr>
              </thead>
              <tbody>
                {transacoes.map((t) => (
                  <tr key={t.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2 text-text-secondary whitespace-nowrap">
                      {formatDateShort(t.data)}
                    </td>
                    <td className="px-3 py-2">{t.descricao}</td>
                    <td className="px-3 py-2">
                      <span className="bg-surface-2 text-text-secondary text-xs px-2 py-0.5 rounded-full">
                        {t.categoria || "Sem categoria"}
                      </span>
                    </td>
                    <td
                      className={`px-3 py-2 text-right whitespace-nowrap ${
                        t.tipo === "credit" ? "text-success" : "text-danger"
                      }`}
                    >
                      {t.tipo === "credit" ? "+" : "-"}
                      {formatCurrency(Math.abs(t.valor))}
                    </td>
                  </tr>
                ))}
                {transacoes.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-3 py-6 text-center text-text-muted">
                      Nenhuma transação nesse período.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="px-3 py-2 text-xs text-text-muted border-t border-border">
            {transacoes.length} transação(ões)
          </div>
        </div>
      )}
    </Modal>
  );
}
