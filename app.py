import streamlit as st
from PIL import Image
import json
import os

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="MRN OCR Extractor",
    page_icon="🧾",
    layout="centered"
)

st.title("🧾 MRN Image OCR Extractor")
st.caption("Upload an MRN image to extract structured meter replacement data.")

# -------------------------------
# FILE UPLOAD
# -------------------------------
uploaded_file = st.file_uploader(
    "Upload MRN Image",
    type=["jpg", "jpeg", "png"]
)

# -------------------------------
# OCR EXTRACTION FUNCTION
# (Replace with Ollama / OCR later)
# -------------------------------
def extract_mrn_data(image_path: str) -> dict:
    """
    Placeholder extraction logic.
    Replace with your OCR / Vision model.
    """

    return {
        "sub_division": "121336",
        "feeder_name": "",
        "consumer_name": "",
        "consumer_address": "4121/122 518/239/3",
        "consumer_account_no": "00/08/30239/3",
        "date_of_installation": "11/04/25",
        "old_meter_no": "MGS 395852",
        "old_meter_reading": "16352",
        "old_meter_make": "",
        "new_meter_no": "ACXS 21030023",
        "new_meter_reading": "0.3",
        "new_meter_make": "",
        "consumer_category": ""
    }

# -------------------------------
# MAIN LOGIC
# -------------------------------
if uploaded_file:
    st.subheader("📷 Uploaded Image")

    image = Image.open(uploaded_file)
    st.image(image, use_container_width=True)

    # Save image temporarily (Streamlit Cloud safe)
    temp_path = os.path.join("/tmp", uploaded_file.name)
    image.save(temp_path)

    if st.button("🔍 Extract Data"):
        with st.spinner("Extracting data from image..."):
            extracted_data = extract_mrn_data(temp_path)

        st.success("✅ Data Extracted Successfully")

        st.subheader("📄 Extracted Data")
        st.code(json.dumps(extracted_data, indent=2), language="json")

        # Download button
        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(extracted_data, indent=2),
            file_name="mrn_extracted_data.json",
            mime="application/json"
        )
