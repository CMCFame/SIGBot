import streamlit as st
import pandas as pd
import openai
import json
import io
from datetime import datetime

# Initialize OpenAI client
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Define the SIG tabs structure
SIG_TABS = {
    "Location Hierarchy": {
        "description": "This tab outlines the geographical service territory represented by a 4-level location hierarchy within ARCOS.",
        "fields": [
            {"name": "Location Names", "type": "text_area", "help": "Must contain a blank space per 25 contiguous characters and have a maximum length of 50 characters."},
            {"name": "Location Codes", "type": "text_area", "help": "Each Level 4 entry must have a unique accompanying Location Code, which can be from your HR system or created by you."},
            {"name": "Time Zones", "type": "text_area", "help": "If your company is located in one time zone, enter it. If it spans multiple time zones, specify for each Level 4 location."},
            {"name": "Location Access and Security", "type": "text_area", "help": "Specify who should have access to location information and any security considerations."}
        ]
    },
    "Matrix of Locations and CO Types": {
        "description": "This tab allows you to define the specific Callout Types available within a given location in ARCOS.",
        "fields": [
            {"name": "Location Hierarchy", "type": "text_area", "help": "Review the 4-level location hierarchy structure defined in the previous tab."},
            {"name": "Callout Types", "type": "text_area", "help": "List the different Callout Types that can be assigned to each location."},
            {"name": "Matrix Configuration", "type": "text_area", "help": "Place an 'X' to indicate which Callout Types are available for each location."}
        ]
    },
    "Matrix of Locations and Reasons": {
        "description": "This tab allows you to define the specific Callout Reasons available within a given location in ARCOS.",
        "fields": [
            {"name": "Location Hierarchy", "type": "text_area", "help": "Review the 4-level location hierarchy structure defined previously."},
            {"name": "Callout Reasons", "type": "text_area", "help": "List the different Callout Reasons that can be assigned to each location."},
            {"name": "Matrix Configuration", "type": "text_area", "help": "List applicable Callout Reasons for each Level 4 location in a single row separated by commas."}
        ]
    },
    "Trouble Locations": {
        "description": "This tab allows you to define a set of Trouble Locations that may be spoken to employees being called out.",
        "fields": [
            {"name": "Trouble Locations List", "type": "text_area", "help": "Create a list of all Trouble Locations for your company."},
            {"name": "Pronunciation", "type": "text_area", "help": "Provide pronunciations for locations which may not be obvious."},
            {"name": "Recording Needed", "type": "text_area", "help": "Indicate if a recording is needed for each Trouble Location."}
        ]
    },
    "Job Classifications": {
        "description": "This tab is used to list the Job Classifications (job titles) of the employees that will be in the ARCOS database.",
        "fields": [
            {"name": "Job Classifications List", "type": "text_area", "help": "List the Job Classifications (job titles) of the employees and assign each a unique ID."},
            {"name": "Journeyman and Apprentice Classes", "type": "text_area", "help": "If applicable, indicate Journeyman and Apprentice classes."},
            {"name": "Recording Needed", "type": "text_area", "help": "Indicate the verbiage to be spoken to employees when being called out."}
        ]
    },
    "Callout Reasons": {
        "description": "This tab shows the Callout Reasons available in ARCOS.",
        "fields": [
            {"name": "Callout Reasons List", "type": "text_area", "help": "List the different Callout Reasons that can be assigned to each callout."},
            {"name": "Pre-recorded Verbiage", "type": "text_area", "help": "Each Callout Reason has a pre-recorded verbiage that can be spoken during the callout."},
            {"name": "Usage Configuration", "type": "text_area", "help": "Indicate which Callout Reasons to use, their sorting order, and default settings."}
        ]
    },
    "Event Types": {
        "description": "This tab outlines the different Event Types used in ARCOS.",
        "fields": [
            {"name": "Event Types List", "type": "text_area", "help": "List the different Event Types that are currently used in ARCOS."},
            {"name": "Configuration", "type": "text_area", "help": "Indicate which Schedule Exceptions to include and configuration settings for each."},
            {"name": "Additional Options", "type": "text_area", "help": "Configure additional options like charging behavior, employee self-service capabilities, and duration limits."}
        ]
    },
    "Callout Type Configuration": {
        "description": "This tab is used to configure the different Callout Types in ARCOS.",
        "fields": [
            {"name": "Callout Types", "type": "text_area", "help": "List the different Callout Types that can be configured."},
            {"name": "Callout Attributes", "type": "text_area", "help": "Configure the specific attributes for each callout type."},
            {"name": "Overlap Configuration", "type": "text_area", "help": "Configure the overlap settings for each callout type."},
            {"name": "Callout Overrides", "type": "text_area", "help": "Configure the override settings for each schedule exception."}
        ]
    },
    "Global Configuration Options": {
        "description": "This tab outlines the global configuration options available in ARCOS.",
        "fields": [
            {"name": "Roster Preferences", "type": "text_area", "help": "Configure the preferences for roster administration."},
            {"name": "Callout Options", "type": "text_area", "help": "Configure various options related to callouts."},
            {"name": "ARCOS Add-Ons", "type": "text_area", "help": "Mark the ARCOS add-on features included in your contract."},
            {"name": "Resequence Options", "type": "text_area", "help": "Configure options related to roster resequencing."},
            {"name": "Paycodes", "type": "text_area", "help": "Configure the various paycodes used in ARCOS."},
            {"name": "VRU Configuration", "type": "text_area", "help": "Configure options related to the Voice Response Unit."}
        ]
    },
    "Data and Interfaces": {
        "description": "This tab outlines the data elements and interfaces required for the ARCOS system.",
        "fields": [
            {"name": "Employee Data", "type": "text_area", "help": "Configure how employee data will be transferred to ARCOS."},
            {"name": "Web Traffic Interface", "type": "text_area", "help": "Configure the web traffic requirements for ARCOS."},
            {"name": "HR Interface", "type": "text_area", "help": "Configure how employee data will be loaded and updated in ARCOS."},
            {"name": "Overtime Interface", "type": "text_area", "help": "Configure how employee overtime hours will be updated in ARCOS."},
            {"name": "Contact Devices", "type": "text_area", "help": "Configure settings related to employee contact devices."}
        ]
    },
    "Additions": {
        "description": "This tab outlines additional configuration options and data elements for the ARCOS system.",
        "fields": [
            {"name": "CTT Configuration", "type": "text_area", "help": "Configure Closest-to-the-Trouble settings."},
            {"name": "Qualifications", "type": "text_area", "help": "Configure qualification settings for employees."},
            {"name": "J/A Rule Usage", "type": "text_area", "help": "Configure Journeyman/Apprentice rule settings."},
            {"name": "Email Alerts", "type": "text_area", "help": "Configure email alert settings."},
            {"name": "Vacation Management", "type": "text_area", "help": "Configure vacation and time-off settings."}
        ]
    }
}

def get_openai_response(prompt, context=""):
    """Get response from OpenAI API"""
    try:
        messages = [
            {"role": "system", "content": "You are a helpful expert on ARCOS system implementation. " + context},
            {"role": "user", "content": prompt}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def load_sig_description():
    """Load the detailed SIG descriptions"""
    with open('sig_descriptions.json', 'r') as file:
        return json.load(file)

def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if 'responses' not in st.session_state:
        st.session_state.responses = {}
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = list(SIG_TABS.keys())[0]

def main():
    st.set_page_config(page_title="ARCOS SIG Form", layout="wide")
    
    # Initialize session state
    initialize_session_state()
    
    # App title and description
    st.title("ARCOS System Implementation Guide Form")
    st.write("Complete the ARCOS System Implementation Guide (SIG) form with AI assistance")
    
    # Create two columns for layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Create tabs for each SIG section
        tabs = st.tabs(list(SIG_TABS.keys()))
        
        # Store current tab selection in session state
        for i, tab_name in enumerate(SIG_TABS.keys()):
            with tabs[i]:
                st.header(tab_name)
                st.write(SIG_TABS[tab_name]["description"])
                
                # Create form fields for this tab
                for field in SIG_TABS[tab_name]["fields"]:
                    field_key = f"{tab_name}_{field['name']}"
                    
                    # Add help text
                    st.write(f"**{field['name']}**")
                    st.info(field["help"])
                    
                    # Get existing value from session state
                    existing_value = st.session_state.responses.get(field_key, "")
                    
                    # Display appropriate input field
                    if field["type"] == "text_area":
                        response = st.text_area(
                            label=f"Enter {field['name']} details",
                            value=existing_value,
                            height=150,
                            key=field_key
                        )
                        # Store response in session state
                        st.session_state.responses[field_key] = response
                    
                    # Add a help button for this field
                    if st.button(f"Get help with {field['name']}", key=f"help_{field_key}"):
                        help_query = f"Explain in detail what information is needed for the '{field['name']}' section in the '{tab_name}' tab of the ARCOS System Implementation Guide. Include examples, best practices, and common configurations."
                        context = f"The user is currently working on the '{tab_name}' tab, specifically the '{field['name']}' section. {field['help']}"
                        help_response = get_openai_response(help_query, context)
                        
                        # Store chat in history
                        st.session_state.chat_history.append({"role": "user", "content": f"Help with {field['name']}"})
                        st.session_state.chat_history.append({"role": "assistant", "content": help_response})
                        
                        # Show the response in an expandable section
                        with st.expander(f"Help for {field['name']}", expanded=True):
                            st.write(help_response)
                
                st.divider()
    
    with col2:
        # AI Assistant section
        st.header("AI Assistant")
        st.write("Ask any question about the ARCOS SIG form:")
        
        # Chat input
        user_question = st.text_input("Your question", key="user_question")
        if st.button("Ask AI Assistant"):
            if user_question:
                # Get current tab for context
                current_tab = st.session_state.current_tab
                context = f"The user is working on the ARCOS System Implementation Guide form. They are currently viewing the '{current_tab}' tab."
                
                # Get response from OpenAI
                response = get_openai_response(user_question, context)
                
                # Store in chat history
                st.session_state.chat_history.append({"role": "user", "content": user_question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        # Display chat history
        st.subheader("Chat History")
        chat_container = st.container()
        
        with chat_container:
            for message in st.session_state.chat_history[-10:]:  # Show last 10 messages
                if message["role"] == "user":
                    st.write(f"You: {message['content']}")
                else:
                    st.write(f"Assistant: {message['content']}")
        
        # Clear chat history button
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.experimental_rerun()
        
        # Export form data
        st.subheader("Export Form Data")
        if st.button("Export as CSV"):
            # Convert responses to DataFrame
            data = []
            for key, value in st.session_state.responses.items():
                tab, field = key.split("_", 1)
                data.append({
                    "Tab": tab,
                    "Field": field,
                    "Response": value
                })
            
            df = pd.DataFrame(data)
            
            # Convert to CSV
            csv = df.to_csv(index=False)
            
            # Create download button
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"arcos_sig_responses_{timestamp}.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()