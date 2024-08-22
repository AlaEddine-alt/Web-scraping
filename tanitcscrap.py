import time
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
import pickle

# Initialize undetected ChromeDriver
options = uc.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = uc.Chrome(options=options)

# JSON file to store scraped data
json_file = "tanitjobs_scraped_data.json"
scraped_data = []

# Cookies file for session persistence
cookies_file = "tanitjobs_cookies.pkl"

# Start URL
start_url = "https://www.tanitjobs.com/jobs/"

def load_cookies():
    try:
        with open(cookies_file, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
        print("Cookies loaded.")
    except FileNotFoundError:
        print("Cookies file not found. Proceeding without cookies.")

def save_cookies():
    with open(cookies_file, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print("Cookies saved.")

def scrape_jobs():
    driver.get(start_url)
    
    # Load cookies if available
    load_cookies()
    driver.refresh()

    # Check if CAPTCHA is present
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="checkbox"]'))
        )
        input("Please solve the CAPTCHA manually, then press Enter to continue...")
    except TimeoutException:
        print("No CAPTCHA detected.")

    # Save cookies after CAPTCHA is solved
    save_cookies()

    # Wait for page to load fully
    time.sleep(5)  # Increase this if necessary

    # Take a screenshot for debugging
    driver.save_screenshot('page_debug.png')
    print("Screenshot saved as page_debug.png")

    while True:
        print("Scraping job listings from the current page...")
        
        try:
            # Wait for job listings to load
            job_listings = WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'article.listing-item'))
            )

            for job in job_listings:
                try:
                    job_title = job.find_element(By.CSS_SELECTOR, 'div.media-heading a').text.strip()
                    company = job.find_element(By.CSS_SELECTOR, 'span.listing-item__info--item-company').text.strip()
                    location = job.find_element(By.CSS_SELECTOR, 'span.listing-item__info--item-location').text.strip()
                    job_url = job.find_element(By.CSS_SELECTOR, 'div.media-heading a').get_attribute('href')

                    job_data = {
                        'title': job_title,
                        'company': company,
                        'location': location,
                        'url': job_url
                    }
                    scraped_data.append(job_data)
                    print(f"Scraped Job: {job_data}")

                except NoSuchElementException as e:
                    print(f"Failed to scrape a job listing: {e}")
                    continue

        except TimeoutException:
            print("Job listings did not load properly. Check the screenshot.")
            break
        
        # Handle pagination
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[aria-label="Next"]'))
            )

            if 'disabled' in next_button.get_attribute('class'):
                print("Next button is disabled. Scraping complete.")
                break

            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            next_button.click()
            time.sleep(2)  # Random delay to simulate human behavior

        except (NoSuchElementException, TimeoutException, ElementClickInterceptedException, StaleElementReferenceException) as e:
            print(f"Pagination failed or no more pages available: {e}.")
            break

    return scraped_data

try:
    job_offers = scrape_jobs()
    print(f"Total jobs scraped: {len(job_offers)}")
finally:
    driver.quit()

    # Save the scraped data to a JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=4)
    print(f"Scraped data has been saved to {json_file}.")
