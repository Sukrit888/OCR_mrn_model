import streamlit as st
from PIL import Image
import json
import base64
import os
from openai import OpenAI

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(
    page_title="MRN OCR Extractor",
    page_icon="🧾",
    layout="centered"
)

st.title("🧾 MRN Image OCR Extractor")
st.caption("Upload a Meter Replacement Notice (MRN) image to extract real data.")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# -------------------------------
# FILE UPLOAD
# -------------------------------
uploaded_file = st.file_uploader(
    "Upload MRN Image",
    type=["jpg", "jpeg", "png"]
)

# -------------------------------
# OCR + EXTRACTION FUNCTION
# -------------------------------
def extract_mrn_data(image_path: str) -> dict:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
You are an OCR and document understanding system.

Extract the following fields from the MRN image.
Return ONLY valid JSON.
If a field is not present, return an empty string.

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
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return {"error": "Failed to parse OCR output", "raw_output": raw_output}

# -------------------------------
# MAIN LOGIC
# -------------------------------
if uploaded_file:
    st.subheader("📷 Uploaded Image")

    image = Image.open(uploaded_file)
    st.image(image, use_container_width=True)

    temp_path = os.path.join("/tmp", uploaded_file.name)
    image.save(temp_path)

    if st.button("🔍 Extract Data"):
        with st.spinner("Reading image and extracting real data..."):
            extracted_data = extract_mrn_data(temp_path)

        st.success("✅ Extraction Complete")

        st.subheader("📄 Extracted Data")
        st.code(json.dumps(extracted_data, indent=2), language="json")

        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(extracted_data, indent=2),
            file_name="mrn_extracted_data.json",
            mime="application/json"
        )
