import streamlit as st
from datetime import datetime
from fpdf import FPDF
import sqlite3
import pandas as pd
import os

# --- Job-specific checklist items ---
CHECKLIST = [
    {"en": "PPE in place and compliant", "fr": "EPI en place et conforme"},
    {"en": "Permit to work displayed", "fr": "Permis de travail affiché"},
    {"en": "Area demarcated", "fr": "Zone délimitée"},
    {"en": "Tools inspected and functional", "fr": "Outils inspectés et fonctionnels"},
    {"en": "Waste properly disposed", "fr": "Déchets correctement éliminés"},
]

# --- Database Init ---
def init_db():
    conn = sqlite3.connect("hse.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY,
        auditor TEXT,
        site TEXT,
        job TEXT,
        date TEXT,
        risk TEXT,
        pdf_path TEXT
    )''')
    conn.commit()
    conn.close()

# --- PDF Generation ---
def create_pdf(data, lang):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Rapport HSE" if lang == "Français" else "HSE Report", ln=True)
    pdf.ln(5)
    for k, v in data.items():
        pdf.cell(0, 10, f"{k}: {v}", ln=True)
    path = f"hse_report_{data['date']}.pdf"
    pdf.output(path)
    return path

# --- Streamlit App ---
st.set_page_config("HSE App")
init_db()

lang = st.selectbox("Language / Langue", ["English", "Français"])
_ = lambda s: s if lang == "English" else {
    "Auditor": "Inspecteur",
    "Site": "Site",
    "Job": "Travail",
    "Date": "Date",
    "Checklist": "Liste de contrôle",
    "Generate PDF": "Générer le PDF",
    "Download PDF": "Télécharger le PDF"
}.get(s, s)

st.title(_("Checklist"))
auditor = st.text_input(_("Auditor"))
site = st.text_input(_("Site"))
job = st.text_input(_("Job"))
date = st.date_input(_("Date"), datetime.today())

st.subheader(_("Checklist"))
non_compliance = 0
responses = {}
for item in CHECKLIST:
    label = item['fr'] if lang == "Français" else item['en']
    choice = st.radio(label, ["Yes", "No", "N/A"], key=label)
    responses[label] = choice
    if choice == "No":
        non_compliance += 1

risk = "Red" if non_compliance > 2 else "Yellow" if non_compliance > 0 else "Green"

data = {
    "auditor": auditor,
    "site": site,
    "job": job,
    "date": str(date),
    "risk": risk
}

if st.button(_("Generate PDF")):
    path = create_pdf(data, lang)
    conn = sqlite3.connect("hse.db")
    conn.execute("INSERT INTO reports (auditor, site, job, date, risk, pdf_path) VALUES (?, ?, ?, ?, ?, ?)",
                 (auditor, site, job, str(date), risk, path))
    conn.commit()
    conn.close()
    with open(path, "rb") as f:
        st.download_button(_("Download PDF"), f, path)

st.markdown("---")
if st.checkbox("Show reports"):
    df = pd.read_sql("SELECT * FROM reports ORDER BY date DESC", sqlite3.connect("hse.db"))
    st.dataframe(df)
