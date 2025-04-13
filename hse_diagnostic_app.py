# This version avoids micropip or restricted imports for sandbox environments
import streamlit as st
from datetime import datetime
from fpdf import FPDF
import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# --- Job-specific checklist items ---
JOB_CHECKLISTS = {
    "Wireline Operation": [
        {"en": "Pre-job safety meeting held (Toolbox Talk)", "fr": "Réunion de sécurité avant le travail (Briefing)"},
        {"en": "Work permit signed and posted", "fr": "Permis de travail signé et affiché"},
        {"en": "PPE compliant (FR suits, gloves, goggles)", "fr": "EPI conforme (tenue FR, gants, lunettes)"},
        {"en": "Line tension monitored throughout", "fr": "Tension de la ligne surveillée en permanence"},
        {"en": "Communication with surface team established", "fr": "Communication avec l'équipe en surface établie"},
        {"en": "Emergency response gear in place", "fr": "Équipement d'urgence en place"},
        {"en": "Hazardous zone demarcated", "fr": "Zone dangereuse balisée"},
        {"en": "Post-job cleanup & waste disposal verified", "fr": "Nettoyage post-travail et gestion des déchets vérifiés"}
    ]
}

SITE_TYPES = ["Onshore", "Offshore", "Support"]

# Initialize SQLite DB
def init_db():
    conn = sqlite3.connect("hse_reports.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_title TEXT,
                    site_type TEXT,
                    location TEXT,
                    date TEXT,
                    auditor TEXT,
                    pdf_path TEXT,
                    risk_level TEXT
                )''')
    conn.commit()
    conn.close()


def log_report_to_db(site_info, pdf_path, risk_level):
    conn = sqlite3.connect("hse_reports.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO reports (job_title, site_type, location, date, auditor, pdf_path, risk_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        site_info['Job Title'],
        site_info['Site Type'],
        site_info['Location'],
        site_info['Date'],
        site_info['Auditor'],
        pdf_path,
        risk_level
    ))
    conn.commit()
    conn.close()


def sanitize(text):
    return text.replace("–", "-").replace("’", "'")


def generate_pdf(site_info, checklist_results, uploaded_images, risk_level, language='English'):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'Rapport de Diagnostic HSE' if language == 'Français' else 'HSE Diagnostic Report', ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    for key, value in site_info.items():
        pdf.cell(0, 10, f"{key}: {sanitize(value)}", ln=True)
    pdf.cell(0, 10, f"Niveau de Risque: {risk_level}" if language == 'Français' else f"Risk Level: {risk_level}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "Liste de Contrôle" if language == 'Français' else "Checklist", ln=True)
    pdf.set_font("Arial", size=10)

    pdf.set_fill_color(200, 220, 255)
    pdf.cell(100, 8, "Point de Contrôle" if language == 'Français' else "Checkpoint", border=1, fill=True)
    pdf.cell(20, 8, "Status", border=1, fill=True)
    pdf.cell(70, 8, "Commentaires" if language == 'Français' else "Comments", border=1, ln=True, fill=True)

    non_compliances = []
    for item, result in checklist_results.items():
        label = item if language != 'Français' else next((e['fr'] for e in JOB_CHECKLISTS['Wireline Operation'] if e['en'] == item), item)
        status = result['status']
        comment = sanitize(result['comment'])
        pdf.cell(100, 8, sanitize(label), border=1)
        pdf.cell(20, 8, status, border=1)
        pdf.cell(70, 8, comment, border=1, ln=True)
        if status == "No":
            non_compliances.append((item, comment))

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "Résumé des Non-Conformités" if language == 'Français' else "Summary of Non-Compliances", ln=True)
    pdf.set_font("Arial", size=10)

    if non_compliances:
        for item, comment in non_compliances:
            pdf.multi_cell(0, 8, f"- {sanitize(label)}: {comment}")
    else:
        pdf.cell(0, 8, "Aucune non-conformité observée." if language == 'Français' else "No non-compliances observed.", ln=True)

    filename = f"HSE_Report_{sanitize(site_info['Location'])}_{sanitize(site_info['Job Title'])}.pdf"
    pdf.output(filename)
    return filename


# --- Streamlit UI ---
init_db()
st.set_page_config(page_title="HSE Diagnostic Tool", layout="centered")
language = st.selectbox("Choose Language / Choisissez la langue", ["English", "Français"])

if language == "Français":
    translations = {
        "Auditor Name": "Nom de l'inspecteur",
        "Access PIN": "Code PIN",
        "Log In": "Connexion",
        "Invalid credentials": "Identifiants invalides",
        "Site Type": "Type de site",
        "HSE Job Responsibility": "Responsabilité HSE",
        "Site Location": "Lieu du site",
        "Inspection Date": "Date d'inspection",
        "Checklist": "Liste de contrôle",
        "Upload Images": "Téléverser des images",
        "Add any evidence images": "Ajouter des images justificatives",
        "Generate Report": "Générer le rapport",
        "Download PDF": "Télécharger le PDF",
        "Dashboard": "Tableau de bord",
        "Total Reports": "Rapports totaux",
        "Red Risk Reports": "Rapports à risque élevé",
        "Report History": "Historique des rapports",
        "Filter by Risk": "Filtrer par niveau de risque",
        "Filter by Auditor": "Filtrer par inspecteur",
        "Download Filtered CSV": "Télécharger CSV filtré",
        "Download CSV": "Télécharger CSV"
    }
    _ = lambda s: translations.get(s, s)
else:
    _ = lambda s: s

st.title(_("🔐 HSE Diagnostic Portal"))

# Basic login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.form("login_form"):
        username = st.text_input(_("Auditor Name"))
        pin = st.text_input(_("Access PIN"), type="password")
        submit = st.form_submit_button(_("Log In"))
        if submit and pin == "1234":
            st.session_state.logged_in = True
            st.session_state.auditor = username
        elif submit:
            st.error(_("Invalid credentials"))
    st.stop()

auditor = st.session_state.auditor
site_type = st.selectbox(_("Site Type"), SITE_TYPES)
job_title = st.selectbox(_("HSE Job Responsibility"), list(JOB_CHECKLISTS.keys()))
location = st.text_input(_("Site Location"), "Stone's Beta-08")
inspection_date = st.date_input(_("Inspection Date"), datetime.today()).strftime('%Y-%m-%d')

st.subheader(_("Checklist"))
checklist_data = {}
num_no = 0
for entry in JOB_CHECKLISTS[job_title]:
    item = entry['fr'] if language == 'Français' else entry['en']
    status = st.radio(item, ["Yes", "No", "N/A"], horizontal=True, key=f"status_{item}")
    comment_label = f"Commentaire pour '{item}'" if language == 'Français' else f"Comment for '{item}'"
    comment = st.text_input(comment_label, "" if status != "No" else "Issue identified", key=f"comment_{item}")
    checklist_data[f"{entry['en']}"] = {"status": status, "comment": comment}
    if status == "No":
        num_no += 1

st.subheader(_("Upload Images"))
uploaded_images = st.file_uploader(_("Add any evidence images"), type=["png", "jpg", "jpeg"], accept_multiple_files=True)

risk_level = "Green" if num_no == 0 else "Yellow" if num_no <= 2 else "Red"

if st.button(_("Generate Report")):
    site_info = {
        "Job Title": job_title,
        "Site Type": site_type,
        "Location": location,
        "Date": inspection_date,
        "Auditor": auditor
    }
    pdf_file = generate_pdf(site_info, checklist_data, uploaded_images, risk_level, language)
    log_report_to_db(site_info, pdf_file, risk_level)
    with open(pdf_file, "rb") as f:
        st.download_button(_("Download PDF"), f, file_name=pdf_file, mime="application/pdf")

# Dashboard
st.subheader("📊 " + _("Dashboard"))
conn = sqlite3.connect("hse_reports.db")
df = pd.read_sql_query("SELECT * FROM reports", conn)
conn.close()

st.metric(_("Total Reports"), len(df))
st.metric(_("Red Risk Reports"), len(df[df['risk_level'] == 'Red']))
st.bar_chart(df['risk_level'].value_counts())

# Report Filter
st.subheader("📁 " + _("Report History"))
filter_risk = st.selectbox(_("Filter by Risk"), ["All"] + df['risk_level'].unique().tolist()).tolist())
filter_auditor = st.text_input(_("Filter by Auditor"))
filtered_df = df.copy()
if filter_risk != "All":
    filtered_df = filtered_df[filtered_df['risk_level'] == filter_risk]
if filter_auditor:
    filtered_df = filtered_df[filtered_df['auditor'].str.contains(filter_auditor, case=False)]
st.dataframe(filtered_df)

if st.button(_("Download Filtered CSV")):
    st.download_button(
        label=_("Download CSV"),
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_reports.csv",
        mime="text/csv"
    ).encode("utf-8"),
        file_name="filtered_reports.csv",
        mime="text/csv"
    )
