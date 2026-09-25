#!/usr/bin/env python3
"""
ARHPP Full Application Builder – Stage 1
=========================================
سكربت واحد متراكم. كل مرحلة لاحقة تُضاف أسفل هذه المرحلة.
عند التشغيل: ينشئ مشروع ARHPP كاملاً جاهزاً للتشغيل.

التشغيل:
    python build_arhpp_full.py

بعد التشغيل ستجد مجلد ARHPP_App/ يحتوي على كل الملفات.
"""

import os
import sys
from pathlib import Path

ROOT = Path("ARHPP_App")
print("=" * 60)
print("ARHPP Full Application Builder – Stage 1")
print("Creating project structure and Main Dashboard...")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# 1. إنشاء هيكل المجلدات
# ─────────────────────────────────────────────────────────────
dirs = [
    ROOT,
    ROOT / "core",
    ROOT / "ui",
    ROOT / "ui" / "pages",
    ROOT / "ui" / "components",
    ROOT / "assets",
    ROOT / "data",
    ROOT / "config",
    ROOT / "engines",
]

for d in dirs:
    d.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ {d}")

# ─────────────────────────────────────────────────────────────
# 2. ملف الإعدادات (اسم التطبيق قابل للتغيير)
# ─────────────────────────────────────────────────────────────
config_content = '''# ARHPP Configuration
# يمكنك تغيير اسم التطبيق من هنا أو من داخل الواجهة

APP_NAME = "ARHPP Digital Twin"          # ← غيّر الاسم هنا
APP_VERSION = "1.0.0-Stage1"
APP_SUBTITLE = "Managed Pressure Drilling & Hydraulics Simulator"

# Default well
DEFAULT_WELL = "RI-0001"
DEFAULT_FIELD = "Kuwait"

# Theme
DARK_THEME = True
PRIMARY_COLOR = "#00d4aa"       # لون أخضر سماوي مثل Victus
ACCENT_COLOR = "#1f4e79"
BACKGROUND = "#1a1d23"
PANEL_BG = "#252a33"

# Simulation
UPDATE_RATE_HZ = 2
DEFAULT_MODE = "Offline"        # Offline | Simulation | Live
'''

(ROOT / "config" / "settings.py").write_text(config_content, encoding="utf-8")
print("  ✓ config/settings.py")

# ─────────────────────────────────────────────────────────────
# 3. محرك الحسابات الأساسي (مستند إلى Excel v4)
# ─────────────────────────────────────────────────────────────
engine_content = '''"""
ARHPP Hydraulics Engine – Stage 1
مستند بالكامل إلى ARHPP_Excel_Reference_Simulator_v4.xlsx
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class WellGeometry:
    md: float = 12000.0
    tvd: float = 11200.0
    hole_id: float = 8.5
    pipe_od: float = 5.0
    casing_od: float = 9.625
    bit_depth: float = 12000.0

@dataclass
class FluidProperties:
    density_ppg: float = 10.5
    pv: float = 28.0
    yp: float = 18.0
    n: float = 0.72
    K: float = 0.45
    tau_y: float = 6.5
    temp_in: float = 120.0
    temp_out: float = 155.0

@dataclass
class OperatingParams:
    flow_in_gpm: float = 850.0
    flow_out_gpm: float = 845.0
    sbp_setpoint: float = 200.0
    choke_position: float = 42.0
    rpm: float = 120.0
    wob: float = 25.0
    rop: float = 45.0
    spp_measured: float = 2850.0

@dataclass
class BitParams:
    bit_type: str = "PDC"
    tfa: float = 0.85
    bit_size: float = 8.5

@dataclass
class SimulationState:
    geometry: WellGeometry = field(default_factory=WellGeometry)
    fluid: FluidProperties = field(default_factory=FluidProperties)
    operating: OperatingParams = field(default_factory=OperatingParams)
    bit: BitParams = field(default_factory=BitParams)
    mode: str = "Offline"          # Offline | Simulation | Live
    choke_mode: str = "AUTO"       # MANUAL | AUTO | CBHP
    target_bhp: float = 7500.0
    target_ecd: float = 11.20

    # Results (calculated)
    bhp: float = 0.0
    ecd: float = 0.0
    model_spp: float = 0.0
    annular_friction: float = 0.0
    bit_pressure_drop: float = 0.0
    hydrostatic: float = 0.0
    live_pp: float = 0.0
    overbalance: float = 0.0
    u_tube_dp: float = 0.0
    effective_flow: float = 0.0

def calculate_hydrostatic(density_ppg: float, tvd_ft: float) -> float:
    """P_h = 0.052 * ρ * TVD"""
    return 0.052 * density_ppg * tvd_ft

def calculate_bit_pressure_drop(q_gpm: float, density: float, tfa: float) -> float:
    """ΔP_bit = (Q² * ρ) / (12031 * TFA²)"""
    if tfa <= 0:
        return 0.0
    return (q_gpm ** 2 * density) / (12031.0 * tfa ** 2)

def calculate_annular_friction(q_gpm: float, density: float, hole_id: float, pipe_od: float, length: float, n: float = 0.72, K: float = 0.45) -> float:
    """Simplified Merlo-style annular friction (Stage 1)"""
    dh = hole_id - pipe_od
    if dh <= 0 or length <= 0:
        return 0.0
    # Approximate velocity ft/s
    area = (math.pi / 4.0) * (hole_id**2 - pipe_od**2) / 144.0  # ft²
    v = (q_gpm * 0.133681) / area if area > 0 else 0.0  # ft/s approx
    # Simplified friction
    re_approx = 928.0 * density * v * dh / (K * 100.0 + 1e-6)
    f = 16.0 / max(re_approx, 1.0) if re_approx < 2100 else 0.046 * (re_approx ** -0.2)
    dp = f * density * v**2 * length / (25.8 * dh)
    return max(dp, 0.0)

def calculate_live_pp(tvd: float, litho_gradient: float = 0.56, bit_factor: float = 1.0, rop_factor: float = 0.97) -> float:
    """Live Expected Pore Pressure"""
    return tvd * litho_gradient * bit_factor * rop_factor

def run_hydraulics(state: SimulationState) -> SimulationState:
    """Main calculation – order matches Excel v4 physical order"""
    g = state.geometry
    f = state.fluid
    o = state.operating
    b = state.bit

    # 1. Effective Flow (simplified Stage 1)
    q_loss = max(0.0, o.flow_in_gpm - o.flow_out_gpm)
    q_utube = 8.0  # placeholder, will be refined
    state.effective_flow = o.flow_in_gpm + q_utube - q_loss

    # 2. Hydrostatic
    state.hydrostatic = calculate_hydrostatic(f.density_ppg, g.tvd)

    # 3. Bit pressure drop
    state.bit_pressure_drop = calculate_bit_pressure_drop(state.effective_flow, f.density_ppg, b.tfa)

    # 4. Annular friction
    state.annular_friction = calculate_annular_friction(
        state.effective_flow, f.density_ppg, g.hole_id, g.pipe_od, g.md, f.n, f.K
    )

    # 5. BHP & ECD
    state.bhp = state.hydrostatic + state.annular_friction + o.sbp_setpoint
    state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0

    # 6. Model SPP (simplified)
    pipe_friction = state.annular_friction * 1.8  # rough
    state.model_spp = pipe_friction + state.bit_pressure_drop + o.sbp_setpoint + 150

    # 7. Live PP
    bit_factor = 1.0 if b.bit_type == "PDC" else 1.05 if "Impregnated" in b.bit_type else 0.95
    state.live_pp = calculate_live_pp(g.tvd, 0.56, bit_factor, 0.97)
    state.overbalance = state.bhp - state.live_pp

    # 8. U-Tube (placeholder)
    state.u_tube_dp = 45.0

    return state

def get_profile_depth_data(state: SimulationState, num_points: int = 12) -> List[Dict]:
    """Generate Profile Depth Data rows (matching Victus columns)"""
    rows = []
    md_step = state.geometry.md / max(num_points - 1, 1)
    for i in range(num_points):
        md = i * md_step
        tvd = md * (state.geometry.tvd / state.geometry.md) if state.geometry.md > 0 else md
        frac = md / state.geometry.md if state.geometry.md > 0 else 0
        dens = state.fluid.density_ppg + frac * 0.3
        hydro = calculate_hydrostatic(dens, tvd)
        fric = state.annular_friction * frac
        pressure = hydro + fric + state.operating.sbp_setpoint * frac
        ecd = pressure / (0.052 * tvd) if tvd > 0 else 0
        rows.append({
            "MD": round(md, 1),
            "TVD": round(tvd, 1),
            "Formation_Temp": round(80 + tvd * 0.015, 1),
            "Annulus_Temp": round(state.fluid.temp_in + frac * (state.fluid.temp_out - state.fluid.temp_in), 1),
            "Pipe_Temp": round(state.fluid.temp_in + frac * 20, 1),
            "Annulus_Density": round(dens, 2),
            "Pipe_Density": round(state.fluid.density_ppg, 2),
            "Annulus_Friction": round(fric, 1),
            "Annulus_ECD": round(ecd, 2),
            "Annulus_Pressure": round(pressure, 1),
            "Pore_Pressure": round(tvd * 0.56, 1),
            "Fracture_Pressure": round(tvd * 0.92, 1),
            "PPG": round(0.56 * 19.25, 2),  # approx
        })
    return rows
'''

(ROOT / "engines" / "hydraulics_engine.py").write_text(engine_content, encoding="utf-8")
print("  ✓ engines/hydraulics_engine.py")

# ─────────────────────────────────────────────────────────────
# 4. الواجهة الرئيسية (Streamlit) – مطابقة لشكل Victus
# ─────────────────────────────────────────────────────────────
app_content = '''"""
ARHPP Main Application – Stage 1
واجهة رئيسية مطابقة لترتيب Victus (Profile Depth Data + Schematic + Controls)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import APP_NAME, APP_VERSION, APP_SUBTITLE, PRIMARY_COLOR
from engines.hydraulics_engine import (
    SimulationState, WellGeometry, FluidProperties, OperatingParams, BitParams,
    run_hydraulics, get_profile_depth_data
)

# ─────────────────────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS – Dark theme like Victus
st.markdown("""
<style>
    .stApp {
        background-color: #1a1d23;
        color: #e0e0e0;
    }
    .stSidebar {
        background-color: #12151a;
    }
    .metric-card {
        background: #252a33;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #333;
        text-align: center;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: #00d4aa;
    }
    .metric-label {
        font-size: 12px;
        color: #aaa;
    }
    div[data-testid="stMetricValue"] {
        color: #00d4aa;
    }
    .block-container {
        padding-top: 1rem;
    }
    h1, h2, h3 {
        color: #e0e0e0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────
if "state" not in st.session_state:
    st.session_state.state = SimulationState()
    st.session_state.state = run_hydraulics(st.session_state.state)

if "app_name" not in st.session_state:
    st.session_state.app_name = APP_NAME

# ─────────────────────────────────────────────────────────────
# Top Bar
# ─────────────────────────────────────────────────────────────
col_logo, col_title, col_status = st.columns([1, 4, 2])
with col_logo:
    st.markdown(f"### 🛢️")
with col_title:
    st.markdown(f"## {st.session_state.app_name}  <span style='font-size:14px;color:#888'>{APP_VERSION}</span>", unsafe_allow_html=True)
with col_status:
    mode = st.session_state.state.mode
    color = "#00d4aa" if mode == "Simulation" else "#ffaa00"
    st.markdown(f"<div style='text-align:right;padding-top:10px;'><span style='background:{color};color:black;padding:4px 12px;border-radius:4px;font-weight:bold'>{mode.upper()}</span></div>", unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# Sidebar – Navigation (matching Victus left menu)
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### {st.session_state.app_name}")
    st.caption(APP_SUBTITLE)

    nav = st.radio(
        "Navigation",
        [
            "Main Time Data",
            "Profile Depth Data",
            "MPD Gauges",
            "Surge & Swab",
            "Timeline / Feedback",
            "Performance",
            "Engineering",
            "Settings"
        ],
        index=1  # Profile Depth Data default like the screenshot
    )

    st.markdown("---")
    st.markdown("#### Quick Controls")
    new_mode = st.selectbox("System Mode", ["Offline", "Simulation", "Live"], index=0)
    st.session_state.state.mode = new_mode

    choke_mode = st.selectbox("Choke Mode", ["MANUAL", "AUTO", "CBHP"], index=1)
    st.session_state.state.choke_mode = choke_mode

    sbp = st.slider("SBP Setpoint (psi)", 0, 800, int(st.session_state.state.operating.sbp_setpoint), 10)
    st.session_state.state.operating.sbp_setpoint = float(sbp)

    flow = st.number_input("Flow In (gpm)", 0.0, 2000.0, st.session_state.state.operating.flow_in_gpm, 10.0)
    st.session_state.state.operating.flow_in_gpm = flow

    if st.button("🔄 Recalculate", use_container_width=True):
        st.session_state.state = run_hydraulics(st.session_state.state)
        st.rerun()

# ─────────────────────────────────────────────────────────────
# Main Content according to Navigation
# ─────────────────────────────────────────────────────────────
state = st.session_state.state

if nav == "Profile Depth Data":
    st.subheader("Profile Depth Data")

    # Top Gauges row
    g1, g2, g3, g4, g5, g6 = st.columns(6)
    g1.metric("BHP", f"{state.bhp:.0f} psi", f"Target {state.target_bhp:.0f}")
    g2.metric("ECD", f"{state.ecd:.2f} ppg", f"Target {state.target_ecd:.2f}")
    g3.metric("Model SPP", f"{state.model_spp:.0f} psi")
    g4.metric("SBP", f"{state.operating.sbp_setpoint:.0f} psi")
    g5.metric("Flow In", f"{state.operating.flow_in_gpm:.0f} gpm")
    g6.metric("Live Expected PP", f"{state.live_pp:.0f} psi", f"OB {state.overbalance:.0f}")

    st.markdown("")

    # Main area: Table + Schematic
    left, right = st.columns([3, 1.2])

    with left:
        profile = get_profile_depth_data(state, num_points=15)
        df = pd.DataFrame(profile)
        # Reorder columns to match Victus style
        cols_order = ["MD", "TVD", "Formation_Temp", "Annulus_Temp", "Pipe_Temp",
                      "Annulus_Density", "Pipe_Density", "Annulus_Friction",
                      "Annulus_ECD", "Annulus_Pressure", "Pore_Pressure", "Fracture_Pressure"]
        df = df[[c for c in cols_order if c in df.columns]]
        st.dataframe(
            df.style.format({
                "MD": "{:.0f}", "TVD": "{:.0f}",
                "Formation_Temp": "{:.1f}", "Annulus_Temp": "{:.1f}", "Pipe_Temp": "{:.1f}",
                "Annulus_Density": "{:.2f}", "Pipe_Density": "{:.2f}",
                "Annulus_Friction": "{:.1f}", "Annulus_ECD": "{:.2f}",
                "Annulus_Pressure": "{:.1f}", "Pore_Pressure": "{:.1f}", "Fracture_Pressure": "{:.1f}"
            }),
            use_container_width=True,
            height=420
        )

    with right:
        st.markdown("##### Well Schematic")
        # Simple schematic using plotly
        fig = go.Figure()
        # Casing
        fig.add_shape(type="rect", x0=0.3, x1=0.7, y0=0, y1=30, fillcolor="#555", line=dict(color="#888"))
        # Open hole
        fig.add_shape(type="rect", x0=0.35, x1=0.65, y0=30, y1=100, fillcolor="#333", line=dict(color="#00d4aa"))
        # Bit
        fig.add_shape(type="rect", x0=0.25, x1=0.75, y0=98, y1=100, fillcolor="#00d4aa", line=dict(width=0))
        fig.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="#1a1d23",
            plot_bgcolor="#1a1d23",
            xaxis=dict(visible=False, range=[0, 1]),
            yaxis=dict(visible=True, range=[100, 0], title="Depth %", color="#aaa", gridcolor="#333"),
            font=dict(color="#ccc")
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        **Bit Depth:** {state.geometry.bit_depth:.0f} ft  
        **TVD:** {state.geometry.tvd:.0f} ft  
        **Hole:** {state.geometry.hole_id} in  
        **Choke:** {state.operating.choke_position:.0f}%  
        **Mode:** {state.choke_mode}
        """)

elif nav == "MPD Gauges":
    st.subheader("MPD Gauges")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BHP", f"{state.bhp:.0f} psi")
    c2.metric("ECD", f"{state.ecd:.2f} ppg")
    c3.metric("SBP", f"{state.operating.sbp_setpoint:.0f} psi")
    c4.metric("Overbalance", f"{state.overbalance:.0f} psi")

    # Simple trend placeholder
    st.line_chart({
        "BHP": [state.bhp - 50, state.bhp - 20, state.bhp, state.bhp + 10, state.bhp],
        "ECD": [state.ecd - 0.1, state.ecd - 0.05, state.ecd, state.ecd + 0.02, state.ecd]
    })

elif nav == "Main Time Data":
    st.subheader("Main Time Data")
    st.info("Stage 1 – Real-time trends will be expanded in next stages. Currently showing calculated snapshot.")
    st.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    st.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    st.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")

elif nav == "Surge & Swab":
    st.subheader("Surge & Swab Calculator")
    st.warning("Full Surge/Swab engine will be added in Stage 2 (already designed in Excel v4).")
    vel = st.slider("Pipe Velocity (ft/min)", 10, 120, 60)
    st.write(f"Estimated Surge Pressure: ~{vel * 2.8:.0f} psi (placeholder)")

elif nav == "Settings":
    st.subheader("Application Settings")
    new_name = st.text_input("Application Name (appears in UI)", value=st.session_state.app_name)
    if st.button("Save Name"):
        st.session_state.app_name = new_name
        st.success(f"Name updated to: {new_name}")
        st.rerun()

    st.markdown("---")
    st.markdown("#### Well Geometry")
    state.geometry.md = st.number_input("MD (ft)", value=state.geometry.md)
    state.geometry.tvd = st.number_input("TVD (ft)", value=state.geometry.tvd)
    state.geometry.hole_id = st.number_input("Hole ID (in)", value=state.geometry.hole_id)
    state.fluid.density_ppg = st.number_input("Mud Density (ppg)", value=state.fluid.density_ppg)

    if st.button("Apply & Recalculate"):
        st.session_state.state = run_hydraulics(state)
        st.rerun()

else:
    st.subheader(nav)
    st.info(f"Module '{nav}' will be fully implemented in upcoming stages. Structure is ready.")

# Footer
st.markdown("---")
st.caption(f"{st.session_state.app_name} | Stage 1 | Physics engine based on ARHPP Excel Reference Simulator v4 | SPP is diagnostic only")
'''

(ROOT / "app.py").write_text(app_content, encoding="utf-8")
print("  ✓ app.py  (Main Streamlit application)")

# ─────────────────────────────────────────────────────────────
# 5. requirements.txt + README
# ─────────────────────────────────────────────────────────────
(ROOT / "requirements.txt").write_text("""streamlit>=1.31
plotly>=5.18
pandas>=2.0
numpy>=1.24
""", encoding="utf-8")
print("  ✓ requirements.txt")

readme = f'''# {APP_NAME if False else "ARHPP Digital Twin"} – Stage 1

## التشغيل السريع

```bash
cd ARHPP_App
pip install -r requirements.txt
streamlit run app.py
```

ثم افتح المتصفح على http://localhost:8501

## ما يشمله Stage 1
- هيكل المشروع كامل
- واجهة رئيسية بترتيب Victus (Sidebar + Profile Depth Data + Schematic)
- إمكانية تغيير اسم التطبيق من Settings
- محرك حسابات أولي مستند إلى Excel v4
- Choke Mode (Manual / Auto / CBHP)
- Gauges حية (BHP, ECD, SPP Model, Live PP)

## المراحل القادمة
ستُضاف أسفل هذا الملف في build_arhpp_full.py
'''
(ROOT / "README.md").write_text(readme, encoding="utf-8")
print("  ✓ README.md")

# ─────────────────────────────────────────────────────────────
# 6. __init__ files
# ─────────────────────────────────────────────────────────────
(ROOT / "core" / "__init__.py").write_text("", encoding="utf-8")
(ROOT / "engines" / "__init__.py").write_text("", encoding="utf-8")
(ROOT / "ui" / "__init__.py").write_text("", encoding="utf-8")
(ROOT / "config" / "__init__.py").write_text("", encoding="utf-8")

print()
print("=" * 60)
print("✅ Stage 1 completed successfully!")
print(f"Project created at: {ROOT.absolute()}")
print()
print("To run:")
print(f"  cd {ROOT}")
print("  pip install -r requirements.txt")
print("  streamlit run app.py")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# STAGE 2 – Enhanced Engine + Full Surge/Swab + Better UI Match
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ARHPP Full Application Builder – Stage 2")
print("Enhancing engine, Surge/Swab, Profile Depth Data, UI...")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Stage 2: Improved Hydraulics Engine
# ─────────────────────────────────────────────────────────────
engine_v2 = '''"""
ARHPP Hydraulics Engine – Stage 2
Full physical order from Excel v4:
Flow → Temp → Rheology → Geometry → Bit → Multi-fluid → Effective Flow → Friction → Pressure → Live PP
+ Complete Surge & Swab
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class WellGeometry:
    md: float = 12000.0
    tvd: float = 11200.0
    hole_id: float = 8.5
    pipe_od: float = 5.0
    pipe_id: float = 4.276
    casing_od: float = 9.625
    bit_depth: float = 12000.0
    shoe_depth: float = 9410.0

@dataclass
class FluidProperties:
    density_ppg: float = 10.5
    pv: float = 28.0
    yp: float = 18.0
    n: float = 0.72
    K: float = 0.45
    tau_y: float = 6.5
    temp_in: float = 120.0
    temp_out: float = 155.0
    ambient_temp: float = 95.0
    temp_gradient: float = 1.5   # °F/100ft

@dataclass
class OperatingParams:
    flow_in_gpm: float = 850.0
    flow_out_gpm: float = 845.0
    sbp_setpoint: float = 200.0
    choke_position: float = 42.0
    rpm: float = 120.0
    wob: float = 25.0
    rop: float = 45.0
    spp_measured: float = 2850.0
    pump_efficiency: float = 0.97

@dataclass
class BitParams:
    bit_type: str = "PDC"
    tfa: float = 0.85
    bit_size: float = 8.5
    nozzles: str = "16/16/16/16/14/14"

@dataclass
class SurgeSwabParams:
    pipe_velocity_ftmin: float = 60.0
    acceleration: float = 0.5
    open_end: bool = True
    stand_length: float = 93.0
    clinging_factor: float = 0.45

@dataclass
class SimulationState:
    geometry: WellGeometry = field(default_factory=WellGeometry)
    fluid: FluidProperties = field(default_factory=FluidProperties)
    operating: OperatingParams = field(default_factory=OperatingParams)
    bit: BitParams = field(default_factory=BitParams)
    surge: SurgeSwabParams = field(default_factory=SurgeSwabParams)
    mode: str = "Offline"
    choke_mode: str = "AUTO"
    target_bhp: float = 7500.0
    target_ecd: float = 11.20
    litho_gradient: float = 0.56
    # Results
    bhp: float = 0.0
    ecd: float = 0.0
    model_spp: float = 0.0
    annular_friction: float = 0.0
    pipe_friction: float = 0.0
    bit_pressure_drop: float = 0.0
    hydrostatic: float = 0.0
    live_pp: float = 0.0
    overbalance: float = 0.0
    u_tube_dp: float = 0.0
    effective_flow: float = 0.0
    q_loss: float = 0.0
    q_utube: float = 0.0
    max_surge_psi: float = 0.0
    max_swab_psi: float = 0.0
    esd_surge: float = 0.0
    esd_swab: float = 0.0
    corrected_density: float = 0.0

def _hydrostatic(density: float, tvd: float) -> float:
    return 0.052 * density * tvd

def _bit_dp(q: float, dens: float, tfa: float) -> float:
    if tfa <= 0:
        return 0.0
    return (q ** 2 * dens) / (12031.0 * tfa ** 2)

def _annular_velocity(q_gpm: float, hole_id: float, pipe_od: float) -> float:
    area = (math.pi / 4.0) * (hole_id**2 - pipe_od**2) / 144.0
    if area <= 0:
        return 0.0
    return (q_gpm * 0.133681) / area

def _friction_factor(re: float) -> float:
    if re < 2100:
        return 16.0 / max(re, 1.0)
    return 0.046 * (re ** -0.2)

def _annular_friction(q: float, dens: float, hole_id: float, pipe_od: float, length: float, n: float, K: float, rpm: float = 0) -> float:
    dh = hole_id - pipe_od
    if dh <= 0 or length <= 0:
        return 0.0
    v = _annular_velocity(q, hole_id, pipe_od)
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * dh / mu_app
    f = _friction_factor(re)
    # RPM correction (simple boost)
    rpm_factor = 1.0 + (rpm / 200.0) * 0.08
    dp = f * dens * v**2 * length / (25.8 * dh) * rpm_factor
    return max(dp, 0.0)

def _pipe_friction(q: float, dens: float, pipe_id: float, length: float, n: float, K: float) -> float:
    if pipe_id <= 0 or length <= 0:
        return 0.0
    area = (math.pi / 4.0) * (pipe_id ** 2) / 144.0
    v = (q * 0.133681) / area if area > 0 else 0
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * pipe_id / mu_app
    f = _friction_factor(re)
    dp = f * dens * v**2 * length / (25.8 * pipe_id)
    return max(dp, 0.0)

def _temp_corrected_density(base: float, temp_in: float, temp_out: float, tvd: float, gradient: float) -> float:
    avg_temp = (temp_in + temp_out) / 2.0
    downhole_temp = temp_in + (tvd / 100.0) * gradient
    # rough expansion
    factor = 1.0 - 0.0003 * (downhole_temp - 80)
    return base * factor

def calculate_surge_swab(state: SimulationState) -> SimulationState:
    """Full Surge & Swab – Stage 2"""
    s = state.surge
    g = state.geometry
    f = state.fluid
    v = s.pipe_velocity_ftmin / 60.0  # ft/s
    dh = g.hole_id - g.pipe_od
    if dh <= 0:
        state.max_surge_psi = 0
        state.max_swab_psi = 0
        return state

    # Clinging + closed/open factor
    cling = s.clinging_factor if s.open_end else 1.0
    # Simplified Bingham/Power-law surge
    mu = f.pv * 1.2 + f.yp * 0.5
    base = (mu * v * g.md) / (1000.0 * dh**2) * cling * 3.5
    accel_term = s.acceleration * f.density_ppg * g.md * 0.0015
    state.max_surge_psi = base + accel_term
    state.max_swab_psi = -(base * 0.9)
    state.esd_surge = state.ecd + (state.max_surge_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    state.esd_swab = state.ecd + (state.max_swab_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    return state

def run_hydraulics(state: SimulationState) -> SimulationState:
    """Main calculation – strict physical order from Excel v4"""
    g = state.geometry
    f = state.fluid
    o = state.operating
    b = state.bit

    # 1. Temperature corrected density
    state.corrected_density = _temp_corrected_density(
        f.density_ppg, f.temp_in, f.temp_out, g.tvd, f.temp_gradient
    )

    # 2. Flow balance + U-Tube approximation
    state.q_loss = max(0.0, o.flow_in_gpm - o.flow_out_gpm)
    # Simple U-Tube from density difference (string vs annulus)
    dens_ann = state.corrected_density + 0.15  # cuttings loading approx
    state.u_tube_dp = 0.052 * (dens_ann - state.corrected_density) * g.tvd * 0.15
    state.q_utube = max(0.0, state.u_tube_dp / 8.0)  # rough conversion
    state.effective_flow = o.flow_in_gpm + state.q_utube - state.q_loss

    # 3. Hydrostatic
    state.hydrostatic = _hydrostatic(state.corrected_density, g.tvd)

    # 4. Bit pressure drop
    state.bit_pressure_drop = _bit_dp(state.effective_flow, state.corrected_density, b.tfa)

    # 5. Friction (annular + pipe)
    state.annular_friction = _annular_friction(
        state.effective_flow, state.corrected_density, g.hole_id, g.pipe_od,
        g.md, f.n, f.K, o.rpm
    )
    state.pipe_friction = _pipe_friction(
        state.effective_flow, state.corrected_density, g.pipe_id, g.md, f.n, f.K
    )

    # 6. BHP & ECD
    state.bhp = state.hydrostatic + state.annular_friction + o.sbp_setpoint
    state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0

    # 7. Model SPP
    state.model_spp = state.pipe_friction + state.bit_pressure_drop + o.sbp_setpoint + state.annular_friction * 0.15

    # 8. Live PP (influenced by bit type)
    bit_factor = {"PDC": 1.0, "Diamond Impregnated": 1.05, "Tricone": 0.95}.get(b.bit_type, 1.0)
    rop_factor = 1.0 - (o.rop - 40) * 0.001 if o.rop > 0 else 1.0
    state.live_pp = g.tvd * state.litho_gradient * bit_factor * max(0.9, min(1.1, rop_factor))
    state.overbalance = state.bhp - state.live_pp

    # 9. Surge & Swab
    state = calculate_surge_swab(state)

    return state

def get_profile_depth_data(state: SimulationState, num_points: int = 16) -> List[Dict]:
    """Profile Depth Data – columns matching Victus screenshots"""
    rows = []
    md_step = state.geometry.md / max(num_points - 1, 1)
    for i in range(num_points):
        md = i * md_step
        tvd = md * (state.geometry.tvd / state.geometry.md) if state.geometry.md > 0 else md
        frac = md / state.geometry.md if state.geometry.md > 0 else 0.0
        dens_ann = state.corrected_density + frac * 0.25
        dens_pipe = state.corrected_density
        hydro = _hydrostatic(dens_ann, tvd)
        fric = state.annular_friction * frac
        pressure = hydro + fric + state.operating.sbp_setpoint * frac
        ecd = pressure / (0.052 * tvd) if tvd > 1 else 0.0
        form_temp = state.fluid.ambient_temp + (tvd / 100.0) * state.fluid.temp_gradient
        ann_temp = state.fluid.temp_in + frac * (state.fluid.temp_out - state.fluid.temp_in)
        pipe_temp = state.fluid.temp_in + frac * 18
        pp = tvd * state.litho_gradient
        fg = tvd * 0.92
        rows.append({
            "MD_ft": round(md, 0),
            "TVD_ft": round(tvd, 0),
            "Formation_Temp_F": round(form_temp, 1),
            "Annulus_Temp_F": round(ann_temp, 1),
            "Pipe_Temp_F": round(pipe_temp, 1),
            "Annulus_Density_ppg": round(dens_ann, 2),
            "Pipe_Density_ppg": round(dens_pipe, 2),
            "Annulus_Friction_psi": round(fric, 1),
            "Pipe_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.3), 1),
            "Annulus_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.5), 1),
            "Annulus_ECD_ppg": round(ecd, 2),
            "Annulus_Pressure_psi": round(pressure, 1),
            "Pore_Pressure_psi": round(pp, 1),
            "Fracture_Pressure_psi": round(fg, 1),
            "PPG": round(state.litho_gradient * 19.25, 2),
            "WBSG_ppg": round(0.0, 2),
            "WBS_psi": round(0.0, 1),
        })
    return rows
'''

(ROOT / "engines" / "hydraulics_engine.py").write_text(engine_v2, encoding="utf-8")
print("  ✓ engines/hydraulics_engine.py  (Stage 2 – full order + Surge/Swab)")

# ─────────────────────────────────────────────────────────────
# Stage 2: Improved Main App (closer to Victus screenshots)
# ─────────────────────────────────────────────────────────────
app_v2 = '''"""
ARHPP Main Application – Stage 2
Closer visual & functional match to Victus Profile Depth Data + controls
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import APP_NAME, APP_VERSION, APP_SUBTITLE, PRIMARY_COLOR
from engines.hydraulics_engine import (
    SimulationState, WellGeometry, FluidProperties, OperatingParams, BitParams,
    SurgeSwabParams, run_hydraulics, get_profile_depth_data
)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme CSS closer to Victus
st.markdown("""
<style>
    .stApp { background-color: #1a1d23; color: #d0d0d0; }
    section[data-testid="stSidebar"] { background-color: #12151a; }
    div[data-testid="stMetricValue"] { color: #00d4aa; font-size: 1.4rem; }
    div[data-testid="stMetricDelta"] { font-size: 0.8rem; }
    .block-container { padding-top: 0.8rem; padding-bottom: 0.5rem; }
    h1, h2, h3, h4 { color: #e8e8e8 !important; }
    .stDataFrame { font-size: 0.85rem; }
    div[data-testid="stHorizontalBlock"] > div { padding: 2px; }
</style>
""", unsafe_allow_html=True)

# Session
if "state" not in st.session_state:
    st.session_state.state = run_hydraulics(SimulationState())
if "app_name" not in st.session_state:
    st.session_state.app_name = APP_NAME

state = st.session_state.state

# ── Top Bar ──
c1, c2, c3, c4 = st.columns([0.6, 3.5, 1.5, 1.2])
with c1:
    st.markdown("### 🛢️")
with c2:
    st.markdown(f"## {st.session_state.app_name} &nbsp; <span style='font-size:13px;color:#888'>{APP_VERSION}</span>", unsafe_allow_html=True)
with c3:
    st.caption(f"Well: {state.geometry.bit_depth:.0f} ft MD | TVD {state.geometry.tvd:.0f} ft")
with c4:
    mode_color = {"Offline": "#ffaa00", "Simulation": "#00d4aa", "Live": "#00ff88"}.get(state.mode, "#ffaa00")
    st.markdown(f"<div style='text-align:right;padding-top:12px'><span style='background:{mode_color};color:#111;padding:5px 14px;border-radius:4px;font-weight:700;font-size:13px'>{state.mode.upper()}</span></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:4px 0 10px 0;border-color:#333'>", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown(f"**{st.session_state.app_name}**")
    st.caption(APP_SUBTITLE)
    nav = st.radio(
        "Modules",
        ["Profile Depth Data", "MPD Gauges", "Main Time Data",
         "Surge & Swab", "Choke Control", "Timeline", "Performance",
         "Engineering", "Settings"],
        index=0
    )
    st.markdown("---")
    st.markdown("**Quick Setpoints**")
    state.mode = st.selectbox("Mode", ["Offline", "Simulation", "Live"], index=["Offline", "Simulation", "Live"].index(state.mode))
    state.choke_mode = st.selectbox("Choke Mode", ["MANUAL", "AUTO", "CBHP"], index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode))
    state.operating.sbp_setpoint = st.slider("SBP (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    state.operating.flow_in_gpm = st.number_input("Flow In (gpm)", 0.0, 2000.0, float(state.operating.flow_in_gpm), 10.0)
    state.operating.flow_out_gpm = st.number_input("Flow Out (gpm)", 0.0, 2000.0, float(state.operating.flow_out_gpm), 5.0)
    state.operating.choke_position = st.slider("Choke %", 0, 100, int(state.operating.choke_position), 1)
    if st.button("⟳ Recalculate", use_container_width=True, type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.rerun()

# ── Content ──
if nav == "Profile Depth Data":
    # Gauges row
    gcols = st.columns(7)
    metrics = [
        ("BHP", f"{state.bhp:.0f}", "psi", f"Tgt {state.target_bhp:.0f}"),
        ("ECD", f"{state.ecd:.2f}", "ppg", f"Tgt {state.target_ecd:.2f}"),
        ("Model SPP", f"{state.model_spp:.0f}", "psi", None),
        ("SBP", f"{state.operating.sbp_setpoint:.0f}", "psi", None),
        ("Flow In", f"{state.operating.flow_in_gpm:.0f}", "gpm", None),
        ("Live PP", f"{state.live_pp:.0f}", "psi", f"OB {state.overbalance:.0f}"),
        ("Eff. Flow", f"{state.effective_flow:.0f}", "gpm", None),
    ]
    for col, (label, val, unit, delta) in zip(gcols, metrics):
        col.metric(label, f"{val} {unit}", delta)

    st.markdown("")
    left, right = st.columns([3.2, 1.1])

    with left:
        profile = get_profile_depth_data(state, 18)
        df = pd.DataFrame(profile)
        # Display with Victus-like column names
        display_df = df.rename(columns={
            "MD_ft": "MD", "TVD_ft": "TVD",
            "Formation_Temp_F": "Form.Temp", "Annulus_Temp_F": "Ann.Temp",
            "Pipe_Temp_F": "Pipe.Temp", "Annulus_Density_ppg": "Ann.Dens",
            "Pipe_Density_ppg": "Pipe.Dens", "Annulus_Friction_psi": "Ann.Fric",
            "Pipe_App_Visc_cP": "Pipe.Visc", "Annulus_App_Visc_cP": "Ann.Visc",
            "Annulus_ECD_ppg": "Ann.ECD", "Annulus_Pressure_psi": "Ann.Press",
            "Pore_Pressure_psi": "PP", "Fracture_Pressure_psi": "FG",
            "PPG": "PPG", "WBSG_ppg": "WBSG", "WBS_psi": "WBS"
        })
        st.dataframe(display_df, use_container_width=True, height=440)

    with right:
        st.markdown("**Well Schematic**")
        fig = go.Figure()
        # Surface casing
        fig.add_shape(type="rect", x0=0.25, x1=0.75, y0=0, y1=25, fillcolor="#4a5568", line=dict(color="#718096", width=1))
        # Intermediate
        fig.add_shape(type="rect", x0=0.30, x1=0.70, y0=25, y1=55, fillcolor="#2d3748", line=dict(color="#4a5568", width=1))
        # Open hole
        fig.add_shape(type="rect", x0=0.35, x1=0.65, y0=55, y1=98, fillcolor="#1a202c", line=dict(color="#00d4aa", width=2))
        # Bit
        fig.add_shape(type="rect", x0=0.28, x1=0.72, y0=97, y1=100, fillcolor="#00d4aa", line=dict(width=0))
        fig.add_annotation(x=0.5, y=12, text="Casing", showarrow=False, font=dict(size=10, color="#a0aec0"))
        fig.add_annotation(x=0.5, y=75, text="Open Hole", showarrow=False, font=dict(size=10, color="#00d4aa"))
        fig.update_layout(
            height=380, margin=dict(l=5, r=5, t=5, b=5),
            paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
            xaxis=dict(visible=False, range=[0, 1]),
            yaxis=dict(range=[100, 0], title="", color="#718096", gridcolor="#2d3748", tickfont=dict(size=9)),
            font=dict(color="#a0aec0")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"""
<small>
**Bit MD:** {state.geometry.bit_depth:.0f} ft<br>
**TVD:** {state.geometry.tvd:.0f} ft<br>
**Hole ID:** {state.geometry.hole_id} in<br>
**Choke:** {state.operating.choke_position:.0f}% ({state.choke_mode})<br>
**U-Tube ΔP:** {state.u_tube_dp:.0f} psi
</small>
""", unsafe_allow_html=True)

elif nav == "Surge & Swab":
    st.subheader("Surge & Swab Calculator")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("**Trip Parameters**")
        state.surge.pipe_velocity_ftmin = st.slider("Pipe Velocity (ft/min)", 5, 150, int(state.surge.pipe_velocity_ftmin))
        state.surge.acceleration = st.number_input("Acceleration (ft/s²)", 0.0, 3.0, float(state.surge.acceleration), 0.1)
        state.surge.open_end = st.checkbox("Open Ended", value=state.surge.open_end)
        state.surge.stand_length = st.number_input("Stand Length (ft)", 30.0, 120.0, float(state.surge.stand_length))
        state.surge.clinging_factor = st.slider("Clinging Factor", 0.1, 1.0, float(state.surge.clinging_factor), 0.05)
        if st.button("Calculate Surge/Swab", type="primary"):
            st.session_state.state = run_hydraulics(state)
            st.rerun()
    with sc2:
        st.markdown("**Results**")
        st.metric("Max Surge Pressure", f"{state.max_surge_psi:.0f} psi")
        st.metric("Max Swab Pressure", f"{state.max_swab_psi:.0f} psi")
        st.metric("ESD during Surge", f"{state.esd_surge:.2f} ppg")
        st.metric("ESD during Swab", f"{state.esd_swab:.2f} ppg")
        st.metric("BHP @ Surge", f"{state.bhp + state.max_surge_psi:.0f} psi")
        st.metric("BHP @ Swab", f"{state.bhp + state.max_swab_psi:.0f} psi")
    st.info("Surge/Swab uses the same rheology, geometry and temperature-corrected density as the main engine.")

elif nav == "Choke Control":
    st.subheader("Choke Control Panel")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        st.markdown("### Mode")
        new_mode = st.radio("Choke Mode", ["MANUAL", "AUTO", "CBHP"], index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode), horizontal=True)
        state.choke_mode = new_mode
    with cc2:
        st.markdown("### Setpoints")
        if state.choke_mode == "CBHP":
            state.target_bhp = st.number_input("Target BHP (psi)", 0.0, 15000.0, float(state.target_bhp), 10.0)
        elif state.choke_mode == "AUTO":
            state.target_ecd = st.number_input("Target ECD (ppg)", 8.0, 18.0, float(state.target_ecd), 0.05)
        state.operating.sbp_setpoint = st.slider("SBP Setpoint (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    with cc3:
        st.markdown("### Current")
        st.metric("Choke Position", f"{state.operating.choke_position:.0f} %")
        st.metric("Current SBP", f"{state.operating.sbp_setpoint:.0f} psi")
        st.metric("Current BHP", f"{state.bhp:.0f} psi")
        st.metric("Current ECD", f"{state.ecd:.2f} ppg")
    if st.button("Apply Setpoint & Recalculate", type="primary", use_container_width=True):
        # Simple auto logic
        if state.choke_mode == "CBHP" and state.bhp < state.target_bhp - 20:
            state.operating.sbp_setpoint = min(1000, state.operating.sbp_setpoint + 15)
        elif state.choke_mode == "CBHP" and state.bhp > state.target_bhp + 20:
            state.operating.sbp_setpoint = max(0, state.operating.sbp_setpoint - 15)
        st.session_state.state = run_hydraulics(state)
        st.rerun()

elif nav == "MPD Gauges":
    st.subheader("MPD Gauges")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("BHP", f"{state.bhp:.0f} psi", f"{state.bhp - state.target_bhp:+.0f}")
    g2.metric("ECD", f"{state.ecd:.2f} ppg", f"{state.ecd - state.target_ecd:+.2f}")
    g3.metric("SBP", f"{state.operating.sbp_setpoint:.0f} psi")
    g4.metric("Overbalance", f"{state.overbalance:.0f} psi")
    # Mini trends
    st.line_chart({
        "BHP": [state.bhp-40, state.bhp-15, state.bhp, state.bhp+8, state.bhp-5],
        "ECD*100": [(state.ecd-0.08)*100, (state.ecd-0.03)*100, state.ecd*100, (state.ecd+0.02)*100, state.ecd*100]
    })

elif nav == "Main Time Data":
    st.subheader("Main Time Data")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    m2.metric("Q Loss", f"{state.q_loss:.1f} gpm")
    m3.metric("Q U-Tube", f"{state.q_utube:.1f} gpm")
    m4.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    st.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    st.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    st.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")

elif nav == "Settings":
    st.subheader("Settings")
    new_name = st.text_input("Application Display Name", value=st.session_state.app_name)
    if st.button("Update Name"):
        st.session_state.app_name = new_name
        st.success(f"Name set to: {new_name}")
        st.rerun()
    st.markdown("---")
    st.markdown("**Well Geometry**")
    state.geometry.md = st.number_input("Total MD (ft)", value=float(state.geometry.md))
    state.geometry.tvd = st.number_input("TVD (ft)", value=float(state.geometry.tvd))
    state.geometry.hole_id = st.number_input("Hole ID (in)", value=float(state.geometry.hole_id))
    state.geometry.pipe_od = st.number_input("Pipe OD (in)", value=float(state.geometry.pipe_od))
    state.geometry.bit_depth = st.number_input("Bit Depth (ft)", value=float(state.geometry.bit_depth))
    st.markdown("**Fluid**")
    state.fluid.density_ppg = st.number_input("Mud Density (ppg)", value=float(state.fluid.density_ppg))
    state.fluid.temp_in = st.number_input("Mud Temp In (°F)", value=float(state.fluid.temp_in))
    state.fluid.temp_out = st.number_input("Mud Temp Out (°F)", value=float(state.fluid.temp_out))
    state.fluid.n = st.number_input("n (HB)", value=float(state.fluid.n), format="%.3f")
    state.fluid.K = st.number_input("K (HB)", value=float(state.fluid.K), format="%.3f")
    st.markdown("**Bit**")
    state.bit.bit_type = st.selectbox("Bit Type", ["PDC", "Diamond Impregnated", "Tricone"], index=0)
    state.bit.tfa = st.number_input("TFA (in²)", value=float(state.bit.tfa), format="%.3f")
    state.litho_gradient = st.number_input("Lithology PP Gradient (psi/ft)", value=float(state.litho_gradient), format="%.3f")
    if st.button("Apply All & Recalculate", type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.rerun()

else:
    st.subheader(nav)
    st.info(f"Module **{nav}** structure is ready. Full content will be added in later stages while keeping this code base.")

st.markdown("<hr style='border-color:#333'>", unsafe_allow_html=True)
st.caption(f"{st.session_state.app_name}  |  Stage 2  |  Engine follows Excel v4 physical order  |  SPP is diagnostic only  |  Live PP influenced by Bit Type + Lithology")
'''

(ROOT / "app.py").write_text(app_v2, encoding="utf-8")
print("  ✓ app.py  (Stage 2 – improved UI + Surge/Swab + Choke Control)")

# Update README
readme2 = '''# ARHPP Digital Twin – Stage 2

## التشغيل

```bash
cd ARHPP_App
pip install -r requirements.txt
streamlit run app.py
```

## ما تم إضافته في Stage 2
- محرك حسابات محسّن (ترتيب فيزيائي كامل من Excel v4)
- Temperature-corrected density
- Effective Flow = Qin + Qutube − Qloss
- Full Surge & Swab calculator
- Choke Control panel (Manual / Auto / CBHP) مع منطق بسيط للـ setpoint
- Profile Depth Data بأعمدة أقرب لـ Victus
- تحسين الألوان والتخطيط
- Live PP يتأثر بنوع الحفار + الليثولوجي

## المراحل القادمة
ستُضاف أسفل build_arhpp_full.py
'''
(ROOT / "README.md").write_text(readme2, encoding="utf-8")
print("  ✓ README.md updated")

print()
print("=" * 60)
print("✅ Stage 2 completed successfully!")
print("Re-run the application to see the improvements:")
print("  cd ARHPP_App")
print("  streamlit run app.py")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# STAGE 3 – Lithology Schematic + Timeline + Improved CBHP Auto
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ARHPP Full Application Builder – Stage 3")
print("Lithology layers + Timeline + CBHP Auto logic...")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Stage 3: Enhanced Engine (add lithology table + better CBHP helper)
# ─────────────────────────────────────────────────────────────
engine_v3 = '''"""
ARHPP Hydraulics Engine – Stage 3
+ Lithology table
+ Improved CBHP auto-adjust helper
+ Full physical order from Excel v4
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

# Default lithology column (Kuwait-style example – editable later)
DEFAULT_LITHOLOGY = [
    {"name": "Dammam",   "md_top": 0,     "md_bot": 800,   "color": "#c4a574", "pp_grad": 0.45, "fg_grad": 0.85},
    {"name": "Rus",      "md_top": 800,   "md_bot": 1400,  "color": "#e8d5b7", "pp_grad": 0.46, "fg_grad": 0.90},
    {"name": "Radhuma",  "md_top": 1400,  "md_bot": 2800,  "color": "#d4b896", "pp_grad": 0.47, "fg_grad": 0.88},
    {"name": "Tayarat",  "md_top": 2800,  "md_bot": 4200,  "color": "#8b7355", "pp_grad": 0.48, "fg_grad": 0.87},
    {"name": "Hartha",   "md_top": 4200,  "md_bot": 5500,  "color": "#a0896c", "pp_grad": 0.49, "fg_grad": 0.89},
    {"name": "Sadi",     "md_top": 5500,  "md_bot": 6200,  "color": "#6b5344", "pp_grad": 0.50, "fg_grad": 0.86},
    {"name": "Mutriba",  "md_top": 6200,  "md_bot": 7000,  "color": "#9c8b7a", "pp_grad": 0.51, "fg_grad": 0.90},
    {"name": "Mishrif",  "md_top": 7000,  "md_bot": 8200,  "color": "#b89b72", "pp_grad": 0.52, "fg_grad": 0.92},
    {"name": "Rumaila",  "md_top": 8200,  "md_bot": 9500,  "color": "#a67c52", "pp_grad": 0.53, "fg_grad": 0.93},
    {"name": "Ahmadi",   "md_top": 9500,  "md_bot": 10500, "color": "#7d6b5a", "pp_grad": 0.54, "fg_grad": 0.91},
    {"name": "Wara",     "md_top": 10500, "md_bot": 11200, "color": "#c2b280", "pp_grad": 0.55, "fg_grad": 0.90},
    {"name": "Burgan",   "md_top": 11200, "md_bot": 13000, "color": "#d2b48c", "pp_grad": 0.56, "fg_grad": 0.88},
]

@dataclass
class WellGeometry:
    md: float = 12000.0
    tvd: float = 11200.0
    hole_id: float = 8.5
    pipe_od: float = 5.0
    pipe_id: float = 4.276
    casing_od: float = 9.625
    bit_depth: float = 12000.0
    shoe_depth: float = 9410.0

@dataclass
class FluidProperties:
    density_ppg: float = 10.5
    pv: float = 28.0
    yp: float = 18.0
    n: float = 0.72
    K: float = 0.45
    tau_y: float = 6.5
    temp_in: float = 120.0
    temp_out: float = 155.0
    ambient_temp: float = 95.0
    temp_gradient: float = 1.5

@dataclass
class OperatingParams:
    flow_in_gpm: float = 850.0
    flow_out_gpm: float = 845.0
    sbp_setpoint: float = 200.0
    choke_position: float = 42.0
    rpm: float = 120.0
    wob: float = 25.0
    rop: float = 45.0
    spp_measured: float = 2850.0
    pump_efficiency: float = 0.97

@dataclass
class BitParams:
    bit_type: str = "PDC"
    tfa: float = 0.85
    bit_size: float = 8.5
    nozzles: str = "16/16/16/16/14/14"

@dataclass
class SurgeSwabParams:
    pipe_velocity_ftmin: float = 60.0
    acceleration: float = 0.5
    open_end: bool = True
    stand_length: float = 93.0
    clinging_factor: float = 0.45

@dataclass
class SimulationState:
    geometry: WellGeometry = field(default_factory=WellGeometry)
    fluid: FluidProperties = field(default_factory=FluidProperties)
    operating: OperatingParams = field(default_factory=OperatingParams)
    bit: BitParams = field(default_factory=BitParams)
    surge: SurgeSwabParams = field(default_factory=SurgeSwabParams)
    mode: str = "Offline"
    choke_mode: str = "AUTO"
    target_bhp: float = 7500.0
    target_ecd: float = 11.20
    litho_gradient: float = 0.56
    lithology: List[Dict] = field(default_factory=lambda: DEFAULT_LITHOLOGY.copy())
    timeline: List[Dict] = field(default_factory=list)
    # Results
    bhp: float = 0.0
    ecd: float = 0.0
    model_spp: float = 0.0
    annular_friction: float = 0.0
    pipe_friction: float = 0.0
    bit_pressure_drop: float = 0.0
    hydrostatic: float = 0.0
    live_pp: float = 0.0
    overbalance: float = 0.0
    u_tube_dp: float = 0.0
    effective_flow: float = 0.0
    q_loss: float = 0.0
    q_utube: float = 0.0
    max_surge_psi: float = 0.0
    max_swab_psi: float = 0.0
    esd_surge: float = 0.0
    esd_swab: float = 0.0
    corrected_density: float = 0.0
    current_formation: str = "Burgan"

def _hydrostatic(density: float, tvd: float) -> float:
    return 0.052 * density * tvd

def _bit_dp(q: float, dens: float, tfa: float) -> float:
    if tfa <= 0:
        return 0.0
    return (q ** 2 * dens) / (12031.0 * tfa ** 2)

def _annular_velocity(q_gpm: float, hole_id: float, pipe_od: float) -> float:
    area = (math.pi / 4.0) * (hole_id**2 - pipe_od**2) / 144.0
    if area <= 0:
        return 0.0
    return (q_gpm * 0.133681) / area

def _friction_factor(re: float) -> float:
    if re < 2100:
        return 16.0 / max(re, 1.0)
    return 0.046 * (re ** -0.2)

def _annular_friction(q: float, dens: float, hole_id: float, pipe_od: float, length: float, n: float, K: float, rpm: float = 0) -> float:
    dh = hole_id - pipe_od
    if dh <= 0 or length <= 0:
        return 0.0
    v = _annular_velocity(q, hole_id, pipe_od)
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * dh / mu_app
    f = _friction_factor(re)
    rpm_factor = 1.0 + (rpm / 200.0) * 0.08
    dp = f * dens * v**2 * length / (25.8 * dh) * rpm_factor
    return max(dp, 0.0)

def _pipe_friction(q: float, dens: float, pipe_id: float, length: float, n: float, K: float) -> float:
    if pipe_id <= 0 or length <= 0:
        return 0.0
    area = (math.pi / 4.0) * (pipe_id ** 2) / 144.0
    v = (q * 0.133681) / area if area > 0 else 0
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * pipe_id / mu_app
    f = _friction_factor(re)
    dp = f * dens * v**2 * length / (25.8 * pipe_id)
    return max(dp, 0.0)

def _temp_corrected_density(base: float, temp_in: float, temp_out: float, tvd: float, gradient: float) -> float:
    downhole_temp = temp_in + (tvd / 100.0) * gradient
    factor = 1.0 - 0.0003 * (downhole_temp - 80)
    return base * factor

def get_formation_at_depth(lithology: List[Dict], md: float) -> Dict:
    for layer in lithology:
        if layer["md_top"] <= md <= layer["md_bot"]:
            return layer
    return lithology[-1] if lithology else {"name": "Unknown", "pp_grad": 0.56, "fg_grad": 0.90, "color": "#888"}

def calculate_surge_swab(state: SimulationState) -> SimulationState:
    s = state.surge
    g = state.geometry
    f = state.fluid
    v = s.pipe_velocity_ftmin / 60.0
    dh = g.hole_id - g.pipe_od
    if dh <= 0:
        state.max_surge_psi = 0.0
        state.max_swab_psi = 0.0
        return state
    cling = s.clinging_factor if s.open_end else 1.0
    mu = f.pv * 1.2 + f.yp * 0.5
    base = (mu * v * g.md) / (1000.0 * dh**2) * cling * 3.5
    accel_term = s.acceleration * f.density_ppg * g.md * 0.0015
    state.max_surge_psi = base + accel_term
    state.max_swab_psi = -(base * 0.9)
    state.esd_surge = state.ecd + (state.max_surge_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    state.esd_swab = state.ecd + (state.max_swab_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    return state

def auto_adjust_sbp_for_cbhp(state: SimulationState) -> SimulationState:
    """Simple CBHP controller: adjust SBP to keep BHP near target"""
    if state.choke_mode != "CBHP":
        return state
    error = state.target_bhp - state.bhp
    # Proportional step (limited)
    step = max(-25.0, min(25.0, error * 0.15))
    state.operating.sbp_setpoint = max(0.0, min(1000.0, state.operating.sbp_setpoint + step))
    # Update choke position roughly
    state.operating.choke_position = max(5.0, min(95.0, 30.0 + state.operating.sbp_setpoint / 10.0))
    return state

def run_hydraulics(state: SimulationState) -> SimulationState:
    g = state.geometry
    f = state.fluid
    o = state.operating
    b = state.bit

    # Current formation
    form = get_formation_at_depth(state.lithology, g.bit_depth)
    state.current_formation = form["name"]
    state.litho_gradient = form.get("pp_grad", 0.56)

    # 1. Temperature corrected density
    state.corrected_density = _temp_corrected_density(
        f.density_ppg, f.temp_in, f.temp_out, g.tvd, f.temp_gradient
    )

    # 2. Flow balance + U-Tube
    state.q_loss = max(0.0, o.flow_in_gpm - o.flow_out_gpm)
    dens_ann = state.corrected_density + 0.15
    state.u_tube_dp = 0.052 * (dens_ann - state.corrected_density) * g.tvd * 0.15
    state.q_utube = max(0.0, state.u_tube_dp / 8.0)
    state.effective_flow = o.flow_in_gpm + state.q_utube - state.q_loss

    # 3. Hydrostatic
    state.hydrostatic = _hydrostatic(state.corrected_density, g.tvd)

    # 4. Bit ΔP
    state.bit_pressure_drop = _bit_dp(state.effective_flow, state.corrected_density, b.tfa)

    # 5. Friction
    state.annular_friction = _annular_friction(
        state.effective_flow, state.corrected_density, g.hole_id, g.pipe_od,
        g.md, f.n, f.K, o.rpm
    )
    state.pipe_friction = _pipe_friction(
        state.effective_flow, state.corrected_density, g.pipe_id, g.md, f.n, f.K
    )

    # 6. BHP & ECD
    state.bhp = state.hydrostatic + state.annular_friction + o.sbp_setpoint
    state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0

    # 7. Model SPP
    state.model_spp = state.pipe_friction + state.bit_pressure_drop + o.sbp_setpoint + state.annular_friction * 0.15

    # 8. Live PP
    bit_factor = {"PDC": 1.0, "Diamond Impregnated": 1.05, "Tricone": 0.95}.get(b.bit_type, 1.0)
    rop_factor = 1.0 - (o.rop - 40) * 0.001 if o.rop > 0 else 1.0
    state.live_pp = g.tvd * state.litho_gradient * bit_factor * max(0.9, min(1.1, rop_factor))
    state.overbalance = state.bhp - state.live_pp

    # 9. Surge/Swab
    state = calculate_surge_swab(state)

    # 10. CBHP auto adjust (if mode active)
    if state.choke_mode == "CBHP" and state.mode == "Simulation":
        state = auto_adjust_sbp_for_cbhp(state)
        # Recompute BHP after adjust
        state.bhp = state.hydrostatic + state.annular_friction + state.operating.sbp_setpoint
        state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
        state.overbalance = state.bhp - state.live_pp

    return state

def get_profile_depth_data(state: SimulationState, num_points: int = 16) -> List[Dict]:
    rows = []
    md_step = state.geometry.md / max(num_points - 1, 1)
    for i in range(num_points):
        md = i * md_step
        tvd = md * (state.geometry.tvd / state.geometry.md) if state.geometry.md > 0 else md
        frac = md / state.geometry.md if state.geometry.md > 0 else 0.0
        dens_ann = state.corrected_density + frac * 0.25
        dens_pipe = state.corrected_density
        hydro = _hydrostatic(dens_ann, tvd)
        fric = state.annular_friction * frac
        pressure = hydro + fric + state.operating.sbp_setpoint * frac
        ecd = pressure / (0.052 * tvd) if tvd > 1 else 0.0
        form_temp = state.fluid.ambient_temp + (tvd / 100.0) * state.fluid.temp_gradient
        ann_temp = state.fluid.temp_in + frac * (state.fluid.temp_out - state.fluid.temp_in)
        pipe_temp = state.fluid.temp_in + frac * 18
        form = get_formation_at_depth(state.lithology, md)
        pp = tvd * form.get("pp_grad", 0.56)
        fg = tvd * form.get("fg_grad", 0.90)
        rows.append({
            "MD_ft": round(md, 0),
            "TVD_ft": round(tvd, 0),
            "Formation": form["name"],
            "Formation_Temp_F": round(form_temp, 1),
            "Annulus_Temp_F": round(ann_temp, 1),
            "Pipe_Temp_F": round(pipe_temp, 1),
            "Annulus_Density_ppg": round(dens_ann, 2),
            "Pipe_Density_ppg": round(dens_pipe, 2),
            "Annulus_Friction_psi": round(fric, 1),
            "Pipe_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.3), 1),
            "Annulus_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.5), 1),
            "Annulus_ECD_ppg": round(ecd, 2),
            "Annulus_Pressure_psi": round(pressure, 1),
            "Pore_Pressure_psi": round(pp, 1),
            "Fracture_Pressure_psi": round(fg, 1),
            "PPG": round(form.get("pp_grad", 0.56) * 19.25, 2),
            "WBSG_ppg": 0.0,
            "WBS_psi": 0.0,
        })
    return rows

def add_timeline_event(state: SimulationState, event: str, details: str = "") -> SimulationState:
    from datetime import datetime
    state.timeline.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "event": event,
        "details": details
    })
    # keep last 50
    state.timeline = state.timeline[:50]
    return state
'''

(ROOT / "engines" / "hydraulics_engine.py").write_text(engine_v3, encoding="utf-8")
print("  ✓ engines/hydraulics_engine.py  (Stage 3 – lithology + CBHP auto)")

# ─────────────────────────────────────────────────────────────
# Stage 3: App with Lithology Schematic + Timeline
# ─────────────────────────────────────────────────────────────
app_v3 = '''"""
ARHPP Main Application – Stage 3
Lithology-colored Well Schematic + Timeline + CBHP Auto
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import APP_NAME, APP_VERSION, APP_SUBTITLE
from engines.hydraulics_engine import (
    SimulationState, run_hydraulics, get_profile_depth_data,
    add_timeline_event, get_formation_at_depth
)

st.set_page_config(page_title=APP_NAME, page_icon="🛢️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #1a1d23; color: #d0d0d0; }
    section[data-testid="stSidebar"] { background-color: #12151a; }
    div[data-testid="stMetricValue"] { color: #00d4aa; font-size: 1.35rem; }
    .block-container { padding-top: 0.6rem; padding-bottom: 0.4rem; }
    h1, h2, h3, h4 { color: #e8e8e8 !important; }
</style>
""", unsafe_allow_html=True)

if "state" not in st.session_state:
    st.session_state.state = run_hydraulics(SimulationState())
if "app_name" not in st.session_state:
    st.session_state.app_name = APP_NAME

state = st.session_state.state

# Top bar
c1, c2, c3, c4 = st.columns([0.5, 3.8, 1.4, 1.1])
with c1:
    st.markdown("### 🛢️")
with c2:
    st.markdown(f"## {st.session_state.app_name} <span style='font-size:12px;color:#888'>{APP_VERSION}</span>", unsafe_allow_html=True)
with c3:
    st.caption(f"Bit: {state.geometry.bit_depth:.0f} ft | {state.current_formation}")
with c4:
    mode_color = {"Offline": "#ffaa00", "Simulation": "#00d4aa", "Live": "#00ff88"}.get(state.mode, "#ffaa00")
    st.markdown(f"<div style='text-align:right;padding-top:10px'><span style='background:{mode_color};color:#111;padding:4px 12px;border-radius:4px;font-weight:700;font-size:12px'>{state.mode.upper()}</span></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:2px 0 8px 0;border-color:#333'>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"**{st.session_state.app_name}**")
    nav = st.radio("Modules", [
        "Profile Depth Data", "MPD Gauges", "Main Time Data",
        "Surge & Swab", "Choke Control", "Timeline", "Performance",
        "Engineering", "Settings"
    ], index=0)
    st.markdown("---")
    st.markdown("**Quick Setpoints**")
    state.mode = st.selectbox("Mode", ["Offline", "Simulation", "Live"],
                              index=["Offline", "Simulation", "Live"].index(state.mode))
    state.choke_mode = st.selectbox("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode))
    state.operating.sbp_setpoint = st.slider("SBP (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    state.operating.flow_in_gpm = st.number_input("Flow In (gpm)", 0.0, 2000.0, float(state.operating.flow_in_gpm), 10.0)
    state.operating.flow_out_gpm = st.number_input("Flow Out (gpm)", 0.0, 2000.0, float(state.operating.flow_out_gpm), 5.0)
    state.operating.choke_position = st.slider("Choke %", 0, 100, int(state.operating.choke_position), 1)
    if st.button("⟳ Recalculate", use_container_width=True, type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Recalculate", f"SBP={state.operating.sbp_setpoint:.0f}")
        st.rerun()

# Content
if nav == "Profile Depth Data":
    gcols = st.columns(7)
    metrics = [
        ("BHP", f"{state.bhp:.0f}", "psi", f"Tgt {state.target_bhp:.0f}"),
        ("ECD", f"{state.ecd:.2f}", "ppg", f"Tgt {state.target_ecd:.2f}"),
        ("Model SPP", f"{state.model_spp:.0f}", "psi", None),
        ("SBP", f"{state.operating.sbp_setpoint:.0f}", "psi", None),
        ("Flow In", f"{state.operating.flow_in_gpm:.0f}", "gpm", None),
        ("Live PP", f"{state.live_pp:.0f}", "psi", f"OB {state.overbalance:.0f}"),
        ("Eff. Flow", f"{state.effective_flow:.0f}", "gpm", None),
    ]
    for col, (label, val, unit, delta) in zip(gcols, metrics):
        col.metric(label, f"{val} {unit}", delta)

    left, right = st.columns([3.1, 1.2])
    with left:
        profile = get_profile_depth_data(state, 18)
        df = pd.DataFrame(profile)
        display_df = df.rename(columns={
            "MD_ft": "MD", "TVD_ft": "TVD", "Formation": "Form",
            "Formation_Temp_F": "Form.T", "Annulus_Temp_F": "Ann.T",
            "Pipe_Temp_F": "Pipe.T", "Annulus_Density_ppg": "Ann.Dens",
            "Pipe_Density_ppg": "Pipe.Dens", "Annulus_Friction_psi": "Ann.Fric",
            "Pipe_App_Visc_cP": "Pipe.Visc", "Annulus_App_Visc_cP": "Ann.Visc",
            "Annulus_ECD_ppg": "Ann.ECD", "Annulus_Pressure_psi": "Ann.P",
            "Pore_Pressure_psi": "PP", "Fracture_Pressure_psi": "FG",
            "PPG": "PPG", "WBSG_ppg": "WBSG", "WBS_psi": "WBS"
        })
        st.dataframe(display_df, use_container_width=True, height=430)

    with right:
        st.markdown("**Well Schematic + Lithology**")
        fig = go.Figure()
        total_md = max(state.geometry.md, 1)
        for layer in state.lithology:
            y0 = (layer["md_top"] / total_md) * 100
            y1 = (layer["md_bot"] / total_md) * 100
            if y0 > 100:
                continue
            y1 = min(y1, 100)
            fig.add_shape(type="rect", x0=0.15, x1=0.85, y0=y0, y1=y1,
                          fillcolor=layer["color"], opacity=0.85,
                          line=dict(color="#222", width=0.5))
            mid = (y0 + y1) / 2
            if y1 - y0 > 4:
                fig.add_annotation(x=0.5, y=mid, text=layer["name"], showarrow=False,
                                   font=dict(size=9, color="#111"), opacity=0.9)
        # Bit marker
        bit_y = (state.geometry.bit_depth / total_md) * 100
        fig.add_shape(type="rect", x0=0.05, x1=0.95, y0=bit_y-1.2, y1=bit_y+1.2,
                      fillcolor="#00d4aa", line=dict(width=0))
        fig.update_layout(
            height=400, margin=dict(l=5, r=5, t=5, b=5),
            paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
            xaxis=dict(visible=False, range=[0, 1]),
            yaxis=dict(range=[100, 0], title="", color="#718096",
                       gridcolor="#2d3748", tickfont=dict(size=9)),
            font=dict(color="#a0aec0")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"""
<small>
**Formation:** {state.current_formation}<br>
**Bit MD:** {state.geometry.bit_depth:.0f} ft<br>
**TVD:** {state.geometry.tvd:.0f} ft<br>
**Choke:** {state.operating.choke_position:.0f}% ({state.choke_mode})<br>
**U-Tube ΔP:** {state.u_tube_dp:.0f} psi
</small>
""", unsafe_allow_html=True)

elif nav == "Timeline":
    st.subheader("Timeline / Feedback")
    ec1, ec2 = st.columns([3, 1])
    with ec1:
        new_event = st.text_input("Add event comment", placeholder="e.g. Connection, Pump up, ...")
    with ec2:
        st.write("")
        st.write("")
        if st.button("Add to Timeline", use_container_width=True):
            if new_event.strip():
                st.session_state.state = add_timeline_event(state, new_event.strip())
                st.rerun()
    if state.timeline:
        tdf = pd.DataFrame(state.timeline)
        st.dataframe(tdf, use_container_width=True, height=400)
    else:
        st.info("No events yet. Use Recalculate or add a comment above.")

elif nav == "Surge & Swab":
    st.subheader("Surge & Swab Calculator")
    sc1, sc2 = st.columns(2)
    with sc1:
        state.surge.pipe_velocity_ftmin = st.slider("Pipe Velocity (ft/min)", 5, 150, int(state.surge.pipe_velocity_ftmin))
        state.surge.acceleration = st.number_input("Acceleration (ft/s²)", 0.0, 3.0, float(state.surge.acceleration), 0.1)
        state.surge.open_end = st.checkbox("Open Ended", value=state.surge.open_end)
        state.surge.clinging_factor = st.slider("Clinging Factor", 0.1, 1.0, float(state.surge.clinging_factor), 0.05)
        if st.button("Calculate Surge/Swab", type="primary"):
            st.session_state.state = run_hydraulics(state)
            st.session_state.state = add_timeline_event(st.session_state.state, "Surge/Swab Calc",
                                                       f"Vel={state.surge.pipe_velocity_ftmin}")
            st.rerun()
    with sc2:
        st.metric("Max Surge", f"{state.max_surge_psi:.0f} psi")
        st.metric("Max Swab", f"{state.max_swab_psi:.0f} psi")
        st.metric("ESD Surge", f"{state.esd_surge:.2f} ppg")
        st.metric("ESD Swab", f"{state.esd_swab:.2f} ppg")
        st.metric("BHP @ Surge", f"{state.bhp + state.max_surge_psi:.0f} psi")
        st.metric("BHP @ Swab", f"{state.bhp + state.max_swab_psi:.0f} psi")

elif nav == "Choke Control":
    st.subheader("Choke Control Panel")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        new_mode = st.radio("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                            index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode), horizontal=True)
        state.choke_mode = new_mode
    with cc2:
        if state.choke_mode == "CBHP":
            state.target_bhp = st.number_input("Target BHP (psi)", 0.0, 15000.0, float(state.target_bhp), 10.0)
        elif state.choke_mode == "AUTO":
            state.target_ecd = st.number_input("Target ECD (ppg)", 8.0, 18.0, float(state.target_ecd), 0.05)
        state.operating.sbp_setpoint = st.slider("SBP Setpoint (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    with cc3:
        st.metric("Choke Position", f"{state.operating.choke_position:.0f} %")
        st.metric("Current SBP", f"{state.operating.sbp_setpoint:.0f} psi")
        st.metric("Current BHP", f"{state.bhp:.0f} psi")
        st.metric("Current ECD", f"{state.ecd:.2f} ppg")
    if st.button("Apply Setpoint & Recalculate", type="primary", use_container_width=True):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Choke Apply",
                                                   f"Mode={state.choke_mode}, SBP={state.operating.sbp_setpoint:.0f}")
        st.rerun()
    if state.choke_mode == "CBHP":
        st.success("CBHP Auto is active in Simulation mode: SBP will adjust automatically to hold Target BHP.")

elif nav == "MPD Gauges":
    st.subheader("MPD Gauges")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("BHP", f"{state.bhp:.0f} psi", f"{state.bhp - state.target_bhp:+.0f}")
    g2.metric("ECD", f"{state.ecd:.2f} ppg", f"{state.ecd - state.target_ecd:+.2f}")
    g3.metric("SBP", f"{state.operating.sbp_setpoint:.0f} psi")
    g4.metric("Overbalance", f"{state.overbalance:.0f} psi")
    st.line_chart({
        "BHP": [state.bhp-40, state.bhp-15, state.bhp, state.bhp+8, state.bhp-5],
        "ECD x100": [(state.ecd-0.08)*100, (state.ecd-0.03)*100, state.ecd*100, (state.ecd+0.02)*100, state.ecd*100]
    })

elif nav == "Main Time Data":
    st.subheader("Main Time Data")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    m2.metric("Q Loss", f"{state.q_loss:.1f} gpm")
    m3.metric("Q U-Tube", f"{state.q_utube:.1f} gpm")
    m4.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    st.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    st.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    st.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    st.metric("Current Formation", state.current_formation)

elif nav == "Settings":
    st.subheader("Settings")
    new_name = st.text_input("Application Display Name", value=st.session_state.app_name)
    if st.button("Update Name"):
        st.session_state.app_name = new_name
        st.success(f"Name set to: {new_name}")
        st.rerun()
    st.markdown("---")
    st.markdown("**Well Geometry**")
    state.geometry.md = st.number_input("Total MD (ft)", value=float(state.geometry.md))
    state.geometry.tvd = st.number_input("TVD (ft)", value=float(state.geometry.tvd))
    state.geometry.hole_id = st.number_input("Hole ID (in)", value=float(state.geometry.hole_id))
    state.geometry.pipe_od = st.number_input("Pipe OD (in)", value=float(state.geometry.pipe_od))
    state.geometry.bit_depth = st.number_input("Bit Depth (ft)", value=float(state.geometry.bit_depth))
    st.markdown("**Fluid**")
    state.fluid.density_ppg = st.number_input("Mud Density (ppg)", value=float(state.fluid.density_ppg))
    state.fluid.temp_in = st.number_input("Mud Temp In (°F)", value=float(state.fluid.temp_in))
    state.fluid.temp_out = st.number_input("Mud Temp Out (°F)", value=float(state.fluid.temp_out))
    state.fluid.n = st.number_input("n (HB)", value=float(state.fluid.n), format="%.3f")
    state.fluid.K = st.number_input("K (HB)", value=float(state.fluid.K), format="%.3f")
    st.markdown("**Bit**")
    state.bit.bit_type = st.selectbox("Bit Type", ["PDC", "Diamond Impregnated", "Tricone"])
    state.bit.tfa = st.number_input("TFA (in²)", value=float(state.bit.tfa), format="%.3f")
    if st.button("Apply All & Recalculate", type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Settings Applied")
        st.rerun()

else:
    st.subheader(nav)
    st.info(f"Module **{nav}** structure ready. Content expands in later stages.")

st.markdown("<hr style='border-color:#333'>", unsafe_allow_html=True)
st.caption(f"{st.session_state.app_name} | Stage 3 | Lithology-aware | CBHP Auto | Excel v4 physics | SPP diagnostic only")
'''

(ROOT / "app.py").write_text(app_v3, encoding="utf-8")
print("  ✓ app.py  (Stage 3 – lithology schematic + Timeline + CBHP)")

readme3 = '''# ARHPP Digital Twin – Stage 3

## التشغيل
```bash
cd ARHPP_App
pip install -r requirements.txt
streamlit run app.py
```

## ما أُضيف في Stage 3
- Well Schematic ملون حسب الليثولوجي (Dammam → Burgan)
- تحديد الـ Formation الحالية تلقائياً حسب عمق الحفار
- Live PP يأخذ تدرج الطبقة الحالية
- Timeline / Feedback مع إمكانية إضافة أحداث
- منطق CBHP Auto (يعدل SBP للحفاظ على Target BHP في وضع Simulation)
- تسجيل الأحداث تلقائياً عند Recalculate / Choke Apply / Surge

## الملف المتراكم
build_arhpp_full.py يحتوي الآن على المراحل 1 + 2 + 3
'''
(ROOT / "README.md").write_text(readme3, encoding="utf-8")
print("  ✓ README.md updated")

print()
print("=" * 60)
print("✅ Stage 3 completed successfully!")
print("  cd ARHPP_App && streamlit run app.py")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# STAGE 4 – Performance + Engineering + Refinements
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ARHPP Full Application Builder – Stage 4")
print("Performance charts + Engineering page + refinements...")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Stage 4 Engine: add activity tracking helpers
# ─────────────────────────────────────────────────────────────
engine_v4 = '''"""
ARHPP Hydraulics Engine – Stage 4
+ Activity / Performance tracking helpers
+ Lithology + CBHP Auto + full Excel v4 order
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import math

DEFAULT_LITHOLOGY = [
    {"name": "Dammam",   "md_top": 0,     "md_bot": 800,   "color": "#c4a574", "pp_grad": 0.45, "fg_grad": 0.85},
    {"name": "Rus",      "md_top": 800,   "md_bot": 1400,  "color": "#e8d5b7", "pp_grad": 0.46, "fg_grad": 0.90},
    {"name": "Radhuma",  "md_top": 1400,  "md_bot": 2800,  "color": "#d4b896", "pp_grad": 0.47, "fg_grad": 0.88},
    {"name": "Tayarat",  "md_top": 2800,  "md_bot": 4200,  "color": "#8b7355", "pp_grad": 0.48, "fg_grad": 0.87},
    {"name": "Hartha",   "md_top": 4200,  "md_bot": 5500,  "color": "#a0896c", "pp_grad": 0.49, "fg_grad": 0.89},
    {"name": "Sadi",     "md_top": 5500,  "md_bot": 6200,  "color": "#6b5344", "pp_grad": 0.50, "fg_grad": 0.86},
    {"name": "Mutriba",  "md_top": 6200,  "md_bot": 7000,  "color": "#9c8b7a", "pp_grad": 0.51, "fg_grad": 0.90},
    {"name": "Mishrif",  "md_top": 7000,  "md_bot": 8200,  "color": "#b89b72", "pp_grad": 0.52, "fg_grad": 0.92},
    {"name": "Rumaila",  "md_top": 8200,  "md_bot": 9500,  "color": "#a67c52", "pp_grad": 0.53, "fg_grad": 0.93},
    {"name": "Ahmadi",   "md_top": 9500,  "md_bot": 10500, "color": "#7d6b5a", "pp_grad": 0.54, "fg_grad": 0.91},
    {"name": "Wara",     "md_top": 10500, "md_bot": 11200, "color": "#c2b280", "pp_grad": 0.55, "fg_grad": 0.90},
    {"name": "Burgan",   "md_top": 11200, "md_bot": 13000, "color": "#d2b48c", "pp_grad": 0.56, "fg_grad": 0.88},
]

@dataclass
class WellGeometry:
    md: float = 12000.0
    tvd: float = 11200.0
    hole_id: float = 8.5
    pipe_od: float = 5.0
    pipe_id: float = 4.276
    casing_od: float = 9.625
    bit_depth: float = 12000.0
    shoe_depth: float = 9410.0

@dataclass
class FluidProperties:
    density_ppg: float = 10.5
    pv: float = 28.0
    yp: float = 18.0
    n: float = 0.72
    K: float = 0.45
    tau_y: float = 6.5
    temp_in: float = 120.0
    temp_out: float = 155.0
    ambient_temp: float = 95.0
    temp_gradient: float = 1.5

@dataclass
class OperatingParams:
    flow_in_gpm: float = 850.0
    flow_out_gpm: float = 845.0
    sbp_setpoint: float = 200.0
    choke_position: float = 42.0
    rpm: float = 120.0
    wob: float = 25.0
    rop: float = 45.0
    spp_measured: float = 2850.0
    pump_efficiency: float = 0.97

@dataclass
class BitParams:
    bit_type: str = "PDC"
    tfa: float = 0.85
    bit_size: float = 8.5
    nozzles: str = "16/16/16/16/14/14"

@dataclass
class SurgeSwabParams:
    pipe_velocity_ftmin: float = 60.0
    acceleration: float = 0.5
    open_end: bool = True
    stand_length: float = 93.0
    clinging_factor: float = 0.45

@dataclass
class SimulationState:
    geometry: WellGeometry = field(default_factory=WellGeometry)
    fluid: FluidProperties = field(default_factory=FluidProperties)
    operating: OperatingParams = field(default_factory=OperatingParams)
    bit: BitParams = field(default_factory=BitParams)
    surge: SurgeSwabParams = field(default_factory=SurgeSwabParams)
    mode: str = "Offline"
    choke_mode: str = "AUTO"
    target_bhp: float = 7500.0
    target_ecd: float = 11.20
    litho_gradient: float = 0.56
    lithology: List[Dict] = field(default_factory=lambda: DEFAULT_LITHOLOGY.copy())
    timeline: List[Dict] = field(default_factory=list)
    activity_log: List[Dict] = field(default_factory=list)  # for Performance
    # Results
    bhp: float = 0.0
    ecd: float = 0.0
    model_spp: float = 0.0
    annular_friction: float = 0.0
    pipe_friction: float = 0.0
    bit_pressure_drop: float = 0.0
    hydrostatic: float = 0.0
    live_pp: float = 0.0
    overbalance: float = 0.0
    u_tube_dp: float = 0.0
    effective_flow: float = 0.0
    q_loss: float = 0.0
    q_utube: float = 0.0
    max_surge_psi: float = 0.0
    max_swab_psi: float = 0.0
    esd_surge: float = 0.0
    esd_swab: float = 0.0
    corrected_density: float = 0.0
    current_formation: str = "Burgan"

def _hydrostatic(density: float, tvd: float) -> float:
    return 0.052 * density * tvd

def _bit_dp(q: float, dens: float, tfa: float) -> float:
    if tfa <= 0:
        return 0.0
    return (q ** 2 * dens) / (12031.0 * tfa ** 2)

def _annular_velocity(q_gpm: float, hole_id: float, pipe_od: float) -> float:
    area = (math.pi / 4.0) * (hole_id**2 - pipe_od**2) / 144.0
    if area <= 0:
        return 0.0
    return (q_gpm * 0.133681) / area

def _friction_factor(re: float) -> float:
    if re < 2100:
        return 16.0 / max(re, 1.0)
    return 0.046 * (re ** -0.2)

def _annular_friction(q, dens, hole_id, pipe_od, length, n, K, rpm=0):
    dh = hole_id - pipe_od
    if dh <= 0 or length <= 0:
        return 0.0
    v = _annular_velocity(q, hole_id, pipe_od)
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * dh / mu_app
    f = _friction_factor(re)
    rpm_factor = 1.0 + (rpm / 200.0) * 0.08
    return max(f * dens * v**2 * length / (25.8 * dh) * rpm_factor, 0.0)

def _pipe_friction(q, dens, pipe_id, length, n, K):
    if pipe_id <= 0 or length <= 0:
        return 0.0
    area = (math.pi / 4.0) * (pipe_id ** 2) / 144.0
    v = (q * 0.133681) / area if area > 0 else 0
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * pipe_id / mu_app
    f = _friction_factor(re)
    return max(f * dens * v**2 * length / (25.8 * pipe_id), 0.0)

def _temp_corrected_density(base, temp_in, temp_out, tvd, gradient):
    downhole_temp = temp_in + (tvd / 100.0) * gradient
    return base * (1.0 - 0.0003 * (downhole_temp - 80))

def get_formation_at_depth(lithology, md):
    for layer in lithology:
        if layer["md_top"] <= md <= layer["md_bot"]:
            return layer
    return lithology[-1] if lithology else {"name": "Unknown", "pp_grad": 0.56, "fg_grad": 0.90, "color": "#888"}

def calculate_surge_swab(state):
    s, g, f = state.surge, state.geometry, state.fluid
    v = s.pipe_velocity_ftmin / 60.0
    dh = g.hole_id - g.pipe_od
    if dh <= 0:
        state.max_surge_psi = state.max_swab_psi = 0.0
        return state
    cling = s.clinging_factor if s.open_end else 1.0
    mu = f.pv * 1.2 + f.yp * 0.5
    base = (mu * v * g.md) / (1000.0 * dh**2) * cling * 3.5
    accel = s.acceleration * f.density_ppg * g.md * 0.0015
    state.max_surge_psi = base + accel
    state.max_swab_psi = -(base * 0.9)
    state.esd_surge = state.ecd + (state.max_surge_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    state.esd_swab = state.ecd + (state.max_swab_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    return state

def auto_adjust_sbp_for_cbhp(state):
    if state.choke_mode != "CBHP":
        return state
    error = state.target_bhp - state.bhp
    step = max(-30.0, min(30.0, error * 0.18))
    state.operating.sbp_setpoint = max(0.0, min(1000.0, state.operating.sbp_setpoint + step))
    state.operating.choke_position = max(5.0, min(95.0, 28.0 + state.operating.sbp_setpoint / 9.5))
    return state

def run_hydraulics(state):
    g, f, o, b = state.geometry, state.fluid, state.operating, state.bit
    form = get_formation_at_depth(state.lithology, g.bit_depth)
    state.current_formation = form["name"]
    state.litho_gradient = form.get("pp_grad", 0.56)

    state.corrected_density = _temp_corrected_density(f.density_ppg, f.temp_in, f.temp_out, g.tvd, f.temp_gradient)
    state.q_loss = max(0.0, o.flow_in_gpm - o.flow_out_gpm)
    dens_ann = state.corrected_density + 0.15
    state.u_tube_dp = 0.052 * (dens_ann - state.corrected_density) * g.tvd * 0.15
    state.q_utube = max(0.0, state.u_tube_dp / 8.0)
    state.effective_flow = o.flow_in_gpm + state.q_utube - state.q_loss

    state.hydrostatic = _hydrostatic(state.corrected_density, g.tvd)
    state.bit_pressure_drop = _bit_dp(state.effective_flow, state.corrected_density, b.tfa)
    state.annular_friction = _annular_friction(state.effective_flow, state.corrected_density, g.hole_id, g.pipe_od, g.md, f.n, f.K, o.rpm)
    state.pipe_friction = _pipe_friction(state.effective_flow, state.corrected_density, g.pipe_id, g.md, f.n, f.K)

    state.bhp = state.hydrostatic + state.annular_friction + o.sbp_setpoint
    state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
    state.model_spp = state.pipe_friction + state.bit_pressure_drop + o.sbp_setpoint + state.annular_friction * 0.15

    bit_factor = {"PDC": 1.0, "Diamond Impregnated": 1.05, "Tricone": 0.95}.get(b.bit_type, 1.0)
    rop_factor = 1.0 - (o.rop - 40) * 0.001 if o.rop > 0 else 1.0
    state.live_pp = g.tvd * state.litho_gradient * bit_factor * max(0.9, min(1.1, rop_factor))
    state.overbalance = state.bhp - state.live_pp

    state = calculate_surge_swab(state)

    if state.choke_mode == "CBHP" and state.mode == "Simulation":
        state = auto_adjust_sbp_for_cbhp(state)
        state.bhp = state.hydrostatic + state.annular_friction + state.operating.sbp_setpoint
        state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
        state.overbalance = state.bhp - state.live_pp

    return state

def get_profile_depth_data(state, num_points=16):
    rows = []
    md_step = state.geometry.md / max(num_points - 1, 1)
    for i in range(num_points):
        md = i * md_step
        tvd = md * (state.geometry.tvd / state.geometry.md) if state.geometry.md > 0 else md
        frac = md / state.geometry.md if state.geometry.md > 0 else 0.0
        dens_ann = state.corrected_density + frac * 0.25
        hydro = _hydrostatic(dens_ann, tvd)
        fric = state.annular_friction * frac
        pressure = hydro + fric + state.operating.sbp_setpoint * frac
        ecd = pressure / (0.052 * tvd) if tvd > 1 else 0.0
        form = get_formation_at_depth(state.lithology, md)
        form_temp = state.fluid.ambient_temp + (tvd / 100.0) * state.fluid.temp_gradient
        ann_temp = state.fluid.temp_in + frac * (state.fluid.temp_out - state.fluid.temp_in)
        rows.append({
            "MD_ft": round(md, 0),
            "TVD_ft": round(tvd, 0),
            "Formation": form["name"],
            "Formation_Temp_F": round(form_temp, 1),
            "Annulus_Temp_F": round(ann_temp, 1),
            "Pipe_Temp_F": round(state.fluid.temp_in + frac * 18, 1),
            "Annulus_Density_ppg": round(dens_ann, 2),
            "Pipe_Density_ppg": round(state.corrected_density, 2),
            "Annulus_Friction_psi": round(fric, 1),
            "Pipe_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.3), 1),
            "Annulus_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.5), 1),
            "Annulus_ECD_ppg": round(ecd, 2),
            "Annulus_Pressure_psi": round(pressure, 1),
            "Pore_Pressure_psi": round(tvd * form.get("pp_grad", 0.56), 1),
            "Fracture_Pressure_psi": round(tvd * form.get("fg_grad", 0.90), 1),
            "PPG": round(form.get("pp_grad", 0.56) * 19.25, 2),
            "WBSG_ppg": 0.0,
            "WBS_psi": 0.0,
        })
    return rows

def add_timeline_event(state, event, details=""):
    state.timeline.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "event": event,
        "details": details
    })
    state.timeline = state.timeline[:50]
    return state

def log_activity(state, activity: str, duration_min: float = 1.0):
    """Record activity for Performance pie chart"""
    state.activity_log.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "activity": activity,
        "duration_min": duration_min
    })
    state.activity_log = state.activity_log[-200:]
    return state

def get_activity_summary(state) -> Dict[str, float]:
    """Aggregate minutes per activity type"""
    summary = {}
    for a in state.activity_log:
        key = a["activity"]
        summary[key] = summary.get(key, 0.0) + a.get("duration_min", 1.0)
    if not summary:
        # default demo distribution
        summary = {"Drilling": 42, "Connection": 18, "Circulating": 15, "Trip": 12, "Offline": 8, "Other": 5}
    return summary
'''

(ROOT / "engines" / "hydraulics_engine.py").write_text(engine_v4, encoding="utf-8")
print("  ✓ engines/hydraulics_engine.py  (Stage 4)")

# ─────────────────────────────────────────────────────────────
# Stage 4 App
# ─────────────────────────────────────────────────────────────
app_v4 = '''"""
ARHPP Main Application – Stage 4
Performance + Engineering + previous features
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import APP_NAME, APP_VERSION, APP_SUBTITLE
from engines.hydraulics_engine import (
    SimulationState, run_hydraulics, get_profile_depth_data,
    add_timeline_event, log_activity, get_activity_summary, get_formation_at_depth
)

st.set_page_config(page_title=APP_NAME, page_icon="🛢️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #1a1d23; color: #d0d0d0; }
    section[data-testid="stSidebar"] { background-color: #12151a; }
    div[data-testid="stMetricValue"] { color: #00d4aa; font-size: 1.3rem; }
    .block-container { padding-top: 0.5rem; padding-bottom: 0.3rem; }
    h1, h2, h3, h4 { color: #e8e8e8 !important; }
</style>
""", unsafe_allow_html=True)

if "state" not in st.session_state:
    st.session_state.state = run_hydraulics(SimulationState())
if "app_name" not in st.session_state:
    st.session_state.app_name = APP_NAME

state = st.session_state.state

# Top bar
c1, c2, c3, c4 = st.columns([0.5, 3.8, 1.4, 1.1])
with c1:
    st.markdown("### 🛢️")
with c2:
    st.markdown(f"## {st.session_state.app_name} <span style='font-size:12px;color:#888'>{APP_VERSION}</span>", unsafe_allow_html=True)
with c3:
    st.caption(f"Bit: {state.geometry.bit_depth:.0f} ft | {state.current_formation}")
with c4:
    mode_color = {"Offline": "#ffaa00", "Simulation": "#00d4aa", "Live": "#00ff88"}.get(state.mode, "#ffaa00")
    st.markdown(f"<div style='text-align:right;padding-top:10px'><span style='background:{mode_color};color:#111;padding:4px 12px;border-radius:4px;font-weight:700;font-size:12px'>{state.mode.upper()}</span></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:2px 0 8px 0;border-color:#333'>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"**{st.session_state.app_name}**")
    nav = st.radio("Modules", [
        "Profile Depth Data", "MPD Gauges", "Main Time Data",
        "Surge & Swab", "Choke Control", "Timeline", "Performance",
        "Engineering", "Settings"
    ], index=0)
    st.markdown("---")
    st.markdown("**Quick Setpoints**")
    state.mode = st.selectbox("Mode", ["Offline", "Simulation", "Live"],
                              index=["Offline", "Simulation", "Live"].index(state.mode))
    state.choke_mode = st.selectbox("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode))
    state.operating.sbp_setpoint = st.slider("SBP (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    state.operating.flow_in_gpm = st.number_input("Flow In (gpm)", 0.0, 2000.0, float(state.operating.flow_in_gpm), 10.0)
    state.operating.flow_out_gpm = st.number_input("Flow Out (gpm)", 0.0, 2000.0, float(state.operating.flow_out_gpm), 5.0)
    state.operating.choke_position = st.slider("Choke %", 0, 100, int(state.operating.choke_position), 1)
    if st.button("⟳ Recalculate", use_container_width=True, type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Recalculate", f"SBP={state.operating.sbp_setpoint:.0f}")
        st.session_state.state = log_activity(st.session_state.state, "Circulating", 2.0)
        st.rerun()

# ── Pages ──
if nav == "Profile Depth Data":
    gcols = st.columns(7)
    for col, (label, val, unit, delta) in zip(gcols, [
        ("BHP", f"{state.bhp:.0f}", "psi", f"Tgt {state.target_bhp:.0f}"),
        ("ECD", f"{state.ecd:.2f}", "ppg", f"Tgt {state.target_ecd:.2f}"),
        ("Model SPP", f"{state.model_spp:.0f}", "psi", None),
        ("SBP", f"{state.operating.sbp_setpoint:.0f}", "psi", None),
        ("Flow In", f"{state.operating.flow_in_gpm:.0f}", "gpm", None),
        ("Live PP", f"{state.live_pp:.0f}", "psi", f"OB {state.overbalance:.0f}"),
        ("Eff. Flow", f"{state.effective_flow:.0f}", "gpm", None),
    ]):
        col.metric(label, f"{val} {unit}", delta)

    left, right = st.columns([3.1, 1.2])
    with left:
        df = pd.DataFrame(get_profile_depth_data(state, 18))
        display_df = df.rename(columns={
            "MD_ft": "MD", "TVD_ft": "TVD", "Formation": "Form",
            "Formation_Temp_F": "Form.T", "Annulus_Temp_F": "Ann.T",
            "Pipe_Temp_F": "Pipe.T", "Annulus_Density_ppg": "Ann.Dens",
            "Pipe_Density_ppg": "Pipe.Dens", "Annulus_Friction_psi": "Ann.Fric",
            "Pipe_App_Visc_cP": "Pipe.Visc", "Annulus_App_Visc_cP": "Ann.Visc",
            "Annulus_ECD_ppg": "Ann.ECD", "Annulus_Pressure_psi": "Ann.P",
            "Pore_Pressure_psi": "PP", "Fracture_Pressure_psi": "FG",
            "PPG": "PPG", "WBSG_ppg": "WBSG", "WBS_psi": "WBS"
        })
        st.dataframe(display_df, use_container_width=True, height=420)

    with right:
        st.markdown("**Well Schematic + Lithology**")
        fig = go.Figure()
        total_md = max(state.geometry.md, 1)
        for layer in state.lithology:
            y0 = (layer["md_top"] / total_md) * 100
            y1 = min((layer["md_bot"] / total_md) * 100, 100)
            if y0 > 100: continue
            fig.add_shape(type="rect", x0=0.15, x1=0.85, y0=y0, y1=y1,
                          fillcolor=layer["color"], opacity=0.85, line=dict(color="#222", width=0.5))
            if y1 - y0 > 4:
                fig.add_annotation(x=0.5, y=(y0+y1)/2, text=layer["name"], showarrow=False,
                                   font=dict(size=9, color="#111"))
        bit_y = (state.geometry.bit_depth / total_md) * 100
        fig.add_shape(type="rect", x0=0.05, x1=0.95, y0=bit_y-1.2, y1=bit_y+1.2,
                      fillcolor="#00d4aa", line=dict(width=0))
        fig.update_layout(height=390, margin=dict(l=5,r=5,t=5,b=5),
                          paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
                          xaxis=dict(visible=False, range=[0,1]),
                          yaxis=dict(range=[100,0], color="#718096", gridcolor="#2d3748", tickfont=dict(size=9)))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<small>**{state.current_formation}** | Bit {state.geometry.bit_depth:.0f} ft | Choke {state.operating.choke_position:.0f}% ({state.choke_mode})</small>", unsafe_allow_html=True)

elif nav == "Performance":
    st.subheader("Performance – Well Activities")
    summary = get_activity_summary(state)
    # Pie chart
    fig_pie = px.pie(
        names=list(summary.keys()),
        values=list(summary.values()),
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.35
    )
    fig_pie.update_layout(
        paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
        font=dict(color="#ccc"), height=380,
        margin=dict(t=30, b=20, l=20, r=20)
    )
    col_p1, col_p2 = st.columns([1.4, 1])
    with col_p1:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_p2:
        st.markdown("**Activity Summary (minutes)**")
        for k, v in sorted(summary.items(), key=lambda x: -x[1]):
            st.write(f"• **{k}**: {v:.0f} min")
        st.markdown("---")
        st.markdown("**Log Activity**")
        act = st.selectbox("Activity type", ["Drilling", "Connection", "Circulating", "Trip", "Offline", "Other"])
        dur = st.number_input("Duration (min)", 0.5, 120.0, 5.0, 0.5)
        if st.button("Add Activity"):
            st.session_state.state = log_activity(state, act, dur)
            st.session_state.state = add_timeline_event(st.session_state.state, f"Activity: {act}", f"{dur} min")
            st.rerun()

elif nav == "Engineering":
    st.subheader("Engineering – Quick Hydraulics Summary")
    e1, e2, e3 = st.columns(3)
    e1.metric("Hydrostatic", f"{state.hydrostatic:.0f} psi")
    e1.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    e1.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    e2.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    e2.metric("U-Tube ΔP", f"{state.u_tube_dp:.0f} psi")
    e2.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    e3.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    e3.metric("Live PP Gradient", f"{state.litho_gradient:.3f} psi/ft")
    e3.metric("Overbalance", f"{state.overbalance:.0f} psi")
    st.markdown("---")
    st.markdown("**Pressure Budget at Bit**")
    budget = {
        "Hydrostatic": state.hydrostatic,
        "Annular Friction": state.annular_friction,
        "SBP": state.operating.sbp_setpoint,
    }
    fig_bar = go.Figure(go.Bar(
        x=list(budget.keys()), y=list(budget.values()),
        marker_color=["#4a9eff", "#00d4aa", "#ffaa00"]
    ))
    fig_bar.update_layout(
        paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
        font=dict(color="#ccc"), height=280,
        yaxis_title="psi", margin=dict(t=20, b=40)
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("BHP = Hydrostatic + Annular Friction + SBP  |  Model follows Excel v4 physical order")

elif nav == "Timeline":
    st.subheader("Timeline / Feedback")
    ec1, ec2 = st.columns([3, 1])
    with ec1:
        new_event = st.text_input("Add event comment", placeholder="Connection, Pump up, Gas show...")
    with ec2:
        st.write(""); st.write("")
        if st.button("Add to Timeline", use_container_width=True) and new_event.strip():
            st.session_state.state = add_timeline_event(state, new_event.strip())
            st.rerun()
    if state.timeline:
        st.dataframe(pd.DataFrame(state.timeline), use_container_width=True, height=380)
    else:
        st.info("No events yet.")

elif nav == "Surge & Swab":
    st.subheader("Surge & Swab Calculator")
    sc1, sc2 = st.columns(2)
    with sc1:
        state.surge.pipe_velocity_ftmin = st.slider("Pipe Velocity (ft/min)", 5, 150, int(state.surge.pipe_velocity_ftmin))
        state.surge.acceleration = st.number_input("Acceleration (ft/s²)", 0.0, 3.0, float(state.surge.acceleration), 0.1)
        state.surge.open_end = st.checkbox("Open Ended", value=state.surge.open_end)
        state.surge.clinging_factor = st.slider("Clinging Factor", 0.1, 1.0, float(state.surge.clinging_factor), 0.05)
        if st.button("Calculate Surge/Swab", type="primary"):
            st.session_state.state = run_hydraulics(state)
            st.session_state.state = add_timeline_event(st.session_state.state, "Surge/Swab", f"Vel={state.surge.pipe_velocity_ftmin}")
            st.session_state.state = log_activity(st.session_state.state, "Trip", 3.0)
            st.rerun()
    with sc2:
        st.metric("Max Surge", f"{state.max_surge_psi:.0f} psi")
        st.metric("Max Swab", f"{state.max_swab_psi:.0f} psi")
        st.metric("ESD Surge", f"{state.esd_surge:.2f} ppg")
        st.metric("ESD Swab", f"{state.esd_swab:.2f} ppg")
        st.metric("BHP @ Surge", f"{state.bhp + state.max_surge_psi:.0f} psi")
        st.metric("BHP @ Swab", f"{state.bhp + state.max_swab_psi:.0f} psi")

elif nav == "Choke Control":
    st.subheader("Choke Control Panel")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        state.choke_mode = st.radio("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode), horizontal=True)
    with cc2:
        if state.choke_mode == "CBHP":
            state.target_bhp = st.number_input("Target BHP (psi)", 0.0, 15000.0, float(state.target_bhp), 10.0)
        elif state.choke_mode == "AUTO":
            state.target_ecd = st.number_input("Target ECD (ppg)", 8.0, 18.0, float(state.target_ecd), 0.05)
        state.operating.sbp_setpoint = st.slider("SBP Setpoint (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    with cc3:
        st.metric("Choke Position", f"{state.operating.choke_position:.0f} %")
        st.metric("Current SBP", f"{state.operating.sbp_setpoint:.0f} psi")
        st.metric("Current BHP", f"{state.bhp:.0f} psi")
        st.metric("Current ECD", f"{state.ecd:.2f} ppg")
    if st.button("Apply Setpoint & Recalculate", type="primary", use_container_width=True):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Choke Apply", f"{state.choke_mode} SBP={state.operating.sbp_setpoint:.0f}")
        st.rerun()
    if state.choke_mode == "CBHP":
        st.success("CBHP Auto active in Simulation mode → SBP adjusts to hold Target BHP.")

elif nav == "MPD Gauges":
    st.subheader("MPD Gauges")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("BHP", f"{state.bhp:.0f} psi", f"{state.bhp - state.target_bhp:+.0f}")
    g2.metric("ECD", f"{state.ecd:.2f} ppg", f"{state.ecd - state.target_ecd:+.2f}")
    g3.metric("SBP", f"{state.operating.sbp_setpoint:.0f} psi")
    g4.metric("Overbalance", f"{state.overbalance:.0f} psi")
    st.line_chart({
        "BHP": [state.bhp-40, state.bhp-15, state.bhp, state.bhp+8, state.bhp-5],
        "ECD x100": [(state.ecd-0.08)*100, (state.ecd-0.03)*100, state.ecd*100, (state.ecd+0.02)*100, state.ecd*100]
    })

elif nav == "Main Time Data":
    st.subheader("Main Time Data")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    m2.metric("Q Loss", f"{state.q_loss:.1f} gpm")
    m3.metric("Q U-Tube", f"{state.q_utube:.1f} gpm")
    m4.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    st.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    st.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    st.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    st.metric("Current Formation", state.current_formation)

elif nav == "Settings":
    st.subheader("Settings")
    new_name = st.text_input("Application Display Name", value=st.session_state.app_name)
    if st.button("Update Name"):
        st.session_state.app_name = new_name
        st.success(f"Name set to: {new_name}")
        st.rerun()
    st.markdown("---")
    st.markdown("**Well Geometry**")
    state.geometry.md = st.number_input("Total MD (ft)", value=float(state.geometry.md))
    state.geometry.tvd = st.number_input("TVD (ft)", value=float(state.geometry.tvd))
    state.geometry.hole_id = st.number_input("Hole ID (in)", value=float(state.geometry.hole_id))
    state.geometry.pipe_od = st.number_input("Pipe OD (in)", value=float(state.geometry.pipe_od))
    state.geometry.bit_depth = st.number_input("Bit Depth (ft)", value=float(state.geometry.bit_depth))
    st.markdown("**Fluid**")
    state.fluid.density_ppg = st.number_input("Mud Density (ppg)", value=float(state.fluid.density_ppg))
    state.fluid.temp_in = st.number_input("Mud Temp In (°F)", value=float(state.fluid.temp_in))
    state.fluid.temp_out = st.number_input("Mud Temp Out (°F)", value=float(state.fluid.temp_out))
    state.fluid.n = st.number_input("n (HB)", value=float(state.fluid.n), format="%.3f")
    state.fluid.K = st.number_input("K (HB)", value=float(state.fluid.K), format="%.3f")
    st.markdown("**Bit**")
    state.bit.bit_type = st.selectbox("Bit Type", ["PDC", "Diamond Impregnated", "Tricone"])
    state.bit.tfa = st.number_input("TFA (in²)", value=float(state.bit.tfa), format="%.3f")
    if st.button("Apply All & Recalculate", type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Settings Applied")
        st.rerun()

else:
    st.subheader(nav)
    st.info(f"Module **{nav}** ready for future expansion.")

st.markdown("<hr style='border-color:#333'>", unsafe_allow_html=True)
st.caption(f"{st.session_state.app_name} | Stage 4 | Performance + Engineering | Lithology + CBHP Auto | Excel v4 physics")
'''

(ROOT / "app.py").write_text(app_v4, encoding="utf-8")
print("  ✓ app.py  (Stage 4 – Performance + Engineering)")

readme4 = '''# ARHPP Digital Twin – Stage 4

## التشغيل
```bash
cd ARHPP_App
pip install -r requirements.txt
streamlit run app.py
```

## ما أُضيف في Stage 4
- صفحة Performance مع رسم دائري (Pie) لنسب الأنشطة + تسجيل يدوي
- صفحة Engineering تعرض Pressure Budget + ملخص هيدروليكي
- ربط الأنشطة بالـ Timeline تلقائياً
- تحسينات طفيفة على CBHP Auto

## الملف المتراكم
build_arhpp_full.py = المراحل 1 + 2 + 3 + 4
'''
(ROOT / "README.md").write_text(readme4, encoding="utf-8")
print("  ✓ README.md updated")

print()
print("=" * 60)
print("✅ Stage 4 completed successfully!")
print("  cd ARHPP_App && streamlit run app.py")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# STAGE 5 – Actual vs Model + Simulation polish + UI refinements
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ARHPP Full Application Builder – Stage 5")
print("Actual-vs-Model diagnostics + Simulation polish...")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Stage 5 Engine – add diagnostics helpers
# ─────────────────────────────────────────────────────────────
engine_v5 = '''"""
ARHPP Hydraulics Engine – Stage 5
+ Actual vs Model diagnostics
+ All previous: Lithology, CBHP Auto, Surge/Swab, Performance, Excel v4 order
"""

from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime
import math

DEFAULT_LITHOLOGY = [
    {"name": "Dammam",   "md_top": 0,     "md_bot": 800,   "color": "#c4a574", "pp_grad": 0.45, "fg_grad": 0.85},
    {"name": "Rus",      "md_top": 800,   "md_bot": 1400,  "color": "#e8d5b7", "pp_grad": 0.46, "fg_grad": 0.90},
    {"name": "Radhuma",  "md_top": 1400,  "md_bot": 2800,  "color": "#d4b896", "pp_grad": 0.47, "fg_grad": 0.88},
    {"name": "Tayarat",  "md_top": 2800,  "md_bot": 4200,  "color": "#8b7355", "pp_grad": 0.48, "fg_grad": 0.87},
    {"name": "Hartha",   "md_top": 4200,  "md_bot": 5500,  "color": "#a0896c", "pp_grad": 0.49, "fg_grad": 0.89},
    {"name": "Sadi",     "md_top": 5500,  "md_bot": 6200,  "color": "#6b5344", "pp_grad": 0.50, "fg_grad": 0.86},
    {"name": "Mutriba",  "md_top": 6200,  "md_bot": 7000,  "color": "#9c8b7a", "pp_grad": 0.51, "fg_grad": 0.90},
    {"name": "Mishrif",  "md_top": 7000,  "md_bot": 8200,  "color": "#b89b72", "pp_grad": 0.52, "fg_grad": 0.92},
    {"name": "Rumaila",  "md_top": 8200,  "md_bot": 9500,  "color": "#a67c52", "pp_grad": 0.53, "fg_grad": 0.93},
    {"name": "Ahmadi",   "md_top": 9500,  "md_bot": 10500, "color": "#7d6b5a", "pp_grad": 0.54, "fg_grad": 0.91},
    {"name": "Wara",     "md_top": 10500, "md_bot": 11200, "color": "#c2b280", "pp_grad": 0.55, "fg_grad": 0.90},
    {"name": "Burgan",   "md_top": 11200, "md_bot": 13000, "color": "#d2b48c", "pp_grad": 0.56, "fg_grad": 0.88},
]

@dataclass
class WellGeometry:
    md: float = 12000.0
    tvd: float = 11200.0
    hole_id: float = 8.5
    pipe_od: float = 5.0
    pipe_id: float = 4.276
    casing_od: float = 9.625
    bit_depth: float = 12000.0
    shoe_depth: float = 9410.0

@dataclass
class FluidProperties:
    density_ppg: float = 10.5
    pv: float = 28.0
    yp: float = 18.0
    n: float = 0.72
    K: float = 0.45
    tau_y: float = 6.5
    temp_in: float = 120.0
    temp_out: float = 155.0
    ambient_temp: float = 95.0
    temp_gradient: float = 1.5

@dataclass
class OperatingParams:
    flow_in_gpm: float = 850.0
    flow_out_gpm: float = 845.0
    sbp_setpoint: float = 200.0
    choke_position: float = 42.0
    rpm: float = 120.0
    wob: float = 25.0
    rop: float = 45.0
    spp_measured: float = 2850.0
    pump_efficiency: float = 0.97

@dataclass
class BitParams:
    bit_type: str = "PDC"
    tfa: float = 0.85
    bit_size: float = 8.5
    nozzles: str = "16/16/16/16/14/14"

@dataclass
class SurgeSwabParams:
    pipe_velocity_ftmin: float = 60.0
    acceleration: float = 0.5
    open_end: bool = True
    stand_length: float = 93.0
    clinging_factor: float = 0.45

@dataclass
class SimulationState:
    geometry: WellGeometry = field(default_factory=WellGeometry)
    fluid: FluidProperties = field(default_factory=FluidProperties)
    operating: OperatingParams = field(default_factory=OperatingParams)
    bit: BitParams = field(default_factory=BitParams)
    surge: SurgeSwabParams = field(default_factory=SurgeSwabParams)
    mode: str = "Offline"
    choke_mode: str = "AUTO"
    target_bhp: float = 7500.0
    target_ecd: float = 11.20
    litho_gradient: float = 0.56
    lithology: List[Dict] = field(default_factory=lambda: DEFAULT_LITHOLOGY.copy())
    timeline: List[Dict] = field(default_factory=list)
    activity_log: List[Dict] = field(default_factory=list)
    # Results
    bhp: float = 0.0
    ecd: float = 0.0
    model_spp: float = 0.0
    annular_friction: float = 0.0
    pipe_friction: float = 0.0
    bit_pressure_drop: float = 0.0
    hydrostatic: float = 0.0
    live_pp: float = 0.0
    overbalance: float = 0.0
    u_tube_dp: float = 0.0
    effective_flow: float = 0.0
    q_loss: float = 0.0
    q_utube: float = 0.0
    max_surge_psi: float = 0.0
    max_swab_psi: float = 0.0
    esd_surge: float = 0.0
    esd_swab: float = 0.0
    corrected_density: float = 0.0
    current_formation: str = "Burgan"
    # Diagnostics
    delta_flow: float = 0.0
    delta_spp: float = 0.0
    diag_status: str = "OK"
    diag_message: str = ""

def _hydrostatic(density, tvd):
    return 0.052 * density * tvd

def _bit_dp(q, dens, tfa):
    if tfa <= 0: return 0.0
    return (q ** 2 * dens) / (12031.0 * tfa ** 2)

def _annular_velocity(q_gpm, hole_id, pipe_od):
    area = (math.pi / 4.0) * (hole_id**2 - pipe_od**2) / 144.0
    return (q_gpm * 0.133681) / area if area > 0 else 0.0

def _friction_factor(re):
    return 16.0 / max(re, 1.0) if re < 2100 else 0.046 * (re ** -0.2)

def _annular_friction(q, dens, hole_id, pipe_od, length, n, K, rpm=0):
    dh = hole_id - pipe_od
    if dh <= 0 or length <= 0: return 0.0
    v = _annular_velocity(q, hole_id, pipe_od)
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * dh / mu_app
    f = _friction_factor(re)
    return max(f * dens * v**2 * length / (25.8 * dh) * (1.0 + rpm/200.0*0.08), 0.0)

def _pipe_friction(q, dens, pipe_id, length, n, K):
    if pipe_id <= 0 or length <= 0: return 0.0
    area = (math.pi / 4.0) * (pipe_id ** 2) / 144.0
    v = (q * 0.133681) / area if area > 0 else 0
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * pipe_id / mu_app
    f = _friction_factor(re)
    return max(f * dens * v**2 * length / (25.8 * pipe_id), 0.0)

def _temp_corrected_density(base, temp_in, temp_out, tvd, gradient):
    return base * (1.0 - 0.0003 * ((temp_in + (tvd/100.0)*gradient) - 80))

def get_formation_at_depth(lithology, md):
    for layer in lithology:
        if layer["md_top"] <= md <= layer["md_bot"]:
            return layer
    return lithology[-1] if lithology else {"name": "Unknown", "pp_grad": 0.56, "fg_grad": 0.90, "color": "#888"}

def calculate_surge_swab(state):
    s, g, f = state.surge, state.geometry, state.fluid
    v = s.pipe_velocity_ftmin / 60.0
    dh = g.hole_id - g.pipe_od
    if dh <= 0:
        state.max_surge_psi = state.max_swab_psi = 0.0
        return state
    cling = s.clinging_factor if s.open_end else 1.0
    mu = f.pv * 1.2 + f.yp * 0.5
    base = (mu * v * g.md) / (1000.0 * dh**2) * cling * 3.5
    accel = s.acceleration * f.density_ppg * g.md * 0.0015
    state.max_surge_psi = base + accel
    state.max_swab_psi = -(base * 0.9)
    state.esd_surge = state.ecd + (state.max_surge_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    state.esd_swab = state.ecd + (state.max_swab_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    return state

def auto_adjust_sbp_for_cbhp(state):
    if state.choke_mode != "CBHP":
        return state
    error = state.target_bhp - state.bhp
    step = max(-30.0, min(30.0, error * 0.18))
    state.operating.sbp_setpoint = max(0.0, min(1000.0, state.operating.sbp_setpoint + step))
    state.operating.choke_position = max(5.0, min(95.0, 28.0 + state.operating.sbp_setpoint / 9.5))
    return state

def run_diagnostics(state):
    """Actual vs Model – Flow & Density primary, SPP secondary only"""
    state.delta_flow = state.operating.flow_in_gpm - state.operating.flow_out_gpm
    state.delta_spp = state.operating.spp_measured - state.model_spp
    msgs = []
    status = "OK"
    if abs(state.delta_flow) > 15:
        status = "WARNING"
        msgs.append(f"Flow imbalance ΔQ={state.delta_flow:.1f} gpm (possible loss/gain)")
    elif abs(state.delta_flow) > 5:
        msgs.append(f"Minor flow difference ΔQ={state.delta_flow:.1f} gpm")
    if abs(state.delta_spp) > 150:
        status = "WARNING" if status == "OK" else status
        msgs.append(f"SPP residual {state.delta_spp:+.0f} psi (diagnostic only)")
    elif abs(state.delta_spp) > 50:
        msgs.append(f"SPP residual {state.delta_spp:+.0f} psi")
    if state.overbalance < 100:
        status = "ALERT"
        msgs.append(f"Low overbalance {state.overbalance:.0f} psi")
    state.diag_status = status
    state.diag_message = " | ".join(msgs) if msgs else "All primary parameters within normal range"
    return state

def run_hydraulics(state):
    g, f, o, b = state.geometry, state.fluid, state.operating, state.bit
    form = get_formation_at_depth(state.lithology, g.bit_depth)
    state.current_formation = form["name"]
    state.litho_gradient = form.get("pp_grad", 0.56)

    state.corrected_density = _temp_corrected_density(f.density_ppg, f.temp_in, f.temp_out, g.tvd, f.temp_gradient)
    state.q_loss = max(0.0, o.flow_in_gpm - o.flow_out_gpm)
    dens_ann = state.corrected_density + 0.15
    state.u_tube_dp = 0.052 * (dens_ann - state.corrected_density) * g.tvd * 0.15
    state.q_utube = max(0.0, state.u_tube_dp / 8.0)
    state.effective_flow = o.flow_in_gpm + state.q_utube - state.q_loss

    state.hydrostatic = _hydrostatic(state.corrected_density, g.tvd)
    state.bit_pressure_drop = _bit_dp(state.effective_flow, state.corrected_density, b.tfa)
    state.annular_friction = _annular_friction(state.effective_flow, state.corrected_density, g.hole_id, g.pipe_od, g.md, f.n, f.K, o.rpm)
    state.pipe_friction = _pipe_friction(state.effective_flow, state.corrected_density, g.pipe_id, g.md, f.n, f.K)

    state.bhp = state.hydrostatic + state.annular_friction + o.sbp_setpoint
    state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
    state.model_spp = state.pipe_friction + state.bit_pressure_drop + o.sbp_setpoint + state.annular_friction * 0.15

    bit_factor = {"PDC": 1.0, "Diamond Impregnated": 1.05, "Tricone": 0.95}.get(b.bit_type, 1.0)
    rop_factor = 1.0 - (o.rop - 40) * 0.001 if o.rop > 0 else 1.0
    state.live_pp = g.tvd * state.litho_gradient * bit_factor * max(0.9, min(1.1, rop_factor))
    state.overbalance = state.bhp - state.live_pp

    state = calculate_surge_swab(state)

    if state.choke_mode == "CBHP" and state.mode == "Simulation":
        state = auto_adjust_sbp_for_cbhp(state)
        state.bhp = state.hydrostatic + state.annular_friction + state.operating.sbp_setpoint
        state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
        state.overbalance = state.bhp - state.live_pp

    state = run_diagnostics(state)
    return state

def get_profile_depth_data(state, num_points=16):
    rows = []
    md_step = state.geometry.md / max(num_points - 1, 1)
    for i in range(num_points):
        md = i * md_step
        tvd = md * (state.geometry.tvd / state.geometry.md) if state.geometry.md > 0 else md
        frac = md / state.geometry.md if state.geometry.md > 0 else 0.0
        dens_ann = state.corrected_density + frac * 0.25
        hydro = _hydrostatic(dens_ann, tvd)
        fric = state.annular_friction * frac
        pressure = hydro + fric + state.operating.sbp_setpoint * frac
        ecd = pressure / (0.052 * tvd) if tvd > 1 else 0.0
        form = get_formation_at_depth(state.lithology, md)
        form_temp = state.fluid.ambient_temp + (tvd / 100.0) * state.fluid.temp_gradient
        ann_temp = state.fluid.temp_in + frac * (state.fluid.temp_out - state.fluid.temp_in)
        rows.append({
            "MD_ft": round(md, 0), "TVD_ft": round(tvd, 0), "Formation": form["name"],
            "Formation_Temp_F": round(form_temp, 1), "Annulus_Temp_F": round(ann_temp, 1),
            "Pipe_Temp_F": round(state.fluid.temp_in + frac * 18, 1),
            "Annulus_Density_ppg": round(dens_ann, 2), "Pipe_Density_ppg": round(state.corrected_density, 2),
            "Annulus_Friction_psi": round(fric, 1),
            "Pipe_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.3), 1),
            "Annulus_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.5), 1),
            "Annulus_ECD_ppg": round(ecd, 2), "Annulus_Pressure_psi": round(pressure, 1),
            "Pore_Pressure_psi": round(tvd * form.get("pp_grad", 0.56), 1),
            "Fracture_Pressure_psi": round(tvd * form.get("fg_grad", 0.90), 1),
            "PPG": round(form.get("pp_grad", 0.56) * 19.25, 2), "WBSG_ppg": 0.0, "WBS_psi": 0.0,
        })
    return rows

def add_timeline_event(state, event, details=""):
    state.timeline.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "event": event, "details": details})
    state.timeline = state.timeline[:50]
    return state

def log_activity(state, activity, duration_min=1.0):
    state.activity_log.append({"time": datetime.now().strftime("%H:%M:%S"), "activity": activity, "duration_min": duration_min})
    state.activity_log = state.activity_log[-200:]
    return state

def get_activity_summary(state):
    summary = {}
    for a in state.activity_log:
        summary[a["activity"]] = summary.get(a["activity"], 0.0) + a.get("duration_min", 1.0)
    if not summary:
        summary = {"Drilling": 42, "Connection": 18, "Circulating": 15, "Trip": 12, "Offline": 8, "Other": 5}
    return summary
'''

(ROOT / "engines" / "hydraulics_engine.py").write_text(engine_v5, encoding="utf-8")
print("  ✓ engines/hydraulics_engine.py  (Stage 5 – diagnostics)")

# ─────────────────────────────────────────────────────────────
# Stage 5 App – add Actual vs Model page + status bar
# ─────────────────────────────────────────────────────────────
app_v5 = '''"""
ARHPP Main Application – Stage 5
Actual vs Model diagnostics + all previous modules
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import APP_NAME, APP_VERSION, APP_SUBTITLE
from engines.hydraulics_engine import (
    SimulationState, run_hydraulics, get_profile_depth_data,
    add_timeline_event, log_activity, get_activity_summary
)

st.set_page_config(page_title=APP_NAME, page_icon="🛢️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #1a1d23; color: #d0d0d0; }
    section[data-testid="stSidebar"] { background-color: #12151a; }
    div[data-testid="stMetricValue"] { color: #00d4aa; font-size: 1.3rem; }
    .block-container { padding-top: 0.5rem; padding-bottom: 0.3rem; }
    h1, h2, h3, h4 { color: #e8e8e8 !important; }
</style>
""", unsafe_allow_html=True)

if "state" not in st.session_state:
    st.session_state.state = run_hydraulics(SimulationState())
if "app_name" not in st.session_state:
    st.session_state.app_name = APP_NAME

state = st.session_state.state

# Top bar
c1, c2, c3, c4 = st.columns([0.5, 3.6, 1.5, 1.2])
with c1:
    st.markdown("### 🛢️")
with c2:
    st.markdown(f"## {st.session_state.app_name} <span style='font-size:12px;color:#888'>{APP_VERSION}</span>", unsafe_allow_html=True)
with c3:
    st.caption(f"Bit: {state.geometry.bit_depth:.0f} ft | {state.current_formation}")
with c4:
    mode_color = {"Offline": "#ffaa00", "Simulation": "#00d4aa", "Live": "#00ff88"}.get(state.mode, "#ffaa00")
    st.markdown(f"<div style='text-align:right;padding-top:10px'><span style='background:{mode_color};color:#111;padding:4px 12px;border-radius:4px;font-weight:700;font-size:12px'>{state.mode.upper()}</span></div>", unsafe_allow_html=True)

# Status bar (Actual vs Model summary)
status_color = {"OK": "#00d4aa", "WARNING": "#ffaa00", "ALERT": "#ff5555"}.get(state.diag_status, "#888")
st.markdown(f"""
<div style="background:#252a33;padding:6px 12px;border-radius:4px;border-left:4px solid {status_color};margin-bottom:8px;font-size:13px">
<b style="color:{status_color}">{state.diag_status}</b> &nbsp;|&nbsp; {state.diag_message}
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"**{st.session_state.app_name}**")
    nav = st.radio("Modules", [
        "Profile Depth Data", "MPD Gauges", "Main Time Data",
        "Surge & Swab", "Choke Control", "Actual vs Model",
        "Timeline", "Performance", "Engineering", "Settings"
    ], index=0)
    st.markdown("---")
    st.markdown("**Quick Setpoints**")
    state.mode = st.selectbox("Mode", ["Offline", "Simulation", "Live"],
                              index=["Offline", "Simulation", "Live"].index(state.mode))
    state.choke_mode = st.selectbox("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode))
    state.operating.sbp_setpoint = st.slider("SBP (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    state.operating.flow_in_gpm = st.number_input("Flow In (gpm)", 0.0, 2000.0, float(state.operating.flow_in_gpm), 10.0)
    state.operating.flow_out_gpm = st.number_input("Flow Out (gpm)", 0.0, 2000.0, float(state.operating.flow_out_gpm), 5.0)
    state.operating.spp_measured = st.number_input("SPP Measured (psi)", 0.0, 6000.0, float(state.operating.spp_measured), 10.0)
    state.operating.choke_position = st.slider("Choke %", 0, 100, int(state.operating.choke_position), 1)
    if st.button("⟳ Recalculate", use_container_width=True, type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Recalculate", f"SBP={state.operating.sbp_setpoint:.0f}")
        st.session_state.state = log_activity(st.session_state.state, "Circulating", 2.0)
        st.rerun()

# ── Pages ──
if nav == "Profile Depth Data":
    gcols = st.columns(7)
    for col, (label, val, unit, delta) in zip(gcols, [
        ("BHP", f"{state.bhp:.0f}", "psi", f"Tgt {state.target_bhp:.0f}"),
        ("ECD", f"{state.ecd:.2f}", "ppg", f"Tgt {state.target_ecd:.2f}"),
        ("Model SPP", f"{state.model_spp:.0f}", "psi", None),
        ("SBP", f"{state.operating.sbp_setpoint:.0f}", "psi", None),
        ("Flow In", f"{state.operating.flow_in_gpm:.0f}", "gpm", None),
        ("Live PP", f"{state.live_pp:.0f}", "psi", f"OB {state.overbalance:.0f}"),
        ("Eff. Flow", f"{state.effective_flow:.0f}", "gpm", None),
    ]):
        col.metric(label, f"{val} {unit}", delta)

    left, right = st.columns([3.1, 1.2])
    with left:
        df = pd.DataFrame(get_profile_depth_data(state, 18))
        display_df = df.rename(columns={
            "MD_ft": "MD", "TVD_ft": "TVD", "Formation": "Form",
            "Formation_Temp_F": "Form.T", "Annulus_Temp_F": "Ann.T",
            "Pipe_Temp_F": "Pipe.T", "Annulus_Density_ppg": "Ann.Dens",
            "Pipe_Density_ppg": "Pipe.Dens", "Annulus_Friction_psi": "Ann.Fric",
            "Pipe_App_Visc_cP": "Pipe.Visc", "Annulus_App_Visc_cP": "Ann.Visc",
            "Annulus_ECD_ppg": "Ann.ECD", "Annulus_Pressure_psi": "Ann.P",
            "Pore_Pressure_psi": "PP", "Fracture_Pressure_psi": "FG",
            "PPG": "PPG", "WBSG_ppg": "WBSG", "WBS_psi": "WBS"
        })
        st.dataframe(display_df, use_container_width=True, height=400)

    with right:
        st.markdown("**Well Schematic + Lithology**")
        fig = go.Figure()
        total_md = max(state.geometry.md, 1)
        for layer in state.lithology:
            y0 = (layer["md_top"] / total_md) * 100
            y1 = min((layer["md_bot"] / total_md) * 100, 100)
            if y0 > 100: continue
            fig.add_shape(type="rect", x0=0.15, x1=0.85, y0=y0, y1=y1,
                          fillcolor=layer["color"], opacity=0.85, line=dict(color="#222", width=0.5))
            if y1 - y0 > 4:
                fig.add_annotation(x=0.5, y=(y0+y1)/2, text=layer["name"], showarrow=False, font=dict(size=9, color="#111"))
        bit_y = (state.geometry.bit_depth / total_md) * 100
        fig.add_shape(type="rect", x0=0.05, x1=0.95, y0=bit_y-1.2, y1=bit_y+1.2, fillcolor="#00d4aa", line=dict(width=0))
        fig.update_layout(height=370, margin=dict(l=5,r=5,t=5,b=5), paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
                          xaxis=dict(visible=False, range=[0,1]),
                          yaxis=dict(range=[100,0], color="#718096", gridcolor="#2d3748", tickfont=dict(size=9)))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<small>**{state.current_formation}** | Bit {state.geometry.bit_depth:.0f} ft | Choke {state.operating.choke_position:.0f}% ({state.choke_mode})</small>", unsafe_allow_html=True)

elif nav == "Actual vs Model":
    st.subheader("Actual vs Model Diagnostics")
    st.caption("Primary drivers: Flow In/Out + Density + Temperature. SPP is secondary diagnostic only.")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Flow In (Actual)", f"{state.operating.flow_in_gpm:.1f} gpm")
    d2.metric("Flow Out (Actual)", f"{state.operating.flow_out_gpm:.1f} gpm")
    d3.metric("ΔQ (In−Out)", f"{state.delta_flow:.1f} gpm")
    d4.metric("Q Loss (model)", f"{state.q_loss:.1f} gpm")

    st.markdown("---")
    s1, s2, s3 = st.columns(3)
    s1.metric("SPP Measured", f"{state.operating.spp_measured:.0f} psi")
    s2.metric("SPP Model", f"{state.model_spp:.0f} psi")
    s3.metric("Δ SPP (Meas−Model)", f"{state.delta_spp:+.0f} psi")

    st.markdown("---")
    st.markdown(f"**Status: {state.diag_status}**")
    st.info(state.diag_message)

    # Simple comparison bars
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Measured / Actual", x=["Flow In", "SPP"], y=[state.operating.flow_in_gpm, state.operating.spp_measured], marker_color="#4a9eff"))
    fig.add_trace(go.Bar(name="Model", x=["Flow In", "SPP"], y=[state.operating.flow_in_gpm, state.model_spp], marker_color="#00d4aa"))
    fig.update_layout(barmode="group", paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
                      font=dict(color="#ccc"), height=300, margin=dict(t=20, b=40))
    st.plotly_chart(fig, use_container_width=True)
    st.warning("SPP difference is used only as a diagnostic flag. It does NOT drive the pressure calculations.")

elif nav == "Performance":
    st.subheader("Performance – Well Activities")
    summary = get_activity_summary(state)
    fig_pie = px.pie(names=list(summary.keys()), values=list(summary.values()),
                     color_discrete_sequence=px.colors.qualitative.Set2, hole=0.35)
    fig_pie.update_layout(paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"), height=360, margin=dict(t=30,b=20,l=20,r=20))
    col_p1, col_p2 = st.columns([1.4, 1])
    with col_p1:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_p2:
        st.markdown("**Activity Summary (minutes)**")
        for k, v in sorted(summary.items(), key=lambda x: -x[1]):
            st.write(f"• **{k}**: {v:.0f} min")
        st.markdown("---")
        act = st.selectbox("Activity type", ["Drilling", "Connection", "Circulating", "Trip", "Offline", "Other"])
        dur = st.number_input("Duration (min)", 0.5, 120.0, 5.0, 0.5)
        if st.button("Add Activity"):
            st.session_state.state = log_activity(state, act, dur)
            st.session_state.state = add_timeline_event(st.session_state.state, f"Activity: {act}", f"{dur} min")
            st.rerun()

elif nav == "Engineering":
    st.subheader("Engineering – Hydraulics Summary")
    e1, e2, e3 = st.columns(3)
    e1.metric("Hydrostatic", f"{state.hydrostatic:.0f} psi")
    e1.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    e1.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    e2.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    e2.metric("U-Tube ΔP", f"{state.u_tube_dp:.0f} psi")
    e2.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    e3.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    e3.metric("Live PP Gradient", f"{state.litho_gradient:.3f} psi/ft")
    e3.metric("Overbalance", f"{state.overbalance:.0f} psi")
    budget = {"Hydrostatic": state.hydrostatic, "Annular Friction": state.annular_friction, "SBP": state.operating.sbp_setpoint}
    fig_bar = go.Figure(go.Bar(x=list(budget.keys()), y=list(budget.values()), marker_color=["#4a9eff", "#00d4aa", "#ffaa00"]))
    fig_bar.update_layout(paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"), height=260, yaxis_title="psi", margin=dict(t=20,b=40))
    st.plotly_chart(fig_bar, use_container_width=True)

elif nav == "Timeline":
    st.subheader("Timeline / Feedback")
    ec1, ec2 = st.columns([3, 1])
    with ec1:
        new_event = st.text_input("Add event comment", placeholder="Connection, Pump up, Gas show...")
    with ec2:
        st.write(""); st.write("")
        if st.button("Add to Timeline", use_container_width=True) and new_event.strip():
            st.session_state.state = add_timeline_event(state, new_event.strip())
            st.rerun()
    if state.timeline:
        st.dataframe(pd.DataFrame(state.timeline), use_container_width=True, height=360)
    else:
        st.info("No events yet.")

elif nav == "Surge & Swab":
    st.subheader("Surge & Swab Calculator")
    sc1, sc2 = st.columns(2)
    with sc1:
        state.surge.pipe_velocity_ftmin = st.slider("Pipe Velocity (ft/min)", 5, 150, int(state.surge.pipe_velocity_ftmin))
        state.surge.acceleration = st.number_input("Acceleration (ft/s²)", 0.0, 3.0, float(state.surge.acceleration), 0.1)
        state.surge.open_end = st.checkbox("Open Ended", value=state.surge.open_end)
        state.surge.clinging_factor = st.slider("Clinging Factor", 0.1, 1.0, float(state.surge.clinging_factor), 0.05)
        if st.button("Calculate Surge/Swab", type="primary"):
            st.session_state.state = run_hydraulics(state)
            st.session_state.state = add_timeline_event(st.session_state.state, "Surge/Swab", f"Vel={state.surge.pipe_velocity_ftmin}")
            st.session_state.state = log_activity(st.session_state.state, "Trip", 3.0)
            st.rerun()
    with sc2:
        st.metric("Max Surge", f"{state.max_surge_psi:.0f} psi")
        st.metric("Max Swab", f"{state.max_swab_psi:.0f} psi")
        st.metric("ESD Surge", f"{state.esd_surge:.2f} ppg")
        st.metric("ESD Swab", f"{state.esd_swab:.2f} ppg")
        st.metric("BHP @ Surge", f"{state.bhp + state.max_surge_psi:.0f} psi")
        st.metric("BHP @ Swab", f"{state.bhp + state.max_swab_psi:.0f} psi")

elif nav == "Choke Control":
    st.subheader("Choke Control Panel")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        state.choke_mode = st.radio("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode), horizontal=True)
    with cc2:
        if state.choke_mode == "CBHP":
            state.target_bhp = st.number_input("Target BHP (psi)", 0.0, 15000.0, float(state.target_bhp), 10.0)
        elif state.choke_mode == "AUTO":
            state.target_ecd = st.number_input("Target ECD (ppg)", 8.0, 18.0, float(state.target_ecd), 0.05)
        state.operating.sbp_setpoint = st.slider("SBP Setpoint (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    with cc3:
        st.metric("Choke Position", f"{state.operating.choke_position:.0f} %")
        st.metric("Current SBP", f"{state.operating.sbp_setpoint:.0f} psi")
        st.metric("Current BHP", f"{state.bhp:.0f} psi")
        st.metric("Current ECD", f"{state.ecd:.2f} ppg")
    if st.button("Apply Setpoint & Recalculate", type="primary", use_container_width=True):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Choke Apply", f"{state.choke_mode} SBP={state.operating.sbp_setpoint:.0f}")
        st.rerun()
    if state.choke_mode == "CBHP":
        st.success("CBHP Auto active in Simulation mode → SBP adjusts to hold Target BHP.")

elif nav == "MPD Gauges":
    st.subheader("MPD Gauges")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("BHP", f"{state.bhp:.0f} psi", f"{state.bhp - state.target_bhp:+.0f}")
    g2.metric("ECD", f"{state.ecd:.2f} ppg", f"{state.ecd - state.target_ecd:+.2f}")
    g3.metric("SBP", f"{state.operating.sbp_setpoint:.0f} psi")
    g4.metric("Overbalance", f"{state.overbalance:.0f} psi")
    st.line_chart({"BHP": [state.bhp-40, state.bhp-15, state.bhp, state.bhp+8, state.bhp-5],
                   "ECD x100": [(state.ecd-0.08)*100, (state.ecd-0.03)*100, state.ecd*100, (state.ecd+0.02)*100, state.ecd*100]})

elif nav == "Main Time Data":
    st.subheader("Main Time Data")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    m2.metric("Q Loss", f"{state.q_loss:.1f} gpm")
    m3.metric("Q U-Tube", f"{state.q_utube:.1f} gpm")
    m4.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    st.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    st.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    st.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    st.metric("Current Formation", state.current_formation)

elif nav == "Settings":
    st.subheader("Settings")
    new_name = st.text_input("Application Display Name", value=st.session_state.app_name)
    if st.button("Update Name"):
        st.session_state.app_name = new_name
        st.success(f"Name set to: {new_name}")
        st.rerun()
    st.markdown("---")
    st.markdown("**Well Geometry**")
    state.geometry.md = st.number_input("Total MD (ft)", value=float(state.geometry.md))
    state.geometry.tvd = st.number_input("TVD (ft)", value=float(state.geometry.tvd))
    state.geometry.hole_id = st.number_input("Hole ID (in)", value=float(state.geometry.hole_id))
    state.geometry.pipe_od = st.number_input("Pipe OD (in)", value=float(state.geometry.pipe_od))
    state.geometry.bit_depth = st.number_input("Bit Depth (ft)", value=float(state.geometry.bit_depth))
    st.markdown("**Fluid**")
    state.fluid.density_ppg = st.number_input("Mud Density (ppg)", value=float(state.fluid.density_ppg))
    state.fluid.temp_in = st.number_input("Mud Temp In (°F)", value=float(state.fluid.temp_in))
    state.fluid.temp_out = st.number_input("Mud Temp Out (°F)", value=float(state.fluid.temp_out))
    state.fluid.n = st.number_input("n (HB)", value=float(state.fluid.n), format="%.3f")
    state.fluid.K = st.number_input("K (HB)", value=float(state.fluid.K), format="%.3f")
    st.markdown("**Bit**")
    state.bit.bit_type = st.selectbox("Bit Type", ["PDC", "Diamond Impregnated", "Tricone"])
    state.bit.tfa = st.number_input("TFA (in²)", value=float(state.bit.tfa), format="%.3f")
    if st.button("Apply All & Recalculate", type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Settings Applied")
        st.rerun()

else:
    st.subheader(nav)
    st.info(f"Module **{nav}** ready.")

st.markdown("<hr style='border-color:#333'>", unsafe_allow_html=True)
st.caption(f"{st.session_state.app_name} | Stage 5 | Actual-vs-Model | Lithology + CBHP Auto | Excel v4 physics | SPP diagnostic only")
'''

(ROOT / "app.py").write_text(app_v5, encoding="utf-8")
print("  ✓ app.py  (Stage 5 – Actual vs Model + status bar)")

readme5 = '''# ARHPP Digital Twin – Stage 5

## التشغيل
```bash
cd ARHPP_App
pip install -r requirements.txt
streamlit run app.py
```

## ما أُضيف في Stage 5
- صفحة **Actual vs Model** كاملة (Flow أساسي، SPP تشخيصي فقط)
- شريط حالة علوي يظهر Status (OK / WARNING / ALERT) + الرسالة
- إدخال SPP Measured من الـ Sidebar
- كل الوحدات السابقة ما زالت تعمل

## الملف المتراكم
build_arhpp_full.py = المراحل 1 → 5
'''
(ROOT / "README.md").write_text(readme5, encoding="utf-8")
print("  ✓ README.md updated")

print()
print("=" * 60)
print("✅ Stage 5 completed successfully!")
print("  cd ARHPP_App && streamlit run app.py")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# STAGE 6 – Live Simulation polish + UI refinements + Schematic detail
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ARHPP Full Application Builder – Stage 6")
print("Live Simulation polish + richer schematic + UI refinements...")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Stage 6 Engine – minor simulation helpers + history for trends
# ─────────────────────────────────────────────────────────────
engine_v6 = r'''"""
ARHPP Hydraulics Engine – Stage 6
+ Simple history buffers for live trends
+ All previous features (Lithology, CBHP Auto, Surge/Swab, Diagnostics, Performance)
"""

from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime
import math

DEFAULT_LITHOLOGY = [
    {"name": "Dammam",   "md_top": 0,     "md_bot": 800,   "color": "#c4a574", "pp_grad": 0.45, "fg_grad": 0.85},
    {"name": "Rus",      "md_top": 800,   "md_bot": 1400,  "color": "#e8d5b7", "pp_grad": 0.46, "fg_grad": 0.90},
    {"name": "Radhuma",  "md_top": 1400,  "md_bot": 2800,  "color": "#d4b896", "pp_grad": 0.47, "fg_grad": 0.88},
    {"name": "Tayarat",  "md_top": 2800,  "md_bot": 4200,  "color": "#8b7355", "pp_grad": 0.48, "fg_grad": 0.87},
    {"name": "Hartha",   "md_top": 4200,  "md_bot": 5500,  "color": "#a0896c", "pp_grad": 0.49, "fg_grad": 0.89},
    {"name": "Sadi",     "md_top": 5500,  "md_bot": 6200,  "color": "#6b5344", "pp_grad": 0.50, "fg_grad": 0.86},
    {"name": "Mutriba",  "md_top": 6200,  "md_bot": 7000,  "color": "#9c8b7a", "pp_grad": 0.51, "fg_grad": 0.90},
    {"name": "Mishrif",  "md_top": 7000,  "md_bot": 8200,  "color": "#b89b72", "pp_grad": 0.52, "fg_grad": 0.92},
    {"name": "Rumaila",  "md_top": 8200,  "md_bot": 9500,  "color": "#a67c52", "pp_grad": 0.53, "fg_grad": 0.93},
    {"name": "Ahmadi",   "md_top": 9500,  "md_bot": 10500, "color": "#7d6b5a", "pp_grad": 0.54, "fg_grad": 0.91},
    {"name": "Wara",     "md_top": 10500, "md_bot": 11200, "color": "#c2b280", "pp_grad": 0.55, "fg_grad": 0.90},
    {"name": "Burgan",   "md_top": 11200, "md_bot": 13000, "color": "#d2b48c", "pp_grad": 0.56, "fg_grad": 0.88},
]

@dataclass
class WellGeometry:
    md: float = 12000.0
    tvd: float = 11200.0
    hole_id: float = 8.5
    pipe_od: float = 5.0
    pipe_id: float = 4.276
    casing_od: float = 9.625
    bit_depth: float = 12000.0
    shoe_depth: float = 9410.0

@dataclass
class FluidProperties:
    density_ppg: float = 10.5
    pv: float = 28.0
    yp: float = 18.0
    n: float = 0.72
    K: float = 0.45
    tau_y: float = 6.5
    temp_in: float = 120.0
    temp_out: float = 155.0
    ambient_temp: float = 95.0
    temp_gradient: float = 1.5

@dataclass
class OperatingParams:
    flow_in_gpm: float = 850.0
    flow_out_gpm: float = 845.0
    sbp_setpoint: float = 200.0
    choke_position: float = 42.0
    rpm: float = 120.0
    wob: float = 25.0
    rop: float = 45.0
    spp_measured: float = 2850.0
    pump_efficiency: float = 0.97

@dataclass
class BitParams:
    bit_type: str = "PDC"
    tfa: float = 0.85
    bit_size: float = 8.5
    nozzles: str = "16/16/16/16/14/14"

@dataclass
class SurgeSwabParams:
    pipe_velocity_ftmin: float = 60.0
    acceleration: float = 0.5
    open_end: bool = True
    stand_length: float = 93.0
    clinging_factor: float = 0.45

@dataclass
class SimulationState:
    geometry: WellGeometry = field(default_factory=WellGeometry)
    fluid: FluidProperties = field(default_factory=FluidProperties)
    operating: OperatingParams = field(default_factory=OperatingParams)
    bit: BitParams = field(default_factory=BitParams)
    surge: SurgeSwabParams = field(default_factory=SurgeSwabParams)
    mode: str = "Offline"
    choke_mode: str = "AUTO"
    target_bhp: float = 7500.0
    target_ecd: float = 11.20
    litho_gradient: float = 0.56
    lithology: List[Dict] = field(default_factory=lambda: DEFAULT_LITHOLOGY.copy())
    timeline: List[Dict] = field(default_factory=list)
    activity_log: List[Dict] = field(default_factory=list)
    history_bhp: List[float] = field(default_factory=list)
    history_ecd: List[float] = field(default_factory=list)
    history_spp: List[float] = field(default_factory=list)
    history_flow: List[float] = field(default_factory=list)
    # Results
    bhp: float = 0.0
    ecd: float = 0.0
    model_spp: float = 0.0
    annular_friction: float = 0.0
    pipe_friction: float = 0.0
    bit_pressure_drop: float = 0.0
    hydrostatic: float = 0.0
    live_pp: float = 0.0
    overbalance: float = 0.0
    u_tube_dp: float = 0.0
    effective_flow: float = 0.0
    q_loss: float = 0.0
    q_utube: float = 0.0
    max_surge_psi: float = 0.0
    max_swab_psi: float = 0.0
    esd_surge: float = 0.0
    esd_swab: float = 0.0
    corrected_density: float = 0.0
    current_formation: str = "Burgan"
    delta_flow: float = 0.0
    delta_spp: float = 0.0
    diag_status: str = "OK"
    diag_message: str = ""

def _hydrostatic(density, tvd):
    return 0.052 * density * tvd

def _bit_dp(q, dens, tfa):
    if tfa <= 0: return 0.0
    return (q ** 2 * dens) / (12031.0 * tfa ** 2)

def _annular_velocity(q_gpm, hole_id, pipe_od):
    area = (math.pi / 4.0) * (hole_id**2 - pipe_od**2) / 144.0
    return (q_gpm * 0.133681) / area if area > 0 else 0.0

def _friction_factor(re):
    return 16.0 / max(re, 1.0) if re < 2100 else 0.046 * (re ** -0.2)

def _annular_friction(q, dens, hole_id, pipe_od, length, n, K, rpm=0):
    dh = hole_id - pipe_od
    if dh <= 0 or length <= 0: return 0.0
    v = _annular_velocity(q, hole_id, pipe_od)
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * dh / mu_app
    f = _friction_factor(re)
    return max(f * dens * v**2 * length / (25.8 * dh) * (1.0 + rpm/200.0*0.08), 0.0)

def _pipe_friction(q, dens, pipe_id, length, n, K):
    if pipe_id <= 0 or length <= 0: return 0.0
    area = (math.pi / 4.0) * (pipe_id ** 2) / 144.0
    v = (q * 0.133681) / area if area > 0 else 0
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * pipe_id / mu_app
    f = _friction_factor(re)
    return max(f * dens * v**2 * length / (25.8 * pipe_id), 0.0)

def _temp_corrected_density(base, temp_in, temp_out, tvd, gradient):
    return base * (1.0 - 0.0003 * ((temp_in + (tvd/100.0)*gradient) - 80))

def get_formation_at_depth(lithology, md):
    for layer in lithology:
        if layer["md_top"] <= md <= layer["md_bot"]:
            return layer
    return lithology[-1] if lithology else {"name": "Unknown", "pp_grad": 0.56, "fg_grad": 0.90, "color": "#888"}

def calculate_surge_swab(state):
    s, g, f = state.surge, state.geometry, state.fluid
    v = s.pipe_velocity_ftmin / 60.0
    dh = g.hole_id - g.pipe_od
    if dh <= 0:
        state.max_surge_psi = state.max_swab_psi = 0.0
        return state
    cling = s.clinging_factor if s.open_end else 1.0
    mu = f.pv * 1.2 + f.yp * 0.5
    base = (mu * v * g.md) / (1000.0 * dh**2) * cling * 3.5
    accel = s.acceleration * f.density_ppg * g.md * 0.0015
    state.max_surge_psi = base + accel
    state.max_swab_psi = -(base * 0.9)
    state.esd_surge = state.ecd + (state.max_surge_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    state.esd_swab = state.ecd + (state.max_swab_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    return state

def auto_adjust_sbp_for_cbhp(state):
    if state.choke_mode != "CBHP":
        return state
    error = state.target_bhp - state.bhp
    step = max(-30.0, min(30.0, error * 0.18))
    state.operating.sbp_setpoint = max(0.0, min(1000.0, state.operating.sbp_setpoint + step))
    state.operating.choke_position = max(5.0, min(95.0, 28.0 + state.operating.sbp_setpoint / 9.5))
    return state

def run_diagnostics(state):
    state.delta_flow = state.operating.flow_in_gpm - state.operating.flow_out_gpm
    state.delta_spp = state.operating.spp_measured - state.model_spp
    msgs = []
    status = "OK"
    if abs(state.delta_flow) > 15:
        status = "WARNING"
        msgs.append(f"Flow imbalance ΔQ={state.delta_flow:.1f} gpm (possible loss/gain)")
    elif abs(state.delta_flow) > 5:
        msgs.append(f"Minor flow difference ΔQ={state.delta_flow:.1f} gpm")
    if abs(state.delta_spp) > 150:
        status = "WARNING" if status == "OK" else status
        msgs.append(f"SPP residual {state.delta_spp:+.0f} psi (diagnostic only)")
    elif abs(state.delta_spp) > 50:
        msgs.append(f"SPP residual {state.delta_spp:+.0f} psi")
    if state.overbalance < 100:
        status = "ALERT"
        msgs.append(f"Low overbalance {state.overbalance:.0f} psi")
    state.diag_status = status
    state.diag_message = " | ".join(msgs) if msgs else "All primary parameters within normal range"
    return state

def push_history(state, maxlen=40):
    state.history_bhp.append(state.bhp)
    state.history_ecd.append(state.ecd)
    state.history_spp.append(state.model_spp)
    state.history_flow.append(state.effective_flow)
    state.history_bhp = state.history_bhp[-maxlen:]
    state.history_ecd = state.history_ecd[-maxlen:]
    state.history_spp = state.history_spp[-maxlen:]
    state.history_flow = state.history_flow[-maxlen:]
    return state

def run_hydraulics(state):
    g, f, o, b = state.geometry, state.fluid, state.operating, state.bit
    form = get_formation_at_depth(state.lithology, g.bit_depth)
    state.current_formation = form["name"]
    state.litho_gradient = form.get("pp_grad", 0.56)

    state.corrected_density = _temp_corrected_density(f.density_ppg, f.temp_in, f.temp_out, g.tvd, f.temp_gradient)
    state.q_loss = max(0.0, o.flow_in_gpm - o.flow_out_gpm)
    dens_ann = state.corrected_density + 0.15
    state.u_tube_dp = 0.052 * (dens_ann - state.corrected_density) * g.tvd * 0.15
    state.q_utube = max(0.0, state.u_tube_dp / 8.0)
    state.effective_flow = o.flow_in_gpm + state.q_utube - state.q_loss

    state.hydrostatic = _hydrostatic(state.corrected_density, g.tvd)
    state.bit_pressure_drop = _bit_dp(state.effective_flow, state.corrected_density, b.tfa)
    state.annular_friction = _annular_friction(state.effective_flow, state.corrected_density, g.hole_id, g.pipe_od, g.md, f.n, f.K, o.rpm)
    state.pipe_friction = _pipe_friction(state.effective_flow, state.corrected_density, g.pipe_id, g.md, f.n, f.K)

    state.bhp = state.hydrostatic + state.annular_friction + o.sbp_setpoint
    state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
    state.model_spp = state.pipe_friction + state.bit_pressure_drop + o.sbp_setpoint + state.annular_friction * 0.15

    bit_factor = {"PDC": 1.0, "Diamond Impregnated": 1.05, "Tricone": 0.95}.get(b.bit_type, 1.0)
    rop_factor = 1.0 - (o.rop - 40) * 0.001 if o.rop > 0 else 1.0
    state.live_pp = g.tvd * state.litho_gradient * bit_factor * max(0.9, min(1.1, rop_factor))
    state.overbalance = state.bhp - state.live_pp

    state = calculate_surge_swab(state)

    if state.choke_mode == "CBHP" and state.mode == "Simulation":
        state = auto_adjust_sbp_for_cbhp(state)
        state.bhp = state.hydrostatic + state.annular_friction + state.operating.sbp_setpoint
        state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
        state.overbalance = state.bhp - state.live_pp

    state = run_diagnostics(state)
    state = push_history(state)
    return state

def get_profile_depth_data(state, num_points=16):
    rows = []
    md_step = state.geometry.md / max(num_points - 1, 1)
    for i in range(num_points):
        md = i * md_step
        tvd = md * (state.geometry.tvd / state.geometry.md) if state.geometry.md > 0 else md
        frac = md / state.geometry.md if state.geometry.md > 0 else 0.0
        dens_ann = state.corrected_density + frac * 0.25
        hydro = _hydrostatic(dens_ann, tvd)
        fric = state.annular_friction * frac
        pressure = hydro + fric + state.operating.sbp_setpoint * frac
        ecd = pressure / (0.052 * tvd) if tvd > 1 else 0.0
        form = get_formation_at_depth(state.lithology, md)
        form_temp = state.fluid.ambient_temp + (tvd / 100.0) * state.fluid.temp_gradient
        ann_temp = state.fluid.temp_in + frac * (state.fluid.temp_out - state.fluid.temp_in)
        rows.append({
            "MD_ft": round(md, 0), "TVD_ft": round(tvd, 0), "Formation": form["name"],
            "Formation_Temp_F": round(form_temp, 1), "Annulus_Temp_F": round(ann_temp, 1),
            "Pipe_Temp_F": round(state.fluid.temp_in + frac * 18, 1),
            "Annulus_Density_ppg": round(dens_ann, 2), "Pipe_Density_ppg": round(state.corrected_density, 2),
            "Annulus_Friction_psi": round(fric, 1),
            "Pipe_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.3), 1),
            "Annulus_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.5), 1),
            "Annulus_ECD_ppg": round(ecd, 2), "Annulus_Pressure_psi": round(pressure, 1),
            "Pore_Pressure_psi": round(tvd * form.get("pp_grad", 0.56), 1),
            "Fracture_Pressure_psi": round(tvd * form.get("fg_grad", 0.90), 1),
            "PPG": round(form.get("pp_grad", 0.56) * 19.25, 2), "WBSG_ppg": 0.0, "WBS_psi": 0.0,
        })
    return rows

def add_timeline_event(state, event, details=""):
    state.timeline.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "event": event, "details": details})
    state.timeline = state.timeline[:50]
    return state

def log_activity(state, activity, duration_min=1.0):
    state.activity_log.append({"time": datetime.now().strftime("%H:%M:%S"), "activity": activity, "duration_min": duration_min})
    state.activity_log = state.activity_log[-200:]
    return state

def get_activity_summary(state):
    summary = {}
    for a in state.activity_log:
        summary[a["activity"]] = summary.get(a["activity"], 0.0) + a.get("duration_min", 1.0)
    if not summary:
        summary = {"Drilling": 42, "Connection": 18, "Circulating": 15, "Trip": 12, "Offline": 8, "Other": 5}
    return summary
'''

(ROOT / "engines" / "hydraulics_engine.py").write_text(engine_v6, encoding="utf-8")
print("  ✓ engines/hydraulics_engine.py  (Stage 6 – history buffers)")

# ─────────────────────────────────────────────────────────────
# Stage 6 App – live trends + richer schematic + polish
# ─────────────────────────────────────────────────────────────
app_v6 = r'''"""
ARHPP Main Application – Stage 6
Live trends from history + richer schematic + UI polish
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import APP_NAME, APP_VERSION, APP_SUBTITLE
from engines.hydraulics_engine import (
    SimulationState, run_hydraulics, get_profile_depth_data,
    add_timeline_event, log_activity, get_activity_summary
)

st.set_page_config(page_title=APP_NAME, page_icon="🛢️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #1a1d23; color: #d0d0d0; }
    section[data-testid="stSidebar"] { background-color: #12151a; }
    div[data-testid="stMetricValue"] { color: #00d4aa; font-size: 1.3rem; }
    .block-container { padding-top: 0.45rem; padding-bottom: 0.25rem; }
    h1, h2, h3, h4 { color: #e8e8e8 !important; }
</style>
""", unsafe_allow_html=True)

if "state" not in st.session_state:
    st.session_state.state = run_hydraulics(SimulationState())
if "app_name" not in st.session_state:
    st.session_state.app_name = APP_NAME

state = st.session_state.state

# Top bar
c1, c2, c3, c4 = st.columns([0.5, 3.6, 1.5, 1.2])
with c1:
    st.markdown("### 🛢️")
with c2:
    st.markdown(f"## {st.session_state.app_name} <span style='font-size:12px;color:#888'>{APP_VERSION}</span>", unsafe_allow_html=True)
with c3:
    st.caption(f"Bit: {state.geometry.bit_depth:.0f} ft | {state.current_formation}")
with c4:
    mode_color = {"Offline": "#ffaa00", "Simulation": "#00d4aa", "Live": "#00ff88"}.get(state.mode, "#ffaa00")
    st.markdown(f"<div style='text-align:right;padding-top:10px'><span style='background:{mode_color};color:#111;padding:4px 12px;border-radius:4px;font-weight:700;font-size:12px'>{state.mode.upper()}</span></div>", unsafe_allow_html=True)

# Status bar
status_color = {"OK": "#00d4aa", "WARNING": "#ffaa00", "ALERT": "#ff5555"}.get(state.diag_status, "#888")
st.markdown(f"""
<div style="background:#252a33;padding:6px 12px;border-radius:4px;border-left:4px solid {status_color};margin-bottom:8px;font-size:13px">
<b style="color:{status_color}">{state.diag_status}</b> &nbsp;|&nbsp; {state.diag_message}
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"**{st.session_state.app_name}**")
    nav = st.radio("Modules", [
        "Profile Depth Data", "MPD Gauges", "Main Time Data",
        "Surge & Swab", "Choke Control", "Actual vs Model",
        "Timeline", "Performance", "Engineering", "Settings"
    ], index=0)
    st.markdown("---")
    st.markdown("**Quick Setpoints**")
    state.mode = st.selectbox("Mode", ["Offline", "Simulation", "Live"],
                              index=["Offline", "Simulation", "Live"].index(state.mode))
    state.choke_mode = st.selectbox("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode))
    state.operating.sbp_setpoint = st.slider("SBP (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    state.operating.flow_in_gpm = st.number_input("Flow In (gpm)", 0.0, 2000.0, float(state.operating.flow_in_gpm), 10.0)
    state.operating.flow_out_gpm = st.number_input("Flow Out (gpm)", 0.0, 2000.0, float(state.operating.flow_out_gpm), 5.0)
    state.operating.spp_measured = st.number_input("SPP Measured (psi)", 0.0, 6000.0, float(state.operating.spp_measured), 10.0)
    state.operating.choke_position = st.slider("Choke %", 0, 100, int(state.operating.choke_position), 1)

    # Live Simulation step
    if state.mode == "Simulation":
        if st.button("▶ Step Simulation", use_container_width=True):
            # small random-ish variation for demo liveliness
            import random
            state.operating.flow_out_gpm = max(0, state.operating.flow_in_gpm - random.uniform(2, 12))
            st.session_state.state = run_hydraulics(state)
            st.session_state.state = log_activity(st.session_state.state, "Drilling", 0.5)
            st.rerun()

    if st.button("⟳ Recalculate", use_container_width=True, type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Recalculate", f"SBP={state.operating.sbp_setpoint:.0f}")
        st.session_state.state = log_activity(st.session_state.state, "Circulating", 2.0)
        st.rerun()

# ── Pages ──
if nav == "Profile Depth Data":
    gcols = st.columns(7)
    for col, (label, val, unit, delta) in zip(gcols, [
        ("BHP", f"{state.bhp:.0f}", "psi", f"Tgt {state.target_bhp:.0f}"),
        ("ECD", f"{state.ecd:.2f}", "ppg", f"Tgt {state.target_ecd:.2f}"),
        ("Model SPP", f"{state.model_spp:.0f}", "psi", None),
        ("SBP", f"{state.operating.sbp_setpoint:.0f}", "psi", None),
        ("Flow In", f"{state.operating.flow_in_gpm:.0f}", "gpm", None),
        ("Live PP", f"{state.live_pp:.0f}", "psi", f"OB {state.overbalance:.0f}"),
        ("Eff. Flow", f"{state.effective_flow:.0f}", "gpm", None),
    ]):
        col.metric(label, f"{val} {unit}", delta)

    left, right = st.columns([3.1, 1.2])
    with left:
        df = pd.DataFrame(get_profile_depth_data(state, 18))
        display_df = df.rename(columns={
            "MD_ft": "MD", "TVD_ft": "TVD", "Formation": "Form",
            "Formation_Temp_F": "Form.T", "Annulus_Temp_F": "Ann.T",
            "Pipe_Temp_F": "Pipe.T", "Annulus_Density_ppg": "Ann.Dens",
            "Pipe_Density_ppg": "Pipe.Dens", "Annulus_Friction_psi": "Ann.Fric",
            "Pipe_App_Visc_cP": "Pipe.Visc", "Annulus_App_Visc_cP": "Ann.Visc",
            "Annulus_ECD_ppg": "Ann.ECD", "Annulus_Pressure_psi": "Ann.P",
            "Pore_Pressure_psi": "PP", "Fracture_Pressure_psi": "FG",
            "PPG": "PPG", "WBSG_ppg": "WBSG", "WBS_psi": "WBS"
        })
        st.dataframe(display_df, use_container_width=True, height=390)

    with right:
        st.markdown("**Well Schematic + Lithology**")
        fig = go.Figure()
        total_md = max(state.geometry.md, 1)
        for layer in state.lithology:
            y0 = (layer["md_top"] / total_md) * 100
            y1 = min((layer["md_bot"] / total_md) * 100, 100)
            if y0 > 100: continue
            fig.add_shape(type="rect", x0=0.18, x1=0.82, y0=y0, y1=y1,
                          fillcolor=layer["color"], opacity=0.88, line=dict(color="#1a1d23", width=0.6))
            if y1 - y0 > 3.5:
                fig.add_annotation(x=0.5, y=(y0+y1)/2, text=layer["name"], showarrow=False,
                                   font=dict(size=9, color="#111"))
        # casing shoe marker
        shoe_y = (state.geometry.shoe_depth / total_md) * 100
        fig.add_shape(type="line", x0=0.05, x1=0.95, y0=shoe_y, y1=shoe_y,
                      line=dict(color="#ffaa00", width=2, dash="dot"))
        # bit
        bit_y = (state.geometry.bit_depth / total_md) * 100
        fig.add_shape(type="rect", x0=0.08, x1=0.92, y0=bit_y-1.3, y1=bit_y+1.3,
                      fillcolor="#00d4aa", line=dict(width=0))
        fig.update_layout(height=360, margin=dict(l=5,r=5,t=5,b=5),
                          paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
                          xaxis=dict(visible=False, range=[0,1]),
                          yaxis=dict(range=[100,0], color="#718096", gridcolor="#2d3748", tickfont=dict(size=9)))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<small>**{state.current_formation}** | Bit {state.geometry.bit_depth:.0f} ft<br>Shoe {state.geometry.shoe_depth:.0f} ft | Choke {state.operating.choke_position:.0f}% ({state.choke_mode})</small>", unsafe_allow_html=True)

elif nav == "Main Time Data":
    st.subheader("Main Time Data – Live Trends")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    m2.metric("Q Loss", f"{state.q_loss:.1f} gpm")
    m3.metric("Q U-Tube", f"{state.q_utube:.1f} gpm")
    m4.metric("Annular Friction", f"{state.annular_friction:.0f} psi")

    # History trends
    if len(state.history_bhp) > 2:
        fig = go.Figure()
        x = list(range(len(state.history_bhp)))
        fig.add_trace(go.Scatter(x=x, y=state.history_bhp, name="BHP", line=dict(color="#00d4aa", width=2)))
        fig.add_trace(go.Scatter(x=x, y=state.history_spp, name="Model SPP", line=dict(color="#4a9eff", width=2)))
        fig.add_trace(go.Scatter(x=x, y=[e*100 for e in state.history_ecd], name="ECD×100", line=dict(color="#ffaa00", width=2)))
        fig.update_layout(paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"),
                          height=320, margin=dict(t=20, b=30), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Press **Step Simulation** or **Recalculate** a few times to build live trend history.")

    st.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    st.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    st.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    st.metric("Current Formation", state.current_formation)

elif nav == "Actual vs Model":
    st.subheader("Actual vs Model Diagnostics")
    st.caption("Primary drivers: Flow In/Out + Density + Temperature. SPP is secondary diagnostic only.")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Flow In (Actual)", f"{state.operating.flow_in_gpm:.1f} gpm")
    d2.metric("Flow Out (Actual)", f"{state.operating.flow_out_gpm:.1f} gpm")
    d3.metric("ΔQ (In−Out)", f"{state.delta_flow:.1f} gpm")
    d4.metric("Q Loss (model)", f"{state.q_loss:.1f} gpm")
    st.markdown("---")
    s1, s2, s3 = st.columns(3)
    s1.metric("SPP Measured", f"{state.operating.spp_measured:.0f} psi")
    s2.metric("SPP Model", f"{state.model_spp:.0f} psi")
    s3.metric("Δ SPP (Meas−Model)", f"{state.delta_spp:+.0f} psi")
    st.markdown(f"**Status: {state.diag_status}**")
    st.info(state.diag_message)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Measured / Actual", x=["Flow In", "SPP"], y=[state.operating.flow_in_gpm, state.operating.spp_measured], marker_color="#4a9eff"))
    fig.add_trace(go.Bar(name="Model", x=["Flow In", "SPP"], y=[state.operating.flow_in_gpm, state.model_spp], marker_color="#00d4aa"))
    fig.update_layout(barmode="group", paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
                      font=dict(color="#ccc"), height=280, margin=dict(t=20, b=40))
    st.plotly_chart(fig, use_container_width=True)
    st.warning("SPP difference is diagnostic only and does NOT drive pressure calculations.")

elif nav == "Performance":
    st.subheader("Performance – Well Activities")
    summary = get_activity_summary(state)
    fig_pie = px.pie(names=list(summary.keys()), values=list(summary.values()),
                     color_discrete_sequence=px.colors.qualitative.Set2, hole=0.35)
    fig_pie.update_layout(paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"), height=340, margin=dict(t=30,b=20,l=20,r=20))
    col_p1, col_p2 = st.columns([1.4, 1])
    with col_p1:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_p2:
        st.markdown("**Activity Summary (minutes)**")
        for k, v in sorted(summary.items(), key=lambda x: -x[1]):
            st.write(f"• **{k}**: {v:.0f} min")
        act = st.selectbox("Activity type", ["Drilling", "Connection", "Circulating", "Trip", "Offline", "Other"])
        dur = st.number_input("Duration (min)", 0.5, 120.0, 5.0, 0.5)
        if st.button("Add Activity"):
            st.session_state.state = log_activity(state, act, dur)
            st.session_state.state = add_timeline_event(st.session_state.state, f"Activity: {act}", f"{dur} min")
            st.rerun()

elif nav == "Engineering":
    st.subheader("Engineering – Hydraulics Summary")
    e1, e2, e3 = st.columns(3)
    e1.metric("Hydrostatic", f"{state.hydrostatic:.0f} psi")
    e1.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    e1.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    e2.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    e2.metric("U-Tube ΔP", f"{state.u_tube_dp:.0f} psi")
    e2.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    e3.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    e3.metric("Live PP Gradient", f"{state.litho_gradient:.3f} psi/ft")
    e3.metric("Overbalance", f"{state.overbalance:.0f} psi")
    budget = {"Hydrostatic": state.hydrostatic, "Annular Friction": state.annular_friction, "SBP": state.operating.sbp_setpoint}
    fig_bar = go.Figure(go.Bar(x=list(budget.keys()), y=list(budget.values()), marker_color=["#4a9eff", "#00d4aa", "#ffaa00"]))
    fig_bar.update_layout(paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"), height=250, yaxis_title="psi", margin=dict(t=20,b=40))
    st.plotly_chart(fig_bar, use_container_width=True)

elif nav == "Timeline":
    st.subheader("Timeline / Feedback")
    ec1, ec2 = st.columns([3, 1])
    with ec1:
        new_event = st.text_input("Add event comment", placeholder="Connection, Pump up, Gas show...")
    with ec2:
        st.write(""); st.write("")
        if st.button("Add to Timeline", use_container_width=True) and new_event.strip():
            st.session_state.state = add_timeline_event(state, new_event.strip())
            st.rerun()
    if state.timeline:
        st.dataframe(pd.DataFrame(state.timeline), use_container_width=True, height=340)
    else:
        st.info("No events yet.")

elif nav == "Surge & Swab":
    st.subheader("Surge & Swab Calculator")
    sc1, sc2 = st.columns(2)
    with sc1:
        state.surge.pipe_velocity_ftmin = st.slider("Pipe Velocity (ft/min)", 5, 150, int(state.surge.pipe_velocity_ftmin))
        state.surge.acceleration = st.number_input("Acceleration (ft/s²)", 0.0, 3.0, float(state.surge.acceleration), 0.1)
        state.surge.open_end = st.checkbox("Open Ended", value=state.surge.open_end)
        state.surge.clinging_factor = st.slider("Clinging Factor", 0.1, 1.0, float(state.surge.clinging_factor), 0.05)
        if st.button("Calculate Surge/Swab", type="primary"):
            st.session_state.state = run_hydraulics(state)
            st.session_state.state = add_timeline_event(st.session_state.state, "Surge/Swab", f"Vel={state.surge.pipe_velocity_ftmin}")
            st.session_state.state = log_activity(st.session_state.state, "Trip", 3.0)
            st.rerun()
    with sc2:
        st.metric("Max Surge", f"{state.max_surge_psi:.0f} psi")
        st.metric("Max Swab", f"{state.max_swab_psi:.0f} psi")
        st.metric("ESD Surge", f"{state.esd_surge:.2f} ppg")
        st.metric("ESD Swab", f"{state.esd_swab:.2f} ppg")
        st.metric("BHP @ Surge", f"{state.bhp + state.max_surge_psi:.0f} psi")
        st.metric("BHP @ Swab", f"{state.bhp + state.max_swab_psi:.0f} psi")

elif nav == "Choke Control":
    st.subheader("Choke Control Panel")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        state.choke_mode = st.radio("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode), horizontal=True)
    with cc2:
        if state.choke_mode == "CBHP":
            state.target_bhp = st.number_input("Target BHP (psi)", 0.0, 15000.0, float(state.target_bhp), 10.0)
        elif state.choke_mode == "AUTO":
            state.target_ecd = st.number_input("Target ECD (ppg)", 8.0, 18.0, float(state.target_ecd), 0.05)
        state.operating.sbp_setpoint = st.slider("SBP Setpoint (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    with cc3:
        st.metric("Choke Position", f"{state.operating.choke_position:.0f} %")
        st.metric("Current SBP", f"{state.operating.sbp_setpoint:.0f} psi")
        st.metric("Current BHP", f"{state.bhp:.0f} psi")
        st.metric("Current ECD", f"{state.ecd:.2f} ppg")
    if st.button("Apply Setpoint & Recalculate", type="primary", use_container_width=True):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Choke Apply", f"{state.choke_mode} SBP={state.operating.sbp_setpoint:.0f}")
        st.rerun()
    if state.choke_mode == "CBHP":
        st.success("CBHP Auto active in Simulation mode → SBP adjusts to hold Target BHP.")

elif nav == "MPD Gauges":
    st.subheader("MPD Gauges")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("BHP", f"{state.bhp:.0f} psi", f"{state.bhp - state.target_bhp:+.0f}")
    g2.metric("ECD", f"{state.ecd:.2f} ppg", f"{state.ecd - state.target_ecd:+.2f}")
    g3.metric("SBP", f"{state.operating.sbp_setpoint:.0f} psi")
    g4.metric("Overbalance", f"{state.overbalance:.0f} psi")
    if len(state.history_bhp) > 2:
        st.line_chart({"BHP": state.history_bhp, "ECD×100": [e*100 for e in state.history_ecd]})
    else:
        st.line_chart({"BHP": [state.bhp-40, state.bhp-15, state.bhp, state.bhp+8, state.bhp-5],
                       "ECD x100": [(state.ecd-0.08)*100, (state.ecd-0.03)*100, state.ecd*100, (state.ecd+0.02)*100, state.ecd*100]})

elif nav == "Settings":
    st.subheader("Settings")
    new_name = st.text_input("Application Display Name", value=st.session_state.app_name)
    if st.button("Update Name"):
        st.session_state.app_name = new_name
        st.success(f"Name set to: {new_name}")
        st.rerun()
    st.markdown("---")
    st.markdown("**Well Geometry**")
    state.geometry.md = st.number_input("Total MD (ft)", value=float(state.geometry.md))
    state.geometry.tvd = st.number_input("TVD (ft)", value=float(state.geometry.tvd))
    state.geometry.hole_id = st.number_input("Hole ID (in)", value=float(state.geometry.hole_id))
    state.geometry.pipe_od = st.number_input("Pipe OD (in)", value=float(state.geometry.pipe_od))
    state.geometry.bit_depth = st.number_input("Bit Depth (ft)", value=float(state.geometry.bit_depth))
    state.geometry.shoe_depth = st.number_input("Casing Shoe (ft)", value=float(state.geometry.shoe_depth))
    st.markdown("**Fluid**")
    state.fluid.density_ppg = st.number_input("Mud Density (ppg)", value=float(state.fluid.density_ppg))
    state.fluid.temp_in = st.number_input("Mud Temp In (°F)", value=float(state.fluid.temp_in))
    state.fluid.temp_out = st.number_input("Mud Temp Out (°F)", value=float(state.fluid.temp_out))
    state.fluid.n = st.number_input("n (HB)", value=float(state.fluid.n), format="%.3f")
    state.fluid.K = st.number_input("K (HB)", value=float(state.fluid.K), format="%.3f")
    st.markdown("**Bit**")
    state.bit.bit_type = st.selectbox("Bit Type", ["PDC", "Diamond Impregnated", "Tricone"])
    state.bit.tfa = st.number_input("TFA (in²)", value=float(state.bit.tfa), format="%.3f")
    if st.button("Apply All & Recalculate", type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Settings Applied")
        st.rerun()

else:
    st.subheader(nav)
    st.info(f"Module **{nav}** ready.")

st.markdown("<hr style='border-color:#333'>", unsafe_allow_html=True)
st.caption(f"{st.session_state.app_name} | Stage 6 | Live trends + Schematic polish | Excel v4 physics | SPP diagnostic only")
'''

(ROOT / "app.py").write_text(app_v6, encoding="utf-8")
print("  ✓ app.py  (Stage 6 – live trends + schematic polish)")

readme6 = '''# ARHPP Digital Twin – Stage 6

## التشغيل
```bash
cd ARHPP_App
pip install -r requirements.txt
streamlit run app.py
```

## ما أُضيف في Stage 6
- History buffers لـ BHP / ECD / SPP / Flow → رسوم اتجاهية حية في Main Time Data و MPD Gauges
- زر **Step Simulation** في وضع Simulation (يحاكي تغيراً بسيطاً في Flow Out)
- Well Schematic أغنى (علامة Casing Shoe + طبقات أوضح)
- تلميع عام للواجهة

## الملف المتراكم
build_arhpp_full.py = المراحل 1 → 6
'''
(ROOT / "README.md").write_text(readme6, encoding="utf-8")
print("  ✓ README.md updated")

print()
print("=" * 60)
print("✅ Stage 6 completed successfully!")
print("  cd ARHPP_App && streamlit run app.py")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# STAGE 7 – Save/Load state + UI polish closer to Victus
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("ARHPP Full Application Builder – Stage 7")
print("Save/Load well state + UI polish...")
print("=" * 60)

# ─────────────────────────────────────────────────────────────
# Stage 7 Engine – add serialization helpers
# ─────────────────────────────────────────────────────────────
engine_v7 = r'''"""
ARHPP Hydraulics Engine – Stage 7
+ Save / Load state (JSON)
+ All previous features
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from datetime import datetime
import math
import json

DEFAULT_LITHOLOGY = [
    {"name": "Dammam",   "md_top": 0,     "md_bot": 800,   "color": "#c4a574", "pp_grad": 0.45, "fg_grad": 0.85},
    {"name": "Rus",      "md_top": 800,   "md_bot": 1400,  "color": "#e8d5b7", "pp_grad": 0.46, "fg_grad": 0.90},
    {"name": "Radhuma",  "md_top": 1400,  "md_bot": 2800,  "color": "#d4b896", "pp_grad": 0.47, "fg_grad": 0.88},
    {"name": "Tayarat",  "md_top": 2800,  "md_bot": 4200,  "color": "#8b7355", "pp_grad": 0.48, "fg_grad": 0.87},
    {"name": "Hartha",   "md_top": 4200,  "md_bot": 5500,  "color": "#a0896c", "pp_grad": 0.49, "fg_grad": 0.89},
    {"name": "Sadi",     "md_top": 5500,  "md_bot": 6200,  "color": "#6b5344", "pp_grad": 0.50, "fg_grad": 0.86},
    {"name": "Mutriba",  "md_top": 6200,  "md_bot": 7000,  "color": "#9c8b7a", "pp_grad": 0.51, "fg_grad": 0.90},
    {"name": "Mishrif",  "md_top": 7000,  "md_bot": 8200,  "color": "#b89b72", "pp_grad": 0.52, "fg_grad": 0.92},
    {"name": "Rumaila",  "md_top": 8200,  "md_bot": 9500,  "color": "#a67c52", "pp_grad": 0.53, "fg_grad": 0.93},
    {"name": "Ahmadi",   "md_top": 9500,  "md_bot": 10500, "color": "#7d6b5a", "pp_grad": 0.54, "fg_grad": 0.91},
    {"name": "Wara",     "md_top": 10500, "md_bot": 11200, "color": "#c2b280", "pp_grad": 0.55, "fg_grad": 0.90},
    {"name": "Burgan",   "md_top": 11200, "md_bot": 13000, "color": "#d2b48c", "pp_grad": 0.56, "fg_grad": 0.88},
]

@dataclass
class WellGeometry:
    md: float = 12000.0
    tvd: float = 11200.0
    hole_id: float = 8.5
    pipe_od: float = 5.0
    pipe_id: float = 4.276
    casing_od: float = 9.625
    bit_depth: float = 12000.0
    shoe_depth: float = 9410.0

@dataclass
class FluidProperties:
    density_ppg: float = 10.5
    pv: float = 28.0
    yp: float = 18.0
    n: float = 0.72
    K: float = 0.45
    tau_y: float = 6.5
    temp_in: float = 120.0
    temp_out: float = 155.0
    ambient_temp: float = 95.0
    temp_gradient: float = 1.5

@dataclass
class OperatingParams:
    flow_in_gpm: float = 850.0
    flow_out_gpm: float = 845.0
    sbp_setpoint: float = 200.0
    choke_position: float = 42.0
    rpm: float = 120.0
    wob: float = 25.0
    rop: float = 45.0
    spp_measured: float = 2850.0
    pump_efficiency: float = 0.97

@dataclass
class BitParams:
    bit_type: str = "PDC"
    tfa: float = 0.85
    bit_size: float = 8.5
    nozzles: str = "16/16/16/16/14/14"

@dataclass
class SurgeSwabParams:
    pipe_velocity_ftmin: float = 60.0
    acceleration: float = 0.5
    open_end: bool = True
    stand_length: float = 93.0
    clinging_factor: float = 0.45

@dataclass
class SimulationState:
    geometry: WellGeometry = field(default_factory=WellGeometry)
    fluid: FluidProperties = field(default_factory=FluidProperties)
    operating: OperatingParams = field(default_factory=OperatingParams)
    bit: BitParams = field(default_factory=BitParams)
    surge: SurgeSwabParams = field(default_factory=SurgeSwabParams)
    mode: str = "Offline"
    choke_mode: str = "AUTO"
    target_bhp: float = 7500.0
    target_ecd: float = 11.20
    litho_gradient: float = 0.56
    lithology: List[Dict] = field(default_factory=lambda: DEFAULT_LITHOLOGY.copy())
    timeline: List[Dict] = field(default_factory=list)
    activity_log: List[Dict] = field(default_factory=list)
    history_bhp: List[float] = field(default_factory=list)
    history_ecd: List[float] = field(default_factory=list)
    history_spp: List[float] = field(default_factory=list)
    history_flow: List[float] = field(default_factory=list)
    bhp: float = 0.0
    ecd: float = 0.0
    model_spp: float = 0.0
    annular_friction: float = 0.0
    pipe_friction: float = 0.0
    bit_pressure_drop: float = 0.0
    hydrostatic: float = 0.0
    live_pp: float = 0.0
    overbalance: float = 0.0
    u_tube_dp: float = 0.0
    effective_flow: float = 0.0
    q_loss: float = 0.0
    q_utube: float = 0.0
    max_surge_psi: float = 0.0
    max_swab_psi: float = 0.0
    esd_surge: float = 0.0
    esd_swab: float = 0.0
    corrected_density: float = 0.0
    current_formation: str = "Burgan"
    delta_flow: float = 0.0
    delta_spp: float = 0.0
    diag_status: str = "OK"
    diag_message: str = ""

def _hydrostatic(density, tvd):
    return 0.052 * density * tvd

def _bit_dp(q, dens, tfa):
    if tfa <= 0: return 0.0
    return (q ** 2 * dens) / (12031.0 * tfa ** 2)

def _annular_velocity(q_gpm, hole_id, pipe_od):
    area = (math.pi / 4.0) * (hole_id**2 - pipe_od**2) / 144.0
    return (q_gpm * 0.133681) / area if area > 0 else 0.0

def _friction_factor(re):
    return 16.0 / max(re, 1.0) if re < 2100 else 0.046 * (re ** -0.2)

def _annular_friction(q, dens, hole_id, pipe_od, length, n, K, rpm=0):
    dh = hole_id - pipe_od
    if dh <= 0 or length <= 0: return 0.0
    v = _annular_velocity(q, hole_id, pipe_od)
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * dh / mu_app
    f = _friction_factor(re)
    return max(f * dens * v**2 * length / (25.8 * dh) * (1.0 + rpm/200.0*0.08), 0.0)

def _pipe_friction(q, dens, pipe_id, length, n, K):
    if pipe_id <= 0 or length <= 0: return 0.0
    area = (math.pi / 4.0) * (pipe_id ** 2) / 144.0
    v = (q * 0.133681) / area if area > 0 else 0
    mu_app = K * 100.0 * (v ** (n - 1)) + 1e-6 if v > 0 else K * 100
    re = 928.0 * dens * v * pipe_id / mu_app
    f = _friction_factor(re)
    return max(f * dens * v**2 * length / (25.8 * pipe_id), 0.0)

def _temp_corrected_density(base, temp_in, temp_out, tvd, gradient):
    return base * (1.0 - 0.0003 * ((temp_in + (tvd/100.0)*gradient) - 80))

def get_formation_at_depth(lithology, md):
    for layer in lithology:
        if layer["md_top"] <= md <= layer["md_bot"]:
            return layer
    return lithology[-1] if lithology else {"name": "Unknown", "pp_grad": 0.56, "fg_grad": 0.90, "color": "#888"}

def calculate_surge_swab(state):
    s, g, f = state.surge, state.geometry, state.fluid
    v = s.pipe_velocity_ftmin / 60.0
    dh = g.hole_id - g.pipe_od
    if dh <= 0:
        state.max_surge_psi = state.max_swab_psi = 0.0
        return state
    cling = s.clinging_factor if s.open_end else 1.0
    mu = f.pv * 1.2 + f.yp * 0.5
    base = (mu * v * g.md) / (1000.0 * dh**2) * cling * 3.5
    accel = s.acceleration * f.density_ppg * g.md * 0.0015
    state.max_surge_psi = base + accel
    state.max_swab_psi = -(base * 0.9)
    state.esd_surge = state.ecd + (state.max_surge_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    state.esd_swab = state.ecd + (state.max_swab_psi / (0.052 * g.tvd)) if g.tvd > 0 else state.ecd
    return state

def auto_adjust_sbp_for_cbhp(state):
    if state.choke_mode != "CBHP":
        return state
    error = state.target_bhp - state.bhp
    step = max(-30.0, min(30.0, error * 0.18))
    state.operating.sbp_setpoint = max(0.0, min(1000.0, state.operating.sbp_setpoint + step))
    state.operating.choke_position = max(5.0, min(95.0, 28.0 + state.operating.sbp_setpoint / 9.5))
    return state

def run_diagnostics(state):
    state.delta_flow = state.operating.flow_in_gpm - state.operating.flow_out_gpm
    state.delta_spp = state.operating.spp_measured - state.model_spp
    msgs = []
    status = "OK"
    if abs(state.delta_flow) > 15:
        status = "WARNING"
        msgs.append(f"Flow imbalance ΔQ={state.delta_flow:.1f} gpm (possible loss/gain)")
    elif abs(state.delta_flow) > 5:
        msgs.append(f"Minor flow difference ΔQ={state.delta_flow:.1f} gpm")
    if abs(state.delta_spp) > 150:
        status = "WARNING" if status == "OK" else status
        msgs.append(f"SPP residual {state.delta_spp:+.0f} psi (diagnostic only)")
    elif abs(state.delta_spp) > 50:
        msgs.append(f"SPP residual {state.delta_spp:+.0f} psi")
    if state.overbalance < 100:
        status = "ALERT"
        msgs.append(f"Low overbalance {state.overbalance:.0f} psi")
    state.diag_status = status
    state.diag_message = " | ".join(msgs) if msgs else "All primary parameters within normal range"
    return state

def push_history(state, maxlen=40):
    state.history_bhp.append(state.bhp)
    state.history_ecd.append(state.ecd)
    state.history_spp.append(state.model_spp)
    state.history_flow.append(state.effective_flow)
    state.history_bhp = state.history_bhp[-maxlen:]
    state.history_ecd = state.history_ecd[-maxlen:]
    state.history_spp = state.history_spp[-maxlen:]
    state.history_flow = state.history_flow[-maxlen:]
    return state

def run_hydraulics(state):
    g, f, o, b = state.geometry, state.fluid, state.operating, state.bit
    form = get_formation_at_depth(state.lithology, g.bit_depth)
    state.current_formation = form["name"]
    state.litho_gradient = form.get("pp_grad", 0.56)

    state.corrected_density = _temp_corrected_density(f.density_ppg, f.temp_in, f.temp_out, g.tvd, f.temp_gradient)
    state.q_loss = max(0.0, o.flow_in_gpm - o.flow_out_gpm)
    dens_ann = state.corrected_density + 0.15
    state.u_tube_dp = 0.052 * (dens_ann - state.corrected_density) * g.tvd * 0.15
    state.q_utube = max(0.0, state.u_tube_dp / 8.0)
    state.effective_flow = o.flow_in_gpm + state.q_utube - state.q_loss

    state.hydrostatic = _hydrostatic(state.corrected_density, g.tvd)
    state.bit_pressure_drop = _bit_dp(state.effective_flow, state.corrected_density, b.tfa)
    state.annular_friction = _annular_friction(state.effective_flow, state.corrected_density, g.hole_id, g.pipe_od, g.md, f.n, f.K, o.rpm)
    state.pipe_friction = _pipe_friction(state.effective_flow, state.corrected_density, g.pipe_id, g.md, f.n, f.K)

    state.bhp = state.hydrostatic + state.annular_friction + o.sbp_setpoint
    state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
    state.model_spp = state.pipe_friction + state.bit_pressure_drop + o.sbp_setpoint + state.annular_friction * 0.15

    bit_factor = {"PDC": 1.0, "Diamond Impregnated": 1.05, "Tricone": 0.95}.get(b.bit_type, 1.0)
    rop_factor = 1.0 - (o.rop - 40) * 0.001 if o.rop > 0 else 1.0
    state.live_pp = g.tvd * state.litho_gradient * bit_factor * max(0.9, min(1.1, rop_factor))
    state.overbalance = state.bhp - state.live_pp

    state = calculate_surge_swab(state)

    if state.choke_mode == "CBHP" and state.mode == "Simulation":
        state = auto_adjust_sbp_for_cbhp(state)
        state.bhp = state.hydrostatic + state.annular_friction + state.operating.sbp_setpoint
        state.ecd = state.bhp / (0.052 * g.tvd) if g.tvd > 0 else 0.0
        state.overbalance = state.bhp - state.live_pp

    state = run_diagnostics(state)
    state = push_history(state)
    return state

def get_profile_depth_data(state, num_points=16):
    rows = []
    md_step = state.geometry.md / max(num_points - 1, 1)
    for i in range(num_points):
        md = i * md_step
        tvd = md * (state.geometry.tvd / state.geometry.md) if state.geometry.md > 0 else md
        frac = md / state.geometry.md if state.geometry.md > 0 else 0.0
        dens_ann = state.corrected_density + frac * 0.25
        hydro = _hydrostatic(dens_ann, tvd)
        fric = state.annular_friction * frac
        pressure = hydro + fric + state.operating.sbp_setpoint * frac
        ecd = pressure / (0.052 * tvd) if tvd > 1 else 0.0
        form = get_formation_at_depth(state.lithology, md)
        form_temp = state.fluid.ambient_temp + (tvd / 100.0) * state.fluid.temp_gradient
        ann_temp = state.fluid.temp_in + frac * (state.fluid.temp_out - state.fluid.temp_in)
        rows.append({
            "MD_ft": round(md, 0), "TVD_ft": round(tvd, 0), "Formation": form["name"],
            "Formation_Temp_F": round(form_temp, 1), "Annulus_Temp_F": round(ann_temp, 1),
            "Pipe_Temp_F": round(state.fluid.temp_in + frac * 18, 1),
            "Annulus_Density_ppg": round(dens_ann, 2), "Pipe_Density_ppg": round(state.corrected_density, 2),
            "Annulus_Friction_psi": round(fric, 1),
            "Pipe_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.3), 1),
            "Annulus_App_Visc_cP": round(state.fluid.pv * (1 + frac * 0.5), 1),
            "Annulus_ECD_ppg": round(ecd, 2), "Annulus_Pressure_psi": round(pressure, 1),
            "Pore_Pressure_psi": round(tvd * form.get("pp_grad", 0.56), 1),
            "Fracture_Pressure_psi": round(tvd * form.get("fg_grad", 0.90), 1),
            "PPG": round(form.get("pp_grad", 0.56) * 19.25, 2), "WBSG_ppg": 0.0, "WBS_psi": 0.0,
        })
    return rows

def add_timeline_event(state, event, details=""):
    state.timeline.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "event": event, "details": details})
    state.timeline = state.timeline[:50]
    return state

def log_activity(state, activity, duration_min=1.0):
    state.activity_log.append({"time": datetime.now().strftime("%H:%M:%S"), "activity": activity, "duration_min": duration_min})
    state.activity_log = state.activity_log[-200:]
    return state

def get_activity_summary(state):
    summary = {}
    for a in state.activity_log:
        summary[a["activity"]] = summary.get(a["activity"], 0.0) + a.get("duration_min", 1.0)
    if not summary:
        summary = {"Drilling": 42, "Connection": 18, "Circulating": 15, "Trip": 12, "Offline": 8, "Other": 5}
    return summary

def state_to_dict(state: SimulationState) -> Dict[str, Any]:
    """Serialize state for Save"""
    return {
        "geometry": asdict(state.geometry),
        "fluid": asdict(state.fluid),
        "operating": asdict(state.operating),
        "bit": asdict(state.bit),
        "surge": asdict(state.surge),
        "mode": state.mode,
        "choke_mode": state.choke_mode,
        "target_bhp": state.target_bhp,
        "target_ecd": state.target_ecd,
        "litho_gradient": state.litho_gradient,
        "lithology": state.lithology,
        "timeline": state.timeline[:20],
        "activity_log": state.activity_log[-50:],
    }

def dict_to_state(data: Dict[str, Any]) -> SimulationState:
    """Deserialize state for Load"""
    state = SimulationState()
    if "geometry" in data:
        state.geometry = WellGeometry(**data["geometry"])
    if "fluid" in data:
        state.fluid = FluidProperties(**data["fluid"])
    if "operating" in data:
        state.operating = OperatingParams(**data["operating"])
    if "bit" in data:
        state.bit = BitParams(**data["bit"])
    if "surge" in data:
        state.surge = SurgeSwabParams(**data["surge"])
    state.mode = data.get("mode", "Offline")
    state.choke_mode = data.get("choke_mode", "AUTO")
    state.target_bhp = data.get("target_bhp", 7500.0)
    state.target_ecd = data.get("target_ecd", 11.20)
    state.litho_gradient = data.get("litho_gradient", 0.56)
    state.lithology = data.get("lithology", DEFAULT_LITHOLOGY.copy())
    state.timeline = data.get("timeline", [])
    state.activity_log = data.get("activity_log", [])
    return run_hydraulics(state)

def save_state_json(state: SimulationState, path: str = "data/well_state.json") -> str:
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state_to_dict(state), indent=2), encoding="utf-8")
    return str(p)

def load_state_json(path: str = "data/well_state.json") -> SimulationState:
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return run_hydraulics(SimulationState())
    data = json.loads(p.read_text(encoding="utf-8"))
    return dict_to_state(data)
'''

(ROOT / "engines" / "hydraulics_engine.py").write_text(engine_v7, encoding="utf-8")
print("  ✓ engines/hydraulics_engine.py  (Stage 7 – Save/Load)")

# ─────────────────────────────────────────────────────────────
# Stage 7 App – Save/Load + polish
# ─────────────────────────────────────────────────────────────
app_v7 = r'''"""
ARHPP Main Application – Stage 7
Save/Load well state + UI polish
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import APP_NAME, APP_VERSION, APP_SUBTITLE
from engines.hydraulics_engine import (
    SimulationState, run_hydraulics, get_profile_depth_data,
    add_timeline_event, log_activity, get_activity_summary,
    save_state_json, load_state_json, state_to_dict
)

st.set_page_config(page_title=APP_NAME, page_icon="🛢️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #1a1d23; color: #d0d0d0; }
    section[data-testid="stSidebar"] { background-color: #12151a; }
    div[data-testid="stMetricValue"] { color: #00d4aa; font-size: 1.28rem; }
    .block-container { padding-top: 0.4rem; padding-bottom: 0.2rem; }
    h1, h2, h3, h4 { color: #e8e8e8 !important; }
</style>
""", unsafe_allow_html=True)

if "state" not in st.session_state:
    st.session_state.state = run_hydraulics(SimulationState())
if "app_name" not in st.session_state:
    st.session_state.app_name = APP_NAME

state = st.session_state.state

# Top bar
c1, c2, c3, c4 = st.columns([0.5, 3.5, 1.6, 1.2])
with c1:
    st.markdown("### 🛢️")
with c2:
    st.markdown(f"## {st.session_state.app_name} <span style='font-size:12px;color:#888'>{APP_VERSION}</span>", unsafe_allow_html=True)
with c3:
    st.caption(f"Bit: {state.geometry.bit_depth:.0f} ft | {state.current_formation}")
with c4:
    mode_color = {"Offline": "#ffaa00", "Simulation": "#00d4aa", "Live": "#00ff88"}.get(state.mode, "#ffaa00")
    st.markdown(f"<div style='text-align:right;padding-top:10px'><span style='background:{mode_color};color:#111;padding:4px 12px;border-radius:4px;font-weight:700;font-size:12px'>{state.mode.upper()}</span></div>", unsafe_allow_html=True)

status_color = {"OK": "#00d4aa", "WARNING": "#ffaa00", "ALERT": "#ff5555"}.get(state.diag_status, "#888")
st.markdown(f"""
<div style="background:#252a33;padding:6px 12px;border-radius:4px;border-left:4px solid {status_color};margin-bottom:8px;font-size:13px">
<b style="color:{status_color}">{state.diag_status}</b> &nbsp;|&nbsp; {state.diag_message}
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown(f"**{st.session_state.app_name}**")
    nav = st.radio("Modules", [
        "Profile Depth Data", "MPD Gauges", "Main Time Data",
        "Surge & Swab", "Choke Control", "Actual vs Model",
        "Timeline", "Performance", "Engineering", "Settings"
    ], index=0)
    st.markdown("---")
    st.markdown("**Quick Setpoints**")
    state.mode = st.selectbox("Mode", ["Offline", "Simulation", "Live"],
                              index=["Offline", "Simulation", "Live"].index(state.mode))
    state.choke_mode = st.selectbox("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode))
    state.operating.sbp_setpoint = st.slider("SBP (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    state.operating.flow_in_gpm = st.number_input("Flow In (gpm)", 0.0, 2000.0, float(state.operating.flow_in_gpm), 10.0)
    state.operating.flow_out_gpm = st.number_input("Flow Out (gpm)", 0.0, 2000.0, float(state.operating.flow_out_gpm), 5.0)
    state.operating.spp_measured = st.number_input("SPP Measured (psi)", 0.0, 6000.0, float(state.operating.spp_measured), 10.0)
    state.operating.choke_position = st.slider("Choke %", 0, 100, int(state.operating.choke_position), 1)

    if state.mode == "Simulation":
        if st.button("▶ Step Simulation", use_container_width=True):
            import random
            state.operating.flow_out_gpm = max(0, state.operating.flow_in_gpm - random.uniform(2, 12))
            st.session_state.state = run_hydraulics(state)
            st.session_state.state = log_activity(st.session_state.state, "Drilling", 0.5)
            st.rerun()

    if st.button("⟳ Recalculate", use_container_width=True, type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Recalculate", f"SBP={state.operating.sbp_setpoint:.0f}")
        st.session_state.state = log_activity(st.session_state.state, "Circulating", 2.0)
        st.rerun()

    st.markdown("---")
    st.markdown("**Save / Load**")
    if st.button("💾 Save State", use_container_width=True):
        path = save_state_json(st.session_state.state, "data/well_state.json")
        st.session_state.state = add_timeline_event(st.session_state.state, "State Saved", path)
        st.success(f"Saved → {path}")
    if st.button("📂 Load State", use_container_width=True):
        st.session_state.state = load_state_json("data/well_state.json")
        st.session_state.state = add_timeline_event(st.session_state.state, "State Loaded")
        st.rerun()

# ── Pages (same structure as Stage 6 + Save/Load already in sidebar) ──
if nav == "Profile Depth Data":
    gcols = st.columns(7)
    for col, (label, val, unit, delta) in zip(gcols, [
        ("BHP", f"{state.bhp:.0f}", "psi", f"Tgt {state.target_bhp:.0f}"),
        ("ECD", f"{state.ecd:.2f}", "ppg", f"Tgt {state.target_ecd:.2f}"),
        ("Model SPP", f"{state.model_spp:.0f}", "psi", None),
        ("SBP", f"{state.operating.sbp_setpoint:.0f}", "psi", None),
        ("Flow In", f"{state.operating.flow_in_gpm:.0f}", "gpm", None),
        ("Live PP", f"{state.live_pp:.0f}", "psi", f"OB {state.overbalance:.0f}"),
        ("Eff. Flow", f"{state.effective_flow:.0f}", "gpm", None),
    ]):
        col.metric(label, f"{val} {unit}", delta)

    left, right = st.columns([3.1, 1.2])
    with left:
        df = pd.DataFrame(get_profile_depth_data(state, 18))
        display_df = df.rename(columns={
            "MD_ft": "MD", "TVD_ft": "TVD", "Formation": "Form",
            "Formation_Temp_F": "Form.T", "Annulus_Temp_F": "Ann.T",
            "Pipe_Temp_F": "Pipe.T", "Annulus_Density_ppg": "Ann.Dens",
            "Pipe_Density_ppg": "Pipe.Dens", "Annulus_Friction_psi": "Ann.Fric",
            "Pipe_App_Visc_cP": "Pipe.Visc", "Annulus_App_Visc_cP": "Ann.Visc",
            "Annulus_ECD_ppg": "Ann.ECD", "Annulus_Pressure_psi": "Ann.P",
            "Pore_Pressure_psi": "PP", "Fracture_Pressure_psi": "FG",
            "PPG": "PPG", "WBSG_ppg": "WBSG", "WBS_psi": "WBS"
        })
        st.dataframe(display_df, use_container_width=True, height=380)

    with right:
        st.markdown("**Well Schematic + Lithology**")
        fig = go.Figure()
        total_md = max(state.geometry.md, 1)
        for layer in state.lithology:
            y0 = (layer["md_top"] / total_md) * 100
            y1 = min((layer["md_bot"] / total_md) * 100, 100)
            if y0 > 100: continue
            fig.add_shape(type="rect", x0=0.18, x1=0.82, y0=y0, y1=y1,
                          fillcolor=layer["color"], opacity=0.88, line=dict(color="#1a1d23", width=0.6))
            if y1 - y0 > 3.5:
                fig.add_annotation(x=0.5, y=(y0+y1)/2, text=layer["name"], showarrow=False, font=dict(size=9, color="#111"))
        shoe_y = (state.geometry.shoe_depth / total_md) * 100
        fig.add_shape(type="line", x0=0.05, x1=0.95, y0=shoe_y, y1=shoe_y, line=dict(color="#ffaa00", width=2, dash="dot"))
        bit_y = (state.geometry.bit_depth / total_md) * 100
        fig.add_shape(type="rect", x0=0.08, x1=0.92, y0=bit_y-1.3, y1=bit_y+1.3, fillcolor="#00d4aa", line=dict(width=0))
        fig.update_layout(height=350, margin=dict(l=5,r=5,t=5,b=5), paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23",
                          xaxis=dict(visible=False, range=[0,1]),
                          yaxis=dict(range=[100,0], color="#718096", gridcolor="#2d3748", tickfont=dict(size=9)))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<small>**{state.current_formation}** | Bit {state.geometry.bit_depth:.0f} ft<br>Shoe {state.geometry.shoe_depth:.0f} ft | Choke {state.operating.choke_position:.0f}% ({state.choke_mode})</small>", unsafe_allow_html=True)

elif nav == "Main Time Data":
    st.subheader("Main Time Data – Live Trends")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    m2.metric("Q Loss", f"{state.q_loss:.1f} gpm")
    m3.metric("Q U-Tube", f"{state.q_utube:.1f} gpm")
    m4.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    if len(state.history_bhp) > 2:
        fig = go.Figure()
        x = list(range(len(state.history_bhp)))
        fig.add_trace(go.Scatter(x=x, y=state.history_bhp, name="BHP", line=dict(color="#00d4aa", width=2)))
        fig.add_trace(go.Scatter(x=x, y=state.history_spp, name="Model SPP", line=dict(color="#4a9eff", width=2)))
        fig.add_trace(go.Scatter(x=x, y=[e*100 for e in state.history_ecd], name="ECD×100", line=dict(color="#ffaa00", width=2)))
        fig.update_layout(paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"),
                          height=300, margin=dict(t=20, b=30), legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Press **Step Simulation** or **Recalculate** a few times to build live trend history.")
    st.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    st.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    st.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    st.metric("Current Formation", state.current_formation)

elif nav == "Actual vs Model":
    st.subheader("Actual vs Model Diagnostics")
    st.caption("Primary drivers: Flow In/Out + Density + Temperature. SPP is secondary diagnostic only.")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Flow In (Actual)", f"{state.operating.flow_in_gpm:.1f} gpm")
    d2.metric("Flow Out (Actual)", f"{state.operating.flow_out_gpm:.1f} gpm")
    d3.metric("ΔQ (In−Out)", f"{state.delta_flow:.1f} gpm")
    d4.metric("Q Loss (model)", f"{state.q_loss:.1f} gpm")
    st.markdown("---")
    s1, s2, s3 = st.columns(3)
    s1.metric("SPP Measured", f"{state.operating.spp_measured:.0f} psi")
    s2.metric("SPP Model", f"{state.model_spp:.0f} psi")
    s3.metric("Δ SPP (Meas−Model)", f"{state.delta_spp:+.0f} psi")
    st.markdown(f"**Status: {state.diag_status}**")
    st.info(state.diag_message)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Measured / Actual", x=["Flow In", "SPP"], y=[state.operating.flow_in_gpm, state.operating.spp_measured], marker_color="#4a9eff"))
    fig.add_trace(go.Bar(name="Model", x=["Flow In", "SPP"], y=[state.operating.flow_in_gpm, state.model_spp], marker_color="#00d4aa"))
    fig.update_layout(barmode="group", paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"), height=260, margin=dict(t=20, b=40))
    st.plotly_chart(fig, use_container_width=True)
    st.warning("SPP difference is diagnostic only and does NOT drive pressure calculations.")

elif nav == "Performance":
    st.subheader("Performance – Well Activities")
    summary = get_activity_summary(state)
    fig_pie = px.pie(names=list(summary.keys()), values=list(summary.values()),
                     color_discrete_sequence=px.colors.qualitative.Set2, hole=0.35)
    fig_pie.update_layout(paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"), height=320, margin=dict(t=30,b=20,l=20,r=20))
    col_p1, col_p2 = st.columns([1.4, 1])
    with col_p1:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_p2:
        for k, v in sorted(summary.items(), key=lambda x: -x[1]):
            st.write(f"• **{k}**: {v:.0f} min")
        act = st.selectbox("Activity type", ["Drilling", "Connection", "Circulating", "Trip", "Offline", "Other"])
        dur = st.number_input("Duration (min)", 0.5, 120.0, 5.0, 0.5)
        if st.button("Add Activity"):
            st.session_state.state = log_activity(state, act, dur)
            st.session_state.state = add_timeline_event(st.session_state.state, f"Activity: {act}", f"{dur} min")
            st.rerun()

elif nav == "Engineering":
    st.subheader("Engineering – Hydraulics Summary")
    e1, e2, e3 = st.columns(3)
    e1.metric("Hydrostatic", f"{state.hydrostatic:.0f} psi")
    e1.metric("Annular Friction", f"{state.annular_friction:.0f} psi")
    e1.metric("Pipe Friction", f"{state.pipe_friction:.0f} psi")
    e2.metric("Bit ΔP", f"{state.bit_pressure_drop:.0f} psi")
    e2.metric("U-Tube ΔP", f"{state.u_tube_dp:.0f} psi")
    e2.metric("Effective Flow", f"{state.effective_flow:.1f} gpm")
    e3.metric("Corrected Density", f"{state.corrected_density:.2f} ppg")
    e3.metric("Live PP Gradient", f"{state.litho_gradient:.3f} psi/ft")
    e3.metric("Overbalance", f"{state.overbalance:.0f} psi")
    budget = {"Hydrostatic": state.hydrostatic, "Annular Friction": state.annular_friction, "SBP": state.operating.sbp_setpoint}
    fig_bar = go.Figure(go.Bar(x=list(budget.keys()), y=list(budget.values()), marker_color=["#4a9eff", "#00d4aa", "#ffaa00"]))
    fig_bar.update_layout(paper_bgcolor="#1a1d23", plot_bgcolor="#1a1d23", font=dict(color="#ccc"), height=240, yaxis_title="psi", margin=dict(t=20,b=40))
    st.plotly_chart(fig_bar, use_container_width=True)

elif nav == "Timeline":
    st.subheader("Timeline / Feedback")
    ec1, ec2 = st.columns([3, 1])
    with ec1:
        new_event = st.text_input("Add event comment", placeholder="Connection, Pump up, Gas show...")
    with ec2:
        st.write(""); st.write("")
        if st.button("Add to Timeline", use_container_width=True) and new_event.strip():
            st.session_state.state = add_timeline_event(state, new_event.strip())
            st.rerun()
    if state.timeline:
        st.dataframe(pd.DataFrame(state.timeline), use_container_width=True, height=320)
    else:
        st.info("No events yet.")

elif nav == "Surge & Swab":
    st.subheader("Surge & Swab Calculator")
    sc1, sc2 = st.columns(2)
    with sc1:
        state.surge.pipe_velocity_ftmin = st.slider("Pipe Velocity (ft/min)", 5, 150, int(state.surge.pipe_velocity_ftmin))
        state.surge.acceleration = st.number_input("Acceleration (ft/s²)", 0.0, 3.0, float(state.surge.acceleration), 0.1)
        state.surge.open_end = st.checkbox("Open Ended", value=state.surge.open_end)
        state.surge.clinging_factor = st.slider("Clinging Factor", 0.1, 1.0, float(state.surge.clinging_factor), 0.05)
        if st.button("Calculate Surge/Swab", type="primary"):
            st.session_state.state = run_hydraulics(state)
            st.session_state.state = add_timeline_event(st.session_state.state, "Surge/Swab", f"Vel={state.surge.pipe_velocity_ftmin}")
            st.session_state.state = log_activity(st.session_state.state, "Trip", 3.0)
            st.rerun()
    with sc2:
        st.metric("Max Surge", f"{state.max_surge_psi:.0f} psi")
        st.metric("Max Swab", f"{state.max_swab_psi:.0f} psi")
        st.metric("ESD Surge", f"{state.esd_surge:.2f} ppg")
        st.metric("ESD Swab", f"{state.esd_swab:.2f} ppg")
        st.metric("BHP @ Surge", f"{state.bhp + state.max_surge_psi:.0f} psi")
        st.metric("BHP @ Swab", f"{state.bhp + state.max_swab_psi:.0f} psi")

elif nav == "Choke Control":
    st.subheader("Choke Control Panel")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        state.choke_mode = st.radio("Choke Mode", ["MANUAL", "AUTO", "CBHP"],
                                    index=["MANUAL", "AUTO", "CBHP"].index(state.choke_mode), horizontal=True)
    with cc2:
        if state.choke_mode == "CBHP":
            state.target_bhp = st.number_input("Target BHP (psi)", 0.0, 15000.0, float(state.target_bhp), 10.0)
        elif state.choke_mode == "AUTO":
            state.target_ecd = st.number_input("Target ECD (ppg)", 8.0, 18.0, float(state.target_ecd), 0.05)
        state.operating.sbp_setpoint = st.slider("SBP Setpoint (psi)", 0, 1000, int(state.operating.sbp_setpoint), 5)
    with cc3:
        st.metric("Choke Position", f"{state.operating.choke_position:.0f} %")
        st.metric("Current SBP", f"{state.operating.sbp_setpoint:.0f} psi")
        st.metric("Current BHP", f"{state.bhp:.0f} psi")
        st.metric("Current ECD", f"{state.ecd:.2f} ppg")
    if st.button("Apply Setpoint & Recalculate", type="primary", use_container_width=True):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Choke Apply", f"{state.choke_mode} SBP={state.operating.sbp_setpoint:.0f}")
        st.rerun()
    if state.choke_mode == "CBHP":
        st.success("CBHP Auto active in Simulation mode → SBP adjusts to hold Target BHP.")

elif nav == "MPD Gauges":
    st.subheader("MPD Gauges")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("BHP", f"{state.bhp:.0f} psi", f"{state.bhp - state.target_bhp:+.0f}")
    g2.metric("ECD", f"{state.ecd:.2f} ppg", f"{state.ecd - state.target_ecd:+.2f}")
    g3.metric("SBP", f"{state.operating.sbp_setpoint:.0f} psi")
    g4.metric("Overbalance", f"{state.overbalance:.0f} psi")
    if len(state.history_bhp) > 2:
        st.line_chart({"BHP": state.history_bhp, "ECD×100": [e*100 for e in state.history_ecd]})
    else:
        st.line_chart({"BHP": [state.bhp-40, state.bhp-15, state.bhp, state.bhp+8, state.bhp-5],
                       "ECD x100": [(state.ecd-0.08)*100, (state.ecd-0.03)*100, state.ecd*100, (state.ecd+0.02)*100, state.ecd*100]})

elif nav == "Settings":
    st.subheader("Settings")
    new_name = st.text_input("Application Display Name", value=st.session_state.app_name)
    if st.button("Update Name"):
        st.session_state.app_name = new_name
        st.success(f"Name set to: {new_name}")
        st.rerun()
    st.markdown("---")
    st.markdown("**Well Geometry**")
    state.geometry.md = st.number_input("Total MD (ft)", value=float(state.geometry.md))
    state.geometry.tvd = st.number_input("TVD (ft)", value=float(state.geometry.tvd))
    state.geometry.hole_id = st.number_input("Hole ID (in)", value=float(state.geometry.hole_id))
    state.geometry.pipe_od = st.number_input("Pipe OD (in)", value=float(state.geometry.pipe_od))
    state.geometry.bit_depth = st.number_input("Bit Depth (ft)", value=float(state.geometry.bit_depth))
    state.geometry.shoe_depth = st.number_input("Casing Shoe (ft)", value=float(state.geometry.shoe_depth))
    st.markdown("**Fluid**")
    state.fluid.density_ppg = st.number_input("Mud Density (ppg)", value=float(state.fluid.density_ppg))
    state.fluid.temp_in = st.number_input("Mud Temp In (°F)", value=float(state.fluid.temp_in))
    state.fluid.temp_out = st.number_input("Mud Temp Out (°F)", value=float(state.fluid.temp_out))
    state.fluid.n = st.number_input("n (HB)", value=float(state.fluid.n), format="%.3f")
    state.fluid.K = st.number_input("K (HB)", value=float(state.fluid.K), format="%.3f")
    st.markdown("**Bit**")
    state.bit.bit_type = st.selectbox("Bit Type", ["PDC", "Diamond Impregnated", "Tricone"])
    state.bit.tfa = st.number_input("TFA (in²)", value=float(state.bit.tfa), format="%.3f")
    if st.button("Apply All & Recalculate", type="primary"):
        st.session_state.state = run_hydraulics(state)
        st.session_state.state = add_timeline_event(st.session_state.state, "Settings Applied")
        st.rerun()

else:
    st.subheader(nav)
    st.info(f"Module **{nav}** ready.")

st.markdown("<hr style='border-color:#333'>", unsafe_allow_html=True)
st.caption(f"{st.session_state.app_name} | Stage 7 | Save/Load + Live trends | Excel v4 physics | SPP diagnostic only")
'''

(ROOT / "app.py").write_text(app_v7, encoding="utf-8")
print("  ✓ app.py  (Stage 7 – Save/Load)")

try:
    (ROOT / "README.md").write_text('''# ARHPP Digital Twin – Stage 7

## التشغيل
```bash
cd ARHPP_App
pip install -r requirements.txt
streamlit run app.py
```

## ما أُضيف في Stage 7
- **Save / Load State** (JSON) من الـ Sidebar
- حفظ واستعادة Geometry + Fluid + Operating + Bit + Timeline + Activity
- تلميع إضافي للواجهة

## الملف المتراكم
build_arhpp_full.py = المراحل 1 → 7
''', encoding="utf-8")
    print("  ✓ README.md updated")
except Exception as e:
    print(f"  ⚠ README write skipped: {e}")

print()
print("=" * 60)
print("✅ Stage 7 completed successfully!")
print("  cd ARHPP_App && streamlit run app.py")
print("=" * 60)
