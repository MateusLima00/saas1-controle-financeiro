import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, TrendingUp } from "lucide-react";
import { SeletorIconeCor } from "../components/IconPicker";
import IconBadge from "../components/IconBadge";
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";
import { useToast } from "../components/ToastProvider";
import { formatCurrency, calcularVariacaoPercentual } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Investimentos.jsx
//
// Lista de investimentos com valor investido x valor atual, calculando
// o rendimento (%) automaticamente. Botão "Aportar" soma no valor
// investido E no valor atual (aporte novo, sem rendimento ainda), via
// PUT /investments/:id. Cada item pode ser editado ou excluído.
// -----------------------------------------------------------------------
const INVESTIMENTO_VAZIO = { nome: "", tipo: "Renda fixa", icone: "TrendingUp", cor: "var(--color-cat-5)", valorInvestido: "" };

export default function Investimentos() {
  const [investimentos, setInvestimentos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const [modo, setModo] = useState("criar"); // "criar" | "editar"
  const [editandoId, setEditandoId] = useState(null);
  const [form, setForm] = useState(INVESTIMENTO_VAZIO);
  const [paraExcluir, setParaExcluir] = useState(null);
  const [aporteAbertoId, setAporteAbertoId] = useState(null);
  const [valorAporte, setValorAporte] = useState("");
  const { mostrarToast } = useToast();

  useEffect(() => {
    let ativo = true;
    api
      .get("/investments")
      .then((data) => ativo && setInvestimentos(data))
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar os investimentos."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  const totalInvestido = investimentos.reduce((soma, i) => soma + i.valorInvestido, 0);
  const totalAtual = investimentos.reduce((soma, i) => soma + i.valorAtual, 0);
  const rendimentoTotal = calcularVariacaoPercentual(totalAtual, totalInvestido);

  function abrirCriar() {
    setModo("criar");
    setForm(INVESTIMENTO_VAZIO);
    setModalAberto(true);
  }

  function abrirEditar(inv) {
    setModo("editar");
    setEditandoId(inv.id);
    setForm({ nome: inv.nome, tipo: inv.tipo, icone: inv.icone, cor: inv.cor, valorInvestido: String(inv.valorInvestido) });
    setModalAberto(true);
  }

  async function salvar(e) {
    e.preventDefault();
    if (!form.nome || !form.valorInvestido) return;

    try {
      if (modo === "criar") {
        const investimento = await api.post("/investments", {
          nome: form.nome,
          tipo: form.tipo,
          icone: form.icone,
          cor: form.cor,
          valorInvestido: Number(form.valorInvestido),
          valorAtual: Number(form.valorInvestido),
        });
        setInvestimentos((atual) => [...atual, investimento]);
        mostrarToast(`Investimento "${form.nome}" adicionado.`);
      } else {
        const investimento = await api.put(`/investments/${editandoId}`, {
          nome: form.nome,
          tipo: form.tipo,
          icone: form.icone,
          cor: form.cor,
          valorInvestido: Number(form.valorInvestido),
        });
        setInvestimentos((atual) => atual.map((i) => (i.id === editandoId ? investimento : i)));
        mostrarToast(`Investimento "${form.nome}" atualizado.`);
      }
      setModalAberto(false);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível salvar o investimento.");
    }
  }

  async function confirmarExclusao() {
    const alvo = paraExcluir;
    setParaExcluir(null);
    try {
      await api.delete(`/investments/${alvo.id}`);
      setInvestimentos((atual) => atual.filter((i) => i.id !== alvo.id));
      mostrarToast(`Investimento "${alvo.nome}" removido.`);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível excluir o investimento.");
    }
  }

  async function registrarAporte(inv) {
    const valor = Number(valorAporte);
    if (!valor || valor <= 0) return;

    try {
      const investimento = await api.put(`/investments/${inv.id}`, {
        valorInvestido: inv.valorInvestido + valor,
        valorAtual: inv.valorAtual + valor,
      });
      setInvestimentos((atual) => atual.map((i) => (i.id === inv.id ? investimento : i)));
      mostrarToast(`Aporte de ${formatCurrency(valor)} registrado.`);
      setValorAporte("");
      setAporteAbertoId(null);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível registrar o aporte.");
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
      <div className="flex justify-between items-center mb-1">
        <h1 className="text-lg font-medium">Investimentos</h1>
        <button
          onClick={abrirCriar}
          className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1"
        >
          <Plus size={14} />
          Novo investimento
        </button>
      </div>
      <p className="text-sm text-text-secondary mb-4">
        Total investido {formatCurrency(totalInvestido)} · hoje vale {formatCurrency(totalAtual)}{" "}
        <span className={rendimentoTotal >= 0 ? "text-success" : "text-danger"}>
          ({rendimentoTotal >= 0 ? "+" : ""}
          {rendimentoTotal}%)
        </span>
      </p>

      <Modal aberto={modalAberto} titulo={modo === "criar" ? "Novo investimento" : "Editar investimento"} onFechar={() => setModalAberto(false)}>
        <form onSubmit={salvar} className="flex flex-col gap-4">
          <SeletorIconeCor
            icone={form.icone}
            cor={form.cor}
            onChangeIcone={(v) => setForm({ ...form, icone: v })}
            onChangeCor={(v) => setForm({ ...form, cor: v })}
          />

          <div className="flex flex-col gap-2">
            <input
              type="text"
              placeholder="Nome (ex: Tesouro IPCA+)"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
              required
            />
            <div className="flex gap-2">
              <select
                value={form.tipo}
                onChange={(e) => setForm({ ...form, tipo: e.target.value })}
                className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1.5 text-sm outline-none"
              >
                <option value="Renda fixa">Renda fixa</option>
                <option value="Renda variável">Renda variável</option>
                <option value="Fundo imobiliário">Fundo imobiliário</option>
                <option value="Criptomoeda">Criptomoeda</option>
              </select>
              <input
                type="number"
                placeholder="Valor investido (R$)"
                value={form.valorInvestido}
                onChange={(e) => setForm({ ...form, valorInvestido: e.target.value })}
                className="flex-1 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
                required
              />
            </div>
          </div>

          <div className="flex justify-between items-center gap-2 pt-1">
            {modo === "editar" ? (
              <button
                type="button"
                onClick={() => {
                  setParaExcluir({ id: editandoId, nome: form.nome });
                  setModalAberto(false);
                }}
                className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] text-danger hover:bg-danger/10 transition-colors flex items-center gap-1"
              >
                <Trash2 size={14} />
                Excluir
              </button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setModalAberto(false)}
                className="text-sm px-4 py-1.5 rounded-[var(--radius-control)] text-text-secondary hover:bg-surface-2 transition-colors"
              >
                Cancelar
              </button>
              <button type="submit" className="bg-accent text-white rounded-[var(--radius-control)] px-4 py-1.5 text-sm">
                {modo === "criar" ? "Adicionar" : "Salvar alterações"}
              </button>
            </div>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        aberto={!!paraExcluir}
        mensagem={`Tem certeza que quer excluir o investimento "${paraExcluir?.nome}"? Essa ação não pode ser desfeita.`}
        onConfirmar={confirmarExclusao}
        onCancelar={() => setParaExcluir(null)}
      />

      {investimentos.length === 0 ? (
        <div className="bg-surface rounded-card border border-border border-dashed p-8 flex flex-col items-center text-center gap-2">
          <TrendingUp size={24} className="text-text-muted" />
          <p className="text-sm text-text-secondary">Nenhum investimento cadastrado ainda.</p>
          <button onClick={abrirCriar} className="text-xs text-accent mt-1">
            Cadastrar o primeiro
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {investimentos.map((inv) => {
            const rendimento = calcularVariacaoPercentual(inv.valorAtual, inv.valorInvestido);
            return (
              <div key={inv.id} className="bg-surface rounded-card border border-border p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <IconBadge nome={inv.icone} cor={inv.cor} />
                    <div>
                      <div className="text-sm font-medium">{inv.nome}</div>
                      <div className="text-xs text-text-muted">{inv.tipo}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-sm font-medium">{formatCurrency(inv.valorAtual)}</div>
                      <div className={`text-xs ${rendimento >= 0 ? "text-success" : "text-danger"}`}>
                        {rendimento >= 0 ? "+" : ""}
                        {rendimento}%
                      </div>
                    </div>
                    <button onClick={() => abrirEditar(inv)} aria-label={`Editar ${inv.nome}`} className="text-text-muted hover:text-text-primary">
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => setParaExcluir({ id: inv.id, nome: inv.nome })}
                      aria-label={`Excluir ${inv.nome}`}
                      className="text-text-muted hover:text-danger"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {aporteAbertoId === inv.id ? (
                  <div className="flex gap-2 mt-3">
                    <input
                      type="number"
                      autoFocus
                      placeholder="Valor do aporte"
                      value={valorAporte}
                      onChange={(e) => setValorAporte(e.target.value)}
                      className="flex-1 bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1 text-sm outline-none"
                    />
                    <button
                      onClick={() => registrarAporte(inv)}
                      className="bg-accent text-white text-xs px-3 rounded-[var(--radius-control)]"
                    >
                      Salvar
                    </button>
                    <button onClick={() => setAporteAbertoId(null)} className="text-xs text-text-muted px-2">
                      Cancelar
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setAporteAbertoId(inv.id)}
                    className="text-xs text-accent mt-3 flex items-center gap-1"
                  >
                    <Plus size={12} /> Aportar
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
