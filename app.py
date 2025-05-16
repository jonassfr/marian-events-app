import streamlit as st
import requests
from datetime import datetime
import pytz
import feedparser


st.set_page_config(page_title="Marian Events Selector", layout="wide")
if "selected_events" not in st.session_state:
    st.session_state.selected_events = []

st.markdown("""
<style>
/* Macht rechte Spalte sticky */
.sticky-output {
    position: sticky;
    top: 100px;
    align-self: flex-start;
    background-color: #F9FAFB;
    padding: 1.2rem;
    border: 1px solid #DAD9D6;
    border-radius: 10px;
    box-shadow: 0 0 8px rgba(0,0,0,0.04);
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
    <style>
    .block-container {
        padding: 2rem 2rem 4rem;
        max-width: 900px;
        margin: auto;
    }

    h1 {
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 2.2rem;
        color: #031E51;
    }

    /* Checkbox block */
    .stCheckbox {
        margin-bottom: 0.5rem;
        padding: 0.6rem;
        border-radius: 8px;
        transition: all 0.3s ease;
        background-color: #FAFAFA;
        border: 1px solid #DAD9D6;
    }

    /* Visuelles Feedback bei Hover */
    .stCheckbox:hover {
        background-color: #F0F4FF;
        border-color: #031E51;
    }

    /* Sichtbare Auswahl mit markiertem Kasten */
    input[type="checkbox"]:checked + div {
        background-color: #E8F0FF !important;
        border-left: 5px solid #FDB813 !important;
        padding-left: 12px;
        font-weight: 600;
    }

    /* Buttons */
    .stButton>button, .stDownloadButton>button {
        background-color: #FDB813;
        color: black;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        margin-top: 1rem;
        transition: 0.2s ease-in-out;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #e0a400;
    }
    </style>
""", unsafe_allow_html=True)

# Marian University Logo oben anzeigen
st.image("https://www.marian.edu/images/default-source/_logos/marian-university-logo.png?sfvrsn=0&MaxWidth=100&MaxHeight=100&ScaleUp=false&Quality=High&Method=ResizeFitToAreaArguments&Signature=0B8446F612A6F807C9682F238368F952", width=200)




# === Config ===
JSON_URL = "https://www.marian.edu/events/_data/current-live.json"
RSS_URL = "https://connect.marian.edu/events.rss"  # ✅ das muss rein!
ICAL_URL = "https://connect.marian.edu/events.ics"
MUKNIGHTS_RSS_URL = "https://muknights.com/calendar.ashx/calendar.rss?sport_id=0&_=cmapqlxzs0001359sumhrir9j"
TARGET_LOCATION = "Indianapolis"

# === Functions ===

@st.cache_data
def load_json_events():
    try:
        res = requests.get(JSON_URL)
        res.raise_for_status()
        raw = res.json()
        return raw.get("events", [])
    except Exception as e:
        st.error("Error loading JSON events.")
        return []

@st.cache_data
def load_rss_events():
    import re
    import html
    from bs4 import BeautifulSoup

    feed = feedparser.parse(RSS_URL)
    eastern = pytz.timezone("US/Eastern")
    events = []

    for entry in feed.entries:
        try:
            title = html.unescape(entry.title)
            link = entry.link
            summary = entry.get("summary", "")

            # Parse HTML content of summary
            soup = BeautifulSoup(summary, "html.parser")
            start_tag = soup.find("time", class_="dt-start")

            if not start_tag or not start_tag.has_attr("datetime"):
                st.warning(f"⚠️ Could not extract date from: {title}")
                continue

            dt_str = start_tag["datetime"]  # e.g., "2025-05-15T09:00:00-04:00"
            start = datetime.fromisoformat(dt_str).astimezone(eastern)

            # Try to extract location (fallback if not found)
            location_tag = soup.find("span", class_="p-location")
            location = location_tag.get_text(strip=True) if location_tag else "Indianapolis"

            events.append({
                "title": title,
                "startDate": start.isoformat(),
                "location": location,
                "url": link
            })

        except Exception as err:
            st.error(f"RSS parsing error for '{entry.title}': {err}")
            continue

    return events

@st.cache_data
def load_muknights_rss_events():
    import html
    import re
    from dateutil import parser
    feed = feedparser.parse(MUKNIGHTS_RSS_URL)
    eastern = pytz.timezone("US/Eastern")
    events = []

    for entry in feed.entries:
        try:
            title = html.unescape(entry.get("title", "Untitled"))

            # Entferne Datum & Uhrzeit am Anfang
            title = re.sub(r"^\d{1,2}/\d{1,2}(\s+\d{1,2}:\d{2}\s*[APMapm]{2})?\s*", "", title)
            # Entferne Tags wie [W], [M], [JV], [B]
            title = re.sub(r"\[\s*[A-Za-z]+\s*\]", "", title).strip()

            link = entry.get("link", "")
            location = entry.get("ev_location", "Indianapolis")

            raw_dt = entry.get("ev_localstartdate") or entry.get("ev_startdate")
            if not raw_dt:
                st.warning(f"Skipped event (no start date): {title}")
                continue

            start = parser.isoparse(raw_dt).astimezone(eastern)

            events.append({
                "title": title,
                "startDate": start.isoformat(),
                "location": location,
                "url": link
            })

        except Exception as err:
            st.error(f"❌ Parsing error: {err}")
            continue

    return events


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

            # Extract location with fallback
            location = e.get("location", "").strip()
            if not location:
                location = "Indianapolis"

            # New section
            if date_str != current_day:
                if current_day:
                    output += "</ul>\n"
                output += f"<b>{date_str}</b>\n<ul>"
                current_day = date_str

            if url:
                output += f'<li><a href="{url}">{title}</a><br>{time_str}, {location}</li>\n'
            else:
                output += f'<li>{title}<br>{time_str}, {location}</li>\n'
        except:
            continue

    if not output.endswith("</ul>"):
        output += "</ul>"

    return output.strip()

# === UI ===

st.title("🗓️ Marian Event Selector")
st.info("👉 **After** selecting all needed events please make sure **Connect Events** is selected **before** downloading the HTML output to ensure accurate location details.")

option = st.selectbox(
    "Select event source:",
    [
        "Campus Events (https://www.marian.edu/events/)",
        "Connect Events (https://connect.marian.edu/events)",
        "Muknights Events (https://muknights.com/calendar)"
    ]
)

if option.startswith("Campus Events"):
    data = load_json_events()
    filtered = [
        e for e in data
        if isinstance(e, dict) and TARGET_LOCATION in e.get("filter2", [])
    ]
elif option.startswith("Connect Events"):
    filtered = load_rss_events()
elif option.startswith("Muknights Events"):
    filtered = load_muknights_rss_events()
else:
    filtered = []

if "checkbox_states" not in st.session_state:
    st.session_state.checkbox_states = {}

if "event_lookup" not in st.session_state:
    st.session_state.event_lookup = {}

# 🟦 Layout in zwei Spalten: Events (links) und Output (rechts)
# Neue Spalten-Struktur
left, right = st.columns([2, 1])

with left:
    for event in sorted(filtered, key=lambda x: x["startDate"]):
        title = event.get("title", "Untitled")
        location = event.get("location", "Indianapolis")
        start = datetime.fromisoformat(event["startDate"]).astimezone(pytz.timezone("US/Eastern"))
        date = start.strftime("%A, %B %d")
        time = start.strftime("%I:%M %p").lstrip("0")

        label = f"📅 {date} – {title} ({time}, {location})"
        unique_key = f'{title}_{start.isoformat()}_{event.get("url", "")}'

        st.session_state.event_lookup[unique_key] = event
        checked = st.session_state.checkbox_states.get(unique_key, False)
        checked = st.checkbox(label, key=unique_key, value=checked)
        st.session_state.checkbox_states[unique_key] = checked

# ✅ Session-State aktualisieren mit allen aktuell gesetzten Checkboxen
st.session_state.selected_events = [
    st.session_state.event_lookup[key]
    for key, is_checked in st.session_state.checkbox_states.items()
    if is_checked and key in st.session_state.event_lookup
]

# ✅ Doppelte Events vermeiden (z. B. bei Quellwechsel)
# Priorisiere Events aus Connect

event_priority = {
    "connect.marian.edu": 1,
    "muknights.com": 2,
    "marian.edu": 3
}

def get_source(event):
    url = event.get("url", "").lower()
    for source in event_priority:
        if source in url:
            return source
    return "unknown"


merged = {}
for e in st.session_state.selected_events:
    key = e["title"] + e["startDate"]
    current_source = get_source(e)
    if key not in merged or event_priority[get_source(merged[key])] > event_priority[current_source]:
        merged[key] = e

combined_selected = list(merged.values())


with right:
    st.markdown('<div class="sticky-output">', unsafe_allow_html=True)

    if st.button("❌ Clear all selections"):
        for key in st.session_state.checkbox_states:
            st.session_state.checkbox_states[key] = False
        st.session_state.selected_events = []
    

    if combined_selected:
        st.markdown("### 📝 Formatted HTML Output")
        text_output = format_selected_events(combined_selected)
        st.markdown("### 📧 HTML Newsletter Preview")
        st.markdown(text_output, unsafe_allow_html=True)
        st.download_button("⬇️ Download HTML file", text_output, file_name="selected-events.html")
    else:
        st.info("✅ Select events to generate the HTML output.")

    st.markdown('</div>', unsafe_allow_html=True)



