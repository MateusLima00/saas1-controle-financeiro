import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Wallet2 } from "lucide-react";
import { SeletorIconeCor } from "../components/IconPicker";
import IconBadge from "../components/IconBadge";
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";
import { useToast } from "../components/ToastProvider";
import { formatCurrency } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Assinaturas.jsx
//
// Lista de assinaturas recorrentes (Netflix, Spotify, etc), com total
// mensal calculado automaticamente e um popup pra adicionar/editar.
// CRUD contra /subscriptions.
// -----------------------------------------------------------------------
const ASSINATURA_VAZIA = {
  nome: "",
  valor: "",
  ciclo: "Mensal",
  icone: "Clapperboard",
  cor: "var(--color-cat-3)",
  proximaCobranca: "",
  duracaoMeses: "",
  dataInicio: "",
};

export default function Assinaturas() {
  const [assinaturas, setAssinaturas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const [modo, setModo] = useState("criar"); // "criar" | "editar"
  const [editandoId, setEditandoId] = useState(null);
  const [form, setForm] = useState(ASSINATURA_VAZIA);
  const [paraExcluir, setParaExcluir] = useState(null);
  const { mostrarToast } = useToast();

  useEffect(() => {
    let ativo = true;
    api
      .get("/subscriptions?incluir_expiradas=true")
      .then((data) => ativo && setAssinaturas(data))
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar as assinaturas."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  const totalMensal = assinaturas
    .filter((a) => a.ciclo === "Mensal" && a.ativa !== false)
    .reduce((soma, a) => soma + a.valor, 0);

  function abrirCriar() {
    setModo("criar");
    setForm(ASSINATURA_VAZIA);
    setModalAberto(true);
  }

  function abrirEditar(a) {
    setModo("editar");
    setEditandoId(a.id);
    setForm({
      nome: a.nome,
      valor: String(a.valor),
      ciclo: a.ciclo,
      icone: a.icone,
      cor: a.cor,
      proximaCobranca: a.proximaCobranca || "",
      duracaoMeses: a.duracaoMeses ? String(a.duracaoMeses) : "",
      dataInicio: a.dataInicio || "",
    });
    setModalAberto(true);
  }

  async function salvar(e) {
    e.preventDefault();
    if (!form.nome || !form.valor) return;

    const payload = {
      ...form,
      valor: Number(form.valor),
      duracaoMeses: form.duracaoMeses ? Number(form.duracaoMeses) : null,
      dataInicio: form.duracaoMeses ? form.dataInicio || new Date().toISOString().slice(0, 10) : null,
    };

    try {
      if (modo === "criar") {
        const assinatura = await api.post("/subscriptions", payload);
        setAssinaturas((atual) => [...atual, assinatura]);
        mostrarToast(`Assinatura "${form.nome}" adicionada.`);
      } else {
        const assinatura = await api.put(`/subscriptions/${editandoId}`, payload);
        setAssinaturas((atual) => atual.map((a) => (a.id === editandoId ? assinatura : a)));
        mostrarToast(`Assinatura "${form.nome}" atualizada.`);
      }
      setModalAberto(false);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível salvar a assinatura.", "erro");
    }
  }

  async function confirmarExclusao() {
    const alvo = paraExcluir;
    setParaExcluir(null);
    try {
      await api.delete(`/subscriptions/${alvo.id}`);
      setAssinaturas((atual) => atual.filter((a) => a.id !== alvo.id));
      mostrarToast(`Assinatura "${alvo.nome}" removida.`);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível excluir a assinatura.", "erro");
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
        <h1 className="text-lg font-medium">Assinaturas</h1>
        <button
          onClick={abrirCriar}
          className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1"
        >
          <Plus size={14} />
          Nova assinatura
        </button>
      </div>
      <p className="text-sm text-text-secondary mb-4">
        Total mensal: <span className="text-danger">{formatCurrency(totalMensal)}</span>
      </p>

      <Modal
        aberto={modalAberto}
        titulo={modo === "criar" ? "Nova assinatura" : "Editar assinatura"}
        onFechar={() => setModalAberto(false)}
      >
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
              placeholder="Nome (ex: Disney+)"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
              required
            />
            <div className="flex gap-2">
              <select
                value={form.ciclo}
                onChange={(e) => setForm({ ...form, ciclo: e.target.value })}
                className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1.5 text-sm outline-none"
              >
                <option value="Mensal">Mensal</option>
                <option value="Anual">Anual</option>
              </select>
              <input
                type="number"
                placeholder="Valor (R$)"
                value={form.valor}
                onChange={(e) => setForm({ ...form, valor: e.target.value })}
                className="w-32 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
                required
              />
              <input
                type="text"
                placeholder="Próxima cobrança (ex: 10/08)"
                value={form.proximaCobranca}
                onChange={(e) => setForm({ ...form, proximaCobranca: e.target.value })}
                className="flex-1 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
              />
            </div>

            <div className="flex flex-col gap-1.5 pt-1">
              <label className="text-xs text-text-muted">
                Contrato por prazo fixo (opcional — ex: academia 12x, plano 24x)
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="1"
                  placeholder="Duração (meses)"
                  value={form.duracaoMeses}
                  onChange={(e) => setForm({ ...form, duracaoMeses: e.target.value })}
                  className="w-36 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
                />
                {form.duracaoMeses && (
                  <input
                    type="date"
                    value={form.dataInicio}
                    onChange={(e) => setForm({ ...form, dataInicio: e.target.value })}
                    className="flex-1 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
                  />
                )}
              </div>
              <p className="text-[11px] text-text-muted">
                {form.duracaoMeses
                  ? "Deixe a data em branco pra começar hoje. Depois do prazo, some sozinha dos lembretes."
                  : "Vazio = assinatura mensal sem fim, como hoje."}
              </p>
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
        mensagem={`Tem certeza que quer excluir a assinatura "${paraExcluir?.nome}"? Essa ação não pode ser desfeita.`}
        onConfirmar={confirmarExclusao}
        onCancelar={() => setParaExcluir(null)}
      />

      {assinaturas.length === 0 ? (
        <div className="bg-surface rounded-card border border-border border-dashed p-8 flex flex-col items-center text-center gap-2">
          <Wallet2 size={24} className="text-text-muted" />
          <p className="text-sm text-text-secondary">Nenhuma assinatura cadastrada ainda.</p>
          <button onClick={abrirCriar} className="text-xs text-accent mt-1">
            Cadastrar a primeira
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {assinaturas.map((a) => (
            <div
              key={a.id}
              className={`bg-surface rounded-card border border-border p-4 flex items-center justify-between ${a.ativa === false ? "opacity-60" : ""}`}
            >
              <div className="flex items-center gap-3">
                <IconBadge nome={a.icone} cor={a.cor} />
                <div>
                  <div className="text-sm font-medium flex items-center gap-2">
                    {a.nome}
                    {a.ativa === false && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-2 text-text-muted">
                        Contrato encerrado
                      </span>
                    )}
                    {a.ativa !== false && a.duracaoMeses && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-2 text-text-secondary">
                        {a.duracaoMeses}x · até {a.dataFim}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-text-muted">
                    {a.ciclo} · próxima cobrança {a.proximaCobranca || "—"}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm">{formatCurrency(a.valor)}</span>
                <button onClick={() => abrirEditar(a)} aria-label={`Editar ${a.nome}`} className="text-text-muted hover:text-text-primary">
                  <Pencil size={15} />
                </button>
                <button
                  onClick={() => setParaExcluir({ id: a.id, nome: a.nome })}
                  aria-label={`Remover ${a.nome}`}
                  className="text-text-muted hover:text-danger"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
