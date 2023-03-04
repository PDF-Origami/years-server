import sqlite3
import argparse
import bs4.element
import requests

from time import time
from json import dumps
from collections import defaultdict
from datetime import datetime
from bs4 import BeautifulSoup


def events_section_filter(tag):
    return tag.name == 'section' and \
           tag.find('h2') is not None and \
           tag.find('h2').text in ["Events", "Happenings"]


def leaf_li_filter(tag):
    """Return true for <li> that don't contain other events."""
    return tag.name == 'li' and 'ul' not in [child.name for child in tag.contents]


def remove_attributes(li):
    li.attrs = {}
    for child in li.children:
        if child.name == 'a':
            child.attrs = {
                'href': 'https://en.wikipedia.org/wiki/' + child.attrs['href'][2:]
            }
    return li


def add_date(event_li: bs4.element.Tag):
    """Add date to an event <li>.

    When events happen on the same day, they're grouped under a <ul>, and the date
    is only shown in the ancestor. This function copies the date from the ancestor.
    """
    if event_li.parent.parent.name == 'li':
        date = event_li.parent.parent.contents[0].text + " – "
        event_li.insert(0, date)
    return event_li


headings = defaultdict(list)

def save_events(year: int, events, conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE year = ?", (year, ))
    # TODO: fix fetched_at actually being saved_at
    for event in events:
        cursor.execute("INSERT INTO events(year, text, fetched_at, links) "
                       "VALUES (?, ?, ?, ?)", (year, event["text"], datetime.now(), dumps(event["links"])))
    conn.commit()


def get_events(year: int):
    r = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/html/AD_{year}",
        headers={"user-agent": "pdforigami@gmail.com"}
    )
    if r.status_code != 200:
        raise Exception(f"Request failed with status {r.status_code}")

    # Parse HTML
    soup = BeautifulSoup(r.text, "html.parser")
    # Find events section
    root = soup.find(events_section_filter)
    if (root is None):
        print(f"Events section not found for year {year}")
        return []
    # Remove references, "dubious", "citation needed", etc.
    for superscript in root.find_all('sup'):
        superscript.decompose()
    event_elements = root.find_all(leaf_li_filter)
    # Add missing dates where applicable
    event_elements = [add_date(el) for el in event_elements]
    events = []
    for el in event_elements:
        pos = 0
        positions = []
        articles = []
        for i in range(len(el.contents)):
            child = el.contents[i]
            if child.name == "a":
                positions.append(pos)
                positions.append(pos + len(child.text))
                articles.append(child["href"][2:]) # TODO: Use .removeprefix() 
            pos += len(child.text)
        events.append({
            "text": el.text,
            "links": {
                "positions": positions,
                "articles": articles
            }})
    return events

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s  START END [--clean-slate]",
        description="Scrape events for the given years from Wikipedia."
    )
    parser.add_argument('year_range', nargs=2)
    parser.add_argument("--clean-slate", action="store_true")
    return parser


def main(start_year: int, end_year: int, clean_slate=True):
    t0 = time()
    conn = sqlite3.connect("db.sqlite3")
    cursor = conn.cursor()
    if clean_slate:
        print("Dropping old events table")
        cursor.execute("DROP TABLE events")
    cursor.execute("CREATE TABLE IF NOT EXISTS events "
                   "(year INT, text TEXT, fetched_at TEXT, links TEXT)")
    event_count = 0
    year_count = 0
    for year in range(start_year, end_year):
        if year % 100 > 59:
            continue
        events = get_events(year)
        if len(events) > 0:
            year_count += 1
        event_count += len(events)
        save_events(year, events, conn)
    conn.close()
    print(f"Fetched {event_count} events for {year_count} year(s) "
          f"in {time() - t0:.2f}s")


if __name__ == "__main__":
    parser = init_argparse()
    args = parser.parse_args()
    years = [int(x) for x in args.year_range]
    print(f"Fetching events for years [{years[0]}, {years[1]})")
    main(years[0], years[1], clean_slate=args.clean_slate)
