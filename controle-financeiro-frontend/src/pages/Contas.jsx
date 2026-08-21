import { useEffect, useRef, useState } from "react";
import { Plus, Trash2, Landmark, RefreshCw, Upload } from "lucide-react";
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";
import ExtratoContaModal from "../components/ExtratoContaModal";
import { useToast } from "../components/ToastProvider";
import { formatCurrency } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Contas.jsx
//
// Contas são sempre cadastradas manualmente. Transações entram por
// lançamento manual, pelo bot do Telegram, ou por importação de extrato
// (CSV/OFX/QFX) — não há mais sincronização automática com banco. CRUD
// contra /accounts.
// -----------------------------------------------------------------------

const statusInfo = {
  connected: { texto: "Ativa", cor: "text-success", bg: "bg-success/10" },
  error: { texto: "Erro", cor: "text-danger", bg: "bg-danger/10" },
  manual: { texto: "Manual", cor: "text-text-secondary", bg: "bg-surface-2" },
};

export default function Contas() {
  const [contas, setContas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const [nova, setNova] = useState({ banco: "", tipo: "checking", saldo: "" });
  const [paraExcluir, setParaExcluir] = useState(null);
  const [contaExtrato, setContaExtrato] = useState(null);
  const [atualizando, setAtualizando] = useState(false);
  const [importandoId, setImportandoId] = useState(null);
  const inputArquivoRef = useRef(null);
  const contaParaImportarRef = useRef(null);
  const { mostrarToast } = useToast();

  useEffect(() => {
    let ativo = true;
    api
      .get("/accounts")
      .then((data) => ativo && setContas(data))
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar as contas."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  async function recarregar() {
    setAtualizando(true);
    try {
      const atualizadas = await api.get("/accounts");
      setContas(atualizadas);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível atualizar a lista.", "erro");
    } finally {
      setAtualizando(false);
    }
  }

  async function adicionarContaManual(e) {
    e.preventDefault();
    if (!nova.banco) return;

    try {
      const conta = await api.post("/accounts", {
        banco: nova.banco,
        tipo: nova.tipo,
        saldo: Number(nova.saldo) || 0,
        status: "manual",
        ultimaSync: "manual",
        origem: "manual",
      });
      setContas((atual) => [...atual, conta]);
      mostrarToast(`Conta "${nova.banco}" adicionada.`);
      setNova({ banco: "", tipo: "checking", saldo: "" });
      setModalAberto(false);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível adicionar a conta.", "erro");
    }
  }

  function abrirSeletorImportacao(contaId) {
    contaParaImportarRef.current = contaId;
    inputArquivoRef.current?.click();
  }

  async function importarArquivo(e) {
    const arquivo = e.target.files?.[0];
    const contaId = contaParaImportarRef.current;
    e.target.value = "";
    if (!arquivo || !contaId) return;

    setImportandoId(contaId);
    try {
      const resultado = await api.upload(`/accounts/${contaId}/import`, arquivo);
      mostrarToast(
        `${resultado.importadas} lançamento(s) importado(s)` +
          (resultado.duplicadas ? `, ${resultado.duplicadas} já existiam` : "") +
          "."
      );
      const atualizadas = await api.get("/accounts");
      setContas(atualizadas);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível importar o arquivo.", "erro");
    } finally {
      setImportandoId(null);
    }
  }

  async function confirmarExclusao() {
    const alvo = paraExcluir;
    setParaExcluir(null);
    try {
      await api.delete(`/accounts/${alvo.id}`);
      setContas((atual) => atual.filter((c) => c.id !== alvo.id));
      mostrarToast(`Conta "${alvo.banco}" removida.`);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível excluir a conta.", "erro");
    }
  }

  if (carregando) {
    return <div className="p-6 text-sm text-text-muted">Carregando...</div>;
  }

  if (erro) {
    return <div className="p-6 text-sm text-danger">{erro}</div>;
  }

  return (
    <div className="p-6">
      <input
        ref={inputArquivoRef}
        type="file"
        accept=".csv,.ofx,.qfx,.pdf"
        className="hidden"
        onChange={importarArquivo}
      />

      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4">
        <h1 className="text-lg font-medium">Contas</h1>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={recarregar}
            disabled={atualizando}
            className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1 disabled:opacity-50"
          >
            <RefreshCw size={14} className={atualizando ? "animate-spin" : ""} />
            {atualizando ? "Atualizando..." : "Atualizar lista"}
          </button>
          <button
            onClick={() => setModalAberto(true)}
            className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1"
          >
            <Plus size={14} />
            Nova conta
          </button>
        </div>
      </div>

      <Modal aberto={modalAberto} titulo="Nova conta" onFechar={() => setModalAberto(false)}>
        <form onSubmit={adicionarContaManual} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Nome (ex: Nubank, Dinheiro em espécie)"
            value={nova.banco}
            onChange={(e) => setNova({ ...nova, banco: e.target.value })}
            className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
            required
          />
          <div className="flex gap-2">
            <select
              value={nova.tipo}
              onChange={(e) => setNova({ ...nova, tipo: e.target.value })}
              className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1.5 text-sm outline-none"
            >
              <option value="checking">Conta corrente</option>
              <option value="savings">Poupança</option>
              <option value="credit_card">Cartão de crédito</option>
            </select>
            <input
              type="number"
              placeholder="Saldo atual (R$)"
              value={nova.saldo}
              onChange={(e) => setNova({ ...nova, saldo: e.target.value })}
              className="flex-1 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setModalAberto(false)}
              className="text-sm px-4 py-1.5 rounded-[var(--radius-control)] text-text-secondary hover:bg-surface-2 transition-colors"
            >
              Cancelar
            </button>
            <button type="submit" className="bg-accent text-white rounded-[var(--radius-control)] px-4 py-1.5 text-sm">
              Adicionar
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        aberto={!!paraExcluir}
        mensagem={`Tem certeza que quer excluir a conta "${paraExcluir?.banco}"? Essa ação não pode ser desfeita.`}
        onConfirmar={confirmarExclusao}
        onCancelar={() => setParaExcluir(null)}
      />

      <ExtratoContaModal
        conta={contaExtrato}
        onFechar={() => setContaExtrato(null)}
        onImportar={() => {
          const contaId = contaExtrato.id;
          setContaExtrato(null);
          abrirSeletorImportacao(contaId);
        }}
      />

      {contas.length === 0 ? (
        <div className="bg-surface rounded-card border border-border border-dashed p-8 flex flex-col items-center text-center gap-2">
          <Landmark size={24} className="text-text-muted" />
          <p className="text-sm text-text-secondary">Nenhuma conta cadastrada ainda.</p>
          <button onClick={() => setModalAberto(true)} className="text-xs text-accent mt-1">
            Adicionar uma conta
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {contas.map((conta) => {
            const status = statusInfo[conta.status] || statusInfo.manual;
            return (
              <div key={conta.id} className="bg-surface rounded-card border border-border p-4 flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">{conta.banco}</div>
                  <div className="text-xs text-text-muted">
                    {conta.tipo === "credit_card" ? "Cartão de crédito" : "Conta"}
                    {conta.ultimaSync && conta.ultimaSync !== "manual" ? ` · último extrato ${conta.ultimaSync}` : ""}
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <span className={conta.saldo < 0 ? "text-danger text-sm" : "text-text-primary text-sm"}>
                    {formatCurrency(conta.saldo)}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded-full ${status.bg} ${status.cor}`}>
                    {status.texto}
                  </span>
                  <button
                    onClick={() => setContaExtrato(conta)}
                    disabled={importandoId === conta.id}
                    aria-label={`Ver extrato de ${conta.banco}`}
                    className="text-text-muted hover:text-accent disabled:opacity-50"
                    title="Ver extrato / importar"
                  >
                    <Upload size={15} />
                  </button>
                  <button
                    onClick={() => setParaExcluir({ id: conta.id, banco: conta.banco })}
                    aria-label={`Remover ${conta.banco}`}
                    className="text-text-muted hover:text-danger"
                    title="Excluir conta"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
