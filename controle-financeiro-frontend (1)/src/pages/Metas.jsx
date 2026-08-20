import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Target } from "lucide-react";
import BarraProgresso from "../components/BarraProgresso";
import { SeletorIconeCor } from "../components/IconPicker";
import IconBadge from "../components/IconBadge";
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";
import { useToast } from "../components/ToastProvider";
import { formatCurrency } from "../utils/format";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Metas.jsx
//
// Junta poupança e planos de viagem numa lista só (o campo "tipo" só
// muda o selinho mostrado). Cada meta tem:
//  - botão "+" pra registrar um novo aporte (POST /goals/:id/contributions)
//  - popup pra criar/editar uma meta (POST/PUT /goals), e excluir com
//    confirmação (DELETE /goals/:id)
// -----------------------------------------------------------------------
const META_VAZIA = { nome: "", tipo: "poupanca", icone: "PiggyBank", cor: "var(--color-cat-1)", valorAlvo: "", prazo: "" };

export default function Metas() {
  const [metas, setMetas] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const [modo, setModo] = useState("criar"); // "criar" | "editar"
  const [editandoId, setEditandoId] = useState(null);
  const [form, setForm] = useState(META_VAZIA);
  const [paraExcluir, setParaExcluir] = useState(null);
  const [aporteAbertoId, setAporteAbertoId] = useState(null);
  const [valorAporte, setValorAporte] = useState("");
  const { mostrarToast } = useToast();

  useEffect(() => {
    let ativo = true;
    api
      .get("/goals")
      .then((data) => ativo && setMetas(data))
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar as metas."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  function abrirCriar() {
    setModo("criar");
    setForm(META_VAZIA);
    setModalAberto(true);
  }

  function abrirEditar(meta) {
    setModo("editar");
    setEditandoId(meta.id);
    setForm({ nome: meta.nome, tipo: meta.tipo, icone: meta.icone, cor: meta.cor, valorAlvo: String(meta.valorAlvo), prazo: meta.prazo || "" });
    setModalAberto(true);
  }

  async function salvar(e) {
    e.preventDefault();
    if (!form.nome || !form.valorAlvo) return;

    try {
      if (modo === "criar") {
        const meta = await api.post("/goals", {
          nome: form.nome,
          tipo: form.tipo,
          icone: form.icone,
          cor: form.cor,
          valorAlvo: Number(form.valorAlvo),
          valorAtual: 0,
          prazo: form.prazo || null,
        });
        setMetas((atual) => [...atual, meta]);
        mostrarToast(`Meta "${form.nome}" criada.`);
      } else {
        const meta = await api.put(`/goals/${editandoId}`, {
          nome: form.nome,
          tipo: form.tipo,
          icone: form.icone,
          cor: form.cor,
          valorAlvo: Number(form.valorAlvo),
          prazo: form.prazo || null,
        });
        setMetas((atual) => atual.map((m) => (m.id === editandoId ? meta : m)));
        mostrarToast(`Meta "${form.nome}" atualizada.`);
      }
      setModalAberto(false);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível salvar a meta.");
    }
  }

  async function confirmarExclusao() {
    const alvo = paraExcluir;
    setParaExcluir(null);
    try {
      await api.delete(`/goals/${alvo.id}`);
      setMetas((atual) => atual.filter((m) => m.id !== alvo.id));
      mostrarToast(`Meta "${alvo.nome}" removida.`);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível excluir a meta.");
    }
  }

  async function registrarAporte(id) {
    const valor = Number(valorAporte);
    if (!valor || valor <= 0) return;

    try {
      const meta = await api.post(`/goals/${id}/contributions`, {
        data: new Date().toISOString().slice(0, 10),
        valor,
      });
      setMetas((atual) => atual.map((m) => (m.id === id ? meta : m)));
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
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-lg font-medium">Metas e planos</h1>
        <button
          onClick={abrirCriar}
          className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1"
        >
          <Plus size={14} />
          Nova meta
        </button>
      </div>

      {/* Popup de nova/editar meta */}
      <Modal aberto={modalAberto} titulo={modo === "criar" ? "Nova meta" : "Editar meta"} onFechar={() => setModalAberto(false)}>
        <form onSubmit={salvar} className="flex flex-col gap-4">
          <SeletorIconeCor
            icone={form.icone}
            cor={form.cor}
            onChangeIcone={(nome) => setForm({ ...form, icone: nome })}
            onChangeCor={(cor) => setForm({ ...form, cor })}
          />

          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Nome da meta (ex: Viagem pro Chile)"
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                className="flex-1 bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
                required
              />
              <select
                value={form.tipo}
                onChange={(e) => setForm({ ...form, tipo: e.target.value })}
                className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1.5 text-sm outline-none"
              >
                <option value="poupanca">Poupança</option>
                <option value="viagem">Viagem</option>
              </select>
            </div>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="Valor alvo (R$)"
                value={form.valorAlvo}
                onChange={(e) => setForm({ ...form, valorAlvo: e.target.value })}
                className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none w-40"
                required
              />
              <input
                type="text"
                placeholder="Prazo (opcional, ex: Dez/2026)"
                value={form.prazo}
                onChange={(e) => setForm({ ...form, prazo: e.target.value })}
                className="bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none flex-1"
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
                {modo === "criar" ? "Criar meta" : "Salvar alterações"}
              </button>
            </div>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        aberto={!!paraExcluir}
        mensagem={`Tem certeza que quer excluir a meta "${paraExcluir?.nome}"? Essa ação não pode ser desfeita.`}
        onConfirmar={confirmarExclusao}
        onCancelar={() => setParaExcluir(null)}
      />

      {metas.length === 0 ? (
        <div className="bg-surface rounded-card border border-border border-dashed p-8 flex flex-col items-center text-center gap-2">
          <Target size={24} className="text-text-muted" />
          <p className="text-sm text-text-secondary">Nenhuma meta cadastrada ainda.</p>
          <button onClick={abrirCriar} className="text-xs text-accent mt-1">
            Criar a primeira meta
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {metas.map((meta) => (
            <div key={meta.id} className="bg-surface rounded-card border border-border p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <IconBadge nome={meta.icone} cor={meta.cor} />
                  <div>
                    <div className="text-sm font-medium">{meta.nome}</div>
                    <div className="text-xs text-text-muted">
                      {meta.tipo === "viagem" ? "Viagem" : "Poupança"}
                      {meta.prazo ? ` · até ${meta.prazo}` : ""}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => abrirEditar(meta)} aria-label={`Editar ${meta.nome}`} className="text-text-muted hover:text-text-primary">
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => setParaExcluir({ id: meta.id, nome: meta.nome })}
                    aria-label={`Excluir ${meta.nome}`}
                    className="text-text-muted hover:text-danger"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <BarraProgresso atual={meta.valorAtual} alvo={meta.valorAlvo} cor={meta.cor} />

              {/* Input de aporte inline - abre só quando clica em "+ Adicionar valor" */}
              {aporteAbertoId === meta.id ? (
                <div className="flex gap-2 mt-3">
                  <input
                    type="number"
                    autoFocus
                    placeholder="Valor"
                    value={valorAporte}
                    onChange={(e) => setValorAporte(e.target.value)}
                    className="flex-1 bg-surface-2 border border-border rounded-[var(--radius-control)] px-2 py-1 text-sm outline-none"
                  />
                  <button
                    onClick={() => registrarAporte(meta.id)}
                    className="bg-accent text-white text-xs px-3 rounded-[var(--radius-control)]"
                  >
                    Salvar
                  </button>
                  <button
                    onClick={() => setAporteAbertoId(null)}
                    className="text-xs text-text-muted px-2"
                  >
                    Cancelar
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setAporteAbertoId(meta.id)}
                  className="text-xs text-accent mt-3 flex items-center gap-1"
                >
                  <Plus size={12} /> Adicionar valor
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
