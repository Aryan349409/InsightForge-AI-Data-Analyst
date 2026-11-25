# Final-Year Report Outline (mapped to this codebase)

| Chapter | What to write | Evidence in the project |
|---|---|---|
| 1. Introduction | Problem: analysts spend ~60-80% of time cleaning/querying; non-technical users can't query data. Objectives, scope. | README intro |
| 2. Literature review | Text-to-SQL (Spider, BIRD benchmarks), PandasAI, Julius AI, Power BI Copilot, ChatGPT Data Analysis, **D-S007/Data-Analytics-AI-Agent (reference)**; LLM hallucination; AutoML. Gap: safety + evaluation + prediction in one open tool. | comparison table in README |
| 3. Requirements | Functional (FR1 ingestion … FR9 reports) and non-functional (security, latency < 10 s, usability, privacy). Use-case diagram. | feature list |
| 4. System design | Architecture diagram, data-flow diagram (level 0/1), sequence diagram of NL→SQL with retry, module diagram. | README architecture; `nl2sql.py` |
| 5. Implementation | One section per module; show the **prompt**, the SQL safety rules, quality-score formula, cleaning log, ML pipeline. | `modules/*` |
| 6. Testing | Test-case table (ID, input, expected, actual); pytest results; security tests (DROP, file read, multi-statement). | `tests/` |
| 7. Results & evaluation | Execution accuracy/latency table across models, by difficulty; quality-score before/after; model metrics vs baseline; (optional) 10-15 person usability survey (SUS). | `modules/evaluation.py` |
| 8. Discussion | Failure analysis: which question types fail & why; cost/privacy trade-offs. | `results.csv` |
| 9. Limitations & future work | See README. | |
| 10. Conclusion · References · Appendix | Code excerpts, screenshots, questionnaire. | |

## Formulas to include
**Data Quality Score** = 100 × (0.4·Completeness + 0.2·Uniqueness + 0.2·Validity + 0.2·Consistency)
- Completeness = 1 − missing cells / total cells
- Uniqueness = 1 − duplicate rows / rows
- Validity = 1 − IQR-outlier values / numeric values
- Consistency = 1 − columns with whitespace/casing inconsistencies / columns

**Execution accuracy** = questions whose result set equals the gold SQL result ÷ total questions.

## Likely viva questions
1. How do you stop the LLM from deleting data? *(AST validation + SELECT-only + whitelist + DuckDB external access off + in-memory copy)*
2. What if the SQL is wrong but runs? *(show SQL to user; benchmark measures this; limitation)*
3. Why DuckDB? *(fast analytical SQL directly over DataFrames, in-process, sandboxed)*
4. Why a baseline in ML? *(a model is only useful if it beats predicting the majority class / mean)*
5. How is privacy handled? *(only schema + sample values leave the machine; local Ollama option)*
6. How does your project differ from the reference repo? *(see README table)*
