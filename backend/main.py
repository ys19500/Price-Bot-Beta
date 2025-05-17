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
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    TimeoutException
)
from bs4 import BeautifulSoup

app = FastAPI()

# -------------------- Chrome Driver Path --------------------
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"  

# -------------------- Request Schema --------------------
class ScrapeRequest(BaseModel):
    url: str

# -------------------- Chrome Driver --------------------
def get_chrome_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    
    service = Service(os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver"))
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

class SwiggyDiscountCouponExtractor:
    def __init__(self, driver):
        self.driver = driver


    def extract_discounts_and_coupons(self):
        discounts, coupons = [], []

        try:
            print("Finding offer cards...")
            cards = self.driver.find_elements(By.XPATH, "//div[starts-with(@data-testid, 'offer-card-container-')]")
            print(f"Found {len(cards)} offer cards.")

            for i in range(len(cards)):
                try:
                    cards = self.driver.find_elements(By.XPATH, "//div[starts-with(@data-testid, 'offer-card-container-')]")
                    card = cards[i]

                    self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                    time.sleep(0.5)
                    print(f"Card {i+1} text: {card.text.strip()[:80]}")


                    try:
                        card.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", card)
                    time.sleep(2)

                    print(f"Clicked card {i+1}")

                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'igolxO')]"))
                        )
                        time.sleep(0.5)

                        heading_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'xtIpQ')]")
                        for el in heading_elements:
                            text = el.text.strip()
                            if text and text not in discounts:
                                discounts.append(text)

                        coupon_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'hHZVJN')]")
                        for el in coupon_elements:
                            text = el.text.strip()
                            if text and text not in coupons:
                                coupons.append(text)

                        close_btn = self.driver.find_element(By.XPATH, "//div[contains(@class, 'dnGnZy') and @aria-hidden='true']")
                        close_btn.click()
                        time.sleep(0.5)
                    except TimeoutException:
                        print(f"Timeout waiting for modal content on card {i+1}.")
                        close_btn = self.driver.find_element(By.XPATH, "//div[contains(@class, 'dnGnZy') and @aria-hidden='true']")
                        close_btn.click()
                        time.sleep(0.5)


                except Exception as e:
                    print(f"Error processing card {i+1}: {repr(e)}")
                    

        except Exception as e:
            print("Error during overall coupon extraction:", repr(e))

        return discounts, coupons



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
        })

    
    discount_coupon_extractor = SwiggyDiscountCouponExtractor(driver)
    discounts, coupons = discount_coupon_extractor.extract_discounts_and_coupons()

    driver.quit()
    return items, restaurant, city, discounts, coupons


def scrape_zomato(url):
    driver = get_chrome_driver()
    driver.get(url)

    try:
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
            items.append({"name": name, "MRP": price})
        except NoSuchElementException:
            continue

    driver.quit()
    return items, restaurant, city, [], []  # No discounts or coupons for Zomato

def scrape_mystore(url):
    driver = get_chrome_driver()
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Extract restaurant name
    restaurant_tag = soup.select_one("h1.catalog-title.m-0.fw-semibold.h2")
    restaurant = restaurant_tag.text.strip() if restaurant_tag else "UnknownRestaurant"

    # Extract city name
    city_tag = soup.select_one("div.seller-caption-top")
    city = city_tag.text.strip() if city_tag else "UnknownCity"

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
            "MRP": price_old.text.strip() if price_old else "N/A",
            "Discounted Price": price_new.text.strip() if price_new else "N/A",
            "discount": discount.text.strip() if discount else "N/A",
            "seller": seller.text.strip() if seller else "N/A"
            })


    driver.quit()
    return items, restaurant, city, [], []  # No coupons/discounts currently extracted for MyStore

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

def write_csv(data, platform, restaurant, city, discounts, coupons):
    city = city.replace(" ", "_").strip()
    restaurant = restaurant.replace(" ", "_").strip()
    platform = platform.lower().strip()

    folder_path = os.path.join("data", city, restaurant)
    os.makedirs(folder_path, exist_ok=True)

    # ---------------- Write item data ----------------
    items_filename = f"{restaurant}_{city}_{platform}_items.csv"
    items_path = os.path.join(folder_path, items_filename)

    with open(items_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        if data:
            headers = list(data[0].keys())
            writer.writerow(headers)
            for item in data:
                writer.writerow([item.get(h, "N/A") for h in headers])
        else:
            writer.writerow(["No items found."])

    # ---------------- Write discounts/coupons if Swiggy ----------------
    offers_path = None
    if platform == "swiggy":
        offers_filename = f"{restaurant}_{city}_{platform}_offers.csv"
        offers_path = os.path.join(folder_path, offers_filename)

        with open(offers_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Discounts"])
            if discounts:
                for discount in discounts:
                    writer.writerow([discount])
            else:
                writer.writerow(["No Discounts"])

            writer.writerow([])  # Blank line between sections
            writer.writerow(["Coupons"])
            if coupons:
                for coupon in coupons:
                    writer.writerow([coupon])
            else:
                writer.writerow(["No Coupons"])

    return items_path, offers_path


# -------------------- Endpoints --------------------
@app.post("/test")
def test_endpoint(request: ScrapeRequest):
    return {"url_received": request.url}

@app.post("/scrape")
def scrape_endpoint(request: ScrapeRequest):
    url = request.url
    platform = identify_website(url)

    if platform == "swiggy":
        data, restaurant, city, discounts, coupons = scrape_swiggy(url)
    elif platform == "zomato":
        data, restaurant, city, discounts, coupons = scrape_zomato(url)
    elif platform == "mystore":
        data, restaurant, city, discounts, coupons = scrape_mystore(url)
    else:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    if not data:
        raise HTTPException(status_code=404, detail="No data found on the page.")

    items_path, offers_path = write_csv(data, platform, restaurant, city, discounts, coupons)


    return {
    "status": "success",
    "platform": platform,
    "restaurant": restaurant,
    "city": city,
    "item_count": len(data),
    "items_csv": items_path,
    "offers_csv": offers_path if platform == "swiggy" else None,
    "data": data
}
