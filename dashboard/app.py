import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import random
import time

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="APD Monitor — HSE Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CONFIG — sesuaikan ini
# ─────────────────────────────────────────────
BACKEND_URL      = "http://localhost:8000"
REFRESH_INTERVAL = 60

# Shift dihitung dari jam di field "created_at"
# karena backend tidak punya field shift sama sekali
def timestamp_to_shift(dt: datetime) -> str:
    h = dt.hour
    if 6 <= h < 14:  return "PAGI"
    if 14 <= h < 22: return "SIANG"
    return "MALAM"

SHIFT_DISPLAY = {"PAGI": "06:00–14:00", "SIANG": "14:00–22:00", "MALAM": "22:00–06:00"}

# ─────────────────────────────────────────────
# GLOBAL CSS — Industrial Control-Room
# ─────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">

<style>
:root {
  --bg-base:      #080B10;
  --bg-panel:     #0E1318;
  --bg-card:      #141A22;
  --amber:        #F5A623;
  --amber-dim:    #7A5012;
  --cyan:         #00D4FF;
  --cyan-dim:     #004F61;
  --red:          #FF3B3B;
  --green:        #3DCC7E;
  --text-primary: #E8EDF2;
  --text-sec:     #7A8A99;
  --text-dim:     #3E4D5C;
  --border:       rgba(0,212,255,0.12);
  --border-amber: rgba(245,166,35,0.25);
  --glow-cyan:    0 0 20px rgba(0,212,255,0.25);
  --glow-amber:   0 0 20px rgba(245,166,35,0.35);
  --glow-red:     0 0 20px rgba(255,59,59,0.35);
}
html, body, [data-testid="stAppViewContainer"] {
  background-color: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-family: 'Rajdhani', sans-serif !important;
}
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }
[data-testid="block-container"] {
  padding: 1.5rem 2rem 3rem !important;
  max-width: 100% !important;
}
[data-testid="stAppViewContainer"]::before {
  content: ''; position: fixed; inset: 0;
  background-image:
    linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px; pointer-events: none; z-index: 0;
}
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--cyan-dim); border-radius: 2px; }

/* HEADER */
.hse-header {
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding-bottom: 1.25rem; margin-bottom: 1.75rem; position: relative;
}
.hse-header::after {
  content: ''; position: absolute; bottom: -1px; left: 0;
  width: 220px; height: 1px;
  background: linear-gradient(90deg, var(--cyan), transparent);
}
.hse-title {
  font-size: 26px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
  background: linear-gradient(90deg, var(--cyan) 0%, #7EEEFF 60%, var(--text-primary) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;
}
.hse-sub { font-size: 12px; font-family: 'Fira Code', monospace; color: var(--text-sec); letter-spacing: 0.06em; margin: 0; }
.hse-meta { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.hse-clock { font-family: 'Fira Code', monospace; font-size: 22px; color: var(--amber); letter-spacing: 0.08em; font-weight: 500; }
.hse-date  { font-size: 12px; font-family: 'Fira Code', monospace; color: var(--text-sec); }
.status-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: 'Fira Code', monospace; font-size: 10px; letter-spacing: 0.1em;
  padding: 3px 10px; border-radius: 2px; margin-top: 4px;
}
.status-live { background: rgba(61,204,126,0.12); border: 1px solid rgba(61,204,126,0.4); color: var(--green); }
.status-demo { background: rgba(245,166,35,0.12); border: 1px solid var(--border-amber); color: var(--amber); }
.status-dot  { width: 6px; height: 6px; border-radius: 50%; animation: blink 1.8s ease-in-out infinite; }
.status-live .status-dot { background: var(--green); }
.status-demo .status-dot { background: var(--amber); }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* SECTION LABEL */
.section-label {
  font-size: 11px; font-family: 'Fira Code', monospace; color: var(--cyan);
  letter-spacing: 0.18em; text-transform: uppercase; margin: 0 0 12px;
  display: flex; align-items: center; gap: 8px;
}
.section-label::before { content: '//'; color: var(--text-dim); }

/* KPI CARDS */
.kpi-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 4px; padding: 18px 20px 16px;
  position: relative; overflow: hidden; transition: border-color 0.2s;
}
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; }
.kpi-card.amber::before { background: var(--amber); box-shadow: var(--glow-amber); }
.kpi-card.cyan::before  { background: var(--cyan);  box-shadow: var(--glow-cyan);  }
.kpi-card.red::before   { background: var(--red);   box-shadow: var(--glow-red);   }
.kpi-card.green::before { background: var(--green); }
.kpi-card:hover { border-color: rgba(0,212,255,0.3); }
.kpi-label { font-size: 10px; font-family: 'Fira Code', monospace; color: var(--text-sec); letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 8px; }
.kpi-value { font-size: 38px; font-weight: 700; line-height: 1; margin: 0 0 6px; letter-spacing: -0.01em; }
.kpi-card.amber .kpi-value { color: var(--amber); }
.kpi-card.cyan  .kpi-value { color: var(--cyan);  }
.kpi-card.red   .kpi-value { color: var(--red);   }
.kpi-card.green .kpi-value { color: var(--green); }
.kpi-delta { font-size: 11px; font-family: 'Fira Code', monospace; color: var(--text-sec); }
.kpi-delta .up   { color: var(--green); }
.kpi-delta .down { color: var(--red); }
.kpi-icon { position: absolute; top: 16px; right: 16px; font-size: 28px; opacity: 0.12; }

/* PANEL */
.panel { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 4px; padding: 20px 22px; margin-bottom: 4px; }
.panel-title { font-size: 13px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-primary); margin: 0 0 16px; }
.panel-title span.accent { color: var(--cyan); }

/* SHIFT BAR */
.shift-row { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.shift-name { font-family: 'Fira Code', monospace; font-size: 11px; color: var(--text-sec); width: 80px; flex-shrink: 0; }
.shift-sub  { font-size: 9px; font-family: 'Fira Code'; color: var(--text-dim); margin-top: 1px; }
.shift-bar-track { flex: 1; height: 8px; background: rgba(255,255,255,0.05); border-radius: 1px; overflow: hidden; }
.shift-bar-fill  { height: 100%; border-radius: 1px; }
.shift-pct { font-family: 'Fira Code', monospace; font-size: 14px; font-weight: 500; width: 50px; text-align: right; flex-shrink: 0; }
.good { background: var(--green); color: var(--green); }
.warn { background: var(--amber); color: var(--amber); }
.crit { background: var(--red);   color: var(--red);   }

/* APD ROW */
.apd-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.apd-row:last-child { border-bottom: none; }
.apd-name  { font-size: 13px; font-weight: 600; letter-spacing: 0.08em; }
.apd-count { font-family: 'Fira Code', monospace; font-size: 20px; font-weight: 500; }
.apd-lbl   { font-size: 10px; font-family: 'Fira Code', monospace; color: var(--text-sec); margin-top: 1px; }

/* VIOLATION TABLE */
.vtable { width: 100%; border-collapse: collapse; font-size: 12px; }
.vtable th { font-family: 'Fira Code', monospace; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-sec); padding: 8px 12px; border-bottom: 1px solid var(--border); text-align: left; font-weight: 400; }
.vtable td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.03); color: var(--text-primary); font-size: 13px; }
.vtable tr:hover td { background: rgba(0,212,255,0.03); }
.badge-v { display: inline-block; font-family: 'Fira Code', monospace; font-size: 9px; letter-spacing: 0.08em; padding: 2px 7px; border-radius: 2px; font-weight: 500; }
.badge-verified   { background: rgba(61,204,126,0.15);  color: var(--green);    border: 1px solid rgba(61,204,126,0.3); }
.badge-unverified { background: rgba(245,166,35,0.15);  color: var(--amber);    border: 1px solid rgba(245,166,35,0.3); }
.badge-false      { background: rgba(122,138,153,0.15); color: var(--text-sec); border: 1px solid rgba(122,138,153,0.3); }
.apd-tag { display: inline-block; font-family: 'Fira Code', monospace; font-size: 9px; padding: 2px 6px; border-radius: 2px; margin-right: 3px; background: rgba(255,59,59,0.12); color: var(--red); border: 1px solid rgba(255,59,59,0.25); }

.hse-divider { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DEMO DATA — dipakai saat backend tidak tersedia
# ─────────────────────────────────────────────
DEMO_AREAS = ["Assembly Line A", "Welding Zone B", "Painting Bay C", "Warehouse D", "QC Station E"]

def make_demo_data():
    random.seed(42)
    today = datetime.now()

    # Trend 30 hari
    trend = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        total     = random.randint(80, 160)
        compliant = random.randint(int(total * 0.70), total)
        trend.append({
            "date": d.strftime("%d %b"),
            "total": total,
            "compliant": compliant,
            "compliance_rate": round(compliant / total * 100, 1),
        })
    df_trend = pd.DataFrame(trend)

    # Per area × shift
    area_rows = []
    for area in DEMO_AREAS:
        for shift in ["PAGI", "SIANG", "MALAM"]:
            total     = random.randint(20, 60)
            compliant = random.randint(int(total * 0.60), total)
            area_rows.append({"area": area, "shift": shift,
                               "rate": round(compliant / total * 100, 1),
                               "violations": total - compliant})
    df_area = pd.DataFrame(area_rows)

    # Summary — nama field sama persis dengan ViolationSummary dari backend
    total_v      = random.randint(80, 130)
    verified     = random.randint(40, 70)
    unverified   = random.randint(20, 40)
    false_alarms = max(total_v - verified - unverified, 0)
    summary = {
        "total_violations":     total_v,
        "verified":             verified,
        "unverified":           unverified,
        "false_alarms":         false_alarms,      # ← sesuai schema: "false_alarms"
        "missing_helmet_count": random.randint(30, 60),  # ← sesuai schema
        "missing_vest_count":   random.randint(20, 45),  # ← sesuai schema
        "missing_mask_count":   random.randint(15, 35),  # ← sesuai schema
        "overall_compliance":   round(random.uniform(74, 91), 1),
    }

    shift_compliance = df_area.groupby("shift")["rate"].mean().round(1).to_dict()

    # Violations terbaru — field sesuai ViolationResponse dari backend
    rows = []
    for _ in range(15):
        ts   = today - timedelta(hours=random.randint(0, 48), minutes=random.randint(0, 59))
        helm = random.choice([True, False])
        vest = random.choice([True, False])
        mask = random.choice([True, False])
        if not helm and not vest and not mask:
            helm = True
        apd_parts = []
        if helm: apd_parts.append("Helm")
        if vest: apd_parts.append("Rompi")
        if mask: apd_parts.append("Masker")
        rows.append({
            "time":            ts.strftime("%d/%m %H:%M"),
            "worker":          f"Pekerja-{random.randint(100, 999)}",   # worker_name_manual
            "area":            random.choice(DEMO_AREAS),                # dari camera_location
            "shift":           timestamp_to_shift(ts),                   # dihitung dari timestamp
            "apd":             "+".join(apd_parts),
            "status":          random.choice(["verified","verified","unverified","unverified","false_alarm"]),
        })
    rows.sort(key=lambda x: x["time"], reverse=True)
    df_viol = pd.DataFrame(rows)

    return summary, shift_compliance, df_trend, df_area, df_viol


# ─────────────────────────────────────────────
# FETCH DARI BACKEND — field name SESUAI schema asli
# ─────────────────────────────────────────────
@st.cache_data(ttl=REFRESH_INTERVAL)
def fetch_data():
    """
    Field name disesuaikan dengan skema backend yang ada:
      - ViolationSummary  (schemas/violation.py)
      - ViolationResponse (schemas/violation.py)
      - CaptureResponse   (schemas/capture.py)
    Shift dihitung dari created_at karena tidak ada field shift di backend.
    Area diambil dari captures.camera_location lewat capture_id.
    """
    try:
        r_sum  = requests.get(f"{BACKEND_URL}/api/violations/summary", timeout=3)
        r_viol = requests.get(f"{BACKEND_URL}/api/violations/",        timeout=3)
        r_cap  = requests.get(f"{BACKEND_URL}/api/captures/",          timeout=3)

        if not (r_sum.ok and r_viol.ok and r_cap.ok):
            raise ConnectionError("Salah satu endpoint tidak bisa diakses")

        # ── 1. Summary (sesuai ViolationSummary) ──
        raw = r_sum.json()
        total_v      = raw.get("total_violations", 0)
        verified     = raw.get("verified", 0)
        unverified   = raw.get("unverified", 0)
        false_alarms = raw.get("false_alarms", 0)       # bukan "false_alarm"
        no_helm      = raw.get("missing_helmet_count", 0)
        no_vest      = raw.get("missing_vest_count", 0)
        no_mask      = raw.get("missing_mask_count", 0)

        # Compliance = (foto processed - violations) / foto processed
        # Backend tidak punya field ini, kita hitung sendiri
        caps = r_cap.json()
        caps_processed = sum(1 for c in caps if c.get("status") == "processed")
        if caps_processed > 0 and total_v <= caps_processed:
            compliance = round((caps_processed - total_v) / caps_processed * 100, 1)
        else:
            compliance = 0.0

        summary = {
            "total_violations":     total_v,
            "verified":             verified,
            "unverified":           unverified,
            "false_alarms":         false_alarms,
            "missing_helmet_count": no_helm,
            "missing_vest_count":   no_vest,
            "missing_mask_count":   no_mask,
            "overall_compliance":   compliance,
        }

        # ── 2. Lookup capture_id → camera_location ──
        # Sesuai CaptureResponse: field "camera_location"
        cap_lookup = {c["id"]: (c.get("camera_location") or "—") for c in caps}

        # ── 3. Parse violations (sesuai ViolationResponse) ──
        violations = r_viol.json()
        rows = []
        for v in violations:
            # Timestamp dari "created_at"
            raw_ts = v.get("created_at", "")
            try:
                ts       = datetime.fromisoformat(raw_ts.split("+")[0].split("Z")[0])
                time_str = ts.strftime("%d/%m %H:%M")
                shift    = timestamp_to_shift(ts)     # dihitung dari jam
            except Exception:
                time_str = raw_ts[:16].replace("T", " ")
                shift    = "—"

            # Nama pekerja: "worker_name_manual" (bukan "worker_name")
            worker = v.get("worker_name_manual") or "—"

            # Area: ambil camera_location dari captures via capture_id
            cap_id = v.get("capture_id")
            area   = cap_lookup.get(cap_id, "—") if cap_id else "—"

            # APD dari field boolean (bukan string)
            apd_parts = []
            if v.get("missing_helmet"): apd_parts.append("Helm")
            if v.get("missing_vest"):   apd_parts.append("Rompi")
            if v.get("missing_mask"):   apd_parts.append("Masker")

            rows.append({
                "time":   time_str,
                "worker": worker,
                "area":   area,
                "shift":  shift,
                "apd":    "+".join(apd_parts) if apd_parts else "—",
                "status": v.get("status", "unverified"),
            })

        df_viol = pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["time","worker","area","shift","apd","status"])

        # ── 4. Trend per hari dari violations ──
        today = datetime.now()
        trend = []
        for i in range(29, -1, -1):
            d     = today - timedelta(days=i)
            d_key = d.strftime("%Y-%m-%d")
            day_v = sum(1 for v in violations if v.get("created_at","")[:10] == d_key)
            day_c = sum(1 for c in caps       if c.get("captured_at","")[:10] == d_key)
            total     = max(day_c, 1)
            compliant = max(total - day_v, 0)
            trend.append({
                "date": d.strftime("%d %b"),
                "total": total,
                "compliant": compliant,
                "compliance_rate": round(compliant / total * 100, 1),
            })
        df_trend = pd.DataFrame(trend)

        # ── 5. Kepatuhan per area × shift dari violations ──
        area_shift: dict = {}
        for v in violations:
            cap_id = v.get("capture_id")
            area   = cap_lookup.get(cap_id, "Unknown") if cap_id else "Unknown"
            raw_ts = v.get("created_at","")
            try:
                ts    = datetime.fromisoformat(raw_ts.split("+")[0].split("Z")[0])
                shift = timestamp_to_shift(ts)
            except Exception:
                shift = "PAGI"
            key = (area, shift)
            if key not in area_shift:
                area_shift[key] = {"total": 0, "violations": 0}
            area_shift[key]["total"]      += 1
            area_shift[key]["violations"] += 1

        area_rows = [
            {"area": a, "shift": s,
             "rate": round(max(d["total"]-d["violations"],0)/max(d["total"],1)*100,1),
             "violations": d["violations"]}
            for (a,s), d in area_shift.items()
        ]
        df_area = pd.DataFrame(area_rows) if area_rows else pd.DataFrame(
            columns=["area","shift","rate","violations"])

        shift_compliance = (
            df_area.groupby("shift")["rate"].mean().round(1).to_dict()
            if not df_area.empty else {"PAGI":0.0,"SIANG":0.0,"MALAM":0.0}
        )

        return summary, shift_compliance, df_trend, df_area, df_viol, True

    except Exception:
        summary, shift_c, df_trend, df_area, df_viol = make_demo_data()
        return summary, shift_c, df_trend, df_area, df_viol, False


# ─────────────────────────────────────────────
# AUTO-REFRESH — aman tanpa time.sleep di main loop
# ─────────────────────────────────────────────
def init_refresh():
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()

def check_refresh() -> int:
    """Return detik tersisa. Kalau sudah waktunya, clear cache & rerun."""
    elapsed = time.time() - st.session_state.last_refresh
    if elapsed >= REFRESH_INTERVAL:
        st.session_state.last_refresh = time.time()
        fetch_data.clear()
        st.rerun()
    return max(0, int(REFRESH_INTERVAL - elapsed))


# ─────────────────────────────────────────────
# CHART BUILDERS
# ─────────────────────────────────────────────
CHART_BG = "rgba(0,0,0,0)"
FONT_MONO = "Fira Code"
FONT_MAIN = "Rajdhani"
GRID_CLR  = "rgba(0,212,255,0.07)"
TEXT_SEC  = "#7A8A99"

def chart_trend(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["compliance_rate"],
        mode="none", fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["compliance_rate"],
        mode="lines+markers",
        line=dict(color="#00D4FF", width=2, shape="spline"),
        marker=dict(size=5, color="#00D4FF", line=dict(color="#080B10", width=1.5)),
        hovertemplate="<b>%{x}</b><br>Kepatuhan: <b>%{y}%</b><extra></extra>",
    ))
    fig.add_hline(y=85, line_dash="dot", line_color="rgba(245,166,35,0.5)", line_width=1,
                  annotation_text="Target 85%",
                  annotation_font=dict(color="#F5A623", size=10, family=FONT_MONO),
                  annotation_position="right")
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=0,r=60,t=10,b=0), height=220,
        font=dict(family=FONT_MAIN, color=TEXT_SEC, size=11),
        xaxis=dict(showgrid=False, zeroline=False, tickangle=-30, nticks=10,
                   tickfont=dict(family=FONT_MONO, size=10, color=TEXT_SEC)),
        yaxis=dict(range=[50,105], showgrid=True, gridcolor=GRID_CLR, zeroline=False,
                   ticksuffix="%", tickfont=dict(family=FONT_MONO, size=10, color=TEXT_SEC)),
        showlegend=False,
        hoverlabel=dict(bgcolor="#141A22", bordercolor="#00D4FF",
                        font=dict(family=FONT_MONO, size=11, color="#E8EDF2")),
    )
    return fig

def chart_area_heatmap(df):
    if df.empty:
        return go.Figure()
    pivot = df.pivot_table(index="area", columns="shift", values="rate", aggfunc="mean").round(1)
    ordered = [s for s in ["PAGI","SIANG","MALAM"] if s in pivot.columns]
    pivot = pivot[ordered]
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale=[[0,"#5C0F0F"],[0.55,"#7A5012"],[0.75,"#1A4040"],[1,"#0E3B22"]],
        zmin=50, zmax=100,
        text=[[f"{v:.0f}%" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(family=FONT_MONO, size=12, color="#E8EDF2"),
        hoverongaps=False,
        hovertemplate="<b>%{y}</b> · %{x}<br>Kepatuhan: <b>%{z}%</b><extra></extra>",
        showscale=True,
        colorbar=dict(thickness=8, ticksuffix="%", outlinewidth=0,
                      tickfont=dict(family=FONT_MONO, size=9, color=TEXT_SEC)),
    ))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=0,r=0,t=8,b=0), height=220,
        font=dict(family=FONT_MAIN, color=TEXT_SEC),
        xaxis=dict(tickfont=dict(family=FONT_MONO, size=11, color="#00D4FF"),
                   side="top", showgrid=False),
        yaxis=dict(tickfont=dict(family=FONT_MONO, size=10, color=TEXT_SEC),
                   showgrid=False, autorange="reversed"),
        hoverlabel=dict(bgcolor="#141A22", bordercolor="#00D4FF",
                        font=dict(family=FONT_MONO, size=11, color="#E8EDF2")),
    )
    return fig

def chart_apd_donut(summary):
    values    = [summary["missing_helmet_count"], summary["missing_vest_count"], summary["missing_mask_count"]]
    total_apd = sum(values)
    fig = go.Figure(go.Pie(
        labels=["Tanpa Helm","Tanpa Rompi","Tanpa Masker"], values=values, hole=0.68,
        marker=dict(colors=["#FF3B3B","#F5A623","#00D4FF"], line=dict(color="#080B10", width=3)),
        textinfo="none",
        hovertemplate="<b>%{label}</b><br>Pelanggaran: <b>%{value}</b><br>Porsi: <b>%{percent}</b><extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{total_apd}</b>",
                        font=dict(family=FONT_MONO, size=26, color="#E8EDF2"),
                        showarrow=False, x=0.5, y=0.55)
    fig.add_annotation(text="kasus",
                        font=dict(family=FONT_MAIN, size=11, color=TEXT_SEC),
                        showarrow=False, x=0.5, y=0.38)
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=0,r=0,t=0,b=0), height=220, showlegend=True,
        legend=dict(font=dict(family=FONT_MAIN, size=12, color=TEXT_SEC),
                    orientation="v", x=1.05, y=0.5, bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#141A22", bordercolor="#FF3B3B",
                        font=dict(family=FONT_MONO, size=11, color="#E8EDF2")),
    )
    return fig

def chart_daily_violations(df):
    last7  = df.tail(7)
    colors = ["#FF3B3B" if r < 80 else "#F5A623" if r < 87 else "#3DCC7E"
              for r in last7["compliance_rate"]]
    fig = go.Figure(go.Bar(
        x=last7["date"], y=last7["total"] - last7["compliant"],
        marker_color=colors, marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Pelanggaran: <b>%{y}</b><extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=0,r=0,t=10,b=0), height=170,
        font=dict(family=FONT_MAIN, color=TEXT_SEC, size=11),
        xaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(family=FONT_MONO, size=9, color=TEXT_SEC)),
        yaxis=dict(showgrid=True, gridcolor=GRID_CLR, zeroline=False,
                   tickfont=dict(family=FONT_MONO, size=9, color=TEXT_SEC)),
        bargap=0.3,
        hoverlabel=dict(bgcolor="#141A22", bordercolor="#F5A623",
                        font=dict(family=FONT_MONO, size=11, color="#E8EDF2")),
    )
    return fig


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def color_class(rate):
    if rate >= 87: return "good"
    if rate >= 75: return "warn"
    return "crit"

def badge_html(status):
    m = {"verified":("badge-verified","VERIFIED"),
         "unverified":("badge-unverified","UNVERIFIED"),
         "false_alarm":("badge-false","FALSE ALARM")}
    cls, label = m.get(status, ("badge-unverified", status.upper()))
    return f'<span class="badge-v {cls}">{label}</span>'

def apd_tags(apd_str):
    if not apd_str or apd_str == "—":
        return '<span style="color:var(--text-dim)">—</span>'
    return " ".join(f'<span class="apd-tag">{p.strip()}</span>' for p in apd_str.split("+"))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    init_refresh()
    seconds_left = check_refresh()   # akan rerun kalau sudah waktunya

    summary, shift_compliance, df_trend, df_area, df_viol, is_live = fetch_data()
    now = datetime.now()

    # ── HEADER ──
    sc  = "status-live" if is_live else "status-demo"
    sl  = "LIVE · BACKEND" if is_live else "DEMO · BACKEND OFFLINE"
    st.markdown(f"""
    <div class="hse-header">
      <div>
        <p class="hse-title">APD Monitor</p>
        <p class="hse-sub">HSE KPI Dashboard</p>
      </div>
      <div class="hse-meta">
        <div class="hse-clock">{now.strftime('%H:%M:%S')}</div>
        <div class="hse-date">{now.strftime('%A, %d %B %Y')}</div>
        <div class="{sc} status-pill"><div class="status-dot"></div>{sl}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── KPI CARDS ──
    st.markdown('<p class="section-label">KPI Utama</p>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    compliance = summary["overall_compliance"]
    comp_color = "green" if compliance >= 87 else "amber" if compliance >= 75 else "red"
    total_v    = summary["total_violations"]

    with c1:
        st.markdown(f"""
        <div class="kpi-card {comp_color}">
          <span class="kpi-icon">⬡</span>
          <p class="kpi-label">Kepatuhan Keseluruhan</p>
          <p class="kpi-value">{compliance}%</p>
          <p class="kpi-delta">dari foto yang diproses backend</p>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card red">
          <span class="kpi-icon">⚠</span>
          <p class="kpi-label">Total Pelanggaran</p>
          <p class="kpi-value">{total_v}</p>
          <p class="kpi-delta">keseluruhan tercatat</p>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card amber">
          <span class="kpi-icon">◎</span>
          <p class="kpi-label">Perlu Diverifikasi</p>
          <p class="kpi-value">{summary['unverified']}</p>
          <p class="kpi-delta">dari {total_v} total</p>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card cyan">
          <span class="kpi-icon">✓</span>
          <p class="kpi-label">Sudah Diverifikasi</p>
          <p class="kpi-value">{summary['verified']}</p>
          <p class="kpi-delta"><span class="up">{summary['false_alarms']}</span> false alarm</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── TREND + SHIFT ──
    col_t, col_s = st.columns([3, 1])
    with col_t:
        st.markdown('<div class="panel"><p class="panel-title">Trend Kepatuhan <span class="accent">30 Hari</span></p>', unsafe_allow_html=True)
        st.plotly_chart(chart_trend(df_trend), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with col_s:
        st.markdown('<div class="panel"><p class="panel-title">Per <span class="accent">Shift</span></p>', unsafe_allow_html=True)
        for name, time_range in SHIFT_DISPLAY.items():
            rate = shift_compliance.get(name, 0.0)
            cls  = color_class(rate)
            st.markdown(f"""
            <div class="shift-row">
              <div><div class="shift-name">{name}</div><div class="shift-sub">{time_range}</div></div>
              <div class="shift-bar-track"><div class="shift-bar-fill {cls}" style="width:{rate}%"></div></div>
              <div class="shift-pct {cls}">{rate}%</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── HEATMAP + DONUT + BAR ──
    col_h, col_d, col_b = st.columns([2, 1.2, 1.4])
    with col_h:
        st.markdown('<div class="panel"><p class="panel-title">Kepatuhan per <span class="accent">Area × Shift</span></p>', unsafe_allow_html=True)
        st.plotly_chart(chart_area_heatmap(df_area), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with col_d:
        st.markdown('<div class="panel"><p class="panel-title">Jenis <span class="accent">APD</span></p>', unsafe_allow_html=True)
        st.plotly_chart(chart_apd_donut(summary), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="panel"><p class="panel-title">Pelanggaran <span class="accent">7 Hari</span></p>', unsafe_allow_html=True)
        st.plotly_chart(chart_daily_violations(df_trend), use_container_width=True, config={"displayModeBar": False})
        total_apd = (summary["missing_helmet_count"] +
                     summary["missing_vest_count"] +
                     summary["missing_mask_count"])
        for apd, key, color in [
            ("HELM",   "missing_helmet_count", "#FF3B3B"),
            ("ROMPI",  "missing_vest_count",   "#F5A623"),
            ("MASKER", "missing_mask_count",   "#00D4FF"),
        ]:
            count = summary[key]
            pct   = round(count / total_apd * 100) if total_apd else 0
            st.markdown(f"""
            <div class="apd-row">
              <div><div class="apd-name" style="color:{color}">{apd}</div><div class="apd-lbl">{pct}% dari total</div></div>
              <div class="apd-count" style="color:{color}">{count}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── VIOLATION TABLE ──
    st.markdown('<p class="section-label">Pelanggaran Terbaru</p>', unsafe_allow_html=True)
    fc1, fc2, _ = st.columns([1, 1, 4])
    with fc1:
        filter_status = st.selectbox("Status", ["Semua","unverified","verified","false_alarm"],
                                     label_visibility="collapsed")
    with fc2:
        filter_shift = st.selectbox("Shift", ["Semua Shift","PAGI","SIANG","MALAM"],
                                    label_visibility="collapsed")

    df_show = df_viol.copy()
    if not df_show.empty:
        if filter_status != "Semua":
            df_show = df_show[df_show["status"] == filter_status]
        if filter_shift != "Semua Shift":
            df_show = df_show[df_show["shift"] == filter_shift]

    rows_html = ""
    for _, row in df_show.head(12).iterrows():
        rows_html += f"""
        <tr>
          <td><span style="font-family:'Fira Code';font-size:11px;color:var(--text-sec)">{row['time']}</span></td>
          <td><b>{row['worker']}</b></td>
          <td>{row['area']}</td>
          <td><span style="font-family:'Fira Code';font-size:11px;color:#00D4FF">{row['shift']}</span></td>
          <td>{apd_tags(row['apd'])}</td>
          <td>{badge_html(row['status'])}</td>
        </tr>"""
    if not rows_html:
        rows_html = '<tr><td colspan="6" style="text-align:center;color:var(--text-dim);padding:24px">Tidak ada data</td></tr>'

    st.markdown(f"""
    <div class="panel">
      <table class="vtable">
        <thead><tr>
          <th>Waktu</th><th>Pekerja</th><th>Area (Kamera)</th>
          <th>Shift</th><th>APD Dilanggar</th><th>Status</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>""", unsafe_allow_html=True)

    # ── FOOTER ──
    st.markdown(f"""
    <hr class="hse-divider">
    <div style="display:flex;justify-content:space-between">
      <span style="font-family:'Fira Code';font-size:10px;color:var(--text-dim)">
        APD MONITOR v1.1 · HSE EPSON MFG · {'LIVE DATA' if is_live else 'DEMO MODE'}
      </span>
      <span style="font-family:'Fira Code';font-size:10px;color:var(--text-dim)">
        Shift dihitung dari timestamp · Area dari camera_location · Refresh {seconds_left}s
      </span>
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()