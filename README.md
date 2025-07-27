> ℹ️ **The configuration (****`.env`****) and dependencies (****`requirements.txt`****) in this project are shared across *****Part 1***** and *****Part 2***** of the assignment.**

---

## 🔐 Environment Configuration (`.env`)

To connect with Azure services, create .env file and fill in your Azure credentials.
This file must be located in the root of the repository (i.e., next to requirements.txt and README.md).

The .env file should look like this:
# Azure Document Intelligence (OCR)
AZURE_OCR_ENDPOINT=https://<your-ocr-resource>.cognitiveservices.azure.com/
AZURE_OCR_API_KEY=your-ocr-api-key

# Azure OpenAI (GPT-4o)
AZURE_OPENAI_ENDPOINT=https://<your-openai-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-api-key

# Azure region
AZURE_LOCATION=eastus

---------------------------------------------------------------------------------------------------

## Part 1: Field Extraction using Document Intelligence & Azure OpenAI

This application allows users to upload scanned National Insurance (ביטוח לאומי) forms (in PDF or image format) and automatically extract important information using artificial intelligence. It supports both Hebrew and English forms.

The system uses:

* **Azure Document Intelligence (OCR)** to read text from the document.
* **Azure OpenAI (GPT-4o)** to understand the content and extract structured information.
* A clear and simple **Streamlit web interface** to guide the user and display the results.

---

## What Happens Behind the Scenes

When you upload a form, the system goes through 4 automatic steps:

### 1. **Text Extraction (OCR)** – (`Part1_form_extraction/document_ocr.py`)

The script reads all visible text from scanned forms (PDF or image) using Azure’s prebuilt-layout model.
It captures printed and handwritten content, in both Hebrew and English, and identifies structural elements like:

* Text lines
* Tables and their cells
* Selection marks (checkboxes and similar elements)

### 2. **Field Extraction with GPT-4o** – (`Part1_form_extraction/form_fields_extractor.py`)

The extracted text is sent to an advanced AI model (GPT-4o), which analyzes the content and extracts key details like name, ID, phone number, address, injury date, and more — all in structured JSON format.

### 3. **Data Validation** – (`Part1_form_extraction/form_fields_extractor.py`)

The extracted information is then checked for correctness. For example:

* ID numbers must be 9–10 digits
* Names must be at least 2 characters
* Dates must make logical sense (e.g., birth before injury)

Any incorrect or missing values are replaced with empty strings (`""`).

### 4. **Quality Metrics** – (`Part1_form_extraction/form_fields_extractor.py`)

The system calculates:

* **Completeness** – how many fields were successfully filled.
* **Consistency** – how much the validated data matches the original extraction.

---

## How to Run Part 1 Application

To run the system locally:

### 1. Install the required Python packages


```bash
pip install -r requirements.txt
```

### 2. Make sure your `.env` file is in place

As shown above, include your Azure credentials in the `.env` file at the root of the project.

### 3. Launch the app

Navigate to the `Part1_form_extraction` folder and run the following command:

```bash
streamlit run app.py
```

The app will open automatically in your browser.
You can now upload a National Insurance form (PDF or image) and view the extracted and validated results through the Streamlit UI.

---------------------------------------------------------------------------------------------------


## Part 2: Microservice-based ChatBot Q&A on Medical Services

This part implements a smart, multilingual chatbot that answers user questions about medical services (Clalit, Maccabi, Meuhedet), based on personal details and official HMO documents provided in HTML format.

The system is **stateless** – meaning the backend does not store any user session. All user details and chat history are passed from the client side with each request.

---

## Key Components & What Each File Does

### 🔹 `bot_app/bot_logic.py`

Contains the full logic of the bot:

* Prompt templates (registration, confirmation, classification, Q\&A)
* Functions to extract user info, classify messages, and answer questions
* Ensures proper conversation flow between user detail collection and Q\&A

### 🔹 `bot_app/embeddings.py`

Handles:

* Creating vector embeddings for texts using ADA-002 model
* Searching for similar chunks in the knowledge base (RAG logic)

### 🔹 `bot_app/html_reader.py`

Parses the HTML files in `phase2_data/` and:

* Extracts relevant chunks (paragraphs, tables, list items)
* Adds metadata (HMO, insurance tier, topic)
* Generates and saves embeddings to `saved_vectors/vectors.json`

### 🔹 `bot_app/server.py`

Implements a **FastAPI microservice** with:

* `/ask` endpoint for handling questions
* `/health` for checking API status
*  Basic logging to monitor API usage, user requests, and internal errors using Python's logging module

### 🔹 `bot_app/user_info.py`

Defines the `UserInfo` model used for structured personal data.

### 🔹 `generate_data.py`

One-time script to extract chunks and generate vectors from HTML files.

### 🔹 `ui/app_ui.py`

Creates a stylish, RTL-friendly **Streamlit interface** that:

* Allows user chat and input in Hebrew or English
* Shows welcome section, chat bubbles, and typing animation
* Handles all state client-side

---

## ▶️ How to Run Part 2 Application

If you **haven’t completed Part 1**, make sure to do the following first:

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Fill in the `.env` file

Create .env file and fill in your Azure credentials as described in the section above.

### 3. Generate embeddings (if not already present)

Check that `saved_vectors/vectors.json` exists. If not, generate it:

```bash
python generate_data.py
```

This will create the vector store from HTML files.

### 4. Start the FastAPI backend
Run from the root directory of the project:

```bash
uvicorn bot_app.server:app --reload
```

Visit the API docs at: `http://localhost:8000/docs`

### 5. Launch the chatbot UI

Navigate to the chatbot folder

cd Part2_ChatBot

Navigate to the UI folder and run:

```bash
streamlit run ui/app_ui.py
```

This opens a chat window for users to start asking health-related questions.


💬 Example User Questions

Here are some example prompts you can use to test the chatbot after completing the identification phase:

אני רוצה להתחיל טיפול בנטורופתיה. מה ההטבות שלי?- 

ומה מגיע לי לגבי ייעוץ תזונתי?- 

---
