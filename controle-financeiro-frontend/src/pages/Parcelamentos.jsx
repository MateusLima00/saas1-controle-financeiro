import { useEffect, useState } from "react";
import { Plus, Trash2, CreditCard, CheckCircle2, Clock } from "lucide-react";
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";
import { useToast } from "../components/ToastProvider";
import { formatCurrency, formatDateShort } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Parcelamentos.jsx
//
// Compras parceladas no cartão: cadastra uma vez (valor total + número de
// parcelas) e o backend gera as parcelas mensais sozinho. Parcela com
// vencimento no passado/hoje já virou transação de verdade (conta no
// gasto do mês) — vencimento futuro é só um compromisso, aparece aqui mas
// não em nenhum saldo ainda. "Fatura do mês" agrega por cartão o que já
// fechou + o que ainda vai fechar esse mês. CRUD contra /parcelamentos.
// -----------------------------------------------------------------------
const FORM_VAZIO = { descricao: "", valorTotal: "", numParcelas: "2", contaId: "", categoriaId: "", dataPrimeiraParcela: "" };

function hojeIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function Parcelamentos() {
  const [compras, setCompras] = useState([]);
  const [faturas, setFaturas] = useState([]);
  const [contas, setContas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  const [paraExcluir, setParaExcluir] = useState(null);
  const { mostrarToast } = useToast();

  function carregarTudo() {
    return Promise.all([
      api.get("/parcelamentos"),
      api.get("/parcelamentos/fatura"),
      api.get("/accounts"),
      api.get("/categories"),
    ]).then(([comprasData, faturasData, contasData, categoriasData]) => {
      setCompras(comprasData);
      setFaturas(faturasData);
      setContas(contasData.filter((c) => c.tipo === "credit_card"));
      setCategorias(categoriasData);
    });
  }

  useEffect(() => {
    let ativo = true;
    carregarTudo()
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar os parcelamentos."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  function abrirCriar() {
    setForm({ ...FORM_VAZIO, dataPrimeiraParcela: hojeIso(), contaId: contas[0]?.id ?? "" });
    setModalAberto(true);
  }

  async function salvar(e) {
    e.preventDefault();
    if (!form.descricao || !form.valorTotal || !form.contaId || !form.dataPrimeiraParcela) return;

    try {
      await api.post("/parcelamentos", {
        descricao: form.descricao,
        valorTotal: Number(form.valorTotal),
        numParcelas: Number(form.numParcelas),
        contaId: Number(form.contaId),
        categoriaId: form.categoriaId ? Number(form.categoriaId) : null,
        dataPrimeiraParcela: form.dataPrimeiraParcela,
      });
      mostrarToast(`Compra "${form.descricao}" parcelada em ${form.numParcelas}x.`);
      setModalAberto(false);
      await carregarTudo();
    } catch (err) {
      mostrarToast(err.message || "Não foi possível cadastrar a compra parcelada.", "erro");
    }
  }

  async function confirmarExclusao() {
    const alvo = paraExcluir;
    setParaExcluir(null);
    try {
      await api.delete(`/parcelamentos/${alvo.id}`);
      mostrarToast(`Compra "${alvo.descricao}" removida.`);
      await carregarTudo();
    } catch (err) {
      mostrarToast(err.message || "Não foi possível excluir.", "erro");
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
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-lg font-medium">Cartão e parcelamentos</h1>
        <button
          onClick={abrirCriar}
          disabled={contas.length === 0}
          className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1 disabled:opacity-50"
        >
          <Plus size={14} />
          Nova compra parcelada
        </button>
      </div>

      {contas.length === 0 && (
        <div className="bg-surface rounded-card border border-border border-dashed p-4 mb-4 text-sm text-text-secondary">
          Nenhum cartão de crédito cadastrado ainda. Crie uma conta do tipo "Cartão de crédito" na
          tela Contas antes de lançar uma compra parcelada.
        </div>
      )}

      {/* Fatura do mês por cartão */}
      {faturas.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
          {faturas.map((f) => (
            <div key={f.contaId} className="bg-surface rounded-card border border-border p-4">
              <div className="flex items-center gap-2 text-sm font-medium mb-2">
                <CreditCard size={15} className="text-text-muted" />
                {f.conta}
              </div>
              <div className="text-xl font-medium mb-1">{formatCurrency(f.totalMes)}</div>
              <div className="text-xs text-text-muted">
                {formatCurrency(f.totalFechado)} já lançado
                {f.totalPendente > 0 ? ` + ${formatCurrency(f.totalPendente)} previsto` : ""} este mês
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal aberto={modalAberto} titulo="Nova compra parcelada" onFechar={() => setModalAberto(false)}>
        <form onSubmit={salvar} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Descrição (ex: Notebook)"
            value={form.descricao}
            onChange={(e) => setForm({ ...form, descricao: e.target.value })}
            className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
            required
          />
          <div className="flex gap-2">
            <input
              type="number"
              step="0.01"
              placeholder="Valor total (R$)"
              value={form.valorTotal}
              onChange={(e) => setForm({ ...form, valorTotal: e.target.value })}
              className="flex-1 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
              required
            />
            <input
              type="number"
              min="1"
              placeholder="Nº parcelas"
              value={form.numParcelas}
              onChange={(e) => setForm({ ...form, numParcelas: e.target.value })}
              className="w-28 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
              required
            />
          </div>
          <select
            value={form.contaId}
            onChange={(e) => setForm({ ...form, contaId: e.target.value })}
            className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1.5 text-sm outline-none"
            required
          >
            <option value="" disabled>Cartão</option>
            {contas.map((c) => (
              <option key={c.id} value={c.id}>{c.banco}</option>
            ))}
          </select>
          <select
            value={form.categoriaId}
            onChange={(e) => setForm({ ...form, categoriaId: e.target.value })}
            className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1.5 text-sm outline-none"
          >
            <option value="">Sem categoria</option>
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
          <div>
            <label className="text-xs text-text-muted block mb-1">Vencimento da 1ª parcela</label>
            <input
              type="date"
              value={form.dataPrimeiraParcela}
              onChange={(e) => setForm({ ...form, dataPrimeiraParcela: e.target.value })}
              className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
              required
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
        mensagem={`Tem certeza que quer excluir a compra "${paraExcluir?.descricao}"? Parcelas já lançadas como transação também serão removidas. Essa ação não pode ser desfeita.`}
        onConfirmar={confirmarExclusao}
        onCancelar={() => setParaExcluir(null)}
      />

      {compras.length === 0 ? (
        <div className="bg-surface rounded-card border border-border border-dashed p-8 flex flex-col items-center text-center gap-2">
          <CreditCard size={24} className="text-text-muted" />
          <p className="text-sm text-text-secondary">Nenhuma compra parcelada cadastrada ainda.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {compras.map((c) => {
            const pagas = c.parcelas.filter((p) => p.paga).length;
            return (
              <div key={c.id} className="bg-surface rounded-card border border-border p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-sm font-medium">{c.descricao}</div>
                    <div className="text-xs text-text-muted">
                      {c.conta} · {formatCurrency(c.valorTotal)} em {c.numParcelas}x
                      {c.categoria ? ` · ${c.categoria}` : ""} · {pagas}/{c.numParcelas} pagas
                    </div>
                  </div>
                  <button
                    onClick={() => setParaExcluir({ id: c.id, descricao: c.descricao })}
                    aria-label={`Remover ${c.descricao}`}
                    className="text-text-muted hover:text-danger"
                    title="Excluir compra parcelada"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {c.parcelas.map((p) => (
                    <span
                      key={p.id}
                      className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${
                        p.paga ? "bg-success/10 text-success" : "bg-surface-2 text-text-secondary"
                      }`}
                      title={p.paga ? "Já lançada" : "Vencimento futuro, ainda não conta no gasto"}
                    >
                      {p.paga ? <CheckCircle2 size={11} /> : <Clock size={11} />}
                      {p.numero}/{c.numParcelas} · {formatCurrency(p.valor)} · {formatDateShort(p.dataVencimento)}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
