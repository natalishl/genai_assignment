import streamlit as st
from document_ocr import extract_text_from_pdf
from form_fields_extractor import (
    extract_fields_from_text,
    validate_extracted_data,
    calculate_completeness,
    calculate_validation_consistency
)
import tempfile
import json
import os


def main():
    st.set_page_config(
        page_title="National Insurance Forms OCR",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("""
    <style>
    .main-result {
        background-color: #f0f8ff;
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
    }
    .result-title {
        color: #2E7D32;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 15px;
        text-align: center;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .step-header {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("📄 National Insurance Forms OCR System")
    st.markdown("Extract and validate data from National Insurance Institute forms using AI-powered OCR.")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        uploaded_file = st.file_uploader(
            "Upload a PDF or image file (JPG/JPEG)",
            type=["pdf", "jpg", "jpeg"],
            help="Select a National Insurance form document to process"
        )

    if uploaded_file:
        with st.spinner("📤 Processing uploaded file..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(uploaded_file.getbuffer())
                temp_file_path = temp_file.name

        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("🔍 Step 1/4: Extracting text using OCR...")
        progress_bar.progress(25)
        
        ocr_text = extract_text_from_pdf(temp_file_path)
        if not ocr_text:
            st.error("❌ OCR text extraction failed.")
            return

        status_text.text("🔢 Step 2/4: Extracting form fields...")
        progress_bar.progress(50)
        
        extracted_data = extract_fields_from_text(ocr_text)
        if not extracted_data:
            st.error("❌ Field extraction failed.")
            return

        try:
            cleaned_data = extracted_data.replace("```json", "").replace("```", "").strip()
            json_data = json.loads(cleaned_data)
        except json.JSONDecodeError as e:
            st.error(f"❌ Error parsing extracted data as JSON: {e}")
            return

        status_text.text("✅ Step 3/4: Validating extracted data...")
        progress_bar.progress(75)
        
        validated_json_str, _ = validate_extracted_data(json_data)
        try:
            validated_data = json.loads(validated_json_str)
        except json.JSONDecodeError as e:
            st.error(f"❌ Error parsing validated data as JSON: {e}")
            return

        status_text.text("📊 Step 4/4: Calculating metrics...")
        progress_bar.progress(100)
        
        completeness = calculate_completeness(validated_data)
        consistency = calculate_validation_consistency(json_data, validated_data)

        progress_bar.empty()
        status_text.empty()

        st.markdown('<div class="success-message">✅ Processing completed successfully!</div>', 
                   unsafe_allow_html=True)

        st.markdown("""
        <div class="main-result">
            <div class="result-title">🎯 FINAL VALIDATED RESULT</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.json(validated_data)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.download_button(
                label="💾 Download Final Result (JSON)",
                data=json.dumps(validated_data, indent=2, ensure_ascii=False),
                file_name=f"validated_{uploaded_file.name.split('.')[0]}.json",
                mime="application/json",
                type="primary"
            )

        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                label="📊 Form Completeness",
                value=f"{completeness}%",
                delta=f"{'Good' if completeness >= 80 else 'Needs Review'}"
            )
            st.progress(completeness / 100)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric(
                label="🔍 Validation Consistency",
                value=f"{consistency}%",
                delta=f"{'Reliable' if consistency >= 90 else 'Check Data'}"
            )
            st.progress(consistency / 100)
            st.markdown('</div>', unsafe_allow_html=True)

        if completeness >= 80 and consistency >= 90:
            st.success("🎉 Excellent! High quality extraction with reliable validation.")
        elif completeness >= 80:
            st.warning("⚠️ Good extraction but validation shows some inconsistencies.")
        else:
            st.warning("⚠️ Form appears incomplete. Please verify the source document quality.")

        with st.expander("🔍 View OCR Text (Raw)", expanded=False):
            st.text_area("Extracted OCR Text", ocr_text, height=200, disabled=True)

        with st.expander("📋 View Raw Extracted Data", expanded=False):
            st.json(json_data)
            st.download_button(
                label="💾 Download Raw Extracted JSON",
                data=json.dumps(json_data, indent=2, ensure_ascii=False),
                file_name=f"raw_extracted_{uploaded_file.name.split('.')[0]}.json",
                mime="application/json"
            )

        with st.expander("📈 Processing Details", expanded=False):
            st.write("**Processing Steps Completed:**")
            st.write("✅ 1. OCR Text Extraction")
            st.write("✅ 2. Field Extraction using AI")
            st.write("✅ 3. Data Validation and Correction")
            st.write("✅ 4. Quality Assessment")
            
            st.write("**File Information:**")
            st.write(f"- **Filename:** {uploaded_file.name}")
            st.write(f"- **File Size:** {uploaded_file.size:,} bytes")
            st.write(f"- **File Type:** {uploaded_file.type}")

        try:
            os.unlink(temp_file_path)
        except:
            pass

    else:
        st.info("👆 Please upload a National Insurance form document to begin processing.")
        
        st.markdown("### 📋 Supported Features:")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **✅ Document Types:**
            - PDF files
            - JPEG/JPG images
            - Hebrew and English forms
            """)
            
        with col2:
            st.markdown("""
            **🔧 Processing Steps:**
            - OCR text extraction
            - AI-powered field extraction
            - Data validation & correction
            - Quality assessment
            """)


if __name__ == "__main__":
    main()