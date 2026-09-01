// ViGenX pipeline editor — no-build React Flow app (ESM via CDN + htm).
import React, { useState, useEffect, useCallback, useRef, useMemo }
  from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";
import ReactFlow, {
  Background, Controls, MiniMap, Handle, Position,
  addEdge, applyNodeChanges, applyEdgeChanges,
} from "https://esm.sh/reactflow@11.11.4?deps=react@18.3.1,react-dom@18.3.1";

const html = htm.bind(React.createElement);
const api = (path, opts) => fetch("/api" + path, opts).then((r) => r.json());
const TERMINAL = ["awaiting_review", "approved", "rejected", "done", "error"];

let SCHEMAS = {};                          // type_id -> schema
const schemaOf = (t) => SCHEMAS[t] || { title: t, inputs: [], outputs: [], params: [] };
let SEQ = 1;

// Typed ports: color-coded so compatible sockets are obvious at a glance.
const TYPE_COLORS = {
  media: "#5b8cff", audio: "#b07cff", subtitles: "#2bd576",
  moments: "#f0b429", text: "#9aa4bd", image: "#ff6fb5", any: "#cfd6e6",
};
const typeColor = (t) => TYPE_COLORS[t] || "#cfd6e6";
const typesCompatible = (a, b) => a === "any" || b === "any" || a === b;

// Resolve any CSS color (named or hex) to a #rrggbb value for the color swatch.
function cssColorToHex(value) {
  if (!value) return "#ffffff";
  if (/^#[0-9a-f]{6}$/i.test(value)) return value;
  try {
    const d = document.createElement("div");
    d.style.color = value;
    document.body.appendChild(d);
    const rgb = getComputedStyle(d).color;
    document.body.removeChild(d);
    const m = rgb.match(/\d+/g);
    if (!m) return "#ffffff";
    return "#" + m.slice(0, 3).map((n) => (+n).toString(16).padStart(2, "0")).join("");
  } catch (e) { return "#ffffff"; }
}

// Sensible file-extension filters for a given file-typed param (by name).
function extsFor(spec) {
  if (spec.type === "folder") return "";
  if (spec.name === "track" || spec.name === "speaker_wav") return "mp3,wav,m4a,ogg,flac";
  if (spec.name === "source") return "mp4,mov,mkv,webm,avi,m4v";
  if (spec.name === "logo_path" || spec.name === "logo") return "png,jpg,jpeg,webp";
  return "";
}

// Node geometry (must match CSS .vx-node-head / .vx-prow heights for handle alignment).
const HEAD = 30, ROW = 26;
const portTop = (i) => HEAD + i * ROW + ROW / 2;

// ---- custom node: labeled typed-port rows + aligned colored handles ---------
function BlockNode({ data, selected }) {
  const s = data.schema;
  const rows = Math.max(s.inputs.length, s.outputs.length, 1);
  const cls = "vx-node" + (selected ? " sel" : "") + (data.status ? " st-" + data.status : "");
  return html`
    <div class=${cls} style=${{ minHeight: `${HEAD + rows * ROW + 6}px` }}>
      <div class="vx-node-head">${s.title}</div>
      <div class="vx-node-rows">
        <div class="vx-col vx-col-in">
          ${s.inputs.map((p) => html`<div class="vx-prow" key=${p.name}
              title=${p.label + " · " + p.type}>${p.label}</div>`)}
        </div>
        <div class="vx-col vx-col-out">
          ${s.outputs.map((p) => html`<div class="vx-prow out" key=${p.name}
              title=${p.label + " · " + p.type}>${p.label}</div>`)}
        </div>
      </div>
      ${s.inputs.map((p, i) => html`<${Handle} key=${"i" + p.name} type="target"
          position=${Position.Left} id=${p.name} title=${p.type}
          style=${{ top: `${portTop(i)}px`, background: typeColor(p.type) }} />`)}
      ${s.outputs.map((p, i) => html`<${Handle} key=${"o" + p.name} type="source"
          position=${Position.Right} id=${p.name} title=${p.type}
          style=${{ top: `${portTop(i)}px`, background: typeColor(p.type) }} />`)}
    </div>`;
}
const nodeTypes = { block: BlockNode };

// ---- param widgets ----------------------------------------------------------
function Field({ spec, value, onChange, fonts, onBrowse }) {
  const v = value === undefined || value === null ? spec.default : value;
  const common = { value: v ?? "", onChange: (e) => onChange(coerce(spec, e.target)) };
  let input;
  if (spec.type === "bool") {
    input = html`<input type="checkbox" checked=${!!v} onChange=${(e) => onChange(e.target.checked)} />`;
  } else if (spec.type === "enum") {
    input = html`<select ...${common}>
      ${spec.choices.map((c) => html`<option key=${c} value=${c}>${c}</option>`)}</select>`;
  } else if (spec.type === "color") {
    input = html`<div class="vx-color-row">
      <input type="color" value=${cssColorToHex(v)} onChange=${(e) => onChange(e.target.value)} />
      <input type="text" value=${v ?? ""} onChange=${(e) => onChange(e.target.value)} />
    </div>`;
  } else if (spec.type === "file" || spec.type === "folder") {
    input = html`<div class="vx-browse-row">
      <input type="text" ...${common} />
      <button type="button" class="vx-btn ghost" title="Browse"
              onClick=${() => onBrowse && onBrowse(spec, (p) => onChange(p))}>📁</button>
    </div>`;
  } else if (spec.type === "font") {
    const list = fonts || [];
    const extra = v && !list.includes(v) ? [v] : [];
    input = html`<select ...${common}>
      <option value="">(default)</option>
      ${[...extra, ...list].map((f) => html`<option key=${f} value=${f}>${f}</option>`)}
    </select>`;
  } else if (spec.type === "text") {
    input = html`<textarea rows="3" ...${common}></textarea>`;
  } else if (spec.type === "int" || spec.type === "float") {
    input = html`<input type="number" step=${spec.type === "int" ? 1 : "any"}
                   min=${spec.min ?? undefined} max=${spec.max ?? undefined} ...${common} />`;
  } else {
    input = html`<input type="text" ...${common} />`;
  }
  return html`<label title=${spec.help || ""}>${spec.label}</label>${input}`;
}
function coerce(spec, target) {
  if (spec.type === "int") return parseInt(target.value || "0", 10);
  if (spec.type === "float") return parseFloat(target.value || "0");
  return target.value;
}

// ---- inspector + preview ----------------------------------------------------
function Inspector({ node, onParam, graphFor, overridesFor, onDelete, hasSource, fonts, onBrowse }) {
  const [t, setT] = useState(1);
  const [showAdv, setShowAdv] = useState(false);
  const [img, setImg] = useState("");
  const [vid, setVid] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const timer = useRef(null);

  const s = node ? node.data.schema : null;
  const params = node ? node.data.params : {};

  const refreshPreview = useCallback(() => {
    if (!node || s.preview_kind === "none") { setImg(""); return; }
    if (!hasSource && s.type_id !== "source") {
      setErr("Pick a source clip to render a preview."); setImg(""); return;
    }
    const overrides = overridesFor ? overridesFor() : {};
    const body = JSON.stringify({ graph: graphFor(), node_id: node.id, t, overrides });
    fetch("/api/preview/frame", { method: "POST", headers: { "Content-Type": "application/json" }, body })
      .then(async (r) => {
        if (!r.ok) { setErr((await r.json()).error || "preview failed"); setImg(""); return; }
        setErr(""); setImg(URL.createObjectURL(await r.blob()));
      })
      .catch((e) => setErr(String(e)));
  }, [node, t, s, graphFor, overridesFor, hasSource]);

  function draft() {
    if (!node) return;
    setBusy(true); setErr(""); setVid("");
    const overrides = overridesFor ? overridesFor() : {};
    fetch("/api/preview/draft", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ graph: graphFor(), node_id: node.id, overrides }) })
      .then(async (r) => {
        setBusy(false);
        if (!r.ok) { setErr((await r.json()).error || "draft failed"); return; }
        setVid(URL.createObjectURL(await r.blob()));
      }).catch((e) => { setBusy(false); setErr(String(e)); });
  }

  useEffect(() => {
    if (!node) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(refreshPreview, 350);
    return () => clearTimeout(timer.current);
  }, [node && node.id, JSON.stringify(params), t]);

  if (!node) return html`<div class="vx-inspector"><p class="vx-muted">
      Select a node to edit its settings and see a live preview.</p>
      <p class="vx-muted">Shortcuts: Ctrl+Z undo · Ctrl+Y redo · Ctrl+C/V copy/paste ·
      Ctrl+D duplicate · Del remove · double-click canvas to add.</p></div>`;

  const basic = s.params.filter((p) => !p.advanced);
  const adv = s.params.filter((p) => p.advanced);
  return html`<div class="vx-inspector">
    <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <h5 style=${{ margin: 0 }}>${s.title}</h5>
      <button class="vx-btn ghost" onClick=${() => onDelete(node.id)}>🗑 Delete</button>
    </div>
    <p class="vx-muted">${s.description || ""}</p>
    ${s.preview_kind !== "none" && !hasSource && s.type_id !== "source"
      ? html`<p class="vx-muted">Tip: pick a clip in <b>Sources</b> to preview on real footage.</p>` : null}
    ${basic.map((spec) => html`<${Field} key=${spec.name} spec=${spec} fonts=${fonts} onBrowse=${onBrowse}
        value=${params[spec.name]} onChange=${(val) => onParam(node.id, spec.name, val)} />`)}
    ${adv.length ? html`<div class="vx-adv-toggle" onClick=${() => setShowAdv(!showAdv)}>
        ${showAdv ? "▾ Hide advanced" : "▸ Advanced"}</div>` : null}
    ${showAdv ? adv.map((spec) => html`<${Field} key=${spec.name} spec=${spec} fonts=${fonts} onBrowse=${onBrowse}
        value=${params[spec.name]} onChange=${(val) => onParam(node.id, spec.name, val)} />`) : null}

    <div class="vx-preview" style=${{ marginTop: "1rem" }}>
      <label>Preview ${s.preview_kind === "none" ? "(non-visual block)" : `@ ${t.toFixed(1)}s`}</label>
      ${s.preview_kind !== "none" ? html`
        <input type="range" min="0" max="30" step="0.5" value=${t}
               onInput=${(e) => setT(parseFloat(e.target.value))} style=${{ width: "100%" }} />
        ${img ? html`<img src=${img} />` : html`<p class="vx-muted">${err || "rendering…"}</p>`}
        ${err && img ? html`<p class="vx-muted">${err}</p>` : null}
        <div style=${{ display: "flex", gap: ".4rem", marginTop: ".4rem" }}>
          <button class="vx-btn ghost" onClick=${refreshPreview}>↻ Refresh</button>
          <button class="vx-btn ghost" onClick=${draft}>${busy ? "…" : "🎬 Draft clip"}</button>
        </div>
        ${vid ? html`<video src=${vid} controls style=${{ marginTop: ".5rem" }}></video>` : null}` : null}
    </div>
  </div>`;
}

// ---- server-side file/folder picker ----------------------------------------
function FsModal({ pick, onClose }) {
  const [cwd, setCwd] = useState("");
  const [data, setData] = useState({ dirs: [], files: [], parent: null, cwd: "" });
  const [err, setErr] = useState("");
  const load = useCallback((path) => {
    const q = new URLSearchParams({ path: path || "", exts: pick.exts || "" });
    fetch("/api/fs/list?" + q.toString()).then((r) => r.json()).then((d) => {
      if (d.error) { setErr(d.error); return; }
      setErr(""); setData(d); setCwd(d.cwd || "");
    }).catch((e) => setErr(String(e)));
  }, [pick]);
  useEffect(() => { load(""); }, []);
  const isFile = pick.mode === "file";
  return html`
    <div class="vx-modal" onClick=${(e) => e.target.classList.contains("vx-modal") && onClose()}>
      <div class="vx-modal-box" style=${{ maxWidth: "640px" }}>
        <div style=${{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong>${isFile ? "Pick a file" : "Pick a folder"}</strong>
          <button class="vx-btn ghost" onClick=${onClose}>Close</button>
        </div>
        <div class="vx-muted" style=${{ margin: ".4rem 0", wordBreak: "break-all" }}>${cwd || "This PC"}</div>
        ${err ? html`<div class="vx-muted">${err}</div>` : null}
        <div class="vx-fs">
          ${data.parent !== null ? html`<div class="vx-fs-row" onClick=${() => load(data.parent)}>⬆ ..</div>` : null}
          ${data.dirs.map((d) => html`<div class="vx-fs-row" key=${d.path}
              onClick=${() => load(d.path)}>📁 ${d.name}</div>`)}
          ${isFile ? data.files.map((f) => html`<div class="vx-fs-row file" key=${f.path}
              onClick=${() => { pick.cb(f.path); onClose(); }}>🎬 ${f.name}</div>`) : null}
        </div>
        ${!isFile && cwd ? html`<button class="vx-btn" style=${{ marginTop: ".6rem" }}
            onClick=${() => { pick.cb(cwd); onClose(); }}>Pick this folder</button>` : null}
      </div>
    </div>`;
}

// ---- main app ---------------------------------------------------------------
function App() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [selId, setSelId] = useState(null);
  const [selEdgeIds, setSelEdgeIds] = useState([]);
  const [palette, setPalette] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [name, setName] = useState("My Pipeline");
  const [gid, setGid] = useState("");
  const [status, setStatus] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [brief, setBrief] = useState("");
  const [plannerMode, setPlannerMode] = useState("auto");
  const [planning, setPlanning] = useState(false);
  const [sources, setSources] = useState([]);
  const [showSrc, setShowSrc] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [srcInput, setSrcInput] = useState("");
  const [srcType, setSrcType] = useState("auto");
  const [palFilter, setPalFilter] = useState("");
  const [addFilter, setAddFilter] = useState("");
  const [fonts, setFonts] = useState([]);
  const [fsPick, setFsPick] = useState(null);     // {mode, exts, cb}
  const [paletteOpen, setPaletteOpen] = useState(true);
  const [rf, setRf] = useState(null);             // React Flow instance
  const [addCompat, setAddCompat] = useState(null); // {nodeId, handleId, side, portType, pos}
  const pending = useRef(null);                   // in-flight onConnectStart info

  // ---- history (undo/redo) ----
  const hist = useRef({ past: [], future: [] });
  const lastParam = useRef(0);
  const snap = () => ({ nodes: JSON.parse(JSON.stringify(nodes)), edges: JSON.parse(JSON.stringify(edges)) });
  const pushHist = useCallback(() => {
    hist.current.past.push(snap());
    if (hist.current.past.length > 60) hist.current.past.shift();
    hist.current.future = [];
  }, [nodes, edges]);
  const undo = useCallback(() => {
    const h = hist.current;
    if (!h.past.length) return;
    h.future.push(snap());
    const prev = h.past.pop();
    setNodes(prev.nodes); setEdges(prev.edges); setStatus("Undo");
  }, [nodes, edges]);
  const redo = useCallback(() => {
    const h = hist.current;
    if (!h.future.length) return;
    h.past.push(snap());
    const nx = h.future.pop();
    setNodes(nx.nodes); setEdges(nx.edges); setStatus("Redo");
  }, [nodes, edges]);

  // ---- node id helper ----
  const mkId = (t) => {
    const ex = new Set(nodes.map((n) => n.id));
    let id;
    do { id = `${t}_${SEQ++}`; } while (ex.has(id));
    return id;
  };

  // ---- ReactFlow change handlers (snapshot on remove/connect/drag) ----
  const onNodesChange = useCallback((c) => {
    if (c.some((x) => x.type === "remove")) pushHist();
    setNodes((ns) => applyNodeChanges(c, ns));
  }, [pushHist]);
  const onEdgesChange = useCallback((c) => {
    if (c.some((x) => x.type === "remove")) pushHist();
    setEdges((es) => applyEdgeChanges(c, es));
  }, [pushHist]);
  const onConnect = useCallback((p) => { pushHist(); setEdges((es) => addEdge({ ...p }, es)); }, [pushHist]);

  // Drag a wire onto empty canvas -> suggest only type-compatible blocks.
  const onConnectStart = useCallback((_evt, p) => { pending.current = p; }, []);
  const onConnectEnd = useCallback((evt) => {
    const p = pending.current; pending.current = null;
    if (!p) return;
    const t = evt && evt.target;
    if (!(t && t.classList && t.classList.contains("react-flow__pane"))) return;
    const node = nodes.find((n) => n.id === p.nodeId);
    if (!node) return;
    const ports = p.handleType === "source" ? node.data.schema.outputs : node.data.schema.inputs;
    const port = (ports || []).find((pp) => pp.name === p.handleId);
    if (!port) return;
    const cx = evt.clientX ?? (evt.changedTouches && evt.changedTouches[0] && evt.changedTouches[0].clientX);
    const cy = evt.clientY ?? (evt.changedTouches && evt.changedTouches[0] && evt.changedTouches[0].clientY);
    let pos;
    if (rf && rf.screenToFlowPosition) pos = rf.screenToFlowPosition({ x: cx, y: cy });
    else if (rf && rf.project) pos = rf.project({ x: cx, y: cy });
    setAddCompat({ nodeId: p.nodeId, handleId: p.handleId, side: p.handleType, portType: port.type, pos });
    setAddFilter(""); setShowAdd(true);
  }, [nodes, rf]);

  function addNodeAndConnect(type_id, compat) {
    const id = mkId(type_id);
    const sch = schemaOf(type_id);
    pushHist();
    setNodes((ns) => ns.concat({
      id, type: "block",
      position: compat.pos || { x: 140 + Math.random() * 220, y: 80 + Math.random() * 220 },
      data: { type_id, params: defaults(type_id), schema: sch },
    }));
    let edge = null;
    if (compat.side === "source") {
      const tp = (sch.inputs || []).find((p) => typesCompatible(compat.portType, p.type));
      if (tp) edge = { source: compat.nodeId, sourceHandle: compat.handleId, target: id, targetHandle: tp.name };
    } else {
      const sp = (sch.outputs || []).find((p) => typesCompatible(compat.portType, p.type));
      if (sp) edge = { source: id, sourceHandle: sp.name, target: compat.nodeId, targetHandle: compat.handleId };
    }
    if (edge) setEdges((es) => addEdge(edge, es));
  }

  function pickAdd(type_id) {
    if (addCompat) addNodeAndConnect(type_id, addCompat);
    else addNode(type_id);
    setShowAdd(false); setAddCompat(null);
  }
  function closeAdd() { setShowAdd(false); setAddCompat(null); }

  // Block incompatible wires AS the user draws them (type mismatch, self-loop,
  // or an input that's already connected) — this is what prevents the
  // "Type mismatch on edge …" errors after the fact.
  const isValidConnection = useCallback((c) => {
    if (!c.source || !c.target || c.source === c.target) return false;
    const src = nodes.find((n) => n.id === c.source);
    const tgt = nodes.find((n) => n.id === c.target);
    if (!src || !tgt) return false;
    const sp = (src.data.schema.outputs || []).find((p) => p.name === c.sourceHandle);
    const tp = (tgt.data.schema.inputs || []).find((p) => p.name === c.targetHandle);
    if (!sp || !tp || !typesCompatible(sp.type, tp.type)) return false;
    if (edges.some((e) => e.target === c.target && e.targetHandle === c.targetHandle)) {
      setStatus(`'${tp.label}' already connected — delete that wire first`);
      return false;
    }
    return true;
  }, [nodes, edges]);
  const onSelectionChange = useCallback(({ nodes: ns, edges: es }) => {
    setSelId(ns && ns[0] ? ns[0].id : null);
    setSelEdgeIds((es || []).map((e) => e.id));
  }, []);

  // ---- delete / clipboard ----
  const deleteNode = useCallback((id) => {
    pushHist();
    setNodes((ns) => ns.filter((n) => n.id !== id));
    setEdges((es) => es.filter((e) => e.source !== id && e.target !== id));
    setSelId((sel) => (sel === id ? null : sel));
  }, [pushHist]);
  const deleteSelection = useCallback(() => {
    if (selId) deleteNode(selId);
    if (selEdgeIds.length) { pushHist(); setEdges((es) => es.filter((e) => !selEdgeIds.includes(e.id))); }
  }, [selId, selEdgeIds, deleteNode, pushHist]);

  const clip = useRef(null);
  const copy = useCallback(() => {
    const n = nodes.find((x) => x.id === selId);
    if (n) { clip.current = JSON.parse(JSON.stringify(n)); setStatus("Copied"); }
  }, [nodes, selId]);
  const paste = useCallback(() => {
    if (!clip.current) return;
    const src = clip.current;
    const id = mkId(src.data.type_id);
    pushHist();
    setNodes((ns) => ns.concat({
      id, type: "block", selected: false,
      position: { x: (src.position?.x || 0) + 48, y: (src.position?.y || 0) + 48 },
      data: { type_id: src.data.type_id, params: { ...src.data.params }, schema: schemaOf(src.data.type_id) },
    }));
  }, [pushHist, nodes]);
  const duplicate = useCallback(() => {
    const n = nodes.find((x) => x.id === selId);
    if (!n) return;
    clip.current = JSON.parse(JSON.stringify(n));
    paste();
  }, [nodes, selId, paste]);

  // ---- load schemas + templates + fonts ----
  useEffect(() => {
    api("/blocks").then((d) => { d.blocks.forEach((b) => (SCHEMAS[b.type_id] = b)); setPalette(d.blocks); });
    api("/templates").then((d) => setTemplates(d.templates));
    api("/fonts").then((d) => setFonts(d.fonts || [])).catch(() => {});
    const tid = window.VIGENX_TEMPLATE_ID;
    if (tid) loadTemplate(tid);
  }, []);

  // Collapse the block palette by toggling a class on the editor grid.
  useEffect(() => {
    const el = document.getElementById("vx-root");
    if (el) el.classList.toggle("vx-collapsed", !paletteOpen);
  }, [paletteOpen]);

  // Open the server-side picker for a file/folder param.
  const onBrowse = useCallback((spec, cb) => {
    setFsPick({ mode: spec.type, exts: extsFor(spec), cb });
  }, []);

  // ---- keyboard shortcuts ----
  useEffect(() => {
    function onKey(e) {
      const tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      const ctrl = e.ctrlKey || e.metaKey;
      if (ctrl && e.key.toLowerCase() === "z" && !e.shiftKey) { e.preventDefault(); undo(); }
      else if (ctrl && (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey))) { e.preventDefault(); redo(); }
      else if (ctrl && e.key.toLowerCase() === "c") { copy(); }
      else if (ctrl && e.key.toLowerCase() === "v") { paste(); }
      else if (ctrl && e.key.toLowerCase() === "d") { e.preventDefault(); duplicate(); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo, copy, paste, duplicate]);

  const graphFor = useCallback(() => ({
    id: gid || undefined, name,
    nodes: nodes.map((n) => ({ id: n.id, type_id: n.data.type_id, params: n.data.params, position: n.position })),
    edges: edges.map((e) => ({ source: e.source, source_port: e.sourceHandle || "out",
                               target: e.target, target_port: e.targetHandle || "in" })),
  }), [nodes, edges, name, gid]);

  function toFlow(graph) {
    const ns = graph.nodes.map((n) => ({
      id: n.id, type: "block",
      position: n.position && n.position.x !== undefined ? n.position : { x: 0, y: 0 },
      data: { type_id: n.type_id, params: { ...n.params }, schema: schemaOf(n.type_id) },
    }));
    const es = graph.edges.map((e, i) => ({
      id: `e${i}`, source: e.source, target: e.target,
      sourceHandle: e.source_port, targetHandle: e.target_port,
    }));
    setNodes(ns); setEdges(es); setName(graph.name || "Untitled"); setGid(graph.id || "");
    hist.current = { past: [], future: [] };
  }
  function loadTemplate(tid) { if (tid) api("/templates/" + tid).then(toFlow); }

  function addNode(type_id, pos) {
    const id = mkId(type_id);
    pushHist();
    setNodes((ns) => ns.concat({
      id, type: "block",
      position: pos || { x: 140 + Math.random() * 220, y: 80 + Math.random() * 220 },
      data: { type_id, params: defaults(type_id), schema: schemaOf(type_id) },
    }));
  }
  function defaults(type_id) {
    const out = {};
    (schemaOf(type_id).params || []).forEach((p) => (out[p.name] = p.default));
    return out;
  }

  const onParam = useCallback((nid, key, val) => {
    const now = Date.now();
    if (now - lastParam.current > 700) { pushHist(); lastParam.current = now; }
    setNodes((ns) => ns.map((n) => n.id === nid
      ? { ...n, data: { ...n.data, params: { ...n.data.params, [key]: val } } } : n));
  }, [pushHist]);

  function autoLayout() {
    const incoming = {}; nodes.forEach((n) => (incoming[n.id] = []));
    edges.forEach((e) => { if (incoming[e.target]) incoming[e.target].push(e.source); });
    const depth = {};
    const dep = (id, seen) => {
      if (depth[id] != null) return depth[id];
      if (seen.has(id)) return 0;
      seen.add(id);
      const ins = incoming[id] || [];
      const v = ins.length ? Math.max(...ins.map((s) => dep(s, seen))) + 1 : 0;
      depth[id] = v; return v;
    };
    nodes.forEach((n) => dep(n.id, new Set()));
    const byLayer = {};
    nodes.forEach((n) => { const L = depth[n.id] || 0; (byLayer[L] = byLayer[L] || []).push(n.id); });
    pushHist();
    setNodes((ns) => ns.map((n) => {
      const L = depth[n.id] || 0; const idx = byLayer[L].indexOf(n.id);
      return { ...n, position: { x: L * 260 + 40, y: idx * 130 + 40 } };
    }));
  }

  function validate() {
    fetch("/api/validate", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ graph: graphFor() }) }).then((r) => r.json())
      .then((d) => setStatus(d.ok ? "Valid ✓" : "Invalid: " + d.error));
  }

  function save() {
    fetch("/api/templates", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(graphFor()) }).then((r) => r.json()).then((d) => {
        setGid(d.id); setStatus("Saved ✓");
        api("/templates").then((x) => setTemplates(x.templates));
      });
  }

  function planWorkflow() {
    const request = brief.trim();
    if (!request || planning) return;
    if (nodes.length && !window.confirm("Replace the current workflow with a generated plan?")) return;
    setPlanning(true); setStatus("Planning workflow..."); setJobUrl("");
    fetch("/api/agent/plan", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brief: request, mode: plannerMode, source: srcInput.trim() }),
    }).then(async (r) => {
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Workflow planning failed");
      return data;
    }).then((data) => {
      toFlow(data.graph);
      const note = (data.warnings || []).length ? ` ${data.warnings.join(" ")}` : "";
      setStatus(`${data.summary} Planner: ${data.planner}.${note}`);
    }).catch((err) => setStatus(err.message || String(err)))
      .finally(() => setPlanning(false));
  }

  // ---- sources ----
  const selectedSources = () => sources.filter((s) => s.selected);
  const previewOverrides = useCallback(() => {
    const sel = sources.filter((s) => s.selected)[0];
    if (!sel) return {};
    const o = {};
    nodes.forEach((n) => { if (n.data.type_id === "source") o[n.id] = { source: sel.source, source_type: sel.source_type }; });
    return o;
  }, [nodes, sources]);
  function resolveSources() {
    setStatus("Resolving…");
    fetch("/api/sources/resolve", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: srcInput, source_type: srcType }) })
      .then((r) => r.json()).then((d) => {
        setSources((d.items || []).map((i) => ({ ...i, selected: true })));
        setStatus(`Found ${(d.items || []).length} item(s)`);
      });
  }
  const toggleSrc = (idx) => setSources((ss) => ss.map((s, i) => i === idx ? { ...s, selected: !s.selected } : s));
  const selectAllSrc = (val) => setSources((ss) => ss.map((s) => ({ ...s, selected: val })));

  // ---- run with live per-node status over SSE ----
  function run() {
    const refs = selectedSources().map((s) => ({ source: s.source, source_type: s.source_type, title: s.title }));
    setNodes((ns) => ns.map((n) => ({ ...n, data: { ...n.data, status: undefined } })));  // clear
    setStatus("Starting…"); setJobUrl("");
    fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ graph: graphFor(), source_refs: refs }) }).then((r) => r.json()).then((d) => {
        if (!d.job_id) { setStatus("Run failed"); return; }
        setJobUrl(d.url);
        const es = new EventSource(`/jobs/${d.job_id}/stream`);
        es.onmessage = (ev) => {
          const data = JSON.parse(ev.data);
          if (data.node_status) {
            setNodes((ns) => ns.map((n) => data.node_status[n.id]
              ? { ...n, data: { ...n.data, status: data.node_status[n.id].status } } : n));
          }
          setStatus(`${data.status} · ${Math.round(data.progress_pct || 0)}%`);
          if (TERMINAL.includes(data.status)) es.close();
        };
        es.onerror = () => es.close();
      });
  }

  // ---- palette ----
  const byCategory = useMemo(() => {
    const f = palFilter.toLowerCase();
    const g = {};
    palette.filter((b) => !f || (b.title + b.category + (b.description || "")).toLowerCase().includes(f))
      .forEach((b) => (g[b.category] = g[b.category] || []).push(b));
    return g;
  }, [palette, palFilter]);
  const addMatches = useMemo(() => {
    const f = addFilter.toLowerCase();
    let list = palette;
    if (addCompat) {
      list = list.filter((b) => {
        const ports = addCompat.side === "source" ? b.inputs : b.outputs;
        return (ports || []).some((p) => typesCompatible(addCompat.portType, p.type));
      });
    }
    return list.filter((b) => !f || (b.title + b.category).toLowerCase().includes(f));
  }, [palette, addFilter, addCompat]);

  const selNode = nodes.find((n) => n.id === selId) || null;

  return html`
    <div class="vx-toolbar">
      <div class="vx-agent-bar">
        <label for="workflow-brief">Describe your edit</label>
        <input id="workflow-brief" value=${brief}
               onChange=${(e) => setBrief(e.target.value)}
               onKeyDown=${(e) => e.key === "Enter" && planWorkflow()}
               placeholder="Turn this podcast into three vertical clips with captions and music" />
        <select value=${plannerMode} onChange=${(e) => setPlannerMode(e.target.value)}
                title="Workflow planner mode">
          <option value="auto">Auto</option>
          <option value="local">Local</option>
          <option value="ai">AI</option>
        </select>
        <button class="vx-btn" disabled=${planning || !brief.trim()} onClick=${planWorkflow}>
          ${planning ? "Planning..." : "Create workflow"}
        </button>
      </div>
      <div class="vx-toolbar-main">
        <button class="vx-btn ghost" title="Toggle block palette"
                onClick=${() => setPaletteOpen((o) => !o)}>${paletteOpen ? "◀" : "▶"}</button>
        <input aria-label="Workflow name" value=${name} onChange=${(e) => setName(e.target.value)}
               style=${{ width: "160px" }} />
        <select aria-label="Load template" onChange=${(e) => loadTemplate(e.target.value)} value="">
          <option value="">Load template...</option>
          ${templates.map((t) => html`<option key=${t.id} value=${t.id}>${t.name}</option>`)}
        </select>
        <button class="vx-btn ghost" title="Undo (Ctrl+Z)" onClick=${undo}>↶</button>
        <button class="vx-btn ghost" title="Redo (Ctrl+Y)" onClick=${redo}>↷</button>
        <button class="vx-btn ghost" title="Auto-arrange" onClick=${autoLayout}>Layout</button>
        <button class="vx-btn ghost" onClick=${validate}>Validate</button>
        <button class="vx-btn ghost" onClick=${save}>Save</button>
        <button class="vx-btn ghost" onClick=${() => setShowSrc(!showSrc)}>Sources (${selectedSources().length})</button>
        <button class="vx-btn ghost" disabled=${!selId && !selEdgeIds.length}
                title="Delete selection (Del)" onClick=${deleteSelection}>Delete</button>
        <button class="vx-btn" onClick=${run}>Run</button>
        <span class="vx-muted" role="status">${status} ${jobUrl ? html`<a href=${jobUrl} style=${{ color: "#9bf" }}>view job ↗</a>` : null}</span>
      </div>
    </div>

    <div class="vx-palette">
      <input placeholder="🔍 search blocks" value=${palFilter}
             onChange=${(e) => setPalFilter(e.target.value)} style=${{ width: "100%", marginBottom: ".4rem" }} />
      <div class="vx-legend">
        ${["media", "audio", "subtitles", "moments", "text", "image"].map((tp) => html`
          <span key=${tp}><i style=${{ background: typeColor(tp) }}></i>${tp}</span>`)}
      </div>
      ${Object.keys(byCategory).sort().map((cat) => html`
        <div key=${cat}>
          <h6>${cat}</h6>
          ${byCategory[cat].map((b) => html`
            <div class="vx-pitem" key=${b.type_id} title=${b.description}
                 onClick=${() => addNode(b.type_id)}>+ ${b.title}</div>`)}
        </div>`)}
    </div>

    <div class="vx-canvas" onDoubleClick=${() => { setAddFilter(""); setShowAdd(true); }}>
      <${ReactFlow} nodes=${nodes} edges=${edges} nodeTypes=${nodeTypes}
        onInit=${setRf}
        onNodesChange=${onNodesChange} onEdgesChange=${onEdgesChange}
        onConnect=${onConnect} onSelectionChange=${onSelectionChange}
        onConnectStart=${onConnectStart} onConnectEnd=${onConnectEnd}
        isValidConnection=${isValidConnection}
        onNodeDragStart=${pushHist} deleteKeyCode=${["Backspace", "Delete"]} fitView>
        <${Background} /><${Controls} />
        <${MiniMap}
          pannable
          zoomable
          nodeColor="#3a425c"
          maskColor="rgba(14, 16, 22, 0.72)"
          style=${{ backgroundColor: "#14161d", border: "1px solid #333b52" }}
        />
      <//>
      ${nodes.length === 0 ? html`<div class="vx-empty">
        Click a block on the left, double-click here, or load a template to start.</div>` : null}
    </div>

    <${Inspector} node=${selNode} onParam=${onParam} graphFor=${graphFor}
                  overridesFor=${previewOverrides} onDelete=${deleteNode}
                  hasSource=${sources.some((s) => s.selected)}
                  fonts=${fonts} onBrowse=${onBrowse} />

    ${fsPick ? html`<${FsModal} pick=${fsPick} onClose=${() => setFsPick(null)} />` : null}

    ${showAdd ? html`
    <div class="vx-modal" onClick=${(e) => e.target.classList.contains("vx-modal") && closeAdd()}>
      <div class="vx-modal-box" style=${{ maxWidth: "480px" }}>
        <strong>${addCompat
          ? html`Connect to a <span style=${{ color: typeColor(addCompat.portType) }}>${addCompat.portType}</span> block`
          : "Add a block"}</strong>
        <input autoFocus placeholder="🔍 search" value=${addFilter}
               onChange=${(e) => setAddFilter(e.target.value)} style=${{ width: "100%", margin: ".5rem 0" }} />
        <div style=${{ maxHeight: "50vh", overflow: "auto" }}>
          ${addMatches.length === 0 ? html`<p class="vx-muted">No compatible blocks.</p>` : null}
          ${addMatches.map((b) => html`
            <div class="vx-pitem" key=${b.type_id} title=${b.description}
                 onClick=${() => pickAdd(b.type_id)}>
              <b>${b.title}</b> <span class="vx-muted">· ${b.category}</span></div>`)}
        </div>
      </div>
    </div>` : null}

    ${showSrc ? html`
    <div class="vx-modal" onClick=${(e) => e.target.classList.contains("vx-modal") && setShowSrc(false)}>
      <div class="vx-modal-box">
        <div style=${{ display: "flex", gap: ".5rem", alignItems: "center" }}>
          <strong>Sources</strong>
          <input style=${{ flex: 1 }} value=${srcInput} onChange=${(e) => setSrcInput(e.target.value)}
                 placeholder="file · folder · *.mp4 glob · video/playlist/channel URL · @instagram" />
          <select value=${srcType} onChange=${(e) => setSrcType(e.target.value)}>
            <option value="auto">auto</option><option value="local">local</option>
            <option value="url">url</option><option value="instagram">instagram</option>
          </select>
          <button class="vx-btn" onClick=${resolveSources}>Resolve</button>
          <button class="vx-btn ghost" onClick=${() => setShowSrc(false)}>Close</button>
        </div>
        <label style=${{ margin: ".5rem 0", display: "block" }}>
          <input type="checkbox" checked=${sources.length > 0 && sources.every((s) => s.selected)}
                 onChange=${(e) => selectAllSrc(e.target.checked)} />
          Select all (${selectedSources().length}/${sources.length})
        </label>
        <div class="vx-grid">
          ${sources.map((s, i) => html`
            <div class=${"vx-card" + (s.selected ? " sel" : "")} key=${i} onClick=${() => toggleSrc(i)}>
              ${s.thumbnail ? html`<img src=${s.thumbnail} />` : html`<div class="vx-noimg">🎬</div>`}
              <div class="vx-card-t" title=${s.title}>${s.title}</div>
              ${s.duration ? html`<div class="vx-muted">${Math.round(s.duration)}s</div>` : null}
            </div>`)}
        </div>
      </div>
    </div>` : null}`;
}

createRoot(document.getElementById("vx-root")).render(html`<${App} />`);
