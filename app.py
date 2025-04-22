# app.py

import streamlit as st
import pandas as pd
import json
import altair as alt
from datetime import datetime
from fpdf import FPDF, FPDFException
import io

# ——— MOCK DATA (non‑PII) ———
USE_MOCK = True

MOCK_SUBMISSIONS_JSON = """
[
  { "id":"11111111-1111-1111-1111-111111111111","nric_fin":"S2342433Z","principal_name":"John Doe","nationality":"SINGAPORE CITIZEN","created_at":"2025-04-21T08:21:39Z" },
  { "id":"22222222-2222-2222-2222-222222222222","nric_fin":"S1234567J","principal_name":"Tom Moddy","nationality":"SINGAPORE CITIZEN","created_at":"2025-04-21T07:55:47Z" },
  { "id":"33333333-3333-3333-3333-333333333333","nric_fin":"S9876543B","principal_name":"Yan Hu","nationality":"SINGAPORE CITIZEN","created_at":"2025-04-21T04:27:24Z" }
]
"""

MOCK_CUSTOMER_JSON = """
{
  "id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","session_id":"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  "nric_fin":"S2342433Z","principal_name":"John Doe","alias_name":"Johnny D","sex":"Male","dob":"1985-08-20",
  "residential_status":"Permanent Resident","nationality":"Singaporean","country_of_birth":"Singapore",
  "pass_type":"PR","pass_status":"Active","pass_expiry_date":"2030-08-20","employment_sector":"Technology",
  "notice_of_assessment":[
    {"year":2024,"type":"Normal Assessment","assessable_income":95000,
     "income_breakdown":{"employment":90000,"trade":2000,"rent":1000,"interest":0}
    },
    {"year":2023,"type":"Normal Assessment","assessable_income":92000,
     "income_breakdown":{"employment":88000,"trade":2000,"rent":1000,"interest":0}
    }
  ],
  "employer_name":"Acme Solutions Pte Ltd","occupation":"Software Engineer",
  "mobile_number":"91230000","email_address":"john.doe@example.com","registered_address":"123 Alpha Street, #01-01, Singapore 123456",
  "revised_mobile_number":"98760000","revised_email_address":"johnny.d@example.com",
  "revised_registered_address":"456 Beta Avenue, #02-02, Singapore 654321",
  "residential_address":"789 Gamma Road, #03-03, Singapore 789123",
  "created_at":"2025-01-10T09:00:00Z","updated_at":"2025-04-22T11:19:45Z"
}
"""

# ——— DATA LOADERS ———
def load_submissions(start_date, end_date):
    data = json.loads(MOCK_SUBMISSIONS_JSON) if USE_MOCK else []
    df = pd.DataFrame(data)
    df["created_at"] = pd.to_datetime(df["created_at"])
    mask = (
        (df["created_at"].dt.date >= start_date) &
        (df["created_at"].dt.date <= end_date)
    )
    return df.loc[mask].reset_index(drop=True)

def load_customer(q):
    data = json.loads(MOCK_CUSTOMER_JSON) if USE_MOCK else {}
    return pd.Series(data)

# ——— PDF GENERATORS ———
def pdf_from_submissions(df: pd.DataFrame) -> io.BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, " KYC ", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 8, f"Total Submissions: {len(df)}", ln=True)
    pdf.ln(5)

    cols = ["NRIC", "Customer Name", "Nationality", "Submitted On"]
    widths = [40, 60, 50, 40]
    pdf.set_font("Helvetica", "B", 10)
    for w, col in zip(widths, cols):
        pdf.cell(w, 8, col, border=1)
    pdf.ln(8)

    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        pdf.cell(widths[0], 6, row["NRIC"], border=1)
        pdf.cell(widths[1], 6, row["Customer Name"], border=1)
        pdf.cell(widths[2], 6, row["Nationality"], border=1)
        pdf.cell(widths[3], 6, row["Submitted On (UTC)"].strftime("%Y-%m-%d"), border=1)
        pdf.ln(6)

    raw = pdf.output(dest="S")
    pdf_bytes = bytes(raw) if isinstance(raw, (bytes, bytearray)) else raw.encode("latin-1")
    return io.BytesIO(pdf_bytes)

def pdf_from_customer(cust: pd.Series) -> io.BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Customer Details", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", size=12)

    # Render basic fields with safe chunking
    fields = [
      ("Principal Name", cust.get("principal_name","-")),
      ("Alias Name",      cust.get("alias_name","-")),
      ("NRIC/FIN",        cust.get("nric_fin","-")),
      ("Sex",             cust.get("sex","-")),
      ("Date of Birth",   cust.get("dob","-")),
      ("Nationality",     cust.get("nationality","-")),
      ("Residential Status", cust.get("residential_status","-")),
      ("Pass Type",       cust.get("pass_type","-")),
      ("Pass Status",     cust.get("pass_status","-")),
      ("Pass Expiry Date",cust.get("pass_expiry_date","-")),
      ("Occupation",      cust.get("occupation","-")),
      ("Employment Sector",cust.get("employment_sector","-")),
      ("Employer Name",   cust.get("employer_name","-"))
    ]
    for label, val in fields:
        text = str(val).replace("\n"," ")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50,6,f"{label}:",ln=0)
        pdf.set_font("Helvetica", size=10)
        for i in range(0, len(text), 50):
            chunk = text[i:i+50]
            try:
                pdf.multi_cell(0,6,chunk)
            except FPDFException:
                pdf.cell(0,6,chunk, ln=1)

    # Notice of Assessment
    pdf.ln(3)
    pdf.set_font("Helvetica","B",12)
    pdf.cell(0,6,"Notice of Assessment (Last 2 Years):",ln=True)
    pdf.set_font("Helvetica",size=10)
    for e in cust.get("notice_of_assessment",[]):
        line = f"{e.get('year','-')} {e.get('type','-')}: Income {e.get('assessable_income','-')}"
        for i in range(0, len(line), 50):
            chunk = line[i:i+50]
            try:
                pdf.multi_cell(0,6,chunk)
            except FPDFException:
                pdf.cell(0,6,chunk, ln=1)

    raw = pdf.output(dest="S")
    pdf_bytes = bytes(raw) if isinstance(raw,(bytes,bytearray)) else raw.encode("latin-1")
    return io.BytesIO(pdf_bytes)

# ——— PAGE CONFIG & CSS ———
st.set_page_config(page_title="Singpass KYC", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
/* Light mode & fonts */
.stApp, .main, .block-container {background:#F5F5F5; color:#000 !important;}
body, .stApp, .main {font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Open Sans', sans-serif; font-size:16px; line-height:1.5;}

/* Header & banner */
.header {display:flex; align-items:center; padding:16px; background:#FFF; box-shadow:0 2px 4px rgba(0,0,0,0.1);}
.header img {height:32px; margin-right:12px;}
.header h1 {font-size:24px; font-weight:500; margin:0;}
.banner {display:flex; justify-content:space-between; background:#C8191D; color:#FFF; padding:6px 20px; font-size:16px;}
.banner .left {font-weight:400;} .banner .right {font-size:12px; opacity:0.9;}

/* Tabs */
[role="tablist"] > [role="tab"] { font-size:18px !important; color:#666 !important; padding:8px 16px !important; }
[role="tablist"] > [role="tab"][aria-selected="true"] { color:#C8191D !important; border-bottom:3px solid #C8191D !important; }

/* Inputs */
.stDateInput>label, .stTextInput>label {font-size:14px; color:#333; margin-bottom:4px;}
.stDateInput>div, .stTextInput>div>div>input { background:#FFF !important; color:#000 !important; border:1px solid #CCC !important; border-radius:4px; padding:4px 8px; }

/* Metric */
.metric {text-align:center; padding:24px;}
.metric .label {font-size:18px; color:#666;}
.metric .value {font-size:64px; color:#C8191D; margin-top:4px;}

/* Table */
.styled-table {width:100%; border-collapse:collapse; font-size:16px;}
.styled-table th {background:#C8191D; color:#FFF; text-align:left; padding:10px;}
.styled-table td {padding:10px; color:#000;}
.styled-table tr:nth-child(even) td {background:#F9F9F9;}
.styled-table tr:nth-child(odd) td {background:#FFF;}

/* Download Button */
.stDownloadButton>button { background-color:#C8191D !important; color:#FFF !important; }

/* Section headers */
h3, h2 {font-size:20px !important; margin-top:24px !important;}

/* Footer */
.footer {padding:12px; font-size:12px; color:#666; text-align:center;}
</style>
""", unsafe_allow_html=True)

# ——— MAIN ———
tabs = st.tabs(["📊 Dashboard", "👤 Customer Details"])

with tabs[0]:
    # Header + banner
    st.markdown("""
      <div class="header">
        <img src="https://raw.githubusercontent.com/your-org/singpass-logo.png" alt="logo"/>
        <h1> KYC </h1>
      </div>
      <div class="banner">
        <div class="left">Dashboard of customer renewals (Production)</div>
        <div class="right">Data retrieved from Singpass</div>
      </div>
    """, unsafe_allow_html=True)

    # Date range picker & metric
    start, end = st.date_input("Date range", [datetime(2025,1,1), datetime(2025,4,22)])
    df = load_submissions(start, end)
    st.markdown(f"""
      <div class="metric">
        <div class="label">Total Submissions</div>
        <div class="value">{len(df)}</div>
      </div>
    """, unsafe_allow_html=True)

    # PDF download at top
    df_disp = (
      df.rename(columns={
        "nric_fin":"NRIC","principal_name":"Customer Name",
        "nationality":"Nationality","created_at":"Submitted On (UTC)"
      })
      .drop(columns=["id"], errors="ignore")
      .head(10)
    )
    pdf_buf = pdf_from_submissions(df_disp)
    st.download_button("⬇️ Download PDF", data=pdf_buf, file_name="submissions.pdf", mime="application/pdf")

    # Table
    st.markdown(df_disp.to_html(classes="styled-table", index=False, border=0), unsafe_allow_html=True)

    # Bar chart
    daily = df.assign(day=df["created_at"].dt.date).groupby("day").size().reset_index(name="Submissions")
    chart = (
      alt.Chart(daily).mark_bar(color="#5470C6").encode(x="day:T", y="Submissions:Q")
      + alt.Chart(daily).mark_text(dy=-10, color="#000").encode(x="day:T", text="Submissions:Q")
    ).properties(height=300).configure_axis(labelColor="black", titleColor="black")
    st.altair_chart(chart, use_container_width=True)

    # Footer
    st.markdown(f'<div class="footer">Data Last Updated: {datetime.now():%m/%d/%Y %I:%M %p} | <a href="#">Privacy Policy</a></div>', unsafe_allow_html=True)

with tabs[1]:
    # Header + banner
    st.markdown("""
      <div class="header">
        <img src="https://raw.githubusercontent.com/your-org/validus-logo.png" alt="logo"/>
        <h1>Company Name</h1>
        <span style="margin-left:auto; background:#C8191D; color:#FFF; padding:2px 6px; font-size:10px; transform:rotate(15deg); position:relative; right:20px; top:-10px;">BETA</span>
      </div>
      <div class="banner">
        <div class="left">Record of customer’s renewed KYC</div>
        <div class="right">Data retrieved from Singpass</div>
      </div>
    """, unsafe_allow_html=True)

    # Search box
    q = st.text_input("Search for Customer (NRIC or Name)")
    st.markdown('<p style="font-size:12px; color:#888; margin-top:-12px;">You may search by NRIC / name</p>', unsafe_allow_html=True)

    if q:
        cust = load_customer(q)
        if not cust.empty:
            pdf_c = pdf_from_customer(cust)
            st.download_button("⬇️ Download PDF", data=pdf_c, file_name="customer_details.pdf", mime="application/pdf")

    if q:
        cust = load_customer(q)
        if cust.empty:
            st.warning("No customer found.")
        else:
            st.markdown('<div style="background:#E0E0E0; padding:20px; border-radius:8px;">', unsafe_allow_html=True)
            def md(l, v): return f"<strong>{l}</strong><br>{v or '—'}"
            # Basic info rows
            c1, c2 = st.columns(2)
            c1.markdown(md("Principal Name", cust.principal_name), unsafe_allow_html=True)
            c2.markdown(md("Alias Name",    cust.alias_name),      unsafe_allow_html=True)
            for cols, keys in [
              (st.columns(3), ["nric_fin","sex","dob"]),
              (st.columns(3), ["country_of_birth","nationality","residential_status"]),
              (st.columns(3), ["pass_type","pass_status","pass_expiry_date"])
            ]:
                for col, k in zip(cols, keys):
                    col.markdown(md(k.replace("_"," ").title(), cust[k]), unsafe_allow_html=True)
            st.markdown(md("Occupation", cust.occupation), unsafe_allow_html=True)
            st.markdown(md("Employment Sector", cust.employment_sector), unsafe_allow_html=True)
            st.markdown(md("Name of Employer", cust.employer_name), unsafe_allow_html=True)

            # Notice of Assessment
            st.markdown("<h3>Notice of Assessment (Last 2 Years)</h3>", unsafe_allow_html=True)
            for ea in cust.notice_of_assessment:
                st.markdown(f"""
                  <div style="background:#FFF; padding:12px; border-radius:4px; margin-bottom:12px;">
                    <strong>Year:</strong> {ea['year']} <strong>Type:</strong> {ea['type']}<br>
                    <strong>Assessable Income:</strong> {ea['assessable_income']:,}<br>
                    <ul style="margin:4px 0 0 16px;">
                      <li>Employment: {ea['income_breakdown']['employment']:,}</li>
                      <li>Trade:      {ea['income_breakdown']['trade']:,}</li>
                      <li>Rent:       {ea['income_breakdown']['rent']:,}</li>
                      <li>Interest:   {ea['income_breakdown']['interest']:,}</li>
                    </ul>
                  </div>
                """, unsafe_allow_html=True)

            # Contact & addresses
            st.markdown("<h3>Contact Details</h3>", unsafe_allow_html=True)
            cc1, cc2 = st.columns(2)
            cc1.markdown(md("Mobile (Singpass)",       cust.mobile_number), unsafe_allow_html=True)
            cc2.markdown(md("Mobile (New)",            cust.revised_mobile_number), unsafe_allow_html=True)
            cc1.markdown(md("Email (Singpass)",        cust.email_address), unsafe_allow_html=True)
            cc2.markdown(md("Email (New)",             cust.revised_email_address), unsafe_allow_html=True)
            st.markdown(md("Registered Address (Singpass)", cust.registered_address), unsafe_allow_html=True)
            st.markdown(md("Registered Address (New)",      cust.revised_registered_address), unsafe_allow_html=True)
            st.markdown(md("Residential Address",           cust.residential_address), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Footer
            st.markdown(f'<div class="footer">Data Last Updated: {datetime.now():%m/%d/%Y %I:%M %p} | <a href="#">Privacy Policy</a></div>', unsafe_allow_html=True)
