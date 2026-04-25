"""Streamlit CRM frontend for lead management."""

from __future__ import annotations

import csv
import io
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from crm_db import (  # noqa: E402
    add_lead,
    delete_lead,
    get_all_leads,
    get_leads_by_outcome,
    get_upcoming_callbacks,
    import_from_scraper_csv,
    import_new_results,
    init_db,
    is_imported,
)


@dataclass(frozen=True)
class LeadView:
    key: str
    label: str
    outcome: str | None


VIEWS: list[LeadView] = [
    LeadView("inbox", "Inbox", None),
    LeadView("callbacks", "Callbacks", "callback"),
    LeadView("interested", "Interested", "interested"),
    LeadView("not_interested", "Not interested", "not_interested"),
    LeadView("all", "All leads", "all"),
    LeadView("imports", "Imports", None),
    LeadView("settings", "Settings", None),
]


def _load_css() -> None:
    css_path = Path(__file__).parent / "ui.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _build_df(leads: list[dict]) -> pd.DataFrame:
    rows = []
    for l in leads:
        rows.append(
            {
                "id": l.get("id"),
                "clinic": _safe_text(l.get("clinic_name")).strip(),
                "contact": _safe_text(l.get("contact_name")).strip(),
                "role": _safe_text(l.get("contact_role")).strip(),
                "size": _safe_text(l.get("clinic_size")).strip(),
                "outcome": _safe_text(l.get("call_outcome")).strip() or "—",
                "next_action": _safe_text(l.get("next_action")).strip(),
                "next_date": _safe_text(l.get("next_action_date")).strip(),
                "updated": _safe_text(l.get("updated_at")).strip(),
                "source": _safe_text(l.get("source_file")).strip(),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["clinic"] = df["clinic"].replace("", "Unnamed")
    df["contact"] = df["contact"].replace("", "—")
    df["role"] = df["role"].replace("", "—")
    df["next_date"] = df["next_date"].replace("", "—")
    df["next_action"] = df["next_action"].replace("", "—")
    df["size"] = df["size"].replace("", "—")
    df["updated"] = df["updated"].replace("", "—")
    df["source"] = df["source"].replace("", "—")
    return df


def _kpi_counts(all_leads: list[dict]) -> dict[str, int]:
    counts = {"total": 0, "inbox": 0, "callbacks": 0, "interested": 0, "not_interested": 0}
    counts["total"] = len(all_leads)
    for l in all_leads:
        outcome = (l.get("call_outcome") or "").strip()
        if not outcome:
            counts["inbox"] += 1
        elif outcome == "callback":
            counts["callbacks"] += 1
        elif outcome == "interested":
            counts["interested"] += 1
        elif outcome == "not_interested":
            counts["not_interested"] += 1
    return counts


def _render_header(title: str, subtitle: str, right_chip: str) -> None:
    st.markdown(
        f"""
        <div class="crm-header">
          <div>
            <div class="crm-title">{title}</div>
            <div class="crm-subtitle">{subtitle}</div>
          </div>
          <div class="crm-chip">{right_chip}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _pick_view() -> LeadView:
    options = {v.label: v for v in VIEWS}
    default = st.session_state.get("nav", "Inbox")
    choice = st.sidebar.radio("Navigation", list(options.keys()), index=list(options.keys()).index(default))
    st.session_state["nav"] = choice
    return options[choice]


def _auto_import_sidebar() -> None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Import")
    auto_import = st.sidebar.toggle("Auto-import new CSVs", value=True, help="Imports new `data/results/*.csv` once per app start.")
    if auto_import and not st.session_state.get("_auto_import_done"):
        summary = import_new_results()
        st.session_state["_auto_import_done"] = True
        if summary["files"]:
            st.sidebar.success(f"Imported {summary['rows']} row(s) from {summary['files']} file(s).")
        else:
            st.sidebar.caption("No new CSVs detected.")

    with st.sidebar.expander("Advanced"):
        force = st.checkbox("Enable force reimport", value=False)
        if st.button("Force reimport all CSVs", disabled=not force, type="secondary"):
            summary = import_new_results(force=True)
            st.sidebar.warning(f"Reimported {summary['rows']} row(s) from {summary['files']} file(s).")
            st.rerun()


def _add_lead_dialog() -> None:
    if not hasattr(st, "dialog"):
        return

    @st.dialog("Add lead")
    def _dialog() -> None:
        c1, c2 = st.columns(2)
        with c1:
            contact_name = st.text_input("Contact name")
            contact_role = st.text_input("Role")
            clinic_name = st.text_input("Clinic name")
            clinic_size = st.text_input("Clinic size")
        with c2:
            call_outcome = st.selectbox("Call outcome", ["", "interested", "callback", "not_interested"], index=0)
            next_action = st.text_input("Next action")
            has_date = st.checkbox("Has next action date", value=False)
            next_action_date = st.date_input("Next action date", value=date.today(), disabled=not has_date)
        notes = st.text_area("Notes", height=140)
        if st.button("Create lead", type="primary"):
            add_lead(
                contact_name=contact_name,
                contact_role=contact_role,
                clinic_name=clinic_name,
                clinic_size=clinic_size,
                call_outcome=call_outcome,
                next_action=next_action,
                next_action_date=next_action_date.isoformat() if has_date else "",
                notes=notes,
                source_file="manual",
            )
            st.session_state["selected_lead_id"] = None
            st.rerun()

    if st.sidebar.button("New lead", type="primary"):
        _dialog()


def _download_current_view(leads: list[dict], filename: str) -> None:
    out = io.StringIO()
    fieldnames = [
        "contact_name",
        "contact_role",
        "clinic_name",
        "clinic_size",
        "call_outcome",
        "next_action",
        "next_action_date",
        "notes",
        "source_file",
        "created_at",
        "updated_at",
    ]
    writer = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for l in leads:
        writer.writerow(l)
    st.download_button(
        "Download CSV",
        data=out.getvalue().encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        type="secondary",
    )


def _lead_selector(df: pd.DataFrame) -> int | None:
    if df.empty:
        return None

    df_display = df.copy()
    df_display = df_display[["id", "clinic", "contact", "outcome", "next_action", "next_date", "updated"]]
    df_display = df_display.rename(
        columns={
            "clinic": "Clinic",
            "contact": "Contact",
            "outcome": "Outcome",
            "next_action": "Next action",
            "next_date": "Next date",
            "updated": "Updated",
        }
    )

    selected_id = st.session_state.get("selected_lead_id")

    try:
        event = st.dataframe(
            df_display.drop(columns=["id"]),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="leads_table",
        )
        if event and getattr(event, "selection", None) and event.selection.rows:
            row_idx = event.selection.rows[0]
            selected_id = int(df.iloc[row_idx]["id"])
    except TypeError:
        st.dataframe(df_display.drop(columns=["id"]), use_container_width=True, hide_index=True)

    if selected_id is None or selected_id not in set(df["id"].tolist()):
        selected_id = int(df.iloc[0]["id"])

    st.session_state["selected_lead_id"] = selected_id
    return selected_id


def _render_editor(lead: dict) -> None:
    st.markdown('<div class="crm-card">', unsafe_allow_html=True)
    st.subheader("Lead")

    quick1, quick2, quick3, quick4 = st.columns([1, 1, 1, 1])
    from crm_db import update_lead  # local import to avoid heavy imports at module load

    with quick1:
        if st.button("Interested", use_container_width=True, type="secondary", key=f"q_int_{lead['id']}"):
            update_lead(lead["id"], call_outcome="interested")
            st.rerun()
    with quick2:
        if st.button("Callback", use_container_width=True, type="secondary", key=f"q_cb_{lead['id']}"):
            update_lead(lead["id"], call_outcome="callback")
            st.rerun()
    with quick3:
        if st.button("Not interested", use_container_width=True, type="secondary", key=f"q_ni_{lead['id']}"):
            update_lead(lead["id"], call_outcome="not_interested")
            st.rerun()
    with quick4:
        if st.button("Clear outcome", use_container_width=True, type="secondary", key=f"q_clr_{lead['id']}"):
            update_lead(lead["id"], call_outcome="")
            st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        contact_name = st.text_input("Contact name", value=lead.get("contact_name", ""), key=f"e_contact_{lead['id']}")
        contact_role = st.text_input("Role", value=lead.get("contact_role", ""), key=f"e_role_{lead['id']}")
        clinic_name = st.text_input("Clinic name", value=lead.get("clinic_name", ""), key=f"e_clinic_{lead['id']}")
        clinic_size = st.text_input("Clinic size", value=lead.get("clinic_size", ""), key=f"e_size_{lead['id']}")
    with c2:
        outcome = (lead.get("call_outcome") or "").strip()
        call_outcome = st.selectbox(
            "Call outcome",
            ["", "interested", "callback", "not_interested"],
            index=["", "interested", "callback", "not_interested"].index(outcome) if outcome in {"", "interested", "callback", "not_interested"} else 0,
            key=f"e_outcome_{lead['id']}",
        )
        next_action = st.text_input("Next action", value=lead.get("next_action", ""), key=f"e_action_{lead['id']}")
        existing_date = _parse_iso_date(lead.get("next_action_date"))
        has_date = st.checkbox("Has next action date", value=existing_date is not None, key=f"e_hasdate_{lead['id']}")
        next_action_date = st.date_input(
            "Next action date",
            value=existing_date or date.today(),
            disabled=not has_date,
            key=f"e_date_{lead['id']}",
        )

    notes = st.text_area("Notes", value=lead.get("notes", ""), height=180, key=f"e_notes_{lead['id']}")

    b1, b2, b3 = st.columns([1, 1, 1])
    with b1:
        if st.button("Save", type="primary", use_container_width=True, key=f"e_save_{lead['id']}"):
            update_lead(
                lead["id"],
                contact_name=contact_name,
                contact_role=contact_role,
                clinic_name=clinic_name,
                clinic_size=clinic_size,
                call_outcome=call_outcome,
                next_action=next_action,
                next_action_date=next_action_date.isoformat() if has_date else "",
                notes=notes,
            )
            st.success("Saved.")
            st.rerun()
    with b2:
        if st.button("Save + Callback", type="secondary", use_container_width=True, key=f"e_save_cb_{lead['id']}"):
            update_lead(
                lead["id"],
                contact_name=contact_name,
                contact_role=contact_role,
                clinic_name=clinic_name,
                clinic_size=clinic_size,
                call_outcome="callback",
                next_action=next_action,
                next_action_date=next_action_date.isoformat() if has_date else "",
                notes=notes,
            )
            st.rerun()
    with b3:
        if st.button("Delete", type="secondary", use_container_width=True, key=f"e_del_{lead['id']}"):
            delete_lead(lead["id"])
            st.session_state["selected_lead_id"] = None
            st.rerun()

    st.caption(f"Source: `{lead.get('source_file') or '—'}` • Updated: `{lead.get('updated_at') or '—'}`")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_imports_view() -> None:
    _render_header("Imports", "Pull scraper outputs into your CRM database.", "Source: data/results")

    results_dir = Path(__file__).parent.parent / "data" / "results"
    files = sorted(results_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True) if results_dir.exists() else []
    if not files:
        st.info("No CSV files found in `data/results`.")
        return

    left, right = st.columns([2, 1], gap="large")
    with left:
        st.markdown('<div class="crm-card">', unsafe_allow_html=True)
        st.subheader("Files")
        selected: list[Path] = []
        for p in files[:75]:
            imported = is_imported(str(p))
            label = f"{p.name}  {'(imported)' if imported else '(new)'}"
            if st.checkbox(label, value=not imported, disabled=imported, key=f"imp_{p.name}"):
                selected.append(p)
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Import selected", type="primary", use_container_width=True, disabled=not selected):
                total = sum(import_from_scraper_csv(str(p)) for p in selected)
                st.success(f"Imported {total} row(s).")
                st.rerun()
        with c2:
            if st.button("Force reimport selected", type="secondary", use_container_width=True, disabled=not selected):
                total = sum(import_from_scraper_csv(str(p), force=True) for p in selected)
                st.warning(f"Reimported {total} row(s).")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="crm-card">', unsafe_allow_html=True)
        st.subheader("Import by path")
        csv_path = st.text_input("CSV path", placeholder=str(results_dir / files[0].name))
        force = st.checkbox("Force reimport (path)", value=False)
        if st.button("Import", type="secondary", use_container_width=True):
            p = Path(csv_path) if csv_path else None
            if p and p.exists() and p.is_file():
                count = import_from_scraper_csv(str(p), force=force)
                st.success(f"Imported {count} row(s).")
                st.rerun()
            else:
                st.error("File not found.")
        st.markdown("</div>", unsafe_allow_html=True)


def _render_settings_view() -> None:
    _render_header("Settings", "Single-user local CRM settings.", "Local only")
    st.markdown('<div class="crm-card">', unsafe_allow_html=True)
    db_path = Path(__file__).parent.parent / "data" / "crm.db"
    st.write(f"Database: `{db_path}`")
    st.write("Tip: If you want a clean slate, you can reset the database.")
    confirm = st.checkbox("I understand this deletes all CRM data", value=False)
    if st.button("Reset database", type="secondary", disabled=not confirm):
        if db_path.exists():
            db_path.unlink()
        init_db()
        st.session_state["selected_lead_id"] = None
        st.success("Database reset.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_callbacks_view() -> None:
    callbacks = get_upcoming_callbacks()
    _render_header("Callbacks", "Upcoming follow-ups, ordered by date.", f"Count: {len(callbacks)}")
    if not callbacks:
        st.info("No upcoming callbacks.")
        return

    df = _build_df(callbacks)
    if not df.empty:
        df = df.sort_values(by=["next_date"], ascending=True, kind="stable").reset_index(drop=True)

    st.markdown('<div class="crm-card">', unsafe_allow_html=True)
    st.subheader("Upcoming")
    st.dataframe(
        df[["clinic", "contact", "next_action", "next_date", "updated"]].rename(
            columns={
                "clinic": "Clinic",
                "contact": "Contact",
                "next_action": "Next action",
                "next_date": "Date",
                "updated": "Updated",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="Lead CRM", page_icon="CRM", layout="wide")
    init_db()
    _load_css()

    st.sidebar.markdown("### Lead CRM")
    st.sidebar.caption("Single-user local call tracker")
    view = _pick_view()
    _auto_import_sidebar()
    _add_lead_dialog()

    all_leads = get_all_leads()
    counts = _kpi_counts(all_leads)

    k1, k2, k3, k4, k5 = st.columns([1, 1, 1, 1, 1], gap="large")
    for col, label, value, hint in [
        (k1, "Total", counts["total"], "All leads"),
        (k2, "Inbox", counts["inbox"], "No outcome yet"),
        (k3, "Callbacks", counts["callbacks"], "Need follow-up"),
        (k4, "Interested", counts["interested"], "Warm leads"),
        (k5, "Not interested", counts["not_interested"], "Closed"),
    ]:
        with col:
            st.markdown(
                f"""
                <div class="crm-card">
                  <div class="kpi">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value">{value}</div>
                  </div>
                  <div class="kpi-hint">{hint}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("")

    if view.key == "imports":
        _render_imports_view()
        return
    if view.key == "settings":
        _render_settings_view()
        return
    if view.key == "callbacks":
        _render_callbacks_view()
        return

    subtitle = "Track call outcomes and next steps. Click a row to edit."
    right_chip = f"Leads: {counts['total']}"
    _render_header(view.label, subtitle, right_chip)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")
    search = st.sidebar.text_input("Search", placeholder="Clinic, contact, role")
    page_size = st.sidebar.slider("Page size", min_value=10, max_value=200, value=30, step=10)

    if view.outcome == "all":
        leads = all_leads
    elif view.outcome in {"interested", "callback", "not_interested"}:
        leads = get_leads_by_outcome(view.outcome)
    else:
        leads = [l for l in all_leads if not (l.get("call_outcome") or "").strip()]

    if search.strip():
        s = search.strip().lower()
        leads = [
            l
            for l in leads
            if s in (l.get("clinic_name") or "").lower()
            or s in (l.get("contact_name") or "").lower()
            or s in (l.get("contact_role") or "").lower()
        ]

    df = _build_df(leads)
    if not df.empty:
        df = df.sort_values(by=["updated"], ascending=False, kind="stable").reset_index(drop=True)

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.markdown('<div class="crm-card">', unsafe_allow_html=True)
        st.subheader("Leads")
        st.caption(f"{len(leads)} in this view")

        if df.empty:
            st.info("No leads in this view.")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            start = int(st.session_state.get("page_start", 0))
            if start >= len(df):
                start = 0
            end = min(len(df), start + int(page_size))
            pager_c1, pager_c2, pager_c3 = st.columns([1, 1, 3])
            with pager_c1:
                if st.button("Prev", use_container_width=True, disabled=start == 0):
                    st.session_state["page_start"] = max(0, start - int(page_size))
                    st.rerun()
            with pager_c2:
                if st.button("Next", use_container_width=True, disabled=end >= len(df)):
                    st.session_state["page_start"] = start + int(page_size)
                    st.rerun()
            with pager_c3:
                st.caption(f"Showing {start + 1}-{end} of {len(df)}")

            page_df = df.iloc[start:end].reset_index(drop=True)
            selected_id = _lead_selector(page_df)
            _download_current_view(leads, filename=f"crm_{view.key}.csv")
            st.markdown("</div>", unsafe_allow_html=True)

    with right:
        if df.empty:
            st.markdown('<div class="crm-card">', unsafe_allow_html=True)
            st.subheader("Editor")
            st.caption("Select a lead to edit.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        selected_id = st.session_state.get("selected_lead_id")
        selected = None
        for l in leads:
            if l.get("id") == selected_id:
                selected = l
                break
        if selected is None:
            selected = leads[0]
            st.session_state["selected_lead_id"] = selected.get("id")

        _render_editor(selected)


if __name__ == "__main__":
    main()
