import streamlit as st
from PIL import Image, ImageEnhance
import json
import base64
import os
import re
from datetime import datetime
from openai import OpenAI

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="AI Based Old Meter to New Smart Meter Replacement Data Audit",
    page_icon="🧾",
    layout="centered"
)

st.title("AI Based Old Meter to New Smart Meter Replacement Data Audit")
st.caption(
    "AI-powered OCR system with validation rules for auditing old-to-new smart meter replacement data."
)

# =====================================================
# OPENAI KEY CHECK
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
# IMAGE PRE-PROCESSING
# =====================================================
def preprocess_image(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    image = ImageEnhance.Contrast(image).enhance(1.6)
    image = ImageEnhance.Sharpness(image).enhance(1.8)
    return image

# =====================================================
# JSON CLEANER
# =====================================================
def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
    if text.lower().startswith("json"):
        text = text[4:]
    return text.strip()

# =====================================================
# FIELD-LEVEL VALIDATORS
# =====================================================
def validate_sub_division(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits if len(digits) in [5, 6] else ""

def validate_account_no(value: str) -> str:
    if not value:
        return ""
    # Allow formats like 00/08/30239/3
    return value.strip() if re.search(r"\d+/\d+/\d+", value) else ""

def validate_meter_no(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    if re.search(r"[A-Za-z]", value) and re.search(r"\d", value):
        return value
    return ""

def validate_reading(value: str) -> str:
    if not value:
        return ""
    match = re.findall(r"\d+\.?\d*", value)
    return match[0] if match else ""

def validate_date(value: str) -> str:
    if not value:
        return ""
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%d/%m/%Y")
        except:
            pass
    return ""

def clean_text(value: str) -> str:
    return value.strip() if value else ""

# =====================================================
# OCR + EXTRACTION
# =====================================================
def extract_mrn_data(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
You are an expert OCR + document understanding system for Indian Electricity MRN forms.

IMPORTANT:
- Carefully scan header, body, tables, stamps, and footer
- Prefer PRINTED text over handwritten for technical fields
- Prefer handwritten only for name/address if printed missing

Return ONLY raw JSON (no markdown).
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

    raw = response.choices[0].message.content
    data = json.loads(clean_json(raw))

    # =================================================
    # APPLY FIELD-LEVEL VALIDATION
    # =================================================
    validated = {
        "sub_division": validate_sub_division(data.get("sub_division")),
        "feeder_name": clean_text(data.get("feeder_name")),
        "consumer_name": clean_text(data.get("consumer_name")),
        "consumer_address": clean_text(data.get("consumer_address")),
        "consumer_account_no": validate_account_no(data.get("consumer_account_no")),
        "date_of_installation": validate_date(data.get("date_of_installation")),
        "old_meter_no": validate_meter_no(data.get("old_meter_no")),
        "old_meter_reading": validate_reading(data.get("old_meter_reading")),
        "old_meter_make": clean_text(data.get("old_meter_make")),
        "new_meter_no": validate_meter_no(data.get("new_meter_no")),
        "new_meter_reading": validate_reading(data.get("new_meter_reading")),
        "new_meter_make": clean_text(data.get("new_meter_make")),
        "consumer_category": clean_text(data.get("consumer_category"))
    }

    return validated

# =====================================================
# UI LOGIC
# =====================================================
if uploaded_file:
    st.subheader("📷 Uploaded Image")

    original = Image.open(uploaded_file)
    processed = preprocess_image(original)

    st.image(
        [original, processed],
        caption=["Original Image", "Enhanced for OCR"],
        use_container_width=True
    )

    temp_path = os.path.join("/tmp", uploaded_file.name)
    processed.save(temp_path)

    if st.button("🔍 Extract & Validate Data"):
        with st.spinner("Extracting and validating MRN data..."):
            output = extract_mrn_data(temp_path)

        st.success("✅ Extraction & Validation Complete")

        st.subheader("📄 Validated Output")
        st.code(json.dumps(output, indent=2), language="json")

        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(output, indent=2),
            file_name="mrn_validated_data.json",
            mime="application/json"
        )
