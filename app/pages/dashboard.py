"""GraphShield investigation workspace.

The ForceGraph3D component remains the main visualization. Node details and
Analyze action live in the in-graph card; LLM investigation content lives in a
fixed left workspace panel.
"""

import json
import os
import sys
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
_BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(_BACKEND_ROOT))



from app.components.data_loader import load_all
from app.components.graph_builder import build_graph_data
from app.components.graph_viewer import render_graph
from app.components.report_history import render_report_history
from security.validation import ValidationError
from services.llm_service import generate_explanation, generate_explanation_stream
from services.transaction_service import SelectedNode, build_context
from utils.cache import executive_summary_cache
from services import firebase_services, report_service

st.set_page_config(
    page_title="Investigation Workspace — GraphShield",
    layout="wide",
    page_icon="🕵️",
)

st.markdown(
    """
<style>
.st-key-investigation_sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: min(430px, 92vw);
    height: 100vh;
    box-sizing: border-box;
    background: #12151c;
    border-right: 1px solid #2a2f3a;
    z-index: 999999;
    overflow-y: auto;
    padding: 18px 18px 28px 18px;
    box-shadow: 4px 0 24px rgba(0,0,0,.45);
}
.st-key-investigation_response_area {
    background: #1a1e28;
    border: 1px solid #2a3040;
    border-radius: 10px;
    padding: 14px 16px;
    margin: 8px 0 16px 0;
    min-height: 130px;
    font-size: 14px;
    line-height: 1.6;
}
.error-box {
    background: #3a1f1f;
    border: 1px solid #7a3a3a;
    border-radius: 8px;
    padding: 12px 14px;
    color: #ffb0b0;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("🕵️ Investigation Workspace")
print(f"[SCRIPT] full rerun at {time.strftime('%H:%M:%S')}.{int(time.time()*1000)%1000:03d}")
d = load_all()

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

st.session_state.setdefault("selected_node", None)
st.session_state.setdefault("sidebar_open", False)
st.session_state.setdefault("initial_analysis_text", None)
st.session_state.setdefault("initial_analysis_error", None)
st.session_state.setdefault("initial_analysis_pending", False)
st.session_state.setdefault("question_answer_text", None)
st.session_state.setdefault("question_error", None)
st.session_state.setdefault("question_pending_id", None)
st.session_state.setdefault("graph_cache_key", None)
st.session_state.setdefault("graph_cache_value", None)
st.session_state.setdefault("report_pdf_bytes", None)
st.session_state.setdefault("report_filename", None)
st.session_state.setdefault("report_txid", None)
st.session_state.setdefault("report_error", None)
st.session_state.setdefault("report_download_token", None)
st.session_state.setdefault("report_storage_error", None)
st.session_state.setdefault("active_run_token", None)


@st.cache_resource
def _analysis_runtime():
    """
    Process-lifetime background runtime shared across Streamlit reruns.

    The worker never touches st.session_state. It writes only to this
    thread-safe registry, while the UI fragment polls the registry.
    """
    return {
        "executor": ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="graphshield-analysis",
        ),
        "jobs": {},
        "lock": threading.RLock(),
    }


def _analysis_job_key(session_id: str, txid: str) -> tuple[str, str]:
    return (str(session_id), str(txid))


def _get_analysis_job(session_id: str, txid: str) -> dict | None:
    runtime = _analysis_runtime()
    key = _analysis_job_key(session_id, txid)

    with runtime["lock"]:
        job = runtime["jobs"].get(key)
        return dict(job) if job is not None else None


def _update_analysis_job(
    session_id: str,
    txid: str,
    **changes,
) -> None:
    runtime = _analysis_runtime()
    key = _analysis_job_key(session_id, txid)

    with runtime["lock"]:
        job = runtime["jobs"].setdefault(
            key,
            {
                "status": "running",
                "partial_text": "",
                "final_text": None,
                "error": None,
                "started_at": time.time(),
                "finished_at": None,
            },
        )
        job.update(changes)


def _analysis_worker(
    session_id: str,
    selected: dict,
) -> None:
    """
    Run the initial-analysis LLM stream outside Streamlit's UI execution.

    Closing the panel does not cancel this worker. The stream is fully consumed,
    so llm_service stores the final Executive Summary in
    executive_summary_cache exactly as before.
    """
    txid = str(selected["txId"])
    started = time.perf_counter()
    accumulated = ""

    try:
        context = build_context(
            txid,
            _build_selected_node_obj(selected),
        )

        for chunk in generate_explanation_stream(
            context,
            request_type="initial_analysis",
            session_id=session_id,
        ):
            accumulated += chunk
            _update_analysis_job(
                session_id,
                txid,
                status="running",
                partial_text=accumulated,
            )

        _update_analysis_job(
            session_id,
            txid,
            status="done",
            partial_text=accumulated,
            final_text=accumulated,
            error=None,
            finished_at=time.time(),
        )

        print(
            f"[ANALYSIS][BG] completed | "
            f"txid={txid} | chars={len(accumulated)} | "
            f"elapsed={time.perf_counter() - started:.3f}s"
        )

    except ValidationError:
        message = (
            "This transaction could not be analyzed because the request did "
            "not pass validation. Please select a valid transaction and try again."
        )
        _update_analysis_job(
            session_id,
            txid,
            status="error",
            error=message,
            finished_at=time.time(),
        )
        print(
            f"[ANALYSIS][BG] validation failed | txid={txid}"
        )

    except Exception as exc:
        message = "The analysis request failed unexpectedly. Please try again."
        _update_analysis_job(
            session_id,
            txid,
            status="error",
            error=message,
            finished_at=time.time(),
        )
        print(
            f"[ANALYSIS][BG] failed | txid={txid} | "
            f"{type(exc).__name__}: {exc}"
        )


def _ensure_initial_analysis_job(
    session_id: str,
    selected: dict,
) -> str:
    """
    Ensure exactly one initial-analysis job exists for this session+transaction.

    Returns one of: "cached", "running", "done", "error", "started".
    """
    txid = str(selected["txId"])

    cached = executive_summary_cache.get(session_id, txid)
    if cached is not None:
        _update_analysis_job(
            session_id,
            txid,
            status="done",
            partial_text=cached,
            final_text=cached,
            error=None,
            finished_at=time.time(),
        )
        return "cached"

    existing = _get_analysis_job(session_id, txid)
    if existing is not None:
        status = str(existing.get("status") or "")
        if status in {"running", "done", "error"}:
            return status

    _update_analysis_job(
        session_id,
        txid,
        status="running",
        partial_text="",
        final_text=None,
        error=None,
        started_at=time.time(),
        finished_at=None,
    )

    runtime = _analysis_runtime()
    runtime["executor"].submit(
        _analysis_worker,
        str(session_id),
        dict(selected),
    )

    print(
        f"[ANALYSIS][BG] started | "
        f"txid={txid} | session_id={session_id}"
    )
    return "started"


def _reset_investigation_state():
    st.session_state.initial_analysis_text = None
    st.session_state.initial_analysis_error = None
    st.session_state.initial_analysis_pending = False
    st.session_state.question_answer_text = None
    st.session_state.question_error = None
    st.session_state.question_pending_id = None
    # Invalidate any stream still running for the transaction being left --
    # it will see the mismatch on its next chunk and abandon cleanly instead
    # of writing its result into the newly-selected transaction's panel.
    st.session_state.active_run_token = None


def _select_node(payload: dict | None):
    if not payload:
        return
    previous_txid = (st.session_state.selected_node or {}).get("txId")
    st.session_state.selected_node = payload
    if payload.get("txId") != previous_txid:
        _reset_investigation_state()


def _build_selected_node_obj(selected: dict) -> SelectedNode:
    return SelectedNode(
        node_index=selected.get("node_index"),
        txId=str(selected["txId"]),
    )


def _run_initial_analysis_streaming(selected: dict, placeholder, run_token: str) -> None:
    """Streams the initial analysis into `placeholder`, writing text as it
    arrives instead of blocking silently. This is the standard fix for
    reasoning-model latency: total wait time is unchanged, but the user sees
    live progress instead of a frozen button.

    Cancellation: `run_token` is a unique id stamped by the caller when this
    request started. On every chunk we check it against
    st.session_state.active_run_token -- if they no longer match (the user
    closed the panel or switched transactions while this was still running
    on the server), we stop writing to session_state and to the placeholder
    and return immediately. Without this, an abandoned stream keeps running
    to completion, writes its result late, and reopens/repopulates a panel
    the user already closed or moved away from.
    """
    started = time.perf_counter()
    accumulated = ""
    try:
        context = build_context(selected["txId"], _build_selected_node_obj(selected))
        for chunk in generate_explanation_stream(
            context,
            request_type="initial_analysis",
            session_id=st.session_state.session_id,
        ):
            if st.session_state.get("active_run_token") != run_token:
                print(f"[STREAM] initial_analysis abandoned (stale token) tx={selected.get('txId')}")
                return  # abandoned: do not write partial/final result anywhere
            accumulated += chunk
            placeholder.markdown(accumulated + " ▌")  # cursor while still streaming

        if st.session_state.get("active_run_token") != run_token:
            print(f"[STREAM] initial_analysis finished but abandoned tx={selected.get('txId')}")
            return

        placeholder.markdown(accumulated)
        st.session_state.initial_analysis_text = accumulated
        st.session_state.initial_analysis_error = None
    except ValidationError:
        if st.session_state.get("active_run_token") == run_token:
            st.session_state.initial_analysis_error = (
                "This transaction could not be analyzed because the request did not pass validation. "
                "Please select a valid transaction and try again."
            )
    except Exception:
        if st.session_state.get("active_run_token") == run_token:
            st.session_state.initial_analysis_error = (
                "The analysis request failed unexpectedly. Please try again."
            )
    finally:
        if st.session_state.get("active_run_token") == run_token:
            st.session_state.initial_analysis_pending = False
        print(f"[PERF] initial_analysis total: {time.perf_counter() - started:.3f}s")


def _run_question_streaming(selected: dict, question_id: str, placeholder, run_token: str) -> None:
    """Streaming counterpart to _run_initial_analysis_streaming. See its
    docstring for the cancellation mechanism (run_token)."""
    started = time.perf_counter()
    accumulated = ""
    try:
        context = build_context(selected["txId"], _build_selected_node_obj(selected))
        for chunk in generate_explanation_stream(
            context,
            request_type="question",
            question_id=question_id,
            session_id=st.session_state.session_id,
        ):
            if st.session_state.get("active_run_token") != run_token:
                print(f"[STREAM] {question_id} abandoned (stale token) tx={selected.get('txId')}")
                return
            accumulated += chunk
            placeholder.markdown(accumulated + " ▌")

        if st.session_state.get("active_run_token") != run_token:
            print(f"[STREAM] {question_id} finished but abandoned tx={selected.get('txId')}")
            return

        placeholder.markdown(accumulated)
        st.session_state.question_answer_text = accumulated
        st.session_state.question_error = None
    except ValidationError:
        if st.session_state.get("active_run_token") == run_token:
            st.session_state.question_error = (
                "This question could not be answered because the request did not pass validation."
            )
    except Exception:
        if st.session_state.get("active_run_token") == run_token:
            st.session_state.question_error = (
                "The question request failed unexpectedly. Please try again."
            )
    finally:
        if st.session_state.get("active_run_token") == run_token:
            st.session_state.question_pending_id = None
        print(f"[PERF] {question_id} total: {time.perf_counter() - started:.3f}s")


SUGGESTED_QUESTIONS = [
    ("question_1", "Which transaction characteristics contributed most to this prediction?"),
    ("question_2", "How did neighboring transactions influence this prediction?"),
    ("question_3", "Which evidence reduced the estimated risk?"),
]

# 1. Graph controls
with st.expander("⚙️ Graph Settings", expanded=False):
    col1, col2, col3 = st.columns(3)
    top_n = col1.slider("Target Transactions", 5, 30, 15)
    max_nb = col2.slider("Maximum Neighbors per Target", 10, 40, 25)
    num_norm = col3.slider("Normal Nodes", 5, 20, 10)

pred_df_filtered = d["pred_df"].copy()


# 3. Graph data memoization: rebuild only when controls or filters change.
graph_cache_key = (
    top_n,
    max_nb,
    num_norm,
)


if st.session_state.graph_cache_key != graph_cache_key:
    started = time.perf_counter()
    st.session_state.graph_cache_value = build_graph_data(
        pred_df=pred_df_filtered,
        edge_np=d["edge_np"],
        node_to_tx=d["node_to_tx"],
        tx_to_node=d["tx_to_node"],
        risk_by_txid=d["risk_by_txid"],
        shap_by_txid=d["shap_by_txid"],
        gnn_edge_imp=d["gnn_edge_imp"],
        gnn_node_imp=d["gnn_node_imp"],
        top_n_targets=top_n,
        max_neighbors=max_nb,
        num_normal=num_norm,
    )
    st.session_state.graph_cache_key = graph_cache_key
    print(f"[PERF] build_graph_data: {time.perf_counter() - started:.3f}s")

graph_data = st.session_state.graph_cache_value

st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

st.caption(
    f"Showing {len(graph_data['nodes'])} nodes · {len(graph_data['links'])} edges · click any node to investigate"
)

events = render_graph(
    graph_data,
    height=650,
    selected_txid=(st.session_state.selected_node or {}).get("txId"),
)

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

# Node selection remains independent from analysis. A node switch clears stale
# investigation content but never calls Azure automatically.
_select_node(events.get("node_clicked"))

analyze_request = events.get("analyze_transaction")
if analyze_request:
    _select_node(analyze_request)
    st.session_state.sidebar_open = True

    txid = str(st.session_state.selected_node["txId"])
    job_state = _ensure_initial_analysis_job(
        st.session_state.session_id,
        st.session_state.selected_node,
    )

    job = _get_analysis_job(
        st.session_state.session_id,
        txid,
    )

    if job_state in {"cached", "done"} and job:
        st.session_state.initial_analysis_text = job.get("final_text")
        st.session_state.initial_analysis_error = None
        st.session_state.initial_analysis_pending = False

    elif job_state == "error" and job:
        st.session_state.initial_analysis_text = None
        st.session_state.initial_analysis_error = job.get("error")
        st.session_state.initial_analysis_pending = False

    else:
        st.session_state.initial_analysis_text = None
        st.session_state.initial_analysis_error = None
        st.session_state.initial_analysis_pending = True

    st.rerun()

report_request = events.get("generate_report")
if report_request:
    print(f"[REPORT] generate_report event received: {report_request}")
    _select_node(report_request)
    txid = str(st.session_state.selected_node["txId"])
    print(f"[REPORT] generation starting | txid={txid} | session_id={st.session_state.session_id}")
    try:
        with st.spinner("Preparing report…"):
            pdf_bytes, filename = report_service.generate_report(
                st.session_state.session_id, st.session_state.selected_node
            )

        if not pdf_bytes:
            raise ValueError("report_service.generate_report returned empty PDF bytes")

        st.session_state.report_pdf_bytes = pdf_bytes
        st.session_state.report_filename = filename
        st.session_state.report_txid = txid
        st.session_state.report_error = None

        # Persist the generated PDF and its metadata. Firebase failure does not
        # block the user's immediate download; it is surfaced separately below.
        try:
            firebase_record = firebase_services.save_report(
                pdf_bytes=pdf_bytes,
                filename=filename,
                transaction_id=txid,
                status="Under Investigation",
            )
            st.session_state.report_storage_error = None
            print(
                f"[REPORT] Firebase save success | txid={txid} "
                f"| doc_id={firebase_record['document_id']} "
                f"| storage_path={firebase_record['storage_path']}"
            )
        except Exception as firebase_exc:
            st.session_state.report_storage_error = (
                "The report was generated and downloaded, but it could not be saved "
                "to Report History. Check the Firebase configuration and try again."
            )
            print(
                f"[REPORT] Firebase save failed | txid={txid} "
                f"| {type(firebase_exc).__name__}: {firebase_exc}"
            )
            import traceback
            traceback.print_exc()

        # New token on every successful generation. The graph component uses it
        # to auto-download exactly once after Streamlit reruns with the PDF data.
        st.session_state.report_download_token = uuid.uuid4().hex

        print(
            f"[REPORT] generation success | txid={txid} | filename={filename} "
            f"| bytes={len(pdf_bytes)} | token={st.session_state.report_download_token}"
        )
        st.rerun()
    except Exception as exc:
        import traceback

        st.session_state.report_pdf_bytes = None
        st.session_state.report_filename = None
        st.session_state.report_txid = None
        st.session_state.report_download_token = None
        st.session_state.report_error = "Could not generate the report. Please try again."
        print(f"[REPORT] generation failed | txid={txid} | {type(exc).__name__}: {exc}")
        traceback.print_exc()
        st.rerun()

if st.session_state.selected_node is None:
    st.info("Click a node in the graph to open its transaction details card.")

# 4/5. Investigation sidebar as a PLAIN fragment (no run_every, no threads).
# Clicking Close or a question button now reruns only this fragment --
# render_graph above is never re-executed by these clicks, which removes the
# 3D graph re-render cost from them. st.rerun() called from inside a fragment
# is automatically scoped to the fragment, not the full app.
_panel_poll_interval = (
    0.5
    if (
        st.session_state.sidebar_open
        and st.session_state.initial_analysis_pending
    )
    else None
)


@st.fragment(run_every=_panel_poll_interval)
def investigation_panel():
    print(
        f"[PANEL] enter | sidebar_open={st.session_state.sidebar_open} "
        f"| selected_txid={(st.session_state.selected_node or {}).get('txId')} "
        f"| pending={st.session_state.initial_analysis_pending} "
        f"| has_text={st.session_state.initial_analysis_text is not None} "
        f"| token={st.session_state.active_run_token}"
    )
    if not (st.session_state.sidebar_open and st.session_state.selected_node is not None):
        return

    selected = st.session_state.selected_node
    selected_txid = str(selected["txId"])

    # Synchronize UI state from the background job registry. This is read-only
    # from the worker's perspective; the worker never touches st.session_state.
    analysis_job = _get_analysis_job(
        st.session_state.session_id,
        selected_txid,
    )

    if analysis_job is not None:
        analysis_status = analysis_job.get("status")

        if analysis_status == "done":
            st.session_state.initial_analysis_text = analysis_job.get("final_text")
            st.session_state.initial_analysis_error = None
            st.session_state.initial_analysis_pending = False

        elif analysis_status == "error":
            st.session_state.initial_analysis_text = None
            st.session_state.initial_analysis_error = analysis_job.get("error")
            st.session_state.initial_analysis_pending = False

        elif analysis_status == "running":
            st.session_state.initial_analysis_pending = True

    with st.container(key="investigation_sidebar"):
        hcol1, hcol2 = st.columns([4, 1])
        hcol1.markdown(f"### 🔎 Transaction {selected['txId']}")
        if hcol2.button("✕", key="close_sidebar", help="Close investigation panel"):
            # Close the UI only. The initial-analysis worker keeps running in
            # the background and will save its completed result in the shared
            # Executive Summary cache. Reopening the same transaction reuses
            # that running job or its cached final result instead of starting
            # another LLM request.
            st.session_state.sidebar_open = False
            st.session_state.question_pending_id = None
            st.session_state.active_run_token = None
            st.rerun()

        st.markdown("**Investigation Response**")
        with st.container(key="investigation_response_area"):
            response_placeholder = st.empty()

            if st.session_state.question_pending_id is not None:
                # Stream directly into the placeholder now, in this same pass,
                # so text appears live instead of a silent block-then-rerun.
                response_placeholder.markdown("⏳ Answering the selected question...")
                _run_question_streaming(
                    selected,
                    st.session_state.question_pending_id,
                    response_placeholder,
                    st.session_state.active_run_token,
                )
            elif st.session_state.question_error:
                response_placeholder.markdown(
                    f'<div class="error-box">⚠️ {st.session_state.question_error}</div>',
                    unsafe_allow_html=True,
                )
            elif st.session_state.question_answer_text:
                response_placeholder.markdown(st.session_state.question_answer_text)
            elif st.session_state.initial_analysis_pending:
                if analysis_job and analysis_job.get("partial_text"):
                    response_placeholder.markdown(
                        analysis_job["partial_text"] + " ▌"
                    )
                else:
                    response_placeholder.markdown(
                        "⏳ Running initial analysis..."
                    )
            elif st.session_state.initial_analysis_error:
                response_placeholder.markdown(
                    f'<div class="error-box">⚠️ {st.session_state.initial_analysis_error}</div>',
                    unsafe_allow_html=True,
                )
            elif st.session_state.initial_analysis_text:
                response_placeholder.markdown(st.session_state.initial_analysis_text)
            else:
                response_placeholder.caption("No analysis is available yet.")

        st.markdown("**Suggested Questions**")
        questions_locked = (
            st.session_state.initial_analysis_text is None
            or st.session_state.initial_analysis_pending
            or st.session_state.question_pending_id is not None
        )

        for q_id, q_text in SUGGESTED_QUESTIONS:
            if st.button(
                q_text,
                key=f"btn_{q_id}",
                disabled=questions_locked,
                use_container_width=True,
            ):
                st.session_state.question_pending_id = q_id
                st.session_state.question_answer_text = None
                st.session_state.question_error = None
                # Fresh token: invalidates any stream still finishing from a
                # previous question/analysis so it abandons instead of landing
                # its result in the wrong place later.
                st.session_state.active_run_token = uuid.uuid4().hex
                st.rerun()

investigation_panel()




# 6. Shared Report History. With no login system, all saved reports are shown.
render_report_history(storage_error=st.session_state.report_storage_error)