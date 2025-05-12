import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
from io import BytesIO
from streamlit_js_eval import streamlit_js_eval

# ---------- Theme & Language Toggle ----------
st.set_page_config(layout="wide")

if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "lang" not in st.session_state:
    st.session_state.lang = "English"

# Top bar controls
col1, col2 = st.columns([1, 1])
with col1:
    theme_choice = st.radio("🎨 Theme:", ["Light", "Dark"], horizontal=True)
    st.session_state.theme = theme_choice.lower()
with col2:
    lang_choice = st.radio("🌐 Language:", ["English", "తెలుగు"], horizontal=True)
    st.session_state.lang = "English" if lang_choice == "English" else "Telugu"

if st.session_state.theme == "dark":
    st.markdown("""
        <style>
        body, .stApp {
            background-color: #0e1117;
            color: white !important;
        }

        /* Headings and text */
        h1, h2, h3, h4, h5, h6, p, label, span, div {
            color: white !important;
        }

        /* Input boxes, select, and text area */
        .stTextInput > div > div > input,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"],
        .stRadio > div,
        textarea {
            background-color: #262730;
            color: white !important;
        }

        /* Buttons */
        button[kind="primary"] {
            background-color: #1f77b4;
            color: white;
        }

        /* Download button */
        .stDownloadButton > button {
            background-color: #1f77b4;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)


# ---------- Translations ----------
T = lambda key: {
    "title": {
        "English": "📚 Teacher Transfer Helper Tool",
        "Telugu": "📚 ఉపాధ్యాయ బదిలీ సహాయ సాధనం"
    },
    "select_district": {
        "English": "Select the District & Role",
        "Telugu": "జిల్లా మరియు రోల్ ఎంచుకోండి"
    },
    "choose_location": {
        "English": "Choose Preferred Location Method",
        "Telugu": "ప్రాధాన్య గల ప్రదేశాన్ని ఎంచుకునే పద్ధతి"
    },
    "priority_input": {
        "English": "Enter Category Priority",
        "Telugu": "వర్గ ప్రాధాన్యతను నమోదు చేయండి"
    },
    "process_button": {
        "English": "Find Nearby Schools",
        "Telugu": "దగ్గరలోని పాఠశాలలు కనుగొనండి"
    },
    "download_label": {
        "English": "🔹 Download Full Result as Excel",
        "Telugu": "🔹 ఫలితాన్ని Excel రూపంలో డౌన్‌లోడ్ చేయండి"
    },
}[key][st.session_state.lang]

# ---------- Sidebar Map & Views ----------
data_dir = "data"
st.sidebar.markdown("### Andhra Pradesh Map")
st.sidebar.image("https://contestchacha.com/wp-content/uploads/2022/06/districts-in-Andhra-Pradesh.jpg", use_container_width=True)

def update_view_count():
    count_file = "views.txt"
    try:
        with open(count_file, "r") as f:
            count = int(f.read())
    except FileNotFoundError:
        count = 0
    count += 1
    with open(count_file, "w") as f:
        f.write(str(count))
    return count

view_count = update_view_count()
st.sidebar.markdown(f"👁️ **Total Views:** `{view_count}`")

# ---------- Dataset Handling ----------
def get_available_datasets():
    if not os.path.exists(data_dir):
        return {}
    files = [f for f in os.listdir(data_dir) if f.endswith(".xlsx")]
    labels = [f.replace(".xlsx", "").replace("_", " ").title() for f in files]
    return dict(zip(labels, files))

@st.cache_data
def load_school_data(filename):
    df = pd.read_excel(os.path.join(data_dir, filename), engine="openpyxl")
    return df

def get_user_coords(location_str):
    geolocator = Nominatim(user_agent="teacher-transfer-app")
    location = geolocator.geocode(location_str + ", Andhra Pradesh")
    if location:
        return (location.latitude, location.longitude)
    return None

def compute_sorted_schools(df, user_coords, priority_order):
    df = df.copy().dropna(subset=['Latitude', 'Longitude'])
    df['Distance_km'] = df.apply(lambda row: geodesic(user_coords, (row['Latitude'], row['Longitude'])).km, axis=1)
    df['PriorityIndex'] = df['Category'].apply(lambda c: priority_order.index(c) if c in priority_order else len(priority_order))
    df_sorted = df.sort_values(by=["PriorityIndex", "Distance_km"])
    return df_sorted[['School', 'Mandal', 'Category', 'Distance_km']]

# ---------- Main UI ----------
st.title(T("title"))
st.write("___")

st.subheader(T("select_district"))
datasets = get_available_datasets()
if not datasets:
    st.error(f"No Excel files found in the '{data_dir}' folder.")
    st.stop()

selected_label = st.selectbox("", list(datasets.keys()))
selected_file = datasets[selected_label]
st.write("___")

st.subheader(T("choose_location"))
location_method = st.radio("", ["Enter manually", "Use current location"])
user_coords = None

if location_method == "Enter manually":
    user_location = st.text_input("Enter your preferred location:")
    latitude_input = st.number_input("OR Enter Latitude:", format="%.6f", step=0.0001)
    longitude_input = st.number_input("OR Enter Longitude:", format="%.6f", step=0.0001)

    if user_location:
        coords = get_user_coords(user_location)
        if coords:
            user_coords = coords
            st.success(f"📍 Found: {coords[0]}, {coords[1]}")
        else:
            st.warning("⚠️ Location not found.")
    elif latitude_input and longitude_input:
        user_coords = (latitude_input, longitude_input)
else:
    loc_data = streamlit_js_eval("navigator.geolocation.getCurrentPosition((pos) => pos.coords)", key="get_user_location")
    if loc_data and all(k in loc_data for k in ["latitude", "longitude"]):
        user_coords = (loc_data["latitude"], loc_data["longitude"])
        st.success(f"📍 Current location: {user_coords[0]:.6f}, {user_coords[1]:.6f}")
    else:
        st.warning("⚠️ Could not fetch current location.")

st.write("___")
st.subheader(T("priority_input"))
priority_input = st.text_input("", value="4 3 2 1")
st.write("___")

if st.button(T("process_button")):
    if not user_coords:
        st.error("Please provide a valid location.")
    else:
        with st.spinner("Processing..."):
            try:
                df = load_school_data(selected_file)
                priority_order = list(map(int, priority_input.strip().split()))
                result_df = compute_sorted_schools(df, user_coords, priority_order)
                st.success("Done!")
                st.dataframe(result_df.head(20))

                output = BytesIO()
                result_df.to_excel(output, index=False, engine="openpyxl")
                st.download_button(
                    label=T("download_label"),
                    data=output.getvalue(),
                    file_name="sorted_schools.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("""
<hr>
<footer style="text-align:center; padding: 20px; background-color:#f4f4f4;">
    <p>Developed by Neha</p>
    <p>Contact: <a href="mailto:nehajanaki7788@gmail.com">nehajanaki7788@gmail.com</a></p>
    <p>🙏 Thank you for using the Teacher Transfer Helper Tool!</p>
</footer>
<footer style="text-align:center; padding: 20px; background-color:#f9f9f9;">
    <p><strong>Support Me:</strong> I'm an aspiring tech enthusiast! If you find this tool useful and want to support my journey, feel free to reach out or contribute.</p>
</footer>
""", unsafe_allow_html=True)
