"""Design system for the site: tokens, CSS and small HTML components.

Every value that comes from a ledger goes through esc() before it reaches the page,
because uploaded files are untrusted.
"""
from __future__ import annotations

from base64 import b64encode
from html import escape

import plotly.graph_objects as go

PINE, PINE_DEEP, BRASS = "#0F4C47", "#0C2F2D", "#C9A24B"
INK, MUTED, LINE, CARD = "#14211F", "#5C6A67", "#E2DED3", "#FFFFFF"
# Risk is ordered, so it is one hue from light to dark, and always labelled in text.
RISK = {"High": "#7E1A1E", "Medium": "#C8563C", "Low": "#E3A58F"}

BRAND_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="8" fill="#0C2F2D"/>
<path d="M8 10h9M8 16h6M8 22h5" stroke="#8FA8A3" stroke-width="2" stroke-linecap="round"/>
<path d="M15 20l3.6 3.6L25.5 12" fill="none" stroke="#C9A24B" stroke-width="3"
 stroke-linecap="round" stroke-linejoin="round"/></svg>"""

TICK_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><path d="M3 8.5l3.2 3.2L13 4.8" '
            'fill="none" stroke="#C9A24B" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def _img(svg: str, size: int) -> str:
    # st.html strips inline <svg>, so icons are embedded as images.
    data = b64encode(svg.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{data}" width="{size}" height="{size}" alt="">'


BRAND_MARK, TICK = _img(BRAND_SVG, 34), _img(TICK_SVG, 14)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');

:root { --pine:#0F4C47; --pine-deep:#0C2F2D; --brass:#C9A24B; --ink:#14211F; --muted:#5C6A67;
        --line:#E2DED3; --card:#FFFFFF; --paper:#F7F5EF;
        --serif:'Fraunces',Georgia,serif; --sans:'Inter',system-ui,sans-serif;
        --mono:'IBM Plex Mono',ui-monospace,monospace; }

html, body, .stApp, .stApp p, .stApp label, .stApp li, .stApp td, .stApp th, .stApp button, .stApp input
  { font-family: var(--sans); }
.stApp { background: var(--paper); color: var(--ink); }
header[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"]
  { display: none; }
[data-testid="stMainBlockContainer"], .block-container
  { max-width: 1180px; padding: 1.1rem 2rem 2.5rem; }

/* Top bar controls */
[data-testid="stPopover"] button, .stDownloadButton button {
  background: var(--card); color: var(--ink); border: 1px solid var(--line); border-radius: 10px;
  font-weight: 500; font-size: .875rem; min-height: 40px; box-shadow: none; transition: border-color .15s, background .15s; }
[data-testid="stPopover"] button:hover, .stDownloadButton button:hover
  { border-color: var(--pine); color: var(--pine); background: #fff; }

/* Section navigation */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); background: transparent; }
.stTabs [data-baseweb="tab"] { height: 46px; padding: 0 14px; background: transparent; color: var(--muted); }
.stTabs [data-baseweb="tab"] p { font-size: .925rem; font-weight: 500; }
.stTabs [aria-selected="true"], .stTabs [aria-selected="true"] p { color: var(--pine); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--brass); height: 3px; border-radius: 3px 3px 0 0; }
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.75rem; }

[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: var(--card); }
[data-testid="stPlotlyChart"] { background: transparent; }
[data-testid="stExpander"] details { background: var(--card); border: 1px solid var(--line); border-radius: 12px; }
.stApp h2, .stApp h3 { font-family: var(--serif); font-weight: 500; letter-spacing: -.01em; color: var(--ink); }

/* Brand */
.ll-brand { display: flex; align-items: center; gap: 11px; }
.ll-brand b { font-family: var(--serif); font-weight: 600; font-size: 1.2rem; letter-spacing: -.01em; color: var(--ink); }

/* Hero */
.ll-hero { background: var(--pine-deep); color: #fff; border-radius: 20px; padding: 56px 52px; margin: 4px 0 14px;
  display: grid; grid-template-columns: minmax(0,1.5fr) minmax(0,1fr); gap: 52px; align-items: center;
  position: relative; overflow: hidden; }
.ll-hero::before { content:""; position:absolute; inset:0; pointer-events:none; opacity:.05;
  background: repeating-linear-gradient(0deg,#fff 0 1px,transparent 1px 34px); }
.ll-hero > * { position: relative; }
.ll-eyebrow { font-family: var(--mono); font-size: .74rem; letter-spacing: .1em; text-transform: uppercase; color: var(--brass); }
.ll-hero h1 { font-family: var(--serif); font-weight: 500; font-size: clamp(2.1rem,4.4vw,3.35rem); line-height: 1.08;
  letter-spacing: -.02em; color: #fff; margin: 14px 0 18px; padding: 0; }
.ll-hero h1 em { font-style: normal; color: var(--brass); }
.ll-hero p { color: #C4D1CE; font-size: 1.04rem; line-height: 1.6; margin: 0; max-width: 34rem; }
.ll-ledger { background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.13); border-radius: 14px; padding: 8px 20px; }
.ll-ledger div { display: flex; justify-content: space-between; align-items: center; gap: 14px; padding: 13px 0;
  border-bottom: 1px solid rgba(255,255,255,.1); }
.ll-ledger div:last-child { border-bottom: 0; }
.ll-ledger span { display: flex; align-items: center; gap: 8px; color: #C4D1CE; font-size: .9rem; }
.ll-ledger b { font-family: var(--mono); font-weight: 500; color: #fff; font-size: 1rem; white-space: nowrap; }

/* How to use it */
.ll-steps { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 14px; margin: 0 0 26px; }
.ll-step { display: flex; gap: 12px; padding: 4px 2px; }
.ll-step i { flex: none; width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--brass); color: #8A6D24;
  font-family: var(--mono); font-style: normal; font-size: .82rem; display: flex; align-items: center; justify-content: center; }
.ll-step b { display: block; font-size: .92rem; font-weight: 600; color: var(--ink); margin-bottom: 2px; }
.ll-step span { font-size: .85rem; color: var(--muted); line-height: 1.45; }

/* Section headings */
.ll-head { margin: 8px 0 18px; }
.ll-head.ll-space { margin-top: 44px; }
.ll-head .ll-eyebrow { color: #8A6D24; }
.ll-head h2 { font-family: var(--serif); font-weight: 500; font-size: 1.7rem; line-height: 1.2; letter-spacing: -.015em;
  margin: 6px 0 6px; padding: 0; color: var(--ink); }
.ll-head p { color: var(--muted); margin: 0; max-width: 46rem; line-height: 1.55; }

/* Test scorecards */
.ll-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 14px; }
.ll-card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 20px; }
.ll-card .n { font-family: var(--serif); font-size: 2.3rem; line-height: 1; color: var(--ink); }
.ll-card .n.zero { color: #A9B2AF; }
.ll-card h3 { font-family: var(--sans); font-size: .93rem; font-weight: 600; letter-spacing: 0; margin: 12px 0 6px; padding: 0; line-height: 1.3; }
.ll-card p { margin: 0; font-size: .84rem; line-height: 1.5; color: var(--muted); }
.ll-card code, .ll-note code { font-family: var(--mono); font-size: .92em; color: var(--pine); background: none; padding: 0; }

/* Small stats */
.ll-stats { display: grid; grid-template-columns: repeat(auto-fit,minmax(170px,1fr)); gap: 14px; margin: 6px 0 18px; }
.ll-stat { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 15px 18px; }
.ll-stat span { display: block; font-size: .8rem; color: var(--muted); margin-bottom: 5px; }
.ll-stat b { font-family: var(--mono); font-weight: 500; font-size: 1.35rem; color: var(--ink); }

.ll-note { background: #FBF6E9; border: 1px solid #EADFC0; border-left: 3px solid var(--brass); border-radius: 10px;
  padding: 14px 18px; color: #4A4326; font-size: .92rem; line-height: 1.55; margin: 4px 0 18px; }
.ll-formula { font-family: var(--mono); font-size: .84rem; color: var(--muted); margin: 0 0 16px; line-height: 1.6; }

/* Priority table */
.ll-tablewrap { background: var(--card); border: 1px solid var(--line); border-radius: 14px; overflow-x: auto; }
.ll-table { width: 100%; border-collapse: collapse; min-width: 720px; font-size: .88rem; }
.ll-table th { text-align: left; font-size: .72rem; letter-spacing: .05em; text-transform: uppercase; font-weight: 600;
  color: var(--muted); padding: 13px 18px; border-bottom: 1px solid var(--line); }
.ll-table td { padding: 13px 18px; border-bottom: 1px solid #EFECE3; vertical-align: middle; color: var(--ink); }
.ll-table tr:last-child td { border-bottom: 0; }
.ll-table .num { text-align: right; font-family: var(--mono); white-space: nowrap; }
.ll-table .id { font-family: var(--mono); font-size: .82rem; white-space: nowrap; }
.ll-table .sub { display: block; color: var(--muted); font-size: .76rem; margin-top: 2px; font-family: var(--sans); }
.ll-pill { display: inline-flex; align-items: center; gap: 6px; font-size: .76rem; font-weight: 600; white-space: nowrap; }
.ll-pill i { width: 9px; height: 9px; border-radius: 3px; display: inline-block; }

.ll-footer { margin-top: 56px; padding-top: 22px; border-top: 1px solid var(--line); display: flex; flex-wrap: wrap;
  justify-content: space-between; gap: 10px; color: var(--muted); font-size: .84rem; }
.ll-footer a { color: var(--pine); font-weight: 500; text-decoration: none; }
.ll-footer a:hover { text-decoration: underline; }

@media (max-width: 960px) {
  .ll-hero { grid-template-columns: 1fr; gap: 30px; padding: 40px 32px; }
  .ll-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .ll-steps { grid-template-columns: 1fr; gap: 10px; }
}
@media (max-width: 560px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: .75rem 16px 2rem; }
  .ll-hero { padding: 30px 22px; border-radius: 16px; }
  .ll-grid { gap: 10px; }
  .ll-card { padding: 16px; }
  .ll-card .n { font-size: 1.9rem; }
  .ll-head h2 { font-size: 1.4rem; }
  .stTabs [data-baseweb="tab"] { padding: 0 10px; }
}
</style>
"""


def esc(value) -> str:
    return escape(str(value), quote=True)


def money(x: float) -> str:
    return f"${x:,.0f}"


def compact_money(x: float) -> str:
    return f"${x / 1e6:,.1f}M" if abs(x) >= 1e6 else money(x)


def brand() -> str:
    return f'<div class="ll-brand">{BRAND_MARK}<b>Tristan Audit Analytics</b></div>'


def hero(flagged: int, total: int, source_note: str, rows: list[tuple[str, str]]) -> str:
    ledger = "".join(f"<div><span>{TICK}{esc(k)}</span><b>{esc(v)}</b></div>" for k, v in rows)
    return f"""<section class="ll-hero"><div>
      <div class="ll-eyebrow">Journal entry testing</div>
      <h1><em>{flagged:,}</em> of {total:,} journal entries need a closer look.</h1>
      <p>This tool tests every entry in a general ledger for the warning signs auditors look for,
      then ranks what to review first. {esc(source_note)}</p>
    </div><div class="ll-ledger">{ledger}</div></section>"""


def steps(items: list[tuple[str, str]]) -> str:
    cells = "".join(f'<div class="ll-step"><i>{n}</i><div><b>{esc(t)}</b><span>{esc(d)}</span></div></div>'
                    for n, (t, d) in enumerate(items, 1))
    return f'<div class="ll-steps">{cells}</div>'


def heading(eyebrow: str, title: str, text: str = "", space: bool = False) -> str:
    body = f"<p>{esc(text)}</p>" if text else ""
    cls = "ll-head ll-space" if space else "ll-head"
    return f'<div class="{cls}"><div class="ll-eyebrow">{esc(eyebrow)}</div><h2>{esc(title)}</h2>{body}</div>'


def test_cards(cards: list[dict]) -> str:
    items = []
    for c in cards:
        zero = " zero" if c["count"] == 0 else ""
        items.append(f'<article class="ll-card"><div class="n{zero}">{c["count"]:,}</div>'
                     f'<h3>{esc(c["name"])}</h3><p>{c["detail"]}</p></article>')
    return f'<div class="ll-grid">{"".join(items)}</div>'


def stats(items: list[tuple[str, str]]) -> str:
    cells = "".join(f'<div class="ll-stat"><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k, v in items)
    return f'<div class="ll-stats">{cells}</div>'


def note(html_text: str) -> str:
    """html_text must already be escaped by the caller."""
    return f'<div class="ll-note">{html_text}</div>'


def risk_pill(level: str) -> str:
    return f'<span class="ll-pill"><i style="background:{RISK.get(level, MUTED)}"></i>{esc(level)}</span>'


def priority_table(df) -> str:
    rows = []
    for r in df.itertuples():
        rows.append(
            f"<tr><td>{risk_pill(r.risk_level)}</td>"
            f'<td class="id">{esc(r.je_id)}<span class="sub">{r.posted_at:%b %d, %Y}</span></td>'
            f"<td>{esc(r.created_by)}</td><td>{esc(r.exceptions)}</td>"
            f'<td class="num">${r.amount:,.2f}</td></tr>')
    return ('<div class="ll-tablewrap"><table class="ll-table"><thead><tr><th>Risk</th><th>Entry</th>'
            '<th>Prepared by</th><th>Why it was flagged</th><th style="text-align:right">Amount</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def footer(repo_url: str) -> str:
    return (f'<footer class="ll-footer"><span>Built by Tristan Phillips. All data is synthetic, and all names '
            f'are fictional.</span><a href="{esc(repo_url)}" target="_blank" rel="noopener">View the code on GitHub</a></footer>')


def style_chart(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=4, r=8, t=8, b=4), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=12.5, color=MUTED),
        hoverlabel=dict(bgcolor=CARD, bordercolor=LINE, font=dict(family="Inter, sans-serif", color=INK, size=13)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None), bargap=0.28)
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=LINE, ticks="", fixedrange=True,
                     automargin=True, showticklabels=True)
    fig.update_yaxes(gridcolor="#ECE8DD", zeroline=False, linecolor="rgba(0,0,0,0)", ticks="", fixedrange=True,
                     automargin=True, showticklabels=True)
    return fig


CHART_CONFIG = {"displayModeBar": False, "responsive": True}
