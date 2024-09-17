import time
import json
from playwright.sync_api import sync_playwright

json_file = "scraped_events_playwright.json"
scraped_data = []

# Event Website URLs
start_url_1 = 'https://www.meetup.com/find/events/'

def scrape_meetup():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            page.goto(start_url_1, timeout=120000)  # Set a 2-minute timeout
            print("Scraping Meetup...")

            # Wait for the main event card to load
            page.wait_for_selector('div[data-testid="categoryResults-eventCard"]', timeout=60000)

            # Scroll to load more events, handling infinite scrolling
            max_scroll_attempts = 5
            scroll_pause_time = 2  # seconds
            last_height = page.evaluate("document.body.scrollHeight")

            for attempt in range(max_scroll_attempts):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(scroll_pause_time)

                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    print("Reached the bottom of the page or no more events loaded.")
                    break
                last_height = new_height

            # Scraping the event cards after scrolling
            event_rows = page.query_selector_all('div[data-testid="categoryResults-eventCard"]')
            if not event_rows:
                print("No event cards found!")
                return

            for row in event_rows:
                try:
                    # Extract the event link
                    event_link_element = row.query_selector('a.w-full.cursor-pointer.hover\\:no-underline')
                    event_link = event_link_element.get_attribute('href') if event_link_element else "No link available"

                    # Extract other relevant data (like title, date, location) - modify these selectors as needed
                    title = row.query_selector('div.someTitleClass').inner_text().strip() if row.query_selector('div.someTitleClass') else "No title available"
                    date = row.query_selector('time').inner_text().strip() if row.query_selector('time') else "No date available"
                    location = row.query_selector('span.someLocationClass').inner_text().strip() if row.query_selector('span.someLocationClass') else "No location available"

                    event_data = {
                        'title': title,
                        'date': date,
                        'location': location,
                        'event_link': event_link
                    }

                    scraped_data.append(event_data)
                    save_to_json(scraped_data)

                except Exception as e:
                    print(f"Error scraping event row: {e}")
                    continue

        except Exception as e:
            print(f"Error loading Meetup: {e}")

        finally:
            browser.close()

def save_to_json(data):
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

scrape_meetup()
