import streamlit as st
from datetime import datetime
from fpdf import FPDF
import os
import sqlite3

# --- Job-specific checklist items ---
JOB_CHECKLISTS = {
    "Wireline Operation": [
        "Pre-job safety meeting held (Toolbox Talk)",
        "Work permit signed and posted",
        "PPE compliant (FR suits, gloves, goggles)",
        "Line tension monitored throughout",
        "Communication with surface team established",
        "Emergency response gear in place",
        "Hazardous zone demarcated",
        "Post-job cleanup & waste disposal verified"
    ],
    "Drilling Operations": [
        "Well control equipment inspected",
        "Daily drilling report updated",
        "Drill floor clear of obstructions",
        "Trip sheets maintained",
        "Mud logging unit operational",
        "Choke manifold tested"
    ],
    "Coiled Tubing": [
        "Pressure test completed",
        "Lubricator assembled correctly",
        "Wellhead pressure monitored",
        "Emergency shutdown system checked",
        "Personnel briefed on escape routes"
    ],
    "Pump/Motor Maintenance": [
        "LOTO procedure applied",
        "Pump base vibration checked",
        "Oil levels verified",
        "Guarding in place",
        "All connections tight after reassembly"
    ],
    "Chemical Injection": [
        "Correct chemical labeled and used",
        "Injection rate calibrated",
        "Tanks properly grounded",
        "Spill trays positioned",
        "PPE worn when handling chemicals"
    ],
    "Flare Management": [
        "Pilot flame stable",
        "Ignition system tested",
        "Flare stack area clear",
        "Pressure relief valves functional",
        "Flaring logs updated"
    ],
    "Welding/Fabrication": [
        "Hot work permit issued",
        "Firewatch assigned",
        "Welding machine grounded",
        "Flashback arrestors installed",
        "Post-weld cleanup completed"
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


def generate_pdf(site_info, checklist_results, uploaded_images, risk_level):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'HSE Diagnostic Report', ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    for key, value in site_info.items():
        pdf.cell(0, 10, f"{key}: {sanitize(value)}", ln=True)
    pdf.cell(0, 10, f"Risk Level: {risk_level}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "Checklist", ln=True)
    pdf.set_font("Arial", size=10)

    pdf.set_fill_color(200, 220, 255)
    pdf.cell(100, 8, "Checkpoint", border=1, fill=True)
    pdf.cell(20, 8, "Status", border=1, fill=True)
    pdf.cell(70, 8, "Comments", border=1, ln=True, fill=True)

    non_compliances = []
    for item, result in checklist_results.items():
        status = result['status']
        comment = sanitize(result['comment'])
        pdf.cell(100, 8, sanitize(item), border=1)
        pdf.cell(20, 8, status, border=1)
        pdf.cell(70, 8, comment, border=1, ln=True)
        if status == "No":
            non_compliances.append((item, comment))

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "Summary of Non-Compliances", ln=True)
    pdf.set_font("Arial", size=10)

    if non_compliances:
        for item, comment in non_compliances:
            pdf.multi_cell(0, 8, f"- {sanitize(item)}: {comment}")
    else:
        pdf.cell(0, 8, "No non-compliances observed.", ln=True)

    if uploaded_images:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 10, "Attached Images", ln=True)
        for img in uploaded_images:
            img_path = os.path.join("temp_uploads", img.name)
            with open(img_path, "wb") as f:
                f.write(img.getbuffer())
            pdf.image(img_path, w=100)
            pdf.ln(10)

    filename = f"HSE_DiagnosticReport_{sanitize(site_info['Location'].replace(' ', '_'))}_{sanitize(site_info['Job Title'].replace(' ', '_'))}.pdf"
    pdf.output(filename)
    return filename


# --- Streamlit UI ---
init_db()
st.set_page_config(page_title="HSE Diagnostic Tool", layout="centered")
st.title("\U0001F527 HSE Diagnostic Checklist")

site_type = st.selectbox("Site Type", SITE_TYPES)
job_title = st.selectbox("Job Title", list(JOB_CHECKLISTS.keys()))
location = st.text_input("Site Location", "Stone's Beta-08")
auditor = st.text_input("Auditor Name", "Jane Doe")
date_today = datetime.today().strftime('%Y-%m-%d')

st.markdown("---")
st.subheader("Checklist")

checklist_data = {}
num_no = 0
for item in JOB_CHECKLISTS[job_title]:
    cols = st.columns([0.5, 0.2, 0.3])
    with cols[0]:
        st.markdown(f"**{item}**")
    with cols[1]:
        status = st.radio("", ["Yes", "No", "N/A"], horizontal=True, key=f"status_{item}")
    with cols[2]:
        comment = st.text_input("Comment", key=f"comment_{item}")
    checklist_data[item] = {"status": status, "comment": comment}
    if status == "No":
        num_no += 1

st.markdown("---")

st.subheader("Upload Evidence Images")
uploaded_images = st.file_uploader("Upload images (optional)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if num_no == 0:
    risk_level = "Green"
elif num_no <= 2:
    risk_level = "Yellow"
else:
    risk_level = "Red"

if st.button("Generate PDF Report"):
    site_info = {
        "Job Title": job_title,
        "Site Type": site_type,
        "Location": location,
        "Date": date_today,
        "Auditor": auditor
    }
    pdf_file = generate_pdf(site_info, checklist_data, uploaded_images, risk_level)
    log_report_to_db(site_info, pdf_file, risk_level)
    with open(pdf_file, "rb") as f:
        st.download_button("Download Report PDF", f, file_name=pdf_file, mime="application/pdf")

st.markdown("---")
st.subheader("📁 View Past Reports")
if st.checkbox("Show Report History"):
    conn = sqlite3.connect("hse_reports.db")
    c = conn.cursor()
    c.execute("SELECT date, job_title, site_type, location, auditor, risk_level FROM reports ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    for row in rows:
        st.write(f"**Date:** {row[0]} | **Job:** {row[1]} | **Site:** {row[2]} | **Location:** {row[3]} | **Auditor:** {row[4]} | **Risk:** {row[5]}")
