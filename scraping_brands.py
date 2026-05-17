import re
from playwright.sync_api import (
    Playwright,
    sync_playwright,
    Page,
)
import re
import pandas as pd
from selectolax.parser import HTMLParser
from tqdm import tqdm

# Absolute path to the Brave browser executable for Playwright automation
browser_path = r"C:\Users\Abdalrhman\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"

def create_session(playwright: Playwright):
    """
    Initializes a Chromium-based browser session pointing to a specific Brave installation.
    
    Args:
        playwright (Playwright): The sync Playwright instance context.
        
    Returns:
        Page: A fresh, isolated browser page object ready for navigation.
    """
    # Launch browser with GUI visible and an open remote debugging port
    browser = playwright.chromium.launch(
        headless=False,                # Show the browser window
        executable_path=browser_path,  # Point to Brave
        args=["--remote-debugging-port=9222"]  # Optional: enable debugging
    )
    # Define a standard full HD desktop viewport context
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080}  # typical full HD screen
    )
    page = context.new_page()
    return page


def brand_crawler(page: Page, brand_link: str):
    """
    Navigates to a given URL, handles basic DOM interaction triggers, 
    and captures the underlying HTML.
    
    Args:
        page (Page): The current active Playwright browser tab.
        brand_link (str): The target URL to scrap.
        
    Returns:
        HTMLParser: A Selectolax HTML parser object initialized with the page's HTML structure.
    """
    page.goto(brand_link, timeout=60_000)
    page.wait_for_load_state("load")
    
    # Simulate user interaction to trigger any lazy-loaded content or event listeners
    page.locator("body").click()
    page.locator("body").press("End")
    page.locator("body").press("Home")
    
    return HTMLParser(html=page.content())
    

def get_brand(web_page: HTMLParser):
    """
    Parses a brand page using CSS selectors to extract logo image links, 
    foundation dates, and origin countries.
    
    Args:
        web_page (HTMLParser): The Selectolax parsed HTML node tree.
        
    Returns:
        tuple: (logo_url, foundation_info, country_info) where elements can be strings or None.
    """
    # ---- 1. Logo URL Extraction ----
    try:
        try:
            # Primary strategy: Target standard logo article layout
            logo_css = "div.logo-art > div.content > p.center > a"
            logo = web_page.css(logo_css)[0].attributes['href']
        except:
            # Secondary fallback: Alternative layout index mapping
            logo_css_2 = "body > div.article > div.logo-art > div.logo-item > p:nth-child(36) > a"
            logo = "https://www.carlogos.org/" + web_page.css(logo_css_2)[-1].attributes['href']
    except:
        logo = None
        
    # ---- 2. Metadata Table Extraction ----
    try:     
        foundation_css = "body > div.article > div.logo-art > div.content > table > tbody > tr:nth-child(2) > td:nth-child(2)"
        country_css = "body > div.article > div.logo-art > div.content > table > tbody > tr:nth-child(4) > td:nth-child(2)"
        
        foundation = web_page.css(foundation_css)[0].text()
        # Grab the target text value and isolate the specific country name out of string variations
        country = web_page.css(country_css)[0].text().split(", ")[-1]
    except:
        country, foundation = None, None
            
    return logo, foundation, country

if __name__ == '__main__': 
    # Load targets from local repository data source
    df = pd.read_csv("brands.csv")
    
    # Initialize targeted structure columns
    df["logo"] = None
    df["foundation"] = None
    df["country"] = None
    continue_ = True
    
    with sync_playwright() as playwright:
        page = create_session(playwright)
        i = 0
        
        # Loop through a subset slice of the main data collection
        for brand in tqdm(df["Brands"][:5]):
            # URL Sanitization: convert spacing to URL patterns and sanitize case matching
            brand_url = f"https://www.carlogos.org/car-brands/{brand.strip().replace(' ', '-').lower()}-logo.html"
            
            # Fault-Tolerant extraction loop with a manual terminal user-override mechanism
            while True:
                try:
                    web_page = brand_crawler(page, brand_url)
                    logo, foundation, country = get_brand(web_page)
                    break
                except Exception as e:
                    print(e)
                    user_input = ""
                    # Handle unexpected issues, letting developer troubleshoot network blocks or element changes mid-execution
                    while user_input not in ['y','n']:
                        user_input = input('\n\n-->>An error occurred!\n\tFix it Manually and Press "y" to continue or "n" to Quit: ').strip().lower()
                    if user_input == 'y':
                        continue_ = True
                    else:
                        continue_ = False
                        break
            
            # Populate changes to internal dataframe state if loop context is verified active
            if continue_:
                df.loc[df["Brands"] == brand, "logo"] = logo
                df.loc[df["Brands"] == brand, "foundation"] = foundation
                df.loc[df["Brands"] == brand, "country"] = country
            else:
                break
            
            # Step management control sequence
            i += 5
            if i == 5:
                break
                
    # Persist updated properties directly back onto storage structures
    df.to_csv("brands_2.csv", index=False)