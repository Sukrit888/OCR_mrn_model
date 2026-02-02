import streamlit as st
from PIL import Image, ImageEnhance
import json
import base64
import os
import re
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
    "AI-powered OCR system to audit and validate old-to-new smart meter replacement data from MRN images."
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
# IMAGE PRE-PROCESSING (KEY UPGRADE)
# =====================================================
def preprocess_image(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")

    # Improve contrast
    image = ImageEnhance.Contrast(image).enhance(1.6)

    # Improve sharpness
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
# NORMALIZATION
# =====================================================
def normalize_sub_division(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits if len(digits) in [5, 6] else ""

def normalize_reading(value: str) -> str:
    return re.sub(r"[^\d.]", "", value or "")

# =====================================================
# OCR + EXTRACTION (TWO-STAGE)
# =====================================================
def extract_mrn_data(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
You are an expert OCR + document understanding system for Indian Electricity MRN forms.

DOCUMENT SCANNING RULES:
- Carefully scan the FULL document: header, tables, body, footer, stamps
- Read text even if faint, rotated, or low-contrast
- Do NOT assume fixed positions (layout varies)

EXTRACTION RULES:
- sub_division: numeric code labeled as Sub-Division / SD Code (5–6 digits)
- Meter numbers are alphanumeric (do not confuse with readings)
- Meter readings are numeric (kWh / units)
- Prefer printed text over handwritten if conflict exists
- Preserve original language (Gujarati / Hindi / English)

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
        data = json.loads(clean_json(raw_output))

        # ---------------------------
        # POST-PROCESSING
        # ---------------------------
        data["sub_division"] = normalize_sub_division(data.get("sub_division"))
        data["old_meter_reading"] = normalize_reading(data.get("old_meter_reading"))
        data["new_meter_reading"] = normalize_reading(data.get("new_meter_reading"))

        return data

    except Exception as e:
        return {
            "error": "Failed to parse OCR output",
            "raw_output": raw_output,
            "exception": str(e)
        }

# =====================================================
# UI LOGIC
# =====================================================
if uploaded_file:
    st.subheader("📷 Uploaded Image")

    original_image = Image.open(uploaded_file)
    processed_image = preprocess_image(original_image)

    st.image(
        [original_image, processed_image],
        caption=["Original Image", "Enhanced for OCR"],
        use_container_width=True
    )

    temp_path = os.path.join("/tmp", uploaded_file.name)
    processed_image.save(temp_path)

    if st.button("🔍 Extract Data"):
        with st.spinner("Analyzing image and extracting detailed information..."):
            extracted_data = extract_mrn_data(temp_path)

        if "error" in extracted_data:
            st.error("❌ Extraction Failed")
            st.code(extracted_data, language="json")
        else:
            st.success("✅ Extraction Complete")

            st.subheader("📄 Extracted Data")
            st.code(json.dumps(extracted_data, indent=2), language="json")

            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(extracted_data, indent=2),
                file_name="mrn_extracted_data.json",
                mime="application/json"
            )
