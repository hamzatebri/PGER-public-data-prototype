"""PGER public-procurement exposure dashboard.

Run from the project folder with: streamlit run dashboard/dashboard.py

All thesis figures and metrics are computed from local frozen files only.
The optional "Live discovery" tab is the one exception: it calls five keyed
discovery sources (Tavily, Guardian, NewsAPI, GNews and NewsData.io), then a
local LM Studio model, to demonstrate the live-evidence
extension described in the methodology - it reads a pre-generated CSV in
data/live_refresh/ (see src/live_evidence_discovery.py). GDELT is checked
separately at low volume because its public DOC API is quota-limited. Neither
live path writes to or is read by any frozen thesis figure or the structural
score.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "data" / "processed" / "public_procurement_exposure_scored_with_event_context.csv"
EVENTS = ROOT / "data" / "processed" / "external_events.csv"
MATCHES = ROOT / "data" / "processed" / "event_portfolio_matches.csv"
EBAE_SAMPLE = ROOT / "data" / "raw" / "ebae_sample" / "SampleFile.EBAE20T422T2_01.csv"
EBAE_QUALITY = ROOT / "data" / "processed" / "ebae_sample_data_quality.csv"
LIVE_REFRESH_DIR = ROOT / "data" / "live_refresh"

CHAIN_STATEMENT = (
    "**Structural review-priority score (50/30/20 observed procurement components) "
    "→ Documented external-event-context flag (separate, time-aligned, category-level) "
    "→ Final user decision (human review).**"
)
SCORE_UNCHANGED_SENTENCE = (
    "Event context appears as a separate review dimension. This keeps the portfolio order "
    "reproducible while allowing the reviewer to filter notices linked to a documented event window."
)


@st.cache_data
def load_portfolio() -> pd.DataFrame:
    frame = pd.read_csv(PORTFOLIO)
    frame["publication_date"] = pd.to_datetime(frame["publication_date"], errors="coerce")
    frame["contract_value_eur"] = pd.to_numeric(frame["contract_value_eur"], errors="coerce")
    return frame


@st.cache_data
def load_events() -> pd.DataFrame:
    events = pd.read_csv(EVENTS, parse_dates=["published_date"])
    return events.sort_values("published_date", ascending=False)


@st.cache_data
def load_ebae_sample() -> pd.DataFrame:
    return pd.read_csv(EBAE_SAMPLE, sep=";", dtype=str)


@st.cache_data
def load_ebae_quality() -> pd.DataFrame:
    return pd.read_csv(EBAE_QUALITY)


st.set_page_config(page_title="PGER Procurement Exposure", layout="wide", page_icon="🧭")

st.markdown(
    """
    <style>
    .stApp { background-color: #0b1220; color: #e7ecf5; }
    section[data-testid="stSidebar"] { background-color: #0f1a2e; border-right: 1px solid #22304a; }
    section[data-testid="stSidebar"] * { color: #cfd9ec !important; }

    .pger-kpi-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin: 4px 0 6px 0;
    }
    .pger-kpi-card {
        background: linear-gradient(160deg, #121f38 0%, #0d1729 100%);
        border: 1px solid #22304a;
        border-left: 3px solid;
        border-radius: 10px;
        padding: 12px 14px 11px 14px;
        min-width: 0;
        transition: border-color 0.15s ease, transform 0.15s ease;
    }
    .pger-kpi-card:hover {
        border-color: #3a4c70;
        transform: translateY(-1px);
    }
    .pger-kpi-top {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 6px;
    }
    .pger-kpi-icon { font-size: 0.95rem; line-height: 1; flex: none; }
    .pger-kpi-label {
        color: #93a4c4;
        font-size: clamp(0.68rem, 1vw, 0.78rem);
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        min-width: 0;
    }
    .pger-kpi-value {
        color: #f2c94c;
        font-weight: 700;
        line-height: 1.15;
        font-size: clamp(1.05rem, 1.6vw, 1.5rem);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .pger-provider-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
        margin: 6px 0 4px 0;
    }
    .pger-provider-chip {
        background: #0f1a2e;
        border: 1px solid #22304a;
        border-left: 3px solid;
        border-radius: 8px;
        padding: 8px 10px;
        min-width: 0;
    }
    .pger-provider-top {
        color: #cfd9ec;
        font-size: 0.82rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .pger-provider-detail {
        color: #8496b8;
        font-size: 0.72rem;
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .pger-band-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 18px;
        margin: 2px 0 10px 0;
    }
    .pger-band-item { display: flex; align-items: baseline; gap: 7px; }
    .pger-band-swatch {
        display: inline-block;
        width: 11px;
        height: 11px;
        border-radius: 3px;
        flex: none;
    }
    .pger-band-name { color: #cfd9ec; font-size: 0.82rem; font-weight: 600; }
    .pger-band-figure { color: #f2c94c; font-size: 0.82rem; font-weight: 700; }
    .pger-band-count { color: #8496b8; font-size: 0.76rem; }

    h1, h2, h3 { color: #f5f7fb !important; }
    h1 { border-bottom: 2px solid #f2c94c; padding-bottom: 8px; display: inline-block; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #22304a; }
    .stTabs [data-baseweb="tab"] {
        background-color: #0f1a2e; border-radius: 8px 8px 0 0; color: #93a4c4;
        padding: 8px 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #16233c !important; color: #f2c94c !important;
        border-bottom: 2px solid #f2c94c;
    }

    div[data-testid="stExpander"] {
        background-color: #0f1a2e; border: 1px solid #22304a; border-radius: 8px;
    }
    div[data-testid="stDataFrame"] { border: 1px solid #22304a; border-radius: 8px; }

    /* st.metric ships dark-on-transparent by default, which reads as washed-out
       grey against this dark background - was near-illegible on Live discovery. */
    div[data-testid="stMetricValue"] { color: #f2c94c !important; font-weight: 700; }
    div[data-testid="stMetricLabel"] { color: #93a4c4 !important; }

    .stAlert { border-radius: 8px; }
    hr { border-color: #22304a; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div style="letter-spacing:0.08em;font-size:0.8rem;color:#f2c94c;font-weight:600;'
    'text-transform:uppercase;margin-bottom:2px;">Public-procurement decision support</div>',
    unsafe_allow_html=True,
)
st.title("PGER public-procurement review")
st.caption(
    "A transparent review workspace built from 24,765 public contracting notices collected from "
    "Spain's Boletín Oficial del Estado (BOE), 2022-2024."
)

df = load_portfolio()
with st.sidebar:
    st.header("Filters")
    sectors = st.multiselect("Procurement category", sorted(df["sector_group"].dropna().unique()))
    regions = st.multiselect("Geographic scope", sorted(df["contracting_authority_region"].dropna().unique()))
    min_value = st.number_input("Minimum contract value (EUR)", min_value=0.0, value=0.0, step=1000.0)
    event_context_only = st.checkbox("Show only notices with a candidate event-context match")
    st.divider()
    st.caption(
        "The portfolio tabs read the same frozen files as the thesis. The optional Discovery snapshot "
        "shows candidate articles retrieved through five routine discovery sources and the local "
        "LM Studio model; the Global Database of Events, Language and Tone (GDELT) is checked separately."
    )

view = df.copy()
if sectors:
    view = view[view["sector_group"].isin(sectors)]
if regions:
    view = view[view["contracting_authority_region"].isin(regions)]
view = view[view["contract_value_eur"] >= min_value]
if event_context_only:
    view = view[view["candidate_event_context_flag"] == 1]

total_value = view["contract_value_eur"].sum()
_kpis = [
    ("📄", "Published notices", f"{len(view):,}", "#2a78d6", None),
    ("🏷️", "Awardee IDs", f"{view['awardee_display_id'].nunique():,}", "#1baf7a", "Distinct awardee display IDs"),
    ("💶", "Published value", f"EUR {total_value / 1e9:,.2f}B", "#f2c94c", f"EUR {total_value:,.0f} exactly"),
    ("🗺️", "Scope values", f"{view['contracting_authority_region'].nunique():,}", "#898781", None),
    ("🔗", "Candidate context", f"{int((view['candidate_event_context_flag'] == 1).sum()):,}", "#eb6834", "Notices selected for an event-source check"),
]
_cards = "".join(
    f'<div class="pger-kpi-card" style="border-left-color:{color};" title="{title or ""}">'
    f'<div class="pger-kpi-top"><span class="pger-kpi-icon">{icon}</span>'
    f'<span class="pger-kpi-label">{label}</span></div>'
    f'<div class="pger-kpi-value">{value}</div>'
    f"</div>"
    for icon, label, value, color, title in _kpis
)
st.markdown(f'<div class="pger-kpi-row">{_cards}</div>', unsafe_allow_html=True)

_live_files = sorted(LIVE_REFRESH_DIR.glob("live_candidates_*.csv")) if LIVE_REFRESH_DIR.exists() else []
if _live_files:
    _live_df = pd.read_csv(_live_files[-1])
    _n_sources = _live_df["source"].nunique()
    _n_candidates = len(_live_df)
    st.markdown(
        f'<div style="display:inline-block;background:#16233c;border:1px solid #f2c94c40;'
        f'border-radius:20px;padding:4px 14px;font-size:0.85rem;color:#f2c94c;margin:4px 0 8px 0;">'
        f'Latest discovery snapshot available: {_n_candidates} candidate records from {_n_sources} providers. '
        f'Open the "Discovery snapshot" tab to inspect the sources.</div>',
        unsafe_allow_html=True,
    )

if len(view):
    # Ordered severity ramp (light -> dark blue), not a status/alarm palette -
    # these bands are a portfolio position, not a risk classification (see
    # SCORE_UNCHANGED_SENTENCE), so red/amber/green would misstate that.
    band_order = ["Routine review", "Focused review", "Priority review"]
    band_colors = {"Routine review": "#86b6ef", "Focused review": "#2a78d6", "Priority review": "#104281"}
    counts = view["review_priority_band"].value_counts()
    n_total = len(view)
    shares = {b: (100.0 * int(counts.get(b, 0)) / n_total if n_total else 0.0) for b in band_order}

    st.markdown("**Review-band composition of the current filtered view**")
    legend_items = "".join(
        f'<div class="pger-band-item">'
        f'<span class="pger-band-swatch" style="background:{band_colors[b]};"></span>'
        f'<span class="pger-band-name">{b.replace(" review", "")}</span>'
        f'<span class="pger-band-figure">{shares[b]:.1f}%</span>'
        f'<span class="pger-band-count">({int(counts.get(b, 0)):,})</span>'
        f'</div>'
        for b in band_order
    )
    st.markdown(f'<div class="pger-band-legend">{legend_items}</div>', unsafe_allow_html=True)

    # Text-free stacked strip: at a 49/40/10 split the narrowest segment can't fit a
    # legible label inside it (Plotly rotates or drops overflow text), so the numbers
    # live in the legend row above and this bar shows proportion only.
    band_fig = go.Figure()
    for band in band_order:
        band_fig.add_trace(
            go.Bar(
                x=[shares[band]],
                y=["Current filtered view"],
                orientation="h",
                name=band.replace(" review", ""),
                marker_color=band_colors[band],
                marker_line_color="#0d1729",
                marker_line_width=1,
                hovertemplate=f"{band}: %{{x:.1f}}%% ({int(counts.get(band, 0)):,} notices)<extra></extra>",
            )
        )
    band_fig.update_layout(
        barmode="stack",
        height=54,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(range=[0, 100], showticklabels=False, showgrid=False, fixedrange=True),
        yaxis=dict(showticklabels=False, fixedrange=True),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(band_fig, width='stretch', config={"displayModeBar": False})
    st.caption(
        f"{n_total:,} notices are visible after the current filters. Routine, Focused and Priority "
        "show relative positions in the portfolio review order."
    )

st.markdown(CHAIN_STATEMENT)
st.caption(SCORE_UNCHANGED_SENTENCE)

tab_priority, tab_event, tab_profile, tab_ebae, tab_live = st.tabs(
    ["Priority queue", "Event context", "Portfolio profile", "EBAE sample (supplementary)", "Discovery snapshot"]
)

# ---------------------------------------------------------------- Priority queue
with tab_priority:
    st.subheader("Review priorities")
    st.write(
        "This view shows which published notices appear first in the review order and which observed "
        "components place them there."
    )
    with st.expander("How the review-priority score is calculated"):
        st.write(
            "The score is a transparent portfolio ordering. It combines the contract-value percentile "
            "(50%), the awardee's value share within the observed contracting authority portfolio (30%), "
            "and the awardee's share of that authority's published notices (20%)."
        )
        st.caption(
            "The first component describes the size of one notice. The other two describe the observed "
            "buyer-awardee relationship by value and by notice frequency. "
            "A later company pilot can add inventory, lead time and approved-alternative information."
        )

    n_options = [15, 25, 50, 100]
    n_selected = st.select_slider(
        "Show top N by review-priority score", options=n_options, value=15,
        help="The chart's height grows with N so every row stays readable - scroll to see the rest.",
    )
    top = view.sort_values("review_priority_score", ascending=False).head(n_selected).copy()
    if not top.empty:
        # A bar chart forces two expectations to line up: sort order and bar LENGTH must
        # encode the same metric, or the chart reads as broken (viewers expect longer =
        # higher-ranked). At the top of a category-concentrated portfolio the score
        # itself clusters within ~0.8 points (see Section 5.4), so a bar sized by score
        # looks flat, and a bar sized by contract value instead breaks the length/order
        # link. The documented fix for closely-spaced values compared against each other
        # (not against zero) is a Cleveland dot plot, zoomed to the real data range -
        # position, not length, carries the comparison, so a non-zero axis is legitimate
        # here (Few, "Dot Plots: A Useful Alternative to Bar Charts"; matches this
        # thesis's own Figure 6, which uses the identical device for the same reason).
        top = top.sort_values("review_priority_score").reset_index(drop=True)
        top["rank"] = range(len(top), 0, -1)
        top["value_musd"] = top["contract_value_eur"] / 1e6
        parsed_date = pd.to_datetime(top["publication_date"], errors="coerce")
        top["date_label"] = parsed_date.dt.strftime("%b %Y").fillna("date n/a")
        top["label"] = "#" + top["rank"].astype(str) + "  " + top["awardee_display_id"]
        top["flagged"] = top["candidate_event_context_flag"] == 1

        comp_cols = ["value_percentile", "authority_awardee_share_percentile", "authority_awardee_notice_share_percentile"]
        x_lo = max(0.0, min(top[comp_cols + ["review_priority_score"]].min().min() - 0.01, 0.99))
        y = top["label"]

        dot_fig = go.Figure()
        for yi, xi in zip(y, top["review_priority_score"]):
            dot_fig.add_trace(go.Scatter(
                x=[x_lo, xi], y=[yi, yi], mode="lines",
                line={"color": "#3a4c70", "width": 1.2}, showlegend=False, hoverinfo="skip",
            ))
        dot_fig.add_trace(go.Scatter(
            x=top["value_percentile"], y=y, mode="markers", name="Value percentile",
            marker={"color": "#2a78d6", "size": 9},
            hovertemplate="Value percentile: %{x:.3f}<extra></extra>",
        ))
        dot_fig.add_trace(go.Scatter(
            x=top["authority_awardee_share_percentile"], y=y, mode="markers", name="Relationship value share",
            marker={"color": "#1baf7a", "size": 9},
            hovertemplate="Relationship value share: %{x:.3f}<extra></extra>",
        ))
        dot_fig.add_trace(go.Scatter(
            x=top["authority_awardee_notice_share_percentile"], y=y, mode="markers", name="Notice share",
            marker={"color": "#eb6834", "size": 9},
            hovertemplate="Authority-awardee notice share: %{x:.3f}<extra></extra>",
        ))
        dot_fig.add_trace(go.Scatter(
            x=top["review_priority_score"], y=y, mode="markers", name="Review-priority score",
            marker={"color": "#f2c94c", "size": 13, "symbol": "diamond", "line": {"color": "#0d1729", "width": 1}},
            hovertemplate="Review-priority score: %{x:.3f}<extra></extra>",
        ))
        flagged_rows = top[top["flagged"]]
        if not flagged_rows.empty:
            dot_fig.add_trace(go.Scatter(
                x=[x_lo] * len(flagged_rows), y=flagged_rows["label"], mode="markers",
                name="Candidate event context", marker={"color": "#eb6834", "size": 11, "symbol": "star"},
                hovertemplate="Candidate event-context match<extra></extra>",
            ))
        # Height scales with row count so each row keeps the same vertical space regardless of
        # N - a fixed height here is exactly what would "break" at N=100 (rows would compress
        # until the dots overlap and the labels become illegible).
        row_px = 34 if len(top) <= 25 else 26
        dot_fig.update_layout(
            height=max(240, 30 + row_px * len(top)),
            margin=dict(l=10, r=25, t=15, b=10),
            xaxis=dict(range=[x_lo, 1.005], title="Percentile / score (0 to 1; axis zoomed)"),
            yaxis=dict(title=""),
            showlegend=False,
        )
        st.markdown(
            f"**Top {len(top)} by review-priority score** "
            "(rank #1 at top; axis zoomed to distinguish close values)"
        )
        dot_legend_items = "".join(
            f'<div class="pger-band-item">'
            f'<span class="pger-band-swatch" style="background:{color};{"border-radius:50%;" if shape=="circle" else "clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);" if shape=="diamond" else ""}"></span>'
            f'<span class="pger-band-name">{name}</span>'
            f'</div>'
            for name, color, shape in [
                ("Value percentile", "#2a78d6", "circle"),
                ("Relationship value share", "#1baf7a", "circle"),
                ("Relationship notice share", "#eb6834", "circle"),
                ("Review-priority score", "#f2c94c", "diamond"),
            ]
        )
        st.markdown(f'<div class="pger-band-legend">{dot_legend_items}</div>', unsafe_allow_html=True)
        st.plotly_chart(dot_fig, width='stretch')
        n_categories = top["sector_group"].nunique()
        if n_categories == 1:
            concentration_note = (
                f" The current filter contains one category: {top['sector_group'].iloc[0]}. "
                "Clear the category filter to compare priorities across the full portfolio."
            )
        else:
            concentration_note = f" {n_categories} categories appear in the current top {len(top)}."
        st.caption(
            "Rank #1 (top row) has the highest review-priority score; the gold diamond is that score, "
            "the three coloured dots are its components (Section 3.7), and the axis is zoomed because "
            "the leading scores cluster within a narrow interval - "
            f"an unzoomed 0-1 bar would show {len(top)} nearly identical bars. Hover over a point or use "
            f"the table below to inspect the exact value, date and category.{concentration_note}"
        )

    ranked = (
        view.groupby(["awardee_display_id", "sector_group"], as_index=False)
        .agg(
            contract_count=("exposure_id", "count"),
            awarded_value_eur=("contract_value_eur", "sum"),
            review_priority_score=("review_priority_score", "mean"),
            latest_contract=("publication_date", "max"),
        )
        .sort_values(["review_priority_score", "awarded_value_eur"], ascending=False)
        .head(25)
    )
    st.markdown("**Awardee-category summary, using the mean notice score**")
    st.dataframe(
        ranked, width='stretch', hide_index=True,
        column_config={
            "awardee_display_id": st.column_config.TextColumn("Awardee"),
            "sector_group": st.column_config.TextColumn("Category"),
            "contract_count": st.column_config.NumberColumn("Notices", format="%d"),
            "awarded_value_eur": st.column_config.NumberColumn("Awarded value", format="EUR %,.0f"),
            "review_priority_score": st.column_config.ProgressColumn(
                "Review-priority score", min_value=0.0, max_value=1.0, format="%.3f",
            ),
            "latest_contract": st.column_config.DateColumn("Latest contract"),
        },
    )
    st.download_button(
        "Download this ranked-awardee table as CSV",
        ranked.to_csv(index=False).encode("utf-8"),
        file_name="pger_ranked_awardees.csv",
        mime="text/csv",
    )

    st.subheader("Published BOE notices")
    all_notices = view.sort_values("contract_value_eur", ascending=False)[
        [
            "exposure_id", "awardee_display_id", "contracting_authority_name", "sector_group",
            "contract_value_eur", "review_priority_score", "review_priority_band",
            "publication_date", "candidate_event_context_flag", "source_url",
        ]
    ].rename(columns={"candidate_event_context_flag": "event_context"})
    notices = all_notices.head(100).copy()
    notices["event_context"] = notices["event_context"].map({1: "Candidate", 0: ""})
    st.dataframe(
        notices,
        width='stretch',
        hide_index=True,
        column_config={
            "source_url": st.column_config.LinkColumn("BOE source"),
            "review_priority_score": st.column_config.ProgressColumn("Priority score", min_value=0.0, max_value=1.0, format="%.3f"),
            "contract_value_eur": st.column_config.NumberColumn("Contract value", format="EUR %,.0f"),
            "publication_date": st.column_config.DateColumn("Published"),
            "awardee_display_id": st.column_config.TextColumn("Awardee"),
            "sector_group": st.column_config.TextColumn("Category"),
        },
    )
    st.download_button(
        "Download all filtered notices as CSV",
        all_notices.assign(event_context=all_notices["event_context"].map({1: "Candidate", 0: ""})).to_csv(index=False).encode("utf-8"),
        file_name="pger_filtered_boe_notices.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------- Candidate event context
with tab_event:
    st.subheader("Why is this notice a candidate for an event-source check?")
    flagged_view = view.loc[view["candidate_event_context_flag"] == 1].copy()
    if not flagged_view.empty:
        # One-at-a-time drill-down alone hides the actual distribution: in the full portfolio,
        # 50 of 51 candidate notices share one campaign, so scrolling the dropdown mostly shows
        # the same answer 50 times. A real chart, not a text summary, makes that concentration
        # obvious in one glance - the same "lead with a chart, not a stat line" standard applied
        # to every other tab.
        camp_summary = (
            flagged_view.groupby("candidate_campaign_ids", as_index=False)
            .agg(
                notices=("exposure_id", "count"),
                value_eur=("contract_value_eur", "sum"),
                category_proxy=("candidate_event_category_proxy", "first"),
            )
            .sort_values("notices")
        )
        camp_summary["label"] = camp_summary["candidate_campaign_ids"].str.replace("CAMPAIGN-", "", regex=False).str.replace("-", " ")
        campaign_word = "campaign" if len(camp_summary) == 1 else "campaigns"
        st.markdown(f"**{len(flagged_view)} candidate notices across {len(camp_summary)} {campaign_word}**")
        fig_camp = go.Figure(go.Bar(
            x=camp_summary["notices"], y=camp_summary["label"], orientation="h",
            marker_color="#eb6834",
            text=[f"  {n} notice{'s' if n != 1 else ''} | EUR {v/1e6:,.1f}M | {c}"
                  for n, v, c in zip(camp_summary["notices"], camp_summary["value_eur"], camp_summary["category_proxy"])],
            textposition="outside", textfont={"size": 12, "color": "#c3c2b7"},
            hovertemplate="%{y}: %{x} notices<extra></extra>",
        ))
        fig_camp.update_layout(
            height=110 + 55 * len(camp_summary), margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(title="Candidate notices", range=[0, camp_summary["notices"].max() * 1.42]),
            yaxis=dict(title=""), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_camp, width='stretch')
        top_share = camp_summary["notices"].max() / camp_summary["notices"].sum()
        if len(camp_summary) > 1 and top_share >= 0.8:
            st.caption(
                f"{int(camp_summary['notices'].max())} of the {int(camp_summary['notices'].sum())} candidate "
                "notices belong to the EU sanctions campaign; one belongs to the Red Sea campaign."
            )
        else:
            st.caption("Candidate notices grouped by the campaign that matched their public category, scope proxy and date.")

        st.markdown("**Inspect one candidate notice**")
        flagged_view["value_musd"] = flagged_view["contract_value_eur"] / 1e6
        flagged_view["date_label"] = pd.to_datetime(flagged_view["publication_date"], errors="coerce").dt.strftime("%b %Y").fillna("date n/a")
        flagged_view["option_label"] = (
            flagged_view["exposure_id"] + "  ·  " + flagged_view["sector_group"].str.slice(0, 24) + "  ·  EUR "
            + flagged_view["value_musd"].round(1).astype(str) + "M  ·  " + flagged_view["date_label"]
        )
        label_to_id = dict(zip(flagged_view["option_label"], flagged_view["exposure_id"]))
        selected_label = st.selectbox(
            "Select a candidate notice to inspect", sorted(label_to_id.keys()),
        )
        selected = label_to_id[selected_label]
        row = view.loc[view["exposure_id"] == selected].iloc[0]
        st.markdown(
            f"**Candidate campaign(s):** {row['candidate_campaign_ids']}  \n"
            f"**Category proxy:** {row['candidate_event_category_proxy']}  \n"
            f"**Matching rule:** {row['candidate_event_matching_rule']}  \n"
            f"**Event date(s):** {row['candidate_event_published_dates']}  \n"
            f"**Source(s):** {row['candidate_event_source_urls']}"
        )
        st.caption(
            "The rule uses the notice's public category, broad contracting scope and date to suggest a source check. "
            "It does not identify the awardee's country or transport route. The reviewer can open the source and "
            "compare it with current contract and operational information."
        )
    else:
        st.write("No notice in the current filtered view meets the candidate event-context rules.")

    st.subheader("External evidence registry")
    st.markdown(
        "These dated public sources provide context for review.  \n"
        "Each one is shown with its source type, evidence strength, and campaign grouping, so the "
        "user can check the original record before interpreting a procurement exposure.  \n"
        "Two dated updates about the same disruption, such as the Red Sea/Gulf of Aden records, are "
        "grouped under one campaign to avoid double counting."
    )
    events_full = load_events()
    campaigns_tl = events_full.drop_duplicates("event_campaign_id").sort_values("campaign_start_date").copy()
    if not campaigns_tl.empty:
        campaigns_tl["start"] = pd.to_datetime(campaigns_tl["campaign_start_date"])
        campaigns_tl["end"] = pd.to_datetime(campaigns_tl["campaign_end_date"])
        campaigns_tl["label"] = campaigns_tl["event_campaign_id"].str.replace("CAMPAIGN-", "", regex=False).str.replace("-", " ")
        fig_tl = go.Figure()
        for _, c in campaigns_tl.iterrows():
            fig_tl.add_trace(go.Scatter(
                x=[c["start"], c["end"]], y=[c["label"], c["label"]], mode="lines+markers",
                line={"color": "#eb6834", "width": 8}, marker={"size": 9, "color": "#eb6834"},
                hovertemplate=f"{c['label']}: %{{x|%Y-%m-%d}}<extra></extra>", showlegend=False,
            ))
        fig_tl.update_layout(
            height=160 + 30 * len(campaigns_tl), margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(title=""), yaxis=dict(title=""),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.markdown("**Documented event-window timeline**")
        st.plotly_chart(fig_tl, width='stretch')
        st.caption(
            "Each bar is the matching window used by the crosswalk (Section 3.6): a finite 180 days "
            "from a single official notice, or extended only when a second dated official record "
            "documents continuation (the Red Sea/Gulf of Aden campaign).  \n"
            "A notice can only become a candidate if its publication date falls inside one of these windows."
        )

    events_display = events_full[[
        "event_campaign_id", "published_date", "source_name", "event_family", "geography",
        "affected_category", "evidence_strength", "campaign_start_date", "campaign_end_date", "source_url",
    ]]
    st.dataframe(
        events_display,
        width='stretch',
        hide_index=True,
        column_config={"source_url": st.column_config.LinkColumn("Source")},
    )
    st.download_button(
        "Download this evidence registry as CSV",
        events_display.to_csv(index=False).encode("utf-8"),
        file_name="pger_external_evidence_registry.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------- Portfolio profile
with tab_profile:
    st.subheader("Value by procurement category")
    n_cats_in_view = view["sector_group"].nunique()
    if n_cats_in_view <= 1:
        st.info(
            f"The current filter leaves only {n_cats_in_view} category "
            f"({view['sector_group'].iloc[0] if n_cats_in_view else 'none'}) - a value-by-category "
            "comparison needs at least two. Clear the category filter in the sidebar to compare across "
            "categories, or use the other charts on this tab, which stay useful for a single category."
        )
    else:
        cat_summary = (
            view.groupby("sector_group", as_index=False)["contract_value_eur"].sum()
            .sort_values("contract_value_eur", ascending=False)
            .head(10)
        )
        cat_total = view["contract_value_eur"].sum()
        cat_summary["pct"] = cat_summary["contract_value_eur"] / cat_total * 100 if cat_total else 0
        cat_summary["value_label"] = cat_summary.apply(
            lambda r: f"  EUR {r['contract_value_eur']/1e9:,.2f}B ({r['pct']:.0f}%)" if r["contract_value_eur"] >= 1e9
            else f"  EUR {r['contract_value_eur']/1e6:,.0f}M ({r['pct']:.0f}%)", axis=1,
        )
        cat_summary = cat_summary.sort_values("contract_value_eur")
        fig_cat = go.Figure(go.Bar(
            x=cat_summary["contract_value_eur"], y=cat_summary["sector_group"], orientation="h",
            marker_color="#2a78d6",
            text=cat_summary["value_label"], textposition="outside", textfont={"size": 11, "color": "#c3c2b7"},
            hovertemplate="%{y}: EUR %{x:,.0f}<extra></extra>",
        ))
        fig_cat.update_layout(
            height=420, margin=dict(l=10, r=110, t=20, b=40),
            xaxis=dict(title="Awarded value (EUR)", range=[0, cat_summary["contract_value_eur"].max() * 1.28]),
            yaxis=dict(title=""), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_cat, width='stretch')
        st.caption(
            "Top 10 Common Procurement Vocabulary divisions by awarded value in the current filtered view."
        )

    st.subheader("Monthly awarded value")
    monthly = view.set_index("publication_date").resample("MS")["contract_value_eur"].sum().reset_index()
    if not monthly.empty:
        fig_month = go.Figure(go.Scatter(
            x=monthly["publication_date"], y=monthly["contract_value_eur"] / 1e6,
            mode="lines", line={"color": "#2a78d6", "width": 2}, fill="tozeroy",
            fillcolor="rgba(42,120,214,0.12)", hovertemplate="%{x|%b %Y}: EUR %{y:,.1f}M<extra></extra>",
        ))
        # Documented external-event campaigns, deduplicated - mirrors Figure 4's device so the
        # interactive view carries the same context the static thesis figure already does.
        events_df = load_events()
        campaigns = events_df.drop_duplicates("event_campaign_id").sort_values("campaign_start_date")
        y_max = (monthly["contract_value_eur"] / 1e6).max()
        for _, ev in campaigns.iterrows():
            start = pd.to_datetime(ev["campaign_start_date"])
            if start < monthly["publication_date"].min() or start > monthly["publication_date"].max():
                continue
            fig_month.add_vline(x=start, line_dash="dash", line_color="#eb6834", line_width=1.1, opacity=0.8)
            fig_month.add_annotation(
                x=start, y=y_max * 1.08, text=ev["event_campaign_id"].replace("CAMPAIGN-", "").replace("-", " "),
                showarrow=False, font={"size": 9, "color": "#eb6834"}, yanchor="bottom",
            )
        peak = monthly.loc[monthly["contract_value_eur"].idxmax()]
        fig_month.update_layout(
            height=400, margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(title=""), yaxis=dict(title="Awarded value (EUR millions)", range=[0, y_max * 1.25]),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_month, width='stretch')
        st.caption(
            f"Peak month: {peak['publication_date']:%B %Y} at EUR {peak['contract_value_eur']/1e6:,.0f}M.  \n"
            "Dashed lines mark the start of a documented external-event window (Section 3.6): they show "
            "timing overlap only, not that the event caused that month's value."
        )
    else:
        st.write("No notices in the current filtered view.")

    st.subheader("Priority-review share by category")
    band_by_cat = (
        view.groupby("sector_group")["review_priority_band"]
        .value_counts(normalize=True).unstack().fillna(0).reset_index()
    )
    if "Priority review" in band_by_cat.columns and not band_by_cat.empty:
        band_by_cat["n"] = view.groupby("sector_group").size().values
        band_by_cat = band_by_cat[band_by_cat["n"] >= 20]  # drop categories too small for a stable share
        top_share = band_by_cat.sort_values("Priority review", ascending=False).head(10).sort_values("Priority review")
        fig_share = go.Figure(go.Bar(
            x=top_share["Priority review"] * 100, y=top_share["sector_group"], orientation="h",
            marker_color="#104281",
            text=[f"  {v:.0f}%" for v in top_share["Priority review"] * 100], textposition="outside",
            textfont={"size": 11, "color": "#c3c2b7"},
            customdata=top_share["n"], hovertemplate="%{y}: %{x:.1f}%% of %{customdata:,} notices<extra></extra>",
        ))
        fig_share.update_layout(
            height=380, margin=dict(l=10, r=60, t=20, b=40),
            xaxis=dict(title="Share of the category's own notices in Priority review (%)", range=[0, 100]),
            yaxis=dict(title=""), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_share, width='stretch')
        st.caption(
            "Categories with at least 20 notices in the current filtered view, ranked by the "
            "proportion of their own notices that land in Priority review, not by raw count."
        )
    else:
        st.write("Not enough notices in the current filtered view to compute a stable per-category share.")

# ---------------------------------------------------------------- EBAE sample
with tab_ebae:
    st.subheader("EBAE sample: Spanish firm context")
    st.caption("Supplementary secondary data · 47 observations from 15 anonymised firms · kept separate from the PGER score")
    st.markdown(
        "This view reads a public Banco de España survey sample containing 47 quarterly observations "
        "from 15 anonymised firms. Eight firms answered the wave-7 question about supply difficulties "
        "linked to the war in Ukraine. The sample adds business context and remains separate from the "
        "BOE portfolio and the PGER score."
    )

    with st.expander("Methodology: how this sample was downloaded, cleaned, transformed and visualised"):
        st.markdown(
            "**1. Data source**  \n"
            "The Banco de España Survey on Business Activity (EBAE) is downloaded as a public sample "
            "extract from the BELab microdata portal, release `EBAE20T422T2_01`.  \n"
            "The matching technical guide for the same release explains the variables and response codes.  \n"
            "Both source files and the download date are recorded in "
            "`docs/EBAE_SAMPLE_SOURCE_NOTE.md`, using the same reproducibility process as the "
            "main BOE file (Section 3.4)."
        )
        st.markdown(
            "**2. Loading**  \n"
            "The file is semicolon-delimited, not comma-delimited.  \n"
            "Every column is loaded as text (`dtype=str`) rather than inferred as numeric.  \n"
            "Fields like `ola` (wave) and `impguerra_sum` (war-impact) are categorical survey codes, "
            "not quantities, so letting pandas infer a numeric type would silently invite arithmetic "
            "(an “average wave number”) that has no real meaning."
        )
        st.markdown(
            "**3. Cleaning**  \n"
            "The analysis is restricted to columns present in the downloaded sample. Missing values "
            "remain missing, and response codes are mapped only with the matching release guide."
        )
        st.markdown(
            "**4. Transformation**  \n"
            "Three derived views are built from the 47 survey observations:"
        )
        st.markdown(
            "- A data-quality summary: row/variable counts, which waves and quarters are actually "
            "present, and how many rows answer the war-impact question.\n"
            "- The war-impact responses, restricted to the 8 rows that are non-null (only wave 7 "
            "records that variable), with the four response codes (1-4) mapped to their plain-language "
            "label.\n"
            "- A sector breakdown by `rama12`."
        )
        st.markdown(
            "The anonymised `codigo` identifier is shortened for display only.  \n"
            "The full 64-character value is used only to connect repeated observations from the same "
            "anonymised firm. It is never joined to BOE data."
        )
        st.markdown(
            "**5. Visualisation**  \n"
            "Both charts below are ordered bar charts, matching the other categorical comparisons in "
            "the project.  \n"
            "A bar chart is the right form for comparing a small number of named categories.  \n"
            "An ordinal Likert scale is kept in its natural order rather than sorted by size.  \n"
            "Every bar carries a direct count label so a reviewer never has to eyeball a gridline."
        )

    ebae = load_ebae_sample()
    if EBAE_QUALITY.exists():
        q = load_ebae_quality().iloc[0]
        # A raw one-row, six-wide-column dataframe truncated the longest values (survey waves,
        # sector list) off the right edge of the screen - small labelled cards read fully instead.
        dq_items = [
            ("Survey observations", f"{int(q['rows'])}", "#2a78d6"),
            ("Distinct firm IDs", f"{int(q['unique_anonymised_firms'])}", "#1baf7a"),
            ("Variables recorded", f"{int(q['variables'])}", "#1baf7a"),
            ("Survey waves present", str(q["waves_present"]), "#f2c94c"),
            ("Quarters covered", str(q["quarters_present"]), "#898781"),
            ("War-impact answered", f"{int(q['impguerra_sum_non_null_rows'])} of {int(q['rows'])} rows", "#eb6834"),
        ]
        dq_cards = "".join(
            f'<div class="pger-kpi-card" style="border-left-color:{color};">'
            f'<div class="pger-kpi-top"><span class="pger-kpi-label">{label}</span></div>'
            f'<div class="pger-kpi-value" style="font-size:1.05rem;white-space:normal;overflow:visible;'
            f'text-overflow:clip;">{value}</div></div>'
            for label, value, color in dq_items
        )
        st.markdown(f'<div class="pger-kpi-row">{dq_cards}</div>', unsafe_allow_html=True)

    war_col = "impguerra_sum"
    if war_col in ebae.columns:
        likert = {"1": "Very negative", "2": "Negative", "3": "Neutral", "4": "Positive"}
        counts = ebae[war_col].dropna().value_counts()
        counts = counts.reindex(list(likert.keys())).fillna(0).astype(int)
        n_answered = int(counts.sum())
        st.markdown(f"**War-in-Ukraine supply impact** (n={n_answered} of {len(ebae)} sample rows; only wave 7 records this question)")
        fig_war = go.Figure(go.Bar(
            x=[likert[k] for k in counts.index], y=counts.values,
            marker_color=["#e34948", "#eb6834", "#898781", "#1baf7a"],
            text=[str(v) for v in counts.values], textposition="outside",
            textfont={"size": 12, "color": "#c3c2b7"},
        ))
        fig_war.update_layout(
            height=300, margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(title=""), yaxis=dict(title="Number of surveyed firms", range=[0, counts.max() * 1.3 or 1]),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_war, width='stretch')
        st.caption(
            "Independent, general Spanish-firm survey evidence about the war in Ukraine as a macro "
            "phenomenon.  \n"
            "Not evidence about any specific BOE-matched exposure, and not the same firms as the BOE "
            "portfolio (matches Figure A1 in the thesis)."
        )

    if "rama12" in ebae.columns:
        sector_counts = ebae["rama12"].dropna().value_counts().sort_values()
        st.markdown("**Sample composition by sector (rama12)**")
        fig_sector = go.Figure(go.Bar(
            x=sector_counts.values, y=sector_counts.index, orientation="h",
            marker_color="#2a78d6",
            text=[str(v) for v in sector_counts.values], textposition="outside",
            textfont={"size": 11, "color": "#c3c2b7"},
        ))
        fig_sector.update_layout(
            height=240, margin=dict(l=10, r=40, t=10, b=10),
            xaxis=dict(title="Firm rows in the sample", range=[0, sector_counts.max() * 1.25]),
            yaxis=dict(title=""), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_sector, width='stretch')
        st.caption(
            "All 47 sample rows by `rama12` sector code, shown to make the sample's real composition "
            "visible at a glance.  \n"
            "Not a claim that it is representative of Spanish firms generally: it is a small public "
            "extract, not a random sample (see the Limitation above and §5.4)."
        )

    st.write(f"Sample preview ({len(ebae)} anonymised firm rows):")
    preview = ebae[["codigo", "ola", "trim", "rama12", "gempleo", "impguerra_sum"]].head(15).copy()
    # The full 64-character anonymised hash has no interpretive value and, shown in full, pushed
    # every other column off the right edge of the screen - keep a short recognisable tail only.
    preview["codigo"] = preview["codigo"].str[-8:].apply(lambda s: f"…{s}")
    st.dataframe(
        preview, width='stretch', hide_index=True,
        column_config={
            "codigo": st.column_config.TextColumn("Anonymised firm ID"),
            "ola": st.column_config.NumberColumn("Wave"),
            "trim": st.column_config.TextColumn("Quarter"),
            "rama12": st.column_config.TextColumn("Sector (rama12)"),
            "gempleo": st.column_config.TextColumn("Employment size band"),
            "impguerra_sum": st.column_config.TextColumn("War-impact response, 1-4 (wave 7 only)"),
        },
    )
    st.download_button(
        "Download this EBAE sample preview as CSV",
        preview.to_csv(index=False).encode("utf-8"),
        file_name="pger_ebae_sample_preview.csv",
        mime="text/csv",
    )
    st.caption(
        "Citation: Bank of Spain Survey on Business Activity - EBAE. BELab. Bank of Spain/CORPME, "
        "Spanish Association of Property and Trade Registrars. DOI: 10.48719/BELab.EBAE20T422T2_01."
    )

# ---------------------------------------------------------------- Discovery snapshot (optional)
with tab_live:
    st.subheader("Saved discovery snapshot: candidate events beyond the frozen registry")
    st.caption("Outside all frozen thesis metrics · Never merged into the structural score or the event-context flag")
    st.markdown(
        "This tab shows the latest saved output from the optional discovery script. It does not touch "
        "the frozen thesis evidence above.  \n"
        "Running `src/live_evidence_discovery.py` searches five routine sources (Tavily, Guardian, "
        "NewsAPI, GNews and NewsData.io) for articles matching the "
        "same three event families as the official registry, removes duplicate URLs, and asks a local "
        "language model (openai/gpt-oss-20b, via LM Studio on this machine) to classify each one - the "
        "same model and prompt already evaluated in Section 4.3.  \n"
        "The Global Database of Events, Language and Tone (GDELT) is checked separately with one small "
        "request, at most once every 24 hours, because its "
        "public DOC service is quota-limited. Its last saved check appears in the service row below.  \n"
        "A human would still check the original source and add a genuinely relevant, well-documented "
        "candidate to the official registry by hand."
    )
    live_files = sorted(LIVE_REFRESH_DIR.glob("live_candidates_*.csv")) if LIVE_REFRESH_DIR.exists() else []
    if live_files:
        latest = live_files[-1]
        live_df = pd.read_csv(latest)
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Candidates retrieved", f"{len(live_df):,}")
        col_b.metric("Assigned to an event family", f"{int((live_df['local_llm_predicted_family'] != 'not_relevant').sum()):,}")
        routine_sources = 5
        col_c.metric(
            "Routine sources represented",
            f"{live_df['source'].nunique()} of {routine_sources}",
        )
        col_d.metric("Published date available", f"{int(live_df['published_date'].fillna('').astype(str).str.strip().ne('').sum())} of {len(live_df)}")

        date_tag = latest.stem.replace("live_candidates_", "")
        status_path = LIVE_REFRESH_DIR / f"live_provider_status_{date_tag}.json"
        if status_path.exists():
            import json as _json

            provider_status = _json.loads(status_path.read_text(encoding="utf-8"))
            provider_display = {
                "tavily": "Tavily", "guardian": "Guardian", "newsapi": "NewsAPI",
                "gnews": "GNews", "newsdata": "NewsData.io", "gdelt": "GDELT",
                "lm_studio": "LM Studio",
            }
            chips = []
            for provider, label in provider_display.items():
                info = provider_status.get(provider, {})
                ok = info.get("ok", False)
                attempts = int(info.get("queries_attempted", 0))
                failures = int(info.get("queries_failed", 0))
                n = info.get("candidates_retrieved", 0)
                raw = info.get("last_error") or ""
                state = info.get("status", "")
                configured = info.get("configured", False)
                checked_at = (info.get("last_checked_utc") or info.get("checked_at") or "")[:10]
                if not configured:
                    detail = "not configured"
                    accent, icon = "#898781", "-"
                elif state == "checked_separately" and ok:
                    detail = f"available · checked {checked_at or 'separately'}"
                    accent, icon = "#1baf7a", "✓"
                elif state == "checked_separately":
                    detail = f"separate check needed{f' · {checked_at}' if checked_at else ''}"
                    accent, icon = "#f2c94c", "!"
                elif attempts == 0:
                    detail = "configured · no request in this run"
                    accent, icon = "#898781", "-"
                elif failures == 0:
                    detail = f"successful · {n} result{'s' if n != 1 else ''}"
                    accent, icon = "#1baf7a", "✓"
                elif ok and n:
                    detail = f"partial · {n} results · {failures}/{attempts} queries failed"
                    accent, icon = "#f2c94c", "!"
                else:
                    detail = f"failed · {(raw or 'no response')[:40]}"
                    accent, icon = "#eb6834", "✗"
                chips.append(
                    f'<div class="pger-provider-chip" style="border-left-color:{accent};" title="{raw if not ok else ""}">'
                    f'<div class="pger-provider-top"><span style="color:{accent};">{icon}</span> {label}</div>'
                    f'<div class="pger-provider-detail">{detail}</div></div>'
                )
            st.markdown(
                '<div style="font-size:0.85rem;color:#93a4c4;margin:10px 0 4px 0;">'
                f"Saved service status for snapshot {date_tag}:</div>"
                f'<div class="pger-provider-row">{"".join(chips)}</div>',
                unsafe_allow_html=True,
            )
        provider_counts = live_df["source"].value_counts().sort_values()
        col_prov, col_agree = st.columns(2)
        with col_prov:
            st.markdown("**Candidates retrieved by provider**")
            fig_prov = go.Figure(go.Bar(
                x=provider_counts.values, y=provider_counts.index, orientation="h",
                marker_color="#2a78d6", text=[str(v) for v in provider_counts.values],
                textposition="outside", textfont={"size": 11, "color": "#c3c2b7"},
            ))
            fig_prov.update_layout(
                height=220, margin=dict(l=10, r=30, t=10, b=10),
                xaxis=dict(title="Candidates", range=[0, provider_counts.max() * 1.3]),
                yaxis=dict(title=""), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_prov, width='stretch', config={"displayModeBar": False})
        with col_agree:
            agree = (live_df["target_family_queried"] == live_df["local_llm_predicted_family"]).sum()
            disagree = len(live_df) - agree
            st.markdown("**Local model vs. the search query it came from**")
            fig_agree = go.Figure(go.Bar(
                x=[agree, disagree], y=["Agrees with query", "Reclassified by model"], orientation="h",
                marker_color=["#1baf7a", "#eb6834"], text=[str(agree), str(disagree)],
                textposition="outside", textfont={"size": 11, "color": "#c3c2b7"},
            ))
            fig_agree.update_layout(
                height=220, margin=dict(l=10, r=30, t=10, b=10),
                xaxis=dict(title="Candidates", range=[0, len(live_df) * 1.15]),
                yaxis=dict(title=""), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_agree, width='stretch', config={"displayModeBar": False})
            st.caption(
                f"{disagree} of {len(live_df)} candidates were assigned a different family from the one "
                "used in their search query. This is a live workflow check, not a performance metric."
            )

        display_cols = ["source", "title", "target_family_queried", "local_llm_predicted_family", "published_date", "url"]
        st.dataframe(
            live_df[display_cols],
            width='stretch', hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("Source URL"),
                "source": st.column_config.TextColumn("Provider"),
                "target_family_queried": st.column_config.TextColumn("Query targeted"),
                "local_llm_predicted_family": st.column_config.TextColumn("Model-assigned family"),
            },
        )
        st.download_button(
            "Download this live-discovery snapshot as CSV",
            live_df[display_cols].to_csv(index=False).encode("utf-8"),
            file_name="pger_live_discovery_candidates.csv",
            mime="text/csv",
        )
        st.caption(f"Snapshot: {latest.name} (generated {latest.stat().st_mtime and pd.Timestamp(latest.stat().st_mtime, unit='s').date()}). Re-run the script above to refresh.")
    else:
        st.write("No live snapshot found yet. Run `python src/live_evidence_discovery.py` to generate one.")

st.info(
    "A review priority is a transparent ordering of published procurement notices. The user should "
    "verify the notice, source evidence, and operational context before taking action."
)
