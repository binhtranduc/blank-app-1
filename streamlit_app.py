from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import ccxt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

AUTO_REFRESH_SECONDS = 5
MAX_HISTORY = 5
PARIS_TZ = ZoneInfo("Europe/Paris")

st.set_page_config(page_title="Market Pulse | Perps", page_icon="◈", layout="wide")

SYMBOLS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",
    "FET/USDT:USDT",
    "PEPE/USDT",
    "QNT/USDT",
    "XRP/USDT",
    "XST/USDT",
]

PAPER_POSITIONS = {
    "BTC/USDT:USDT": {"qty": 0.05, "entry": 62000.0},
    "ETH/USDT:USDT": {"qty": 0.8, "entry": 3300.0},
    "SOL/USDT:USDT": {"qty": 6.0, "entry": 118.0},
    "FET/USDT:USDT": {"qty": 20.0, "entry": 0.75},
    "PEPE/USDT": {"qty": 5000.0, "entry": 0.0000085},
    "QNT/USDT": {"qty": 8.0, "entry": 80.0},
    "XRP/USDT": {"qty": 120.0, "entry": 0.6},
    "XST/USDT": {"qty": 2000.0, "entry": 0.00036},
}

STARTING_EQ = 10000.0

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    :root {
        --ink: #e8eee9;
        --muted: #84938d;
        --line: #24332e;
        --panel: #111a17;
        --base: #0a100e;
        --mint: #73e0ae;
        --lime: #c3ef75;
        --coral: #ff826e;
        --amber: #f0bd69;
    }
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    .stApp { background: var(--base); color: var(--ink); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; }
    [data-testid="stMainBlockContainer"] { max-width: 1440px; padding-top: 1.1rem; }
    .terminal-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 4px 0 19px; border-bottom: 1px solid var(--line); margin-bottom: 21px;
    }
    .brand { display: flex; gap: 11px; align-items: center; }
    .brand-mark {
        width: 34px; height: 34px; display: grid; place-items: center;
        border: 1px solid #3c584b; border-radius: 9px; color: var(--lime);
        background: #15221c; font-size: 20px;
    }
    .brand-name { color: var(--ink); font-size: 14px; font-weight: 700; line-height: 1.2; }
    .brand-sub { color: var(--muted); font: 10px 'DM Mono', monospace; margin-top: 4px; }
    .live-pill { color: var(--mint); font: 10px 'DM Mono', monospace; letter-spacing: .04em; }
    .live-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--mint); margin-right: 7px; box-shadow: 0 0 10px #73e0ae70; }
    .section-kicker { color: var(--muted); font: 10px 'DM Mono', monospace; text-transform: uppercase; margin: 2px 0 9px; }
    .section-title { color: var(--ink); font-size: 17px; font-weight: 600; margin: 0 0 12px; }
    .metric-card {
        min-height: 108px; background: var(--panel); border: 1px solid var(--line);
        border-radius: 8px; padding: 16px 17px; position: relative; overflow: hidden;
    }
    .metric-label { color: var(--muted); font-size: 11px; }
    .metric-value { color: var(--ink); font: 600 24px 'DM Mono', monospace; margin-top: 13px; }
    .metric-note { color: var(--muted); font-size: 10px; margin-top: 5px; }
    .positive { color: var(--mint) !important; }
    .negative { color: var(--coral) !important; }
    .panel {
        background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
        padding: 16px 18px; min-height: 100%;
    }
    .panel-heading { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 7px; }
    .panel-title { color: var(--ink); font-size: 14px; font-weight: 600; }
    .panel-note { color: var(--muted); font: 10px 'DM Mono', monospace; }
    .coin-tile {
        min-height: 111px; background: var(--panel); border: 1px solid var(--line);
        border-radius: 8px; padding: 13px 14px;
    }
    .coin-name { color: var(--muted); font: 10px 'DM Mono', monospace; }
    .coin-price { color: var(--ink); font: 500 16px 'DM Mono', monospace; margin: 13px 0 7px; }
    .coin-change { font: 11px 'DM Mono', monospace; }
    .tape { color: #83938b; font: 9px 'DM Mono', monospace; margin-top: 9px; white-space: nowrap; overflow: hidden; }
    .stDataFrame { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    [data-testid="stMetric"] { background: transparent; }
    [data-testid="stVegaLiteChart"] { margin-top: 2px; }
    @media (max-width: 700px) {
        [data-testid="stMainBlockContainer"] { padding: 1rem 1rem 2rem; }
        .metric-value { font-size: 19px; }
        .panel { padding: 13px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="terminal-header">
      <div class="brand">
        <div class="brand-mark">◈</div>
        <div><div class="brand-name">MARKET PULSE</div><div class="brand-sub">PERPETUALS TERMINAL · BINANCE</div></div>
      </div>
      <div class="live-pill"><span class="live-dot"></span>MARKET FEED</div>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_exchange():
    return ccxt.binanceusdm({"enableRateLimit": True})


@st.cache_resource
def get_spot_exchange():
    return ccxt.binance({"enableRateLimit": True})


def exchange_for_symbol(symbol):
    return get_exchange() if ":USDT" in symbol else get_spot_exchange()


def fetch_live_prices():
    prices = {}
    errors = {}
    for sym in SYMBOLS:
        try:
            ticker = exchange_for_symbol(sym).fetch_ticker(sym)
            if ticker["last"] is not None:
                prices[sym] = float(ticker["last"])
        except (ccxt.BaseError, TypeError, ValueError) as error:
            errors[sym] = str(error)
    return prices, errors


def update_history(history, now, prices):
    for sym, price in prices.items():
        history[sym].append({"time": now, "price": price})
        if len(history[sym]) > MAX_HISTORY:
            history[sym] = history[sym][-MAX_HISTORY:]


def compute_live_data(history):
    prices = {sym: hist[-1]["price"] for sym, hist in history.items() if hist}
    total_pnl = 0.0
    value = 0.0
    for sym, pos in PAPER_POSITIONS.items():
        current = prices.get(sym, pos["entry"])
        total_pnl += (current - pos["entry"]) * pos["qty"]
        value += current * pos["qty"]
    equity = STARTING_EQ + total_pnl
    return {
        "prices": prices,
        "equity": equity,
        "pnl": total_pnl,
        "value": value,
        "history": history,
    }


@st.cache_data(ttl=15, show_spinner=False)
def fetch_candles(symbol, timeframe):
    exchange = exchange_for_symbol(symbol)
    candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=120)
    frame = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    frame["time"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
    frame["EMA 20"] = frame["close"].ewm(span=20, adjust=False).mean()
    frame["EMA 50"] = frame["close"].ewm(span=50, adjust=False).mean()
    return frame


def compute_signal(symbol, timeframe="15m"):
    candles = fetch_candles(symbol, timeframe)
    if candles.empty:
        return {
            "bias": "Neutral",
            "confidence": 0,
            "entry": "N/A",
            "stop": "N/A",
            "target": "N/A",
            "reason": "No candle data available yet.",
        }

    close = float(candles["close"].iloc[-1])
    ema20 = float(candles["EMA 20"].iloc[-1])
    ema50 = float(candles["EMA 50"].iloc[-1])
    recent = candles.tail(14)
    last_change = float(recent["close"].pct_change().dropna().iloc[-1]) if not recent["close"].pct_change().dropna().empty else 0.0
    gains = recent["close"].diff().clip(lower=0).mean()
    losses = (-recent["close"].diff().clip(upper=0)).mean()
    rsi = 50.0
    if losses != 0:
        rsi = 100 - (100 / (1 + (gains / losses)))

    ema_trend = 0.0
    ema_slope = 0.0
    if ema20 > ema50:
        ema_trend += 35
    else:
        ema_trend -= 35
    if close > ema20:
        ema_trend += 25
    else:
        ema_trend -= 25
    ema_slope = ((ema20 - ema50) / max(ema50, 1e-9)) * 100

    rsi_signal = 0.0
    if rsi >= 60:
        rsi_signal += 15
    elif rsi <= 40:
        rsi_signal -= 15
    elif 45 <= rsi <= 55:
        rsi_signal += 5

    momentum_signal = 0.0
    if last_change > 0.01:
        momentum_signal += 20
    elif last_change < -0.01:
        momentum_signal -= 20
    if close > recent["close"].quantile(0.7):
        momentum_signal += 10
    elif close < recent["close"].quantile(0.3):
        momentum_signal -= 10

    trend_strength = ema_trend + rsi_signal + momentum_signal + (ema_slope * 2)

    last_low = candles["low"].tail(20).min()
    last_high = candles["high"].tail(20).max()
    mid = (last_low + last_high) / 2
    entry_band = (last_low + last_high) / 2

    if trend_strength >= 25:
        bias = "Bullish"
        entry = f"Buy near ${entry_band:,.4f}"
        stop = f"Below ${last_low:,.4f}"
        target = f"Above ${last_high:,.4f}"
        reason = "Price is holding above the EMA stack, RSI is constructive, and recent momentum is pushing higher."
    elif trend_strength <= -25:
        bias = "Bearish"
        entry = f"Sell near ${entry_band:,.4f}"
        stop = f"Above ${last_high:,.4f}"
        target = f"Below ${last_low:,.4f}"
        reason = "Trend is fading beneath the EMA stack with weak momentum and a defensive RSI profile."
    else:
        bias = "Neutral"
        entry = f"Watch ${entry_band:,.4f}"
        stop = f"Below ${last_low:,.4f}"
        target = f"Above ${last_high:,.4f}"
        reason = "Consolidation is dominant; wait for a stronger break or rejection at the current range."

    confidence = max(55, min(96, int(abs(trend_strength) * 1.2 + 58)))

    return {
        "bias": bias,
        "confidence": confidence,
        "entry": entry,
        "stop": stop,
        "target": target,
        "reason": reason,
        "rsi": float(rsi),
        "ema20": float(ema20),
        "ema50": float(ema50),
    }


def format_price(price):
    return f"${price:,.2f}" if price >= 1 else f"${price:.4f}"


def paris_time_string(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    paris_dt = dt.astimezone(PARIS_TZ)
    return paris_dt.strftime("%Y-%m-%d %H:%M:%S %Z")


@st.fragment(run_every=AUTO_REFRESH_SECONDS)
def live_dashboard():
    if "market_history" not in st.session_state:
        st.session_state.market_history = defaultdict(list)

    now = datetime.now(timezone.utc)
    paris_now = now.astimezone(PARIS_TZ)
    live_prices, errors = fetch_live_prices()
    update_history(st.session_state.market_history, now, live_prices)
    live_data = compute_live_data(st.session_state.market_history)

    pnl_class = "positive" if live_data["pnl"] >= 0 else "negative"
    metrics = [
        ("MARKED P&L · PAPER", f"${live_data['pnl']:,.2f}", "Simulated positions", pnl_class),
        ("PAPER EQUITY", f"${live_data['equity']:,.2f}", "Starting balance $10,000", ""),
        ("POSITION VALUE", f"${live_data['value']:,.2f}", "Based on tracked marks", ""),
        ("LIVE MARKETS", f"{len(live_prices):02d} / {len(SYMBOLS):02d}", "USDT perpetual contracts", ""),
    ]
    metric_cols = st.columns(4, gap="small")
    for column, (label, value, note, value_class) in zip(metric_cols, metrics):
        with column:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value {value_class}">{value}</div>'
                f'<div class="metric-note">{note}</div></div>',
                unsafe_allow_html=True,
            )

    st.write("")
    chart_col, watch_col = st.columns([1.65, 1], gap="small")
    with chart_col:
        st.markdown(
            '<div class="panel-heading"><div><div class="section-kicker">TRADE STUDY</div>'
            '<div class="panel-title">Candles · trend · volume</div></div>'
            '<div class="panel-note">BINANCE MARKETS</div></div>',
            unsafe_allow_html=True,
        )
        selector_cols = st.columns([1.4, 1])
        with selector_cols[0]:
            selected_symbol = st.selectbox(
                "Market",
                SYMBOLS,
                format_func=lambda symbol: f"{symbol.split('/')[0]} / USDT",
                key="analysis_symbol",
            )
        with selector_cols[1]:
            timeframe = st.segmented_control(
                "Candle interval",
                ["5m", "15m", "1h", "4h"],
                default="15m",
                key="analysis_timeframe",
            )

        try:
            candles = fetch_candles(selected_symbol, timeframe)
            if candles.empty:
                st.info("No candle data returned for this market.")
            else:
                figure = make_subplots(
                    rows=2,
                    cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.04,
                    row_heights=[0.76, 0.24],
                )
                figure.add_trace(
                    go.Candlestick(
                        x=candles["time"],
                        open=candles["open"],
                        high=candles["high"],
                        low=candles["low"],
                        close=candles["close"],
                        name="Price",
                        increasing_line_color="#73e0ae",
                        decreasing_line_color="#ff826e",
                    ),
                    row=1,
                    col=1,
                )
                figure.add_trace(
                    go.Scatter(
                        x=candles["time"],
                        y=candles["EMA 20"],
                        name="EMA 20",
                        line={"color": "#f0bd69", "width": 1.4},
                    ),
                    row=1,
                    col=1,
                )
                figure.add_trace(
                    go.Scatter(
                        x=candles["time"],
                        y=candles["EMA 50"],
                        name="EMA 50",
                        line={"color": "#82b8ff", "width": 1.4},
                    ),
                    row=1,
                    col=1,
                )
                volume_colors = [
                    "#73e0ae" if close >= open_price else "#ff826e"
                    for open_price, close in zip(candles["open"], candles["close"])
                ]
                figure.add_trace(
                    go.Bar(
                        x=candles["time"],
                        y=candles["volume"],
                        name="Volume",
                        marker_color=volume_colors,
                        showlegend=False,
                    ),
                    row=2,
                    col=1,
                )
                figure.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#111a17",
                    plot_bgcolor="#111a17",
                    font={"family": "Space Grotesk, sans-serif", "color": "#cbd6cf", "size": 11},
                    margin={"l": 8, "r": 8, "t": 18, "b": 8},
                    height=440,
                    xaxis_rangeslider_visible=False,
                    legend={"orientation": "h", "y": 1.06, "x": 0},
                )
                figure.update_xaxes(gridcolor="#24332e", showgrid=True)
                figure.update_yaxes(gridcolor="#24332e", showgrid=True)
                figure.update_yaxes(title_text="Volume", row=2, col=1)
                source = "Binance USD-M perpetual" if ":USDT" in selected_symbol else "Binance spot"
                st.plotly_chart(
                    figure,
                    width="stretch",
                    config={"displayModeBar": False, "scrollZoom": True},
                    key="entry_candlestick_chart",
                )
                st.caption(f"{source} · 120 candles · EMA 20 / 50 · volume")

                signal = compute_signal(selected_symbol, timeframe)
                bias_color = "#73e0ae" if signal["bias"] == "Bullish" else "#ff826e" if signal["bias"] == "Bearish" else "#f0bd69"
                st.markdown(
                    f"""
                    <div class="panel" style="margin-top: 14px; border-color:{bias_color};">
                      <div class="panel-heading">
                        <div><div class="section-kicker">ENTRY MODEL</div><div class="panel-title">{signal['bias']} bias</div></div>
                        <div class="panel-note">{signal['confidence']}% confidence</div>
                      </div>
                      <div class="metric-value" style="font-size: 18px; color:{bias_color}; margin-top: 0;">{signal['entry']}</div>
                      <div class="metric-note" style="margin-top:8px;">Stop: {signal['stop']} · Target: {signal['target']}</div>
                      <div class="metric-note" style="margin-top:8px;">RSI: {signal['rsi']:.1f} · EMA20: {signal['ema20']:.4f} · EMA50: {signal['ema50']:.4f}</div>
                      <div class="metric-note" style="margin-top:8px;">{signal['reason']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        except (ccxt.BaseError, ValueError, KeyError) as error:
            st.warning(f"Could not load candle data for {selected_symbol}: {error}")

    with watch_col:
        st.markdown(
            '<div class="panel-heading"><div><div class="section-kicker">MARKET WATCH</div>'
            '<div class="panel-title">Tracked contracts</div></div>'
            f'<div class="panel-note">{paris_now.strftime("%H:%M:%S %Z")}</div></div>',
            unsafe_allow_html=True,
        )
        rows = []
        for sym in SYMBOLS:
            history = st.session_state.market_history.get(sym, [])
            if history:
                last = history[-1]["price"]
                previous = history[-2]["price"] if len(history) > 1 else last
                change = (last / previous - 1) * 100 if previous else 0
                rows.append(
                    {
                        "Contract": sym.split("/")[0],
                        "Last price": format_price(last),
                        "5s move": f"{change:+.3f}%",
                    }
                )
            else:
                rows.append({"Contract": sym.split("/")[0], "Last price": "—", "5s move": "—"})
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
            height=285,
        )

    st.markdown(
        '<div class="section-kicker" style="margin-top:18px">ASSET SNAPSHOT</div>'
        '<div class="section-title">Live prices · rolling five-point tape</div>',
        unsafe_allow_html=True,
    )
    coin_cols = st.columns(len(SYMBOLS), gap="small")
    for column, sym in zip(coin_cols, SYMBOLS):
        history = st.session_state.market_history.get(sym, [])
        with column:
            if history:
                last = history[-1]["price"]
                previous = history[-2]["price"] if len(history) > 1 else last
                change = (last / previous - 1) * 100 if previous else 0
                change_class = "positive" if change >= 0 else "negative"
                tape = " · ".join(format_price(point["price"]) for point in history[-MAX_HISTORY:])
                st.markdown(
                    f'<div class="coin-tile"><div class="coin-name">{sym.split("/")[0]} / USDT</div>'
                    f'<div class="coin-price">{format_price(last)}</div>'
                    f'<div class="coin-change {change_class}">{change:+.3f}% <span style="color:#84938d">· 5s</span></div>'
                    f'<div class="tape">{tape}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="coin-tile"><div class="coin-name">{sym.split("/")[0]} / USDT</div>'
                    '<div class="coin-price">Connecting…</div><div class="coin-change">Waiting for price</div></div>',
                    unsafe_allow_html=True,
                )

    if errors:
        st.warning(f"Market feed temporarily unavailable for {len(errors)} contract(s); showing the last received prices.")
    st.caption(
        f"Updated {paris_time_string(now)} · refreshes every {AUTO_REFRESH_SECONDS}s · "
        "P&L and equity are illustrative paper positions, not live account balances."
    )


live_dashboard()
