import streamlit as st
from PIL import Image
import json
import base64
import os
import re
from openai import OpenAI

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="MRN OCR Extractor",
    page_icon="🧾",
    layout="centered"
)

st.title("🧾 MRN Image OCR Extractor")
st.caption("Upload a Meter Replacement Notice (MRN) image to extract verified data.")

# =====================================================
# OPENAI KEY CHECK (CRASH-PROOF)
# =====================================================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ OPENAI_API_KEY not found. Please add it in Streamlit Secrets.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =====================================================
# FILE UPLOADER
# =====================================================
uploaded_file = st.file_uploader(
    "Upload MRN Image",
    type=["jpg", "jpeg", "png"]
)

# =====================================================
# JSON CLEANER (MARKDOWN SAFE)
# =====================================================
def clean_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]

    if text.lower().startswith("json"):
        text = text[4:]

    return text.strip()

# =====================================================
# DOMAIN VALIDATION FUNCTIONS
# =====================================================
def normalize_sub_division(value: str) -> str:
    if not value:
        return ""

    digits = re.sub(r"\D", "", value)

    # Sub-Division codes are typically 5–6 digits
    if len(digits) not in [5, 6]:
        return ""

    return digits


def fallback_sub_division(data: dict) -> str:
    """
    If OCR picked wrong sub-division, try recovering
    from other numeric fields using domain rules.
    """
    for v in data.values():
        digits = re.sub(r"\D", "", str(v))
        if len(digits) in [5, 6]:
            return digits
    return ""


# =====================================================
# OCR + EXTRACTION FUNCTION
# =====================================================
def extract_mrn_data(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
You are extracting data from an Indian Electricity Meter Replacement Notice (MRN).

IMPORTANT RULES:
- sub_division is a numeric code (5–6 digits)
- It is usually labeled as "Sub-Division", "Sub Division", or "SD Code"
- Do NOT confuse it with account number, feeder code, or meter number
- If multiple numeric codes exist, choose the one explicitly tied to Sub-Division

Return ONLY raw JSON.
Do NOT use markdown.
If a field is missing, return an empty string.

Fields:
sub_division
feeder_name
consumer_name
consumer_address
consumer_account_no
date_of_installation
old_meter_no
old_meter_reading
old_meter_make
new_meter_no
new_meter_reading
new_meter_make
consumer_category
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        temperature=0
    )

    raw_output = response.choices[0].message.content

    try:
        cleaned = clean_json(raw_output)
        data = json.loads(cleaned)

        # -------------------------------
        # POST-PROCESSING FIXES
        # -------------------------------
        data["sub_division"] = normalize_sub_division(
            data.get("sub_division", "")
        )

        if not data["sub_division"]:
            data["sub_division"] = fallback_sub_division(data)

        return data

    except Exception as e:
        return {
            "error": "Failed to parse OCR output",
            "raw_output": raw_output,
            "exception": str(e)
        }

# =====================================================
# MAIN UI LOGIC
# =====================================================
if uploaded_file:
    st.subheader("📷 Uploaded Image")

    image = Image.open(uploaded_file)
    st.image(image, use_container_width=True)

    temp_path = os.path.join("/tmp", uploaded_file.name)
    image.save(temp_path)

    if st.button("🔍 Extract Data"):
        with st.spinner("Reading image and extracting verified MRN data..."):
            extracted_data = extract_mrn_data(temp_path)

        if "error" in extracted_data:
            st.error("❌ OCR Parsing Failed")
            st.code(extracted_data, language="json")
        else:
            st.success("✅ Extraction Complete")

            st.subheader("📄 Extracted & Validated Data")
            st.code(json.dumps(extracted_data, indent=2), language="json")

            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(extracted_data, indent=2),
                file_name="mrn_extracted_data.json",
                mime="application/json"
            )
