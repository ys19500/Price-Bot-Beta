import os
import csv
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

app = FastAPI()

# -------------------- Chrome Driver Path --------------------
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"  # Update if necessary

# -------------------- Request Schema --------------------
class ScrapeRequest(BaseModel):
    url: str

# -------------------- Chrome Driver --------------------
def get_chrome_driver():
    options = Options()
    #options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

# -------------------- Identify Platform --------------------
def identify_website(url: str):
    if "swiggy" in url:
        return "swiggy"
    elif "zomato" in url:
        return "zomato"
    elif "mystore" in url:
        return "mystore"
    return None

# -------------------- Scrapers --------------------
def scrape_swiggy(url):
    driver = get_chrome_driver()
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'QMaYM')]"))
    )

    try:
        city = driver.find_element(By.XPATH, "//a[contains(@href, '/city/')]/span[@itemprop='name']").text.strip()
    except NoSuchElementException:
        city = "UnknownCity"

    try:
        restaurant = driver.find_element(By.XPATH, "//span[@class='_2vs3E']").text.strip()
    except NoSuchElementException:
        restaurant = "UnknownRestaurant"

    items = []
    products = driver.find_elements(By.XPATH, "//div[contains(@class, 'QMaYM')]")
    for product in products:
        try:
            name = product.find_element(By.XPATH, ".//div[@aria-hidden='true' and contains(@class, 'dwSeRx')]").text.strip()
        except NoSuchElementException:
            name = "N/A"

        mrp = "N/A"
        discounted_price = "N/A"

        try:
            mrp = product.find_element(By.XPATH, ".//div[contains(@class, 'hTspMV')]").text.strip()
        except NoSuchElementException:
            try:
                mrp = product.find_element(By.XPATH, ".//div[contains(@class, 'chixpw')]").text.strip()
            except NoSuchElementException:
                pass

        try:
            discounted_element = product.find_element(By.XPATH, ".//div[contains(@class, 'chixpw')]")
            if mrp != discounted_element.text.strip():
                discounted_price = discounted_element.text.strip()
        except NoSuchElementException:
            pass

        items.append({
            "name": name,
            "MRP": mrp,
            "Discounted Price": discounted_price,
            "Offer": "",
            "code": ""
        })

    driver.quit()
    return items, restaurant, city

def scrape_zomato(url):
    driver = get_chrome_driver()
    driver.get(url)

    try:
        # Wait up to 15 seconds for at least one menu item container to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class= 'sc-nUItV gZWJDT']"))
        )
    except Exception:
        driver.quit()
        raise HTTPException(status_code=504, detail="Zomato page took too long to load.")

    city = "UnknownCity"
    restaurant = "UnknownRestaurant"

    try:
        breadcrumb_links = driver.find_elements(By.XPATH, "//a[contains(@class, 'sc-ukj373-3')]")
        if len(breadcrumb_links) >= 5:
            city = breadcrumb_links[2].get_attribute("title").strip()
            restaurant = breadcrumb_links[4].get_attribute("title").strip()
    except Exception:
        pass

    items = []
    elements = driver.find_elements(By.XPATH, "//div[@class= 'sc-nUItV gZWJDT']")
    for el in elements:
        try:
            price = el.find_element(By.XPATH, ".//span[@class= 'sc-17hyc2s-1 cCiQWA']").text.strip()
            name = el.find_element(By.XPATH, ".//h4[@class = 'sc-cGCqpu chKhYc']").text.strip()
            items.append({"name": name, "price": price})
        except NoSuchElementException:
            continue

    driver.quit()
    return items, restaurant, city


def scrape_mystore(url):
    driver = get_chrome_driver()
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    items = []
    cards = soup.select("div.product-caption-top.mt-auto")
    for card in cards:
        name = card.select_one("a.twoline_ellipsis")
        seller = card.select_one("a.product_seller_name")
        container = card.find_previous("div")
        price_new = container.select_one("span.price-new")
        price_old = container.select_one("span.price-old")
        discount = container.select_one("span.discount-off")

        items.append({
            "name": name.text.strip() if name else "N/A",
            "price": price_new.text.strip() if price_new else "N/A",
            "old_price": price_old.text.strip() if price_old else "N/A",
            "discount": discount.text.strip() if discount else "N/A",
            "seller": seller.text.strip() if seller else "N/A"
        })
    return items

# -------------------- Helpers --------------------
def extract_restaurant_and_city(url):
    url = url.lower()
    parts = url.split('/')
    restaurant = 'unknown_restaurant'
    city = 'unknown_city'

    if "swiggy" in url or "zomato" in url:
        if len(parts) > 4:
            city = parts[3]
        if len(parts) > 5:
            restaurant = parts[5].split('?')[0].replace('-', '_')
    elif "mystore" in url:
        city = "mystore"
        restaurant = parts[2].split('.')[0]
    return restaurant.strip('_'), city.strip('_')

def write_csv(data, platform, restaurant, city):
    city = city.replace(" ", "_").strip()
    restaurant = restaurant.replace(" ", "_").strip()
    platform = platform.lower().strip()

    folder_path = os.path.join("data", city, restaurant)
    os.makedirs(folder_path, exist_ok=True)

    filename = f"{restaurant}_{city}_{platform}.csv"
    full_path = os.path.join(folder_path, filename)

    keys = data[0].keys()
    with open(full_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

    return full_path

# -------------------- Endpoints --------------------
@app.post("/test")
def test_endpoint(request: ScrapeRequest):
    return {"url_received": request.url}

@app.post("/scrape")
def scrape_endpoint(request: ScrapeRequest):
    url = request.url
    platform = identify_website(url)

    if platform == "swiggy":
        data, restaurant, city = scrape_swiggy(url)
    elif platform == "zomato":
        data, restaurant, city = scrape_zomato(url)
    elif platform == "mystore":
        data = scrape_mystore(url)
        restaurant, city = extract_restaurant_and_city(url)
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    if not data:
        raise HTTPException(status_code=404, detail="No data found on the page.")

    csv_path = write_csv(data, platform, restaurant, city)

    return {
        "status": "success",
        "platform": platform,
        "restaurant": restaurant,
        "city": city,
        "csv_path": csv_path,
        "item_count": len(data),
        "data": data
    }
