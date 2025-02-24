import streamlit as st
import openai
import pandas as pd
import json
import os
from datetime import datetime

# Initialize OpenAI client
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Load configuration data
def load_sig_structure():
    """Load the SIG form structure from a JSON file"""
    with open('sig_structure.json', 'r') as file:
        return json.load(file)

def load_instructions():
    """Load AI instructions from file"""
    with open('prompt.txt', 'r') as file:
        return file.read()

# Initialize SIG structure as a global variable 
# (in production, this would be loaded from the JSON file)
SIG_STRUCTURE = {
    "Location Hierarchy": {
        "description": "Outlines the geographical service territory represented by a 4-level location hierarchy within ARCOS.",
        "sections": [
            {
                "name": "Location Names",
                "description": "Names must contain a blank space per 25 contiguous characters and have a maximum length of 50 characters.",
                "questions": [
                    "What naming convention would you like to use for your locations?",
                    "Do you have any existing location names that need to be preserved?"
                ]
            },
            {
                "name": "Location Codes",
                "description": "Each Level 4 entry must have a unique accompanying Location Code.",
                "questions": [
                    "Will you use existing location codes from your HR system?",
                    "If creating new codes, what format would you prefer?"
                ]
            },
            {
                "name": "Time Zones",
                "description": "Specify time zones for each location or set a global default.",
                "questions": [
                    "Does your company span multiple time zones?",
                    "If yes, which time zones are represented in your service territory?"
                ]
            },
            {
                "name": "Location Access and Security",
                "description": "Define who has access to which location information.",
                "questions": [
                    "Who needs access to each location's information?",
                    "Are there specific security requirements for location data?"
                ]
            }
        ]
    },
    # Additional tabs would be defined here...
    "Matrix of Locations and CO Types": {
        "description": "Defines the specific Callout Types available within a given location in ARCOS.",
        "sections": [
            {
                "name": "Location Hierarchy",
                "description": "Review the 4-level location hierarchy established in the previous tab.",
                "questions": [
                    "Have you finalized your location hierarchy structure?",
                    "Are there any changes needed before proceeding?"
                ]
            },
            {
                "name": "Callout Types",
                "description": "Define the different Callout Types that can be assigned to each location.",
                "questions": [
                    "Which standard callout types will you need?",
                    "Do you require any custom callout types?"
                ]
            },
            {
                "name": "Matrix Configuration",
                "description": "Indicate which Callout Types are available for each location.",
                "questions": [
                    "Should all locations have access to all callout types?",
                    "Are there specific callout types that should be restricted to certain locations?"
                ]
            }
        ]
    }
    # More tabs would be defined here...
}

def get_openai_response(messages):
    """Get response from OpenAI API"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except openai.APIError as e:
        return f"Error: {e}"

def display_chat_history():
    """Display the visible conversation history"""
    for message in st.session_state.visible_messages:
        if message["role"] == "user":
            st.write("👤 You:", message["content"])
        elif message["role"] == "assistant":
            st.write("🤖 Assistant:", message["content"])

def initialize_session():
    """Initialize all session state variables"""
    st.session_state.initialized = True
    st.session_state.responses = {}
    st.session_state.chat_history = []
    st.session_state.visible_messages = []
    
    # Tab and section navigation
    st.session_state.current_tab_index = 0
    st.session_state.current_section_index = 0
    st.session_state.current_question_index = 0
    
    # SIG structure
    st.session_state.sig_structure = SIG_STRUCTURE
    
    # Load AI instructions
    instructions = load_instructions()
    st.session_state.chat_history = [{"role": "system", "content": instructions}]
    
    # Add initial greeting
    welcome_message = "Hello! I'm your ARCOS System Implementation Guide assistant. I'll help you complete the configuration forms by providing context and explaining the options available. If you're unsure about any question, simply ask for more information or type a ? and I'll provide a detailed explanation. Let's get started with the Location Hierarchy tab."
    
    st.session_state.chat_history.append({"role": "assistant", "content": welcome_message})
    st.session_state.visible_messages.append({"role": "assistant", "content": welcome_message})

def get_current_tab_and_section():
    """Get the current tab and section details"""
    tabs = list(st.session_state.sig_structure.keys())
    current_tab_name = tabs[st.session_state.current_tab_index]
    current_tab = st.session_state.sig_structure[current_tab_name]
    
    current_section = current_tab["sections"][st.session_state.current_section_index]
    
    return current_tab_name, current_tab, current_section

def provide_contextual_help():
    """Provide contextual help for the current section"""
    tab_name, _, section = get_current_tab_and_section()
    
    help_messages = st.session_state.chat_history.copy()
    help_query = f"Can you explain in detail what information is needed for the '{section['name']}' section in the '{tab_name}' tab? Please include examples and best practices."
    
    help_messages.append({"role": "user", "content": help_query})
    help_response = get_openai_response(help_messages)
    
    # Add help interaction to chat history
    st.session_state.chat_history.append({"role": "user", "content": "I need help with this section"})
    st.session_state.chat_history.append({"role": "assistant", "content": help_response})
    
    st.session_state.visible_messages.extend([
        {"role": "user", "content": "I need help with this section"},
        {"role": "assistant", "content": help_response}
    ])

def process_user_input(user_input):
    """Process user input and get AI response"""
    tab_name, _, section = get_current_tab_and_section()
    
    # Store response if answering a question
    response_key = f"{tab_name}_{section['name']}"
    if response_key not in st.session_state.responses:
        st.session_state.responses[response_key] = []
    
    st.session_state.responses[response_key].append(user_input)
    
    # Add user input to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.session_state.visible_messages.append({"role": "user", "content": user_input})
    
    # Generate context for AI response
    context = f"The user is currently in the '{tab_name}' tab, '{section['name']}' section. "
    context += f"Description: {section['description']}. "
    
    if 'questions' in section:
        context += f"Current question: {section['questions'][st.session_state.current_question_index]}. "
    
    # Get AI response
    ai_messages = st.session_state.chat_history.copy()
    ai_messages.append({"role": "system", "content": context})
    
    ai_response = get_openai_response(ai_messages)
    
    # Add AI response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
    st.session_state.visible_messages.append({"role": "assistant", "content": ai_response})
    
    # Check if we should advance to the next question
    if 'questions' in section:
        if st.session_state.current_question_index < len(section['questions']) - 1:
            st.session_state.current_question_index += 1

def calculate_progress():
    """Calculate overall progress through the form"""
    total_sections = sum(len(tab["sections"]) for tab in st.session_state.sig_structure.values())
    
    # Count completed sections (those with at least one response)
    completed_sections = 0
    for tab_name, tab in st.session_state.sig_structure.items():
        for section in tab["sections"]:
            response_key = f"{tab_name}_{section['name']}"
            if response_key in st.session_state.responses and st.session_state.responses[response_key]:
                completed_sections += 1
    
    return completed_sections / total_sections if total_sections > 0 else 0

def export_configuration():
    """Export the completed configuration as a CSV file"""
    data = []
    
    for tab_name, tab in st.session_state.sig_structure.items():
        for section in tab["sections"]:
            response_key = f"{tab_name}_{section['name']}"
            responses = st.session_state.responses.get(response_key, [])
            
            # Join multiple responses with a separator
            response_text = " | ".join(responses) if responses else "Not provided"
            
            data.append({
                "Tab": tab_name,
                "Section": section["name"],
                "Description": section["description"],
                "Response": response_text
            })
    
    # Create DataFrame and download as CSV
    df = pd.DataFrame(data)
    
    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    csv_data = df.to_csv(index=False).encode('utf-8')
    
    return csv_data, f"arcos_configuration_{timestamp}.csv"

def main():
    st.title("ARCOS System Implementation Guide Bot")
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        initialize_session()
    
    # Sidebar for navigation between tabs
    tab_names = list(st.session_state.sig_structure.keys())
    selected_tab = st.sidebar.selectbox(
        "Select SIG Tab", 
        tab_names,
        index=st.session_state.current_tab_index
    )
    
    # Update current tab if changed
    if tab_names[st.session_state.current_tab_index] != selected_tab:
        st.session_state.current_tab_index = tab_names.index(selected_tab)
        st.session_state.current_section_index = 0
        st.session_state.current_question_index = 0
    
    # Get current tab and section
    tab_name, current_tab, current_section = get_current_tab_and_section()
    
    # Display current tab information
    st.header(tab_name)
    st.write(current_tab["description"])
    
    # Display chat history
    with st.container():
        display_chat_history()
    
    # Show current section within tab
    st.subheader(f"Current Section: {current_section['name']}")
    st.write(current_section["description"])
    
    # Display current question if available
    if 'questions' in current_section and current_section['questions']:
        current_question = current_section['questions'][st.session_state.current_question_index]
        st.write(f"**Question:** {current_question}")
    
    # Help button and section navigation
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        help_button = st.button("Need help with this section?")
    with col2:
        prev_button = st.button("Previous Section", disabled=st.session_state.current_section_index == 0)
    with col3:
        next_button = st.button("Next Section", disabled=st.session_state.current_section_index == len(current_tab["sections"]) - 1)
    
    # Handle section navigation
    if prev_button and st.session_state.current_section_index > 0:
        st.session_state.current_section_index -= 1
        st.session_state.current_question_index = 0
        st.rerun()
    
    if next_button and st.session_state.current_section_index < len(current_tab["sections"]) - 1:
        st.session_state.current_section_index += 1
        st.session_state.current_question_index = 0
        st.rerun()
    
    # Form input handling
    with st.form(key='chat_form', clear_on_submit=True):
        user_input = st.text_input("Your message:", placeholder="Ask a question or provide information...")
        submit_button = st.form_submit_button("Send")
    
    # Process user input
    if submit_button and user_input:
        process_user_input(user_input)
        st.rerun()
    
    # Handle help button
    if help_button:
        provide_contextual_help()
        st.rerun()
    
    # Progress tracking
    progress = calculate_progress()
    st.sidebar.write("### Progress")
    st.sidebar.progress(progress)
    st.sidebar.write(f"{int(progress * 100)}% complete")
    
    # Export functionality
    st.sidebar.write("### Export Options")
    if st.sidebar.button("Export Configuration"):
        csv_data, filename = export_configuration()
        st.sidebar.download_button(
            label="📥 Download Configuration (CSV)",
            data=csv_data,
            file_name=filename,
            mime="text/csv"
        )

if __name__ == "__main__":
    main()