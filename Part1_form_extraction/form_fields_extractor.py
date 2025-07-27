import openai
import os
from dotenv import load_dotenv
from document_ocr import extract_text_from_pdf
import json
from typing import Tuple

# Load environment variables
load_dotenv()

# Configure Azure OpenAI client
client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def extract_fields_from_text(ocr_text: str) -> str:
    messages = [
        {"role": "system", "content": "You are an expert in data analysis and creating the appropriate JSON based on the data received from OCR."},
        {"role": "user", "content": f"""
Please extract the following fields from the text and return them as raw JSON only. Do not include explanations, markdown, or backticks.
If a field is missing, use an empty string.

Expected fields:
- lastName, firstName, idNumber, gender
- dateOfBirth (day, month, year)
- address (street, houseNumber, entrance, apartment, city, postalCode, poBox)
- landlinePhone, mobilePhone
- jobType
- dateOfInjury (day, month, year), timeOfInjury
- accidentLocation, accidentAddress, accidentDescription
- injuredBodyPart, signature
- formFillingDate (day, month, year)
- formReceiptDateAtClinic (day, month, year)
- medicalInstitutionFields (healthFundMember, natureOfAccident, medicalDiagnoses)

Text:
{ocr_text}
"""}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2000,
            temperature=0.3
        )
        result = response.choices[0].message.content.strip()
        return result.replace("```json", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error extracting fields: {e}")
        return None

def validate_extracted_data(json_object: dict) -> Tuple[str, str]:
    json_str = json.dumps(json_object, ensure_ascii=False)

    prompt = f"""
You are an expert in data validation. Validate the following JSON fields based on the rules below.
Return the corrected JSON ONLY (no markdown, no explanation). Replace invalid values with "".

Validation rules:
- lastName, firstName: at least 2 characters
- idNumber: 9-10 digit number
- gender: one of M, F, male, female, ז, נ, זכר, נקבה, לא מוגדר
- dateOfBirth, dateOfInjury, formFillingDate, formReceiptDateAtClinic: valid dates
- address fields: at least 2 characters or 5-7 digit postal code
- phone numbers: 7-15 digits
- jobType, accidentDescription, accidentLocation: at least 2 characters
- dateOfBirth < formFillingDate, dateOfInjury <= formFillingDate

Here is the JSON:
{json_str}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=2000,
            temperature=0.3
        )
        result = response.choices[0].message.content.strip()
        return result.replace("```json", "").replace("```", "").strip(), None
    except Exception as e:
        print(f"Error validating data: {e}")
        return None, None

def calculate_completeness(data: dict) -> float:
    def count(d):
        total = 0
        empty = 0
        for v in d.values():
            if isinstance(v, dict):
                t, e = count(v)
                total += t
                empty += e
            else:
                total += 1
                if not v or str(v).strip() == "":
                    empty += 1
        return total, empty

    total, empty = count(data)
    return round(100 * (total - empty) / total, 2) if total > 0 else 0.0

def calculate_validation_consistency(predicted: dict, validated: dict) -> float:
    def flatten(d, prefix=''):
        flat = {}
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                flat.update(flatten(v, full_key))
            else:
                flat[full_key] = str(v).strip()
        return flat

    pred_flat = flatten(predicted)
    val_flat = flatten(validated)

    if not pred_flat or not val_flat:
        return 0.0

    total = len(val_flat)
    unchanged = sum(1 for k in val_flat if k in pred_flat and pred_flat[k] == val_flat[k])

    return round(100 * unchanged / total, 2)

def process_pdf(file_path: str, ground_truth_path: str = None):
    print(f"Processing: {file_path}")
    ocr_text = extract_text_from_pdf(file_path)
    if not ocr_text:
        print("OCR extraction failed.")
        return

    raw = extract_fields_from_text(ocr_text)
    if not raw:
        print("Field extraction failed.")
        return

    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error parsing extracted JSON: {e}")
        print("Raw output:", raw)
        return

    validated_raw, _ = validate_extracted_data(extracted)
    if not validated_raw:
        print("Validation failed.")
        return

    try:
        validated = json.loads(validated_raw)
    except json.JSONDecodeError as e:
        print(f"Error parsing validated JSON: {e}")
        print("Raw output:", validated_raw)
        return

    print("\nExtracted JSON:")
    print(json.dumps(extracted, indent=2, ensure_ascii=False))

    print("\nValidated JSON:")
    print(json.dumps(validated, indent=2, ensure_ascii=False))

    completion = calculate_completeness(validated)
    print(f"\n🧮 Completion Rate: {completion}%")
    if completion < 80:
        print("⚠️ Warning: Form is incomplete (more than 20% of fields are missing).")
    else:
        print("✅ Form is sufficiently complete.")

    consistency = calculate_validation_consistency(extracted, validated)
    print(f"🔁 Validation Consistency: {consistency}%")
