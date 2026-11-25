# 🧠 InsightForge - AI Data Analyst

Upload a dataset (CSV / Excel / JSON / REST API / SQL database), and InsightForge **profiles it, cleans it,
answers questions asked in plain English, draws charts, trains predictive models, writes insights, and exports a report.**

> **Reference & attribution.** The overall idea (multi-source ingestion → cleaning → NLP-to-SQL → visualisation → reporting)
> was inspired by the open-source [D-S007/Data-Analytics-AI-Agent](https://github.com/D-S007/Data-Analytics-AI-Agent) (MIT).
> This project is an independent implementation (no code copied) with a different architecture and several extensions
> listed below. Cite the reference in your literature review.

## What it adds beyond the reference idea

| Area | Reference (per its README) | InsightForge |
|---|---|---|
| Data ingestion | CSV/XLSX, API, DB | CSV/TSV/XLSX/JSON, REST API, any SQLAlchemy DB (read-only) |
| Cleaning | Automated ETL | Explainable cleaning with a **step-by-step log** + before/after **Data Quality Score** |
| NL querying | NL → SQL | NL → SQL with **AST-level safety validation**, sandboxed DuckDB, **self-repair retries**, conversation memory |
| Prediction | - | **Auto-ML** (3 models + baseline + permutation importance), **forecasting** with back-test, **clustering** |
| Insights | - | Deterministic statistical findings + optional LLM narrative (grounded in computed facts) |
| Evaluation | - | **Benchmark harness**: execution accuracy, valid-SQL rate, latency by difficulty |
| Testing | - | 30 automated unit tests (pytest) |
| LLM | HuggingFace | Provider-agnostic: Claude, OpenAI, or **free local Ollama** |

## Architecture

```
 ┌───────────────────────────── Streamlit UI (app.py) ─────────────────────────────┐
 │  Profile │ Clean │ Ask (chat) │ Charts │ Predict │ Insights │ Report            │
 └──────────────┬──────────────────────────────────────────────────────────────────┘
                │
 ┌──────────────▼───────────────┐   ┌───────────────────────────────────────────────┐
 │ ingestion.py                 │   │ nl2sql.py  ──►  llm.py (Claude/OpenAI/Ollama) │
 │ profiling.py (quality score) │   │   │  prompt = schema + history + question     │
 │ cleaning.py  (logged steps)  │   │   ▼                                           │
 └──────────────┬───────────────┘   │ sql_safety.py  (sqlglot AST validation)       │
                │                   │   │  only 1 SELECT, whitelisted table,        │
 ┌──────────────▼───────────────┐   │   ▼  no file functions                        │
 │ ml.py  (auto-ML, forecast,   │   │ DuckDB in-memory (external access disabled)   │
 │         clustering)          │   │   │  error? → feed back to LLM → retry (≤2)   │
 │ insights.py  visualization.py│   └───┴───────────────────────────────────────────┘
 │ report.py (HTML/Excel/PDF)   │        evaluation.py  (benchmark harness)
 └──────────────────────────────┘
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # add your API key (or configure Ollama)
python sample_data/generate_sample.py                  # (already included) messy retail dataset
streamlit run app.py
```

Without an API key everything works **except** natural-language querying and the AI narrative
(profiling, cleaning, charts, ML, forecasting, clustering, statistical insights, and reports are all offline).

### Free / local LLM (no API cost)
```bash
ollama pull qwen2.5-coder:7b
# Select Ollama (local) in the sidebar; no API key or .env required.
```

## Tests
```bash
pytest -q          # 30 tests: SQL safety, cleaning, profiling, NL→SQL retry logic (fake LLM), ML, forecasting
```

## Evaluation (this becomes your Results chapter)
```bash
python evaluation/make_questions.py     # 15 starter questions with gold SQL → extend to 40–50
python -m modules.evaluation --data sample_data/sales.csv --questions evaluation/questions_sales.json \
       --provider anthropic --out evaluation/results_claude.csv
python -m modules.evaluation ... --provider openai --model llama3.1 --out evaluation/results_llama.csv
```
Outputs valid-SQL rate, **execution accuracy** (result-set match against gold SQL), average latency and accuracy by
difficulty. Compare models/prompt variants in a table + chart.

## Project layout
```
app.py                  Streamlit UI
modules/
  ingestion.py          files, REST API, SQL DB loaders
  profiling.py          column profiling, outliers, Data Quality Score
  cleaning.py           explainable cleaning pipeline
  llm.py                provider-agnostic LLM client
  nl2sql.py             question → SQL → validated → executed → self-repair
  sql_safety.py         AST-based SQL guardrails
  ml.py                 auto-ML, forecasting, clustering
  insights.py           statistical facts + LLM narrative
  visualization.py      auto charts + chart picker for query results
  report.py             HTML / Excel / PDF export
  evaluation.py         benchmark harness
tests/                  pytest suite
evaluation/             benchmark questions
sample_data/            dataset generator + sales.csv
docs/REPORT_OUTLINE.md  chapter-by-chapter report guide mapped to this code
```

## Known limitations (state these honestly in your report)
- LLM-generated SQL can be wrong yet plausible - hence showing SQL + evaluation. Accuracy depends on the model.
- Data is sent to the LLM provider as **schema + 3 sample values per column** (not full rows) - use a local model for sensitive data.
- Single-table analysis; multi-table joins are future work.
- Forecasting is univariate (Holt-Winters); no exogenous variables.
- Datasets are held in memory - suited to files up to a few hundred MB.

## Future scope
Multi-table schema + join inference · RAG over data dictionaries · scheduled reports · role-based access ·
agentic multi-step analysis (planner/executor) · deployment on Streamlit Cloud / Docker.
