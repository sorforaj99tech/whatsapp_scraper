import time
import re
import gspread
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ─── এখানে তোমার link দুটো বসাও ───────────────────────────
GROUP_INVITE_LINK = "https://Open this link to join my WhatsApp Group: https://chat.whatsapp.com/CaCwfjCKyF4LmBILOD9UMj?mode=gi_t"  # তোমার WhatsApp group link
GOOGLE_SHEET_URL  = "https://https://docs.google.com/spreadsheets/d/1-gzFoB-2XLW3ObyOzA43xXZxoQ5AXJ0laXW1ciqUSwU/edit?gid=0#gid=0"  # তোমার Google Sheet link
CREDENTIALS_FILE  = "credentials.json"
SHEET_NAME        = "Members"
# ────────────────────────────────────────────────────────────

def setup_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(GOOGLE_SHEET_URL)
    try:
        ws = sheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=SHEET_NAME, rows=2000, cols=3)
    ws.clear()
    ws.append_row(["#", "Name", "Phone Number"])
    return ws

def setup_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--user-data-dir=./whatsapp_session")
    options.add_argument("--no-sandbox")
    options.add_argument("--headless="False")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(driver_version="146").install()),
        options=options
    )
    return driver

def extract_members(driver):
    members = []
    seen = set()

    member_elements = driver.find_elements(
        By.CSS_SELECTOR,
        'div[data-testid="cell-frame-container"]'
    )

    print(f"মোট {len(member_elements)} টি element পাওয়া গেছে")

    for el in member_elements:
        try:
            name_el = el.find_element(By.CSS_SELECTOR, 'span[title]')
            name = name_el.get_attribute("title").strip()

            try:
                sub_el = el.find_element(
                    By.CSS_SELECTOR,
                    'span[data-testid="cell-frame-secondary-detail"]'
                )
                subtitle = sub_el.text.strip()
            except Exception:
                subtitle = ""

            phone_match = re.search(r'[\+\d][\d\s\-\(\)]{7,}', subtitle)
            phone = phone_match.group().strip() if phone_match else subtitle

            if name and name not in seen:
                seen.add(name)
                members.append({"name": name, "phone": phone})

        except Exception:
            continue

    return members

def upload_to_sheet(ws, members):
    print(f"\n{len(members)} জন member Google Sheet এ upload করছি...")
    rows = [[i+1, m["name"], m["phone"]] for i, m in enumerate(members)]
    if rows:
        ws.append_rows(rows, value_input_option="RAW")
    print(f"Done! {len(members)} জন member sheet এ add হয়েছে।")

def main():
    print("=" * 40)
    print("  WhatsApp Group Member Scraper")
    print("=" * 40)

    # Google Sheet setup
    print("\n[1/4] Google Sheet connect করছি...")
    ws = setup_google_sheet()
    print("      Google Sheet ready!")

    # Browser open
    print("\n[2/4] Browser open করছি...")
    driver = setup_browser()
    wait = WebDriverWait(driver, 60)

    # WhatsApp Web load
    print("\n[3/4] WhatsApp Web load করছি...")
    driver.get("https://web.whatsapp.com")
    print("      QR code scan করো (প্রথমবার হলে)")
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'div[data-testid="chat-list"]')
    ))
    print("      WhatsApp Web ready!")

    # Group open
    print("\n[4/4] Group এ যাচ্ছি...")
    driver.get(GROUP_INVITE_LINK)
    time.sleep(5)

    input("\nGroup member list open করো, তারপর Enter চাপো...")

    # Scroll to load all members
    print("Member list scroll করছি (সব load হতে সময় লাগবে)...")
    for i in range(60):
        driver.execute_script(
            "var els = document.querySelectorAll('div[style*=\"overflow-y\"]');"
            "if(els.length) els[els.length-1].scrollBy(0, 600);"
        )
        time.sleep(0.4)
        if (i+1) % 10 == 0:
            print(f"  Scroll {i+1}/60 হয়েছে...")

    time.sleep(2)

    # Extract
    print("\nMember data extract করছি...")
    members = extract_members(driver)

    if not members:
        print("কোনো member পাওয়া যায়নি!")
        print("Browser manually দেখো এবং Enter চাপো আবার try করতে...")
        input()
        members = extract_members(driver)

    # Upload
    if members:
        upload_to_sheet(ws, members)
        print(f"\nGoogle Sheet link: {GOOGLE_SHEET_URL}")
    else:
        print("Member পাওয়া যায়নি। WhatsApp Web এর structure পরিবর্তন হয়েছে হতে পারে।")

    input("\nশেষ! Enter চাপো browser বন্ধ করতে...")
    driver.quit()

if __name__ == "__main__":
    main()