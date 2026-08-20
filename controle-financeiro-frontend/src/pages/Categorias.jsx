import { useEffect, useState } from "react";
import { Plus, Check, Trash2, Tags } from "lucide-react";
import { CORES_DISPONIVEIS } from "../components/IconPicker";
import Modal from "../components/Modal";
import ConfirmDialog from "../components/ConfirmDialog";
import { useToast } from "../components/ToastProvider";
import { api } from "../api/client";

// -----------------------------------------------------------------------
// Categorias.jsx
//
// Tela de gerenciamento de categorias e das regras de categorização
// automática (ex: "contém 'uber' -> Transporte"). Um único popup é
// reaproveitado tanto pra criar uma categoria nova quanto pra editar
// uma já existente — "modo" controla qual dos dois é. CRUD contra
// /categories.
// -----------------------------------------------------------------------
const CATEGORIA_VAZIA = { nome: "", cor: CORES_DISPONIVEIS[0].valor, regra: "" };

export default function Categorias() {
  const [categorias, setCategorias] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [modalAberto, setModalAberto] = useState(false);
  const [modo, setModo] = useState("criar"); // "criar" | "editar"
  const [editandoId, setEditandoId] = useState(null);
  const [form, setForm] = useState(CATEGORIA_VAZIA);
  const [paraExcluir, setParaExcluir] = useState(null);
  const { mostrarToast } = useToast();

  useEffect(() => {
    let ativo = true;
    api
      .get("/categories")
      .then((data) => ativo && setCategorias(data))
      .catch((err) => ativo && setErro(err.message || "Não foi possível carregar as categorias."))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  function abrirCriar() {
    setModo("criar");
    setForm(CATEGORIA_VAZIA);
    setModalAberto(true);
  }

  function abrirEditar(cat) {
    setModo("editar");
    setEditandoId(cat.id);
    setForm({ nome: cat.nome, cor: cat.cor, regra: cat.regra });
    setModalAberto(true);
  }

  async function salvar(e) {
    e.preventDefault();
    if (!form.nome) return;

    try {
      if (modo === "criar") {
        const categoria = await api.post("/categories", { nome: form.nome, cor: form.cor, regra: form.regra || "manual" });
        setCategorias((atual) => [...atual, categoria]);
        mostrarToast(`Categoria "${form.nome}" criada.`);
      } else {
        const categoria = await api.put(`/categories/${editandoId}`, { nome: form.nome, cor: form.cor, regra: form.regra || "manual" });
        setCategorias((atual) => atual.map((c) => (c.id === editandoId ? categoria : c)));
        mostrarToast(`Categoria "${form.nome}" atualizada.`);
      }
      setModalAberto(false);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível salvar a categoria.", "erro");
    }
  }

  async function confirmarExclusao() {
    const alvo = paraExcluir;
    setParaExcluir(null);
    try {
      await api.delete(`/categories/${alvo.id}`);
      setCategorias((atual) => atual.filter((c) => c.id !== alvo.id));
      mostrarToast(`Categoria "${alvo.nome}" removida.`);
    } catch (err) {
      mostrarToast(err.message || "Não foi possível excluir a categoria.", "erro");
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
        <h1 className="text-lg font-medium">Categorias</h1>
        <button
          onClick={abrirCriar}
          className="text-sm px-3 py-1.5 rounded-[var(--radius-control)] border border-border hover:bg-surface-2 transition-colors flex items-center gap-1"
        >
          <Plus size={14} />
          Nova categoria
        </button>
      </div>

      <Modal
        aberto={modalAberto}
        titulo={modo === "criar" ? "Nova categoria" : "Editar categoria"}
        onFechar={() => setModalAberto(false)}
      >
        <form onSubmit={salvar} className="flex flex-col gap-4">
          <div>
            <div className="text-xs text-text-muted mb-1.5">Cor</div>
            <div className="flex items-center gap-2 flex-wrap">
              {CORES_DISPONIVEIS.map((c) => (
                <button
                  key={c.valor}
                  type="button"
                  title={c.nome}
                  aria-label={`Cor ${c.nome}`}
                  onClick={() => setForm({ ...form, cor: c.valor })}
                  className="w-6 h-6 rounded-full flex items-center justify-center transition-transform hover:scale-110"
                  style={{
                    backgroundColor: c.valor,
                    outline: form.cor === c.valor ? `2px solid ${c.valor}` : "none",
                    outlineOffset: 2,
                  }}
                >
                  {form.cor === c.valor && <Check size={12} className="text-white" strokeWidth={3} />}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <input
              type="text"
              placeholder="Nome da categoria (ex: Educação)"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
              required
            />
            <input
              type="text"
              placeholder='Regra (opcional, ex: contém "curso", "livraria")'
              value={form.regra}
              onChange={(e) => setForm({ ...form, regra: e.target.value })}
              className="w-full bg-surface-2 border border-border rounded-[var(--radius-control)] px-3 py-1.5 text-sm outline-none"
            />
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
                {modo === "criar" ? "Criar categoria" : "Salvar alterações"}
              </button>
            </div>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        aberto={!!paraExcluir}
        mensagem={`Tem certeza que quer excluir a categoria "${paraExcluir?.nome}"? Essa ação não pode ser desfeita.`}
        onConfirmar={confirmarExclusao}
        onCancelar={() => setParaExcluir(null)}
      />

      {categorias.length === 0 ? (
        <div className="bg-surface rounded-card border border-border border-dashed p-8 flex flex-col items-center text-center gap-2">
          <Tags size={24} className="text-text-muted" />
          <p className="text-sm text-text-secondary">Nenhuma categoria cadastrada ainda.</p>
          <button onClick={abrirCriar} className="text-xs text-accent mt-1">
            Criar a primeira
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {categorias.map((cat) => (
            <div
              key={cat.id}
              className="bg-surface rounded-card border border-border p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                {/* Bolinha colorida representando a cor da categoria */}
                <span
                  className="w-3 h-3 rounded-full inline-block"
                  style={{ backgroundColor: cat.cor }}
                />
                <div>
                  <div className="text-sm font-medium">{cat.nome}</div>
                  <div className="text-xs text-text-muted">Regra: {cat.regra}</div>
                </div>
              </div>

              <button
                onClick={() => abrirEditar(cat)}
                className="text-xs text-text-secondary hover:text-text-primary"
              >
                Editar
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
