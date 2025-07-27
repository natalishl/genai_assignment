import streamlit as st
import requests
import json
from typing import List, Dict

# Configuration
API_URL = "http://localhost:8000"  # Change this to your FastAPI server URL

# Page configuration
st.set_page_config(
    page_title="בוט רפואי",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for RTL and improved chat styling
st.markdown("""
<style>
    /* Hide Streamlit header and footer */
    header[data-testid="stHeader"] {
        height: 0px;
        background: transparent;
    }
    
    .stAppViewContainer > .main {
        padding-top: 0rem;
    }
    
    /* Main container */
    .main > div {
        direction: rtl;
        text-align: right;
        max-width: 100%;
    }
    
    /* Chat container styling */
    .stChatMessage {
        direction: rtl;
        text-align: right;
        margin-bottom: 1rem;
    }
    
    .stChatInputContainer {
        direction: rtl;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 1rem;
        border-top: 1px solid #e0e0e0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        z-index: 999;
    }
    
    .stTextInput > div > div > input {
        direction: rtl;
        text-align: right;
        border-radius: 25px;
        border: 2px solid #4CAF50;
        padding: 12px 20px;
        font-size: 16px;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #45a049;
        box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
    }
    
    /* Chat header */
    .chat-header {
        background: linear-gradient(135deg, #4CAF50, #45a049);
        color: white;
        padding: 15px 20px;
        text-align: center;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 998;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    /* Chat messages area */
    .chat-container {
        margin-top: 80px;
        margin-bottom: 120px;
        padding: 0 20px;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* Message bubbles */
    .stChatMessage[data-testid="chat-message-user"] {
        background: #e3f2fd;
        border-radius: 18px 18px 5px 18px;
        padding: 12px 18px;
        margin-right: 60px;
        margin-left: 10px;
    }
    
    .stChatMessage[data-testid="chat-message-assistant"] {
        background: #f5f5f5;
        border-radius: 18px 18px 18px 5px;
        padding: 12px 18px;
        margin-left: 60px;
        margin-right: 10px;
    }
    
    /* Welcome section */
    .welcome-section {
        text-align: center;
        padding: 40px 20px;
        background: linear-gradient(135deg, #f8f9ff, #e8f5e8);
        border-radius: 20px;
        margin: 20px;
        border: 1px solid #e0e0e0;
    }
    
    .service-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 15px;
        margin: 30px 0;
        padding: 0 20px;
    }
    
    .service-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
        transition: transform 0.2s, box-shadow 0.2s;
        cursor: pointer;
    }
    
    .service-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.15);
    }
    
    .service-icon {
        font-size: 2.5rem;
        margin-bottom: 10px;
    }
    
    .service-title {
        font-size: 1rem;
        font-weight: bold;
        color: #2c3e50;
    }
    
    /* Typing indicator */
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #666;
        font-style: italic;
        margin: 10px 0;
    }
    
    .typing-dots {
        display: flex;
        gap: 3px;
    }
    
    .typing-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #4CAF50;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
        40% { transform: scale(1); opacity: 1; }
    }
    
    /* Error message */
    .error-message {
        background-color: #fdf2f2;
        color: #e74c3c;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e74c3c;
        margin: 10px 0;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .chat-container {
            padding: 0 10px;
        }
        
        .stChatMessage[data-testid="chat-message-user"] {
            margin-right: 30px;
        }
        
        .stChatMessage[data-testid="chat-message-assistant"] {
            margin-left: 30px;
        }
        
        .service-grid {
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "היי! 👋 אני הבוט הרפואי שלך. איך אוכל לעזור לך היום? אתה יכול לשאול אותי על נושאי בריאות, שירותי בריאות בישראל, או כל דבר רפואי אחר."}
        ]
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

def call_api(question: str, chat_history: List[Dict[str, str]]) -> Dict:
    """Call the FastAPI backend"""
    try:
        response = requests.post(
            f"{API_URL}/ask",
            json={
                "question": question,
                "chat_history": chat_history
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "answer": f"מצטער, נתקלתי בבעיה טכנית (שגיאת שרת: {response.status_code}). אנא נסה שוב.",
                "chat_history": chat_history,
                "error": f"HTTP {response.status_code}"
            }
    except requests.exceptions.RequestException as e:
        return {
            "answer": "מצטער, לא ניתן להתחבר לשרת כרגע. אנא בדוק את החיבור לאינטרנט ונסה שוב מאוחר יותר.",
            "chat_history": chat_history,
            "error": str(e)
        }

def display_welcome_section():
    """Display welcome section with services"""
    st.markdown("""
    <div class="welcome-section">
        <h1>🏥 ברוכים הבאים לבוט הרפואי החכם</h1>
        <p style="font-size: 1.2rem; margin: 20px 0;">אני כאן לעזור לך עם שאלות בנושא בריאות ושירותי בריאות בישראל</p>
        <p style="color: #666;">בחר נושא או פשוט התחל לכתוב את השאלה שלך:</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Services grid
    st.markdown("""
    <div class="service-grid">
        <div class="service-card" onclick="document.querySelector('.stTextInput input').value='ספר לי על רפואה משלימה'; document.querySelector('.stTextInput input').focus();">
            <div class="service-icon">🌿</div>
            <div class="service-title">רפואה משלימה</div>
        </div>
        <div class="service-card" onclick="document.querySelector('.stTextInput input').value='מה זה מרפאות תקשורת?'; document.querySelector('.stTextInput input').focus();">
            <div class="service-icon">💬</div>
            <div class="service-title">מרפאות תקשורת</div>
        </div>
        <div class="service-card" onclick="document.querySelector('.stTextInput input').value='איך למצוא מרפאת שיניים?'; document.querySelector('.stTextInput input').focus();">
            <div class="service-icon">🦷</div>
            <div class="service-title">מרפאות שיניים</div>
        </div>
        <div class="service-card" onclick="document.querySelector('.stTextInput input').value='מה זה בדיקת אופטומטריה?'; document.querySelector('.stTextInput input').focus();">
            <div class="service-icon">👁️</div>
            <div class="service-title">אופטומטריה</div>
        </div>
        <div class="service-card" onclick="document.querySelector('.stTextInput input').value='ספר לי על שירותי הריון'; document.querySelector('.stTextInput input').focus();">
            <div class="service-icon">🤱</div>
            <div class="service-title">שירותי הריון</div>
        </div>
        <div class="service-card" onclick="document.querySelector('.stTextInput input').value='אילו סדנאות בריאות יש?'; document.querySelector('.stTextInput input').focus();">
            <div class="service-icon">🎓</div>
            <div class="service-title">סדנאות בריאות</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main application function"""
    initialize_session_state()
    
    # Fixed header
    st.markdown("""
    <div class="chat-header">
        <h2 style="margin: 0; font-size: 1.5rem;">🏥 בוט רפואי חכם</h2>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">יועץ בריאות מקצועי</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check API connection
    api_connected = True
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=5)
        if health_response.status_code != 200:
            api_connected = False
    except requests.exceptions.RequestException:
        api_connected = False
    
    if not api_connected:
        st.markdown("""
        <div class="error-message">
            ⚠️ לא ניתן להתחבר לשרת הAPI כרגע. הבוט עובד במצב הדגמה.
        </div>
        """, unsafe_allow_html=True)
    
    # Chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Welcome section (show only if no user messages)
    user_messages = [msg for msg in st.session_state.messages if msg["role"] == "user"]
    if len(user_messages) == 0:
        display_welcome_section()
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input (fixed at bottom)
    if prompt := st.chat_input("כתוב את השאלה שלך כאן... 💬"):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Show typing indicator
        with st.chat_message("assistant"):
            with st.spinner("🤔 חושב על התשובה..."):
                if api_connected:
                    response = call_api(prompt, st.session_state.chat_history)
                    
                    if response.get("error"):
                        answer = "מצטער, נתקלתי בבעיה טכנית. אנא נסה שוב או נסח את השאלה באופן שונה."
                    else:
                        answer = response["answer"]
                        st.session_state.chat_history = response["chat_history"]
                else:
                    # Demo response when API is not connected
                    answer = f"זו תגובה לדוגמה לשאלתך: '{prompt}'. כרגע הבוט עובד במצב הדגמה מכיוון שהAPI לא זמין."
                
                # Update session state
                st.session_state.messages.append({"role": "assistant", "content": answer})
        
        # Refresh to show new messages
        st.rerun()

    # Sidebar with additional options
    with st.sidebar:
        st.markdown("### ⚙️ הגדרות")
        
        if st.button("🗑️ נקה את השיחה", use_container_width=True):
            st.session_state.messages = [
                {"role": "assistant", "content": "היי! 👋 אני הבוט הרפואי שלך. איך אוכל לעזור לך היום?"}
            ]
            st.session_state.chat_history = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 סטטיסטיקות")
        user_msgs = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
        bot_msgs = len([msg for msg in st.session_state.messages if msg["role"] == "assistant"])
        st.metric("הודעות שלך", user_msgs)
        st.metric("תגובות הבוט", bot_msgs - 1)  # -1 for initial greeting
        
  
        
        # API Status
        st.markdown("### 🔗 סטטוס חיבור")
        try:
            health_response = requests.get(f"{API_URL}/health", timeout=2)
            if health_response.status_code == 200:
                st.success("✅ API מחובר ופעיל")
            else:
                st.error("❌ שגיאה בחיבור לAPI")
        except:
            st.error("❌ API לא זמין")
        
        st.markdown("---")
        st.markdown("### 💡 טיפים")
        st.info("• נסח שאלות ברורות וספציפיות\n• אתה יכול לשאול על תרופות, תסמינים, בדיקות ועוד\n• הבוט לא מחליף יעוץ רפואי מקצועי")

if __name__ == "__main__":
    main()