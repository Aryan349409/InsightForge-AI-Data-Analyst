"""Report export: self-contained HTML, Excel workbook, PDF."""
from __future__ import annotations

import html
import io
from datetime import datetime

import pandas as pd


def build_html(title: str, profile: dict, cleaning_log: list[str], insights: list[str],
               narrative: str, figs: list, qa: list[dict]) -> str:
    esc = html.escape
    parts = [f"<html><head><meta charset='utf-8'><title>{esc(title)}</title>"
             "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:960px;margin:2rem auto;color:#222}"
             "h1,h2{color:#1f3a5f}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 10px}"
             "code,pre{background:#f4f4f4;padding:6px;display:block;white-space:pre-wrap}</style></head><body>",
             f"<h1>{esc(title)}</h1><p>Generated {datetime.now():%Y-%m-%d %H:%M}</p>",
             f"<h2>Data quality: {profile['quality_score']}/100</h2>",
             f"<p>{profile['rows']:,} rows &times; {profile['columns']} columns &middot; "
             f"{profile['missing_cells']} missing cells &middot; {profile['duplicate_rows']} duplicate rows</p>"]
    if cleaning_log:
        parts.append("<h2>Cleaning steps</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in cleaning_log) + "</ul>")
    if insights:
        parts.append("<h2>Key findings</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in insights) + "</ul>")
    if narrative:
        parts.append(f"<h2>AI summary</h2><p>{esc(narrative).replace(chr(10), '<br>')}</p>")
    if figs:
        parts.append("<h2>Charts</h2>")
        for i, (t, fig) in enumerate(figs):
            parts.append(f"<h3>{esc(t)}</h3>" + fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False))
    if qa:
        parts.append("<h2>Questions asked</h2>")
        for item in qa:
            parts.append(f"<h3>{esc(item['question'])}</h3><pre>{esc(item['sql'])}</pre>")
            if item.get("df") is not None:
                parts.append(item["df"].head(20).to_html(index=False))
    parts.append("</body></html>")
    return "".join(parts)


def build_excel(df_clean: pd.DataFrame, profile: dict, cleaning_log: list[str],
                insights: list[str], qa: list[dict]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df_clean.to_excel(xw, sheet_name="Clean data", index=False)
        pd.DataFrame(profile["columns_info"]).to_excel(xw, sheet_name="Profile", index=False)
        pd.DataFrame({"Cleaning log": cleaning_log}).to_excel(xw, sheet_name="Cleaning log", index=False)
        pd.DataFrame({"Insight": insights}).to_excel(xw, sheet_name="Insights", index=False)
        for i, item in enumerate(qa[:10], 1):
            if item.get("df") is not None:
                item["df"].to_excel(xw, sheet_name=f"Q{i}", index=False)
    return buf.getvalue()


def build_pdf(title: str, profile: dict, cleaning_log: list[str], insights: list[str],
              narrative: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
    e = [Paragraph(html.escape(title), st["Title"]),
         Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M}", st["Normal"]), Spacer(1, 12),
         Paragraph(f"Data quality score: <b>{profile['quality_score']}/100</b>", st["Heading2"]),
         Table([["Rows", "Columns", "Missing cells", "Duplicates", "Outliers"],
                [profile["rows"], profile["columns"], profile["missing_cells"],
                 profile["duplicate_rows"], profile["outlier_cells"]]])]
    for head, items in (("Cleaning steps", cleaning_log), ("Key findings", insights)):
        e += [Spacer(1, 12), Paragraph(head, st["Heading2"])]
        e += [Paragraph("&bull; " + html.escape(x), st["Normal"]) for x in items]
    if narrative:
        e += [Spacer(1, 12), Paragraph("AI summary", st["Heading2"])]
        e += [Paragraph(html.escape(line), st["Normal"]) for line in narrative.split("\n") if line.strip()]
    doc.build(e)
    return buf.getvalue()
