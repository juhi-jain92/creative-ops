import io
import sys
from pathlib import Path

import streamlit as st
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from harness import run_approval_pipeline

st.set_page_config(page_title="Creative Approval", layout="wide")

INDUSTRY_VERTICALS = [
    "Select…",
    "Automotive",
    "Consumer Packaged Goods",
    "E-Commerce / Retail",
    "Financial Services",
    "Food & Beverage",
    "Healthcare & Pharma",
    "Media & Entertainment",
    "Technology",
    "Travel & Hospitality",
    "Telecommunications",
    "Other",
]

MAX_SIZE_BYTES = 150 * 1024
REQUIRED_DIMS = (300, 250)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1100px; }
    [data-testid="stFileUploaderDropzoneInstructions"] small { display: none; }
    [data-testid="stFileUploaderDropzoneInstructions"]::after {
        content: "Limit 150 KB per file";
        font-size: 0.8rem;
        color: #6b7280;
    }
    .success-box {
        background: #f0fdf4;
        border: 1.5px solid #86efac;
        border-radius: 10px;
        padding: 1.5rem 2rem;
        margin-top: 1.5rem;
    }
    .meta-row { display: flex; gap: 2rem; flex-wrap: wrap; margin-top: 0.5rem; }
    .meta-item { font-size: 0.92rem; color: #374151; }
    .meta-label { font-weight: 600; color: #111827; }
    h1 { font-size: 1.6rem !important; font-weight: 700 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Creative Approval")
st.caption("Upload your display creative and fill in the campaign details to begin the approval process.")

st.divider()

upload_col, form_col = st.columns([1, 1.4], gap="large")

with upload_col:
    st.subheader("Creative File")
    uploaded_file = st.file_uploader(
        "Drop a JPG or PNG here (max 150 KB)",
        type=["jpg", "jpeg", "png"],
        help="Accepted formats: JPG, PNG · Max size: 150 KB · Required dimensions: 300 × 250 px",
    )

with form_col:
    st.subheader("Campaign Details")
    advertiser = st.text_input("Advertiser Name", placeholder="e.g. Acme Corporation")
    vertical = st.selectbox("Industry Vertical", INDUSTRY_VERTICALS)
    st.text_input("Ad Slot", value="300 × 250", disabled=True)
    start_date = st.date_input("Campaign Start Date")
    email = st.text_input(
        "Your Email",
        value="juhijaindtu@gmail.com",
        placeholder="you@example.com",
    )

st.divider()

submit = st.button("Submit for Validation", type="primary", use_container_width=False)

if submit:
    errors = []

    if uploaded_file is None:
        errors.append("Please upload a creative file.")
    else:
        file_bytes = uploaded_file.read()
        size_kb = len(file_bytes) / 1024

        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png"):
            errors.append(f"File type **{ext.upper()}** is not supported. Use JPG or PNG.")

        if len(file_bytes) > MAX_SIZE_BYTES:
            errors.append(f"File size is **{size_kb:.1f} KB** — must be under 150 KB.")

        try:
            img = Image.open(io.BytesIO(file_bytes))
            w, h = img.size
            if (w, h) != REQUIRED_DIMS:
                errors.append(
                    f"Dimensions are **{w} × {h} px** — must be exactly 300 × 250 px."
                )
        except Exception:
            errors.append("Could not read image dimensions. Make sure the file is a valid JPG or PNG.")

    if not advertiser.strip():
        errors.append("Advertiser Name is required.")
    if vertical == "Select…":
        errors.append("Please select an Industry Vertical.")
    if not email.strip() or "@" not in email:
        errors.append("A valid email address is required.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        st.session_state["validated"] = True
        st.session_state["preview_bytes"] = file_bytes
        st.session_state["meta"] = {
            "Advertiser": advertiser.strip(),
            "Vertical": vertical,
            "Ad Slot": "300 × 250",
            "Start Date": start_date.strftime("%B %d, %Y"),
            "Email": email.strip(),
            "File": uploaded_file.name,
            "Size": f"{size_kb:.1f} KB",
        }

if st.session_state.get("validated"):
    meta = st.session_state["meta"]
    preview_bytes = st.session_state["preview_bytes"]

    st.markdown(
        """
        <div class="success-box">
        <span style="font-size:1.1rem; font-weight:700; color:#15803d;">✓ Creative validated successfully</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    prev_col, detail_col = st.columns([1, 1.5], gap="large")

    with prev_col:
        st.image(preview_bytes, caption=meta["File"], use_column_width=False, width=300)

    with detail_col:
        st.markdown("**Campaign details**")
        rows = [
            ("Advertiser", meta["Advertiser"]),
            ("Industry Vertical", meta["Vertical"]),
            ("Ad Slot", meta["Ad Slot"]),
            ("Campaign Start", meta["Start Date"]),
            ("Email", meta["Email"]),
            ("File", f"{meta['File']} ({meta['Size']})"),
        ]
        for label, value in rows:
            st.markdown(f"<span style='color:#6b7280;font-size:.85rem;'>{label}</span><br><span style='font-weight:600'>{value}</span>", unsafe_allow_html=True)
            st.write("")

    st.divider()

    if st.button("Run Approval Check", type="primary"):
        with st.spinner("Processing…"):
            result = run_approval_pipeline(preview_bytes, meta)
        st.session_state["pipeline_result"] = result

if st.session_state.get("pipeline_result"):
    result = st.session_state["pipeline_result"]
    verdict = result["verdict"]

    VERDICT_STYLE = {
        "Approved": ("✓ Approved", "#15803d", "#f0fdf4", "#86efac"),
        "Flagged":  ("⚠ Flagged",  "#92400e", "#fffbeb", "#fcd34d"),
        "Rejected": ("✕ Rejected", "#991b1b", "#fef2f2", "#fca5a5"),
    }
    label, text_color, bg_color, border_color = VERDICT_STYLE[verdict]

    st.markdown(
        f"""
        <div style="background:{bg_color};border:1.5px solid {border_color};border-radius:10px;
                    padding:1.2rem 2rem;margin-top:1rem;">
          <span style="font-size:1.15rem;font-weight:700;color:{text_color};">{label}</span>
          <span style="margin-left:1.5rem;color:#6b7280;font-size:0.9rem;">
            Pass rate: <strong>{result['pass_rate']*100:.0f}%</strong>
            &nbsp;·&nbsp; Rules version: {result['rules_version']}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Rule breakdown")
    for r in result["logs"]:
        icon = "✓" if r["passed"] else ("✕" if r["rule_type"] == "hard_stop" else "⚠")
        color = "#15803d" if r["passed"] else ("#991b1b" if r["rule_type"] == "hard_stop" else "#92400e")
        badge = "Hard stop" if r["rule_type"] == "hard_stop" else "Soft rule"
        st.markdown(
            f"<span style='color:{color};font-weight:600;'>{icon} {r['rule_name']}</span>"
            f"<span style='color:#9ca3af;font-size:0.8rem;margin-left:0.5rem;'>[{badge}]</span>"
            f"<span style='color:#374151;font-size:0.88rem;margin-left:0.75rem;'>{r['reasoning']}</span>",
            unsafe_allow_html=True,
        )
