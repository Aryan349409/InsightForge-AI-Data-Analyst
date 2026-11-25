"""Signature presentation layer."""
import streamlit as st
import plotly.io as pio
import plotly.graph_objects as go
import plotly.express as px
from html import escape
from modules.chart_colors import apply_colors
PALETTE=['#6D5CE8','#00A991','#F2A65A','#4389E8','#D76BA4','#8795AA']

PRESETS = {
    'Lagoon': ['#087F8C','#E08A54','#7167B8','#4A9B77','#C45E83','#527BAA'],
    'Orchid': ['#7655B5','#B86C9D','#4D8EB5','#E3A44D','#39978A','#8D729D'],
    'Earth': ['#487B69','#B66A50','#C39A4A','#657E9B','#8E7090','#719B52'],
    'Ocean': ['#2166AC','#159A9C','#64A6D9','#7359B5','#E6A24C','#C65C76'],
}

def palette_controls():
    with st.sidebar.expander('Chart appearance', expanded=False):
        if st.button('Reset palette', key='forge_reset'):
            st.session_state['forge_palette_choice'] = 'Lagoon'
            for i,c in enumerate(PRESETS['Lagoon']):
                st.session_state[f'forge_color_{i}'] = c
            st.session_state['forge_mode'] = 'Palette'
            st.session_state['forge_single'] = PRESETS['Lagoon'][0]
        choice = st.selectbox('Colour palette', list(PRESETS) + ['Custom'], key='forge_palette_choice')
        if choice == 'Custom':
            cols = st.columns(3)
            colors = [cols[i % 3].color_picker(f'Colour {i+1}', c, key=f'forge_color_{i}') for i,c in enumerate(PRESETS['Lagoon'])]
        else:
            colors = PRESETS[choice]
        st.markdown('<div style="display:flex;gap:5px">'+''.join(f'<span style="background:{c};height:18px;flex:1;border-radius:5px"></span>' for c in colors)+'</div>', unsafe_allow_html=True)
        mode = st.selectbox('Chart colouring', ['Palette', 'Single colour'], key='forge_mode')
        if mode == 'Single colour':
            st.color_picker('Chart colour', colors[0], key='forge_single')
        st.caption('Palette colours cycle across bars and series. Heatmaps retain a colour scale.')
    PALETTE[:] = colors

def setup():
    pio.templates['forge']=go.layout.Template(layout=dict(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#344C4B',family='Arial',size=13),colorway=PALETTE,xaxis=dict(gridcolor='#D9E3DF',zerolinecolor='#D9E3DF'),yaxis=dict(gridcolor='#D9E3DF',zerolinecolor='#D9E3DF'),margin=dict(l=25,r=25,t=45,b=35)))
    pio.templates.default='forge'
    px.defaults.color_discrete_sequence=PALETTE
    st.markdown('''<style>
    .stApp {background:radial-gradient(ellipse at 90% 0%,#e0e9f0 0%,transparent 52%),radial-gradient(ellipse at 0% 80%,#e5e5d5 0%,transparent 55%),#e7eeea;color:#243d3b;}
    [data-testid="stHeader"] {background:transparent;}
    [data-testid="stSidebar"] {background:#e3ebe6;border-right:1px solid #cbd9d3;}
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:1rem;}
    .block-container {max-width:1440px;padding:2.5rem 3rem 4rem;}
    h1,h2,h3 {letter-spacing:-.045em;color:#243d3b;}
    .forge-brand {font-size:1.5rem;font-weight:850;letter-spacing:-.07em;color:#243d3b;display:flex;align-items:center;gap:10px;}
    .forge-mark {display:inline-grid;place-items:center;background:#087f8c;color:white;border-radius:12px;width:38px;height:38px;font-size:24px;}
    .forge-kicker {font-size:.68rem;letter-spacing:.16em;font-weight:800;color:#087f8c;text-transform:uppercase;}
    .forge-hero {position:relative;overflow:hidden;padding:1.5rem 0 1.1rem;margin-bottom:.7rem;border-bottom:1px solid #e1e5ef;}
    .forge-hero h1 {font-size:clamp(2rem,3vw,2.9rem);line-height:1.12;margin:.4rem 0;color:#243d3b;}
    .forge-hero p {color:#667085;font-size:.98rem;margin:.5rem 0;}
    .forge-welcome {position:relative;overflow:hidden;background:radial-gradient(circle at 88% 18%,#c5dce7 0,transparent 42%),linear-gradient(120deg,#d0e6d9,#e8e6d5);border-radius:24px;padding:3rem;color:#243d3b;margin:1rem 0 1.6rem;}
    .forge-welcome h1 {color:#243d3b;font-size:clamp(2.4rem,4vw,4rem);line-height:1.05;max-width:650px;}
    .forge-welcome p {color:#45615d;max-width:560px;}
    .forge-welcome .forge-kicker {color:#087f8c;}
    [data-testid="stMetric"] {background:#f2f5ef;border:1px solid #cbd9d3;border-radius:18px;padding:1.2rem;min-height:125px;box-shadow:0 4px 16px #20204006;}
    [data-testid="stMetricValue"] {font-weight:780;letter-spacing:-.055em;}
    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {background:#f2f5ef;border:1px solid #cbd9d3;border-radius:16px;padding:.35rem;overflow:hidden;}
    [data-testid="stChatMessage"] {background:#f2f5ef;border:1px solid #cbd9d3;border-radius:18px;padding:1rem;}
    [data-testid="stChatInput"] {border-radius:16px;}
    [data-testid="stSidebar"] [role="radiogroup"] label {padding:9px 12px;border-radius:9px;transition:background .15s;}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#d7e8e2;}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#cde3de;color:#17665f;font-weight:700;}
    .stButton button,.stDownloadButton button {border-radius:10px;font-weight:650;min-height:2.7rem;transition:transform .15s,box-shadow .15s;}
    .stButton button:hover,.stDownloadButton button:hover {transform:translateY(-1px);box-shadow:0 4px 12px #087f8c22;}
    .stButton button[kind="primary"] {background:#087f8c;color:white;border:0;}
    .forge-card {background:#f2f5ef;border:1px solid #cbd9d3;border-radius:18px;padding:1.4rem;min-height:150px;}
    .forge-card b {display:block;color:#243d3b;font-size:1.08rem;margin:.6rem 0;}
    .forge-card p {color:#667085;font-size:.88rem;margin:0;}
    .forge-num {display:inline-block;color:#087f8c;background:#dbece5;border-radius:8px;padding:7px 10px;font-weight:800;font-size:.8rem;}
    .forge-status {background:#e3ebe6;border:1px solid #cbd9d3;border-radius:12px;padding:12px 16px;color:#475467;font-size:.85rem;margin-bottom:1rem;}
    .forge-welcome {border:1px solid #b9d0c7;display:grid;grid-template-columns:1.4fr 1fr;gap:2rem;align-items:center;}
    .forge-art {width:100%;max-width:420px;justify-self:center;}
    .forge-tag {display:inline-block;border:1px solid #a8c8bc;border-radius:30px;padding:6px 12px;color:#35665e;font-size:.75rem;font-weight:700;margin-top:1rem;}
    .forge-card {box-shadow:0 8px 24px #294c4310;transition:transform .18s;}
    .forge-card:hover {transform:translateY(-3px);}
    @media(max-width:850px){.forge-welcome{grid-template-columns:1fr}.forge-art{max-width:260px}}
    @media(max-width:700px){.block-container{padding:2rem 1rem}.forge-welcome{padding:1.5rem}}
    </style>''',unsafe_allow_html=True)

def hero(kicker,title,description):
    st.markdown(f'<div class="forge-hero"><div class="forge-kicker">{escape(kicker)}</div><h1>{escape(title)}</h1><p>{escape(description)}</p></div>',unsafe_allow_html=True)

def landing():
    st.markdown('''<div class="forge-welcome"><div><div class="forge-kicker">INSIGHTFORGE / ANALYTICS STUDIO</div><h1>Turn raw data into remarkable insights.</h1><p>Explore, clean, visualize and ask your data questions in one intelligent workspace.</p><span class="forge-tag">01 Connect &nbsp; → &nbsp; 02 Explore &nbsp; → &nbsp; 03 Discover</span></div><svg class="forge-art" viewBox="0 0 320 240" role="img" aria-label="Decorative analytics illustration"><rect x="12" y="12" width="296" height="216" rx="22" fill="#f0f5ef" stroke="#a8c8bc"/><circle cx="35" cy="35" r="5" fill="#087f8c"/><circle cx="51" cy="35" r="5" fill="#e08a54"/><path d="M30 57H290M30 100H290M30 143H290M30 186H290" stroke="#d1e0d9"/><g fill="#80b9ad"><rect x="42" y="139" width="28" height="47" rx="5"/><rect x="88" y="113" width="28" height="73" rx="5"/><rect x="134" y="125" width="28" height="61" rx="5"/><rect x="180" y="83" width="28" height="103" rx="5"/><rect x="226" y="64" width="28" height="122" rx="5"/></g><path d="M56 126L102 91L148 105L194 59L240 42" fill="none" stroke="#087f8c" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><circle cx="240" cy="42" r="6" fill="#e08a54"/><text x="30" y="211" font-size="10" fill="#45615d">ILLUSTRATIVE ANALYTICS</text></svg></div>''',unsafe_allow_html=True)
    st.subheader('Start exploring')
    cards=[('01','Data overview','Understand quality and structure.'),('02','Data preparation','Clean and transform records.'),('03','AI assistant','Ask questions in natural language.'),('04','Visual explorer','Discover patterns visually.'),('05','Predictive lab','Train models and forecast trends.'),('06','Insights & reports','Turn findings into decisions.')]
    for i in range(0,6,3):
        for col,(n,t,d) in zip(st.columns(3),cards[i:i+3]):
            col.markdown(f'<div class="forge-card"><span class="forge-num">{n}</span><b>{t}</b><p>{d}</p></div>',unsafe_allow_html=True)
    st.info('Connect a dataset using the sidebar to begin.')


def style_chart(fig, mode=None, single=None, overrides=None):
    return apply_colors(fig, PALETTE, mode or st.session_state.get('forge_mode', 'Palette'),
                        single or st.session_state.get('forge_single', PALETTE[0]), overrides)


def show_chart(fig, mode=None, single=None, overrides=None, **kwargs):
    return st.plotly_chart(style_chart(fig, mode, single, overrides), theme=None, **kwargs)
