"""ForceGraph3D V2 component for GraphShield.
 
The graph engine and visual interactions stay in JavaScript. The V2 component
bridge sends discrete node and Analyze actions back to Streamlit.
"""
 
import base64
 
import streamlit as st
 
_HTML = """
<div id="graph-shell">
<div id="graph"></div>
<div id="legend">
  <div><span style="background:#ff4d4d"></span>Suspicious target</div>
  <div><span style="background:#f6cfc7"></span>Important neighbor</div>
  <div><span style="background:#b9d7e3"></span>Normal / licit comparison</div>
  <div class="legend-help">Click node · Drag to rotate · Scroll to zoom</div>
</div>
<div id="panel"></div>
</div>
"""
 
_CSS = """
:root{
  --card-1:#07506a;
  --card-2:#124f65;
  --card-3:#0d4054;
  --card-4:#083240;
  --cream:#ffffffdb;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
html,body,#graph-shell{background:#f5f8fa}
body.gs-dark, body.gs-dark #graph-shell{background:#0a3142}
#graph-shell{
  position:relative;width:100%;height:100%;min-height:420px;overflow:hidden;
  background:
    radial-gradient(circle at 18% 18%,rgba(7,80,106,.055),transparent 24%),
    radial-gradient(circle at 82% 12%,rgba(18,79,101,.045),transparent 22%),
    linear-gradient(135deg,#f8fbfc 0%,#f2f7f9 55%,#edf4f6 100%);
}
body.gs-light #graph-shell{
  background:#c7d7e1 !important;
}
body.gs-dark #graph-shell{
  background:#b4c0c4 !important;
}
#graph-shell::before,#graph-shell::after{
  content:"";position:absolute;left:-8%;right:-8%;pointer-events:none;z-index:1;
  border-radius:50%;filter:blur(2px)
}
#graph-shell::before{
  height:30%;bottom:-18%;opacity:.24;
  background:radial-gradient(75% 140% at 22% 0%,rgba(7,80,106,.08),transparent 60%),radial-gradient(70% 130% at 72% 0%,rgba(18,79,101,.065),transparent 62%);
}
#graph-shell::after{
  height:20%;bottom:-12%;opacity:.16;
  background:radial-gradient(62% 120% at 48% 0%,rgba(7,80,106,.08),transparent 64%);
}
body.gs-dark #graph-shell::before{opacity:.16;background:transparent !important}
body.gs-dark #graph-shell::after{opacity:.10;background:transparent !important}
#graph{width:100%;height:100%;position:relative;z-index:2;overflow:hidden}
#graph .scene-container,#graph canvas{display:block !important;margin:0 !important;padding:0 !important}
body.gs-light #graph,body.gs-light #graph .scene-container,body.gs-light #graph canvas,body.gs-light .scene-nav-info{background:#c7d7e1 !important}
body.gs-dark #graph,body.gs-dark #graph .scene-container,body.gs-dark #graph canvas,body.gs-dark .scene-nav-info{background:#526c76 !important}
#panel{
  position:absolute;top:18px;right:18px;width:clamp(320px,30vw,430px);max-height:calc(100% - 36px);overflow-y:auto;
  background:rgba(58,79,89,1.000);
  color:#fff;border:1px solid rgba(46,73,82,1.000);border-radius:30px;padding:20px;box-sizing:border-box;
  box-shadow:0 24px 58px rgba(3,31,45,.28);font-size:12px;line-height:1.5;display:none;z-index:20;
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)
}
#panel::before{content:"";position:absolute;width:124px;height:124px;border-radius:50%;right:-42px;top:-42px;background:rgba(255,255,255,.10);pointer-events:none}
#panel::-webkit-scrollbar{width:7px}#panel::-webkit-scrollbar-thumb{background:rgba(255,255,255,.20);border-radius:999px}
.panel-top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:14px;position:relative;z-index:2}
.panel-title-wrap{min-width:0}
#panel h3{margin:0;font-size:28px;line-height:1.1;color:#fff;word-break:break-word}
.risk-pill{display:inline-flex;align-items:center;justify-content:center;padding:10px 15px;border-radius:999px;background:var(--cream);color:var(--card-4);font-weight:800;font-size:12px;white-space:nowrap;border:1px solid rgba(255,255,255,.28);box-shadow:0 10px 24px rgba(3,31,45,.14)}
.info-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;position:relative;z-index:2}
.info-box{min-width:0;border-radius:21px;padding:14px 15px;background:rgba(8,50,64,.46);border:1px solid rgba(255,255,255,.10);box-shadow:inset 0 1px 0 rgba(255,255,255,.035)}
.info-box.wide{grid-column:1/-1}
.lbl{color:rgba(255,255,255,.72);font-size:10px;text-transform:uppercase;letter-spacing:.045em;margin:0 0 6px;font-weight:700}
.val{color:#fff;word-break:break-word;font-size:13px;font-weight:700;line-height:1.4}
.raw{color:rgba(255,255,255,.63);font-size:9px;font-family:monospace;margin-top:5px;word-break:break-word;line-height:1.4}
.rh{color:#fff;font-weight:800}.rl{color:#fff;font-weight:800}
#pc{position:absolute;top:14px;right:14px;left:auto;cursor:pointer;color:rgba(255,255,255,.92);font-size:17px;background:rgba(8,50,64,.55);border:1px solid rgba(255,255,255,.22);width:34px;height:34px;border-radius:50%;z-index:25;display:flex;align-items:center;justify-content:center;line-height:1;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);box-shadow:0 6px 16px rgba(0,0,0,.28)}.panel-top{padding-right:44px}
#pc:hover{color:#fff;background:rgba(255,255,255,.12)}
.actions{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;margin-top:15px;position:relative;z-index:2}
/* Unified Analyze / Report buttons.
   Rest: dark translucent surface, white text (old Report look).
   Hover: cream surface, dark navy text (old Analyze look).
   Both selectors include .primary so it does NOT retain the old cream-at-rest
   appearance -- the class stays for backwards compat but is visually inert. */
/* REST -- both buttons, same look. No :focus/:active in this selector list,
   otherwise clicking the button re-applies the rest bg on top of :hover. */
.action-btn,
.action-btn.primary{min-height:52px;padding:11px 12px;border-radius:18px;border:1px solid rgba(255,255,255,.14) !important;background-color:rgba(255,255,255,.06) !important;background-image:none !important;color:#fff !important;-webkit-text-fill-color:#fff !important;cursor:pointer;font-weight:700;font-size:12px;white-space:normal;transition:background-color .18s ease,color .18s ease,transform .18s ease,border-color .18s ease;opacity:1 !important;box-shadow:none !important}
/* HOVER -- both buttons flip to cream + dark navy. Hoisted with html/body
   ancestor for extra specificity so nothing wins by accident. */
html body .action-btn:hover:not(:disabled),
html body .action-btn.primary:hover:not(:disabled){transform:translateY(-1px);background-color:#ffffffdb !important;background-image:none !important;border-color:rgba(255,255,255,.28) !important;color:#083240 !important;-webkit-text-fill-color:#083240 !important;box-shadow:0 12px 24px rgba(3,31,45,.15) !important}
.action-btn:disabled,
.action-btn.primary:disabled{cursor:not-allowed;transform:none;background:rgba(255,255,255,.10) !important;color:#eaf3f7 !important;-webkit-text-fill-color:#eaf3f7 !important;border-color:rgba(255,255,255,.14) !important;opacity:1 !important;box-shadow:none !important}
.report-error{margin-top:10px;padding:10px 11px;border-radius:12px;background:rgba(78,24,24,.72);border:1px solid rgba(255,176,176,.25);color:#ffd0d0;font-size:10px}
#legend{
  position:absolute !important;top:40px !important;left:18px !important;bottom:auto !important;right:auto !important;width:min(255px,calc(100% - 36px));box-sizing:border-box;
  color:#fff;font-size:11px;background:rgba(58,79,89,1.000);padding:15px 16px;border-radius:22px;z-index:10;pointer-events:none;
  border:1px solid rgba(255,255,255,.14);box-shadow:0 18px 40px rgba(3,31,45,.20);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)
}
/* LIGHT mode: legend matches the dashboard sidebar (white surface, dark text) */
body.gs-light #legend{background:#ffffff !important;color:#063142 !important;border:1px solid #d8e3ea !important;box-shadow:0 12px 30px rgba(6,49,66,.12) !important}
body.gs-light #legend::before{color:#063142 !important}
body.gs-light #legend>div,body.gs-light #legend .legend-help{color:#063142 !important}
body.gs-light #legend span{box-shadow:0 0 0 2px rgba(6,49,66,.10) !important}
body.gs-light .legend-help{color:#4a6373 !important}
#legend::before{content:"Legend";display:block;color:var(--legend-title-color,#fff);font-size:17px;font-weight:800;margin-bottom:10px;text-align:left}
body.gs-dark #legend::before{color:#fff !important}
#legend>div{display:flex;align-items:center;gap:7px;margin:7px 0;font-weight:700}
#legend span{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:0;flex:0 0 auto;box-shadow:0 0 0 2px rgba(255,255,255,.08)}
.legend-help{margin-top:8px;color:rgba(255,255,255,.65);font-size:9px;font-weight:500!important}
/* rotate/zoom/pan hint: no pill background, keep readability via text-shadow */
#graph .scene-nav-info,.scene-nav-info{opacity:1 !important;visibility:visible !important;border:none !important;margin:0 !important;padding:0 !important;width:100% !important;box-sizing:border-box !important;font-weight:600 !important;pointer-events:none !important;backdrop-filter:none !important;-webkit-backdrop-filter:none !important}
body.gs-light #graph .scene-nav-info,body.gs-light .scene-nav-info{color:#083240 !important;text-shadow:0 1px 2px rgba(255,255,255,.6) !important}
body.gs-dark #graph .scene-nav-info,body.gs-dark .scene-nav-info{color:#1c2529 !important;text-shadow:0 1px 2px rgba(255,255,255,.6) !important}
#graph .scene-nav-info{color:#083240 !important;text-shadow:0 1px 2px rgba(255,255,255,.6) !important}
/* ---- LIGHT mode: card matches the dashboard sidebar (white) + response area (#f4f8fb) ---- */
body.gs-light #panel{background:#ffffff !important;color:#063142 !important;border:1px solid #d8e3ea !important;box-shadow:0 16px 40px rgba(6,49,66,.14) !important}
body.gs-light #panel::before{background:rgba(6,49,66,.04) !important}
body.gs-light #panel::-webkit-scrollbar-thumb{background:rgba(6,49,66,.20) !important}
body.gs-light #panel h3{color:#063142 !important}
body.gs-light .info-box{background:#f4f8fb !important;border:1px solid #d8e3ea !important;box-shadow:inset 0 1px 0 rgba(255,255,255,.9) !important}
body.gs-light .lbl{color:#4a6373 !important}
body.gs-light .val{color:#063142 !important}
body.gs-light .raw{color:#5a7180 !important}
body.gs-light .rh,body.gs-light .rl{color:#063142 !important}
body.gs-light .risk-pill{background:#e5eef3 !important;color:#0b3a4c !important;border:1px solid #d0dde4 !important;box-shadow:0 6px 16px rgba(6,49,66,.08) !important}
body.gs-light #pc{background:#eef4f7 !important;border:1px solid #cfdde5 !important;color:#063142 !important;box-shadow:0 2px 6px rgba(6,49,66,.08) !important}
body.gs-light #pc:hover{background:#e0ebf1 !important;color:#063142 !important}
@media (max-width:900px){
  #legend{top:10px;left:10px;width:min(220px,calc(100% - 20px));font-size:10px;padding:11px 12px;border-radius:18px}
  #legend::before{font-size:15px;margin-bottom:7px}
  .legend-help{display:none}
  #panel{top:10px;right:10px;width:min(390px,calc(100% - 20px));max-height:calc(100% - 20px);padding:17px;border-radius:25px}
  #panel h3{font-size:23px}.risk-pill{font-size:11px;padding:8px 12px}
}
@media (max-width:620px){
  #panel{left:8px;right:8px;width:auto;top:8px;max-height:calc(100% - 16px);padding:15px;border-radius:22px}
  .panel-top{flex-direction:column;padding-left:38px}
  .info-grid{grid-template-columns:1fr;gap:9px}.info-box.wide{grid-column:auto}
  .actions{grid-template-columns:1fr}.action-btn{min-height:48px}
  #legend{width:min(205px,calc(100% - 16px));left:8px;top:8px}
}
"""
 
_JS = r"""
function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (window.ForceGraph3D && src.includes("3d-force-graph")) { resolve(); return; }
    if (window.THREE && src.includes("three")) { resolve(); return; }
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      existing.addEventListener("load", resolve, {once:true});
      existing.addEventListener("error", () => reject(new Error("Failed to load " + src)), {once:true});
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load " + src));
    document.head.appendChild(s);
  });
}
 
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, ch => ({
    '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'
  })[ch]);
}
 
export default async function(component) {
  const { data, setTriggerValue, parentElement } = component;
 
  await loadScript("https://unpkg.com/three@0.149.0/build/three.min.js");
  await loadScript("https://unpkg.com/3d-force-graph@1.71.3/dist/3d-force-graph.min.js");
 
  const graphData = data.graph_data || {nodes:[], links:[]};
  const height = data.height || 650;
  const selectedTxId = data.selected_txid ? String(data.selected_txid) : null;
  const reportTxId = data.report_txid ? String(data.report_txid) : null;
  const reportPdfBase64 = data.report_pdf_base64 || null;
  const reportFilename = data.report_filename || "GraphShield_Report.pdf";
  const reportError = data.report_error || null;
  const reportDownloadToken = data.report_download_token || null;
 
  console.log("[REPORT][GRAPH] component state", {
    selectedTxId,
    reportTxId,
    hasPdf: Boolean(reportPdfBase64),
    pdfBase64Length: reportPdfBase64 ? reportPdfBase64.length : 0,
    reportFilename,
    reportDownloadToken,
    reportError
  });
 
  const graphEl = parentElement.querySelector("#graph");
  const shellEl = parentElement.querySelector("#graph-shell");
  const panel = parentElement.querySelector("#panel");

  // Keep the iframe/component, shell and WebGL host at exactly the same height.
  // This prevents unpainted rows above/below the canvas from showing as white strips.
  document.documentElement.style.height = height + "px";
  document.body.style.height = height + "px";
  // parentElement is a ShadowRoot in Streamlit bidi components, not a normal HTMLElement.
  // A ShadowRoot has querySelector(), but no .style property. Set its host safely instead.
  const hostEl = parentElement.host || null;
  if (hostEl && hostEl.style) hostEl.style.height = height + "px";
  if (shellEl) shellEl.style.height = height + "px";
  graphEl.style.height = height + "px";
 
  // Single source of truth for the graph canvas background.
  // Change these two values only; every place that paints the canvas uses graphBg().
  const GRAPH_BG_LIGHT = "#c7d7e1";
  const GRAPH_BG_DARK  = "#526c76";
  const graphBg = () => document.body.classList.contains("gs-light") ? GRAPH_BG_LIGHT : GRAPH_BG_DARK;
 
  function applyGraphTheme(){
    const light = document.body.classList.contains("gs-light");
    const S = (el, styles) => { if(!el) return; for(const k in styles){ el.style.setProperty(k, styles[k], "important"); } };
    const SS = (sel, styles) => parentElement.querySelectorAll(sel).forEach(el => S(el, styles));
    const panelEl = parentElement.querySelector("#panel");
    const legendEl = parentElement.querySelector("#legend");
    if (light) {
      // Match the dashboard sidebar: white surface, #f4f8fb inner boxes, dark text.
      S(panelEl, {background:"#ffffff", color:"#063142", border:"1px solid #d8e3ea", "box-shadow":"0 16px 40px rgba(6,49,66,.14)"});
      SS("#panel h3", {color:"#063142"});
      SS(".info-box", {background:"#f4f8fb", border:"1px solid #d8e3ea", "box-shadow":"inset 0 1px 0 rgba(255,255,255,.9)"});
      SS(".lbl", {color:"#4a6373"});
      SS(".val", {color:"#063142"});
      SS(".raw", {color:"#5a7180"});
      SS(".rh,.rl", {color:"#063142"});
      SS(".risk-pill", {background:"#e5eef3", color:"#0b3a4c", border:"1px solid #d0dde4", "box-shadow":"0 6px 16px rgba(6,49,66,.08)"});
      S(legendEl, {background:"#ffffff", color:"#063142", border:"1px solid #d8e3ea", "box-shadow":"0 12px 30px rgba(6,49,66,.12)", "--legend-title-color":"#063142"});
      SS("#legend > div", {color:"#063142"});
      SS(".legend-help", {color:"#4a6373"});
    } else {
      // Restore the original dark values.
      S(panelEl, {background:"rgba(58,79,89,1)", color:"#fff", border:"1px solid rgba(46,73,82,1)", "box-shadow":"0 24px 58px rgba(3,31,45,.28)"});
      SS("#panel h3", {color:"#fff"});
      SS(".info-box", {background:"rgba(8,50,64,.46)", border:"1px solid rgba(255,255,255,.10)", "box-shadow":"inset 0 1px 0 rgba(255,255,255,.035)"});
      SS(".lbl", {color:"rgba(255,255,255,.72)"});
      SS(".val", {color:"#fff"});
      SS(".raw", {color:"rgba(255,255,255,.63)"});
      SS(".rh,.rl", {color:"#fff"});
      SS(".risk-pill", {background:"#ffffffdb", color:"#08343f", border:"1px solid rgba(255,255,255,.28)", "box-shadow":"0 10px 24px rgba(3,31,45,.14)"});
      S(legendEl, {background:"rgba(58,79,89,1)", color:"#fff", border:"1px solid rgba(255,255,255,.14)", "box-shadow":"0 18px 40px rgba(3,31,45,.20)", "--legend-title-color":"#fff"});
      SS("#legend > div", {color:"#fff"});
      SS(".legend-help", {color:"rgba(255,255,255,.65)"});
    }
    const pc = parentElement.querySelector("#pc");
    if (pc && pc.__gsThemePc) pc.__gsThemePc();
    const g = parentElement.__graphShieldGraph;
    if (g) g.backgroundColor(graphBg());
  }
 
  function syncTheme(){
    let isLight = true;
    try { isLight = window.parent.document.body.classList.contains("gs-light"); } catch (e) {}
    document.body.classList.toggle("gs-light", isLight);
    document.body.classList.toggle("gs-dark", !isLight);
    applyGraphTheme();
 
    // 3d-force-graph injects its own "Left-click: rotate / Mouse-wheel: zoom / Right-click: pan"
    // hint directly into the DOM with a fixed text color. That color isn't theme-aware, so it
    // becomes unreadable against our dark background. Find it by its known text and recolor it
    // to match the active theme every time this runs.
    const navInfo = parentElement.querySelector(".scene-nav-info")
      || Array.from(graphEl.querySelectorAll("div")).find(el => (el.textContent || "").includes("Left-click"));
    if (navInfo) {
      const c = isLight ? "#083240" : "#1c2529";
      navInfo.style.setProperty("color", c, "important");
      navInfo.style.setProperty("background", graphBg(), "important");
      navInfo.style.setProperty("margin", "0", "important");
      navInfo.style.setProperty("width", "100%", "important");
      navInfo.style.setProperty("box-sizing", "border-box", "important");
      navInfo.querySelectorAll("*").forEach(el => el.style.setProperty("color", c, "important"));
    }
 
    // Keep the action buttons' rest colors in sync with the theme when the user
    // toggles light/dark. Skip a button that is currently hovered/focused so we
    // don't stomp its hover state mid-interaction.
    parentElement.querySelectorAll(".action-btn").forEach(b => {
      if (b.__gsApplyRest && !b.matches(":hover") && document.activeElement !== b) {
        b.__gsApplyRest();
      }
    });
 
    return isLight;
  }
  const isLightTheme = syncTheme();
  setInterval(syncTheme, 700);
 
  let hoverTooltip = parentElement.querySelector("#graph-hover-tooltip");
 
  if (!hoverTooltip) {
    hoverTooltip = document.createElement("div");
    hoverTooltip.id = "graph-hover-tooltip";
    hoverTooltip.style.position = "absolute";
    hoverTooltip.style.display = "none";
    hoverTooltip.style.pointerEvents = "none";
    hoverTooltip.style.zIndex = "30";
    hoverTooltip.style.padding = "6px 9px";
    hoverTooltip.style.borderRadius = "6px";
    hoverTooltip.style.background = "rgba(17, 21, 29, 0.96)";
    hoverTooltip.style.border = "1px solid #2b3140";
    hoverTooltip.style.color = "#f5f7fb";
    hoverTooltip.style.fontSize = "12px";
    hoverTooltip.style.whiteSpace = "nowrap";
    hoverTooltip.style.boxShadow = "0 6px 18px rgba(0, 0, 0, 0.24)";
    hoverTooltip.style.transform = "translate(12px, 12px)";
    parentElement.appendChild(hoverTooltip);
  }
 
  const positionHoverTooltip = event => {
    if (!hoverTooltip || hoverTooltip.style.display === "none") return;
 
    const rect = parentElement.getBoundingClientRect();
    hoverTooltip.style.left = `${event.clientX - rect.left}px`;
    hoverTooltip.style.top = `${event.clientY - rect.top}px`;
  };
 
  graphEl.addEventListener("mousemove", positionHoverTooltip);
 
  function fmtRisk(r){
    if(r===null||r===undefined)return"n/a";
    const pct=(Number(r)*100).toFixed(1)+"%";
    return Number(r)>=0.5?`<span class="rh">${pct}</span>`:`<span class="rl">${pct}</span>`;
  }
 
  function listOrNA(items){
    if(!Array.isArray(items) || items.length===0) return "n/a";
    return items.map(x=>`• ${escapeHtml(x)}`).join("<br>");
  }
 
  function hidePanel(){ panel.style.display="none"; }
 
  function nodePayload(n){
    return {txId:String(n.txId), group:n.group, node_index:n.id};
  }
 
  function showPanel(n){
    // panel.innerHTML below rebuilds the action buttons from scratch, which
    // wipes their inline hover styles and mouseenter listeners. CCv2 re-invokes
    // this render function on events like hover, so an unguarded rebuild
    // destroys the freshly-styled buttons before a hover can show -- that is why
    // the cream/lift hover never appeared. Rebuild ONLY when the shown node or
    // report state truly changed; otherwise leave the existing DOM (and its
    // hover state) untouched.
    const sig = [String(n.txId), reportError || "", reportDownloadToken || ""].join("|");
    if (panel.dataset.gsSig === sig && panel.style.display === "block") {
      return;
    }
    panel.dataset.gsSig = sig;
    panel.style.display="block";
    const label=n.group==="target"?"Target":(n.group==="neighbor"?"Neighbor":"Normal");
    const riskText = n.predicted_risk===null || n.predicted_risk===undefined
      ? "Risk n/a"
      : `${Number(n.predicted_risk)>=0.5?"High Risk":"Low Risk"} • ${(Number(n.predicted_risk)*100).toFixed(1)}%`;
    panel.innerHTML=`
      <button id="pc" aria-label="Close transaction details">✕</button>
      <div class="panel-top">
        <div class="panel-title-wrap"><h3>${escapeHtml(n.txId)}</h3></div>
        <div class="risk-pill">${escapeHtml(riskText)}</div>
      </div>
      <div class="info-grid">
        <div class="info-box"><div class="lbl">Transaction Type</div><div class="val">${escapeHtml(label)}</div></div>
        <div class="info-box"><div class="lbl">Prediction</div><div class="val">${escapeHtml(n.prediction || "n/a")}</div></div>
        <div class="info-box"><div class="lbl">True Label</div><div class="val">${escapeHtml(n.true_label || "n/a")}</div></div>
        <div class="info-box"><div class="lbl">Risk Score</div><div class="val">${fmtRisk(n.predicted_risk)}</div></div>
        <div class="info-box"><div class="lbl">Positive SHAP Features</div><div class="val">${escapeHtml(n.shap_increasing_cat || "n/a")}</div><div class="raw">${escapeHtml(n.shap_increasing_raw || "")}</div></div>
        <div class="info-box"><div class="lbl">Negative SHAP Features</div><div class="val">${escapeHtml(n.shap_decreasing_cat || "n/a")}</div><div class="raw">${escapeHtml(n.shap_decreasing_raw || "")}</div></div>
        <div class="info-box wide"><div class="lbl">GNN Importance</div><div class="val">${Number(n.gnn_importance || 0).toFixed(4)}</div></div>
        <div class="info-box"><div class="lbl">Transaction Profile Factors</div><div class="val">${listOrNA(n.transaction_profile_factors)}</div></div>
        <div class="info-box"><div class="lbl">Network Context Factors</div><div class="val">${listOrNA(n.network_context_factors)}</div></div>
      </div>
      <div class="actions">
        <button id="analyze-btn" class="action-btn primary">Analyze Transaction</button>
        <button id="report-btn" class="action-btn">Generate Report</button>
      </div>
      ${reportError && selectedTxId === String(n.txId) ? `<div class="report-error">⚠️ ${escapeHtml(reportError)}</div>` : ""}`;
 
    panel.querySelector("#pc").onclick = e => { e.stopPropagation(); hidePanel(); };
 
    // Theme-aware close (X) chip. It is injected via innerHTML, so its colors are
    // driven from JS (like the action buttons) rather than the component css=.
    (function themeClose(){
      const pc = panel.querySelector("#pc");
      if (!pc) return;
      const s = (p, v) => pc.style.setProperty(p, v, "important");
      const paint = hover => {
        const light = document.body.classList.contains("gs-light");
        if (light) {
          s("border", "1px solid #cfdde5");
          s("color", "#063142");
          s("background", hover ? "#e0ebf1" : "#eef4f7");
        } else {
          s("border", "1px solid rgba(255,255,255,.22)");
          s("color", hover ? "#fff" : "rgba(255,255,255,.92)");
          s("background", hover ? "rgba(255,255,255,.12)" : "rgba(8,50,64,.55)");
        }
      };
      paint(false);
      pc.addEventListener("mouseenter", () => paint(true));
      pc.addEventListener("mouseleave", () => paint(false));
      pc.__gsThemePc = () => paint(false);
    })();
 
    // The component css= scoping does NOT reach these buttons because they are
    // injected via innerHTML after mount. So we style them from JS with inline
    // !important, which wins over any stylesheet and any CCv2 scoping. Rest =
    // dark translucent + white text; hover = cream + navy + slight lift.
    (function styleActionButtons() {
      const set = (el, prop, val) => el.style.setProperty(prop, val, "important");
      panel.querySelectorAll(".action-btn").forEach(btn => {
        // Base look (independent of any stylesheet).
        set(btn, "min-height", "52px");
        set(btn, "padding", "11px 12px");
        set(btn, "border-radius", "18px");
        set(btn, "border", "1px solid rgba(255,255,255,.14)");
        set(btn, "background-image", "none");
        set(btn, "font-weight", "700");
        set(btn, "font-size", "12px");
        set(btn, "white-space", "normal");
        set(btn, "transition",
          "background-color .18s ease,color .18s ease,transform .18s ease,border-color .18s ease,box-shadow .18s ease");
 
        const applyRest = () => {
          const light = document.body.classList.contains("gs-light");
          if (btn.disabled) {
            if (light) {
              set(btn, "background-color", "#e9eff3");
              set(btn, "color", "#9db2bd");
              set(btn, "-webkit-text-fill-color", "#9db2bd");
              set(btn, "border-color", "#dbe6ec");
            } else {
              set(btn, "background-color", "rgba(255,255,255,.10)");
              set(btn, "color", "#eaf3f7");
              set(btn, "-webkit-text-fill-color", "#eaf3f7");
              set(btn, "border-color", "rgba(255,255,255,.14)");
            }
            set(btn, "transform", "none");
            set(btn, "box-shadow", "none");
            set(btn, "cursor", "not-allowed");
            return;
          }
          if (light) {
            set(btn, "background-color", "#eef4f7");
            set(btn, "color", "#063142");
            set(btn, "-webkit-text-fill-color", "#063142");
            set(btn, "border-color", "#d8e3ea");
          } else {
            set(btn, "background-color", "rgba(255,255,255,.06)");
            set(btn, "color", "#fff");
            set(btn, "-webkit-text-fill-color", "#fff");
            set(btn, "border-color", "rgba(255,255,255,.14)");
          }
          set(btn, "transform", "none");
          set(btn, "box-shadow", "none");
          set(btn, "cursor", "pointer");
        };
        const applyHover = () => {
          if (btn.disabled) return;
          const light = document.body.classList.contains("gs-light");
          if (light) {
            set(btn, "background-color", "#e4edf2");
            set(btn, "color", "#063142");
            set(btn, "-webkit-text-fill-color", "#063142");
            set(btn, "border-color", "#cfdde5");
            set(btn, "transform", "translateY(-2px)");
            set(btn, "box-shadow", "0 8px 18px rgba(6,49,66,.12)");
          } else {
            set(btn, "background-color", "#ffffffdb");   // cream
            set(btn, "color", "#083240");                // dark navy
            set(btn, "-webkit-text-fill-color", "#083240");
            set(btn, "border-color", "rgba(255,255,255,.28)");
            set(btn, "transform", "translateY(-2px)");   // lift
            set(btn, "box-shadow", "0 12px 24px rgba(3,31,45,.15)");
          }
        };
 
        applyRest();
        btn.addEventListener("mouseenter", applyHover);
        btn.addEventListener("mouseleave", applyRest);
        btn.addEventListener("focus", applyHover);
        btn.addEventListener("blur", applyRest);
        btn.__gsApplyRest = applyRest;  // so disabled-state changes can refresh
      });
    })();
 
    // Panel content was just injected; theme its surfaces/text immediately.
    applyGraphTheme();
 
    function resetAnalyzeButton() {
      const analyzeBtn = panel.querySelector("#analyze-btn");
      const reportBtn = panel.querySelector("#report-btn");
 
      if (analyzeBtn) {
        analyzeBtn.textContent = "Analyze Transaction";
        analyzeBtn.disabled = false;
      }
 
      if (reportBtn) {
        reportBtn.disabled = false;
      }
    }
 
    function waitForInvestigationSidebar() {
      try {
        const parentDoc = window.parent.document;
 
        const existingSidebar =
          parentDoc.querySelector(".st-key-investigation_sidebar");
 
        if (existingSidebar) {
          resetAnalyzeButton();
          return;
        }
 
        const observer = new MutationObserver(() => {
          const sidebar =
            parentDoc.querySelector(".st-key-investigation_sidebar");
 
          if (sidebar) {
            resetAnalyzeButton();
            observer.disconnect();
          }
        });
 
        observer.observe(parentDoc.body, {
          childList: true,
          subtree: true
        });
      } catch (err) {
        console.warn(
          "[ANALYSIS][GRAPH] sidebar observer setup failed",
          err
        );
 
        resetAnalyzeButton();
      }
    }
 
    panel.querySelector("#analyze-btn").onclick = e => {
      e.stopPropagation();
 
      const b = e.currentTarget;
      const reportBtn = panel.querySelector("#report-btn");
 
      if (b.disabled) {
        return;
      }
 
      b.textContent = "⏳ Opening analysis…";
      b.disabled = true;
 
      if (reportBtn) {
        reportBtn.disabled = true;
      }
 
      waitForInvestigationSidebar();
 
      setTriggerValue(
        "analyze_transaction",
        nodePayload(n)
      );
    };
    panel.querySelector("#report-btn").onclick = e => {
      e.stopPropagation();
      const b = e.currentTarget;
      b.textContent = "⏳ Preparing report…";
      b.disabled = true;
      panel.querySelector("#analyze-btn").disabled = true;
      setTriggerValue("generate_report", nodePayload(n));
    };
  }
 
  function downloadReportOnce() {
    console.log("[REPORT][GRAPH] downloadReportOnce called");
 
    if (!reportPdfBase64) {
      console.log("[REPORT][GRAPH] download skipped: no PDF data");
      return;
    }
    if (!reportDownloadToken) {
      console.error("[REPORT][GRAPH] download skipped: missing report_download_token");
      return;
    }
    if (!reportTxId) {
      console.error("[REPORT][GRAPH] download skipped: missing report_txid");
      return;
    }
 
    const storageKey = "graphshield_report_download_token";
    const previousToken = sessionStorage.getItem(storageKey);
    if (previousToken === reportDownloadToken) {
      console.log("[REPORT][GRAPH] download skipped: token already downloaded", reportDownloadToken);
      return;
    }
 
    try {
      console.log("[REPORT][GRAPH] decoding PDF", {
        txid: reportTxId,
        filename: reportFilename,
        token: reportDownloadToken,
        base64Length: reportPdfBase64.length
      });
 
      const binary = atob(reportPdfBase64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
 
      const blob = new Blob([bytes], {type: "application/pdf"});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = reportFilename || "GraphShield_Report.pdf";
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      a.remove();
 
      sessionStorage.setItem(storageKey, reportDownloadToken);
      console.log("[REPORT][GRAPH] download triggered successfully", {
        filename: a.download,
        byteLength: bytes.length,
        token: reportDownloadToken
      });
 
      setTimeout(() => URL.revokeObjectURL(url), 3000);
    } catch (err) {
      console.error("[REPORT][GRAPH] download failed", err);
    }
  }
 
  downloadReportOnce();
 
  let G = parentElement.__graphShieldGraph;
  if (!G) {
    G = ForceGraph3D()(graphEl)
      .backgroundColor(graphBg())
      .nodeLabel(() => "")
      .nodeColor(n=>n.group==="target"?"#ff4d4d":n.group==="neighbor"?"#f6cfc7":"#b9d7e3")
      .nodeVal(n=>n.group==="target"?14:3+9*Number(n.gnn_importance || 0))
      .linkWidth(l=>0.5+5*Number(l.importance || 0))
      .linkColor(() => "rgba(255,255,255,0.25)")
      .linkDirectionalParticles(1)
      .linkDirectionalParticleWidth(l=>1+2*Number(l.importance || 0))
      // Let the simulation run its natural cooldown once on initial load,
      // then it settles on its own (default cooldownTicks). We do NOT set
      // cooldownTicks(0) here, so the very first layout still animates in.
      .onEngineStop(() => { parentElement.__graphShieldSettled = true; });
    parentElement.__graphShieldGraph = G;
  }
  G.backgroundColor(graphBg());
  G.height(height);
  G.width(graphEl.clientWidth || parentElement.clientWidth || window.innerWidth);
 
 
  // graphData(...) is NOT a passive setter -- calling it tells 3d-force-graph
  // the data changed, which reheats/restarts the force simulation, even if the
  // data is identical. Streamlit's V2 component can re-invoke this render
  // function on events like hover, so calling graphData() unconditionally on
  // every invocation was re-triggering the simulation on every hover -- that
  // reheat is what produced the "jump/push up" feeling. Guard it behind a
  // hash of the actual data so it only runs when the graph truly changed.
  const graphHash = JSON.stringify(graphData);
  if (parentElement.__graphShieldHash !== graphHash) {
    parentElement.__graphShieldHash = graphHash;
    G.graphData(graphData);
    // Once the simulation has already settled once before (e.g. a filter
    // change after the initial load), don't let a data refresh reheat it
    // into a long-running re-simulation -- resolve it near-instantly instead.
    if (parentElement.__graphShieldSettled) {
      G.cooldownTicks(0);
    }
  }
 
  // Interaction handlers are cheap to (re)bind and are NOT the reheat source;
  // rebinding them on every invocation is safe and keeps closures fresh.
  G.onNodeClick(n=>{
      showPanel(n);
      setTriggerValue("node_clicked", nodePayload(n));
      const norm=Math.hypot(n.x||0,n.y||0,n.z||0) || 1;
      const dist=80, r=1+dist/norm;
      G.cameraPosition({x:(n.x||0)*r,y:(n.y||0)*r,z:(n.z||0)*r},n,800);
    })
    .onNodeHover(n=>{
      graphEl.style.cursor = n ? "pointer" : "default";
 
      if (!hoverTooltip) return;
 
      if (n) {
        const group = String(n.group || "").toUpperCase();
        const txId = String(n.txId ?? n.id ?? "");
 
        hoverTooltip.textContent =
          group && txId
            ? `${group} · ${txId}`
            : (txId || group);
 
        hoverTooltip.style.display = "block";
      } else {
        hoverTooltip.style.display = "none";
      }
    })
    .onBackgroundClick(()=>{
      hidePanel();
      graphEl.style.cursor="default";
 
      if (hoverTooltip) {
        hoverTooltip.style.display = "none";
      }
    });
 
  if (selectedTxId) {
    const selectedNode = graphData.nodes.find(n => String(n.txId) === selectedTxId);
    if (selectedNode) showPanel(selectedNode);
  }
}
"""
 
_component = st.components.v2.component(
    "graphshields_force_graph_v7",
    html=_HTML,
    css=_CSS,
    js=_JS,
)
 
 
def render_graph(
    graph_data_3d: dict,
    height: int = 720,
    key: str = "force_graph_3d",
    selected_txid: str | None = None,
):
    """Render the graph and return discrete component events.
 
    Returns a dict with optional ``node_clicked`` and ``analyze_transaction``
    payloads. Trigger callbacks are registered explicitly so the attributes are
    always present on the V2 ComponentResult.
    """
    # Read report state directly from Streamlit. This keeps the public
    # render_graph() call unchanged while allowing the graph card to switch
    # while keeping the card button labeled Generate Report; the PDF downloads
    # automatically once after report generation succeeds.
    report_pdf_bytes = st.session_state.get("report_pdf_bytes")
    report_filename = st.session_state.get("report_filename")
    report_txid = st.session_state.get("report_txid")
    report_error = st.session_state.get("report_error")
    report_download_token = st.session_state.get("report_download_token")
 
    print(
        "[REPORT][GRAPH] render state | "
        f"selected_txid={selected_txid} | report_txid={report_txid} | "
        f"has_pdf={bool(report_pdf_bytes)} | bytes={len(report_pdf_bytes) if report_pdf_bytes else 0} | "
        f"filename={report_filename} | token={report_download_token} | error={report_error}"
    )
 
    result = _component(
        data={
            "graph_data": graph_data_3d,
            "height": height,
            "selected_txid": selected_txid,
            "report_pdf_base64": (
                base64.b64encode(report_pdf_bytes).decode("ascii")
                if report_pdf_bytes
                else None
            ),
            "report_filename": report_filename,
            "report_txid": report_txid,
            "report_error": report_error,
            "report_download_token": report_download_token,
        },
        on_node_clicked_change=lambda: None,
        on_analyze_transaction_change=lambda: None,
        on_generate_report_change=lambda: None,
        key=key,
    )
    if result is None:
        return {"node_clicked": None, "analyze_transaction": None, "generate_report": None}
    return {
        "node_clicked": getattr(result, "node_clicked", None),
        "analyze_transaction": getattr(result, "analyze_transaction", None),
        "generate_report": getattr(result, "generate_report", None),
    }