import streamlit as st
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Marian Events Selector", layout="wide")

# === Configuration ===
JSON_URL = "https://www.marian.edu/events/_data/current-live.json"
TARGET_LOCATION = "Indianapolis"

# === Load event data ===
@st.cache_data
def load_events():
    try:
        res = requests.get(JSON_URL)
        res.raise_for_status()
        raw = res.json()
        return raw.get("events", [])
    except Exception as e:
        st.error("Error loading events.")
        return []

# === Format selected events as HTML ===
def format_selected_events(events):
    eastern = pytz.timezone("US/Eastern")
    events.sort(key=lambda x: x['startDate'])
    output = ""
    current_day = ""

    for e in events:
        try:
            title = e.get("title", "").strip()
            url = e.get("url", "").strip()
            start = datetime.fromisoformat(e["startDate"]).astimezone(eastern)
            date_str = start.strftime("%A, %B %d")
            time_str = start.strftime("%I:%M %p").lstrip("0")

            # Extract location
            location = ""
            if isinstance(e.get("additionDetails"), list) and len(e["additionDetails"]) > 0:
                loc_text = e["additionDetails"][0].get("text", "").strip()
                if loc_text:
                    location = loc_text
            if not location:
                location = "Indianapolis"  # fallback

            # New day header
            if date_str != current_day:
                if current_day:
                    output += "</ul>\n"
                output += f"<b>{date_str}</b>\n<ul>"
                current_day = date_str

            # Event entry with link
            if url:
                output += f'<li><a href="{url}">{title}</a><br>{time_str}, {location}</li>\n'
            else:
                output += f'<li>{title}<br>{time_str}, {location}</li>\n'
        except Exception as err:
            print("Error:", err)
            continue

    if not output.endswith("</ul>\n"):
        output += "</ul>"

    return output.strip()

# === Main App ===
st.title("🗓️ Marian Event Selector")
st.write("Select events from the **Indianapolis** location and download the formatted HTML for your newsletter.")

data = load_events()

# Filter for Indianapolis events
filtered = [
    e for e in data
    if isinstance(e, dict) and TARGET_LOCATION in e.get("filter2", [])
]

if not filtered:
    st.warning("No events found for Indianapolis.")
else:
    selected = []
    for event in sorted(filtered, key=lambda x: x["startDate"]):
        title = event.get("title", "Untitled")
        location = event.get("location", "")
        start = datetime.fromisoformat(event["startDate"]).astimezone(pytz.timezone("US/Eastern"))
        date = start.strftime("%A, %B %d")
        time = start.strftime("%I:%M %p").lstrip("0")

        label = f"📅 {date} – {title} ({time}, {location})"
        if st.checkbox(label):
            selected.append(event)

    if selected:
        st.markdown("---")
        st.subheader("📝 Formatted HTML Output")
        text_output = format_selected_events(selected)
        st.markdown("### 📧 HTML Newsletter Preview")
        st.markdown(text_output, unsafe_allow_html=True)
        st.download_button("⬇️ Download HTML file", text_output, file_name="indianapolis-events.html")
    else:
        st.info("Select events above to generate the HTML output.")
