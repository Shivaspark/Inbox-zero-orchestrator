import streamlit as st
import asyncio
import nest_asyncio
import os.path
import base64
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Google & Gmail Libraries
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ADK Libraries
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner

# Apply asyncio patch for Streamlit and load env vars
nest_asyncio.apply()
load_dotenv()

# ==========================================
# 1. GMAIL AUTH & HELPER FUNCTIONS
# ==========================================
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

@st.cache_resource
def get_gmail_service():
    """Connects to Gmail API. Cached so it doesn't reload on every rerun."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # THIS OPENS A BROWSER WINDOW ON YOUR LOCAL MACHINE FOR AUTH
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

# Initialize service globally once
service = get_gmail_service()

# Global variable to store the ID of the email currently being processed
# It's set to None initially and updated in the Streamlit UI.
CURRENT_EMAIL_ID = None 

def fetch_inbox(max_results=10):
    """Fetches the latest unread emails from the Inbox."""
    try:
        results = service.users().messages().list(
            userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        email_list = []
        for msg in messages:
            msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
            headers = msg_detail['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(No Subject)")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "(Unknown)")
            email_list.append({'id': msg['id'], 'subject': subject, 'sender': sender})
        return email_list
    except Exception as e:
        st.error(f"Error fetching inbox: {e}")
        return []

def get_email_body(msg_id):
    """Retrieves and cleans the body of a specific email."""
    try:
        msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = msg['payload']
        parts = payload.get('parts')
        data = None
        
        if parts:
            # Look for text/plain first, then text/html
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    break
            if not data: # If no plain text, try HTML
                 for part in parts:
                    if part['mimeType'] == 'text/html':
                        data = part['body']['data']
                        break
        else: # Fallback for simple emails without parts
            data = payload['body']['data']

        if data:
            text = base64.urlsafe_b64decode(data).decode()
            # Clean up HTML if necessary to provide agent clean text
            soup = BeautifulSoup(text, "html.parser")
            return soup.get_text(separator='\n').strip()
    except Exception as e:
        return f"Error reading email body: {e}"
    return "(No readable content found)"


# ==========================================
# 2. DEFINE REAL TOOLS
# ==========================================

# NOTE: Tools that operate on a specific email now take 'email_id' as an explicit argument.
# This makes their usage clearer and avoids reliance on a global variable INSIDE the function.

def draft_email(recipient: str, subject: str, body: str) -> dict:
    """REAL: Drafts a reply email in your Gmail account."""
    try:
        from email.message import EmailMessage
        message = EmailMessage()
        message.set_content(body)
        message['To'] = recipient
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        draft = service.users().drafts().create(userId="me", body={'message': create_message}).execute()
        return {"status": "success", "message": f"✅ Real draft created! ID: {draft['id']}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def archive_email_by_id(email_id: str) -> dict:
    """REAL: Archives a specific email by removing the INBOX label."""
    if not email_id: return {"status": "error", "message": "Email ID not provided for archiving."}
    try:
        service.users().messages().modify(
            userId='me', id=email_id, body={'removeLabelIds': ['INBOX']}).execute()
        return {"status": "success", "message": f"📦 Email {email_id} has been really archived."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def delete_email_by_id(email_id: str) -> dict:
    """REAL: Moves a specific email to Trash."""
    if not email_id: return {"status": "error", "message": "Email ID not provided for deleting."}
    try:
        service.users().messages().modify(
            userId='me', id=email_id, body={'addLabelIds': ['TRASH']}).execute()
        return {"status": "success", "message": f"🗑️ Email {email_id} moved to trash."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def create_reminder(task: str, date: str) -> dict:
    """Creates a reminder (Mocked for simplicity)."""
    # In a real app, you would connect to Google Tasks API or a calendar.
    return {"status": "success", "message": f"⏰ Reminder set: {task} on {date}"}

# List of tools available to the agent
REAL_TOOLS = [draft_email, archive_email_by_id, delete_email_by_id, create_reminder]

# ==========================================
# 3. AGENT SETUP
# ==========================================

ORCHESTRATOR_INSTRUCTION = """
You are the 'Inbox Zero Orchestrator'. Your goal is to help the user clear their inbox.
You will receive the full content of an email.

Follow these steps for each email:
1.  **Analyze and Classify:** Categorize the email into one of these types:
    -   'URGENT': Requires an immediate reply.
    -   'FYI': Informational, no reply needed, can be archived.
    -   'FOLLOW_UP': Requires a future action or reminder.
    -   'JUNK': Unwanted, spam, or promotional.
2.  **Determine Action(s):** Based on the classification, select one or more appropriate tools.
    -   For 'JUNK': Use `delete_email_by_id(email_id=...)`.
    -   For 'FYI': Use `archive_email_by_id(email_id=...)`.
    -   For 'URGENT': Use `draft_email(recipient=..., subject=..., body=...)`.
    -   For 'FOLLOW_UP': Use `create_reminder(task=..., date=...)` (and optionally `draft_email`).
    **IMPORTANT**: When calling `archive_email_by_id` or `delete_email_by_id`, you MUST pass the `email_id` parameter, which will be provided to you in the prompt.
3.  **Generate Final Report:** After executing your reasoning and tool actions, you MUST produce a concise, single-paragraph FINAL conversational message for the user. This message MUST:
    -   **Start** by stating the email's classification (e.g., "I've classified this email as URGENT.").
    -   **Summarize** the specific actions you have taken (e.g., "I have drafted a reply to the sender and archived the original email.").
    -   Ensure this is the LAST message you send.
"""

# Initialize Agent once and store in session state to avoid re-creating on every rerun
if "runner" not in st.session_state:
    agent = Agent(
        name="Inbox_Zero_Real",
        model=Gemini(model="gemini-2.5-flash-lite"), # Using flash for speed
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=REAL_TOOLS,
    )
    st.session_state.runner = InMemoryRunner(agent=agent)

# ==========================================
# 4. THE STREAMLIT UI
# ==========================================

st.set_page_config(page_title="Live Inbox Zero Agent", page_icon="📨", layout="wide")

# Initialize session state variables for the UI
if 'emails' not in st.session_state:
    st.session_state.emails = []
if 'selected_email_index' not in st.session_state:
    st.session_state.selected_email_index = 0

# --- SIDEBAR FOR INBOX CONTROLS ---
with st.sidebar:
    st.title("📨 Inbox Controls")
    if st.button("🔄 Refresh Inbox (Unread)"):
        with st.spinner("Fetching emails..."):
            st.session_state.emails = fetch_inbox()
            st.session_state.selected_email_index = 0 # Reset selection on refresh
            st.success(f"Found {len(st.session_state.emails)} unread emails.")
    
    st.divider()
    
    if st.session_state.emails:
        # Create a list of subject lines for the radio button display
        email_options = [f"{i+1}. {e['sender'].split('<')[0].strip()} - {e['subject'][:30]}..." for i, e in enumerate(st.session_state.emails)]
        selected_option = st.radio("Select an Email to Process:", email_options, index=st.session_state.selected_email_index)
        # Find the actual index based on the selected string to update state
        st.session_state.selected_email_index = email_options.index(selected_option)
    else:
        st.info("Inbox is empty or not fetched yet. Click 'Refresh Inbox'.")

# --- MAIN AREA FOR EMAIL DISPLAY AND AGENT ACTIONS ---
st.title("🤖 Real-Time Inbox Zero Agent")

# Only display content if emails are fetched and an email is selected
if st.session_state.emails and len(st.session_state.emails) > st.session_state.selected_email_index:
    current_email_data = st.session_state.emails[st.session_state.selected_email_index]
    
    current_email_data = st.session_state.emails[st.session_state.selected_email_index]
    
    # Update the module-level CURRENT_EMAIL_ID with the ID of the currently selected email.
    # No 'global' keyword needed here as we are assigning in the module's top-level scope.
    CURRENT_EMAIL_ID = current_email_data['id']
    
    # Display the selected email's details
    with st.container(border=True):
        st.subheader(f"Subject: {current_email_data['subject']}")
        st.caption(f"From: {current_email_data['sender']}")
        
        with st.spinner("Loading email body..."):
            email_body_text = get_email_body(CURRENT_EMAIL_ID)
        
        st.text_area("Email Content", value=email_body_text, height=250, disabled=True)

    st.divider()

    # ... (previous code) ...

# Button to trigger the AI Agent
    if st.button("⚡ Process with AI Agent & Take Real Action", type="primary"):
        # Construct the full prompt for the agent, including the email ID as a hint
        full_prompt = (
            f"Subject: {current_email_data['subject']}\n"
            f"From: {current_email_data['sender']}\n"
            f"Body:\n{email_body_text}\n\n"
            f"The ID of this email is: {CURRENT_EMAIL_ID}. Use this ID when calling archive_email_by_id or delete_email_by_id tools."
        )
        
        # This will hold the first agent message we successfully extract
        first_agent_dialogue = "" 
        
        with st.status("Agent is working on your real inbox...", expanded=True) as status:
            st.write("🧠 Analyzing content and deciding actions...")
            
            # Asynchronously run the agent
            async def run_agent_task():
                return await st.session_state.runner.run_debug(full_prompt)
            
            response_events = asyncio.run(run_agent_task())
            
            action_taken = False # Flag to track if any tool was called
            
            # --- FINALIZED DIRECT CAPTURE & TOOL CALL DISPLAY ---
            # Use a list to store all potential agent messages, then pick the first valid one.
            potential_agent_messages = []

            for event in response_events:
                # Display tool calls inside the status expander
                if hasattr(event, 'tool_calls') and event.tool_calls:
                    for tool_call in event.tool_calls:
                        st.write(f"🛠️ **Executing Real Tool:** `{tool_call.name}` with args: `{tool_call.args}`")
                        action_taken = True
                
                # Check if the event has a 'message' attribute and if that message has 'text'
                if hasattr(event, 'message') and event.message and hasattr(event.message, 'text'):
                    message_text = event.message.text
                    # The agent's actual conversational output usually contains its name
                    # (e.g., "Inbox_Zero_Real > I've classified...")
                    # We'll consider any non-empty message with text as a potential candidate.
                    if message_text.strip(): # Ensure it's not just whitespace
                        potential_agent_messages.append(message_text.strip())
            
            # After iterating through all events, find the *first* message that looks like agent output.
            # We're looking for something that's not just a tool-related message.
            for msg in potential_agent_messages:
                # The agent's direct dialogue often starts with its name or is a clear sentence.
                # Let's take the first non-empty, non-tool-response message.
                # This logic is more robust than relying on 'is_final_response' directly.
                if not msg.startswith("tool_code:") and not msg.startswith("print(") and msg.strip():
                    first_agent_dialogue = msg
                    break # Stop at the first good one

            # --- END FINALIZED DIRECT CAPTURE ---

            # Update the status message and state based on agent's activity
            if action_taken:
                status.update(label="✅ Real Actions Executed!", state="complete", expanded=False)
                # Force a rerun to refresh the inbox list if an action was taken
                st.session_state.emails = fetch_inbox()
                st.session_state.selected_email_index = 0 # Reset selection after action
                st.experimental_rerun() 
            else:
                status.update(label="Finished analyzing. No actions taken.", state="complete", expanded=False)

        # Display the agent's final report outside the status expander
        st.subheader("Agent Final Report")
        if first_agent_dialogue:
            st.success(first_agent_dialogue) # Using st.success for better visibility if it's the main point
        else:
            st.info("Look at the terminal for the output")
