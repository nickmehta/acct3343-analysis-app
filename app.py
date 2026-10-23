
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Stock Analysis App",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Stock Analysis & Screening App")
st.write(
    "Screen public companies using financial measures to identify "
    "potential BUY and SELL candidates. These screens are educational "
    "signals, not personalized financial advice."
)

# Load company data
@st.cache_data
def load_data():
    df = pd.read_csv("universe.csv")

    required = ["Ticker", "STA", "GPA", "Book_to_Market"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        st.error(f"Missing required columns: {missing}")
        st.stop()

    for col in ["STA", "GPA", "Book_to_Market", "Market_Cap"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("Could not find universe.csv. Put it in the same repository folder as app.py.")
    st.stop()

# Sidebar filters
st.sidebar.header("Screening Filters")

min_market_cap = st.sidebar.number_input(
    "Minimum market capitalization ($)",
    min_value=0,
    value=300_000_000,
    step=100_000_000
)

if "Market_Cap" in df.columns:
    filtered = df[
        df["Market_Cap"].isna() |
        (df["Market_Cap"] >= min_market_cap)
    ].copy()
else:
    filtered = df.copy()
    st.sidebar.warning("Market capitalization data is unavailable.")

st.sidebar.caption(
    "Adjust the thresholds below to update the candidate lists."
)

gpa_cutoff = st.sidebar.slider(
    "Minimum GPA for BUY screen",
    min_value=0.0,
    max_value=1.0,
    value=0.20,
    step=0.01
)

bm_cutoff = st.sidebar.slider(
    "Minimum Book-to-Market for BUY screen",
    min_value=0.0,
    max_value=2.0,
    value=0.30,
    step=0.05
)

sta_cutoff = st.sidebar.slider(
    "Minimum STA for SELL screen",
    min_value=-0.5,
    max_value=0.5,
    value=0.05,
    step=0.01
)

# Candidate screens
buy = filtered[
    (filtered["GPA"] >= gpa_cutoff) &
    (filtered["Book_to_Market"] >= bm_cutoff)
].copy()

sell = filtered[
    filtered["STA"] >= sta_cutoff
].copy()

# Summary metrics
c1, c2, c3 = st.columns(3)
c1.metric("Companies in dataset", len(df))
c2.metric("Potential BUY candidates", len(buy))
c3.metric("Potential SELL candidates", len(sell))

st.divider()

# BUY section
st.header("🟢 Potential BUY Candidates")
st.write(
    "**Logic:** High gross profitability and high book-to-market. "
    "GPA measures gross profit relative to assets. Book-to-market "
    "compares book equity with market capitalization."
)

if buy.empty:
    st.info("No BUY candidates meet the current filters. Adjust the sidebar.")
else:
    buy_display = [
        col for col in [
            "Ticker", "GPA", "Book_to_Market",
            "Market_Cap", "Total_Assets", "Gross_Profit"
        ] if col in buy.columns
    ]

    st.dataframe(
        buy[buy_display].sort_values(
            ["GPA", "Book_to_Market"],
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

# SELL section
st.header("🔴 Potential SELL Candidates")
st.write(
    "**Logic:** High scaled total accruals (STA). STA is calculated as "
    "(net income − operating cash flow) / total assets. High positive "
    "accruals may indicate that reported earnings are less supported "
    "by operating cash flow; this alone does not prove poor quality."
)

if sell.empty:
    st.info("No SELL candidates meet the current threshold. Adjust the sidebar.")
else:
    sell_display = [
        col for col in [
            "Ticker", "STA", "Net_Income",
            "Operating_Cash_Flow", "Total_Assets"
        ] if col in sell.columns
    ]

    st.dataframe(
        sell[sell_display].sort_values("STA", ascending=False),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# Company detail
st.header("🔎 Explore an Individual Company")

available_tickers = sorted(
    filtered["Ticker"].dropna().astype(str).unique()
)

if available_tickers:
    selected = st.selectbox("Choose a ticker", available_tickers)
    company = filtered[
        filtered["Ticker"].astype(str) == selected
    ].iloc[0]

    st.subheader(f"Company: {selected}")

    detail_cols = [
        col for col in [
            "GPA", "Book_to_Market", "STA",
            "Market_Cap", "Total_Assets",
            "Gross_Profit", "Net_Income", "Operating_Cash_Flow"
        ] if col in company.index
    ]

    st.dataframe(
        pd.DataFrame({
            "Measure": detail_cols,
            "Value": [company[col] for col in detail_cols]
        }),
        use_container_width=True,
        hide_index=True
    )

    reasons = []

    if pd.notna(company["GPA"]) and company["GPA"] >= gpa_cutoff:
        reasons.append("meets the GPA threshold")

    if (
        pd.notna(company["Book_to_Market"])
        and company["Book_to_Market"] >= bm_cutoff
    ):
        reasons.append("meets the book-to-market threshold")

    if pd.notna(company["STA"]) and company["STA"] >= sta_cutoff:
        reasons.append("meets the STA threshold")

    if reasons:
        st.write("Screening observations: " + "; ".join(reasons) + ".")
    else:
        st.write(
            "This company does not meet the currently selected thresholds "
            "for the measures with available data."
        )

# Visualization
st.header("📈 Compare the Measures")

plot_data = filtered.dropna(subset=["GPA", "Book_to_Market"]).copy()

if not plot_data.empty:
    fig = px.scatter(
        plot_data,
        x="Book_to_Market",
        y="GPA",
        hover_name="Ticker",
        title="Gross Profitability vs. Book-to-Market",
        labels={
            "Book_to_Market": "Book-to-Market",
            "GPA": "Gross Profitability / Total Assets"
        }
    )
    fig.add_vline(x=bm_cutoff, line_dash="dash")
    fig.add_hline(y=gpa_cutoff, line_dash="dash")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough complete GPA and book-to-market data to draw the chart.")

st.caption(
    "Data source: Yahoo Finance via yfinance. Financial statement values "
    "may be missing or differ across companies. Verify formulas and "
    "thresholds against your course materials before submitting."
)
