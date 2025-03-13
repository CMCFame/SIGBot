# ============================================================================
# IMPORTS AND SETUP
# ============================================================================
import streamlit as st
import pandas as pd
import openai
import json
import io
from datetime import datetime
import base64

# ============================================================================
# OPENAI CLIENT INITIALIZATION
# ============================================================================
try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    print(f"Warning: OpenAI client initialization failed - {str(e)}")
    # Create a dummy client for demo purposes when API key is not available
    class DummyClient:
        def __init__(self):
            self.chat = self
            self.completions = self
        
        def create(self, **kwargs):
            from collections import namedtuple
            Choice = namedtuple('Choice', ['message'])
            Message = namedtuple('Message', ['content'])
            Response = namedtuple('Response', ['choices'])
            
            msg = Message(content="This is a placeholder response since the OpenAI API key is not configured. In a real deployment, this would be a helpful response from the AI model.")
            choices = [Choice(message=msg)]
            return Response(choices=choices)
    
    client = DummyClient()

# ============================================================================
# STREAMLIT PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="ARCOS SIG Form",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# COLOR SCHEME AND CSS STYLING
# ============================================================================
# Define color scheme to match ARCOS branding
ARCOS_RED = "#e3051b"
ARCOS_LIGHT_RED = "#ffcccc"
ARCOS_GREEN = "#99cc99"
ARCOS_BLUE = "#6699ff"

# Custom CSS to improve the look and feel
st.markdown("""
<style>
    .main-header {color: #e3051b; font-size: 2.5rem; font-weight: bold;}
    .tab-header {color: #e3051b; font-size: 1.5rem; font-weight: bold; margin-top: 1rem;}
    .section-header {font-size: 1.2rem; font-weight: bold; margin-top: 1rem; margin-bottom: 0.5rem;}
    .info-box {background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 10px;}
    .red-bg {background-color: #ffcccc;}
    .green-bg {background-color: #99cc99;}
    .blue-bg {background-color: #6699ff;}
    .stButton>button {background-color: #e3051b; color: white;}
    .stButton>button:hover {background-color: #b30000;}
    .help-btn {font-size: 0.8rem; padding: 2px 8px;}
    .st-emotion-cache-16idsys p {font-size: 14px;}
    .hierarchy-table th {background-color: #e3051b; color: white; text-align: center; font-weight: bold;}
    .hierarchy-table td {text-align: center; padding: 8px;}
    .color-key-box {padding: 5px; margin: 2px; display: inline-block; width: 80px; text-align: center;}
    .arcos-logo {max-width: 200px; margin-bottom: 10px;}
    .download-button {background-color: #28a745; color: white; padding: 10px 15px; border-radius: 5px; text-decoration: none; display: inline-block; margin-top: 10px;}
    .download-button:hover {background-color: #218838; color: white; text-decoration: none;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
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

def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if 'responses' not in st.session_state:
        st.session_state.responses = {}
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Location Hierarchy"
        
    if 'hierarchy_data' not in st.session_state:
        # Initialize with some sample data, now including callout types and reasons
        st.session_state.hierarchy_data = {
            "levels": ["Level 1", "Level 2", "Level 3", "Level 4"],
            "labels": ["Parent Company", "Business Unit", "Division", "OpCenter"],
            "entries": [
                {
                    "level1": "", 
                    "level2": "", 
                    "level3": "", 
                    "level4": "", 
                    "timezone": "", 
                    "codes": ["", "", "", "", ""],
                    "callout_types": {
                        "Normal": False,
                        "All Hands on Deck": False,
                        "Fill Shift": False,
                        "Travel": False,
                        "Notification": False,
                        "Notification (No Response)": False
                    },
                    "callout_reasons": ""
                }
            ],
            "timezone": "ET / CT / MT / AZ / PT"
        }
    
    # If existing entries don't have callout_types or callout_reasons fields, add them
    if 'hierarchy_data' in st.session_state:
        for entry in st.session_state.hierarchy_data["entries"]:
            if "callout_types" not in entry:
                entry["callout_types"] = {
                    "Normal": False,
                    "All Hands on Deck": False,
                    "Fill Shift": False,
                    "Travel": False,
                    "Notification": False,
                    "Notification (No Response)": False
                }
            if "callout_reasons" not in entry:
                entry["callout_reasons"] = ""
        
    if 'callout_types' not in st.session_state:
        st.session_state.callout_types = ["Normal", "All Hands on Deck", "Fill Shift", "Travel", "Notification", "Notification (No Response)"]
    
    if 'callout_reasons' not in st.session_state:
        st.session_state.callout_reasons = ["Gas Leak", "Gas Fire", "Gas Emergency", "Car Hit Pole", "Wires Down"]
        
    if 'job_classifications' not in st.session_state:
        st.session_state.job_classifications = [
            {"type": "", "title": "", "ids": ["", "", "", "", ""], "recording": ""}
        ]

def render_color_key():
    """Render the color key header similar to the Excel file"""
    st.markdown("""
    <div style="margin-bottom: 15px; border: 1px solid #ddd; padding: 10px;">
        <h3>Color Key</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 5px;">
            <div class="color-key-box" style="background-color: #ffcccc;">Delete</div>
            <div class="color-key-box" style="background-color: #99cc99;">Changes</div>
            <div class="color-key-box" style="background-color: #6699ff;">Moves</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================
def load_callout_reasons():
    """Load callout reasons from JSON file"""
    try:
        with open('callout_reasons.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading callout reasons: {str(e)}")
        # Return a basic set if file can't be loaded
        return [
            {"ID": "0", "Callout Reason Drop-Down Label": "", "Use?": "x", "Default?": "x", "Verbiage": "n/a"},
            {"ID": "1001", "Callout Reason Drop-Down Label": "Broken Line", "Use?": "x", "Default?": "", "Verbiage": "Pre-recorded"},
            {"ID": "1002", "Callout Reason Drop-Down Label": "Depression Road", "Use?": "x", "Default?": "", "Verbiage": "Pre-recorded"},
            {"ID": "1003", "Callout Reason Drop-Down Label": "Depression Yard", "Use?": "x", "Default?": "", "Verbiage": "Pre-recorded"},
            {"ID": "1007", "Callout Reason Drop-Down Label": "Emergency", "Use?": "x", "Default?": "", "Verbiage": "Pre-recorded"},
            {"ID": "1008", "Callout Reason Drop-Down Label": "Odor", "Use?": "x", "Default?": "", "Verbiage": "Pre-recorded"}
        ]

# ============================================================================
# LOCATION HIERARCHY TAB
# ============================================================================
def render_location_hierarchy_form():
    """Render the Location Hierarchy form with interactive elements"""
    st.markdown('<p class="tab-header">Location Hierarchy - Complete Configuration</p>', unsafe_allow_html=True)
    
    # Generate a unique identifier for this session
    import uuid
    session_id = str(uuid.uuid4())[:8]
    
    # Display descriptive text
    with st.expander("Instructions", expanded=False):
        st.markdown("""
        In ARCOS, your geographical service territory will be represented by a 4-level location hierarchy. You may refer to each Level by changing the Label to suit your requirements. The breakdown doesn't have to be geographical. Different business functions may also be split into different Level 2 or Level 3 locations.
        
        **Location names must contain a blank space per 25 contiguous characters.** Example: the hyphenated village of "Sutton-under-Whitestonecliffe" in England would be considered invalid (29 contiguous characters). Sutton under Whitestonecliffe would be valid. The max length for a location name is 50 characters.
        
        **Each Level 4 entry must have an accompanying Location Code.** This code can be from your HR system or something you create. It is important to make sure each code and each Location Name (on all levels) is unique. A code can be any combination of numbers and letters.
        
        **To create sub-branches:** 
        - Add a new location entry and fill only the levels you need.
        - Use the "Add sub-branch" buttons to quickly create entries that inherit values from their parent levels.
        
        **For each Level 4 (OpCenter):**
        - Add Location Codes (up to 5)
        - Configure Callout Types that apply to this location
        - Specify Callout Reasons specific to this location (comma-separated)
        """)
    
    # Add New Location button
    if st.button("➕ Add New Location Entry", key=f"add_loc_entry_{session_id}"):
        st.session_state.hierarchy_data["entries"].append(
            {
                "level1": "", 
                "level2": "", 
                "level3": "", 
                "level4": "", 
                "timezone": "", 
                "codes": ["", "", "", "", ""],
                "callout_types": {
                    "Normal": False,
                    "All Hands on Deck": False,
                    "Fill Shift": False,
                    "Travel": False,
                    "Notification": False,
                    "Notification (No Response)": False
                },
                "callout_reasons": ""
            }
        )
        st.rerun()
    
    # Default time zone info
    st.markdown('<p class="section-header">Default Time Zone</p>', unsafe_allow_html=True)
    st.write("Set a default time zone to be used when a specific zone is not specified for a location entry.")
    default_timezone = st.text_input("Default Time Zone", 
                                   value=st.session_state.hierarchy_data["timezone"],
                                   key=f"default_timezone_{session_id}")
    st.session_state.hierarchy_data["timezone"] = default_timezone
    
    # Preview of hierarchy structure in table format
    st.markdown('<p class="section-header">Hierarchy Entries</p>', unsafe_allow_html=True)
    
    # Display a table header without using columns
    labels = st.session_state.hierarchy_data["labels"]
    st.markdown(f"""
    <div style="display: flex; margin-bottom: 10px; font-weight: bold;">
        <div style="flex: 0.5; min-width: 50px;">Entry #</div>
        <div style="flex: 2;">{labels[0]}</div>
        <div style="flex: 2;">{labels[1]}</div>
        <div style="flex: 2;">{labels[2]}</div>
        <div style="flex: 2;">{labels[3]}</div>
        <div style="flex: 2;">Time Zone</div>
        <div style="flex: 0.5; min-width: 50px;">Actions</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Instead of nesting columns, we'll create a separate row for each entry
    for i, entry in enumerate(st.session_state.hierarchy_data["entries"]):
        # Creating separate containers for each row to avoid nesting columns
        entry_container = st.container()
        
        # Use a simple single-level column layout for each entry
        with entry_container:
            row_cols = st.columns([0.5, 2, 2, 2, 2, 2, 0.5])
            
            with row_cols[0]:
                st.write(f"#{i+1}")
            
            with row_cols[1]:
                entry["level1"] = st.text_input("Level 1", value=entry["level1"], key=f"lvl1_{i}_{session_id}", 
                                              placeholder=f"Enter {labels[0]}", label_visibility="collapsed")
            
            with row_cols[2]:
                entry["level2"] = st.text_input("Level 2", value=entry["level2"], key=f"lvl2_{i}_{session_id}", 
                                              placeholder=f"Enter {labels[1]}", label_visibility="collapsed")
            
            with row_cols[3]:
                entry["level3"] = st.text_input("Level 3", value=entry["level3"], key=f"lvl3_{i}_{session_id}", 
                                              placeholder=f"Enter {labels[2]}", label_visibility="collapsed")
            
            with row_cols[4]:
                entry["level4"] = st.text_input("Level 4", value=entry["level4"], key=f"lvl4_{i}_{session_id}", 
                                              placeholder=f"Enter {labels[3]}", label_visibility="collapsed")
            
            with row_cols[5]:
                entry["timezone"] = st.text_input("Time Zone", value=entry.get("timezone", ""), key=f"tz_{i}_{session_id}",
                                               placeholder=st.session_state.hierarchy_data["timezone"], 
                                               label_visibility="collapsed")
            
            with row_cols[6]:
                # Delete button
                if st.button("🗑️", key=f"del_{i}_{session_id}", help="Remove this entry"):
                    st.session_state.hierarchy_data["entries"].pop(i)
                    st.rerun()
        
        # Sub-branch buttons in a separate container
        if entry["level1"]:
            branch_container = st.container()
            with branch_container:
                sb_cols = st.columns([4, 2, 2, 2, 2])
                
                # Add Business Unit button (only if level1 is filled)
                with sb_cols[1]:
                    if st.button(f"+ Add Business Unit", key=f"add_bu_{i}_{session_id}", 
                               help=f"Add a new Business Unit under {entry['level1']}"):
                        new_entry = {
                            "level1": entry["level1"],
                            "level2": "",
                            "level3": "",
                            "level4": "",
                            "timezone": entry.get("timezone", ""),
                            "codes": ["", "", "", "", ""],
                            "callout_types": {
                                "Normal": False,
                                "All Hands on Deck": False,
                                "Fill Shift": False,
                                "Travel": False,
                                "Notification": False,
                                "Notification (No Response)": False
                            },
                            "callout_reasons": ""
                        }
                        st.session_state.hierarchy_data["entries"].append(new_entry)
                        st.rerun()
                
                # Add Division button (only if level1 and level2 are filled)
                with sb_cols[2]:
                    if entry["level2"]:
                        if st.button(f"+ Add Division", key=f"add_div_{i}_{session_id}", 
                                   help=f"Add a new Division under {entry['level2']}"):
                            new_entry = {
                                "level1": entry["level1"],
                                "level2": entry["level2"],
                                "level3": "",
                                "level4": "",
                                "timezone": entry.get("timezone", ""),
                                "codes": ["", "", "", "", ""],
                                "callout_types": {
                                    "Normal": False,
                                    "All Hands on Deck": False,
                                    "Fill Shift": False,
                                    "Travel": False,
                                    "Notification": False,
                                    "Notification (No Response)": False
                                },
                                "callout_reasons": ""
                            }
                            st.session_state.hierarchy_data["entries"].append(new_entry)
                            st.rerun()
                
                # Add OpCenter button (only if level1, level2, and level3 are filled)
                with sb_cols[3]:
                    if entry["level2"] and entry["level3"]:
                        if st.button(f"+ Add OpCenter", key=f"add_op_{i}_{session_id}", 
                                   help=f"Add a new OpCenter under {entry['level3']}"):
                            new_entry = {
                                "level1": entry["level1"],
                                "level2": entry["level2"],
                                "level3": entry["level3"],
                                "level4": "",
                                "timezone": entry.get("timezone", ""),
                                "codes": ["", "", "", "", ""],
                                "callout_types": {
                                    "Normal": False,
                                    "All Hands on Deck": False,
                                    "Fill Shift": False,
                                    "Travel": False,
                                    "Notification": False,
                                    "Notification (No Response)": False
                                },
                                "callout_reasons": ""
                            }
                            st.session_state.hierarchy_data["entries"].append(new_entry)
                            st.rerun()
        
        # LEVEL 4 CONFIGURATION in a separate container
        if entry["level4"]:
            with st.expander(f"Configure {entry['level4']} Details", expanded=False):
                # 1. LOCATION CODES SECTION
                st.markdown(f"<div style='margin: 10px 0;'><b>Location Codes for {entry['level4']}</b></div>", unsafe_allow_html=True)
                
                # Split code fields into separate containers to avoid nesting
                code_container = st.container()
                with code_container:
                    # Create 5 columns for the codes
                    code_cols = st.columns(5)
                    
                    # Add text fields for each code
                    for j in range(5):
                        with code_cols[j]:
                            if j < len(entry["codes"]):
                                entry["codes"][j] = st.text_input(
                                    f"Code {j+1}", 
                                    value=entry["codes"][j], 
                                    key=f"code_{i}_{j}_{session_id}"
                                )
                            else:
                                # Ensure we have 5 codes
                                while len(entry["codes"]) <= j:
                                    entry["codes"].append("")
                                
                                entry["codes"][j] = st.text_input(
                                    f"Code {j+1}", 
                                    value="", 
                                    key=f"code_{i}_{j}_{session_id}"
                                )
                
                st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
                
                # 2. CALLOUT TYPES SECTION
                st.markdown(f"<div style='margin: 10px 0;'><b>Callout Types for {entry['level4']}</b></div>", unsafe_allow_html=True)
                st.write("Select the callout types available for this location:")
                
                # Split checkboxes into separate groups to avoid nesting
                ct_container1 = st.container()
                with ct_container1:
                    ct_cols1 = st.columns(3)
                    with ct_cols1[0]:
                        entry["callout_types"]["Normal"] = st.checkbox(
                            "Normal", 
                            value=entry["callout_types"].get("Normal", False),
                            key=f"ct_normal_{i}_{session_id}"
                        )
                    
                    with ct_cols1[1]:
                        entry["callout_types"]["All Hands on Deck"] = st.checkbox(
                            "All Hands on Deck", 
                            value=entry["callout_types"].get("All Hands on Deck", False),
                            key=f"ct_ahod_{i}_{session_id}"
                        )
                    
                    with ct_cols1[2]:
                        entry["callout_types"]["Fill Shift"] = st.checkbox(
                            "Fill Shift", 
                            value=entry["callout_types"].get("Fill Shift", False),
                            key=f"ct_fill_{i}_{session_id}"
                        )
                
                ct_container2 = st.container()
                with ct_container2:
                    ct_cols2 = st.columns(3)
                    with ct_cols2[0]:
                        entry["callout_types"]["Travel"] = st.checkbox(
                            "Travel", 
                            value=entry["callout_types"].get("Travel", False),
                            key=f"ct_travel_{i}_{session_id}"
                        )
                    
                    with ct_cols2[1]:
                        entry["callout_types"]["Notification"] = st.checkbox(
                            "Notification", 
                            value=entry["callout_types"].get("Notification", False),
                            key=f"ct_notif_{i}_{session_id}"
                        )
                    
                    with ct_cols2[2]:
                        entry["callout_types"]["Notification (No Response)"] = st.checkbox(
                            "Notification (No Response)", 
                            value=entry["callout_types"].get("Notification (No Response)", False),
                            key=f"ct_notif_nr_{i}_{session_id}"
                        )
                
                st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
                
                # 3. CALLOUT REASONS SECTION
                st.markdown(f"<div style='margin: 10px 0;'><b>Callout Reasons for {entry['level4']}</b></div>", unsafe_allow_html=True)
                st.write("Enter applicable callout reasons for this location (comma-separated):")
                
                entry["callout_reasons"] = st.text_area(
                    "Callout Reasons",
                    value=entry.get("callout_reasons", ""),
                    height=100,
                    key=f"reasons_{i}_{session_id}",
                    placeholder="Gas Leak, Gas Fire, Gas Emergency, Car Hit Pole, Wires Down"
                )
            
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        else:
            if entry["level1"] or entry["level2"] or entry["level3"]:
                st.info(f"Enter {labels[3]} to complete this entry and add location codes, callout types, and reasons.")
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    # Show preview in a separate container to avoid nesting
    preview_container = st.container()
    with preview_container:
        st.markdown('<p class="section-header">Hierarchy Preview</p>', unsafe_allow_html=True)
        
        def generate_hierarchy_preview():
            # Create a tree structure to organize the hierarchy
            tree = {}
            
            # Populate the tree
            for entry in st.session_state.hierarchy_data["entries"]:
                if not entry["level1"]:
                    continue
                    
                l1 = entry["level1"]
                if l1 not in tree:
                    tree[l1] = {}
                
                if entry["level2"]:
                    l2 = entry["level2"]
                    if l2 not in tree[l1]:
                        tree[l1][l2] = {}
                    
                    if entry["level3"]:
                        l3 = entry["level3"]
                        if l3 not in tree[l1][l2]:
                            tree[l1][l2][l3] = []
                        
                        if entry["level4"]:
                            l4_info = {
                                "name": entry["level4"],
                                "codes": [c for c in entry["codes"] if c],
                                "timezone": entry["timezone"],
                                "callout_types": [ct for ct, enabled in entry["callout_types"].items() if enabled],
                                "callout_reasons": entry["callout_reasons"]
                            }
                            tree[l1][l2][l3].append(l4_info)
            
            # Generate the text representation
            lines = []
            
            for l1, l1_children in tree.items():
                lines.append(f"• {l1}")
                
                for l2, l2_children in l1_children.items():
                    lines.append(f"  • {l2}")
                    
                    for l3, l3_children in l2_children.items():
                        lines.append(f"    • {l3}")
                        
                        for l4_info in l3_children:
                            lines.append(f"      • {l4_info['name']}")
                            
                            if l4_info["codes"]:
                                lines.append(f"        (Codes: {', '.join(l4_info['codes'])})")
                            
                            if l4_info["timezone"]:
                                lines.append(f"        [Time Zone: {l4_info['timezone']}]")
                            
                            if l4_info["callout_types"]:
                                lines.append(f"        [Callout Types: {', '.join(l4_info['callout_types'])}]")
                            
                            if l4_info["callout_reasons"]:
                                lines.append(f"        [Callout Reasons: {l4_info['callout_reasons']}]")
            
            if not lines:
                return "No entries yet. Use the form on the left to add location hierarchy entries."
            
            return "\n".join(lines)
        
        st.code(generate_hierarchy_preview())
        
        # Display sample hierarchy from example
        st.markdown('<p class="section-header">Sample Hierarchy</p>', unsafe_allow_html=True)
        st.info("""
        Example hierarchy:
        
        • CenterPoint Energy (Level 1)
          • Houston Electric (Level 2)
            • Distribution Operations (Level 3)
              • Baytown (Level 4, Codes: B1, B2, B3)
                [Callout Types: Normal, All Hands on Deck]
                [Callout Reasons: Gas Leak, Gas Fire, Gas Emergency]
              • Bellaire (Level 4, Codes: ENN1, ENN2)
                [Callout Types: Normal, Fill Shift]
                [Callout Reasons: Car Hit Pole, Wires Down]
        """)

# ============================================================================
# MATRIX OF LOCATIONS AND CALLOUT TYPES TAB
# ============================================================================
def render_matrix_locations_callout_types():
    """Render the Matrix of Locations and Callout Types with interactive elements"""
    st.markdown('<p class="tab-header">Matrix of Locations and CO Types</p>', unsafe_allow_html=True)
    
    with st.expander("Instructions", expanded=False):
        st.markdown("""
        This tab allows you to define the specific Callout Types available within a given location in ARCOS.
        
        The matrix allows you to place an "X" in the appropriate cells to indicate which Callout Types are available for each location. If your company desires to have all Callout Types available to all locations, this tab can be skipped.
        """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Manage callout types
        st.markdown('<p class="section-header">Manage Callout Types</p>', unsafe_allow_html=True)
        
        # Current callout types
        st.write("Current Callout Types:")
        
        # Display current callout types in rows of 3
        callout_types = st.session_state.callout_types
        
        # Calculate how many rows we need
        num_items = len(callout_types)
        items_per_row = 3
        num_rows = (num_items + items_per_row - 1) // items_per_row  # Ceiling division
        
        # Create each row separately
        for row in range(num_rows):
            # Create columns for this row
            row_cols = st.columns(items_per_row)
            
            # Fill columns with items
            for col in range(items_per_row):
                idx = row * items_per_row + col
                
                # Check if we have an item for this position
                if idx < num_items:
                    with row_cols[col]:
                        callout_type = callout_types[idx]
                        st.write(f"🔹 {callout_type}")
                        if st.button("Remove", key=f"rm_co_{idx}", help=f"Remove {callout_type}"):
                            st.session_state.callout_types.pop(idx)
                            st.rerun()
        
        # Add new callout type - in a separate row
        st.markdown('<p class="section-header">Add New Callout Type</p>', unsafe_allow_html=True)
        add_cols = st.columns([3, 1])
        with add_cols[0]:
            new_callout = st.text_input("New Callout Type Name", key="new_callout")
        with add_cols[1]:
            if st.button("Add"):
                if new_callout and new_callout not in st.session_state.callout_types:
                    st.session_state.callout_types.append(new_callout)
                    st.rerun()
        
        # Matrix configuration
        st.markdown('<p class="section-header">Callout Types by Location Matrix</p>', unsafe_allow_html=True)
        
        # Create a DataFrame to represent the matrix with full hierarchy path
        matrix_data = []
        
        # Add entries from location hierarchy
        for entry in st.session_state.hierarchy_data["entries"]:
            if entry["level4"]:  # Only Level 4 locations need callout type assignments
                # Create full hierarchical path for display
                hierarchy_path = []
                if entry["level1"]:
                    hierarchy_path.append(entry["level1"])
                if entry["level2"]:
                    hierarchy_path.append(entry["level2"])
                if entry["level3"]:
                    hierarchy_path.append(entry["level3"])
                
                # Format the path for display
                path_str = " > ".join(hierarchy_path)
                location_display = f"{entry['level4']} ({path_str})"
                
                # Use the level4 name as the key for data storage
                location_name = entry["level4"]
                
                row_data = {"Location": location_name, "Display": location_display, "Path": path_str}
                
                # Add a column for each callout type
                for ct in st.session_state.callout_types:
                    key = f"matrix_{location_name}_{ct}".replace(" ", "_")
                    if key not in st.session_state.responses:
                        st.session_state.responses[key] = False
                    row_data[ct] = st.session_state.responses[key]
                
                matrix_data.append(row_data)
        
        # Sort the matrix by hierarchy path to group related locations together
        if matrix_data:
            matrix_data = sorted(matrix_data, key=lambda x: x["Path"])
        
        # Convert to DataFrame
        if matrix_data:
            # Display each location in its own section
            for i, row in enumerate(matrix_data):
                location = row["Location"]
                st.write(f"**{row['Display']}**")
                
                # Calculate number of columns and rows needed for checkboxes
                num_callout_types = len(st.session_state.callout_types)
                max_cols_per_row = 4  # Maximum 4 checkboxes per row
                num_checkbox_rows = (num_callout_types + max_cols_per_row - 1) // max_cols_per_row
                
                # Create rows of checkboxes
                for row_idx in range(num_checkbox_rows):
                    # Create columns for this row
                    check_cols = st.columns(max_cols_per_row)
                    
                    # Fill columns with checkboxes
                    for col_idx in range(max_cols_per_row):
                        ct_idx = row_idx * max_cols_per_row + col_idx
                        
                        # Check if we still have callout types
                        if ct_idx < num_callout_types:
                            with check_cols[col_idx]:
                                ct = st.session_state.callout_types[ct_idx]
                                # Create a unique key for each checkbox that includes the location index and callout type index
                                checkbox_key = f"matrix_{i}_{location}_{ct_idx}_{ct}".replace(" ", "_")
                                
                                # Store the actual response key (which we'll still use for data storage)
                                response_key = f"matrix_{location}_{ct}".replace(" ", "_")
                                
                                # Use the checkbox with unique key, but store in the original response key
                                st.session_state.responses[response_key] = st.checkbox(
                                    ct, 
                                    value=row.get(ct, False), 
                                    key=checkbox_key  # Using the unique key here
                                )
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        else:
            st.warning("Add Level 4 locations in the Location Hierarchy tab first to configure this matrix.")
    
    with col2:
        # Preview matrix as a table
        st.markdown('<p class="section-header">Matrix Preview</p>', unsafe_allow_html=True)
        
        if matrix_data:
            # Create a display version of the matrix for the preview
            preview_data = []
            for row in matrix_data:
                # Use the hierarchical display name for the preview
                display_row = {"Location": row["Display"]}
                for ct in st.session_state.callout_types:
                    key = f"matrix_{row['Location']}_{ct}".replace(" ", "_")
                    display_row[ct] = "X" if key in st.session_state.responses and st.session_state.responses[key] else ""
                preview_data.append(display_row)
            
            # Create dataframe and display it
            preview_df = pd.DataFrame(preview_data)
            # Limit the column width of the location column to prevent very wide tables
            st.dataframe(preview_df, use_container_width=True)
        else:
            st.info("Add locations to see the matrix preview.")
        
        # Help section
        st.markdown('<p class="section-header">Need Help?</p>', unsafe_allow_html=True)
        help_topic = st.selectbox(
            "Select topic for help",
            ["Callout Types", "Matrix Configuration", "Best Practices for Callout Types"]
        )
        
        if st.button("Get Help"):
            help_query = f"Explain in detail what I need to know about {help_topic} when configuring the Matrix of Locations and Callout Types in ARCOS. Include examples and best practices."
            with st.spinner("Loading help..."):
                help_response = get_openai_response(help_query)
                st.session_state.chat_history.append({"role": "user", "content": f"Help with {help_topic}"})
                st.session_state.chat_history.append({"role": "assistant", "content": help_response})
            
            st.info(help_response)

# ============================================================================
# JOB CLASSIFICATIONS TAB
# ============================================================================
def render_job_classifications():
    """Render the Job Classifications form with interactive elements"""
    st.markdown('<p class="tab-header">Job Classifications</p>', unsafe_allow_html=True)
    
    with st.expander("Instructions", expanded=False):
        st.markdown("""
        This tab is used to list the Job Classifications (job titles) of the employees that will be in the ARCOS database.
        
        List the Job Classifications (job titles) of the employees and assign each a unique ID (typically taken from your HR system).
        If you have more than one ID for a Job Class, you can separate up to 5 in different columns.
        
        If applicable, indicate Journeyman and Apprentice classes. If your company requires the option to have a duty position or classification spoken to employees
        when being called out, please indicate the verbiage.
        """)
    
    # Initialize the job classifications if not already in session state
    if 'job_classifications' not in st.session_state:
        st.session_state.job_classifications = [
            {"type": "", "title": "", "ids": ["", "", "", "", ""], "recording": ""}
        ]
    
    # Generate a unique identifier for this session
    import uuid
    session_id = str(uuid.uuid4())[:8]
    
    # Add new job classification button - with a unique key
    if st.button("➕ Add Job Classification", key=f"add_job_class_{session_id}"):
        st.session_state.job_classifications.append(
            {"type": "", "title": "", "ids": ["", "", "", "", ""], "recording": ""}
        )
        st.rerun()
    
    # Display and edit job classifications - avoiding nested columns
    for i, job in enumerate(st.session_state.job_classifications):
        st.markdown(f"<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        st.markdown(f"<p><b>Job Classification #{i+1}</b></p>", unsafe_allow_html=True)
        
        # Type and title in separate container
        type_title_container = st.container()
        with type_title_container:
            type_title_cols = st.columns([2, 3])
            with type_title_cols[0]:
                job["type"] = st.selectbox(
                    "Type", 
                    ["", "Journeyman", "Apprentice"], 
                    index=["", "Journeyman", "Apprentice"].index(job["type"]) if job["type"] in ["", "Journeyman", "Apprentice"] else 0,
                    key=f"job_type_{i}_{session_id}"
                )
            with type_title_cols[1]:
                job["title"] = st.text_input("Job Classification Title", value=job["title"], key=f"job_title_{i}_{session_id}")
        
        # IDs in separate container
        st.markdown("<p><b>Job Classification IDs</b> (up to 5)</p>", unsafe_allow_html=True)
        ids_container = st.container()
        with ids_container:
            id_cols = st.columns(5)
            for j in range(5):
                with id_cols[j]:
                    # Ensure we have enough id slots
                    while len(job["ids"]) <= j:
                        job["ids"].append("")
                    job["ids"][j] = st.text_input(f"ID {j+1}", value=job["ids"][j], key=f"job_id_{i}_{j}_{session_id}")
        
        # Recording in separate container
        recording_container = st.container()
        with recording_container:
            job["recording"] = st.text_input(
                "Recording Verbiage (what should be spoken during callout)", 
                value=job["recording"], 
                key=f"job_rec_{i}_{session_id}",
                help="Leave blank if same as Job Title"
            )
        
        # Delete button in separate container - with unique key
        delete_container = st.container()
        with delete_container:
            if st.button("🗑️ Remove", key=f"del_job_{i}_{session_id}"):
                st.session_state.job_classifications.pop(i)
                st.rerun()
    
    # Preview in separate container
    preview_container = st.container()
    with preview_container:
        st.markdown('<p class="section-header">Classifications Preview</p>', unsafe_allow_html=True)
        
        if st.session_state.job_classifications:
            # Create display data
            job_data = []
            for job in st.session_state.job_classifications:
                if job["title"]:  # Only include jobs with titles
                    job_data.append({
                        "Type": job["type"],
                        "Title": job["title"],
                        "IDs": ", ".join([id for id in job["ids"] if id]),
                        "Recording": job["recording"] if job["recording"] else "(Same as title)"
                    })
            
            if job_data:
                job_df = pd.DataFrame(job_data)
                st.dataframe(job_df, use_container_width=True)
            else:
                st.info("Add job classifications to see the preview.")
        else:
            st.info("No job classifications added yet.")

# ============================================================================
# CALLOUT REASONS TAB
# ============================================================================
def render_callout_reasons_form():
    """Render the Callout Reasons form with interactive elements"""
    st.markdown('<p class="tab-header">Callout Reasons</p>', unsafe_allow_html=True)
    
    with st.expander("Instructions", expanded=False):
        st.markdown("""
        This tab shows the Callout Reasons available in ARCOS.
        
        Select which callout reasons you would like to use in your ARCOS system. You can filter the list to find specific reasons,
        and mark which one should be the default. Each reason has pre-recorded verbiage that will be spoken during callouts.
        """)
    
    # Load callout reasons
    callout_reasons = load_callout_reasons()
    
    # Store selected reasons in session state if not already there
    if 'selected_callout_reasons' not in st.session_state:
        st.session_state.selected_callout_reasons = [r["ID"] for r in callout_reasons if r.get("Use?") == "x"]
    
    if 'default_callout_reason' not in st.session_state:
        default_reasons = [r["ID"] for r in callout_reasons if r.get("Default?") == "x"]
        st.session_state.default_callout_reason = default_reasons[0] if default_reasons else ""
    
    # Split the UI into left and right parts (filters/list on left, preview on right)
    # Using separate containers to avoid nesting issues
    
    # 1. Filters section
    filter_container = st.container()
    with filter_container:
        st.markdown('<p class="section-header">Filter Callout Reasons</p>', unsafe_allow_html=True)
        
        # Use separate containers for each row of filters
        filter_row1 = st.container()
        with filter_row1:
            filter_cols1 = st.columns([3, 1, 1])
            
            with filter_cols1[0]:
                search_term = st.text_input("Search by name or ID", key="search_callout_reasons")
            
            with filter_cols1[1]:
                show_selected_only = st.checkbox("Show selected only", key="show_selected_only")
            
            with filter_cols1[2]:
                # Bulk operations
                if st.button("Clear All Selections"):
                    st.session_state.selected_callout_reasons = []
                    st.rerun()
    
    # Apply filters
    filtered_reasons = callout_reasons.copy()  # Create a copy to avoid modifying the original
    
    if search_term:
        search_term = search_term.lower().strip()  # Normalize and clean the search term
        
        # Create a new filtered list based on search term
        filtered_reasons = []
        for reason in callout_reasons:
            # Convert values to strings to avoid type errors
            reason_id = str(reason.get("ID", "")).lower()
            reason_label = str(reason.get("Callout Reason Drop-Down Label", "")).lower()
            
            # Check if search term appears in either ID or label
            if search_term in reason_id or search_term in reason_label:
                filtered_reasons.append(reason)
    
    # Apply selected-only filter
    if show_selected_only:
        filtered_reasons = [r for r in filtered_reasons if r.get("ID") in st.session_state.selected_callout_reasons]
    
    # 2. Results count and pagination in separate container
    pagination_container = st.container()
    with pagination_container:
        st.markdown('<p class="section-header">Select Callout Reasons to Use</p>', unsafe_allow_html=True)
        
        # Show count of filtered results
        if search_term or show_selected_only:
            st.write(f"Showing {len(filtered_reasons)} of {len(callout_reasons)} reasons")
        
        # Pagination controls in separate row
        items_per_page = 15
        total_reasons = len(filtered_reasons)
        total_pages = max(1, (total_reasons + items_per_page - 1) // items_per_page)
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 0
        
        # Cap current page to valid range
        st.session_state.current_page = min(st.session_state.current_page, total_pages - 1)
        st.session_state.current_page = max(st.session_state.current_page, 0)
        
        if total_pages > 1:
            page_container = st.container()
            with page_container:
                page_cols = st.columns([1, 3, 1])
                
                with page_cols[0]:
                    if st.button("◀ Previous", disabled=st.session_state.current_page == 0):
                        st.session_state.current_page = max(0, st.session_state.current_page - 1)
                        st.rerun()
                
                with page_cols[1]:
                    st.write(f"Page {st.session_state.current_page + 1} of {total_pages}")
                
                with page_cols[2]:
                    if st.button("Next ▶", disabled=st.session_state.current_page >= total_pages - 1):
                        st.session_state.current_page = min(total_pages - 1, st.session_state.current_page + 1)
                        st.rerun()
    
    # 3. Display paginated results
    results_container = st.container()
    with results_container:
        # Calculate pagination indices
        start_idx = st.session_state.current_page * items_per_page
        end_idx = min(start_idx + items_per_page, total_reasons)
        
        if total_reasons == 0:
            st.info("No callout reasons match your filter criteria.")
        else:
            current_page_reasons = filtered_reasons[start_idx:end_idx]
            
            # Create separate container for each reason to avoid nesting issues
            for i, reason in enumerate(current_page_reasons):
                reason_container = st.container()
                with reason_container:
                    reason_id = str(reason.get("ID", ""))
                    reason_label = reason.get("Callout Reason Drop-Down Label", "")
                    is_default = reason_id == st.session_state.default_callout_reason
                    
                    reason_cols = st.columns([5, 2, 2])
                    with reason_cols[0]:
                        # Format row with alternating background for readability
                        background = "#f9f9f9" if i % 2 == 0 else "#ffffff"
                        
                        # Create checkbox for selection
                        default_checked = reason_id in st.session_state.selected_callout_reasons
                        is_checked = st.checkbox(
                            f"{reason_id}: {reason_label}",
                            value=default_checked,
                            key=f"reason_{reason_id}"
                        )
                        
                        # Update session state based on checkbox
                        if is_checked and reason_id not in st.session_state.selected_callout_reasons:
                            st.session_state.selected_callout_reasons.append(reason_id)
                        elif not is_checked and reason_id in st.session_state.selected_callout_reasons:
                            st.session_state.selected_callout_reasons.remove(reason_id)
                    
                    with reason_cols[1]:
                        st.write(f"Verbiage: {reason.get('Verbiage', '')}")
                    
                    with reason_cols[2]:
                        # Set as default button
                        if st.button(f"Set as Default", key=f"default_{reason_id}", 
                                   disabled=not is_checked):
                            st.session_state.default_callout_reason = reason_id
                            # Update the JSON data
                            for r in callout_reasons:
                                r["Default?"] = "x" if r["ID"] == reason_id else ""
                            st.rerun()
                    
                    # Add a separator
                    if i < len(current_page_reasons) - 1:
                        st.markdown("<hr style='margin: 5px 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
    
    # 4. Preview section in separate container
    preview_container = st.container()
    with preview_container:
        st.markdown('<p class="section-header">Selected Callout Reasons</p>', unsafe_allow_html=True)
        
        selected_count = len(st.session_state.selected_callout_reasons)
        st.write(f"You have selected {selected_count} callout reason(s).")
        
        # Display selected reasons
        if selected_count > 0:
            selected_reasons = [r for r in callout_reasons if str(r.get("ID", "")) in st.session_state.selected_callout_reasons]
            
            # Create a DataFrame for display
            selected_df = pd.DataFrame([{
                "ID": r.get("ID", ""),
                "Reason": r.get("Callout Reason Drop-Down Label", ""),
                "Default": "✓" if r.get("ID") == st.session_state.default_callout_reason else ""
            } for r in selected_reasons])
            
            st.dataframe(selected_df, use_container_width=True)
            
            # Export selected reasons button
            if st.button("Update Configuration"):
                # Update the Use? and Default? flags in the callout_reasons.json file
                for r in callout_reasons:
                    r["Use?"] = "x" if r["ID"] in st.session_state.selected_callout_reasons else ""
                    r["Default?"] = "x" if r["ID"] == st.session_state.default_callout_reason else ""
                
                # Try to save the updated json
                try:
                    with open('callout_reasons.json', 'w') as file:
                        json.dump(callout_reasons, file, indent=2)
                    st.success("Callout Reasons configuration updated successfully!")
                except Exception as e:
                    st.error(f"Error saving configuration: {str(e)}")
        else:
            st.info("No callout reasons selected. Please select from the list on the left.")

# ============================================================================
# EVENT TYPES TAB
# ============================================================================
def render_event_types_form():
    """Render the Event Types form with interactive elements matching the Excel format"""
    st.markdown('<p class="tab-header">Event Types</p>', unsafe_allow_html=True)
    
    # Display descriptive text
    with st.expander("Instructions", expanded=False):
        st.markdown("""
        Following are the "Event Types" that are currently used in ARCOS.
        
        - Place an "X" in the "Use?" column for each Schedule Exception you want included in your system.
        - Place an "X" in the "Use in Schedule Module Dropdown" for those Events types used as exceptions and needed in the "Add Dropdown".
        - Add additional Event Types at the bottom of the list. Include all working Event Types as well.
        - Click on the drop-down arrow in cell B3 and select "X" to view only those Schedule Exceptions you will be using.
        - Answer the questions in columns D-G, where appropriate.
        """)
    
    # Initialize event types in session state if not already there
    if 'event_types' not in st.session_state:
        st.session_state.event_types = [
            {
                "id": "1001",
                "description": "Working - Normal Shift",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1017",
                "description": "Discipline",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1018",
                "description": "Sick",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1019",
                "description": "Do Not Call",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1024",
                "description": "Vacation",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1030",
                "description": "Family Illness",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1123",
                "description": "FMLA",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1124",
                "description": "Funeral",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1153",
                "description": "Light Duty",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1188",
                "description": "Personal Holiday",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1251",
                "description": "Military Leave",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1252",
                "description": "Personal Request",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1327",
                "description": "Mutual Assistance",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1372",
                "description": "Vacation Request",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1424",
                "description": "Out Working",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1500",
                "description": "Rest Time",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1501",
                "description": "Workmans Comp",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            },
            {
                "id": "1502",
                "description": "Working - Holdover",
                "use": True,
                "use_in_dropdown": True,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            }
        ]
    
    # Main content area
    st.markdown('<p class="section-header">Event Types Configuration</p>', unsafe_allow_html=True)
    
    # Last Revision Date
    date_cols = st.columns([3, 1])
    with date_cols[0]:
        st.write("Last Revision Date:")
    with date_cols[1]:
        current_date = datetime.now().strftime("%m/%d/%Y")
        revision_date = st.text_input("", value=current_date, key="revision_date", 
                                     label_visibility="collapsed")
    
    # Create a scrollable container for the table
    with st.container():
        # Header row for mobile columns
        header_cols = st.columns([2, 1, 1, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2])
        
        with header_cols[0]:
            st.write("Event Description")
        with header_cols[1]:
            st.write("Use?")
        with header_cols[2]:
            st.write("Use in Schedule Module Dropdown")
        with header_cols[3]:
            st.write("Include in Override ALL?")
        with header_cols[4]:
            st.write("If an override occurs on this Schedule Exception and the employee is called and results in a non-accept, should the employee be Charged or Excused?")
        with header_cols[5]:
            st.write("If an employee is skipped during a callout due to being on this Schedule Exception, should he be Charged or Excused?")
        with header_cols[6]:
            st.write("Can the employee place themselves on this Exception on Inbound?")
        with header_cols[7]:
            st.write("Allow users to be released from this schedule record via Mobile?")
        with header_cols[8]:
            st.write("Allow users to automatically enter rest status from this schedule record via Mobile?")
        with header_cols[9]:
            st.write("Allow users to make themselves unavailable using this schedule record via Mobile?")
        with header_cols[10]:
            st.write("Allow users to place themselves on this status via rest status via Mobile?")
        with header_cols[11]:
            st.write("What is the minimum duration users can place themselves on this schedule record? (In Hours)")
        with header_cols[12]:
            st.write("What is the maximum duration users can place themselves on this schedule record? (In Hours)")
        
        # Add button for new event type
        if st.button("➕ Add New Event Type"):
            # Generate new ID (just increment the highest existing ID)
            existing_ids = [int(event["id"]) for event in st.session_state.event_types]
            new_id = str(max(existing_ids) + 1) if existing_ids else "2000"
            
            # Add new empty event type
            st.session_state.event_types.append({
                "id": new_id,
                "description": "",
                "use": False,
                "use_in_dropdown": False,
                "include_in_override": False,
                "charged_or_excused": "",
                "available_on_inbound": "",
                "employee_on_exception": "",
                "release_mobile": False,
                "release_auto": False,
                "make_unavailable": False,
                "place_status": False,
                "min_duration": "",
                "max_duration": ""
            })
            st.rerun()
        
        # Filter options
        filter_cols = st.columns([3, 1])
        with filter_cols[0]:
            st.write("Filter Event Types:")
        with filter_cols[1]:
            show_active_only = st.checkbox("Show active only", value=False, key="show_active_events")
        
        # Apply filter
        filtered_events = st.session_state.event_types
        if show_active_only:
            filtered_events = [event for event in filtered_events if event["use"]]
        
        # Divider
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        
        # Create each row for event types
        for i, event in enumerate(filtered_events):
            # Event row
            event_cols = st.columns([2, 1, 1, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2])
            
            with event_cols[0]:
                # Description
                event["description"] = st.text_input(
                    "Description", 
                    value=event["description"], 
                    key=f"event_desc_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[1]:
                # Use checkbox
                event["use"] = st.checkbox(
                    "Use", 
                    value=event["use"], 
                    key=f"event_use_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[2]:
                # Use in dropdown checkbox
                event["use_in_dropdown"] = st.checkbox(
                    "Use in Dropdown", 
                    value=event["use_in_dropdown"], 
                    key=f"event_dropdown_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[3]:
                # Override checkbox
                event["include_in_override"] = st.checkbox(
                    "Include in Override", 
                    value=event["include_in_override"], 
                    key=f"event_override_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[4]:
                # Charged or excused selection for non-accept
                event["charged_or_excused"] = st.selectbox(
                    "Charged or Excused", 
                    ["", "Charged", "Excused"], 
                    index=0 if not event["charged_or_excused"] else 
                          (1 if event["charged_or_excused"] == "Charged" else 2),
                    key=f"event_charge1_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[5]:
                # Charged or excused selection for skipped
                event["employee_on_exception"] = st.selectbox(
                    "Charged or Excused", 
                    ["", "Charged", "Excused"], 
                    index=0 if not event["employee_on_exception"] else 
                          (1 if event["employee_on_exception"] == "Charged" else 2),
                    key=f"event_charge2_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[6]:
                # Can place on inbound selection
                event["available_on_inbound"] = st.selectbox(
                    "Available on Inbound", 
                    ["", "Yes", "No"], 
                    index=0 if not event["available_on_inbound"] else 
                          (1 if event["available_on_inbound"] == "Yes" else 2),
                    key=f"event_inbound_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[7]:
                # Release via mobile
                event["release_mobile"] = st.checkbox(
                    "Release via Mobile", 
                    value=event["release_mobile"], 
                    key=f"event_release_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[8]:
                # Auto rest status
                event["release_auto"] = st.checkbox(
                    "Auto Rest", 
                    value=event["release_auto"], 
                    key=f"event_auto_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[9]:
                # Make unavailable
                event["make_unavailable"] = st.checkbox(
                    "Make Unavailable", 
                    value=event["make_unavailable"], 
                    key=f"event_unavail_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[10]:
                # Place on status
                event["place_status"] = st.checkbox(
                    "Place Status", 
                    value=event["place_status"], 
                    key=f"event_status_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[11]:
                # Min duration
                event["min_duration"] = st.text_input(
                    "Min Duration", 
                    value=event["min_duration"], 
                    key=f"event_min_{i}",
                    label_visibility="collapsed"
                )
            
            with event_cols[12]:
                # Max duration
                event["max_duration"] = st.text_input(
                    "Max Duration", 
                    value=event["max_duration"], 
                    key=f"event_max_{i}",
                    label_visibility="collapsed"
                )
            
            # Add remove button for this event type
            remove_cols = st.columns([12, 1])
            with remove_cols[1]:
                if st.button("🗑️", key=f"remove_event_{i}"):
                    st.session_state.event_types.pop(i)
                    st.rerun()
            
            # Add a horizontal line between rows for better readability
            st.markdown("<hr style='margin: 5px 0; border: none; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)
    
    # Side panel with help content
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Help section
        st.markdown('<p class="section-header">Need Help?</p>', unsafe_allow_html=True)
        help_topic = st.selectbox(
            "Select topic for help",
            ["Event Types", "Schedule Exceptions", "Override Configuration", "Mobile Configuration"]
        )
        
        if st.button("Get Help"):
            help_query = f"Explain in detail what I need to know about {help_topic} when configuring ARCOS. Include examples and best practices."
            with st.spinner("Loading help..."):
                help_response = get_openai_response(help_query)
                st.session_state.chat_history.append({"role": "user", "content": f"Help with {help_topic}"})
                st.session_state.chat_history.append({"role": "assistant", "content": help_response})
            
            st.info(help_response)

# ============================================================================
# TROUBLE LOCATIONS TAB
# ============================================================================
def render_trouble_locations_form():
    """Render the Trouble Locations form with interactive elements"""
    st.markdown('<p class="tab-header">Trouble Locations - 2</p>', unsafe_allow_html=True)
    
    # Instructions
    with st.expander("Instructions", expanded=False):
        st.markdown("""
        On this tab you can define a set of Trouble Locations that may be spoken to employees being called out. This can be based on the originating location of a callout or a dropdown list. Your ARCOS project manager will discuss these options with you.
        
        Create a list below of all Trouble Locations for your company and provide pronunciations for locations which may not be obvious.
        
        If your company requires that spoken Trouble Locations be restricted by specific locations within ARCOS (when using a dropdown list), please inform your project manager.
        
        **IMPORTANT - DOUBLE CHECK WITH YOUR IMPLEMENTATION MANAGER ON THE NUMBER OF CALL RECORDINGS THAT ARE AVAILABLE IN YOUR CONTRACT**
        """)
    
    # Initialize trouble locations in session state if not already there
    if 'trouble_locations' not in st.session_state:
        st.session_state.trouble_locations = [
            {"recording_needed": True, "id": "", "location": "", "verbiage": ""}
        ]
    
    # Create table header
    st.markdown("""
    <div style="display: flex; margin-bottom: 10px; font-weight: bold; background-color: #e3051b; color: white; padding: 8px 0;">
        <div style="flex: 1; text-align: center;">Recording Needed</div>
        <div style="flex: 1; text-align: center;">ID</div>
        <div style="flex: 2; text-align: center;">Trouble Location</div>
        <div style="flex: 2; text-align: center;">Verbiage (Pronunciation)</div>
        <div style="flex: 0.5; text-align: center;">Action</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display existing entries
    for i, location in enumerate(st.session_state.trouble_locations):
        location_container = st.container()
        with location_container:
            cols = st.columns([1, 1, 2, 2, 0.5])
            
            with cols[0]:
                location["recording_needed"] = st.checkbox(
                    "Recording Needed", 
                    value=location.get("recording_needed", True),
                    key=f"rec_needed_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[1]:
                location["id"] = st.text_input(
                    "ID", 
                    value=location.get("id", ""),
                    key=f"loc_id_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[2]:
                location["location"] = st.text_input(
                    "Trouble Location", 
                    value=location.get("location", ""),
                    key=f"loc_name_{i}",
                    label_visibility="collapsed"
                )
            
            with cols[3]:
                location["verbiage"] = st.text_input(
                    "Verbiage (Pronunciation)", 
                    value=location.get("verbiage", ""),
                    key=f"loc_verbiage_{i}",
                    label_visibility="collapsed",
                    placeholder="e.g., rok-ferd"
                )
            
            with cols[4]:
                if st.button("🗑️", key=f"del_loc_{i}", help="Remove this location"):
                    st.session_state.trouble_locations.pop(i)
                    st.rerun()
    
    # Add New Entry button
    if st.button("➕ Add Trouble Location"):
        st.session_state.trouble_locations.append(
            {"recording_needed": True, "id": "", "location": "", "verbiage": ""}
        )
        st.rerun()
    
    # Preview section
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p class="section-header">Trouble Locations Preview</p>', unsafe_allow_html=True)
    
    # Create a DataFrame for preview
    if st.session_state.trouble_locations:
        preview_data = []
        for location in st.session_state.trouble_locations:
            if location["location"]:  # Only show locations with names
                preview_data.append({
                    "Recording Needed": "X" if location["recording_needed"] else "",
                    "ID": location["id"],
                    "Trouble Location": location["location"],
                    "Pronunciation": location["verbiage"]
                })
        
        if preview_data:
            preview_df = pd.DataFrame(preview_data)
            st.dataframe(preview_df, use_container_width=True)
        else:
            st.info("Add trouble locations to see the preview.")
    else:
        st.info("No trouble locations added yet.")
    
    # Example section
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p class="section-header">Example Entries</p>', unsafe_allow_html=True)
    
    example_data = [
        {"Recording Needed": "X", "ID": "001", "Trouble Location": "Rockford", "Pronunciation": "rok-ferd"},
        {"Recording Needed": "X", "ID": "002", "Trouble Location": "Paxton", "Pronunciation": "pak-stuhn"},
        {"Recording Needed": "", "ID": "003", "Trouble Location": "Chicago", "Pronunciation": ""}
    ]
    
    example_df = pd.DataFrame(example_data)
    st.dataframe(example_df, use_container_width=True)
    
    # Help section
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p class="section-header">Need Help?</p>', unsafe_allow_html=True)
    
    help_topic = st.selectbox(
        "Select topic for help",
        ["Trouble Locations", "Pronunciation Guide", "Recording Requirements", "Best Practices"]
    )
    
    if st.button("Get Help"):
        help_query = f"Explain in detail what I need to know about {help_topic} when configuring the Trouble Locations tab in ARCOS. Include examples and best practices."
        with st.spinner("Loading help..."):
            help_response = get_openai_response(help_query)
            st.session_state.chat_history.append({"role": "user", "content": f"Help with {help_topic}"})
            st.session_state.chat_history.append({"role": "assistant", "content": help_response})
        
        st.info(help_response)

# ============================================================================
# GENERIC TAB RENDERER
# ============================================================================
def render_generic_tab(tab_name):
    """Render a generic form for tabs that are not yet implemented with custom UI"""
    st.markdown(f'<p class="tab-header">{tab_name}</p>', unsafe_allow_html=True)
    
    # Load descriptions
    try:
        with open('sig_descriptions.json', 'r') as file:
            descriptions = json.load(file)
        
        if tab_name in descriptions:
            tab_desc = descriptions[tab_name]
            st.write(tab_desc["description"])
            
            # Create form fields for this tab
            for field_name, field_info in tab_desc["fields"].items():
                field_key = f"{tab_name}_{field_name}"
                
                # Create expandable section for each field
                with st.expander(f"{field_name}", expanded=False):
                    st.markdown(f"**Description:** {field_info['description']}")
                    
                    if "example" in field_info:
                        st.markdown(f"**Example:** {field_info['example']}")
                    
                    if "best_practices" in field_info:
                        st.markdown(f"**Best Practices:** {field_info['best_practices']}")
                    
                    # Get existing value from session state
                    existing_value = st.session_state.responses.get(field_key, "")
                    
                    # Display input field
                    response = st.text_area(
                        label=f"Enter your {field_name} details below",
                        value=existing_value,
                        height=150,
                        key=field_key
                    )
                    
                    # Store response in session state
                    st.session_state.responses[field_key] = response
                    
                    # Add a help button for this field
                    if st.button(f"Get more help with {field_name}", key=f"help_{field_key}"):
                        help_query = f"Explain in detail what information is needed for the '{field_name}' section in the '{tab_name}' tab of the ARCOS System Implementation Guide. Include examples, best practices, and common configurations."
                        with st.spinner("Loading help..."):
                            help_response = get_openai_response(help_query)
                            st.session_state.chat_history.append({"role": "user", "content": f"Help with {field_name}"})
                            st.session_state.chat_history.append({"role": "assistant", "content": help_response})
                        
                        st.info(help_response)
        else:
            st.write(f"This tab allows you to configure {tab_name} settings in ARCOS.")
            
            # Generic text field for this tab
            tab_key = tab_name.replace(" ", "_").lower()
            existing_value = st.session_state.responses.get(tab_key, "")
            
            response = st.text_area(
                label=f"Enter {tab_name} details",
                value=existing_value,
                height=300,
                key=tab_key
            )
            
            st.session_state.responses[tab_key] = response
            
    except Exception as e:
        st.error(f"Error loading tab data: {str(e)}")
        
        # Generic text field as fallback
        tab_key = tab_name.replace(" ", "_").lower()
        existing_value = st.session_state.responses.get(tab_key, "")
        
        response = st.text_area(
            label=f"Enter {tab_name} details",
            value=existing_value,
            height=300,
            key=tab_key
        )
        
        st.session_state.responses[tab_key] = response

# ============================================================================
# AI ASSISTANT PANEL
# ============================================================================
def render_ai_assistant_panel():
    """Render the AI Assistant panel in the sidebar"""
    st.sidebar.markdown('<p class="section-header">AI Assistant</p>', unsafe_allow_html=True)
    
    # Chat input
    user_question = st.sidebar.text_input("Ask anything about ARCOS configuration:", key="user_question")
    
    if st.sidebar.button("Ask AI Assistant"):
        if user_question:
            # Get current tab for context
            current_tab = st.session_state.current_tab
            context = f"The user is working on the ARCOS System Implementation Guide form. They are currently viewing the '{current_tab}' tab."
            
            # Show spinner while getting response
            with st.sidebar:
                with st.spinner("Getting response..."):
                    # Get response from OpenAI
                    response = get_openai_response(user_question, context)
                    
                    # Store in chat history
                    st.session_state.chat_history.append({"role": "user", "content": user_question})
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # Display chat history
    st.sidebar.markdown('<p class="section-header">Chat History</p>', unsafe_allow_html=True)
    
    chat_container = st.sidebar.container()
    
    with chat_container:
        # Show up to 10 most recent messages
        recent_messages = st.session_state.chat_history[-10:] if len(st.session_state.chat_history) > 0 else []
        for message in recent_messages:
            if message["role"] == "user":
                st.sidebar.markdown(f"<div style='background-color: #f0f0f0; padding: 8px; border-radius: 5px; margin-bottom: 8px;'><b>You:</b> {message['content']}</div>", unsafe_allow_html=True)
            else:
                st.sidebar.markdown(f"<div style='background-color: #e6f7ff; padding: 8px; border-radius: 5px; margin-bottom: 8px;'><b>Assistant:</b> {message['content']}</div>", unsafe_allow_html=True)
    
    # Clear chat history button
    if st.sidebar.button("Clear Chat History", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================
def export_to_csv():
    """Export all form data to CSV and return CSV data"""
    # Collect data from all tabs
    data = []
    
    # Add location hierarchy data
    data.append({"Tab": "Location Hierarchy", "Section": "Labels", "Response": str(st.session_state.hierarchy_data["labels"])})
    
    # Add each location entry separately for better readability
    for i, entry in enumerate(st.session_state.hierarchy_data["entries"]):
        if entry["level1"] or entry["level2"] or entry["level3"] or entry["level4"]:
            location_str = f"Level 1: {entry['level1']}, Level 2: {entry['level2']}, Level 3: {entry['level3']}, Level 4: {entry['level4']}"
            timezone_str = entry["timezone"] if entry["timezone"] else st.session_state.hierarchy_data["timezone"]
            codes_str = ", ".join([code for code in entry["codes"] if code])
            
            # Get enabled callout types
            callout_types_str = ", ".join([ct for ct, enabled in entry.get("callout_types", {}).items() if enabled])
            
            # Get callout reasons
            callout_reasons_str = entry.get("callout_reasons", "")
            
            data.append({
                "Tab": "Location Hierarchy", 
                "Section": f"Location Entry #{i+1}", 
                "Response": f"{location_str}, Time Zone: {timezone_str}, Codes: {codes_str}"
            })
            
            # Add matrix data from the integrated callout types
            if entry["level4"] and callout_types_str:
                data.append({
                    "Tab": "Matrix of Locations and CO Types", 
                    "Section": entry["level4"], 
                    "Response": callout_types_str
                })
            
            # Add matrix data from the integrated callout reasons
            if entry["level4"] and callout_reasons_str:
                data.append({
                    "Tab": "Matrix of Locations and Reasons", 
                    "Section": entry["level4"], 
                    "Response": callout_reasons_str
                })
    
    # Add job classifications
    for i, job in enumerate(st.session_state.job_classifications):
        if job["title"]:
            ids_str = ", ".join([id for id in job["ids"] if id])
            data.append({
                "Tab": "Job Classifications",
                "Section": f"{job['title']} ({job['type']})",
                "Response": f"IDs: {ids_str}, Recording: {job['recording'] if job['recording'] else 'Same as title'}"
            })
    
    # Add callout reasons
    if 'selected_callout_reasons' in st.session_state:
        # Load reasons
        callout_reasons = load_callout_reasons()
        selected_reasons = [r for r in callout_reasons if r.get("ID") in st.session_state.selected_callout_reasons]
        
        data.append({
            "Tab": "Callout Reasons",
            "Section": "Selected Reasons",
            "Response": ", ".join([f"{r.get('ID')}: {r.get('Callout Reason Drop-Down Label')}" for r in selected_reasons])
        })
        
        if 'default_callout_reason' in st.session_state and st.session_state.default_callout_reason:
            default_reason = next((r for r in callout_reasons if r.get("ID") == st.session_state.default_callout_reason), None)
            if default_reason:
                data.append({
                    "Tab": "Callout Reasons",
                    "Section": "Default Reason",
                    "Response": f"{default_reason.get('ID')}: {default_reason.get('Callout Reason Drop-Down Label')}"
                })
    
    # Add all other responses
    for key, value in st.session_state.responses.items():
        if not key.startswith("matrix_") and not key.startswith("reason_") and value:  # Skip matrix entries, reason checkboxes, and empty responses
            if "_" in key:
                parts = key.split("_", 1)
                if len(parts) > 1:
                    tab, section = parts
                    data.append({
                        "Tab": tab,
                        "Section": section,
                        "Response": value
                    })
    
    # Create DataFrame and return CSV
    df = pd.DataFrame(data)
    csv = df.to_csv(index=False).encode('utf-8')
    return csv

def export_to_excel():
    """Export data to Excel format with formatting similar to the original SIG"""
    # Use pandas to create an Excel file in memory
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Create a DataFrame for Location Hierarchy
    location_data = []
    for entry in st.session_state.hierarchy_data["entries"]:
        if entry["level1"] or entry["level2"] or entry["level3"] or entry["level4"]:
            location_data.append({
                "Level 1": entry["level1"],
                "Level 2": entry["level2"],
                "Level 3": entry["level3"],
                "Level 4": entry["level4"],
                "Time Zone": entry["timezone"] if entry["timezone"] else st.session_state.hierarchy_data["timezone"],
                "Code 1": entry["codes"][0] if len(entry["codes"]) > 0 else "",
                "Code 2": entry["codes"][1] if len(entry["codes"]) > 1 else "",
                "Code 3": entry["codes"][2] if len(entry["codes"]) > 2 else "",
                "Code 4": entry["codes"][3] if len(entry["codes"]) > 3 else "",
                "Code 5": entry["codes"][4] if len(entry["codes"]) > 4 else ""
            })
    
    # Create a DataFrame for the hierarchy data
    if location_data:
        hierarchy_df = pd.DataFrame(location_data)
        hierarchy_df.to_excel(writer, sheet_name='Location Hierarchy', index=False)
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Location Hierarchy']
        
        # Add formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': ARCOS_RED,
            'font_color': 'white',
            'border': 1
        })
        
        # Apply formatting
        for col_num, value in enumerate(hierarchy_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
    
    # Create a DataFrame for Matrix of Locations and CO Types from the hierarchy data
    matrix_data = []
    for entry in st.session_state.hierarchy_data["entries"]:
        if entry["level4"]:
            row_data = {
                "Location": entry["level4"],
                "Normal": "X" if entry.get("callout_types", {}).get("Normal", False) else "",
                "All Hands on Deck": "X" if entry.get("callout_types", {}).get("All Hands on Deck", False) else "",
                "Fill Shift": "X" if entry.get("callout_types", {}).get("Fill Shift", False) else "",
                "Travel": "X" if entry.get("callout_types", {}).get("Travel", False) else "",
                "Notification": "X" if entry.get("callout_types", {}).get("Notification", False) else "",
                "Notification (No Response)": "X" if entry.get("callout_types", {}).get("Notification (No Response)", False) else ""
            }
            
            matrix_data.append(row_data)
    
    # Add matrix sheet
    if matrix_data:
        matrix_df = pd.DataFrame(matrix_data)
        matrix_df.to_excel(writer, sheet_name='Matrix of CO Types', index=False)
        
        # Format the matrix sheet
        worksheet = writer.sheets['Matrix of CO Types']
        for col_num, value in enumerate(matrix_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
    
    # Create a DataFrame for Matrix of Locations and Reasons from the hierarchy data
    reasons_data = []
    for entry in st.session_state.hierarchy_data["entries"]:
        if entry["level4"] and entry.get("callout_reasons", ""):
            # Create hierarchical path for display
            hierarchy_path = []
            if entry["level1"]:
                hierarchy_path.append(entry["level1"])
            if entry["level2"]:
                hierarchy_path.append(entry["level2"])
            if entry["level3"]:
                hierarchy_path.append(entry["level3"])
            
            path_str = " > ".join(hierarchy_path)
            
            reasons_data.append({
                "Level 1": entry["level1"],
                "Level 2": entry["level2"],
                "Level 3": entry["level3"],
                "Level 4": entry["level4"],
                "Callout Reasons": entry["callout_reasons"]
            })
    
    # Add reasons sheet
    if reasons_data:
        reasons_df = pd.DataFrame(reasons_data)
        reasons_df.to_excel(writer, sheet_name='Matrix of Reasons', index=False)
        
        # Format the reasons sheet
        worksheet = writer.sheets['Matrix of Reasons']
        for col_num, value in enumerate(reasons_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
    
    # Create a DataFrame for Job Classifications
    job_data = []
    for job in st.session_state.job_classifications:
        if job["title"]:
            job_data.append({
                "Type": job["type"],
                "Classification": job["title"],
                "ID 1": job["ids"][0] if len(job["ids"]) > 0 else "",
                "ID 2": job["ids"][1] if len(job["ids"]) > 1 else "",
                "ID 3": job["ids"][2] if len(job["ids"]) > 2 else "",
                "ID 4": job["ids"][3] if len(job["ids"]) > 3 else "",
                "ID 5": job["ids"][4] if len(job["ids"]) > 4 else "",
                "Recording": job["recording"]
            })
    
    if job_data:
        job_df = pd.DataFrame(job_data)
        job_df.to_excel(writer, sheet_name='Job Classifications', index=False)
        
        # Format the job sheet
        worksheet = writer.sheets['Job Classifications']
        for col_num, value in enumerate(job_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
    
    # Create a DataFrame for Callout Reasons
    if 'selected_callout_reasons' in st.session_state:
        callout_reasons = load_callout_reasons()
        selected_reasons = [r for r in callout_reasons if r.get("ID") in st.session_state.selected_callout_reasons]
        
        if selected_reasons:
            reason_data = [{
                "ID": r.get("ID", ""),
                "Callout Reason": r.get("Callout Reason Drop-Down Label", ""),
                "Use?": "X" if r.get("ID") in st.session_state.selected_callout_reasons else "",
                "Default?": "X" if r.get("ID") == st.session_state.default_callout_reason else "",
                "Verbiage": r.get("Verbiage", "")
            } for r in callout_reasons]  # Include all reasons with "Use?" marked
            
            reason_df = pd.DataFrame(reason_data)
            reason_df.to_excel(writer, sheet_name='Callout Reasons', index=False)
            
            # Format the reasons sheet
            worksheet = writer.sheets['Callout Reasons']
            for col_num, value in enumerate(reason_df.columns.values):
                worksheet.write(0, col_num, value, header_format)
    
    # Create a sheet for other responses
    other_data = []
    for key, value in st.session_state.responses.items():
        if not key.startswith("matrix_") and not key.startswith("reason_") and value:  # Skip matrix entries, reason checkboxes and empty responses
            if "_" in key:
                parts = key.split("_", 1)
                if len(parts) > 1:
                    tab, section = parts
                    other_data.append({
                        "Tab": tab,
                        "Section": section,
                        "Response": value
                    })
    
    if other_data:
        other_df = pd.DataFrame(other_data)
        other_df.to_excel(writer, sheet_name='Other Configurations', index=False)
        
        # Format the other sheet
        worksheet = writer.sheets['Other Configurations']
        for col_num, value in enumerate(other_df.columns.values):
            worksheet.write(0, col_num, value, header_format)
    
    # Close the writer and get the output
    writer.close()
    
    # Seek to the beginning of the stream
    output.seek(0)
    
    return output.getvalue()

# ============================================================================
# MAIN APPLICATION FUNCTION
# ============================================================================
def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()
    
    # Generate a unique ID for this session
    import uuid
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    session_id = st.session_state.session_id
    
    # List of tabs for navigation
    tabs = [
        "Location Hierarchy",
        "Trouble Locations",
        "Job Classifications",
        "Callout Reasons",
        "Event Types",
        "Callout Type Configuration",
        "Global Configuration Options",
        "Data and Interfaces",
        "Additions"
    ]
    
    # Display ARCOS logo and title
    col1, col2 = st.columns([1, 5])
    with col1:
        try:
            st.image("https://www.arcos-inc.com/wp-content/uploads/2020/02/ARCOS-RGB-Red.svg", width=150)
        except Exception as e:
            # Fallback if image can't be loaded
            st.write("ARCOS")
            print(f"Error loading logo: {str(e)}")
    
    with col2:
        st.markdown('<p class="main-header">System Implementation Guide Form</p>', unsafe_allow_html=True)
        st.write("Complete your ARCOS configuration with AI assistance")
    
    # Display color key legend
    render_color_key()
    
    # Use radio buttons for tab selection
    st.write("Select a tab:")
    
    # Use a radio group for tab selection
    # Ensure we're using a unique key that includes the session ID
    selected_tab = st.radio(
        label="Select tab:",
        options=tabs,
        index=tabs.index(st.session_state.current_tab) if st.session_state.current_tab in tabs else 0,
        key=f"nav_tabs_{session_id}",
        horizontal=True
    )
    
    # Update current tab if changed
    if selected_tab != st.session_state.current_tab:
        st.session_state.current_tab = selected_tab
        st.rerun()
    
    # Show current tab
    st.write(f"Current Tab: {selected_tab}")
    
    # Export buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export as CSV", key=f"export_csv_{session_id}"):
            csv_data = export_to_csv()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create download link
            st.markdown(
                f'<a href="data:text/csv;base64,{base64.b64encode(csv_data).decode()}" download="arcos_sig_{timestamp}.csv" class="download-button">Download CSV</a>',
                unsafe_allow_html=True
            )
    
    with col2:
        if st.button("Export as Excel", key=f"export_excel_{session_id}"):
            excel_data = export_to_excel()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create download link
            b64 = base64.b64encode(excel_data).decode()
            st.markdown(
                f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="arcos_sig_{timestamp}.xlsx" class="download-button">Download Excel</a>',
                unsafe_allow_html=True
            )
    
    # Add a separator
    st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
    
    # Create a container for the main content area
    content_container = st.container()
    with content_container:
        try:
            # Main content area - render the appropriate tab
            if selected_tab == "Location Hierarchy":
                render_location_hierarchy_form()
            elif selected_tab == "Trouble Locations":
                render_trouble_locations_form()
            elif selected_tab == "Job Classifications":
                render_job_classifications()
            elif selected_tab == "Callout Reasons":
                render_callout_reasons_form()
            elif selected_tab == "Event Types":
                render_event_types_form()
            else:
                # For other tabs, use the generic form renderer
                render_generic_tab(selected_tab)
        except Exception as e:
            st.error(f"Error rendering tab: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    # Add a separator
    st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
    
    # AI Assistant
    st.subheader("AI Assistant")
    
    # Use two columns for the AI assistant
    ai_cols = st.columns([3, 1])
    
    with ai_cols[0]:
        # Chat input with unique key
        user_question = st.text_input("Ask anything about ARCOS configuration:", key=f"user_question_{session_id}")
        
        if st.button("Ask AI Assistant", key=f"ask_ai_{session_id}"):
            if user_question:
                # Get current tab for context
                context = f"The user is working on the ARCOS System Implementation Guide form. They are currently viewing the '{selected_tab}' tab."
                
                # Show spinner while getting response
                with st.spinner("Getting response..."):
                    # Get response from OpenAI
                    response = get_openai_response(user_question, context)
                    
                    # Store in chat history
                    st.session_state.chat_history.append({"role": "user", "content": user_question})
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    with ai_cols[1]:
        # Display chat history
        st.markdown('<p class="section-header">Chat History</p>', unsafe_allow_html=True)
        
        if "chat_history" in st.session_state and st.session_state.chat_history:
            # Show recent messages
            recent_messages = st.session_state.chat_history[-6:]  # Show last 6 messages
            for msg in recent_messages:
                if msg["role"] == "user":
                    st.markdown(f"<div style='background-color: #f0f0f0; padding: 8px; border-radius: 5px; margin-bottom: 8px;'><b>You:</b> {msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='background-color: #e6f7ff; padding: 8px; border-radius: 5px; margin-bottom: 8px;'><b>Assistant:</b> {msg['content']}</div>", unsafe_allow_html=True)
            
            # Clear chat history button
            if st.button("Clear Chat History", key=f"clear_chat_{session_id}"):
                st.session_state.chat_history = []
                st.rerun()
        else:
            st.info("No chat history yet. Ask a question to get started.")

# Run the application
if __name__ == "__main__":
    main()

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================
# This line is critical - it actually runs the application
if __name__ == "__main__":
    main()