// App.jsx — GraphShield, full two-mode port.
// Structure + colors mirror graph_viewer.py. Mode = gs-light / gs-dark on <body>,
// defaulting to the OS setting. All logic (stream / questions / reports / history)
// is unchanged from Step 3c.

import { useEffect, useRef, useState } from "react";
import ForceGraph3D from "react-force-graph-3d";
import "./index.css";

const SESSION_ID = crypto.randomUUID?.() ?? String(Math.random()).slice(2);

const GRAPH_BG_LIGHT = "#c7d7e1";
const GRAPH_BG_DARK = "#526c76";

const nodeColor = (n) =>
  n.group === "target" ? "#ff4d4d" : n.group === "neighbor" ? "#f6cfc7" : "#b9d7e3";
const nodeVal = (n) =>
  n.group === "target" ? 14 : 3 + 9 * Number(n.gnn_importance || 0);

const QUESTIONS = [
  { id: "question_1", label: "What drove this prediction?" },
  { id: "question_2", label: "How did neighbors influence it?" },
  { id: "question_3", label: "What reduced the risk?" },
];

// Renders a factor list ("n/a" if empty) — mirrors listOrNA in the original.
function listOrNA(v) {
  if (Array.isArray(v)) return v.length ? v.join(", ") : "n/a";
  return v || "n/a";
}

export default function App() {
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [selected, setSelected] = useState(null);
  const [analysis, setAnalysis] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [reportError, setReportError] = useState("");
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  // start from the OS preference, then let the user toggle
  const [dark, setDark] = useState(
    () => window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? true
  );

  const esRef = useRef(null);
  const fgRef = useRef(null);

  // Apply the mode class to <body> so all the gs-light/gs-dark CSS keys off it.
  useEffect(() => {
    document.body.classList.toggle("gs-dark", dark);
    document.body.classList.toggle("gs-light", !dark);
  }, [dark]);

  useEffect(() => {
    fetch("/api/graph?top_n_targets=15&max_neighbors=25&num_normal=10")
      .then((r) => r.json())
      .then(setGraph)
      .catch((e) => console.error("graph load failed", e));
  }, []);

  useEffect(() => () => esRef.current?.close(), []);

  function handleNodeClick(node) {
    esRef.current?.close();
    setStreaming(false);
    setAnalysis("");
    setSelected(node);

    const distance = 120;
    const hyp = Math.hypot(node.x || 0, node.y || 0, node.z || 0) || 1;
    const r = 1 + distance / hyp;
    fgRef.current?.cameraPosition(
      { x: (node.x || 0) * r, y: (node.y || 0) * r, z: (node.z || 0) * r },
      node,
      800
    );
  }

  function runAnalysis(questionId = null) {
    if (!selected) return;
    esRef.current?.close();
    setAnalysis("");
    setStreaming(true);

    const params = new URLSearchParams({
      txid: selected.txId,
      node_index: String(selected.id),
      request_type: questionId ? "question" : "initial_analysis",
      session_id: SESSION_ID,
    });
    if (questionId) params.set("question_id", questionId);

    const es = new EventSource(`/api/analysis/stream?${params}`);
    esRef.current = es;
    es.onmessage = (ev) => setAnalysis((prev) => prev + ev.data.replaceAll("\\n", "\n"));
    es.addEventListener("done", () => { es.close(); setStreaming(false); });
    es.addEventListener("error", (ev) => {
      setAnalysis((prev) => prev + `\n[error] ${ev.data ?? "stream failed"}`);
      es.close(); setStreaming(false);
    });
  }

  async function downloadReport() {
    if (!selected) return;
    setReporting(true);
    setReportError("");
    const params = new URLSearchParams({
      session_id: SESSION_ID, txid: selected.txId, node_index: String(selected.id),
    });
    try {
      const res = await fetch(`/api/reports?${params}`, { method: "POST" });
      if (!res.ok) {
        const msg = await res.json().catch(() => ({}));
        throw new Error(msg.detail || `Report failed (${res.status})`);
      }
      const blob = await res.blob();
      const disp = res.headers.get("Content-Disposition") || "";
      const match = disp.match(/filename="(.+?)"/);
      const filename = match ? match[1] : `report_${selected.txId}.pdf`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setReportError(e.message);
    } finally {
      setReporting(false);
    }
  }

  async function loadHistory() {
    setShowHistory(true);
    try {
      const res = await fetch("/api/reports/history?limit=50");
      setHistory(await res.json());
    } catch (e) {
      console.error("history load failed", e);
    }
  }

  function downloadFromHistory(storagePath) {
    const url = `/api/reports/download?storage_path=${encodeURIComponent(storagePath)}`;
    window.open(url, "_blank");
  }

  const riskText =
    selected?.predicted_risk != null
      ? `Risk ${(Number(selected.predicted_risk) * 100).toFixed(1)}%`
      : "Risk n/a";

  return (
    <div className="app">
      {/* ---------- Sidebar ---------- */}
      <div className="sidebar">
        <div className="brand-row">
          <div className="brand">GraphShield</div>
          <button className="mode-toggle" onClick={() => setDark((d) => !d)}>
            {dark ? "☀ Light" : "🌙 Dark"}
          </button>
        </div>

        {!selected && !showHistory && <p className="hint">Click a node to inspect it.</p>}

        {selected && (
          <>
            <div className="panel-top">
              <h3>{selected.txId}</h3>
              <div className="risk-pill">{riskText}</div>
            </div>

            <div className="info-grid">
              <div className="info-box"><div className="lbl">Prediction</div><div className="val">{selected.prediction || "n/a"}</div></div>
              <div className="info-box"><div className="lbl">True Label</div><div className="val">{selected.true_label || "n/a"}</div></div>
              <div className="info-box">
                <div className="lbl">Positive SHAP</div>
                <div className="val">{selected.shap_increasing_cat || "n/a"}</div>
                <div className="raw">{selected.shap_increasing_raw || ""}</div>
              </div>
              <div className="info-box">
                <div className="lbl">Negative SHAP</div>
                <div className="val">{selected.shap_decreasing_cat || "n/a"}</div>
                <div className="raw">{selected.shap_decreasing_raw || ""}</div>
              </div>
              <div className="info-box wide"><div className="lbl">GNN Importance</div><div className="val">{Number(selected.gnn_importance || 0).toFixed(4)}</div></div>
              <div className="info-box"><div className="lbl">Transaction Profile Factors</div><div className="val">{listOrNA(selected.transaction_profile_factors)}</div></div>
              <div className="info-box"><div className="lbl">Network Context Factors</div><div className="val">{listOrNA(selected.network_context_factors)}</div></div>
            </div>

            <div className="actions">
              <button className="action-btn" onClick={() => runAnalysis()} disabled={streaming}>
                {streaming ? "Analyzing…" : "Analyze Transaction"}
              </button>
              <button className="action-btn" onClick={downloadReport} disabled={reporting}>
                {reporting ? "Generating…" : "Generate Report"}
              </button>
            </div>
            {reportError && <div className="report-error">⚠️ {reportError}</div>}

            <div className="section">
              <div className="section-title">Ask a question</div>
              {QUESTIONS.map((q) => (
                <button key={q.id} className="action-btn qbtn" onClick={() => runAnalysis(q.id)} disabled={streaming}>
                  {q.label}
                </button>
              ))}
            </div>

            {(analysis || streaming) && (
              <div className="response">
                {analysis}
                {streaming && <span style={{ opacity: 0.5 }}>▌</span>}
              </div>
            )}
          </>
        )}

        {/* ---------- History ---------- */}
        <div className="section">
          <button className="action-btn qbtn" onClick={loadHistory}>Report History</button>
          {showHistory && history.map((r) => (
            <div className="hist-item" key={r.document_id}>
              <div><strong>{r.transaction_id}</strong> · {r.status}</div>
              <div style={{ opacity: 0.7 }}>{r.generated_at}</div>
              <span className="hist-dl" onClick={() => downloadFromHistory(r.storage_path)}>Download</span>
            </div>
          ))}
          {showHistory && history.length === 0 && <p className="hint">No reports yet.</p>}
        </div>
      </div>

      {/* ---------- Graph ---------- */}
      <div className="graph-pane">
        <div className="legend">
          <div className="legend-title">Legend</div>
          <div className="legend-row"><span style={{ background: "#ff4d4d" }} />Suspicious target</div>
          <div className="legend-row"><span style={{ background: "#f6cfc7" }} />Important neighbor</div>
          <div className="legend-row"><span style={{ background: "#b9d7e3" }} />Normal / licit comparison</div>
          <div className="legend-help">Click node · Drag to rotate · Scroll to zoom</div>
        </div>
        <ForceGraph3D
          ref={fgRef}
          graphData={graph}
          nodeId="id"
          nodeLabel={(n) => `${n.txId} (${n.prediction})`}
          nodeColor={nodeColor}
          nodeVal={nodeVal}
          linkWidth={(l) => 0.5 + 5 * Number(l.importance || 0)}
          linkColor={() => "rgba(255,255,255,0.25)"}
          onNodeClick={handleNodeClick}
          backgroundColor={dark ? GRAPH_BG_DARK : GRAPH_BG_LIGHT}
        />
      </div>
    </div>
  );
}