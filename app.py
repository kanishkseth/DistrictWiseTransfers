import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
from io import BytesIO
from streamlit_js_eval import streamlit_js_eval
from geopy.geocoders import Nominatim
# 📂 Path where static data is stored
data_dir = "data"
# 👁️ Track total views
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

# 🟢 Update and display the view count
view_count = update_view_count()
st.sidebar.markdown(f"👁️ **Total Views:** `{view_count}`")

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

# Space for UI enhancements
st.write("___")

# Step 1: Select dataset
st.subheader("Select the District & Role")
datasets = get_available_datasets()
if not datasets:
    st.error(f"No Excel files found in the '{data_dir}' folder.")
    st.stop()

selected_label = st.selectbox("Select your district and transfer type:", list(datasets.keys()))
selected_file = datasets[selected_label]

# Create some space between widgets
st.write("___")

# Step 2: Choose how to enter location
st.subheader("Choose Preferred Location Method")

location_method = st.radio("How would you like to provide location Priority?",
                           options=["Enter manually", "Use current location"])

user_coords = None

if location_method == "Enter manually":
    user_location = st.text_input("Enter your preferred location (e.g., Bapatla, Andhra Pradesh):")
    latitude_input = st.number_input("OR Enter Latitude:", format="%.6f", step=0.0001)
    longitude_input = st.number_input("OR Enter Longitude:", format="%.6f", step=0.0001)

    if user_location:
        try:
            geolocator = Nominatim(user_agent="teacher-transfer")
            location = geolocator.geocode(user_location)
            if location:
                user_coords = (location.latitude, location.longitude)
                st.success(f"📍 Location found: {location.address}")
                st.write(f"Latitude: {location.latitude}, Longitude: {location.longitude}")
            else:
                st.warning("⚠️ Could not find the entered location.")
        except Exception as e:
            st.error(f"Error finding location: {e}")
    elif latitude_input and longitude_input:
        user_coords = (latitude_input, longitude_input)

else:
    loc_data = streamlit_js_eval(
        js_expressions="navigator.geolocation.getCurrentPosition((pos) => pos.coords)",
        key="get_user_location"
    )

    if loc_data and all(k in loc_data for k in ["latitude", "longitude"]):
        latitude_input = loc_data["latitude"]
        longitude_input = loc_data["longitude"]
        st.success(f"📍 Your current location: {latitude_input:.6f}, {longitude_input:.6f}")
        user_coords = (latitude_input, longitude_input)
    else:
        st.warning("⚠️ Could not fetch your location. Try allowing browser permission or enter manually.")

# Space for better UX
st.write("___")

# Step 3: Enter category priority
st.subheader("Enter Category Priority")

default_priority = "4 3 2 1"
priority_input = st.text_input("Enter category priority (e.g., 4 3 2 1):", value=default_priority)

# Space for better UX
st.write("___")

# Step 4: Process button
if st.button("Find Nearby Schools"):
    if not user_location and (latitude_input == 0 or longitude_input == 0):
        st.error("Please enter your preferred location or provide latitude and longitude.")
    else:
        with st.spinner("Processing..."):
            # Determine coordinates based on user input
            if user_location:
                user_coords = get_user_coords(user_location)
            else:
                user_coords = (latitude_input, longitude_input)

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
