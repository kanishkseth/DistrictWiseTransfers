import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
from io import BytesIO

# 📂 Path where static data is stored
data_dir = "data"

# ⚖️ All available datasets (assuming naming convention like guntur_sgt.xlsx, guntur_sa.xlsx)
def get_available_datasets():
    if not os.path.exists(data_dir):
        return {}
    files = [f for f in os.listdir(data_dir) if f.endswith(".xlsx")]
    labels = [f.replace(".xlsx", "").replace("_", " ").title() for f in files]
    return dict(zip(labels, files))

# 🔍 Geocode user's preferred location
def get_user_coords(location_str):
    geolocator = Nominatim(user_agent="teacher-transfer-app")
    location = geolocator.geocode(location_str + ", Andhra Pradesh")
    if location:
        return (location.latitude, location.longitude)
    else:
        return None

# 📆 Load school data for a district
@st.cache_data
def load_school_data(filename):
    df = pd.read_excel(os.path.join(data_dir, filename), engine="openpyxl")
    return df

# 🚀 Compute distances and return sorted schools
def compute_sorted_schools(df, user_coords, priority_order):
    df = df.copy()
    df = df.dropna(subset=['Latitude', 'Longitude'])
    df['Distance_km'] = df.apply(lambda row: geodesic(user_coords, (row['Latitude'], row['Longitude'])).km, axis=1)
    df['PriorityIndex'] = df['Category'].apply(lambda c: priority_order.index(c) if c in priority_order else len(priority_order))
    df_sorted = df.sort_values(by=["PriorityIndex", "Distance_km"])
    return df_sorted[['School', 'Mandal', 'Category', 'Distance_km']]

# 🚤 Streamlit UI
st.title("📚 Teacher Transfer Helper Tool")

# Step 1: Select dataset
datasets = get_available_datasets()
if not datasets:
    st.error(f"No Excel files found in the '{data_dir}' folder.")
    st.stop()

selected_label = st.selectbox("Select your district and transfer type:", list(datasets.keys()))
selected_file = datasets[selected_label]

# Step 2: Enter preferred location
user_location = st.text_input("Enter your preferred location (e.g., Bapatla, Andhra Pradesh):")

# Step 3: Enter category priority
default_priority = "4 3 2 1"
priority_input = st.text_input("Enter category priority (e.g., 4 3 2 1):", value=default_priority)

# Step 4: Process button
if st.button("Find Nearby Schools"):
    if not user_location:
        st.error("Please enter your preferred location.")
    else:
        with st.spinner("Processing..."):
            user_coords = get_user_coords(user_location)
            if not user_coords:
                st.error("Could not find coordinates for the location. Try a more specific name.")
            else:
                try:
                    df = load_school_data(selected_file)
                    try:
                        priority_order = list(map(int, priority_input.strip().split()))
                    except ValueError:
                        st.error("Invalid category priority format. Please enter numbers like: 4 3 2 1")
                        st.stop()

                    result_df = compute_sorted_schools(df, user_coords, priority_order)

                    # Download option
                    st.success("Done! Sorted results are ready.")
                    st.dataframe(result_df.head(20))

                    # Convert to Excel for download
                    output = BytesIO()
                    result_df.to_excel(output, index=False, engine="openpyxl")
                    st.download_button(
                        label="🔹 Download Full Result as Excel",
                        data=output.getvalue(),
                        file_name="sorted_schools.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Error processing file: {e}")
# Add "Help the Creator" section in the footer
st.markdown("""
    <hr>
    <footer style="text-align:center; padding: 20px; background-color:#f4f4f4;">
        <p>Developed by Neha</p>
        <p>For further data analytics or inquiries, feel free to reach out: <a href="mailto:nehajanaki7788@gmail.com">nehajanaki7788@gmail.com</a></p>
        <p>Thank you for using the Teacher Transfer Helper Tool!</p>
    </footer>
    <hr>
    <footer style="text-align:center; padding: 20px; background-color:#f9f9f9;">
        <p><strong>Support Me:</strong> I'm an aspiring tech enthusiast! If you find this tool useful and want to support my journey, feel free to reach out or contribute.</p>
    </footer>
    """, unsafe_allow_html=True)
