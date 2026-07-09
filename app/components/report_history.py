"""Streamlit UI for the shared GraphShield report history."""

from __future__ import annotations

from datetime import date, datetime
from html import escape

import streamlit as st

from services import firebase_services


_HISTORY_CSS = """
<style>
.report-history-toolbar {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin: 0 0 12px 0;
}

/* Keep the date widget compact on the right without an extra popover wrapper. */
[class*="st-key-report_history_date_wrap"] {
    max-width: 310px;
    margin-left: auto;
}

.report-history-card {
    position: relative;
    width: 100%;
    box-sizing: border-box;
    background: #171b24;
    border: 1px solid #2b3140;
    border-radius: 12px;
    padding: 18px 64px 16px 18px;
    margin: 12px 0;
    overflow: visible;
}

.report-history-id {
    font-size: 16px;
    font-weight: 700;
    color: #f5f7fb;
    margin: 0 0 8px 0;
}

.report-history-meta {
    color: #aab2c0;
    font-size: 13px;
    line-height: 1.7;
    margin: 0;
}

.report-history-status {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 999px;
    background: #262d3b;
    border: 1px solid #3a4356;
    color: #d6dbea;
    font-size: 12px;
    margin-top: 6px;
}

/* Native anchored menu: stays attached to its card and scrolls with it. */
.report-menu {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
}

.report-menu summary {
    list-style: none;
    cursor: pointer;
    color: #aab2c0;
    font-size: 22px;
    line-height: 1;
    padding: 2px 5px;
    border-radius: 6px;
    user-select: none;
}

.report-menu summary::-webkit-details-marker {
    display: none;
}

.report-menu summary:hover {
    color: #f5f7fb;
    background: #232936;
}

.report-menu-panel {
    position: absolute;
    top: 30px;
    right: 0;
    min-width: 145px;
    padding: 6px;
    border-radius: 8px;
    border: 1px solid #2b3140;
    background: #11151d;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
    z-index: 20;
}

.report-download-link {
    display: block;
    white-space: nowrap;
    padding: 8px 12px;
    border-radius: 6px;
    color: #e8ecf5 !important;
    text-decoration: none !important;
    font-size: 13px;
    text-align: left;
}

.report-download-link:hover {
    background: #232936;
    color: #ffffff !important;
}
</style>
"""


def _format_timestamp(value) -> str:
    if isinstance(value, datetime):
        return value.astimezone().strftime("%b %d, %Y · %I:%M %p")
    return "—"


def _render_card(report: dict, index: int) -> None:
    report_id = str(report.get("report_id") or "Report")
    txid = str(report.get("transaction_id") or "—")
    status = str(report.get("status") or "Generated")
    generated_at = _format_timestamp(report.get("generated_at"))
    filename = str(report.get("filename") or f"{report_id}_{txid}.pdf")
    storage_path = str(report.get("storage_path") or "")

    try:
        download_url = firebase_services.get_report_download_url(
            storage_path,
            filename=filename,
            expires_minutes=15,
        )
        menu_html = f"""
        <details class="report-menu">
            <summary aria-label="Report actions">⋮</summary>
            <div class="report-menu-panel">
                <a
                    class="report-download-link"
                    href="{escape(download_url, quote=True)}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    Download PDF
                </a>
            </div>
        </details>
        """
    except Exception as exc:
        print(
            f"[FIREBASE][REPORT] download URL failed | "
            f"report_id={report_id} | "
            f"{type(exc).__name__}: {exc}"
        )
        menu_html = """
        <details class="report-menu">
            <summary aria-label="Report actions">⋮</summary>
            <div class="report-menu-panel">
                <span class="report-download-link">Download unavailable</span>
            </div>
        </details>
        """

    st.markdown(
        f"""
        <div class="report-history-card" id="report-card-{index}">
            <div class="report-history-id">{escape(report_id)}</div>
            <div class="report-history-meta">
                Transaction ID: <b>{escape(txid)}</b><br/>
                Generated: {escape(generated_at)}<br/>
                <span class="report-history-status">{escape(status)}</span>
            </div>
            {menu_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report_history(*, storage_error: str | None = None) -> None:
    """Render report history below the Investigation Workspace."""
    st.markdown(_HISTORY_CSS, unsafe_allow_html=True)
    st.markdown("## Report History")

    if storage_error:
        st.warning(storage_error)

    # Direct date input: no popover wrapper, so only Streamlit's calendar opens.
    with st.container(key="report_history_date_wrap"):
        date_range = st.date_input(
            "Date Filter",
            value=(),
            key="report_history_date_filter",
            label_visibility="collapsed",
        )

    start_date: date | None = None
    end_date: date | None = None

    if isinstance(date_range, tuple):
        if len(date_range) >= 1:
            start_date = date_range[0]
        if len(date_range) >= 2:
            end_date = date_range[1]
        elif len(date_range) == 1:
            end_date = date_range[0]

    try:
        reports = firebase_services.get_reports(
            limit=100,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        st.error(f"Could not load report history: {exc}")
        print(
            f"[FIREBASE][REPORT] history load failed | "
            f"{type(exc).__name__}: {exc}"
        )
        return

    if not reports:
        st.info("No reports are available for the selected date range.")
        return

    for index, report in enumerate(reports):
        _render_card(report, index)
