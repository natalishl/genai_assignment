from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv

# Load .env from the project root (one level above this file)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

# Load credentials from environment
endpoint = os.getenv("AZURE_OCR_ENDPOINT")
api_key = os.getenv("AZURE_OCR_API_KEY")

if not endpoint or not api_key:
    raise ValueError("❌ Missing Azure OCR credentials. Check your .env file.")

client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-layout", f)
        result = poller.result()
    return result

def print_all_document_content(result):
    for page in result.pages:
        print(f"---- Analyzing page #{page.page_number} ----")
        print(f"Page has width: {page.width} and height: {page.height}")

        if hasattr(page, 'lines'):
            for line_idx, line in enumerate(page.lines):
                print(f"Line #{line_idx}: {line.content}")

        if hasattr(page, 'tables'):
            for table_idx, table in enumerate(page.tables):
                print(f"Table #{table_idx}: {table.row_count} rows and {table.column_count} columns")
                for cell in table.cells:
                    print(f"Cell[{cell.row_index}][{cell.column_index}]: {cell.content}")

        if hasattr(page, 'selection_marks'):
            for selection_mark in page.selection_marks:
                print(f"Selection mark: {selection_mark.state} with confidence {selection_mark.confidence}")

def process_pdf(file_path):
    result = extract_text_from_pdf(file_path)
    print_all_document_content(result)
