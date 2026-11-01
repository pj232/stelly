# -*- coding: utf-8 -*-
"""
GC Bâtiment R-n / R+n — collecte, analyse et gestion de données d'un projet de bâtiment
(sous-sols, niveaux, descente de charges, béton armé, fondations, actions, incendie, quantités).
Lancement :  streamlit run App.py

Résultats indicatifs (méthodes simplifiées) : à valider par un ingénieur / bureau d'études.
"""
import io
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="GC Bâtiment R-n / R+n", page_icon="🏢", layout="wide",
                   initial_sidebar_state="expanded")

# ===================== THÈME =====================
ACCENT = "#E4572E"
ACCENT_CLAIR = "#FFD9CC"
FOND = "#F7F4EF"
NOIR = "#2B2D42"
ROUGE = "#C1121F"
VERT = "#2A9D4F"
ORANGE = "#F2A541"
BLEU = "#3A6EA5"
GRIS = "#8D99AE"
PALETTE = [NOIR, ACCENT, BLEU, ORANGE, VERT, ROUGE, GRIS]

CSS = f"""
<style>
.stApp {{ background: radial-gradient(circle at 10% 0%,#FFFFFF 0%,{FOND} 45%,#EFE9E1 100%); color:{NOIR}; }}
h1,h2,h3,h4,h5 {{ color:{NOIR} !important; font-weight:800 !important; letter-spacing:-0.01em; }}
[data-testid="stSidebar"] {{ background:linear-gradient(180deg,{NOIR} 0%,#1B1C2E 100%); border-right:0; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] div, [data-testid="stSidebar"] small {{ color:#EDEAE4 !important; }}
.brand {{ background:{ACCENT}; color:#FFFFFF; font-weight:900; font-size:1.15rem; padding:14px;
          border-radius:14px; text-align:center; margin-bottom:10px; box-shadow:0 6px 18px {ACCENT}55; }}
.hero {{ background:linear-gradient(115deg,{NOIR} 0%,#3D405B 65%,#565A7C 100%); border-radius:18px 18px 0 0;
         padding:20px 28px; box-shadow:0 8px 24px #2B2D4233; }}
.hero h1 {{ margin:0; color:#FFFFFF !important; font-size:1.85rem; }}
.hero p {{ margin:6px 0 0; color:{ACCENT_CLAIR}; font-weight:600; }}
.hazard {{ height:8px; border-radius:0 0 18px 18px; margin-bottom:20px;
           background:linear-gradient(90deg,{ACCENT} 0%,{ORANGE} 50%,{ACCENT} 100%); background-size:200% 100%;
           animation:slide 4s linear infinite; }}
@keyframes slide {{ from {{ background-position:0 0; }} to {{ background-position:200% 0; }} }}
[data-testid="stMetric"] {{ background:#FFFFFF; border-radius:16px; border-top:5px solid {ACCENT};
          padding:12px 18px; box-shadow:0 6px 18px #2B2D4222; }}
[data-testid="stMetricValue"] {{ color:{NOIR}; font-weight:800; }}
.stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button {{
    background:{ACCENT}; color:#FFFFFF; border:0; font-weight:800; border-radius:999px; padding:0.45rem 1.3rem;
    box-shadow:0 4px 12px {ACCENT}55; }}
.stButton>button:hover, .stDownloadButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover {{
    background:{NOIR}; color:#FFFFFF; }}
.stTabs [data-baseweb="tab-list"] {{ gap:8px; flex-wrap:wrap; }}
.stTabs [data-baseweb="tab"] {{ background:#FFFFFF; border-radius:999px; padding:8px 18px; font-weight:700;
    color:{NOIR}; border:1px solid #D9D3CA; }}
.stTabs [aria-selected="true"] {{ background:{NOIR}; color:#FFFFFF; border-color:{NOIR}; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
.note {{ background:#FFFFFF; color:{NOIR}; padding:12px 18px; border-radius:12px; border-left:6px solid {ACCENT};
         margin:8px 0 14px; font-size:0.95rem; box-shadow:0 3px 10px #2B2D4214; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def _wide():
    try:
        v = tuple(int(x) for x in st.__version__.split(".")[:2])
    except Exception:
        v = (0, 0)
    return {"width": "stretch"} if v >= (1, 50) else {"use_container_width": True}


WIDE = _wide()
_PN = [0]


# ===================== OUTILS =====================
def hero(titre, sous=""):
    st.markdown(f"<div class='hero'><h1>{titre}</h1><p>{sous}</p></div><div class='hazard'></div>",
                unsafe_allow_html=True)


def note(txt):
    st.markdown(f"<div class='note'>{txt}</div>", unsafe_allow_html=True)


def fnum(x, default=0.0):
    try:
        v = float(x)
        return default if math.isnan(v) else v
    except Exception:
        return default


def fmt(x, nd=2):
    try:
        return f"{x:,.{nd}f}".replace(",", " ")
    except Exception:
        return str(x)


def num(df, col):
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def verdict(cond, ok_msg, ko_msg):
    (st.success if cond else st.error)(("✅ " + ok_msg) if cond else ("❌ " + ko_msg))


def pplot(fig, height=420):
    _PN[0] += 1
    fig.update_layout(height=height, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(color=NOIR),
                      colorway=PALETTE, margin=dict(l=20, r=20, t=55, b=20), title_font=dict(size=16, color=NOIR))
    fig.update_xaxes(gridcolor="#E6E0D6", zerolinecolor="#B9B1A3")
    fig.update_yaxes(gridcolor="#E6E0D6", zerolinecolor="#B9B1A3")
    try:
        st.plotly_chart(fig, key=f"pl{_PN[0]}", **WIDE)
    except TypeError:
        st.plotly_chart(fig, key=f"pl{_PN[0]}")


def show_df(df, **kw):
    try:
        st.dataframe(df, hide_index=True, **WIDE, **kw)
    except TypeError:
        st.dataframe(df, hide_index=True, **kw)


# ===================== SCHÉMAS =====================
COLS = {
    "niveaux": ["Niveau", "Hauteur (m)", "Surface (m²)", "Usage", "G (kN/m²)", "Q (kN/m²)"],
    "releves": ["Date", "Niveau", "Paramètre", "Valeur", "Unité", "Opérateur", "Remarque"],
    "journal": ["Date", "Météo", "Effectif", "Activités", "Observations"],
    "essais": ["Date", "Élément", "Classe", "Âge (j)", "Résistance (MPa)"],
    "metre": ["Lot", "Désignation", "Unité", "Quantité", "PU"],
    "taches": ["Tâche", "Début", "Durée (j)", "Avancement (%)", "Responsable", "Prédécesseurs"],
    "risques": ["Risque", "Phase", "Probabilité", "Gravité", "Mesure de maîtrise"],
    "ev": ["Mois", "PV cumulé", "EV cumulée", "AC cumulé"],
    "couches": ["Matériau", "Épaisseur (cm)"],
    "parois": ["Paroi", "Surface (m²)", "U (W/m²·K)"],
}
DATES = {"releves": ["Date"], "journal": ["Date"], "essais": ["Date"], "taches": ["Début"]}
NUMS = {
    "niveaux": ["Hauteur (m)", "Surface (m²)", "G (kN/m²)", "Q (kN/m²)"], "releves": ["Valeur"], "journal": ["Effectif"],
    "essais": ["Âge (j)", "Résistance (MPa)"], "metre": ["Quantité", "PU"], "taches": ["Durée (j)", "Avancement (%)"],
    "risques": ["Probabilité", "Gravité"], "ev": ["Mois", "PV cumulé", "EV cumulée", "AC cumulé"],
    "couches": ["Épaisseur (cm)"], "parois": ["Surface (m²)", "U (W/m²·K)"],
}
LABELS = {
    "niveaux": "Niveaux R-n R+n", "releves": "Relevés de chantier", "journal": "Journal de chantier",
    "essais": "Essais béton", "metre": "Métré", "taches": "Planning", "risques": "Risques HSE", "ev": "Suivi coûts",
    "couches": "Paroi (couches)", "parois": "Parois thermiques",
}
USAGES = {"Parking": (1.0, 2.5), "Habitation": (2.5, 1.5), "Bureaux": (2.5, 2.5), "Commerce": (2.0, 5.0),
          "Local technique": (2.0, 5.0), "Terrasse inaccessible": (3.5, 1.0), "Terrasse accessible": (4.0, 3.5)}
PARAMS = {"Affaissement (slump)": "mm", "Température béton": "°C", "Désaplomb poteau": "mm", "Flèche dalle": "mm",
          "Fissure (ouverture)": "mm", "Niveau topographique": "m", "Humidité support": "%"}
TOLERANCES = {"Température béton": (5, 30), "Désaplomb poteau": (-10, 10), "Fissure (ouverture)": (None, 0.3),
              "Affaissement (slump)": (70, 160)}
METEO = ["Ensoleillé", "Nuageux", "Pluie légère", "Pluie forte", "Vent fort", "Forte chaleur"]
CLASSES_BETON = ["C20/25", "C25/30", "C30/37", "C35/45", "C40/50"]
USAGE_PROJET = ["Habitation collective", "Bureaux", "Mixte commerce + habitation", "Hôtel", "Équipement public"]
MATERIAUX = {"Enduit ciment": 1.0, "Parpaing creux (équiv.)": 1.0, "Béton armé": 2.3, "Brique alvéolaire": 0.30,
             "Béton cellulaire": 0.16, "Plâtre / BA13": 0.25, "Polystyrène expansé": 0.038, "Laine de roche": 0.038,
             "Laine de verre": 0.035, "Polyuréthane": 0.025, "Carrelage + chape": 1.4}


def coerce(df, key):
    d = df.copy()
    for c in COLS[key]:
        if c not in d.columns:
            d[c] = None
    d = d[COLS[key]]
    for c in DATES.get(key, []):
        d[c] = pd.to_datetime(d[c], errors="coerce").dt.date
        d[c] = d[c].where(d[c].notna(), None)
    for c in NUMS.get(key, []):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.reset_index(drop=True)


def metre_totals(df):
    d = df.copy()
    d["Quantité"], d["PU"] = num(d, "Quantité"), num(d, "PU")
    d["Total"] = d["Quantité"] * d["PU"]
    d["Lot"] = d["Lot"].fillna("Divers").astype(str)
    return d


def gen_niveaux(n_ss, n_et, s_ss, s_et, usage_rdc="Commerce", usage_et="Habitation"):
    rows = []
    for k in range(n_ss, 0, -1):
        g, q = USAGES["Parking"]
        rows.append(("R-%d" % k, 2.8, s_ss, "Parking", g, q))
    g, q = USAGES[usage_rdc]
    rows.append(("RDC", 3.6, s_et, usage_rdc, g, q))
    for k in range(1, n_et + 1):
        g, q = USAGES[usage_et]
        rows.append(("R+%d" % k, 3.0, s_et, usage_et, g, q))
    g, q = USAGES["Terrasse inaccessible"]
    rows.append(("Terrasse", 0.0, s_et * 0.9, "Terrasse inaccessible", g, q))
    return coerce(pd.DataFrame(rows, columns=COLS["niveaux"]), "niveaux")


def niveaux_calc(df):
    """Ajoute les cotes (RDC = 0,00) et les indicateurs de niveau."""
    d = df.dropna(subset=["Niveau"]).copy().reset_index(drop=True)
    for c in NUMS["niveaux"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
    names = [str(x) for x in d["Niveau"]]
    i0 = names.index("RDC") if "RDC" in names else 0
    cote = [0.0] * len(d)
    for i in range(i0 + 1, len(d)):
        cote[i] = cote[i - 1] + d["Hauteur (m)"][i - 1]
    for i in range(i0 - 1, -1, -1):
        cote[i] = cote[i + 1] - d["Hauteur (m)"][i]
    d["Cote plancher (m)"] = cote
    d["Sous-sol"] = [c < -1e-9 for c in cote]
    return d



# ===================== ÉDITEUR DE TABLEAUX (état fiable) =====================
def bump(key):
    S = st.session_state
    S[f"{key}__v"] = S.get(f"{key}__v", 0) + 1


def set_df(key, df):
    st.session_state[key] = df
    bump(key)


def add_rows(key, new):
    S = st.session_state
    set_df(key, pd.concat([S[key], coerce(new, key)], ignore_index=True))


def _apply_delta(key):
    S = st.session_state
    ver = S.get(f"{key}__v", 0)
    delta = S.get(f"ed_{key}_{ver}") or {}
    df = S[key].astype(object).reset_index(drop=True)
    for r, ch in (delta.get("edited_rows") or {}).items():
        r = int(r)
        if r < len(df):
            for c, v in ch.items():
                if c in df.columns:
                    df.iat[r, df.columns.get_loc(c)] = v
    for row in delta.get("added_rows") or []:
        df = pd.concat([df, pd.DataFrame([row], columns=df.columns)], ignore_index=True)
    dels = [int(i) for i in (delta.get("deleted_rows") or []) if int(i) < len(df)]
    if dels:
        df = df.drop(index=dels).reset_index(drop=True)
    S[key] = coerce(df, key) if key in COLS else df.infer_objects()
    S[f"{key}__v"] = ver + 1


def editor(key, config=None, dynamic=True):
    """Tableau éditable : S[key] reste la source de vérité (mise à jour par callback)."""
    S = st.session_state
    kw = dict(key=f"ed_{key}_{S.get(f'{key}__v', 0)}", column_config=config or {},
              num_rows="dynamic" if dynamic else "fixed", hide_index=True, on_change=_apply_delta, args=(key,))
    try:
        return st.data_editor(S[key], **WIDE, **kw)
    except TypeError:
        return st.data_editor(S[key], **kw)


# ===================== PLANNING (chemin critique) =====================
def cpm(df):
    d = df.dropna(subset=["Tâche"]).copy()
    d["Tâche"] = d["Tâche"].astype(str)
    d = d.drop_duplicates("Tâche").reset_index(drop=True)
    d["Durée (j)"] = pd.to_numeric(d["Durée (j)"], errors="coerce").fillna(0).clip(lower=0)
    names = d["Tâche"].tolist()
    dur = dict(zip(names, d["Durée (j)"]))
    preds = {n: [x.strip() for x in str(p).split(";") if x.strip() in dur and x.strip() != n]
             for n, p in zip(names, d["Prédécesseurs"].fillna(""))}
    order, state = [], {}

    def visit(n):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            raise ValueError(f"Boucle de dépendances autour de « {n} »")
        state[n] = 1
        for p in preds[n]:
            visit(p)
        state[n] = 2
        order.append(n)

    for n in names:
        visit(n)
    ES, EF = {}, {}
    for n in order:
        ES[n] = max([EF[p] for p in preds[n]], default=0.0)
        EF[n] = ES[n] + dur[n]
    T = max(EF.values(), default=0.0)
    succ = {n: [m for m in names if n in preds[m]] for n in names}
    LS, LF = {}, {}
    for n in reversed(order):
        LF[n] = min([LS[s] for s in succ[n]], default=T)
        LS[n] = LF[n] - dur[n]
    d["ES"] = d["Tâche"].map(ES)
    d["EF"] = d["Tâche"].map(EF)
    d["Marge (j)"] = d["Tâche"].map(lambda n: LS[n] - ES[n])
    d["Critique"] = d["Marge (j)"].abs() < 1e-9
    return d, T


# ===================== CALCULS : BÉTON ARMÉ =====================
G = 9.81


def beton_props(classe):
    fck = float(str(classe).replace("C", "").split("/")[0])
    return dict(fck=fck, fcd=fck / 1.5, fctm=0.30 * fck ** (2 / 3), Ecm=22 * ((fck + 8) / 10) ** 0.3)


def aire_barre(phi):
    return math.pi * phi ** 2 / 4.0


def flexion_rect(M_kNm, b, d, fck, fyk, dp=None):
    fcd, fyd = fck / 1.5, fyk / 1.15
    M = abs(M_kNm) * 1e6
    mu = M / (b * d ** 2 * fcd)
    res = dict(mu=mu, mu_lim=0.295, As=0.0, As2=0.0, double=False)
    if M == 0:
        return res
    if mu <= 0.295:
        xi = 1 - math.sqrt(1 - 2 * mu)
        res["As"] = M / (d * (1 - xi / 2) * fyd)
    else:
        dp = dp or 0.1 * d
        z_lim = d * (1 - 0.36 / 2)
        res["As2"] = (M - 0.295 * b * d ** 2 * fcd) / ((d - dp) * fyd)
        res["As"] = 0.295 * b * d ** 2 * fcd / (z_lim * fyd) + res["As2"]
        res["double"] = True
    return res


def vrd_c(b, d, fck, As):
    rho = min(As / (b * d), 0.02)
    k = min(2.0, 1 + math.sqrt(200.0 / d))
    v = 0.18 / 1.5 * k * (100 * rho * fck) ** (1 / 3)
    return max(v, 0.035 * k ** 1.5 * math.sqrt(fck)) * b * d / 1e3


def as_min_flex(b, d, fck, fyk):
    return max(0.26 * 0.30 * fck ** (2 / 3) / fyk * b * d, 0.0013 * b * d)


def choisir_armature(As, h):
    if As <= 0:
        return "—"
    smax = min(3 * h, 400)
    for phi in (8, 10, 12, 14, 16, 20, 25):
        s = math.floor(1000 * aire_barre(phi) / As / 25) * 25
        if s >= 100:
            return f"HA{phi} @ {int(min(s, smax))}"
    return "HA25 @ 100 (augmenter la section)"


def options_barres(As_req, b, c, phit):
    rows = []
    for phi in (10, 12, 14, 16, 20, 25, 32):
        n = max(2, math.ceil(As_req / aire_barre(phi))) if As_req > 0 else 2
        s = (b - 2 * (c + phit) - n * phi) / (n - 1)
        rows.append({"Barres": f"{n} HA{phi}", "As fournie (cm²)": round(n * aire_barre(phi) / 100, 2),
                     "Espacement libre (mm)": round(s), "Faisable (1 lit)": "✅" if s >= max(phi, 25) else "❌ (2 lits)"})
    return pd.DataFrame(rows)


def poinconnement(N_kN, bc, hc, d, p_kPa, fck, rho=0.01):
    """Vérification au poinçonnement à 2d du poteau. bc, hc, d en mm ; p en kPa."""
    u1 = 2 * (bc + hc) + 4 * math.pi * d
    A_ctl = (bc + 2 * d) * (hc + 2 * d) / 1e6
    V = max(N_kN - p_kPa * A_ctl, 0.0)
    vEd = 1.15 * V * 1e3 / (u1 * d)
    k = min(2.0, 1 + math.sqrt(200.0 / d))
    vRd = max(0.18 / 1.5 * k * (100 * rho * fck) ** (1 / 3), 0.035 * k ** 1.5 * math.sqrt(fck))
    return vEd, vRd, vEd <= vRd


# ===================== CALCULS : NIVEAUX ET DESCENTE DE CHARGES =====================
def descente(niv, Ss, hd, bc, hc, psi0, classe, rho):
    d = niv.reset_index(drop=True)
    T = len(d) - 1
    fcd = beton_props(classe)["fcd"]
    fyd = 500 / 1.15
    rows = []
    for i in range(T):
        Gc = sum((hd / 100 * 25 + d["G (kN/m²)"][j]) * Ss for j in range(i + 1, T + 1))
        Gc += sum(bc / 100 * hc / 100 * d["Hauteur (m)"][j] * 25 for j in range(i, T))
        floors = list(range(i + 1, T))
        qs = sum(d["Q (kN/m²)"][j] * Ss for j in floors)
        nf = len(floors)
        alpha = 1.0 if nf <= 2 else (2 + (nf - 2) * psi0) / nf
        Qc = d["Q (kN/m²)"][T] * Ss + alpha * qs
        Ned, Nser = 1.35 * Gc + 1.5 * Qc, Gc + Qc
        Ac = Ned * 1e3 / (0.7 * (fcd + rho * fyd))
        side = max(25, math.ceil(math.sqrt(Ac) / 10 / 5) * 5)
        rows.append({"Poteau (pied du niveau)": d["Niveau"][i], "Cote du pied (m)": round(d["Cote plancher (m)"][i], 2),
                     "G cumulé (kN)": round(Gc, 1), "Q cumulé dégressé (kN)": round(Qc, 1), "N_Ed ELU (kN)": round(Ned, 1),
                     "N_ser ELS (kN)": round(Nser, 1), "Côté carré mini (cm)": side})
    return pd.DataFrame(rows)


def volumes_niveaux(niv, p):
    """Quantités de structure par niveau. p = dictionnaire des paramètres."""
    rows = []
    d = niv.reset_index(drop=True)
    T = len(d) - 1
    for i in range(len(d)):
        S_, h = d["Surface (m²)"][i], d["Hauteur (m)"][i]
        dalle = S_ * p["hd"] / 100
        poutres = S_ * p["rp"]
        npot = S_ / p["maille"] if i < T else 0
        pot = npot * p["bc"] / 100 * p["hc"] / 100 * h
        voile = 0.0
        if d["Sous-sol"][i]:
            voile = p["perim"] * h * p["ev"] / 100
        elif d["Niveau"][i] == "RDC":
            voile = p["noyau"] * h * 0.2 * 0.5
        else:
            voile = p["noyau"] * h * 0.2 if i < T else 0.0
        b_tot = dalle + poutres + pot + voile
        acier = dalle * p["ra_d"] + poutres * p["ra_p"] + pot * p["ra_pt"] + voile * p["ra_v"]
        coff = S_ * (1 + 0.9 * p["rp"] / 0.06 * 0.3) + (npot * 2 * (p["bc"] + p["hc"]) / 100 * h) + 2 * voile / 0.2 * 0.9
        rows.append({"Niveau": d["Niveau"][i], "Dalle (m³)": dalle, "Poutres (m³)": poutres, "Poteaux (m³)": pot,
                     "Voiles (m³)": voile, "Béton (m³)": b_tot, "Acier (kg)": acier, "Coffrage (m²)": coff})
    return pd.DataFrame(rows)


# ===================== CALCULS : SOUS-SOL ET FONDATIONS =====================
def voile_enterre(h, K0, gam, q, hw, gsat=20.0):
    """Voile périphérique articulé en tête, encastré en pied. hw = hauteur d'eau au-dessus du pied (m).
    Retourne M_base, V_base, M_trav (kN·m/m, ELU) pour la poussée des terres + eau + surcharge."""
    z = np.linspace(0, h, 201)
    dz = z[1] - z[0]
    zw = h - hw
    sig_v = np.where(z <= zw, gam * z, gam * zw + (gsat - 9.81) * (z - zw))
    p_soil = K0 * sig_v
    p_w = np.where(z > zw, 9.81 * (z - zw), 0.0)
    p_q = np.full_like(z, K0 * q)
    a = h - z
    b = z
    mfix = lambda p: float((p * a * b * (h + b) / (2 * h ** 2) * dz).sum())
    rb = lambda p: float((p * a ** 2 * (3 * h - a) / (2 * h ** 3) * dz).sum())
    Mg = mfix(p_soil) + mfix(p_w)
    Mq = mfix(p_q)
    Rg = rb(p_soil) + rb(p_w)
    Rq = rb(p_q)
    Vg = float((p_soil + p_w).sum() * dz) - Rg
    Vq = float(p_q.sum() * dz) - Rq
    M_base = 1.35 * Mg + 1.5 * Mq
    V_base = 1.35 * Vg + 1.5 * Vq
    M_trav = 0.55 * M_base * 0.5
    return M_base, V_base, M_trav


def semelle_isolee(Ned, Nser, qadm, a_cm, D, fyk):
    gam_s, B = 18.0, 1.0
    for _ in range(30):
        h = max(0.4, (B - a_cm / 100) / 4 + 0.05)
        W = B * B * h * 25 + B * B * max(D - h, 0) * gam_s
        Bn = math.ceil(math.sqrt((Nser + W) / qadm) / 0.05) * 0.05
        if abs(Bn - B) < 1e-9:
            break
        B = Bn
    h = math.ceil(max(0.4, (B - a_cm / 100) / 4 + 0.05) / 0.05) * 0.05
    d = h - 0.06
    As = Ned * (B - a_cm / 100) / (8 * d * fyk / 1.15 * 1e3) * 1e4
    return B, h, As


# ===================== CALCULS : ACTIONS =====================
def vent_qp(z, vb0, z0, zmin):
    kr = 0.19 * (z0 / 0.05) ** 0.07
    ze = max(z, zmin)
    cr = kr * math.log(ze / z0)
    iv = 1.0 / math.log(ze / z0)
    return (1 + 7 * iv) * 0.5 * 1.25 * (cr * vb0) ** 2 / 1000.0


def spectre_ec8(T, ag, S_, TB, TC, TD, q, beta=0.2):
    if T <= TB:
        return ag * S_ * (2 / 3 + T / TB * (2.5 / q - 2 / 3))
    if T <= TC:
        return ag * S_ * 2.5 / q
    if T <= TD:
        return max(ag * S_ * 2.5 / q * TC / T, beta * ag)
    return max(ag * S_ * 2.5 / q * TC * TD / T ** 2, beta * ag)


def seisme_niveaux(niv, gstruct, psiE, ag, S_, TB, TC, TD, q, Ct):
    d = niv[niv["Cote plancher (m)"] >= -1e-9].reset_index(drop=True)
    H = float(d["Cote plancher (m)"].iloc[-1]) if len(d) else 3.0
    T1 = Ct * max(H, 3.0) ** 0.75
    Sd = spectre_ec8(T1, ag, S_, TB, TC, TD, q)
    W = (gstruct + d["G (kN/m²)"] + psiE * d["Q (kN/m²)"]) * d["Surface (m²)"]
    lam = 0.85 if (T1 <= 2 * TC and len(d) > 2) else 1.0
    Fb = Sd / G * float(W.sum()) * lam
    z = d["Cote plancher (m)"].clip(lower=0.5)
    Fi = Fb * W * z / float((W * z).sum())
    out = pd.DataFrame({"Niveau": d["Niveau"], "z (m)": d["Cote plancher (m)"], "Poids W (kN)": W.round(0),
                        "Force Fi (kN)": Fi.round(1)})
    out["Effort tranchant (kN)"] = out["Force Fi (kN)"][::-1].cumsum()[::-1].round(1)
    out["Moment (kN·m)"] = [round(float((out["Force Fi (kN)"][i:] * (out["z (m)"][i:] - out["z (m)"][i])).sum()), 0)
                             for i in range(len(out))]
    return out, T1, Sd, Fb, float(W.sum())


# ===================== CALCULS : THERMIQUE, INCENDIE, ASCENSEURS =====================
def unites_passage(effectif):
    if effectif <= 0:
        return 0
    if effectif <= 50:
        return 1
    if effectif <= 100:
        return 2
    return 2 + math.ceil((effectif - 100) / 100)


def largeur_up(up):
    return {0: 0.0, 1: 0.9, 2: 1.4}.get(up, 0.6 * up)


def ascenseurs(pop, H, v, cap_kg, arrets, pct5=0.07):
    C = max(1, int(cap_kg / 75 * 0.8))
    rtt = 2 * H / v + (arrets + 1) * 10 + C * 2.0 * 2
    cap5 = 300 * C / rtt
    return C, rtt, cap5, math.ceil(pop * pct5 / cap5) if pop > 0 else 0


def eval_beton(df):
    d = df.copy()
    d["Âge (j)"] = pd.to_numeric(d["Âge (j)"], errors="coerce")
    d["Résistance (MPa)"] = pd.to_numeric(d["Résistance (MPa)"], errors="coerce")
    d = d.dropna(subset=["Classe", "Âge (j)", "Résistance (MPa)"])
    rows = []
    for cl, g in d[d["Âge (j)"].round() == 28].groupby("Classe"):
        try:
            fck = float(str(cl).replace("C", "").split("/")[0])
        except ValueError:
            continue
        v = g["Résistance (MPa)"].values
        n = len(v)
        if n < 3:
            rows.append({"Classe": cl, "n": n, "fcm (MPa)": round(float(v.mean()), 1), "f min (MPa)": round(float(v.min()), 1),
                         "Statut": "⚠️ Échantillon insuffisant"})
            continue
        ok = v.mean() >= fck + 4 and v.min() >= fck - 4
        rows.append({"Classe": cl, "n": n, "fcm (MPa)": round(float(v.mean()), 1), "f min (MPa)": round(float(v.min()), 1),
                     "Statut": "✅ Conforme" if ok else "❌ Non conforme"})
    return pd.DataFrame(rows, columns=["Classe", "n", "fcm (MPa)", "f min (MPa)", "Statut"])


def planning_par_niveaux(niv, debut):
    """Planning type généré à partir des niveaux R-n / R+n."""
    rows = [("Installation de chantier", 15, ""), ("Terrassement et soutènement", 25, "Installation de chantier"),
            ("Fondations / radier", 30, "Terrassement et soutènement")]
    prev = "Fondations / radier"
    for _, r in niv.iterrows():
        n = str(r["Niveau"])
        if n == "Terrasse":
            rows.append(("Structure Terrasse + acrotères", 15, prev))
            prev = "Structure Terrasse + acrotères"
        else:
            rows.append((f"Structure {n}", 20 if r["Sous-sol"] else 18, prev))
            prev = f"Structure {n}"
    rows += [("Maçonnerie et cloisons", 60, prev), ("Étanchéité et toiture", 15, prev),
             ("Lots techniques", 80, "Maçonnerie et cloisons"), ("Enduits et façades", 50, "Maçonnerie et cloisons"),
             ("Revêtements et peinture", 60, "Lots techniques;Enduits et façades"),
             ("Réception", 10, "Revêtements et peinture;Étanchéité et toiture")]
    return pd.DataFrame([{"Tâche": a, "Début": debut, "Durée (j)": b, "Avancement (%)": 0.0, "Responsable": "",
                          "Prédécesseurs": c} for a, b, c in rows])


# ===================== ÉTAT INITIAL =====================
def init_state():
    S = st.session_state
    if "init" in S:
        return
    today = date.today()
    rng = np.random.default_rng(21)
    S.projet = dict(nom="Résidence Les Orchidées (2 SS + RDC + R+5)", moa="SCI Horizon", lieu="", usage="Mixte commerce + habitation",
                    n_ss=2, n_et=5, budget=14_000_000.0, debut=today - timedelta(days=150), fin=today + timedelta(days=420),
                    devise="€")
    S.niveaux = gen_niveaux(2, 5, 700.0, 560.0, "Commerce", "Habitation")
    S.sol = dict(qadm=220.0, gam=18.0, phi=30.0, q=10.0, nappe=1.5)
    names = list(S.niveaux["Niveau"])
    rows = []
    for i in range(14):
        p = list(PARAMS)[i % 5]
        mu, sd = {"Affaissement (slump)": (110, 12), "Température béton": (22, 3), "Désaplomb poteau": (2, 3),
                  "Flèche dalle": (4, 1.2), "Fissure (ouverture)": (0.1, 0.05)}[p]
        rows.append({"Date": today - timedelta(days=28 - 2 * i), "Niveau": names[i % 5], "Paramètre": p,
                     "Valeur": round(float(mu + rng.normal(0, sd)), 2), "Unité": PARAMS[p], "Opérateur": "Contrôle chantier",
                     "Remarque": ""})
    S.releves = coerce(pd.DataFrame(rows), "releves")
    acts = ["Coulage radier général", "Voiles périphériques R-2", "Ferraillage poteaux R-1", "Bétonnage dalle RDC",
            "Coffrage plancher R+1", "Montage poteaux R+2"]
    S.journal = coerce(pd.DataFrame([{"Date": today - timedelta(days=10 - 2 * i), "Météo": METEO[i % 3],
                                      "Effectif": int(25 + rng.integers(0, 20)), "Activités": a,
                                      "Observations": "RAS" if i % 2 == 0 else "Retard livraison acier de 1 jour"}
                                     for i, a in enumerate(acts)]), "journal")
    et = [{"Date": today - timedelta(days=80 - 6 * i), "Élément": f"Radier / voiles SS {i + 1}", "Classe": "C30/37", "Âge (j)": 28.0,
           "Résistance (MPa)": round(float(rng.normal(40, 2.0)), 1)} for i in range(6)]
    et += [{"Date": today - timedelta(days=50 - 6 * i), "Élément": f"Dalle niveau {i + 1}", "Classe": "C25/30", "Âge (j)": 28.0,
            "Résistance (MPa)": round(float(rng.normal(33.5, 2.0)), 1)} for i in range(6)]
    S.essais = coerce(pd.DataFrame(et), "essais")
    mt = [("01 Terrassement et soutènement", "Fouille en déblai (2 sous-sols)", "m³", 7000, 14),
          ("01 Terrassement et soutènement", "Soutènement (parois, butons)", "m²", 1200, 180),
          ("02 Fondations", "Béton du radier général", "m³", 700, 330), ("02 Fondations", "Acier HA fondations", "kg", 70000, 1.7),
          ("03 Structure BA", "Béton de structure (dalles, poteaux, voiles)", "m³", 2600, 360),
          ("03 Structure BA", "Acier HA superstructure", "kg", 260000, 1.7), ("03 Structure BA", "Coffrage", "m²", 14000, 28),
          ("04 Maçonnerie et cloisons", "Maçonnerie et cloisons", "m²", 9000, 36),
          ("05 Étanchéité", "Étanchéité toiture-terrasse", "m²", 600, 55), ("06 Menuiseries", "Menuiseries alu double vitrage", "u", 150, 780),
          ("07 Revêtements", "Enduits et façades", "m²", 5200, 32), ("07 Revêtements", "Carrelage et peinture", "m²", 6800, 38),
          ("08 Lots techniques", "Électricité, plomberie, CVC", "forfait", 1, 2_100_000),
          ("08 Lots techniques", "Ascenseurs", "u", 2, 48000), ("08 Lots techniques", "Sécurité incendie et désenfumage", "forfait", 1, 320000),
          ("09 Parkings", "Rampes, marquage et équipements", "forfait", 1, 160000), ("10 Divers", "Études, contrôle et essais", "forfait", 1, 420000)]
    S.metre = coerce(pd.DataFrame(mt, columns=COLS["metre"]), "metre")
    nv = niveaux_calc(S.niveaux)
    tdf = planning_par_niveaux(nv, today)
    sched, _ = cpm(tdf)
    tdf["Début"] = [S.projet["debut"] + timedelta(days=int(v)) for v in sched["ES"]]
    tdf["Avancement (%)"] = [100.0 if i < 5 else 60.0 if i == 5 else 0.0 for i in range(len(tdf))]
    S.taches = coerce(tdf, "taches")
    rk = [("Chute de hauteur (rives de dalle, trémies)", "Structure", 3, 5, "Garde-corps, filets, harnais"),
          ("Éboulement / glissement de la fouille", "Terrassement", 2, 5, "Soutènement, blindage, suivi topographique"),
          ("Venue d'eau / remontée de nappe", "Sous-sol", 3, 4, "Pompage, rabattement, étanchéité"),
          ("Effondrement d'étaiement", "Structure", 2, 5, "Plan d'étaiement, délais de décoffrage"),
          ("Chute d'objets / grue", "Levage", 3, 4, "Zones balisées, élingage contrôlé"),
          ("Électrisation", "Installation", 2, 4, "Différentiels 30 mA, vérifications"),
          ("Incendie de chantier (soudure, déchets)", "Second œuvre", 2, 4, "Permis de feu, extincteurs"),
          ("Coactivité entre corps d'état", "Finitions", 4, 3, "Plan de coordination")]
    S.risques = coerce(pd.DataFrame(rk, columns=COLS["risques"]), "risques")
    B = S.projet["budget"]
    S.ev = coerce(pd.DataFrame({"Mois": list(range(1, 15)),
                                "PV cumulé": [B * x for x in (.03, .08, .14, .21, .29, .37, .46, .55, .64, .73, .82, .90, .96, 1.0)],
                                "EV cumulée": [B * x for x in (.03, .075, .13, .19, .26)] + [np.nan] * 9,
                                "AC cumulé": [B * x for x in (.032, .08, .14, .205, .28)] + [np.nan] * 9}), "ev")
    S.couches = coerce(pd.DataFrame({"Matériau": ["Enduit ciment", "Parpaing creux (équiv.)", "Polystyrène expansé", "Plâtre / BA13"],
                                     "Épaisseur (cm)": [2.0, 20.0, 10.0, 1.3]}), "couches")
    S.parois = coerce(pd.DataFrame({"Paroi": ["Murs extérieurs", "Toiture-terrasse", "Plancher bas", "Vitrages", "Portes"],
                                    "Surface (m²)": [2100.0, 520.0, 560.0, 480.0, 40.0],
                                    "U (W/m²·K)": [0.40, 0.25, 0.35, 1.6, 1.8]}), "parois")
    S.init = True


def hauteurs(S):
    nv = niveaux_calc(S.niveaux)
    top = float(nv["Cote plancher (m)"].max()) if len(nv) else 0.0
    prof = -float(nv["Cote plancher (m)"].min()) if len(nv) else 0.0
    return nv, top, max(prof, 0.0)


def fig_elevation(nv):
    fig = go.Figure()
    cmap = {"Parking": GRIS, "Habitation": ACCENT, "Bureaux": BLEU, "Commerce": ORANGE, "Local technique": NOIR,
            "Terrasse inaccessible": VERT, "Terrasse accessible": VERT}
    wmax = float(nv["Surface (m²)"].max()) or 1.0
    for _, r in nv.iterrows():
        w = 0.35 + 0.65 * r["Surface (m²)"] / wmax
        z0, h = r["Cote plancher (m)"], max(r["Hauteur (m)"], 0.4)
        fig.add_shape(type="rect", x0=-w / 2, x1=w / 2, y0=z0, y1=z0 + h, fillcolor=cmap.get(r["Usage"], GRIS),
                      line=dict(color="#FFFFFF", width=2), opacity=0.92)
        fig.add_annotation(x=0, y=z0 + h / 2, text=f"<b>{r['Niveau']}</b>  {z0:+.2f} m", showarrow=False,
                           font=dict(color="#FFFFFF", size=12))
    top = float(nv["Cote plancher (m)"].max()) + 1
    bot = float(nv["Cote plancher (m)"].min()) - 1
    fig.add_hline(y=0, line_dash="dot", line_color=ROUGE, annotation_text="Terrain naturel")
    fig.update_xaxes(visible=False, range=[-0.8, 0.8])
    fig.update_yaxes(range=[bot, top], title="Cote (m)")
    fig.update_layout(title="Coupe schématique R-n / R+n", showlegend=False)
    return fig


# ===================== PAGE : TABLEAU DE BORD =====================
def page_dashboard():
    S = st.session_state
    P = S.projet
    nv, top, prof = hauteurs(S)
    hero("🏢 Tableau de bord du projet", f"{P['nom']} — {P['usage']}")
    with st.expander("✏️ Informations générales du projet"):
        c1, c2, c3 = st.columns(3)
        P["nom"] = c1.text_input("Nom du projet", P["nom"])
        P["moa"] = c2.text_input("Maître d'ouvrage", P["moa"])
        P["lieu"] = c3.text_input("Localisation", P["lieu"])
        c1, c2, c3, c4 = st.columns(4)
        P["usage"] = c1.selectbox("Usage", USAGE_PROJET, index=USAGE_PROJET.index(P["usage"]) if P["usage"] in USAGE_PROJET else 0)
        P["budget"] = float(c2.number_input("Budget cible HT", 0.0, 1e11, float(P["budget"]), 50000.0))
        P["debut"] = c3.date_input("Début des travaux", P["debut"])
        P["fin"] = c4.date_input("Fin contractuelle", P["fin"])
        devs = ["€", "FCFA", "$", "MAD", "DZD"]
        P["devise"] = c1.selectbox("Devise", devs, index=devs.index(P["devise"]) if P["devise"] in devs else 0)
        st.caption("Le nombre de niveaux se règle dans « Niveaux R-n / R+n ».")
    dev = P["devise"]
    plancher = float(nv[nv["Usage"].str.startswith("Terrasse") == False]["Surface (m²)"].sum())
    t = S.taches.dropna(subset=["Tâche"])
    dur = num(t, "Durée (j)")
    avanc = float((dur * num(t, "Avancement (%)")).sum() / dur.sum()) if dur.sum() > 0 else 0.0
    tot = float(metre_totals(S.metre)["Total"].sum())
    ess = eval_beton(S.essais)
    r = S.risques
    n_crit = int((num(r, "Probabilité") * num(r, "Gravité") >= 15).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Configuration", f"R-{P['n_ss']} / R+{P['n_et']}" if P["n_ss"] else f"R+{P['n_et']}")
    c2.metric("Hauteur hors sol", f"{top:.1f} m")
    c3.metric("Profondeur des sous-sols", f"{prof:.1f} m")
    c4.metric("Surface de plancher", f"{fmt(plancher, 0)} m²")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avancement global", f"{avanc:.1f} %")
    c2.metric("Estimation du métré HT", f"{fmt(tot, 0)} {dev}",
              f"{(tot - P['budget']) / P['budget'] * 100:+.1f} % vs budget" if P["budget"] else None, delta_color="inverse")
    c3.metric("Ratio / m² de plancher", f"{fmt(tot / plancher, 0) if plancher else '—'} {dev}/m²")
    c4.metric("Jours avant échéance", f"{(P['fin'] - date.today()).days} j")
    c1, c2, c3 = st.columns(3)
    c1.metric("Classes de béton conformes", f"{int((ess['Statut'] == '✅ Conforme').sum())} / {len(ess)}")
    c2.metric("Risques critiques (≥15)", n_crit)
    c3.metric("Effectif moyen", f"{num(S.journal, 'Effectif').mean():.0f} pers." if len(S.journal) else "—")
    g1, g2 = st.columns([1, 1])
    with g1:
        pplot(fig_elevation(nv), 500)
    with g2:
        tt = t.copy()
        tt["Avancement (%)"] = num(tt, "Avancement (%)")
        fig = px.bar(tt, x="Avancement (%)", y="Tâche", orientation="h", range_x=[0, 100], color="Avancement (%)",
                     color_continuous_scale=[[0, ACCENT_CLAIR], [1, NOIR]], title="Avancement par tâche")
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(coloraxis_showscale=False)
        pplot(fig, 500)
    lots = metre_totals(S.metre).groupby("Lot", as_index=False)["Total"].sum()
    if len(lots) and lots["Total"].sum() > 0:
        pplot(px.pie(lots, names="Lot", values="Total", hole=0.5, title="Répartition du coût par lot",
                     color_discrete_sequence=PALETTE + ["#6D597A", "#B56576", "#355070"]), 380)


# ===================== PAGE : NIVEAUX =====================
def page_niveaux():
    S = st.session_state
    P = S.projet
    hero("🏗️ Niveaux R-n / R+n", "Définir les sous-sols et les étages : hauteurs, surfaces, usages, charges et cotes")
    with st.expander("⚙️ Générer ou régénérer la liste des niveaux", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        nss = int(c1.number_input("Sous-sols (n de R-n)", 0, 8, int(P["n_ss"]), 1))
        net = int(c2.number_input("Étages (n de R+n)", 0, 60, int(P["n_et"]), 1))
        sss = float(c3.number_input("Surface par sous-sol (m²)", 50.0, 50000.0, 700.0, 10.0))
        set_ = float(c4.number_input("Surface par étage (m²)", 50.0, 50000.0, 560.0, 10.0))
        u1, u2 = st.columns(2)
        ur = u1.selectbox("Usage du RDC", [k for k in USAGES if not k.startswith("Terrasse") and k != "Parking"], index=2)
        ue = u2.selectbox("Usage des étages", [k for k in USAGES if not k.startswith("Terrasse") and k != "Parking"], index=0)
        if st.button("🔄 Générer les niveaux"):
            P["n_ss"], P["n_et"] = nss, net
            set_df("niveaux", gen_niveaux(nss, net, sss, set_, ur, ue))
            st.rerun()
    note("Modifier librement les hauteurs, surfaces, usages et charges. Le niveau « RDC » est la cote 0,00 ; le dernier niveau est la terrasse.")
    editor("niveaux", {"Usage": st.column_config.SelectboxColumn("Usage", options=list(USAGES))})
    nv, top, prof = hauteurs(S)
    if nv.empty:
        st.info("Aucun niveau défini.")
        return
    hors = nv[~nv["Usage"].str.startswith("Terrasse")]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Niveaux", len(nv))
    c2.metric("Hauteur hors sol", f"{top:.2f} m")
    c3.metric("Profondeur sous le RDC", f"{prof:.2f} m")
    c4.metric("Surface de plancher totale", f"{fmt(hors['Surface (m²)'].sum(), 0)} m²")
    g1, g2 = st.columns([1, 1])
    with g1:
        pplot(fig_elevation(nv), 520)
    with g2:
        show_df(nv[["Niveau", "Cote plancher (m)", "Hauteur (m)", "Surface (m²)", "Usage", "G (kN/m²)", "Q (kN/m²)"]].round(2))
        by = hors.groupby("Usage", as_index=False)["Surface (m²)"].sum()
        pplot(px.pie(by, names="Usage", values="Surface (m²)", hole=0.5, title="Surfaces par usage",
                     color_discrete_sequence=PALETTE), 300)


# ===================== PAGE : COLLECTE =====================
def page_collecte():
    S = st.session_state
    hero("📥 Collecte de données de chantier", "Journal, relevés de contrôle par niveau, import / fusion de fichiers")
    names = [str(x) for x in S.niveaux["Niveau"]] or ["RDC"]
    t1, t2, t3 = st.tabs(["📓 Journal de chantier", "📏 Relevés et mesures", "📎 Import / fusion"])
    with t1:
        with st.form("form_journal", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Date", date.today())
            m = c2.selectbox("Météo", METEO)
            e = c3.number_input("Effectif présent", 0, 1000, 30)
            act = st.text_area("Activités réalisées")
            obs = st.text_area("Incidents / observations")
            if st.form_submit_button("➕ Ajouter l'entrée"):
                add_rows("journal", pd.DataFrame([{"Date": d, "Météo": m, "Effectif": e, "Activités": act, "Observations": obs}]))
                st.rerun()
        editor("journal", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                           "Météo": st.column_config.SelectboxColumn("Météo", options=METEO)})
    with t2:
        with st.form("form_releve", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            d = c1.date_input("Date du relevé", date.today())
            nvl = c2.selectbox("Niveau", names)
            p = c3.selectbox("Paramètre", list(PARAMS))
            v = c4.number_input("Valeur", value=0.0, step=0.1, format="%.2f")
            c1, c2 = st.columns(2)
            op = c1.text_input("Opérateur")
            rem = c2.text_input("Remarque")
            if st.form_submit_button("➕ Enregistrer le relevé"):
                add_rows("releves", pd.DataFrame([{"Date": d, "Niveau": nvl, "Paramètre": p, "Valeur": v, "Unité": PARAMS[p],
                                                   "Opérateur": op, "Remarque": rem}]))
                st.rerun()
        editor("releves", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                           "Paramètre": st.column_config.SelectboxColumn("Paramètre", options=list(PARAMS))})
        r = S.releves.copy()
        r["Valeur"] = pd.to_numeric(r["Valeur"], errors="coerce")
        r = r.dropna(subset=["Date", "Valeur", "Paramètre"])
        if len(r):
            sel = st.selectbox("Paramètre à analyser", sorted(r["Paramètre"].unique()))
            rr = r[r["Paramètre"] == sel].sort_values("Date")
            fig = px.line(rr, x="Date", y="Valeur", color="Niveau", markers=True, title=f"{sel} — évolution",
                          color_discrete_sequence=PALETTE)
            lo, hi = TOLERANCES.get(sel, (None, None))
            for lim in (lo, hi):
                if lim is not None:
                    fig.add_hline(y=lim, line_dash="dash", line_color=ROUGE)
            pplot(fig, 340)
    with t3:
        key = st.selectbox("Jeu de données cible", list(LABELS), format_func=lambda k: LABELS[k])
        st.caption("Colonnes attendues : " + " | ".join(COLS[key]))
        up = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx"])
        if up is not None:
            try:
                df = pd.read_csv(up, sep=None, engine="python") if up.name.lower().endswith(".csv") else pd.read_excel(up)
                manque = [c for c in COLS[key] if c not in df.columns]
                if manque:
                    st.error("Colonnes manquantes : " + ", ".join(manque))
                else:
                    df = coerce(df, key)
                    show_df(df.head(20))
                    mode = st.radio("Mode", ["Ajouter aux données existantes", "Remplacer les données"], horizontal=True)
                    if st.button("📥 Importer"):
                        set_df(key, pd.concat([S[key], df], ignore_index=True) if mode.startswith("Ajouter") else df)
                        st.rerun()
            except Exception as ex:
                st.error(f"Lecture impossible : {ex}")


# ===================== PAGE : DESCENTE DE CHARGES =====================
def page_charges():
    S = st.session_state
    nv, top, prof = hauteurs(S)
    hero("⚖️ Descente de charges", "Cumul des charges par poteau, dégression des charges d'exploitation, prédimensionnement")
    if len(nv) < 2:
        st.info("Définir au moins 2 niveaux.")
        return
    c1, c2, c3, c4 = st.columns(4)
    Ss = c1.number_input("Surface d'influence du poteau (m²)", 4.0, 100.0, 30.0, 1.0)
    hd = c2.number_input("Épaisseur de dalle (cm)", 12.0, 40.0, 22.0, 1.0)
    classe = c3.selectbox("Classe du béton", CLASSES_BETON, index=2)
    rho = c4.number_input("Taux d'armatures ρ (%)", 0.5, 4.0, 1.5, 0.1) / 100
    c1, c2, c3 = st.columns(3)
    bc = c1.number_input("Section poteau b (cm)", 20.0, 120.0, 40.0, 5.0)
    hc = c2.number_input("Section poteau h (cm)", 20.0, 120.0, 40.0, 5.0)
    psi0 = c3.number_input("ψ0 (dégressivité)", 0.3, 1.0, 0.7, 0.05)
    df = descente(nv, Ss, hd, bc, hc, psi0, classe, rho)
    cA, cB = st.columns([1, 1])
    with cA:
        show_df(df)
    with cB:
        fig = go.Figure()
        fig.add_bar(y=df["Poteau (pied du niveau)"], x=df["G cumulé (kN)"], orientation="h", name="G", marker_color=NOIR)
        fig.add_bar(y=df["Poteau (pied du niveau)"], x=df["Q cumulé dégressé (kN)"], orientation="h", name="Q dégressé",
                    marker_color=ACCENT)
        fig.update_layout(barmode="stack", title="Charges cumulées au pied de chaque niveau (kN)")
        pplot(fig, 420)
    pied = df.iloc[0]
    st.subheader("Poteau le plus chargé (pied)")
    c1, c2, c3 = st.columns(3)
    c1.metric("N_Ed (ELU)", f"{fmt(pied['N_Ed ELU (kN)'], 0)} kN")
    c2.metric("N_ser (ELS)", f"{fmt(pied['N_ser ELS (kN)'], 0)} kN")
    c3.metric("Côté carré minimal", f"{pied['Côté carré mini (cm)']:.0f} cm")
    verdict(min(bc, hc) >= pied["Côté carré mini (cm)"] * 0.9 and bc * hc >= pied["Côté carré mini (cm)"] ** 2 * 0.95,
            f"La section {bc:.0f}×{hc:.0f} cm convient au pied (ordre de grandeur).",
            f"Section {bc:.0f}×{hc:.0f} cm insuffisante : prévoir au moins {pied['Côté carré mini (cm)']:.0f} cm de côté.")
    note("ELU : N = 1,35 G + 1,5 Q. Dégression : α_n = (2 + (n−2)ψ0)/n sur les étages courants. Le prédimensionnement "
         "suppose N ≤ 0,7·Ac·(f_cd + ρ f_yd). Les poteaux de façade et de rive sont à majorer pour la flexion.")
    # variation de section
    df2 = df.copy()
    df2["Section proposée (cm)"] = df2["Côté carré mini (cm)"].apply(lambda s: f"{max(25, math.ceil(s / 5) * 5):.0f} × {max(25, math.ceil(s / 5) * 5):.0f}")
    st.subheader("Sections proposées par niveau")
    show_df(df2[["Poteau (pied du niveau)", "N_Ed ELU (kN)", "Section proposée (cm)"]])


# ===================== PAGE : BÉTON ARMÉ =====================
def page_beton_arme():
    hero("🧱 Béton armé : poutre, poteau, dalle", "Flexion simple, effort tranchant, poinçonnement, armatures")
    t1, t2, t3 = st.tabs(["Poutre / bande de dalle", "Poinçonnement dalle-poteau", "Armatures de dalle"])
    with t1:
        c1, c2, c3, c4 = st.columns(4)
        L = c1.number_input("Portée L (m)", 1.0, 20.0, 6.0, 0.5)
        b = c2.number_input("Largeur b (mm)", 150.0, 1000.0, 300.0, 10.0)
        h = c3.number_input("Hauteur h (mm)", 200.0, 1500.0, 550.0, 10.0)
        enr = c4.number_input("Enrobage + cadre (mm)", 20.0, 80.0, 45.0, 1.0)
        c1, c2, c3, c4 = st.columns(4)
        g = c1.number_input("g (kN/m)", 0.0, 500.0, 25.0, 1.0)
        q = c2.number_input("q (kN/m)", 0.0, 500.0, 10.0, 1.0)
        classe = c3.selectbox("Béton", CLASSES_BETON, index=2, key="poutre_cl")
        fyk = c4.selectbox("Acier fyk (MPa)", [400, 500], index=1)
        sch = st.radio("Schéma statique", ["Isostatique (appuis simples)", "Continue (travée de rive)", "Continue (travée intermédiaire)"],
                       horizontal=True)
        pu = 1.35 * g + 1.5 * q
        if sch.startswith("Iso"):
            Mt, Ma, V = pu * L ** 2 / 8, 0.0, pu * L / 2
        elif "rive" in sch:
            Mt, Ma, V = 0.08 * pu * L ** 2 * 1.0, 0.125 * pu * L ** 2, 0.6 * pu * L
        else:
            Mt, Ma, V = 0.07 * pu * L ** 2, 0.10 * pu * L ** 2, 0.5 * pu * L
        d = h - enr
        fck = beton_props(classe)["fck"]
        rt = flexion_rect(Mt, b, d, fck, fyk)
        ra = flexion_rect(Ma, b, d, fck, fyk)
        asmin = as_min_flex(b, d, fck, fyk)
        As_t = max(rt["As"], asmin)
        vrd = vrd_c(b, d, fck, max(As_t, 1.0))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("p_u (ELU)", f"{pu:.1f} kN/m")
        c2.metric("M travée", f"{Mt:.1f} kN·m")
        c3.metric("M appui", f"{Ma:.1f} kN·m")
        c4.metric("V_Ed", f"{V:.1f} kN")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("As travée", f"{As_t / 100:.2f} cm²")
        c2.metric("As appui", f"{max(ra['As'], asmin if Ma > 0 else 0) / 100:.2f} cm²")
        c3.metric("μ travée", f"{rt['mu']:.3f}")
        c4.metric("V_Rd,c", f"{vrd:.1f} kN")
        verdict(not rt["double"], "Section simplement armée (μ ≤ μ_lim).", "μ > μ_lim : section à armatures comprimées ou à agrandir.")
        verdict(V <= vrd, "Pas d'armatures d'effort tranchant nécessaires par calcul (cadres minimaux).",
                "V_Ed > V_Rd,c : armatures d'effort tranchant à dimensionner (bielles).")
        st.markdown("**Choix des barres (travée)**")
        show_df(options_barres(As_t, b, enr - 10, 8))
        Ecm = beton_props(classe)["Ecm"] * 1e3
        flc = 5 * (0.7 * pu) * (L * 1000) ** 4 / (384 * Ecm * (b * h ** 3 / 12)) * 1.0
        st.caption(f"Flèche élastique indicative (section brute, 0,7·p_u) ≈ {flc:.1f} mm ; limite L/250 = {L * 1000 / 250:.0f} mm "
                   "(la fissuration et le fluage l'augmentent : à vérifier).")
        xs = np.linspace(0, L, 100)
        if sch.startswith("Iso"):
            M = pu * xs * (L - xs) / 2
        else:
            M = -Ma * (1 - 4 * xs * (L - xs) / L ** 2) + Mt * 4 * xs * (L - xs) / L ** 2
        fig = go.Figure(go.Scatter(x=xs, y=-M, fill="tozeroy", line_color=ACCENT, name="M (kN·m)"))
        fig.update_layout(title="Diagramme des moments (convention : tendu en bas vers le bas)", xaxis_title="x (m)",
                          yaxis_title="M (kN·m)")
        pplot(fig, 320)
    with t2:
        c1, c2, c3, c4 = st.columns(4)
        N = c1.number_input("Charge N_Ed au poteau (kN)", 50.0, 20000.0, 1500.0, 50.0)
        bcc = c2.number_input("Poteau b (mm)", 200.0, 1200.0, 400.0, 10.0)
        hcc = c3.number_input("Poteau h (mm)", 200.0, 1200.0, 400.0, 10.0)
        ep = c4.number_input("Épaisseur dalle (mm)", 150.0, 800.0, 250.0, 10.0)
        c1, c2, c3 = st.columns(3)
        pk = c1.number_input("Charge répartie ELU (kPa)", 0.0, 100.0, 12.0, 1.0)
        cl = c2.selectbox("Béton", CLASSES_BETON, index=2, key="poin_cl")
        rh = c3.number_input("ρ armatures tendues (%)", 0.2, 2.0, 0.8, 0.1) / 100
        dd = ep - 35
        vE, vR, ok = poinconnement(N, bcc, hcc, dd, pk, beton_props(cl)["fck"], rh)
        c1, c2, c3 = st.columns(3)
        c1.metric("v_Ed", f"{vE:.2f} MPa")
        c2.metric("v_Rd,c", f"{vR:.2f} MPa")
        c3.metric("Taux", f"{vE / vR * 100:.0f} %")
        verdict(ok, "Poinçonnement vérifié sans armature.", "Poinçonnement non vérifié : épaissir, chapiteau ou armatures de poinçonnement.")
        if not ok:
            for e in range(int(ep) + 10, 801, 10):
                v2, r2, o2 = poinconnement(N, bcc, hcc, e - 35, pk, beton_props(cl)["fck"], rh)
                if o2:
                    st.info(f"Épaisseur minimale pour vérifier sans armature : ≈ {e} mm.")
                    break
    with t3:
        c1, c2, c3, c4 = st.columns(4)
        lx = c1.number_input("Portée lx (m)", 2.0, 10.0, 5.0, 0.25)
        ly = c2.number_input("Portée ly (m)", 2.0, 15.0, 6.0, 0.25)
        e = c3.number_input("Épaisseur (mm)", 120.0, 400.0, 200.0, 10.0)
        cl = c4.selectbox("Béton", CLASSES_BETON, index=1, key="dalle_cl")
        c1, c2 = st.columns(2)
        gd = c1.number_input("G total (kN/m²)", 0.0, 30.0, 6.5, 0.5)
        qd = c2.number_input("Q (kN/m²)", 0.0, 20.0, 2.5, 0.5)
        pu = 1.35 * gd + 1.5 * qd
        alpha = min(lx, ly) / max(lx, ly)
        lx = min(lx, ly)
        if alpha < 0.4:
            mx, my = pu * lx ** 2 / 8, 0.0
            typ = "Portée unidirectionnelle"
        else:
            mux = {1.0: 0.0368, 0.9: 0.0456, 0.8: 0.0561, 0.7: 0.0684, 0.6: 0.0810, 0.5: 0.0966}
            k = min(mux, key=lambda x: abs(x - alpha))
            muy = {1.0: 0.9543, 0.9: 0.8875, 0.8: 0.8251, 0.7: 0.7655, 0.6: 0.7127, 0.5: 0.6628}
            mx = mux[k] * pu * lx ** 2
            my = muy[k] * mx
            typ = "Dalle portant dans les deux sens"
        d = e - 30
        fck, fyk = beton_props(cl)["fck"], 500
        rx = flexion_rect(0.75 * mx, 1000, d, fck, fyk)
        ry = flexion_rect(0.75 * my, 1000, d - 10, fck, fyk)
        asm = as_min_flex(1000, d, fck, fyk)
        c1, c2, c3 = st.columns(3)
        c1.metric("Type", typ)
        c2.metric("M_x travée (0,75·M0)", f"{0.75 * mx:.1f} kN·m/m")
        c3.metric("M_y travée", f"{0.75 * my:.1f} kN·m/m")
        c1, c2 = st.columns(2)
        c1.metric("Armatures sens x", choisir_armature(max(rx["As"], asm), e), f"{max(rx['As'], asm) / 100:.2f} cm²/m")
        c2.metric("Armatures sens y", choisir_armature(max(ry["As"], asm * 0.8), e), f"{max(ry['As'], asm * 0.8) / 100:.2f} cm²/m")
        note("Dalle sur appuis simples avec coefficients de Pigeaud/BAEL simplifiés ; moments de travée = 0,75·M0, appuis = 0,5·M0. "
             "Armatures minimales selon EC2 (As,min).")


# ===================== PAGE : SOUS-SOLS ET FONDATIONS =====================
def page_fondations():
    S = st.session_state
    nv, top, prof = hauteurs(S)
    sol = S.sol
    hero("⛏️ Sous-sols et fondations", "Voiles enterrés, poussée des terres et de l'eau, semelles, radier, flottaison, rampe de parking")
    c1, c2, c3, c4, c5 = st.columns(5)
    sol["qadm"] = c1.number_input("Contrainte admissible (kPa)", 50.0, 1500.0, float(sol["qadm"]), 10.0)
    sol["gam"] = c2.number_input("γ sol (kN/m³)", 14.0, 23.0, float(sol["gam"]), 0.5)
    sol["phi"] = c3.number_input("φ' (°)", 15.0, 45.0, float(sol["phi"]), 1.0)
    sol["q"] = c4.number_input("Surcharge voisine (kPa)", 0.0, 100.0, float(sol["q"]), 5.0)
    sol["nappe"] = c5.number_input("Profondeur nappe (m / TN)", 0.0, 30.0, float(sol["nappe"]), 0.5)
    t1, t2, t3, t4 = st.tabs(["Voile périphérique", "Semelle isolée", "Radier et flottaison", "Rampe de parking"])
    with t1:
        if prof <= 0:
            st.info("Aucun sous-sol défini : générer des niveaux R-n pour utiliser cet outil.")
        h = st.number_input("Hauteur libre du voile (m)", 1.0, 20.0, max(float(prof), 2.8), 0.1)
        ev = st.number_input("Épaisseur du voile (cm)", 15.0, 60.0, 25.0, 1.0)
        cl = st.selectbox("Béton", CLASSES_BETON, index=2, key="voile_cl")
        K0 = 1 - math.sin(math.radians(sol["phi"]))
        zw_ok = sol["nappe"] < h
        hw = max(h - sol["nappe"], 0.0) if zw_ok else 0.0
        M_b, V_b, M_t = voile_enterre(h, K0, sol["gam"], sol["q"], hw)
        d = ev * 10 - 45
        fck = beton_props(cl)["fck"]
        rb = flexion_rect(M_b, 1000, d, fck, 500)
        rt = flexion_rect(M_t, 1000, d, fck, 500)
        asm = as_min_flex(1000, d, fck, 500)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("K0 = 1 − sin φ'", f"{K0:.2f}")
        c2.metric("Hauteur d'eau", f"{hw:.2f} m")
        c3.metric("M encastrement ELU", f"{M_b:.1f} kN·m/m")
        c4.metric("V_Ed pied", f"{V_b:.1f} kN/m")
        c1, c2 = st.columns(2)
        c1.metric("Armatures au pied (face terre)", choisir_armature(max(rb["As"], asm), ev * 10),
                  f"{max(rb['As'], asm) / 100:.2f} cm²/m")
        c2.metric("Armatures en travée (face int.)", choisir_armature(max(rt["As"], asm), ev * 10),
                  f"{max(rt['As'], asm) / 100:.2f} cm²/m")
        verdict(V_b <= vrd_c(1000, d, fck, max(rb["As"], asm)), "Effort tranchant repris par le béton seul.",
                "Effort tranchant élevé : épaissir le voile ou ajouter des armatures transversales.")
        z = np.linspace(0, h, 100)
        zw = h - hw
        sv = np.where(z <= zw, sol["gam"] * z, sol["gam"] * zw + 10.19 * (z - zw))
        pt = K0 * sv + K0 * sol["q"] + np.where(z > zw, 9.81 * (z - zw), 0.0)
        fig = go.Figure(go.Scatter(x=pt, y=-z, fill="tozerox", line_color=ACCENT))
        fig.update_layout(title="Poussée totale (terres + surcharge + eau) en kPa", xaxis_title="kPa", yaxis_title="Profondeur (m)")
        pplot(fig, 340)
        note("Modèle : voile articulé en tête (plancher haut) et encastré en pied, K0 au repos. Les poussées sont à compléter par "
             "l'étude géotechnique ; vérifier l'étanchéité (cuvelage) sous le niveau de nappe.")
    with t2:
        c1, c2, c3, c4 = st.columns(4)
        Ned = c1.number_input("N_Ed (kN)", 100.0, 30000.0, 1800.0, 50.0)
        Nser = c2.number_input("N_ser (kN)", 100.0, 30000.0, 1300.0, 50.0)
        a = c3.number_input("Côté du poteau (cm)", 20.0, 120.0, 40.0, 5.0)
        D = c4.number_input("Profondeur d'assise (m)", 0.5, 12.0, max(prof + 0.5, 1.0), 0.1)
        B, hh, As = semelle_isolee(Ned, Nser, sol["qadm"], a, D, 500.0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Côté B (carrée)", f"{B:.2f} m")
        c2.metric("Hauteur h", f"{hh:.2f} m")
        c3.metric("As par sens", f"{As:.1f} cm²", choisir_armature(As / B, hh * 1000) + " /m")
        qmax = (Nser + B * B * hh * 25) / (B * B)
        verdict(qmax <= sol["qadm"], f"Contrainte de service {qmax:.0f} kPa ≤ q_adm.", f"Contrainte {qmax:.0f} kPa > q_adm.")
        st.caption("Méthode des bielles : As = N_Ed (B − a) / (8 d f_yd). Poinçonnement et cisaillement à contrôler en détail.")
    with t3:
        c1, c2, c3 = st.columns(3)
        Ar = c1.number_input("Surface du radier (m²)", 50.0, 50000.0, float(S.niveaux["Surface (m²)"].max()), 10.0)
        Wt = c2.number_input("Poids total en service (kN)", 1000.0, 5e6, float(
            ((S.niveaux["G (kN/m²)"].astype(float) + 0.3 * S.niveaux["Q (kN/m²)"].astype(float) + 4.0)
             * S.niveaux["Surface (m²)"].astype(float)).sum()), 500.0)
        ep = c3.number_input("Épaisseur du radier (m)", 0.3, 3.0, 0.8, 0.05)
        Wr = Ar * ep * 25
        sig = (Wt + Wr) / Ar
        verdict(sig <= sol["qadm"], f"Contrainte moyenne {sig:.0f} kPa ≤ q_adm ({sol['qadm']:.0f} kPa).",
                f"Contrainte moyenne {sig:.0f} kPa > q_adm : élargir ou approfondir (semelles + pieux).")
        zr = prof + ep
        hw = max(zr - sol["nappe"], 0.0)
        if hw > 0:
            U = 9.81 * hw * Ar
            fs = (Wt * 0.9 + Wr) / U
            c1, c2, c3 = st.columns(3)
            c1.metric("Sous-pression", f"{fmt(U, 0)} kN")
            c2.metric("Poids stabilisant (0,9 G)", f"{fmt(Wt * 0.9 + Wr, 0)} kN")
            c3.metric("Coefficient vs soulèvement", f"{fs:.2f}")
            verdict(fs >= 1.1, "Stabilité à la flottaison assurée (≥ 1,10).",
                    "Risque de soulèvement : lestage, ancrages ou drainage permanent.")
        else:
            st.success("La nappe est sous la base du radier : pas de sous-pression à l'ELS.")
    with t4:
        c1, c2, c3 = st.columns(3)
        dh = c1.number_input("Dénivelé à franchir (m)", 1.0, 20.0, 2.8, 0.1)
        pent = c2.number_input("Pente de la rampe (%)", 5.0, 25.0, 15.0, 0.5)
        larg = c3.number_input("Largeur utile (m)", 2.5, 12.0, 3.5, 0.1)
        Lr = dh / (pent / 100)
        c1, c2, c3 = st.columns(3)
        c1.metric("Longueur de rampe", f"{Lr:.1f} m")
        c2.metric("Surface de rampe", f"{Lr * larg:.0f} m²")
        c3.metric("Nombre de niveaux desservis", int(max(prof // 2.8, 1)))
        verdict(pent <= 18, "Pente admissible (≤ 18 % en usage courant).", "Pente excessive : prévoir raccords de 10 % ou 3 m aux extrémités.")
        verdict(larg >= 3.0, "Largeur compatible avec une rampe à sens unique (≥ 3,0 m).", "Largeur insuffisante pour une rampe.")
        nb = st.number_input("Surface de parking à desservir (m²)", 100.0, 100000.0, float(S.niveaux["Surface (m²)"].max()), 50.0)
        st.metric("Nombre de places estimé (25 m²/place)", int(nb // 25))


# ===================== PAGE : ACTIONS (VENT, NEIGE, SÉISME) =====================
def page_actions():
    S = st.session_state
    nv, top, prof = hauteurs(S)
    hero("🌬️ Actions climatiques et sismiques", "Vent par niveau, neige en toiture, séisme (force latérale équivalente par niveau)")
    t1, t2, t3 = st.tabs(["Vent", "Neige", "Séisme"])
    with t1:
        c1, c2, c3, c4 = st.columns(4)
        vb0 = c1.number_input("Vitesse de base vb,0 (m/s)", 15.0, 50.0, 26.0, 1.0)
        cat = c2.selectbox("Catégorie de terrain", {"0 mer": (0.003, 1), "I": (0.01, 1), "II campagne": (0.05, 2),
                                                    "III banlieue": (0.3, 5), "IV ville dense": (1.0, 10)}.keys(), index=3)
        z0, zmin = {"0 mer": (0.003, 1), "I": (0.01, 1), "II campagne": (0.05, 2), "III banlieue": (0.3, 5),
                    "IV ville dense": (1.0, 10)}[cat]
        larg = c3.number_input("Largeur de façade exposée (m)", 5.0, 200.0, 25.0, 1.0)
        cpe = c4.number_input("c_pe + c_pi (face au vent)", 0.5, 2.0, 1.1, 0.1)
        zs = np.arange(0, max(top, 3.0) + 1, 1.0)
        qp = [vent_qp(max(z, 1.0), vb0, z0, zmin) for z in zs]
        H = max(top, 3.0)
        qH = vent_qp(H, vb0, z0, zmin)
        c1, c2, c3 = st.columns(3)
        c1.metric("q_p(H)", f"{qH:.2f} kPa")
        c2.metric("Pression sur façade", f"{qH * cpe:.2f} kPa")
        c3.metric("Effort total à la base", f"{sum(qp[i] * cpe * larg for i in range(len(zs))) * 1.0:.0f} kN")
        fig = go.Figure(go.Scatter(x=qp, y=zs, mode="lines+markers", line_color=ACCENT))
        fig.update_layout(title="Profil de pression dynamique de pointe q_p(z)", xaxis_title="q_p (kPa)", yaxis_title="z (m)")
        pplot(fig, 360)
        d = nv[nv["Cote plancher (m)"] >= 0].copy()
        d["z milieu (m)"] = d["Cote plancher (m)"] + d["Hauteur (m)"] / 2
        d["F vent (kN)"] = [vent_qp(max(z, 1.0), vb0, z0, zmin) * cpe * larg * h for z, h in zip(d["z milieu (m)"], d["Hauteur (m)"])]
        show_df(d[["Niveau", "Cote plancher (m)", "Hauteur (m)", "F vent (kN)"]].round(2))
        note("EN 1991-1-4 simplifié : q_p = (1+7·Iv)·½ρ·v_m²(z), ρ = 1,25 kg/m³. Les coefficients de pression réels dépendent de la "
             "forme et des rapports h/d : à préciser en bureau d'études.")
    with t2:
        c1, c2, c3 = st.columns(3)
        sk = c1.number_input("Charge de neige au sol s_k (kN/m²)", 0.0, 6.0, 0.45, 0.05)
        mu = c2.number_input("Coefficient de forme μ", 0.2, 2.0, 0.8, 0.1)
        ce = c3.number_input("C_e × C_t", 0.5, 1.2, 1.0, 0.05)
        s = mu * ce * sk
        ter = S.niveaux[S.niveaux["Niveau"].astype(str) == "Terrasse"]
        At = float(ter["Surface (m²)"].iloc[0]) if len(ter) else 0.0
        c1, c2 = st.columns(2)
        c1.metric("Charge de neige en toiture", f"{s:.2f} kN/m²")
        c2.metric("Effort total sur la terrasse", f"{s * At:.0f} kN")
    with t3:
        c1, c2, c3, c4 = st.columns(4)
        ag = c1.number_input("a_g (m/s²)", 0.2, 8.0, 1.6, 0.1)
        sol_c = c2.selectbox("Classe de sol", {"A": (1.0, .15, .4, 2.0), "B": (1.2, .15, .5, 2.0), "C": (1.15, .2, .6, 2.0),
                                               "D": (1.35, .2, .8, 2.0), "E": (1.4, .15, .5, 2.0)}.keys(), index=1)
        S_, TB, TC, TD = {"A": (1.0, .15, .4, 2.0), "B": (1.2, .15, .5, 2.0), "C": (1.15, .2, .6, 2.0),
                          "D": (1.35, .2, .8, 2.0), "E": (1.4, .15, .5, 2.0)}[sol_c]
        q = c3.number_input("Coefficient de comportement q", 1.0, 5.0, 3.0, 0.5)
        gam_i = c4.selectbox("Importance γ_I", [0.8, 1.0, 1.2, 1.4], index=1)
        c1, c2, c3 = st.columns(3)
        gst = c1.number_input("Poids structure (kN/m²)", 2.0, 12.0, 5.0, 0.5)
        psiE = c2.number_input("ψ_E = φ·ψ2", 0.1, 1.0, 0.24, 0.02)
        Ct = c3.selectbox("Contreventement (C_t)", [0.085, 0.075, 0.05], format_func=lambda x: {0.085: "Portiques acier",
                          0.075: "Portiques béton", 0.05: "Voiles / autres"}[x], index=2)
        out, T1, Sd, Fb, W = seisme_niveaux(nv, gst, psiE, ag * gam_i, S_, TB, TC, TD, q, Ct)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Période T1", f"{T1:.2f} s")
        c2.metric("S_d(T1)", f"{Sd:.2f} m/s²")
        c3.metric("Poids sismique W", f"{fmt(W, 0)} kN")
        c4.metric("Effort tranchant à la base", f"{fmt(Fb, 0)} kN", f"{Fb / W * 100:.1f} % de W")
        show_df(out)
        fig = go.Figure(go.Bar(y=out["Niveau"], x=out["Force Fi (kN)"], orientation="h", marker_color=NOIR))
        fig.update_layout(title="Forces sismiques par niveau (kN)")
        pplot(fig, 360)
        tt = np.linspace(0.02, 4, 200)
        fig = go.Figure(go.Scatter(x=tt, y=[spectre_ec8(t, ag * gam_i, S_, TB, TC, TD, q) for t in tt], line_color=ACCENT))
        fig.add_vline(x=T1, line_dash="dash", line_color=ROUGE, annotation_text="T1")
        fig.update_layout(title="Spectre de calcul de l'EC8", xaxis_title="T (s)", yaxis_title="S_d (m/s²)")
        pplot(fig, 320)
        note("Méthode des forces latérales (EC8) : F_b = S_d(T1)·W·λ/g, répartie selon W·z. Les sous-sols rigides sont exclus du "
             "poids sismique. Effets de torsion et analyse modale non traités.")


# ===================== PAGE : THERMIQUE =====================
def page_thermique():
    S = st.session_state
    hero("🌡️ Thermique du bâtiment", "Résistance et coefficient U d'une paroi, déperditions de l'enveloppe, énergie")
    t1, t2 = st.tabs(["Paroi composite", "Déperditions de l'enveloppe"])
    with t1:
        note("Chaque couche est définie par son matériau et son épaisseur ; λ provient de la table interne.")
        editor("couches", {"Matériau": st.column_config.SelectboxColumn("Matériau", options=list(MATERIAUX))})
        c = S.couches.dropna(subset=["Matériau"]).copy()
        c["Épaisseur (cm)"] = pd.to_numeric(c["Épaisseur (cm)"], errors="coerce").fillna(0.0)
        c["λ (W/m·K)"] = c["Matériau"].map(MATERIAUX).fillna(1.0)
        c["R (m²·K/W)"] = c["Épaisseur (cm)"] / 100 / c["λ (W/m·K)"]
        c1, c2 = st.columns(2)
        rsi, rse = c1.number_input("Rsi", 0.0, 0.5, 0.13, 0.01), c2.number_input("Rse", 0.0, 0.3, 0.04, 0.01)
        Rt = rsi + rse + float(c["R (m²·K/W)"].sum())
        c1, c2 = st.columns(2)
        c1.metric("R total", f"{Rt:.2f} m²·K/W")
        c2.metric("U = 1/R", f"{1 / Rt:.3f} W/m²·K")
        show_df(c.round(3))
    with t2:
        editor("parois", None)
        p = S.parois.dropna(subset=["Paroi"]).copy()
        p["Surface (m²)"] = pd.to_numeric(p["Surface (m²)"], errors="coerce").fillna(0.0)
        p["U (W/m²·K)"] = pd.to_numeric(p["U (W/m²·K)"], errors="coerce").fillna(0.0)
        p["UA (W/K)"] = p["Surface (m²)"] * p["U (W/m²·K)"]
        c1, c2, c3, c4 = st.columns(4)
        ti = c1.number_input("T intérieure (°C)", 10.0, 28.0, 20.0, 1.0)
        te = c2.number_input("T extérieure de base (°C)", -30.0, 20.0, 2.0, 1.0)
        vol = c3.number_input("Volume chauffé (m³)", 100.0, 500000.0, float(S.niveaux["Surface (m²)"].sum() * 2.8), 100.0)
        n = c4.number_input("Renouvellement (vol/h)", 0.1, 3.0, 0.6, 0.1)
        UAt = float(p["UA (W/K)"].sum())
        Hv = 0.34 * n * vol
        Pt = (UAt + Hv) * (ti - te)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Σ U·A", f"{fmt(UAt, 0)} W/K")
        c2.metric("Ventilation", f"{fmt(Hv, 0)} W/K")
        c3.metric("Puissance de dimensionnement", f"{fmt(Pt / 1000, 1)} kW")
        c4.metric("Besoin annuel (indicatif)", f"{fmt((UAt + Hv) * 2600 * 24 / 1000, 0)} kWh")
        if UAt > 0:
            fig = px.pie(p, names="Paroi", values="UA (W/K)", hole=0.5, title="Part de chaque paroi dans les déperditions",
                         color_discrete_sequence=PALETTE)
            pplot(fig, 340)
        show_df(p.round(2))


# ===================== PAGE : CIRCULATIONS, INCENDIE, ASCENSEURS =====================
def page_securite_usage():
    S = st.session_state
    nv, top, prof = hauteurs(S)
    hero("🚪 Circulations, incendie et ascenseurs", "Unités de passage, classement, nombre d'ascenseurs, escaliers")
    t1, t2, t3 = st.tabs(["Évacuation", "Ascenseurs", "Classement incendie"])
    with t1:
        c1, c2 = st.columns(2)
        occ = c1.number_input("Occupants par étage", 0, 2000, 60)
        dens = c2.number_input("Densité (m²/pers.)", 1.0, 30.0, 15.0, 1.0)
        rows = []
        for _, r in nv.iterrows():
            if str(r["Niveau"]) == "Terrasse":
                continue
            eff = int(r["Surface (m²)"] / dens) if occ == 0 else int(occ)
            up = unites_passage(eff)
            rows.append({"Niveau": r["Niveau"], "Effectif": eff, "UP requises": up, "Largeur cumulée (m)": largeur_up(up),
                         "Nb d'escaliers": 1 if eff < 100 else 2})
        df = pd.DataFrame(rows)
        show_df(df)
        if len(df):
            pplot(px.bar(df, x="Niveau", y="Effectif", color="UP requises", color_continuous_scale=[[0, ACCENT_CLAIR], [1, NOIR]],
                         title="Effectif et unités de passage"), 300)
        note("1 UP = 0,60 m ; 1 UP jusqu'à 50 personnes, 2 UP jusqu'à 100, puis +1 UP par 100 personnes. Valeurs usuelles à "
             "confirmer avec la réglementation locale applicable.")
    with t2:
        c1, c2, c3, c4 = st.columns(4)
        pop = c1.number_input("Population desservie", 5, 5000, int(S.niveaux["Surface (m²)"].sum() / 15))
        v = c2.number_input("Vitesse (m/s)", 0.4, 6.0, 1.0, 0.1)
        cap = c3.number_input("Charge nominale (kg)", 320, 2500, 630, 10)
        pct = c4.number_input("Trafic de pointe 5 min (%)", 3.0, 20.0, 7.0, 0.5) / 100
        H = max(top, 3.0)
        arr = len(nv[nv["Cote plancher (m)"] >= 0]) - 1 + max(int(prof // 2.8), 0)
        C, rtt, cap5, nb = ascenseurs(pop, H, v, cap, arr, pct)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Capacité (pers.)", C)
        c2.metric("Temps d'un aller-retour", f"{rtt:.0f} s")
        c3.metric("Capacité / 5 min", f"{cap5:.1f} pers.")
        c4.metric("Ascenseurs requis", nb)
        verdict(nb <= 2, "Parc d'ascenseurs raisonnable.", "Nombre élevé : réétudier vitesse et charge.")
    with t3:
        hp = st.number_input("Hauteur du plancher bas du dernier niveau (m)", 0.0, 300.0, float(max(top - 3.0, 0.0)), 0.5)
        fam = st.selectbox("Famille", ["Habitation", "Bureaux", "Commerce / ERP", "Parking couvert"])
        if fam == "Habitation":
            cl = "1ère famille" if hp <= 8 else "2e famille" if hp <= 28 else "3e famille" if hp <= 50 else "4e famille (IGH)"
        elif fam == "Bureaux":
            cl = "Hauteur ≤ 28 m : bureaux courants" if hp <= 28 else "Hauteur > 28 m : IGH ou dispositions renforcées"
        else:
            cl = "ERP / parc : règles spécifiques de désenfumage et de recoupement"
        st.metric("Classement indicatif", cl)
        rd = st.number_input("Stabilité au feu requise (min)", 30, 240, 90 if hp > 8 else 60, 30)
        st.caption("Enrobage minimal des armatures vis-à-vis du feu (poteau 40×40, ordre de grandeur) : "
                   f"{ {30: 20, 60: 30, 90: 35, 120: 45, 180: 55, 240: 65}.get(rd, 40)} mm.")
        note("Dispositions indicatives : à confirmer avec le classement officiel (réglementation locale) et le bureau de contrôle.")


# ===================== PAGE : BÉTON ET ACIERS =====================
def page_materiaux():
    S = st.session_state
    hero("🧪 Béton et aciers", "Essais de résistance, conformité, formulation, ancrage et recouvrement")
    t1, t2, t3 = st.tabs(["Essais de compression", "Formulation (Dreux simplifiée)", "Ancrage / recouvrement"])
    with t1:
        with st.form("form_essai", clear_on_submit=True):
            c1, c2, c3, c4, c5 = st.columns(5)
            d = c1.date_input("Date", date.today())
            el = c2.text_input("Élément", "Dalle R+1")
            cl = c3.selectbox("Classe", CLASSES_BETON, index=1)
            age = c4.number_input("Âge (j)", 1.0, 180.0, 28.0, 1.0)
            r = c5.number_input("Résistance (MPa)", 1.0, 100.0, 30.0, 0.5)
            if st.form_submit_button("➕ Ajouter l'essai"):
                add_rows("essais", pd.DataFrame([{"Date": d, "Élément": el, "Classe": cl, "Âge (j)": age, "Résistance (MPa)": r}]))
                st.rerun()
        editor("essais", {"Classe": st.column_config.SelectboxColumn("Classe", options=CLASSES_BETON),
                          "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY")})
        ev = eval_beton(S.essais)
        if len(ev):
            show_df(ev)
        e = S.essais.copy()
        e["Résistance (MPa)"] = pd.to_numeric(e["Résistance (MPa)"], errors="coerce")
        e = e.dropna(subset=["Résistance (MPa)", "Classe"])
        if len(e):
            fig = px.box(e, x="Classe", y="Résistance (MPa)", points="all", color="Classe", color_discrete_sequence=PALETTE,
                         title="Dispersion des résistances par classe")
            pplot(fig, 340)
        note("Critère de conformité (indicatif) : f_cm ≥ f_ck + 4 et f_min ≥ f_ck − 4 pour au moins 3 résultats à 28 jours.")
    with t2:
        c1, c2, c3, c4 = st.columns(4)
        fck = c1.selectbox("Classe", CLASSES_BETON, index=2, key="form_cl")
        cim = c2.number_input("Dosage ciment (kg/m³)", 250.0, 500.0, 350.0, 5.0)
        ee = c3.number_input("Eau (L/m³)", 120.0, 250.0, 180.0, 5.0)
        air = c4.number_input("Air occlus (%)", 0.0, 8.0, 1.5, 0.5)
        fc = beton_props(fck)["fck"]
        gc = 3.1
        vol_pate = cim / gc / 1000 + ee / 1000 + air / 100
        vgr = 1 - vol_pate
        sable = st.slider("Part de sable dans les granulats (%)", 30, 55, 42)
        mg = vgr * 2650
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("E/C", f"{ee / cim:.2f}")
        c2.metric("Sable", f"{mg * sable / 100:.0f} kg/m³")
        c3.metric("Gravillons", f"{mg * (100 - sable) / 100:.0f} kg/m³")
        c4.metric("Masse volumique", f"{(cim + ee + mg) / 1000 * 1000:.0f} kg/m³")
        fcm = 0.5 * 42.5 * (cim / ee - 0.5) * 1.1
        verdict(fcm >= fc + 8, f"Résistance estimée (Bolomey) ≈ {fcm:.0f} MPa : suffisant pour {fck}.",
                f"Résistance estimée ≈ {fcm:.0f} MPa : insuffisante, réduire E/C ou augmenter le ciment.")
    with t3:
        c1, c2, c3, c4 = st.columns(4)
        phi = c1.selectbox("Diamètre HA (mm)", [8, 10, 12, 14, 16, 20, 25, 32], index=4)
        cl = c2.selectbox("Béton", CLASSES_BETON, index=2, key="anc_cl")
        bon = c3.selectbox("Conditions d'adhérence", ["Bonnes", "Médiocres"])
        fyk = c4.selectbox("fyk", [400, 500], index=1, key="anc_fy")
        p = beton_props(cl)
        fctd = 0.7 * p["fctm"] / 1.5
        eta1 = 1.0 if bon == "Bonnes" else 0.7
        fbd = 2.25 * eta1 * fctd
        lbrqd = phi / 4 * (fyk / 1.15) / fbd
        lb_min = max(0.3 * lbrqd, 10 * phi, 100)
        c1, c2, c3 = st.columns(3)
        c1.metric("f_bd", f"{fbd:.2f} MPa")
        c2.metric("Longueur d'ancrage de référence", f"{lbrqd:.0f} mm  (≈ {lbrqd / phi:.0f} φ)")
        c3.metric("Recouvrement (α6 = 1,5)", f"{max(1.5 * lbrqd, 15 * phi, 200):.0f} mm")
        st.caption(f"Longueur minimale d'ancrage : {lb_min:.0f} mm.")


# ===================== PAGE : QUANTITÉS =====================
def page_quantites():
    S = st.session_state
    nv, top, prof = hauteurs(S)
    hero("🧮 Quantités par niveau et métré", "Béton, acier et coffrage estimés par niveau puis métré chiffré")
    t1, t2 = st.tabs(["Quantités de structure par niveau", "Métré et chiffrage"])
    with t1:
        c1, c2, c3, c4 = st.columns(4)
        hd = c1.number_input("Dalle (cm)", 12.0, 40.0, 22.0, 1.0)
        rp = c2.number_input("Poutres (m³ par m² de plancher)", 0.0, 0.2, 0.05, 0.005, format="%.3f")
        maille = c3.number_input("Surface par poteau (m²)", 10.0, 100.0, 30.0, 1.0)
        perim = c4.number_input("Périmètre sous-sols (m)", 20.0, 2000.0, 110.0, 5.0)
        c1, c2, c3, c4 = st.columns(4)
        bc = c1.number_input("Poteau b (cm)", 20.0, 120.0, 40.0, 5.0, key="q_bc")
        hc = c2.number_input("Poteau h (cm)", 20.0, 120.0, 40.0, 5.0, key="q_hc")
        ev = c3.number_input("Voile enterré (cm)", 15.0, 60.0, 25.0, 1.0, key="q_ev")
        noyau = c4.number_input("Longueur voiles de noyau (m)", 0.0, 500.0, 40.0, 1.0)
        c1, c2, c3, c4 = st.columns(4)
        ra_d = c1.number_input("Ratio dalle (kg/m³)", 40.0, 200.0, 90.0, 5.0)
        ra_p = c2.number_input("Ratio poutres (kg/m³)", 60.0, 250.0, 130.0, 5.0)
        ra_pt = c3.number_input("Ratio poteaux (kg/m³)", 80.0, 300.0, 150.0, 5.0)
        ra_v = c4.number_input("Ratio voiles (kg/m³)", 40.0, 200.0, 90.0, 5.0)
        p = dict(hd=hd, rp=rp, maille=maille, bc=bc, hc=hc, perim=perim, ev=ev, noyau=noyau, ra_d=ra_d, ra_p=ra_p, ra_pt=ra_pt, ra_v=ra_v)
        q = volumes_niveaux(nv, p)
        show_df(q.round(1))
        tot = q[["Béton (m³)", "Acier (kg)", "Coffrage (m²)"]].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Béton total", f"{fmt(tot['Béton (m³)'], 0)} m³")
        c2.metric("Acier total", f"{fmt(tot['Acier (kg)'] / 1000, 1)} t")
        c3.metric("Coffrage", f"{fmt(tot['Coffrage (m²)'], 0)} m²")
        c4.metric("Ratio acier", f"{tot['Acier (kg)'] / max(tot['Béton (m³)'], 1):.0f} kg/m³")
        fig = go.Figure()
        for col, colr in (("Dalle (m³)", ACCENT), ("Poutres (m³)", BLEU), ("Poteaux (m³)", ORANGE), ("Voiles (m³)", NOIR)):
            fig.add_bar(x=q["Niveau"], y=q[col], name=col, marker_color=colr)
        fig.update_layout(barmode="stack", title="Volume de béton par niveau et par élément (m³)")
        pplot(fig, 380)
    with t2:
        editor("metre", {"Unité": st.column_config.SelectboxColumn("Unité", options=["m³", "m²", "ml", "kg", "u", "forfait"])})
        m = metre_totals(S.metre)
        tot = float(m["Total"].sum())
        c1, c2, c3 = st.columns(3)
        tva = c2.number_input("TVA (%)", 0.0, 30.0, 18.0, 0.5)
        alea = c3.number_input("Aléas (%)", 0.0, 25.0, 5.0, 0.5)
        c1.metric("Total HT", f"{fmt(tot, 0)} {S.projet['devise']}")
        ht = tot * (1 + alea / 100)
        c1, c2 = st.columns(2)
        c1.metric("HT avec aléas", f"{fmt(ht, 0)} {S.projet['devise']}")
        c2.metric("TTC", f"{fmt(ht * (1 + tva / 100), 0)} {S.projet['devise']}")
        g = m.groupby("Lot", as_index=False)["Total"].sum().sort_values("Total", ascending=False)
        if len(g):
            pplot(px.bar(g, x="Total", y="Lot", orientation="h", title="Coût par lot", color_discrete_sequence=[ACCENT]), 380)



# ===================== PAGE : PLANNING =====================
def page_planning():
    S = st.session_state
    P = S.projet
    hero("📅 Planning et chemin critique", "Gantt • calage automatique • marges • avancement réel")
    note("Prédécesseurs : noms de tâches séparés par « ; ».")
    if st.button("🏗️ Générer le planning type depuis les niveaux R-n / R+n"):
        tdf = planning_par_niveaux(niveaux_calc(S.niveaux), P["debut"])
        sch, _ = cpm(tdf)
        tdf["Début"] = [P["debut"] + timedelta(days=int(v)) for v in sch["ES"]]
        set_df("taches", coerce(tdf, "taches"))
        st.rerun()
    editor("taches", {"Début": st.column_config.DateColumn("Début", format="DD/MM/YYYY")})
    mode = st.radio("Calendrier", ["Dates saisies", "Calage automatique selon prédécesseurs"], horizontal=True)
    try:
        d, T = cpm(S.taches)
    except ValueError as ex:
        st.error(str(ex))
        return
    d["Avancement (%)"] = pd.to_numeric(d["Avancement (%)"], errors="coerce").fillna(0).clip(0, 100)
    if mode.startswith("Calage"):
        d["Début_"] = [pd.Timestamp(P["debut"]) + pd.Timedelta(days=float(v)) for v in d["ES"]]
    else:
        d["Début_"] = pd.to_datetime(d["Début"], errors="coerce").fillna(pd.Timestamp(P["debut"]))
    d["Fin_"] = d["Début_"] + pd.to_timedelta(d["Durée (j)"], unit="D")
    today = pd.Timestamp(date.today())
    d["Statut"] = [("Terminé" if a >= 100 else "En retard" if f < today else "En cours" if s <= today else "À venir")
                   for a, f, s in zip(d["Avancement (%)"], d["Fin_"], d["Début_"])]
    if mode.startswith("Calage") and st.button("💾 Appliquer ces dates au tableau"):
        tt = S.taches.copy()
        mp = dict(zip(d["Tâche"], d["Début_"].dt.date))
        tt["Début"] = [mp.get(n, x) for n, x in zip(tt["Tâche"], tt["Début"])]
        set_df("taches", tt)
        st.rerun()
    fig = px.timeline(d, x_start="Début_", x_end="Fin_", y="Tâche", color="Statut",
                      color_discrete_map={"Terminé": VERT, "En cours": ACCENT, "En retard": ROUGE, "À venir": "#C9C5AA"},
                      title="Diagramme de Gantt")
    fig.update_yaxes(autorange="reversed")
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper", line=dict(color=ROUGE, width=2, dash="dash"))
    pplot(fig, 140 + 32 * len(d))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Durée (chemin critique)", f"{T:.0f} j")
    c2.metric("Fin prévue", (pd.Timestamp(P["debut"]) + pd.Timedelta(days=T)).strftime("%d/%m/%Y"))
    c3.metric("Tâches en retard", int((d["Statut"] == "En retard").sum()))
    c4.metric("Tâches critiques", int(d["Critique"].sum()))
    out = d[["Tâche", "Responsable", "Durée (j)", "Avancement (%)", "Marge (j)", "Critique", "Statut"]].copy()
    out["Critique"] = out["Critique"].map({True: "🔴 Oui", False: "—"})
    show_df(out)


# ===================== PAGE : COÛTS (EVM) =====================
def page_cout():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    hero("💰 Suivi des coûts — valeur acquise", "PV, EV, AC • CPI, SPI • prévision à l'achèvement")
    bac = st.number_input(f"Budget à l'achèvement BAC ({dev})", 0.0, 1e10, float(P["budget"]), 10000.0)
    note("Saisir les valeurs cumulées par mois : valeur planifiée (PV), acquise (EV) et coût réel (AC).")
    editor("ev")
    ev = S.ev.copy()
    for c in COLS["ev"]:
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    ev = ev.dropna(subset=["Mois"]).sort_values("Mois")
    last = ev.dropna(subset=["EV cumulée", "AC cumulé", "PV cumulé"])
    if last.empty:
        st.info("Renseigner au moins un mois complet.")
        return
    r = last.iloc[-1]
    PV, EV, AC = float(r["PV cumulé"]), float(r["EV cumulée"]), float(r["AC cumulé"])
    CPI = EV / AC if AC else float("nan")
    SPI = EV / PV if PV else float("nan")
    EAC = bac / CPI if CPI else float("nan")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CPI (coût)", f"{CPI:.2f}", "sous budget" if CPI >= 1 else "dépassement", delta_color="normal" if CPI >= 1 else "inverse")
    c2.metric("SPI (délai)", f"{SPI:.2f}", "en avance" if SPI >= 1 else "en retard", delta_color="normal" if SPI >= 1 else "inverse")
    c3.metric("CV = EV − AC", f"{fmt(EV - AC, 0)} {dev}")
    c4.metric("SV = EV − PV", f"{fmt(EV - PV, 0)} {dev}")
    c1, c2, c3 = st.columns(3)
    c1.metric("EAC (prévision finale)", f"{fmt(EAC, 0)} {dev}")
    c2.metric("ETC (reste à dépenser)", f"{fmt(EAC - AC, 0)} {dev}")
    c3.metric("VAC (écart final)", f"{fmt(bac - EAC, 0)} {dev}")
    fig = go.Figure()
    for col, color in [("PV cumulé", GRIS), ("EV cumulée", ACCENT), ("AC cumulé", ROUGE)]:
        fig.add_trace(go.Scatter(x=ev["Mois"], y=ev[col], name=col, mode="lines+markers", line=dict(color=color, width=4)))
    fig.add_hline(y=bac, line_dash="dot", line_color=NOIR, annotation_text="BAC")
    fig.update_layout(title="Courbes en S", xaxis_title="Mois", yaxis_title=dev)
    pplot(fig, 400)




# ===================== PAGE : HSE ET RISQUES =====================
def page_hse():
    S = st.session_state
    hero("🦺 Santé, sécurité et risques", "Registre des risques, matrice probabilité × gravité, plan d'actions")
    editor("risques", {"Probabilité": st.column_config.NumberColumn("Probabilité", min_value=1, max_value=5, step=1),
                       "Gravité": st.column_config.NumberColumn("Gravité", min_value=1, max_value=5, step=1)})
    r = S.risques.dropna(subset=["Risque"]).copy()
    r["Probabilité"] = pd.to_numeric(r["Probabilité"], errors="coerce").fillna(1).clip(1, 5)
    r["Gravité"] = pd.to_numeric(r["Gravité"], errors="coerce").fillna(1).clip(1, 5)
    r["Criticité"] = r["Probabilité"] * r["Gravité"]
    r["Niveau"] = pd.cut(r["Criticité"], [0, 5, 11, 16, 30], labels=["Faible", "Modéré", "Élevé", "Critique"])
    c1, c2, c3, c4 = st.columns(4)
    for c, lab in zip((c1, c2, c3, c4), ("Faible", "Modéré", "Élevé", "Critique")):
        c.metric(lab, int((r["Niveau"] == lab).sum()))
    Z = np.array([[p * g for p in range(1, 6)] for g in range(1, 6)], dtype=float)
    fig = go.Figure(go.Heatmap(z=Z, x=list(range(1, 6)), y=list(range(1, 6)), colorscale=[[0, "#DDF3E2"], [.35, "#FFE8A8"],
                                                                                          [.65, "#F5A25D"], [1, ROUGE]],
                               showscale=False, text=Z.astype(int), texttemplate="%{text}", opacity=0.75))
    fig.add_trace(go.Scatter(x=r["Probabilité"] + np.linspace(-0.2, 0.2, len(r)), y=r["Gravité"] + np.linspace(0.2, -0.2, len(r)),
                             mode="markers+text", text=list(range(1, len(r) + 1)), textposition="middle center",
                             marker=dict(size=22, color=NOIR), textfont=dict(color="#FFFFFF"), hovertext=r["Risque"], name="Risques"))
    fig.update_layout(title="Matrice des risques (numéros = lignes du registre)", xaxis_title="Probabilité", yaxis_title="Gravité")
    pplot(fig, 420)
    show_df(r.sort_values("Criticité", ascending=False)[["Risque", "Phase", "Criticité", "Niveau", "Mesure de maîtrise"]])
    st.subheader("Rappel des mesures de prévention par type de travaux")
    st.markdown("- **Sous-sols :** blindage de fouille, pompage, étaiement contrôlé, ventilation lors des coulages.\n"
                "- **Superstructure :** garde-corps et filets en rives, plan d'étaiement et de décoffrage, protection des trémies.\n"
                "- **Levage :** zone balisée, élingage vérifié, limitation par vent fort.\n"
                "- **Second œuvre :** coordination des corps d'état, permis de feu, vérifications électriques.")




# ===================== PAGE : EXPORT =====================
def build_excel():
    S = st.session_state
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame({"Clé": list(S.projet), "Valeur": [str(v) for v in S.projet.values()]}).to_excel(xw, sheet_name="Projet", index=False)
        for k in COLS:
            S[k].to_excel(xw, sheet_name=LABELS[k][:31], index=False)
        metre_totals(S.metre).to_excel(xw, sheet_name="Metre avec totaux", index=False)
    return buf.getvalue()


def build_rapport():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    nv, top, prof = hauteurs(S)
    t = S.taches.dropna(subset=["Tâche"])
    dur = num(t, "Durée (j)")
    avanc = float((dur * num(t, "Avancement (%)")).sum() / dur.sum()) if dur.sum() else 0.0
    mt = metre_totals(S.metre)
    hors = nv[~nv["Usage"].str.startswith("Terrasse")]
    L = [f"# Rapport de synthèse — {P['nom']}", f"*Édité le {date.today().strftime('%d/%m/%Y')}*", "",
         "## Ouvrage", f"- Configuration : R-{P['n_ss']} / R+{P['n_et']}", f"- Hauteur hors sol : {top:.1f} m — profondeur : {prof:.1f} m",
         f"- Surface de plancher : {hors['Surface (m²)'].sum():,.0f} m²".replace(",", " "), f"- Usage : {P['usage']}", "",
         "## Avancement et délais", f"- Avancement global pondéré : **{avanc:.1f} %**", f"- Période : {P['debut']} → {P['fin']}", "",
         "## Coûts", f"- Estimation du métré HT : **{mt['Total'].sum():,.0f} {dev}**".replace(",", " "),
         f"- Budget cible : {P['budget']:,.0f} {dev}".replace(",", " "), "", "## Béton"]
    ev = eval_beton(S.essais)
    L += [f"- {x['Classe']} : n={x['n']}, f_cm={x['fcm (MPa)']} MPa → {x['Statut']}" for _, x in ev.iterrows()] or ["- Aucun essai."]
    r = S.risques
    nc = int((num(r, "Probabilité") * num(r, "Gravité") >= 15).sum())
    L += ["", "## Risques", f"- Risques critiques (≥ 15) : {nc}", "", "---",
          "*Généré par GC Bâtiment R-n / R+n — résultats indicatifs à valider par un ingénieur / bureau d'études.*"]
    return "\n".join(L)


def page_export():
    S = st.session_state
    hero("📤 Export, rapport et sauvegarde", "Classeur Excel • rapport de synthèse • restauration")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Classeur Excel complet", build_excel(), "projet_batiment.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    rap = build_rapport()
    c2.download_button("⬇️ Rapport de synthèse (Markdown)", rap.encode("utf-8"), "rapport_batiment.md", "text/markdown")
    with st.expander("👁️ Aperçu du rapport", expanded=True):
        st.markdown(rap)
    cols = st.columns(4)
    for i, k in enumerate(COLS):
        cols[i % 4].download_button(f"⬇️ {LABELS[k]}", S[k].to_csv(index=False).encode("utf-8-sig"), f"{k}.csv", "text/csv", key=f"csv_{k}")
    up = st.file_uploader("Restaurer un classeur exporté", type=["xlsx"])
    if up is not None and st.button("♻️ Restaurer les données"):
        try:
            sheets = pd.read_excel(up, sheet_name=None)
            inv = {v[:31]: k for k, v in LABELS.items()}
            for nom, df in sheets.items():
                if nom in inv:
                    set_df(inv[nom], coerce(df, inv[nom]))
            st.success("Données restaurées.")
            st.rerun()
        except Exception as ex:
            st.error(f"Restauration impossible : {ex}")
    if st.button("🗑️ Recharger les données de démonstration"):
        for k in list(S.keys()):
            del S[k]
        st.rerun()


# ===================== NAVIGATION =====================
PAGES = {
    "🏠 Tableau de bord": page_dashboard,
    "🏗️ Niveaux R-n / R+n": page_niveaux,
    "📥 Collecte et journal": page_collecte,
    "⚖️ Descente de charges": page_charges,
    "🧱 Béton armé": page_beton_arme,
    "⛏️ Sous-sols et fondations": page_fondations,
    "🌬️ Vent, neige, séisme": page_actions,
    "🌡️ Thermique": page_thermique,
    "🚪 Circulations et incendie": page_securite_usage,
    "🧪 Béton et aciers": page_materiaux,
    "🧮 Quantités et métré": page_quantites,
    "📅 Planning": page_planning,
    "💰 Suivi des coûts (EVM)": page_cout,
    "🦺 HSE et risques": page_hse,
    "📤 Export et rapport": page_export,
}


def main():
    init_state()
    with st.sidebar:
        st.markdown("<div class='brand'>🏢 GC Bâtiment R-n / R+n</div>", unsafe_allow_html=True)
        choix = st.radio("Navigation", list(PAGES), label_visibility="collapsed")
        st.markdown("---")
        st.caption(f"Projet : {st.session_state.projet['nom']}")
        st.caption("Résultats indicatifs — validation par un ingénieur / bureau d'études requise.")
    PAGES[choix]()


if __name__ == "__main__":
    main()
