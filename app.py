import streamlit as st
import requests
from datetime import datetime
import pytz
import feedparser


st.set_page_config(page_title="Marian Events Selector", layout="wide")

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
    from dateutil import parser  # besser als datetime.strptime für ISO-Formate
    feed = feedparser.parse(MUKNIGHTS_RSS_URL)
    eastern = pytz.timezone("US/Eastern")
    events = []

    for entry in feed.entries:
        try:
            title = html.unescape(entry.get("title", "Untitled"))
            link = entry.get("link", "")
            location = entry.get("ev_location", "Indianapolis")

            # 🕒 Zeit korrekt parsen (z.B. "2025-04-15T18:00:00.0000000Z")
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

if not filtered:
    st.warning("No events found.")
else:
    selected = []
    for event in sorted(filtered, key=lambda x: x["startDate"]):
        title = event.get("title", "Untitled")
        location = event.get("location", "")
        start = datetime.fromisoformat(event["startDate"]).astimezone(pytz.timezone("US/Eastern"))
        date = start.strftime("%A, %B %d")
        time = start.strftime("%I:%M %p").lstrip("0")

        label = f"📅 {date} – {title} ({time}, {location})"
        if st.checkbox(label, key=hash(str(event))):
            selected.append(event)

    if selected:
        st.markdown("---")
        st.subheader("📝 Formatted HTML Output")
        text_output = format_selected_events(selected)
        st.markdown("### 📧 HTML Newsletter Preview")
        st.markdown(text_output, unsafe_allow_html=True)
        st.download_button("⬇️ Download HTML file", text_output, file_name="selected-events.html")
    else:
        st.info("Select events above to generate the HTML output.")


