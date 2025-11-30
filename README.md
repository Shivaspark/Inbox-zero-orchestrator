# 📧 Inbox Zero Orchestrator (Live Version)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io/)
![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Status](https://img.shields.io/badge/Status-Live_Prototype-green)

**An autonomous AI Agent that connects to your real Gmail inbox to triage, draft, and declutter automatically.**

The **Inbox Zero Orchestrator** is a local "Human-in-the-Loop" AI agent powered by **Google Gemini 2.0 Flash** and the **Google Agent Development Kit (ADK)**. It reads your unread emails, intelligently classifies them (Urgent, FYI, Spam, Follow-up), and executes real API actions—like drafting replies or archiving newsletters—to help you achieve Inbox Zero.

---

## 🚀 Features

* **Real-Time Gmail Sync:** Fetches unread emails directly from your live inbox using the Gmail API.
* **Intelligent Triage:** Uses Gemini 2.0 Flash to "read" and understand the intent of every email.
* **Autonomous Actions:**
    * **📝 Auto-Draft:** Pre-writes context-aware replies for urgent emails (saved to Drafts).
    * **📦 Auto-Archive:** Identifies "FYI" or newsletter emails and archives them to clear clutter.
    * **🗑️ Auto-Delete:** Detects spam and moves it to the trash.
    * **⏰ Task Extraction:** Identifies follow-up tasks and sets reminders.
* **"Glass Box" UI:** Built with **Streamlit**, showing the agent's real-time thought process, tool execution, and decision-making.

---

## 🛠️ Tech Stack

* **AI Model:** Google Gemini 2.0 Flash (`gemini-2.5-flash-lite`)
* **Framework:** [Google Agent Development Kit (ADK)](https://github.com/google/generative-ai-python)
* **Interface:** Streamlit
* **APIs:** Google Gmail API (OAuth 2.0)
* **Language:** Python 3.10+

---

## 📋 Prerequisites

Before running this project, ensure you have:

1.  **Python 3.10 or higher** installed.
2.  A **Google Cloud Project** with the Gmail API enabled.
3.  A **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/).

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/inbox-zero-orchestrator.git](https://github.com/your-username/inbox-zero-orchestrator.git)
cd inbox-zero-orchestrator
```
### 2. Install Dependencies
Create a virtual environment and install the required packages:

```
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate

# Install libraries
pip install streamlit google-adk google-generativeai google-auth google-auth-oauthlib google-api-python-client beautifulsoup4 python-dotenv nest_asyncio

```
### 3. Configure Credentials
A. Gemini API Key
Create a file named .env in the root folder and add your key:
```
GOOGLE_API_KEY=your_actual_api_key_here
```

B. Gmail OAuth Credentials
Go to the Google Cloud Console.

Create a project -> Enable "Gmail API".

Go to Credentials -> Create Credentials -> OAuth Client ID (Desktop App).

Download the JSON file, rename it to credentials.json, and place it in the root folder.

Important: In the "OAuth Consent Screen" settings, add your email as a Test User.

##🏃‍♂️ Usage
Run the Streamlit application locally:

```bash
streamlit run app.py

```
1. A browser window will open.

2. On the first run, it will ask you to Sign In with Google.

(Note: Since the app is unverified, you may see a warning. Click "Advanced" -> "Go to Project (Unsafe)" to proceed.)

3. Grant the requested permissions (Read, Compose, Modify labels).

4. Once authenticated, click "Refresh Inbox" in the sidebar.

5. Select an email and click "⚡ Process with AI Agent" to see it work!

```
inbox-zero-orchestrator/
├── app.py                # Main application logic (Streamlit + Agent)
├── credentials.json      # OAuth 2.0 Client ID (You must provide this)
├── .env                  # Environment variables (API Key)
├── token.json            # Auto-generated user auth token (Git-ignored)
├── requirements.txt      # List of dependencies
└── README.md             # Project documentation
```
##⚠️ Troubleshooting

RefreshError: invalid_grant

This means your auth token has expired (common for testing apps every 7 days).

Fix: Delete the token.json file and restart the app to re-login.

403 Access Denied

Ensure your email address is added as a Test User in the Google Cloud Console "OAuth Consent Screen" section.

##🔮 Future Roadmap

1. Chrome Extension: Porting this logic to a browser extension for client-side, decentralized privacy.

2. RAG Integration: Connecting to a local vector store to let the agent search past emails for context.

3. Calendar Agent: Adding a second agent to cross-reference availability for meeting requests.


video link : (https://youtu.be/YnSNAeKJBTM)





