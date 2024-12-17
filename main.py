import time
import pymysql
import datetime
from datetime import datetime
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)

# connect aal baase donne
conn = pymysql.connect(
    db="soc",  # ism l base
    user="root",  # ism l user 
    password="ala123",  # ism l password talqahoum l qol fl west l projet mtaa spring application.yaml
    host="localhost",  # khalaeha localhost 
    port=3306  # numro l port ili tekhdem bih
)
cur = conn.cursor()

# Configure ChromeDriver path and options
options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--disable-blink-features")
options.add_argument("--disable-blink-features=AutomationControlled")
# options.add_argument("--headless")  # Uncomment this line to run in headless mode
options.add_argument('--ignore-certificate-errors')
options.add_argument('--allow-running-insecure-content')
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36")

service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service, options=options)


json_file = "combined_scraped_jobs.json"
csv_file = "combined_scraped_jobs.csv"
scraped_data = []

# awel site  - emploi.nat.tn
start_url_1 = 'https://www.emploi.nat.tn/fo/Fr/global.php?page=164&idgrpspec=true&FormLinks_Sorting=7&FormLinks_Sorted=7'

def scrape_emploi_nat():
    driver.get(start_url_1)
    time.sleep(2)  

    job_count = 0
    max_jobs = 25

    while job_count < max_jobs:
        print("Scraping job listings from emploi.nat.tn...")
        job_rows = driver.find_elements(By.CSS_SELECTOR, 'tr.emp')

        for row in job_rows:
            if job_count >= max_jobs:
                break

            try:
                profession = row.find_element(By.CSS_SELECTOR, "td.profession").get_attribute("textContent").strip()
                posts = row.find_element(By.CSS_SELECTOR, "td.poste:not([style*='display:none'])").get_attribute("textContent").strip()
                lieu = row.find_element(By.CSS_SELECTOR, "td.service").get_attribute("textContent").strip()
                date = row.find_element(By.CSS_SELECTOR, "td.status.sorting_1").get_attribute("textContent").strip()
                link_element = row.find_element(By.CSS_SELECTOR, "td.profession a")

                if not profession or not posts or not lieu or not date:
                    print("Skipping job offer due to missing critical attribute.")
                    continue

                job_data = scrape_job_details(profession, posts, lieu, date, link_element)
                if job_data:
                    scraped_data.append(job_data)
                    save_to_database(job_data)
                    job_count += 1
            except NoSuchElementException:
                print("Skipping job offer due to missing element in the row.")
                continue

        if job_count >= max_jobs:
            break

        # Handle pagination - click next page
        try:
            next_button = driver.find_element(By.ID, 'menuTable_next')
            if 'ui-state-disabled' in next_button.get_attribute('class'):
                print("Next button is disabled. No more pages to scrape.")
                break
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(2)
        except (NoSuchElementException, TimeoutException, ElementClickInterceptedException, ElementNotInteractableException) as e:
            print(f"Pagination failed or no more pages available: {e}.")
            break

def scrape_job_details(profession, posts, lieu, date, link_element, retries=3):
    for attempt in range(retries):
        try:
            driver.execute_script("arguments[0].click();", link_element)
            WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div#detail")))

            profil = driver.find_element(By.XPATH, "//p[b[contains(text(), 'Votre Profil')]]/following-sibling::table").text.strip()
            mission = driver.find_element(By.XPATH, "//p[b[contains(text(), 'Votre mission')]]/following-sibling::table").text.strip()

            try:
                contact_info = driver.find_element(By.XPATH, "//div[@class='panel panel-info']//div[@align='center']").text.strip()
            except NoSuchElementException:
                contact_info = "N/A"

            details = f"Lieu: {lieu}\nProfil: {profil}\nMission: {mission}"

#story l data 
            job_data = {
                'source': 'emploi.nat.tn',
                'title': profession,
                'nb_posts': posts,
                'post_date': date,  
                'description': details,
                'contact': contact_info
            }

            return job_data
        except (StaleElementReferenceException, TimeoutException) as e:
            time.sleep(2)
            continue
        except NoSuchElementException:
            return None
        finally:
            try:
                close_button = driver.find_element(By.CSS_SELECTOR, "button.close-modal")
                close_button.click()
            except NoSuchElementException:
                pass
    return None



def save_to_database(job_data):
    # Generate UUID makench bch yaaml error
    cur.execute("SELECT MAX(id) FROM job_offer")
    result = cur.fetchone()
    max_id = result[0] if result[0] is not None else 0
    job_id = max_id + 1

    
    timestamp = datetime.now()

   
    description = job_data.get('description', '')
    if len(description) > 5000:
        description = description[:5000]

    # l faza hethi bch tsob beha f west l base ahawka 
    insert_query = """
    INSERT INTO job_offer (id, source, title, nb_posts, post_date, contact)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    # Extract values
    values = (
        job_id,  # Insert the generated job ID
        job_data.get('source'),
        job_data.get('title'),
        job_data.get('nb_posts'),
        job_data.get('post_date'),  # Use the post_date as a string
        job_data.get('contact', '')
    )
    
    cur.execute(insert_query, values)
    conn.commit()

# Scrape all pages of both websites
try:
    scrape_emploi_nat()
    
finally:
    driver.quit()
    cur.close()
    conn.close()