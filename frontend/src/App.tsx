import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import "./App.css";

type Market = "India" | "Forex" | "Crypto";
type Page = "Overview" | "Markets" | "Watchlist" | "Analytics" | "AI Research" | "RAG Pipeline" | "API Explorer";
type CryptoQuote = { symbol: string; name: string; price_usd: number; price_inr: number; change_24h_percent: number | null; volume_24h_usd: number | null; market_cap_usd: number | null };
type MarketQuote = { symbol: string; name: string; price: number; as_of: string; change_percent: number; source: string; data_type: string };
type Point = { timestamp: number; value: number; date?: string };
type ResearchResult = { source?: string; text?: string; chunk_number?: number; distance?: number };

const API = "http://127.0.0.1:8000";
const PERIODS = ["1D", "1W", "1M", "1Y"] as const;
const NAV: { label: Page; icon: string; group: string }[] = [
  { label: "Overview", icon: "▦", group: "WORKSPACE" },
  { label: "Markets", icon: "⌁", group: "WORKSPACE" },
  { label: "Watchlist", icon: "☆", group: "WORKSPACE" },
  { label: "Analytics", icon: "▥", group: "INTELLIGENCE" },
  { label: "AI Research", icon: "✳", group: "INTELLIGENCE" },
  { label: "RAG Pipeline", icon: "◈", group: "SYSTEM" },
  { label: "API Explorer", icon: "⌘", group: "SYSTEM" },
];
const ROUTES = [
  ["GET", "/health", "Backend health check"],
  ["GET", "/api/v1/market/crypto/prices", "Crypto market quotes"],
  ["GET", "/api/v1/market/crypto/history", "Historical crypto prices"],
  ["GET", "/api/v1/market/forex/prices", "Forex reference rates"],
  ["GET", "/api/v1/market/forex/history", "Historical FX rates"],
  ["GET", "/api/v1/market/india/prices", "Indian market quotes"],
  ["GET", "/api/v1/market/india/history", "Historical Indian market data"],
  ["POST", "/api/v1/bitcoin/ask", "AI financial Q&A"],
  ["POST", "/api/v1/research/search", "Semantic research retrieval"],
];

function fmt(value: number, digits = 2) {
  return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function fmtINR(value: number) {
  return "₹" + value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}
function fmtUSD(value: number) { return "$" + value.toLocaleString("en-US", { maximumFractionDigits: 2 }); }
function signed(value: number) { return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`; }
function dateLabel(ts: number) { return new Date(ts).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }); }
function isPositive(value: number) { return value >= 0; }

function App() {
  const [page, setPage] = useState<Page>("Overview");
  const [market, setMarket] = useState<Market>("India");
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>("1M");
  const [crypto, setCrypto] = useState("BTC");
  const [forex, setForex] = useState("USD/INR");
  const [india, setIndia] = useState("NIFTY 50");
  const [cryptoQuotes, setCryptoQuotes] = useState<CryptoQuote[]>([]);
  const [forexQuotes, setForexQuotes] = useState<MarketQuote[]>([]);
  const [indiaQuotes, setIndiaQuotes] = useState<MarketQuote[]>([]);
  const [feedErrors, setFeedErrors] = useState<Record<string, string>>({});
  const [points, setPoints] = useState<Point[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [search, setSearch] = useState("");
  const [watchlist, setWatchlist] = useState<string[]>(["NIFTY 50", "USD/INR", "BTC", "ETH"]);
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [researchQuery, setResearchQuery] = useState("");
  const [researchResults, setResearchResults] = useState<ResearchResult[]>([]);
  const [researchLoading, setResearchLoading] = useState(false);
  const [researchError, setResearchError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadMarkets = useCallback(async () => {
    const jobs = [
      ["Crypto", `${API}/api/v1/market/crypto/prices`],
      ["Forex", `${API}/api/v1/market/forex/prices`],
      ["India", `${API}/api/v1/market/india/prices`],
    ] as const;
    await Promise.all(jobs.map(async ([key, url]) => {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`API returned ${response.status}`);
        const data = await response.json();
        if (key === "Crypto") setCryptoQuotes(Array.isArray(data) ? data : (data.prices ?? data.data ?? []));
        if (key === "Forex") setForexQuotes(Array.isArray(data) ? data : (data.prices ?? data.data ?? []));
        if (key === "India") setIndiaQuotes(Array.isArray(data) ? data : (data.prices ?? data.data ?? []));
        setFeedErrors(old => ({ ...old, [key]: "" }));
      } catch (err) {
        setFeedErrors(old => ({ ...old, [key]: err instanceof Error ? err.message : "Unable to load feed" }));
      }
    }));
    try {
      const response = await fetch(`${API}/health`);
      setApiStatus(response.ok ? "online" : "offline");
    } catch { setApiStatus("offline"); }
    setLastUpdated(new Date());
  }, []);

  useEffect(() => {
    void loadMarkets();
    const timer = window.setInterval(() => void loadMarkets(), 60_000);
    return () => window.clearInterval(timer);
  }, [loadMarkets]);

  useEffect(() => {
    if (market === "India" && indiaQuotes.length && !indiaQuotes.some(q => q.symbol === india)) setIndia(indiaQuotes[0].symbol);
    if (market === "Forex" && forexQuotes.length && !forexQuotes.some(q => q.symbol === forex)) setForex(forexQuotes[0].symbol);
  }, [indiaQuotes, forexQuotes, market, india, forex]);

  const selectedSymbol = market === "Crypto" ? crypto : market === "Forex" ? forex : india;
  const selectedCryptoQuote = cryptoQuotes.find(q => q.symbol === crypto);
  const selectedForexQuote = forexQuotes.find(q => q.symbol === forex);
  const selectedIndiaQuote = indiaQuotes.find(q => q.symbol === india);
  const selectedQuote = market === "Crypto" ? selectedCryptoQuote : market === "Forex" ? selectedForexQuote : selectedIndiaQuote;
  const allRows = useMemo(() => {
    const c = cryptoQuotes.map(q => ({ market: "Crypto" as Market, symbol: q.symbol, name: q.name, price: q.price_usd, currency: "USD", change: q.change_24h_percent, source: "Crypto" }));
    const f = forexQuotes.map(q => ({ market: "Forex" as Market, symbol: q.symbol, name: q.name, price: q.price, currency: "FX", change: q.change_percent, source: q.source }));
    const i = indiaQuotes.map(q => ({ market: "India" as Market, symbol: q.symbol, name: q.name, price: q.price, currency: "INR", change: q.change_percent, source: q.source }));
    return [...i, ...f, ...c];
  }, [cryptoQuotes, forexQuotes, indiaQuotes]);

  useEffect(() => {
    let alive = true;
    const loadHistory = async () => {
      setHistoryLoading(true); setHistoryError("");
      try {
        let url = "";
        if (market === "Crypto") {
          const days: Record<string, number> = { "1D": 1, "1W": 7, "1M": 30, "1Y": 365 };
          url = `${API}/api/v1/market/crypto/history?symbol=${encodeURIComponent(crypto)}&days=${days[period]}`;
        } else if (market === "Forex") {
          url = `${API}/api/v1/market/forex/history?symbol=${encodeURIComponent(forex)}&period=${encodeURIComponent(period)}`;
        } else {
          url = `${API}/api/v1/market/india/history?symbol=${encodeURIComponent(india)}&period=${encodeURIComponent(period)}`;
        }
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Historical API returned ${response.status}`);
        const payload = await response.json();
        const raw = Array.isArray(payload.prices) ? payload.prices : Array.isArray(payload.data) ? payload.data : [];
        const normalized: Point[] = raw.map((p: Record<string, unknown>) => {
          const rawTs = p.timestamp ?? p.time ?? p.date;
          const timestamp = typeof rawTs === "number" ? rawTs : Date.parse(String(rawTs ?? ""));
          const rawValue = p.value ?? p.price ?? p.close ?? p.price_usd ?? p.close_price;
          return { timestamp, value: Number(rawValue), date: typeof p.date === "string" ? p.date : undefined };
        }).filter((p: Point) => Number.isFinite(p.timestamp) && Number.isFinite(p.value)).sort((a: Point, b: Point) => a.timestamp - b.timestamp);
        if (normalized.length < 2) throw new Error("Not enough historical points for this symbol and period.");
        if (alive) setPoints(normalized);
      } catch (err) {
        if (alive) { setPoints([]); setHistoryError(err instanceof Error ? err.message : "Unable to load chart history"); }
      } finally { if (alive) setHistoryLoading(false); }
    };
    void loadHistory();
    return () => { alive = false; };
  }, [market, crypto, forex, india, period]);

  const chart = useMemo(() => {
    if (points.length < 2) return { line: "", area: "", min: 0, max: 0, latest: 0, change: 0 };
    const values = points.map(p => p.value); const min = Math.min(...values); const max = Math.max(...values); const range = max - min || 1;
    const line = points.map((p, i) => `${i === 0 ? "M" : "L"} ${(i / (points.length - 1) * 900).toFixed(2)} ${(230 - ((p.value - min) / range) * 190).toFixed(2)}`).join(" ");
    return { line, area: `${line} L 900 250 L 0 250 Z`, min, max, latest: values[values.length - 1], change: ((values[values.length - 1] - values[0]) / (Math.abs(values[0]) || 1)) * 100 };
  }, [points]);

  function selectMarket(next: Market) { setMarket(next); setPage("Markets"); }
  function selectRow(row: { market: Market; symbol: string }) {
    setMarket(row.market); setPage("Markets");
    if (row.market === "Crypto") setCrypto(row.symbol);
    if (row.market === "Forex") setForex(row.symbol);
    if (row.market === "India") setIndia(row.symbol);
  }
  function toggleWatch(symbol: string) { setWatchlist(old => old.includes(symbol) ? old.filter(s => s !== symbol) : [...old, symbol]); }

  async function askAI(e: FormEvent) {
    e.preventDefault(); if (question.trim().length < 3) return;
    setAskLoading(true); setAnswer("");
    try {
      const response = await fetch(`${API}/api/v1/bitcoin/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: question.trim() }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? data.error ?? `Request failed: ${response.status}`);
      setAnswer(data.answer ?? data.response ?? data.message ?? JSON.stringify(data, null, 2));
    } catch (err) { setAnswer(`AI response unavailable. ${err instanceof Error ? err.message : "Check the backend connection."}`); }
    finally { setAskLoading(false); }
  }
  async function searchResearch(e: FormEvent) {
    e.preventDefault(); if (!researchQuery.trim()) return;
    setResearchLoading(true); setResearchError(""); setResearchResults([]);
    try {
      const response = await fetch(`${API}/api/v1/research/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: researchQuery.trim(), top_k: 5 }) });
      const data = await response.json(); if (!response.ok) throw new Error(data.detail ?? data.error ?? `Request failed: ${response.status}`);
      setResearchResults(Array.isArray(data.results) ? data.results : []);
    } catch (err) { setResearchError(err instanceof Error ? err.message : "Research search failed."); }
    finally { setResearchLoading(false); }
  }

  const marketRows = market === "India"
    ? indiaQuotes.map(q => ({ market: "India" as Market, symbol: q.symbol, name: q.name, price: q.price, currency: "INR", change: q.change_percent, source: q.source }))
    : market === "Forex"
      ? forexQuotes.map(q => ({ market: "Forex" as Market, symbol: q.symbol, name: q.name, price: q.price, currency: "FX", change: q.change_percent, source: q.source }))
      : cryptoQuotes.map(q => ({ market: "Crypto" as Market, symbol: q.symbol, name: q.name, price: q.price_usd, currency: "USD", change: q.change_24h_percent, source: "Crypto" }));
  const filteredRows = marketRows.filter(r => `${r.symbol} ${r.name}`.toLowerCase().includes(search.toLowerCase()));
  const marketLabel = market === "India" ? "Indian Equities" : market === "Forex" ? "Foreign Exchange" : "Digital Assets";
  const selectedDisplayPrice = market === "India" && selectedIndiaQuote ? fmtINR(selectedIndiaQuote.price) : market === "Forex" && selectedForexQuote ? fmt(selectedForexQuote.price, 4) : selectedCryptoQuote ? fmtUSD(selectedCryptoQuote.price_usd) : "—";
  const statusText = apiStatus === "online" ? "SYSTEM OPERATIONAL" : apiStatus === "offline" ? "API DISCONNECTED" : "CHECKING CONNECTION";

  return <div className="terminal-app">
    <aside className="sidebar">
      <button className="brand" onClick={() => setPage("Overview")} aria-label="AlphaSightAI home"><span className="brand-glyph">α</span><span className="brand-word">ALPHA<span>SIGHT</span><small>AI MARKET INTELLIGENCE</small></span></button>
      <div className="workspace-switch"><span className="workspace-avatar">H</span><span><b>Research Desk</b><small>Personal workspace</small></span><span className="chevron">⌄</span></div>
      {(["WORKSPACE", "INTELLIGENCE", "SYSTEM"] as const).map(group => <div className="nav-group" key={group}><div className="nav-caption">{group}</div>{NAV.filter(n => n.group === group).map(item => <button key={item.label} className={`nav-item ${page === item.label ? "active" : ""}`} onClick={() => setPage(item.label)}><span className="nav-glyph">{item.icon}</span><span>{item.label}</span>{item.label === "AI Research" && <span className="nav-new">AI</span>}</button>)}</div>)}
      <div className="sidebar-spacer" />
      <div className="plan-card"><div className="plan-icon">✳</div><b>Intelligence workspace</b><p>Market data, research and signals in one place.</p><span className="plan-status"><i /> LOCAL BUILD</span></div>
      <div className="sidebar-footer"><span className={`status-led ${apiStatus}`} /><span>{statusText}</span><button title="Refresh data" onClick={() => void loadMarkets()}>↻</button></div>
      <a className="github-link" href="https://github.com/harshadkorde144/AlphaSightAI" target="_blank" rel="noreferrer">↗ &nbsp; Repository</a>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="crumb"><span>AlphaSightAI</span><span className="slash">/</span><b>{page}</b></div><div className="top-actions"><div className="global-search"><span>⌕</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search instruments..." aria-label="Search instruments" /><kbd>⌘ K</kbd></div><span className="top-divider" /><div className="session-state"><i className={`status-led ${apiStatus}`} />{apiStatus === "online" ? "Connected" : apiStatus === "offline" ? "Offline" : "Connecting"}</div><button className="avatar-button" title="Workspace profile">HK</button></div></header>
      <div className="page-wrap">
        {page === "Overview" && <>
          <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> MARKET INTELLIGENCE PLATFORM</div><h1>Market overview<span className="heading-period">.</span></h1><p>A clear view of the markets that move your world.</p></div><div className="heading-right"><span className="date-stamp">{new Date().toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}</span><button className="button-secondary" onClick={() => void loadMarkets()}>↻ Refresh data</button></div></section>
          <section className="market-strip"><button className={`market-tile ${market === "India" ? "chosen" : ""}`} onClick={() => selectMarket("India")}><span className="tile-kicker"><span className="flag-dot india-dot" /> INDIA · EQUITIES</span><b>{indiaQuotes[0] ? fmtINR(indiaQuotes[0].price) : "—"}</b><span className={`tile-change ${indiaQuotes[0] && isPositive(indiaQuotes[0].change_percent) ? "up" : "down"}`}>{indiaQuotes[0] ? signed(indiaQuotes[0].change_percent) : (feedErrors.India || "Awaiting feed")}</span><small>{indiaQuotes[0]?.name ?? "NIFTY 50"}</small></button><button className={`market-tile ${market === "Forex" ? "chosen" : ""}`} onClick={() => selectMarket("Forex")}><span className="tile-kicker"><span className="flag-dot forex-dot" /> FX · REFERENCE RATES</span><b>{forexQuotes.find(q => q.symbol === "USD/INR") ? fmt(forexQuotes.find(q => q.symbol === "USD/INR")!.price, 4) : "—"}</b><span className={`tile-change ${forexQuotes.find(q => q.symbol === "USD/INR") && isPositive(forexQuotes.find(q => q.symbol === "USD/INR")!.change_percent) ? "up" : "down"}`}>{forexQuotes.find(q => q.symbol === "USD/INR") ? signed(forexQuotes.find(q => q.symbol === "USD/INR")!.change_percent) : (feedErrors.Forex || "Awaiting feed")}</span><small>USD / INR</small></button><button className={`market-tile ${market === "Crypto" ? "chosen" : ""}`} onClick={() => selectMarket("Crypto")}><span className="tile-kicker"><span className="flag-dot crypto-dot" /> DIGITAL ASSETS</span><b>{cryptoQuotes.find(q => q.symbol === "BTC") ? fmtUSD(cryptoQuotes.find(q => q.symbol === "BTC")!.price_usd) : "—"}</b><span className={`tile-change ${cryptoQuotes.find(q => q.symbol === "BTC")?.change_24h_percent != null && isPositive(cryptoQuotes.find(q => q.symbol === "BTC")!.change_24h_percent!) ? "up" : "down"}`}>{cryptoQuotes.find(q => q.symbol === "BTC")?.change_24h_percent != null ? signed(cryptoQuotes.find(q => q.symbol === "BTC")!.change_24h_percent!) : (feedErrors.Crypto || "Awaiting feed")}</span><small>Bitcoin · BTC</small></button><div className="market-tile market-tile-status"><span className="tile-kicker">DATA STATUS</span><b className="status-large"><i className={`status-led ${apiStatus}`} />{apiStatus === "online" ? "Operational" : apiStatus === "offline" ? "Disconnected" : "Checking"}</b><small>{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}` : "Waiting for first sync"}</small><span className="status-foot">Auto refresh · 60 sec</span></div></section>
          <section className="dashboard-grid"><div className="panel chart-panel"><div className="panel-top"><div><div className="section-kicker">MARKET PERFORMANCE</div><h2>Price action <span className="muted-inline">/ {marketLabel}</span></h2></div><div className="segmented">{(["India", "Forex", "Crypto"] as Market[]).map(m => <button key={m} className={market === m ? "selected" : ""} onClick={() => setMarket(m)}>{m}</button>)}</div></div>
            <div className="chart-instrument"><div className="instrument-icon">{market === "India" ? "N" : market === "Forex" ? "FX" : "₿"}</div><div><b>{selectedSymbol}</b><small>{selectedQuote?.name ?? (market === "India" ? "Indian market index" : market === "Forex" ? "Currency pair" : "Digital asset")}</small></div><div className="instrument-price"><b>{selectedDisplayPrice}</b><span className={chart.change >= 0 ? "up" : "down"}>{points.length > 1 ? `${signed(chart.change)} · selected range` : "Historical change unavailable"}</span></div></div>
            <div className="chart-legend"><span><i className="legend-line" /> Historical price</span><span className="chart-source">{market === "Forex" ? "DAILY REFERENCE RATE" : market === "India" ? "INDIA MARKET FEED" : "CRYPTO MARKET FEED"}</span></div>
            <div className="chart-plot">{historyLoading ? <div className="chart-message"><span className="loader" />Loading historical prices…</div> : historyError ? <div className="chart-message chart-error">{historyError}</div> : points.length > 1 ? <><div className="chart-y-labels"><span>{fmt(chart.max, market === "Forex" ? 4 : 2)}</span><span>{fmt((chart.max + chart.min) / 2, market === "Forex" ? 4 : 2)}</span><span>{fmt(chart.min, market === "Forex" ? 4 : 2)}</span></div><svg className="price-svg" viewBox="0 0 900 270" preserveAspectRatio="none" role="img" aria-label={`${selectedSymbol} historical price chart`}><defs><linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b5f36c" stopOpacity=".22" /><stop offset="100%" stopColor="#b5f36c" stopOpacity="0" /></linearGradient></defs>{[40, 100, 160, 220].map(y => <line key={y} x1="0" y1={y} x2="900" y2={y} className="grid-line" />)}<path d={chart.area} fill="url(#chartGradient)" /><path d={chart.line} className="price-line" /><circle cx="900" cy={230 - ((chart.latest - chart.min) / (chart.max - chart.min || 1)) * 190} r="4" className="chart-endpoint" /></svg><div className="chart-x-labels"><span>{dateLabel(points[0].timestamp)}</span><span>{dateLabel(points[Math.floor(points.length / 2)].timestamp)}</span><span>{dateLabel(points[points.length - 1].timestamp)}</span></div></> : <div className="chart-message">Historical data will appear when the selected feed returns enough data points.</div>}</div>
            <div className="chart-footer"><div className="period-control">{PERIODS.map(p => <button key={p} className={period === p ? "active" : ""} onClick={() => setPeriod(p)}>{p}</button>)}</div><span>Source: {market === "Crypto" ? "Configured crypto provider" : (selectedQuote as MarketQuote | undefined)?.source ?? (market === "Forex" ? "Frankfurter / configured provider" : "Configured India provider")}</span></div>
          </div>
            <div className="panel watch-panel"><div className="panel-top"><div><div className="section-kicker">YOUR INSTRUMENTS</div><h2>Watchlist</h2></div><button className="text-link" onClick={() => setPage("Watchlist")}>View all ↗</button></div><div className="watch-table"><div className="watch-head"><span>ASSET</span><span>LAST PRICE</span><span>24H</span></div>{allRows.filter(r => watchlist.includes(r.symbol)).slice(0, 6).map(row => <button className="watch-row" key={`${row.market}-${row.symbol}`} onClick={() => selectRow(row)}><span className="watch-asset"><i className={`asset-mark ${row.market.toLowerCase()}`}>{row.market === "India" ? "I" : row.market === "Forex" ? "F" : row.symbol.slice(0, 1)}</i><span><b>{row.symbol}</b><small>{row.name}</small></span></span><b className="watch-price">{row.currency === "INR" ? fmtINR(row.price) : row.currency === "USD" ? fmtUSD(row.price) : fmt(row.price, 4)}</b><span className={`watch-change ${row.change != null && row.change >= 0 ? "up" : "down"}`}>{row.change == null ? "—" : signed(row.change)}</span></button>)}{allRows.filter(r => watchlist.includes(r.symbol)).length === 0 && <div className="empty-state">No watchlist assets are currently available from the feeds.</div>}</div><button className="add-watch" onClick={() => setPage("Watchlist")}>＋ Manage watchlist</button></div></section>
          <section className="bottom-grid"><div className="panel movers-panel"><div className="panel-top"><div><div className="section-kicker">MARKET SNAPSHOT</div><h2>Instruments overview</h2></div><button className="text-link" onClick={() => setPage("Markets")}>Open markets ↗</button></div><div className="movers-list">{allRows.slice(0, 5).map(row => <button key={`${row.market}-${row.symbol}`} className="mover-row" onClick={() => selectRow(row)}><span className={`mover-symbol ${row.market.toLowerCase()}`}>{row.symbol.slice(0, 3)}</span><span className="mover-name"><b>{row.symbol}</b><small>{row.market} · {row.name}</small></span><span className="mover-price">{row.currency === "INR" ? fmtINR(row.price) : row.currency === "USD" ? fmtUSD(row.price) : fmt(row.price, 4)}</span><span className={`mover-change ${row.change != null && row.change >= 0 ? "up" : "down"}`}>{row.change == null ? "—" : signed(row.change)}</span></button>)}{allRows.length === 0 && <div className="empty-state">Market feeds are loading. Values appear when the APIs respond.</div>}</div></div><div className="panel insight-panel"><div className="panel-top"><div><div className="section-kicker">AI WORKSPACE</div><h2>Research assistant</h2></div><span className="ai-badge">✳ AI</span></div><p className="panel-copy">Ask a financial question and send it to the configured AI endpoint.</p><div className="prompt-chips"><button onClick={() => { setQuestion("What factors influence Bitcoin volatility?"); setPage("AI Research"); }}>Bitcoin volatility</button><button onClick={() => { setQuestion("Explain market risk in simple terms."); setPage("AI Research"); }}>Market risk</button></div><button className="button-primary full-button" onClick={() => setPage("AI Research")}>Open AI workspace <span>↗</span></button><div className="disclaimer">For research and education only. Not investment advice.</div></div></section>
        </>}

        {page === "Markets" && <><section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> MARKET DATA</div><h1>Markets<span className="heading-period">.</span></h1><p>Explore historical prices across supported asset classes.</p></div><button className="button-secondary" onClick={() => void loadMarkets()}>↻ Refresh feeds</button></section><div className="panel market-workspace"><div className="segmented large">{(["India", "Forex", "Crypto"] as Market[]).map(m => <button key={m} className={market === m ? "selected" : ""} onClick={() => setMarket(m)}>{m}</button>)}</div><div className="market-workspace-grid"><div className="market-asset-list"><div className="list-title">{marketLabel}<span>{marketRows.length} instruments</span></div><input className="field" value={search} onChange={e => setSearch(e.target.value)} placeholder="Filter instruments..." />{filteredRows.map(row => <button className={`asset-select ${selectedSymbol === row.symbol ? "selected" : ""}`} key={row.symbol} onClick={() => selectRow(row)}><span><b>{row.symbol}</b><small>{row.name}</small></span><span className="asset-select-price">{row.currency === "INR" ? fmtINR(row.price) : row.currency === "USD" ? fmtUSD(row.price) : fmt(row.price, 4)}<small className={row.change != null && row.change >= 0 ? "up" : "down"}>{row.change == null ? "—" : signed(row.change)}</small></span></button>)}{filteredRows.length === 0 && <div className="empty-state">{feedErrors[market] || "No instruments match this filter."}</div>}</div><div className="market-detail"><div className="detail-top"><div><div className="section-kicker">SELECTED INSTRUMENT</div><h2>{selectedSymbol}</h2><p>{selectedQuote?.name ?? "Waiting for market data"}</p></div><button className="button-secondary" onClick={() => toggleWatch(selectedSymbol)}>{watchlist.includes(selectedSymbol) ? "★ In watchlist" : "☆ Add to watchlist"}</button></div><div className="detail-price"><b>{selectedDisplayPrice}</b><span className={selectedQuote && (market === "Crypto" ? (selectedCryptoQuote?.change_24h_percent ?? 0) >= 0 : market === "Forex" ? (selectedForexQuote?.change_percent ?? 0) >= 0 : (selectedIndiaQuote?.change_percent ?? 0) >= 0) ? "up" : "down"}>{selectedQuote ? signed(market === "Crypto" ? (selectedCryptoQuote?.change_24h_percent ?? 0) : market === "Forex" ? (selectedForexQuote?.change_percent ?? 0) : (selectedIndiaQuote?.change_percent ?? 0)) : "Feed unavailable"}</span></div><div className="detail-chart">{historyLoading ? <div className="chart-message"><span className="loader" /> Loading chart…</div> : historyError ? <div className="chart-message chart-error">{historyError}</div> : points.length > 1 ? <><svg viewBox="0 0 900 250" preserveAspectRatio="none"><defs><linearGradient id="detailGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#b5f36c" stopOpacity=".18" /><stop offset="100%" stopColor="#b5f36c" stopOpacity="0" /></linearGradient></defs>{[40, 100, 160, 220].map(y => <line key={y} x1="0" y1={y} x2="900" y2={y} className="grid-line" />)}<path d={chart.area} fill="url(#detailGradient)" /><path d={chart.line} className="price-line" /></svg><div className="chart-x-labels"><span>{dateLabel(points[0].timestamp)}</span><span>{dateLabel(points[Math.floor(points.length / 2)].timestamp)}</span><span>{dateLabel(points[points.length - 1].timestamp)}</span></div></> : <div className="chart-message">No historical data available.</div>}</div><div className="chart-footer"><div className="period-control">{PERIODS.map(p => <button key={p} className={period === p ? "active" : ""} onClick={() => setPeriod(p)}>{p}</button>)}</div><span>History source: configured API</span></div></div></div></div></>}

        {page === "Watchlist" && <><section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> PERSONAL WORKSPACE</div><h1>Watchlist<span className="heading-period">.</span></h1><p>Keep the instruments you follow close at hand.</p></div></section><div className="panel table-panel"><div className="panel-top"><div><div className="section-kicker">SAVED INSTRUMENTS</div><h2>Tracked assets</h2></div><span className="muted-inline">{watchlist.length} symbols</span></div><div className="wide-table"><div className="wide-table-head"><span>INSTRUMENT</span><span>MARKET</span><span>LAST PRICE</span><span>CHANGE</span><span>ACTION</span></div>{watchlist.map(symbol => { const row = allRows.find(r => r.symbol === symbol); return <div className="wide-table-row" key={symbol}><button className="row-symbol" onClick={() => row && selectRow(row)}><b>{symbol}</b><small>{row?.name ?? "Feed not currently available"}</small></button><span>{row?.market ?? "—"}</span><b>{row ? row.currency === "INR" ? fmtINR(row.price) : row.currency === "USD" ? fmtUSD(row.price) : fmt(row.price, 4) : "—"}</b><span className={row?.change != null && row.change >= 0 ? "up" : "down"}>{row?.change == null ? "—" : signed(row.change)}</span><button className="remove-watch" onClick={() => toggleWatch(symbol)}>Remove</button></div> })}</div><div className="watch-add-row"><select className="field" id="add-watch-select" defaultValue=""><option value="" disabled>Add an available instrument…</option>{allRows.filter(r => !watchlist.includes(r.symbol)).map(r => <option key={`${r.market}-${r.symbol}`} value={`${r.market}|${r.symbol}`}>{r.symbol} · {r.market}</option>)}</select><button className="button-primary" onClick={() => { const el = document.getElementById("add-watch-select") as HTMLSelectElement | null; if (el?.value) { const [, symbol] = el.value.split("|"); setWatchlist(old => [...old, symbol]); el.value = ""; } }}>Add instrument</button></div></div></>}

        {page === "Analytics" && <><section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> MARKET METRICS</div><h1>Analytics<span className="heading-period">.</span></h1><p>Performance context from the feeds currently connected to your workspace.</p></div></section><section className="analytics-grid"><div className="panel analytics-card"><span className="section-kicker">SUPPORTED INSTRUMENTS</span><b className="analytics-value">{allRows.length}</b><p>Quotes received across all configured market feeds.</p></div><div className="panel analytics-card"><span className="section-kicker">WATCHLIST SIZE</span><b className="analytics-value">{watchlist.length}</b><p>Symbols saved in this browser session.</p></div><div className="panel analytics-card"><span className="section-kicker">API STATUS</span><b className={`analytics-value ${apiStatus === "online" ? "up" : apiStatus === "offline" ? "down" : ""}`}>{apiStatus === "online" ? "Online" : apiStatus === "offline" ? "Offline" : "Checking"}</b><p>Backend health endpoint response.</p></div></section><div className="panel table-panel"><div className="panel-top"><div><div className="section-kicker">DATA AVAILABILITY</div><h2>Market feed diagnostics</h2></div><button className="button-secondary" onClick={() => void loadMarkets()}>Run refresh</button></div>{(["India", "Forex", "Crypto"] as Market[]).map(m => <div className="diagnostic-row" key={m}><span className="diagnostic-led" /><span><b>{m}</b><small>{m === "India" ? "Indian market prices and history" : m === "Forex" ? "FX reference rates and history" : "Digital asset quotes and history"}</small></span><span className={feedErrors[m] ? "down" : "up"}>{feedErrors[m] ? feedErrors[m] : (m === "India" ? indiaQuotes.length : m === "Forex" ? forexQuotes.length : cryptoQuotes.length) + " quotes received"}</span></div>)}<p className="panel-note">Technical indicators, portfolio performance, drawdown and risk statistics require their own validated calculations and data. They are not fabricated in this interface.</p></div></>}

        {page === "AI Research" && <><section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> RESEARCH WORKSPACE</div><h1>AI Research<span className="heading-period">.</span></h1><p>Submit questions to the configured AI Q&amp;A and semantic retrieval endpoints.</p></div><span className="ai-badge large-badge">✳ AI ENABLED BY BACKEND</span></section><div className="research-grid"><div className="panel research-panel"><div className="panel-top"><div><div className="section-kicker">FINANCIAL Q&amp;A</div><h2>Ask the research assistant</h2></div><span className="ai-badge">✳ GROQ / API</span></div><p className="panel-copy">Ask a question. Responses depend on the current backend configuration and available context.</p><div className="prompt-chips"><button onClick={() => setQuestion("What factors influence Bitcoin volatility?")}>Bitcoin volatility</button><button onClick={() => setQuestion("Explain the relationship between interest rates and currency markets.")}>Rates &amp; FX</button><button onClick={() => setQuestion("What is market capitalization and why does it matter?")}>Market cap</button></div><form className="research-form" onSubmit={askAI}><label htmlFor="ai-question">YOUR QUESTION</label><textarea id="ai-question" value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask about a market, asset, or financial concept…" rows={4} /><div className="form-bottom"><span>POST · /api/v1/bitcoin/ask</span><button className="button-primary" disabled={askLoading || question.trim().length < 3}>{askLoading ? <><span className="loader small-loader" /> Thinking…</> : <>Run analysis <span>↗</span></>}</button></div></form>{answer && <div className="response-card"><div className="section-kicker">RESPONSE</div><p>{answer}</p></div>}<p className="panel-note">AI-generated output may be inaccurate. This is not investment advice.</p></div><div className="panel research-panel"><div className="panel-top"><div><div className="section-kicker">KNOWLEDGE RETRIEVAL</div><h2>Search research context</h2></div><span className="mini-tag">RAG</span></div><p className="panel-copy">Retrieve relevant indexed research chunks from the backend.</p><form className="research-form" onSubmit={searchResearch}><label htmlFor="research-query">SEMANTIC SEARCH</label><textarea id="research-query" value={researchQuery} onChange={e => setResearchQuery(e.target.value)} placeholder="e.g. What drives currency volatility?" rows={3} /><div className="form-bottom"><span>POST · /api/v1/research/search</span><button className="button-primary" disabled={researchLoading || !researchQuery.trim()}>{researchLoading ? "Searching…" : "Search context ↗"}</button></div></form>{researchError && <div className="inline-error">{researchError}</div>}{researchResults.map((r, i) => <article className="result-card" key={`${r.source}-${r.chunk_number}-${i}`}><div className="result-meta"><b>{r.source ?? "Retrieved source"}</b><span>{r.chunk_number != null ? `Chunk ${r.chunk_number}` : "Context result"}</span></div><p>{r.text ?? "No text field returned by API."}</p>{r.distance != null && <small>Distance: {r.distance.toFixed(4)}</small>}</article>)}{!researchResults.length && !researchError && !researchLoading && <div className="empty-state">Search results will appear here after a successful request.</div>}</div></div></>}

        {page === "RAG Pipeline" && <><section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> SYSTEM INTELLIGENCE</div><h1>RAG pipeline<span className="heading-period">.</span></h1><p>Retrieval-augmented generation workflow and current implementation map.</p></div></section><div className="panel pipeline-panel"><div className="pipeline-step"><span className="pipeline-number">01</span><div><b>Research query</b><p>User submits a financial question or semantic search query.</p></div><span className="state-chip">INPUT</span></div><div className="pipeline-connector" /><div className="pipeline-step"><span className="pipeline-number">02</span><div><b>Retrieval API</b><p><code>POST /api/v1/research/search</code> requests relevant indexed chunks.</p></div><span className="state-chip">API</span></div><div className="pipeline-connector" /><div className="pipeline-step"><span className="pipeline-number">03</span><div><b>Context ranking</b><p>Returned source, chunk number and distance are shown when supplied by the backend.</p></div><span className="state-chip">VERIFY</span></div><div className="pipeline-connector" /><div className="pipeline-step"><span className="pipeline-number">04</span><div><b>LLM response</b><p>Configured Q&amp;A endpoint generates an answer. Validate source grounding and quality with tests.</p></div><span className="state-chip">API</span></div></div><div className="panel table-panel"><div className="section-kicker">IMPLEMENTATION NOTE</div><h2>Pipeline status</h2><p className="panel-copy">This page documents the current UI integration points; it does not claim that each internal retrieval or agent stage has been independently verified.</p><button className="button-primary" onClick={() => setPage("AI Research")}>Test research endpoints ↗</button></div></>}

        {page === "API Explorer" && <><section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> DEVELOPER TOOLS</div><h1>API explorer<span className="heading-period">.</span></h1><p>Endpoints used by the frontend integration.</p></div><span className={`api-health ${apiStatus}`}>● {statusText}</span></section><div className="panel table-panel"><div className="panel-top"><div><div className="section-kicker">CONNECTED ROUTES</div><h2>API reference</h2></div><span className="muted-inline">{ROUTES.length} routes</span></div>{ROUTES.map(([method, path, description]) => <div className="api-route" key={path}><span className={`method-pill ${method.toLowerCase()}`}>{method}</span><code>{path}</code><span>{description}</span><button title="Copy endpoint path" onClick={() => void navigator.clipboard?.writeText(path)}>Copy</button></div>)}<p className="panel-note">Endpoint availability depends on the FastAPI backend running at {API} and the configured Vite/API setup.</p></div></>}

        <footer className="app-footer"><span>ALPHASIGHTAI <i>•</i> MARKET INTELLIGENCE WORKSPACE</span><span>Values reflect configured feeds · For research only</span></footer>
      </div>
    </main>
  </div>;
}

export default App;
