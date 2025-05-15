import streamlit as st
import requests
from datetime import datetime
import pytz
import feedparser


st.set_page_config(page_title="Marian Events Selector", layout="wide")
if "selected_events" not in st.session_state:
    st.session_state.selected_events = []

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

if not filtered:
    st.warning("No events found.")
else:
    for event in sorted(filtered, key=lambda x: x["startDate"]):
        title = event.get("title", "Untitled")
        location = event.get("location", "")
        start = datetime.fromisoformat(event["startDate"]).astimezone(pytz.timezone("US/Eastern"))
        date = start.strftime("%A, %B %d")
        time = start.strftime("%I:%M %p").lstrip("0")

        label = f"📅 {date} – {title} ({time}, {location})"
        unique_key = f'{title}_{start.isoformat()}_{event.get("url", "")}'

        # 🔁 Event global merken
        st.session_state.event_lookup[unique_key] = event

        # Checkbox anzeigen mit gemerktem Zustand
        checked = st.session_state.checkbox_states.get(unique_key, False)
        checked = st.checkbox(label, key=unique_key, value=checked)
        st.session_state.checkbox_states[unique_key] = checked

    # ✅ Final ausgewählte Events sammeln
    st.session_state.selected_events = [
        st.session_state.event_lookup[key]
        for key, is_checked in st.session_state.checkbox_states.items()
        if is_checked and key in st.session_state.event_lookup
    ]

    # Entferne Duplikate (z. B. beim Hin- und Herwechseln der Quellen)
    unique_events = {e["title"] + e["startDate"]: e for e in st.session_state.selected_events}
    combined_selected = list(unique_events.values())

    if combined_selected:
        st.markdown("---")
        st.subheader("📝 Formatted HTML Output")
        text_output = format_selected_events(combined_selected)
        st.markdown("### 📧 HTML Newsletter Preview")
        st.markdown(text_output, unsafe_allow_html=True)
        st.download_button("⬇️ Download HTML file", text_output, file_name="selected-events.html")
    else:
        st.info("Select events above to generate the HTML output.")


