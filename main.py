import os
import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# List of asset links with their filehashes
assets = [
    {"link": "https://files.finkraft.ai/6bee039bff0331d37fd332af6f841977", "filehash": "6bee039bff0331d37fd332af6f841977"},
    {"link": "https://files.finkraft.ai/b557f6be890d1fcae95b7faa302dd0e4", "filehash": "b557f6be890d1fcae95b7faa302dd0e4"},
    {"link": "https://files.finkraft.ai/b573634bcc62d0170b2cc53701000dcb", "filehash": "b573634bcc62d0170b2cc53701000dcb"}  # Example with no invoice
]

DOWNLOAD_DIR = "/Users/mac/Desktop/Indigo/Downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# CSV to save filehashes with "No Invoice"
OUTPUT_CSV = "/Users/mac/Desktop/Indigo/no_invoice_filehashes.csv"

chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
})

driver = webdriver.Chrome(options=chrome_options)

# Open CSV in write mode
with open(OUTPUT_CSV, mode='w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["filehash"])  # header

    for asset in assets:
        driver.get(asset["link"])
        time.sleep(3)

        try:
            download_button = driver.find_element(By.TAG_NAME, "a")
            download_button.click()
            print(f"Clicked download for: {asset['filehash']}")
        except Exception as e:
            print(f"Could not click download for {asset['filehash']}: {e}")
            continue

        # Wait for file to appear in download folder
        timeout = 20  # seconds
        file_found = False
        for _ in range(timeout):
            files = os.listdir(DOWNLOAD_DIR)
            if files:
                latest_file = max([os.path.join(DOWNLOAD_DIR, f) for f in files], key=os.path.getctime)
                if not latest_file.endswith(".crdownload"):  # skip partially downloaded files
                    file_found = True
                    break
            time.sleep(1)

        if not file_found:
            print(f"Download timeout for {asset['filehash']}")
            continue

        # Read file content
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "No Invoice" in content:
                writer.writerow([asset["filehash"]])
                print(f"'No Invoice' found for {asset['filehash']}")
            else :                
                print(f"Invoice found for {asset['filehash']}")    
        except Exception as e:
            print(f"Error reading file {latest_file}: {e}")

driver.quit()
print("All downloads processed.")
