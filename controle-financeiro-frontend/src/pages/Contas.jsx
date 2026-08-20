import { useEffect, useRef, useState } from "react";
import { Plus, Trash2, Landmark, RefreshCw, Upload } from "lucide-react";
import { PluggyConnect } from "react-pluggy-connect";
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";
import { useToast } from "../components/ToastProvider";
import { formatCurrency } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Contas.jsx
//
// Status de cada conta conectada via Pluggy + possibilidade de adicionar
// uma conta manual (fallback de CSV/OFX, ou algo que a Pluggy não cobre).
// "Conectar novo banco" abre o Pluggy Connect Widget (OAuth de verdade
// com o banco, o backend não consegue automatizar esse login). Ao
// terminar, o itemId retornado é mandado pro backend em /accounts/sync
// pra buscar contas/transações. Contas manuais podem ser removidas (as
// via Pluggy se desconectam por lá). CRUD contra /accounts.
// -----------------------------------------------------------------------

const statusInfo = {
  connected: { texto: "Conectado", cor: "text-success", bg: "bg-success/10" },
  error: { texto: "Erro na sincronização", cor: "text-danger", bg: "bg-danger/10" },
  pending: { texto: "Sincronizando...", cor: "text-text-secondary", bg: "bg-surface-2" },
  manual: { texto: "Manual", cor: "text-text-secondary", bg: "bg-surface-2" },
};

export default function Contas() {
  const [contas, setContas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const [nova, setNova] = useState({ banco: "", tipo: "checking", saldo: "" });
  const [paraExcluir, setParaExcluir] = useState(null);
  const [sincronizando, setSincronizando] = useState(false);
  const [importandoId, setImportandoId] = useState(null);
  const [connectToken, setConnectToken] = useState(null);
  const [carregandoToken, setCarregandoToken] = useState(false);
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

  // O sync automático de 20 em 20 min roda no BACKEND (app/scheduler.py,
  // job pluggy_frequent_sync) — não depende de ninguém com essa tela
  // aberta (uso principal é via bot do Telegram/Nero). Aqui no frontend
  // só recarregamos a lista quando a aba volta a ficar visível, pra
  // mostrar dado fresco sem esperar o próximo `GET /accounts` manual.
  useEffect(() => {
    function aoVoltarVisivel() {
      if (document.visibilityState === "visible") {
        api.get("/accounts").then(setContas).catch(() => {});
      }
    }
    document.addEventListener("visibilitychange", aoVoltarVisivel);
    return () => document.removeEventListener("visibilitychange", aoVoltarVisivel);
  }, []);

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

  async function sincronizarAgora(itemId) {
    setSincronizando(true);
    try {
      await api.post("/accounts/sync", itemId ? { itemId } : undefined);
      const atualizadas = await api.get("/accounts");
      setContas(atualizadas);
      mostrarToast("Contas sincronizadas.");
    } catch (err) {
      mostrarToast(err.message || "Não foi possível sincronizar agora.", "erro");
    } finally {
      setSincronizando(false);
    }
  }

  async function abrirConectarBanco() {
    setCarregandoToken(true);
    try {
      const { connectToken: token } = await api.post("/accounts/connect-token");
      setConnectToken(token);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível iniciar a conexão com o banco.", "erro");
    } finally {
      setCarregandoToken(false);
    }
  }

  function aoConectarComSucesso(itemData) {
    setConnectToken(null);
    mostrarToast("Banco conectado, sincronizando...");
    sincronizarAgora(itemData?.item?.id);
  }

  function aoErrarConexao(error) {
    setConnectToken(null);
    mostrarToast(error?.message || "Não foi possível conectar o banco.", "erro");
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
        accept=".csv,.ofx,.qfx"
        className="hidden"
        onChange={importarArquivo}
      />

      <div className="flex justify-between items-center mb-4">
        <h1 className="text-lg font-medium">Contas conectadas</h1>
        <div className="flex gap-2">
          <button
            onClick={() => sincronizarAgora()}
            disabled={sincronizando}
            className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1 disabled:opacity-50"
          >
            <RefreshCw size={14} className={sincronizando ? "animate-spin" : ""} />
            {sincronizando ? "Sincronizando..." : "Atualizar agora"}
          </button>
          <button
            onClick={() => setModalAberto(true)}
            className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1"
          >
            <Plus size={14} />
            Conta manual
          </button>
          <button
            onClick={abrirConectarBanco}
            disabled={carregandoToken}
            className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors disabled:opacity-50"
          >
            {carregandoToken ? "Abrindo..." : "Conectar novo banco"}
          </button>
        </div>
      </div>

      {connectToken && (
        <PluggyConnect
          connectToken={connectToken}
          includeSandbox={false}
          onSuccess={aoConectarComSucesso}
          onError={aoErrarConexao}
          onClose={() => setConnectToken(null)}
        />
      )}

      <Modal aberto={modalAberto} titulo="Nova conta manual" onFechar={() => setModalAberto(false)}>
        <form onSubmit={adicionarContaManual} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Nome (ex: Dinheiro em espécie)"
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

      {contas.length === 0 ? (
        <div className="bg-surface rounded-card border border-border border-dashed p-8 flex flex-col items-center text-center gap-2">
          <Landmark size={24} className="text-text-muted" />
          <p className="text-sm text-text-secondary">Nenhuma conta cadastrada ainda.</p>
          <button onClick={() => setModalAberto(true)} className="text-xs text-accent mt-1">
            Adicionar uma conta manual
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {contas.map((conta) => {
            const status = statusInfo[conta.status];
            return (
              <div key={conta.id} className="bg-surface rounded-card border border-border p-4 flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">{conta.banco}</div>
                  <div className="text-xs text-text-muted">
                    {conta.tipo === "credit_card" ? "Cartão de crédito" : "Conta"}
                    {conta.origem === "manual" ? " · adicionada manualmente" : ` · última sync ${conta.ultimaSync}`}
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
                    onClick={() => abrirSeletorImportacao(conta.id)}
                    disabled={importandoId === conta.id}
                    aria-label={`Importar extrato para ${conta.banco}`}
                    className="text-text-muted hover:text-accent disabled:opacity-50"
                    title="Importar extrato (CSV/OFX)"
                  >
                    <Upload size={15} />
                  </button>
                  {conta.origem === "manual" && (
                    <button
                      onClick={() => setParaExcluir({ id: conta.id, banco: conta.banco })}
                      aria-label={`Remover ${conta.banco}`}
                      className="text-text-muted hover:text-danger"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
