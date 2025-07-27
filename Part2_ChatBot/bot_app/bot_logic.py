import os
from dotenv import load_dotenv
import openai
from typing import List, Dict
from bot_app.embeddings import find_similar_chunks

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-01",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

system_prompt = """
You are a smart and polite virtual assistant for healthcare services in Israel.

Your task is to collect the following user details through a natural and adaptive conversation:
1. First name
2. Last name (at least 2 characters)
3. ID number (exactly 9 digits)
4. Gender
5. Age (number between 0 and 120)
6. HMO – one of: Maccabi / Meuhedet / Clalit (or מכבי / מאוחדת / כללית)
7. HMO card number (exactly 9 digits)
8. Insurance tier – one of: Gold / Silver / Bronze (or זהב / כסף / ארד)

Follow these rules:
- Speak in the same language the user uses (Hebrew or English).
- Respond naturally and conversationally. Acknowledge what the user already gave you.
- If the user gives multiple fields in one message, extract them and move to the next missing field.
- Ask one question at a time.
- If the user's message is unclear, very short, or seems like gibberish, politely ask them to clarify while staying friendly and helpful.
- Politely point out invalid answers and ask again.
- Never list all questions at once.
- Always make the conversation feel human and smooth.
- Handle typos, variations, and informal language naturally (e.g., "נקבהה" means "נקבה", "זכרר" means "זכר").

After collecting all required details, summarize everything clearly and ask for confirmation: "Are these details correct?" (or in Hebrew: "האם הפרטים נכונים?")

IMPORTANT: Only after the user confirms everything (says yes/כן/correct etc.), you MUST respond with:
"מצוין! עכשיו תוכל לשאול שאלה ששייכת לשירותים הרפואיים שלך."
(or in English: "Great! Now feel free to ask me a question about your medical services.")

Do NOT move to answering medical questions until you explicitly tell the user they can ask questions.
"""

extraction_prompt_template = """
Extract user information from this healthcare registration conversation. Look for the following fields and return them in JSON format:

Required fields:
- first_name: First name
- last_name: Last name (at least 2 characters)
- id_number: ID number (exactly 9 digits)
- gender: Gender (זכר/נקבה or male/female - normalize variations like "נקבהה" to "נקבה")
- age: Age (number between 0 and 120)
- hmo: HMO name (Maccabi/Meuhedet/Clalit or מכבי/מאוחדת/כללית)
- hmo_card: HMO card number (exactly 9 digits)
- insurance_tier: Insurance tier (Gold/Silver/Bronze or זהב/כסף/ארד)

Rules:
- Only extract information that was clearly provided by the user
- Normalize variations (e.g., "נקבהה" → "נקבה", "מכביי" → "מכבי")
- If information wasn't provided, use empty string ""
- Return only valid JSON

Conversation:
{conversation_text}
"""

confirmation_prompt_template = """
Is this confirmation? '{user_reply}' Answer YES or NO.
"""

medical_classification_prompt_template = """
Message: '{message}'
Context: '{context}'
Answer MEDICAL or NON_MEDICAL.
"""
qa_prompt_template = """
You are a helpful, professional, and trustworthy assistant for healthcare services in Israel.

You have access to:
1. The user's personal details (such as HMO, insurance tier, age, etc.)
2. Knowledge base entries about healthcare services
3. The conversation history to understand context and follow-up questions

Each entry may refer to a specific HMO and insurance tier, and includes the benefits related to a treatment.

Your task:
- Use the conversation history to understand the context and any follow-up questions
- If the user asks a follow-up question about a previous topic, reference the previous discussion
- Use only the chunks in the knowledge base to answer the user's question
- Match the user's HMO and insurance tier to the relevant entries
- If there's a match, provide the exact benefits described in the entry
- Do NOT invent any information
- If no match is found, say: "I'm sorry, I couldn't find information related to your question."
- Respond in the same language the user used (Hebrew or English)
- Do not mention the words "context" or "entry" – just answer naturally and clearly
- Be conversational and reference previous parts of the conversation when relevant

---

User Info:
{user_info_text}

Knowledge Base:
{context}

---

User question:
{user_message}
"""


redirect_prompt_template = """
The user said: "{user_message}"

This doesn't appear to be a medical question.

Respond in the user's language. Redirect politely to healthcare topics.
Examples:
- "I'm here to help with questions about medical services. What would you like to know about your healthcare benefits?"
- "אני כאן לעזור עם שאלות על שירותים רפואיים. במה תרצה שאעזור לך בנושא הבריאות שלך?"
"""

def ask_gpt(messages, max_tokens=1000, temperature=0.1):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    ).choices[0].message.content.strip()

def extract_user_info_with_ai(chat_history: List[Dict[str, str]]) -> Dict[str, str]:
    conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])
    prompt = extraction_prompt_template.format(conversation_text=conversation_text)
    try:
        response = ask_gpt([
            {"role": "system", "content": "Extract user information from a healthcare registration conversation and return JSON."},
            {"role": "user", "content": prompt}
        ], max_tokens=500, temperature=0)
        
        print(f"🔍 AI extraction response: {response}")
        
        import json
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
        else:
            return eval(response.strip())
    except Exception as e:
        print(f"AI extraction failed: {e}")
        return {}

def is_medical_related_ai(user_message: str, chat_history: List[Dict[str, str]]) -> bool:
    recent_messages = chat_history[-6:] if len(chat_history) >= 6 else chat_history
    recent_context = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in recent_messages])
    classification_prompt = medical_classification_prompt_template.format(message=user_message, context=recent_context)
    try:
        response = ask_gpt([
            {"role": "system", "content": "Classify messages as MEDICAL or NON_MEDICAL."},
            {"role": "user", "content": classification_prompt}
        ], max_tokens=10, temperature=0)
        return response.strip().upper() == "MEDICAL"
    except:
        return True

def extract_key_terms(user_message: str) -> List[str]:
    words = user_message.replace('?', '').replace('.', '').replace(',', '').split()
    return [w.lower() for w in words if len(w.strip()) > 2][:3]

def transform_chunk(chunk: str) -> str:
    """
    ממיר צ'אנק טכני בפורמט תגים לניסוח שפה טבעית כדי ש-GPT יבין ויענה נכון.
    """
    import re
    
    service_match = re.search(r"\[שירות: ([^\]]+)\]", chunk)
    hmo_match = re.search(r"\[קופת חולים: ([^\]]+)\]", chunk)
    tier_match = re.search(r"\[רמת ביטוח: ([^\]]+)\]", chunk)
    
    if service_match and hmo_match and tier_match:
 
        last_bracket_pos = chunk.rfind(']')
        if last_bracket_pos != -1 and last_bracket_pos < len(chunk) - 1:
            benefit_text = chunk[last_bracket_pos + 1:].strip()
            
            service = service_match.group(1)
            hmo = hmo_match.group(1)
            tier = tier_match.group(1)
            
            return (
                f"עבור טיפול ב{service}: חברי קופת חולים {hmo} ברמת ביטוח {tier} "
                f"זכאים ל{benefit_text}"
            )
    
    return chunk.strip()

def enhanced_search_and_answer(user_message: str, user_info: Dict[str, str]) -> str:
    print(f"\n🔍 DEBUG - User info received: {user_info}")
    
    tier_translation = {"זהב": "Gold", "כסף": "Silver", "ארד": "Bronze"}
    hmo_translation = {"מכבי": "Maccabi", "מאוחדת": "Meuhedet", "כללית": "Clalit"}
    
    original_hmo = user_info.get("hmo", "").lower()
    clean_hmo = original_hmo.rstrip('י')
    normalized_hmo = hmo_translation.get(clean_hmo, original_hmo)
    user_info["hmo"] = normalized_hmo
    
    original_tier = user_info.get("insurance_tier", "").lower()
    normalized_tier = tier_translation.get(original_tier, original_tier)
    user_info["insurance_tier"] = normalized_tier
    
    print(f"🔍 DEBUG - After normalization: HMO={normalized_hmo}, Tier={normalized_tier}")

    if not normalized_hmo or not normalized_tier:
        print("⚠️ WARNING: Missing HMO or insurance tier information")
        return "מצטער, אני צריך את פרטי קופת החולים ודרגת הביטוח שלך כדי לתת לך מידע מדויק."

    relevant_chunks = find_similar_chunks(user_message, top_k=5)
    if not relevant_chunks or all(len(chunk.strip()) < 50 for chunk in relevant_chunks):
        key_terms = extract_key_terms(user_message)
        for term in key_terms:
            relevant_chunks.extend(find_similar_chunks(term, top_k=2))
        relevant_chunks = list(dict.fromkeys(relevant_chunks))[:5]

    transformed_chunks = []
    for chunk in relevant_chunks:
        if chunk.strip():
            transformed = transform_chunk(chunk.strip())
            if transformed:
                transformed_chunks.append(transformed)
    
    if not transformed_chunks:
        return "אני מצטער, לא הצלחתי למצוא מידע הקשור לשאלתך."
    
    context = "\n\n".join([f"• {c}" for c in transformed_chunks])

    user_info_text = "\n".join([f"{k}: {v}" for k, v in user_info.items() if v])

    qa_prompt = qa_prompt_template.format(
        user_info_text=user_info_text,
        context=context,
        user_message=user_message
    )
    
    print("\n📤 QA PROMPT:")
    print(qa_prompt)
    print("\n" + "="*50)

    return ask_gpt([
        {"role": "system", "content": "You are a helpful assistant. Answer only based on provided context."},
        {"role": "user", "content": qa_prompt}
    ], max_tokens=1000, temperature=0.1)



def all_info_collected(chat_history: List[Dict[str, str]]) -> bool:
    for i in range(len(chat_history) - 1, -1, -1):
        message = chat_history[i]
        if message.get("role") == "assistant" and (
            "האם הפרטים נכונים" in message.get("content", "") or
            "are these details correct" in message.get("content", "").lower()
        ):
            if i + 1 < len(chat_history):
                reply = chat_history[i + 1].get("content", "").strip().lower()
                return reply in ["כן", "yes", "נכון", "correct"]
            break
    return False


def extract_user_info(chat_history: List[Dict[str, str]]) -> Dict[str, str]:
    """
    מחלץ את פרטי המשתמש מההיסטוריה של השיחה
    """
    print("\n🔍 Starting user info extraction...")
    
    try:
        user_info = extract_user_info_with_ai(chat_history)
        if user_info and len(user_info) > 3:  
            print(f"✅ AI extraction successful: {user_info}")
            return user_info
        
        print("⚠️ AI extraction failed or incomplete, trying manual extraction...")
        
        manual_info = {}
        
        for i in range(len(chat_history) - 1):
            if chat_history[i].get("role") == "assistant" and chat_history[i+1].get("role") == "user":
                question = chat_history[i].get("content", "").lower()
                answer = chat_history[i+1].get("content", "").strip()
                
                print(f"🔍 Analyzing: Q='{question[:50]}...' A='{answer}'")
                
                if "שם הפרטי" in question or "first name" in question:
                    parts = answer.split()
                    if len(parts) >= 2:
                        manual_info["first_name"] = parts[0]
                        manual_info["last_name"] = " ".join(parts[1:])
                        print(f"✅ Found names: {parts[0]} {' '.join(parts[1:])}")
                    else:
                        manual_info["first_name"] = answer
                        print(f"✅ Found first name: {answer}")
                
                elif "שם המשפחה" in question or "last name" in question:
                    manual_info["last_name"] = answer
                    print(f"✅ Found last name: {answer}")
                
                elif "תעודת זהות" in question or "id number" in question:
                    if answer.isdigit() and len(answer) == 9:
                        manual_info["id_number"] = answer
                        print(f"✅ Found ID: {answer}")
                
                elif "מגדר" in question or "gender" in question:
                    clean_gender = answer.lower().rstrip('הה')  # מסיר 'הה' בסוף
                    if clean_gender in ["זכר", "נקבה", "male", "female"]:
                        manual_info["gender"] = clean_gender
                        print(f"✅ Found gender: {clean_gender}")
                
                elif "גיל" in question or "age" in question:
                    if answer.isdigit() and 0 <= int(answer) <= 120:
                        manual_info["age"] = answer
                        print(f"✅ Found age: {answer}")
                
                elif "קופת חולים" in question or "hmo" in question or "באיזו קופ" in question:
                    clean_hmo = answer.lower().rstrip('י')
                    if clean_hmo in ["מכבי", "מאוחדת", "כללית", "maccabi", "meuhedet", "clalit"]:
                        manual_info["hmo"] = clean_hmo
                        print(f"✅ Found HMO: {clean_hmo}")
                
                elif "כרטיס" in question or "card" in question:
                    if answer.isdigit() and len(answer) == 9:
                        manual_info["hmo_card"] = answer
                        print(f"✅ Found card: {answer}")
                
                elif ("מסלול" in question or "דרגת ביטוח" in question or 
                      "insurance tier" in question or "ביטוח" in question or "מהו מסלול" in question):
                    if answer.lower() in ["זהב", "כסף", "ארד", "gold", "silver", "bronze"]:
                        manual_info["insurance_tier"] = answer.lower()
                        print(f"✅ Found insurance tier: {answer.lower()}")
        
        print(f"📋 Manual extraction result: {manual_info}")
        return manual_info
        
    except Exception as e:
        print(f"❌ Error in extract_user_info: {e}")
        return {}

def get_answer(user_message: str, chat_history: List[Dict[str, str]] = []) -> Dict:
    try:
        if all_info_collected(chat_history):
            user_info = extract_user_info(chat_history)
            if not is_medical_related_ai(user_message, chat_history):
                redirect_prompt = redirect_prompt_template.format(user_message=user_message)
                bot_reply = ask_gpt([
                    {"role": "system", "content": "You are a helpful healthcare assistant."},
                    {"role": "user", "content": redirect_prompt}
                ], max_tokens=500, temperature=0.3)
            else:
                bot_reply = enhanced_search_and_answer(user_message, user_info)
            updated_history = chat_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": bot_reply}
            ]
            return {"answer": bot_reply, "chat_history": updated_history}
        else:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(chat_history)
            messages.append({"role": "user", "content": user_message})
            bot_reply = ask_gpt(messages)
            updated_history = chat_history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": bot_reply}
            ]
            return {"answer": bot_reply, "chat_history": updated_history}
    except Exception as e:
        return {"answer": f"שגיאה בשליחת הבקשה למודל: {e}", "chat_history": chat_history}