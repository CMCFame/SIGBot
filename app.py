def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()
    
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
    
    # Create tabs for navigation
    tabs = [
        "Location Hierarchy",
        "Matrix of Locations and CO Types", 
        "Matrix of Locations and Reasons",
        "Trouble Locations",
        "Job Classifications",
        "Callout Reasons",
        "Event Types",
        "Callout Type Configuration",
        "Global Configuration Options",
        "Data and Interfaces",
        "Additions"
    ]
    
    # Create a sidebar for navigation and AI assistant
    st.sidebar.markdown('<p class="section-header">Navigation</p>', unsafe_allow_html=True)
    selected_tab = st.sidebar.selectbox("Select SIG Tab", tabs, index=tabs.index(st.session_state.current_tab))
    
    # Update current tab in session state
    st.session_state.current_tab = selected_tab
    
    # Display progress
    completed_tabs = sum(1 for tab in tabs if any(key.startswith(tab.replace(" ", "_")) for key in st.session_state.responses))
    progress = completed_tabs / len(tabs)
    
    st.sidebar.progress(progress)
    st.sidebar.write(f"Progress: {int(progress * 100)}% complete")
    
    # Export options in sidebar
    st.sidebar.markdown('<p class="section-header">Export Options</p>', unsafe_allow_html=True)
    
    # Using separate buttons for export to avoid nested columns issue
    if st.sidebar.button("Export as CSV"):
        csv_data = export_to_csv()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create download link
        st.sidebar.markdown(
            f'<a href="data:text/csv;base64,{base64.b64encode(csv_data).decode()}" download="arcos_sig_{timestamp}.csv" class="download-button">Download CSV</a>',
            unsafe_allow_html=True
        )
    
    if st.sidebar.button("Export as Excel"):
        excel_data = export_to_excel()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create download link
        b64 = base64.b64encode(excel_data).decode()
        st.sidebar.markdown(
            f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="arcos_sig_{timestamp}.xlsx" class="download-button">Download Excel</a>',
            unsafe_allow_html=True
        )
    
    # Render the AI assistant in the sidebar
    render_ai_assistant_panel()
    
    # Main content area - render the appropriate tab
    try:
        if selected_tab == "Location Hierarchy":
            render_location_hierarchy_form()
        elif selected_tab == "Matrix of Locations and CO Types":
            render_matrix_locations_callout_types()
        elif selected_tab == "Job Classifications":
            render_job_classifications()
        else:
            # For other tabs, use the generic form renderer
            render_generic_tab(selected_tab)
    except Exception as e:
        st.error(f"Error rendering tab: {str(e)}")
        # Print more detailed error for debugging
        import traceback
        print(f"Error details: {traceback.format_exc()}")

# This line is critical - it actually runs the application
if __name__ == "__main__":
    main()def export_to_excel():
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
    
    # Create a DataFrame for Matrix of Locations and CO Types
    if st.session_state.callout_types and [entry["level4"] for entry in st.session_state.hierarchy_data["entries"] if entry["level4"]]:
        # Create the matrix data
        matrix_data = []
        for entry in st.session_state.hierarchy_data["entries"]:
            if entry["level4"]:
                row_data = {
                    "Location": entry["level4"]
                }
                for ct in st.session_state.callout_types:
                    key = f"matrix_{entry['level4']}_{ct}".replace(" ", "_")
                    row_data[ct] = "X" if key in st.session_state.responses and st.session_state.responses[key] else ""
                
                matrix_data.append(row_data)
        
        if matrix_data:
            matrix_df = pd.DataFrame(matrix_data)
            matrix_df.to_excel(writer, sheet_name='Matrix of CO Types', index=False)
            
            # Format the matrix sheet
            worksheet = writer.sheets['Matrix of CO Types']
            for col_num, value in enumerate(matrix_df.columns.values):
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
    
    # Create a sheet for other responses
    other_data = []
    for key, value in st.session_state.responses.items():
        if not key.startswith("matrix_") and value:  # Skip matrix entries already added and empty responses
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
    
    return output.getvalue()def export_to_csv():
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
            
            data.append({
                "Tab": "Location Hierarchy", 
                "Section": f"Location Entry #{i+1}", 
                "Response": f"{location_str}, Time Zone: {timezone_str}, Codes: {codes_str}"
            })
    
    # Add matrix data
    for location in [entry["level4"] for entry in st.session_state.hierarchy_data["entries"] if entry["level4"]]:
        matrix_row = {"Tab": "Matrix of Locations and CO Types", "Section": location, "Response": ""}
        assigned_types = []
        
        for ct in st.session_state.callout_types:
            key = f"matrix_{location}_{ct}".replace(" ", "_")
            if key in st.session_state.responses and st.session_state.responses[key]:
                assigned_types.append(ct)
        
        if assigned_types:
            matrix_row["Response"] = ", ".join(assigned_types)
            data.append(matrix_row)
    
    # Add job classifications
    for i, job in enumerate(st.session_state.job_classifications):
        if job["title"]:
            ids_str = ", ".join([id for id in job["ids"] if id])
            data.append({
                "Tab": "Job Classifications",
                "Section": f"{job['title']} ({job['type']})",
                "Response": f"IDs: {ids_str}, Recording: {job['recording'] if job['recording'] else 'Same as title'}"
            })
    
    # Add all other responses
    for key, value in st.session_state.responses.items():
        if not key.startswith("matrix_") and value:  # Skip matrix entries already added and empty responses
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
    return csvimport streamlit as st
import pandas as pd
import openai
import json
import io
from datetime import datetime
import base64

# Initialize OpenAI client - using a try/except to handle cases where the API key isn't set
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

# Set page configuration
st.set_page_config(
    page_title="ARCOS SIG Form",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        # Initialize with some sample data
        st.session_state.hierarchy_data = {
            "levels": ["Level 1", "Level 2", "Level 3", "Level 4"],
            "labels": ["Parent Company", "Business Unit", "Division", "OpCenter"],
            "entries": [
                {"level1": "", "level2": "", "level3": "", "level4": "", "timezone": "", "codes": ["", "", "", "", ""]}
            ],
            "timezone": "ET / CT / MT / AZ / PT"
        }
        
    if 'callout_types' not in st.session_state:
        st.session_state.callout_types = ["Normal", "All Hands on Deck", "Fill Shift", "Notification", "Notification (No Response)"]
    
    if 'callout_reasons' not in st.session_state:
        st.session_state.callout_reasons = ["Gas Leak", "Gas Fire", "Gas Emergency", "Car Hit Pole", "Wires Down"]

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

def render_location_hierarchy_form():
    """Render the Location Hierarchy form with interactive elements"""
    st.markdown('<p class="tab-header">Location Hierarchy - 1</p>', unsafe_allow_html=True)
    
    # Display descriptive text
    with st.expander("Instructions", expanded=False):
        st.markdown("""
        In ARCOS, your geographical service territory will be represented by a 4-level location hierarchy. You may refer to each Level by changing the Label to suit your requirements. The breakdown doesn't have to be geographical. Different business functions may also be split into different Level 2 or Level 3 locations.
        
        **Location names must contain a blank space per 25 contiguous characters.** Example: the hyphenated village of "Sutton-under-Whitestonecliffe" in England would be considered invalid (29 contiguous characters). Sutton under Whitestonecliffe would be valid. The max length for a location name is 50 characters.
        
        **Each Level 4 entry must have an accompanying Location Code.** This code can be from your HR system or something you create. It is important to make sure each code and each Location Name (on all levels) is unique. A code can be any combination of numbers and letters.
        """)
    
    # Create the main form content
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Level labels editing
        st.markdown('<p class="section-header">Level Labels</p>', unsafe_allow_html=True)
        
        cols = st.columns(4)
        new_labels = st.session_state.hierarchy_data["labels"].copy()
        
        for i, col in enumerate(cols):
            with col:
                new_label = st.text_input(f"Level {i+1} Label", 
                                         value=st.session_state.hierarchy_data["labels"][i],
                                         key=f"label_{i}")
                new_labels[i] = new_label
        
        st.session_state.hierarchy_data["labels"] = new_labels
        
        # Hierarchy table with interactive editing
        st.markdown('<p class="section-header">Location Hierarchy Structure</p>', unsafe_allow_html=True)
        
        # Add entry button
        if st.button("➕ Add New Location Entry"):
            st.session_state.hierarchy_data["entries"].append(
                {"level1": "", "level2": "", "level3": "", "level4": "", "timezone": "", "codes": ["", "", "", "", ""]}
            )
        
        # Time zone selection for the whole company
        timezone_options = ["ET", "CT", "MT", "AZ", "PT"]
        default_timezone = st.text_input("Default Time Zone (if your company is in one time zone)", 
                                       value=st.session_state.hierarchy_data["timezone"])
        st.session_state.hierarchy_data["timezone"] = default_timezone
        
        # Create editable table of hierarchy entries
        for i, entry in enumerate(st.session_state.hierarchy_data["entries"]):
            st.markdown(f"<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            st.markdown(f"<p><b>Location Entry #{i+1}</b></p>", unsafe_allow_html=True)
            
            # Level 1-4 inputs in a row
            level_cols = st.columns([5, 5, 5, 5])
            
            with level_cols[0]:
                entry["level1"] = st.text_input("Level 1", value=entry["level1"], key=f"lvl1_{i}")
            with level_cols[1]:
                entry["level2"] = st.text_input("Level 2", value=entry["level2"], key=f"lvl2_{i}")
            with level_cols[2]:
                entry["level3"] = st.text_input("Level 3", value=entry["level3"], key=f"lvl3_{i}")
            with level_cols[3]:
                entry["level4"] = st.text_input("Level 4", value=entry["level4"], key=f"lvl4_{i}")
            
            # Time Zone in a new row
            timezone_col = st.columns([1])[0]
            with timezone_col:
                entry["timezone"] = st.text_input("Time Zone", value=entry.get("timezone", ""), key=f"tz_{i}",
                                               placeholder=st.session_state.hierarchy_data["timezone"])
            
            # Location codes (only editable if Level 4 is filled)
            if entry["level4"]:
                st.markdown("<b>Location Codes</b> (up to 5)", unsafe_allow_html=True)
                # Create a single row of columns for the codes
                code_cols = st.columns(5)
                for j in range(5):
                    with code_cols[j]:
                        if j < len(entry["codes"]):
                            entry["codes"][j] = st.text_input(f"Code {j+1}", value=entry["codes"][j], key=f"code_{i}_{j}")
                        else:
                            # Ensure we have 5 codes
                            while len(entry["codes"]) <= j:
                                entry["codes"].append("")
                            entry["codes"][j] = st.text_input(f"Code {j+1}", value="", key=f"code_{i}_{j}")
            else:
                st.info("Enter Level 4 to add location codes")
            
            # Delete button
            if st.button("🗑️ Remove", key=f"del_{i}"):
                st.session_state.hierarchy_data["entries"].pop(i)
                st.experimental_rerun()
    
    with col2:
        # Preview the hierarchy as a tree
        st.markdown('<p class="section-header">Hierarchy Preview</p>', unsafe_allow_html=True)
        
        def generate_hierarchy_preview():
            preview = []
            for entry in st.session_state.hierarchy_data["entries"]:
                if entry["level1"]:
                    preview.append(f"• {entry['level1']}")
                    if entry["level2"]:
                        preview.append(f"  • {entry['level2']}")
                        if entry["level3"]:
                            preview.append(f"    • {entry['level3']}")
                            if entry["level4"]:
                                preview.append(f"      • {entry['level4']}")
            return "\n".join(preview)
        
        st.code(generate_hierarchy_preview())
        
        # Help section
        st.markdown('<p class="section-header">Need Help?</p>', unsafe_allow_html=True)
        help_topic = st.selectbox(
            "Select topic for help",
            ["Location Names", "Location Codes", "Time Zones", "Location Hierarchy", "Best Practices"]
        )
        
        if st.button("Get Help"):
            help_query = f"Explain in detail what I need to know about {help_topic} when configuring the Location Hierarchy in ARCOS. Include examples and best practices."
            with st.spinner("Loading help..."):
                help_response = get_openai_response(help_query)
                st.session_state.chat_history.append({"role": "user", "content": f"Help with {help_topic}"})
                st.session_state.chat_history.append({"role": "assistant", "content": help_response})
            
            st.info(help_response)

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
                            st.experimental_rerun()
        
        # Add new callout type - in a separate row
        st.markdown('<p class="section-header">Add New Callout Type</p>', unsafe_allow_html=True)
        add_cols = st.columns([3, 1])
        with add_cols[0]:
            new_callout = st.text_input("New Callout Type Name", key="new_callout")
        with add_cols[1]:
            if st.button("Add"):
                if new_callout and new_callout not in st.session_state.callout_types:
                    st.session_state.callout_types.append(new_callout)
                    st.experimental_rerun()
        
        # Matrix configuration
        st.markdown('<p class="section-header">Callout Types by Location Matrix</p>', unsafe_allow_html=True)
        
        # Create a DataFrame to represent the matrix
        matrix_data = []
        
        # Add entries from location hierarchy
        for entry in st.session_state.hierarchy_data["entries"]:
            if entry["level4"]:  # Only Level 4 locations need callout type assignments
                location_name = entry["level4"]
                row_data = {"Location": location_name}
                
                # Add a column for each callout type
                for ct in st.session_state.callout_types:
                    key = f"matrix_{location_name}_{ct}".replace(" ", "_")
                    if key not in st.session_state.responses:
                        st.session_state.responses[key] = False
                    row_data[ct] = st.session_state.responses[key]
                
                matrix_data.append(row_data)
        
        # Convert to DataFrame
        if matrix_data:
            # Display each location in its own section
            for i, row in enumerate(matrix_data):
                location = row["Location"]
                st.write(f"**{location}**")
                
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
                                key = f"matrix_{location}_{ct}".replace(" ", "_")
                                st.session_state.responses[key] = st.checkbox(
                                    ct, 
                                    value=row.get(ct, False), 
                                    key=key
                                )
                
                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        else:
            st.warning("Add Level 4 locations in the Location Hierarchy tab first to configure this matrix.")
    
    with col2:
        # Preview matrix as a table
        st.markdown('<p class="section-header">Matrix Preview</p>', unsafe_allow_html=True)
        
        if matrix_data:
            # Create a display version of the matrix
            preview_data = []
            for row in matrix_data:
                display_row = {"Location": row["Location"]}
                for ct in st.session_state.callout_types:
                    display_row[ct] = "X" if row.get(ct, False) else ""
                preview_data.append(display_row)
            
            preview_df = pd.DataFrame(preview_data)
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
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Add new job classification button
        if st.button("➕ Add Job Classification"):
            st.session_state.job_classifications.append(
                {"type": "", "title": "", "ids": ["", "", "", "", ""], "recording": ""}
            )
        
        # Display and edit job classifications
        for i, job in enumerate(st.session_state.job_classifications):
            st.markdown(f"<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            st.markdown(f"<p><b>Job Classification #{i+1}</b></p>", unsafe_allow_html=True)
            
            # First row with type and title
            type_title_cols = st.columns([2, 3])
            with type_title_cols[0]:
                job["type"] = st.selectbox(
                    "Type", 
                    ["", "Journeyman", "Apprentice"], 
                    index=["", "Journeyman", "Apprentice"].index(job["type"]) if job["type"] in ["", "Journeyman", "Apprentice"] else 0,
                    key=f"job_type_{i}"
                )
            with type_title_cols[1]:
                job["title"] = st.text_input("Job Classification Title", value=job["title"], key=f"job_title_{i}")
            
            # Second row with IDs
            st.markdown("<p><b>Job Classification IDs</b> (up to 5)</p>", unsafe_allow_html=True)
            # Create a new row for IDs
            id_cols = st.columns(5)
            for j in range(5):
                with id_cols[j]:
                    # Ensure we have enough id slots
                    while len(job["ids"]) <= j:
                        job["ids"].append("")
                    job["ids"][j] = st.text_input(f"ID {j+1}", value=job["ids"][j], key=f"job_id_{i}_{j}")
            
            # Third row with recording - in its own row
            recording_col = st.columns([1])[0]  # Single column for recording
            with recording_col:
                job["recording"] = st.text_input(
                    "Recording Verbiage (what should be spoken during callout)", 
                    value=job["recording"], 
                    key=f"job_rec_{i}",
                    help="Leave blank if same as Job Title"
                )
            
            # Delete button
            if st.button("🗑️ Remove", key=f"del_job_{i}"):
                st.session_state.job_classifications.pop(i)
                st.experimental_rerun()
    
    with col2:
        # Preview the job classifications
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
        
        # Help section
        st.markdown('<p class="section-header">Need Help?</p>', unsafe_allow_html=True)
        help_topic = st.selectbox(
            "Select topic for help",
            ["Job Classifications", "Journeyman vs Apprentice", "Job IDs", "Recording Verbiage"]
        )
        
        if st.button("Get Help"):
            help_query = f"Explain in detail what I need to know about {help_topic} when configuring Job Classifications in ARCOS. Include examples and best practices."
            with st.spinner("Loading help..."):
                help_response = get_openai_response(help_query)
                st.session_state.chat_history.append({"role": "user", "content": f"Help with {help_topic}"})
                st.session_state.chat_history.append({"role": "assistant", "content": help_response})
            
            st.info(help_response)

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
            
            # Get response from OpenAI
            with st.sidebar.spinner("Getting response..."):
                response = get_openai_response(user_question, context)
                
                # Store in chat history
                st.session_state.chat_history.append({"role": "user", "content": user_question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
    
    # Display chat history
    st.sidebar.markdown('<p class="section-header">Chat History</p>', unsafe_allow_html=True)
    
    chat_container = st.sidebar.container()
    
    with chat_container:
        # Show up to 10 most recent messages
        recent_messages = st.session_state.chat_history[-10:]
        for message in recent_messages:
            if message["role"] == "user":
                st.sidebar.markdown(f"<div style='background-color: #f0f0f0; padding: 8px; border-radius: 5px; margin-bottom: 8px;'><b>You:</b> {message['content']}</div>", unsafe_allow_html=True)
            else:
                st.sidebar.markdown(f"<div style='background-color: #e6f7ff; padding: 8px; border-radius: 5px; margin-bottom: 8px;'><b>Assistant:</b> {message['content']}</div>", unsafe_allow_html=True)
    
    # Clear chat history button
    if st.sidebar.button("Clear Chat History", key="clear_chat"):
        st.session_state.chat_history = []
        st.experimental_rerun()