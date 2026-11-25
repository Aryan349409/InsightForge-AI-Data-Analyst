"""InsightForge - AI Data Analyst (Streamlit UI)."""
from __future__ import annotations

import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui import setup, hero, landing, PALETTE, show_chart, palette_controls, style_chart
import os
from html import escape
from modules import insights as ins
from modules import ml, report
from modules import visualization as viz
from modules.cleaning import clean
from modules.ingestion import load_api, load_file, load_sql, safe_table_name
from modules.llm import LLMClient
from modules.nl2sql import ask, schema_context
from modules.profiling import profile, semantic_type

warnings.filterwarnings("ignore")
st.set_page_config(page_title="InsightForge - AI Data Analyst", page_icon="🧠", layout="wide")


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ----------------------------------------------------------------- state ---
DEFAULTS = {"raw": None, "df": None, "log": [], "table": "data", "qa": [], "history": [],
            "narrative": "", "ml": None, "forecast": None, "cluster": None, "source": ""}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
S = st.session_state


def set_data(df: pd.DataFrame, name: str):
    S.raw, S.df, S.log = df, None, []
    S.table, S.source = safe_table_name(name), name
    S.qa, S.history, S.narrative, S.ml, S.forecast, S.cluster = [], [], "", None, None, None


# --------------------------------------------------------------- sidebar ---
with st.sidebar:
    st.markdown('<div class="forge-brand"><span class="forge-mark">◈</span> InsightForge</div>', unsafe_allow_html=True)
    st.caption("AI DATA ANALYST / WORKSPACE")
    st.divider()

    pages = ["Overview", "Data preparation", "AI assistant", "Visual explorer", "Predictive lab", "Insights", "Export center"]
    icons = ["◫", "◇", "✦", "▥", "↗", "◎", "↓"]
    st.caption("WORKSPACE")
    page = st.radio("Navigate", pages, format_func=lambda x: icons[pages.index(x)] + "   " + x, label_visibility="collapsed")
    st.divider()
    with st.expander("Data connection", expanded=S.raw is None):
        src = st.radio("Source", ["Sample dataset", "Upload file", "REST API", "SQL database"], label_visibility="collapsed")
        try:
            if src == "Sample dataset":
                if st.button("Load retail sales sample", type="primary", width="stretch"):
                    set_data(load_file("sample_data/sales.csv"), "sales.csv")
            elif src == "Upload file":
                up = st.file_uploader("CSV / Excel / JSON", type=["csv", "tsv", "xlsx", "xls", "json"])
                if up is not None and S.source != up.name:
                    set_data(load_file(up), up.name)
            elif src == "REST API":
                url = st.text_input("JSON endpoint URL")
                if st.button("Fetch") and url:
                    set_data(load_api(url), "api_data")
            else:
                conn = st.text_input("SQLAlchemy URL", placeholder="postgresql://user:pass@host/db")
                query = st.text_area("SELECT query", "SELECT * FROM my_table LIMIT 5000")
                if st.button("Run query") and conn:
                    set_data(load_sql(conn, query), "db_query")
        except Exception as e:
            st.error(f"Could not load data: {e}")


    with st.expander("🤖 LLM settings", expanded=False):
        provider = st.selectbox("Provider", ["ollama", "openai", "anthropic"],
                                format_func=lambda x: {"ollama":"Ollama (local)","openai":"OpenAI","anthropic":"Anthropic"}[x])
        if provider == "ollama":
            model = st.text_input("Local model", os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"), key="ollama_model")
            api_key, base_url = None, None
            st.caption("Local endpoint: 127.0.0.1:11434 · No API key needed")
        else:
            model = st.text_input("Model (blank = default)", key=f"model_{provider}")
            api_key = st.text_input("API key (blank = use .env)", type="password", key=f"key_{provider}")
            base_url = st.text_input("Base URL (optional)") if provider == "openai" else None
    llm = LLMClient(provider=provider, model=model or None, api_key=api_key or None, base_url=base_url or None)
    st.caption("AI · " + ("Ollama local · configured" if provider == "ollama" else ("Configured" if llm.available else "API key required")))

    if S.raw is not None:
        st.success(f"Loaded **{S.source}** · {S.raw.shape[0]:,} rows × {S.raw.shape[1]} cols")

palette_controls()
setup()

# ------------------------------------------------------------------ main ---
if S.raw is None:
    landing()
    st.stop()

working = S.df if S.df is not None else S.raw
prof = profile(working)
headers = [
    ("01 / DATA OVERVIEW", "Dataset intelligence", "Understand the structure and quality of your data at a glance."),
    ("02 / DATA PREPARATION", "Make your data analysis-ready", "Configure cleaning rules and review every transformation."),
    ("03 / AI ASSISTANT", "Ask your data anything", "Natural-language questions, transparent SQL and interactive results."),
    ("04 / VISUAL EXPLORER", "See the story in your data", "Explore automatic visualizations or build a chart of your own."),
    ("05 / PREDICTIVE LAB", "Explore what comes next", "Train models, forecast trends and discover meaningful segments."),
    ("06 / INSIGHTS", "From findings to decisions", "Review computed statistics and generate an AI executive summary."),
    ("07 / EXPORT CENTER", "Take your insights with you", "Export reports and the working dataset in convenient formats."),
]
hero(*headers[pages.index(page)])
st.markdown(f'<div class="forge-status">● &nbsp; <b>{escape(S.source)}</b> &nbsp; · &nbsp; {len(working):,} records &nbsp; · &nbsp; {len(working.columns)} fields &nbsp; · &nbsp; {"Cleaned" if S.df is not None else "Raw"}</div>', unsafe_allow_html=True)

# -------- Profile
if page == pages[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quality score", f"{prof['quality_score']}/100")
    c2.metric("Missing cells", f"{prof['missing_cells']:,}")
    c3.metric("Duplicate rows", f"{prof['duplicate_rows']:,}")
    c4.metric("Outlier values", f"{prof['outlier_cells']:,}")
    d = prof["dimensions"]
    fig = go.Figure(go.Bar(x=list(d.values()), y=[k.title() for k in d], orientation="h", marker=dict(color=PALETTE[:len(d)])))
    fig.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(range=[0, 100], title="%"))
    show_chart(fig, width="stretch")
    t1, t2 = st.tabs(["Column diagnostics", "Data preview"])
    with t1:
        st.dataframe(pd.DataFrame(prof["columns_info"]), width="stretch", hide_index=True)
    with t2:
        st.dataframe(working.head(100), width="stretch")

# -------- Clean
if page == pages[1]:
    st.write("Cleaning is **explainable**: every change is logged and can be reviewed.")
    c1, c2, c3 = st.columns(3)
    impute = c1.selectbox("Missing values", ["auto", "drop", "none"],
                          help="auto = median for numbers, mode for categories")
    outl = c2.selectbox("Outliers", ["none", "cap", "remove"])
    dedup = c3.checkbox("Remove duplicates", True)
    if st.button("Run cleaning", type="primary"):
        S.df, S.log = clean(S.raw, impute=impute, outliers=outl, drop_duplicates=dedup)
        S.ml = S.forecast = S.cluster = None
        st.rerun()
    if S.df is not None:
        before = profile(S.raw)
        a, b = st.columns(2)
        a.metric("Quality score", f"{prof['quality_score']}/100", f"{prof['quality_score'] - before['quality_score']:+.1f}")
        b.metric("Rows", f"{len(S.df):,}", f"{len(S.df) - len(S.raw):+,}")
        st.subheader("What changed")
        for line in S.log:
            st.markdown(f"- {line}")
    else:
        st.info("Run cleaning to create the working dataset used by the other tabs.")

# -------- Ask
if page == pages[2]:
    st.write("Ask questions in plain English. The generated SQL is always shown so you can **verify** it.")
    with st.expander("Schema the AI sees"):
        st.code(schema_context(working, S.table))
    for item in S.qa:
        with st.chat_message("user"):
            st.write(item["question"])
        with st.chat_message("assistant"):
            if item["error"]:
                st.error(item["error"])
            with st.expander("View generated SQL", expanded=bool(item["error"])):
                st.code(item["sql"] or "-- no SQL produced", language="sql")
            if item["df"] is not None:
                st.dataframe(item["df"], width="stretch")
                fig = viz.chart_for_result(item["df"])
                if fig is not None:
                    show_chart(fig, width="stretch", key=f"c{id(item)}")
            st.caption(f"{item['attempts']} attempt(s) · {item['latency']:.1f}s")
    suggested = None
    if not S.qa:
        st.subheader("Start a conversation")
        for col, prompt in zip(st.columns(3), ["How many records are there?", "Summarize the dataset by category", "Which columns contain missing values?"]):
            if col.button(prompt, width="stretch"):
                suggested = prompt
    q = st.chat_input("Ask a question about your dataset…") or suggested
    if q:
        if not llm.available:
            st.error("Add an API key in the sidebar (or .env) to use natural-language queries.")
        else:
            with st.spinner("Thinking..."):
                r = ask(llm, q, working, S.table, S.history)
            S.qa.append({"question": q, "sql": r.sql, "df": r.df, "error": r.error,
                         "attempts": r.attempts, "latency": r.latency})
            if r.ok:
                S.history.append((q, r.sql))
            st.rerun()

# -------- Charts
if page == pages[3]:
    st.subheader("Automatic charts")
    auto = viz.auto_charts(working)
    for i in range(0, len(auto), 2):
        for col, (title, fig) in zip(st.columns(2), auto[i:i+2]):
            with col:
                st.markdown(f"**{title}**")
                show_chart(fig, width="stretch", key=f"auto_{title}")
    st.subheader("Build your own")
    cols = list(working.columns)
    cc = st.columns(4)
    kind = cc[0].selectbox("Type", ["bar", "line", "scatter", "box", "histogram"])
    xcol = cc[1].selectbox("X", cols)
    ycol = cc[2].selectbox("Y", [None] + cols)
    color = cc[3].selectbox("Colour", [None] + cols)
    try:
        if kind == "histogram":
            fig = px.histogram(working, x=xcol, color=color)
        else:
            fn = {"bar": px.bar, "line": px.line, "scatter": px.scatter, "box": px.box}[kind]
            fig = fn(working, x=xcol, y=ycol, color=color)
        chart_mode = st.selectbox("Custom chart colours", ["Use sidebar", "Single colour", "Palette"] + (["Individual colours"] if kind == "bar" and color is None else []))
        overrides = {}
        single = None
        if chart_mode == "Single colour":
            single = st.color_picker("Choose chart colour", PALETTE[0], key="custom_chart_single")
        elif chart_mode == "Individual colours":
            categories = list(dict.fromkeys(str(v) for v in fig.data[0].x)) if fig.data else []
            with st.expander("Choose each bar colour", expanded=True):
                for i, category in enumerate(categories[:50]):
                    overrides[category] = st.color_picker(category, PALETTE[i % len(PALETTE)], key=f"bar_colour_{xcol}_{i}_{category}")
                if len(categories) > 50:
                    st.caption("First 50 categories can be customized; remaining categories use the palette.")
        show_chart(fig, width="stretch", key="custom", mode=None if chart_mode == "Use sidebar" else chart_mode, single=single, overrides=overrides)
    except Exception as e:
        st.warning(f"Cannot draw that combination: {e}")

# -------- Predict
if page == pages[4]:
    mode = st.radio("Analysis", ["Predict a column (auto-ML)", "Forecast a time series", "Customer / record segmentation"],
                    horizontal=True)
    types = {c: semantic_type(working[c]) for c in working.columns}
    if mode.startswith("Predict"):
        target = st.selectbox("Target column to predict", list(working.columns),
                              index=list(working.columns).index("returned") if "returned" in working.columns else 0)
        if st.button("Train & compare models", type="primary"):
            try:
                with st.spinner("Training 3 models..."):
                    S.ml = ml.train(working, target)
            except Exception as e:
                st.error(str(e))
        if S.ml:
            m = S.ml
            st.success(f"**{m['task'].title()}** · best model: **{m['best_model']}** "
                       f"(train {m['n_train']:,} / test {m['n_test']:,})")
            base_lbl = "majority-class accuracy" if m["task"] == "classification" else "R² of predicting the mean"
            st.caption(f"Baseline ({base_lbl}): {m['baseline']:.3f} - a useful model must beat this.")
            st.dataframe(m["comparison"], hide_index=True, width="stretch")
            show_chart(px.bar(m["importance"].head(10).iloc[::-1], x="importance", y="feature",
                                   orientation="h", title="Permutation feature importance"),
                            width="stretch")
    elif mode.startswith("Forecast"):
        dts = [c for c, t in types.items() if t == "datetime"]
        nums = [c for c, t in types.items() if t == "numeric"]
        if not dts:
            st.info("No datetime column found. Run cleaning first so dates are parsed.")
        else:
            c1, c2, c3 = st.columns(3)
            dcol, vcol = c1.selectbox("Date", dts), c2.selectbox("Value", nums)
            horizon = c3.slider("Periods ahead (months)", 3, 12, 6)
            if st.button("Forecast", type="primary"):
                try:
                    S.forecast = ml.forecast(working, dcol, vcol, horizon)
                except Exception as e:
                    st.error(str(e))
            if S.forecast:
                f = S.forecast
                fig = go.Figure()
                fig.add_scatter(x=f["history"].index, y=f["history"].values, name="History")
                fig.add_scatter(x=f["forecast"].index, y=f["forecast"].values, name="Forecast", line=dict(dash="dash"))
                show_chart(fig, width="stretch")
                mape = f"{f['mape']:.1f}%" if f["mape"] is not None else "n/a"
                st.caption(f"Method: {f['method']} · back-test over last {f['holdout']} periods: MAE {f['mae']:,.0f}, MAPE {mape}")
    else:
        if st.button("Find segments", type="primary"):
            try:
                S.cluster = ml.cluster(working)
            except Exception as e:
                st.error(str(e))
        if S.cluster:
            c = S.cluster
            st.success(f"Best k = {c['k']} (silhouette {c['silhouette']:.2f})")
            st.dataframe(c["profile"], width="stretch")
            st.bar_chart(c["sizes"], color=PALETTE[0])

# -------- Insights
if page == pages[5]:
    facts = ins.statistical_facts(working, prof)
    st.subheader("Statistical findings (computed, not generated)")
    for f in facts:
        st.markdown(f"- {f}")
    st.subheader("AI executive summary")
    if st.button("Generate summary", disabled=not llm.available):
        extra = ""
        if S.ml:
            extra = f"Model result: {S.ml['best_model']} for '{S.ml['target']}'. Top features: " + \
                    ", ".join(S.ml["importance"]["feature"].head(3))
        try:
            with st.spinner("Writing..."):
                S.narrative = ins.narrative(llm, facts, extra)
        except Exception as e:
            st.error(str(e))
    if S.narrative:
        st.write(S.narrative)
    if not llm.available:
        st.caption("Add an API key to enable the AI narrative.")

# -------- Report
if page == pages[6]:
    title = st.text_input("Report title", f"Analysis of {S.source}")
    facts = ins.statistical_facts(working, prof)
    charts = [(name, style_chart(fig)) for name, fig in viz.auto_charts(working, 6)]
    st.write("Download your analysis in three formats.")
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇ HTML (interactive)", report.build_html(title, prof, S.log, facts, S.narrative, charts, S.qa),
                       "report.html", "text/html")
    c2.download_button("⬇ Excel", report.build_excel(working, prof, S.log, facts, S.qa), "report.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    c3.download_button("⬇ PDF", report.build_pdf(title, prof, S.log, facts, S.narrative), "report.pdf", "application/pdf")
    st.download_button("⬇ Cleaned CSV", working.to_csv(index=False), "clean_data.csv", "text/csv")
