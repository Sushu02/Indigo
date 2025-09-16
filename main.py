# import os
# import time
# import csv
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options

# # List of asset links with their filehashes
# assets = [
#     {"link": "https://files.finkraft.ai/6bee039bff0331d37fd332af6f841977", "filehash": "6bee039bff0331d37fd332af6f841977"},
#     {"link": "https://files.finkraft.ai/b557f6be890d1fcae95b7faa302dd0e4", "filehash": "b557f6be890d1fcae95b7faa302dd0e4"},
#     {"link": "https://files.finkraft.ai/b573634bcc62d0170b2cc53701000dcb", "filehash": "b573634bcc62d0170b2cc53701000dcb"}  # Example with no invoice
# ]

# DOWNLOAD_DIR = "/Users/mac/Desktop/Indigo/Downloads"
# os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# # CSV to save filehashes with "No Invoice"
# OUTPUT_CSV = "/Users/mac/Desktop/Indigo/no_invoice_filehashes.csv"

# chrome_options = Options()
# chrome_options.add_experimental_option("prefs", {
#     "download.default_directory": DOWNLOAD_DIR,
#     "download.prompt_for_download": False,
#     "directory_upgrade": True,
#     "safebrowsing.enabled": True
# })

# driver = webdriver.Chrome(options=chrome_options)

# # Open CSV in write mode
# with open(OUTPUT_CSV, mode='w', newline='') as csvfile:
#     writer = csv.writer(csvfile)
#     writer.writerow(["filehash"])  # header

#     for asset in assets:
#         driver.get(asset["link"])
#         time.sleep(3)

#         try:
#             download_button = driver.find_element(By.TAG_NAME, "a")
#             download_button.click()
#             print(f"Clicked download for: {asset['filehash']}")
#         except Exception as e:
#             print(f"Could not click download for {asset['filehash']}: {e}")
#             continue

#         # Wait for file to appear in download folder
#         timeout = 20  # seconds
#         file_found = False
#         for _ in range(timeout):
#             files = os.listdir(DOWNLOAD_DIR)
#             if files:
#                 latest_file = max([os.path.join(DOWNLOAD_DIR, f) for f in files], key=os.path.getctime)
#                 if not latest_file.endswith(".crdownload"):  # skip partially downloaded files
#                     file_found = True
#                     break
#             time.sleep(1)

#         if not file_found:
#             print(f"Download timeout for {asset['filehash']}")
#             continue

#         # Read file content
#         try:
#             with open(latest_file, "r", encoding="utf-8") as f:
#                 content = f.read()
#             if "No Invoice" in content:
#                 writer.writerow([asset["filehash"]])
#                 print(f"'No Invoice' found for {asset['filehash']}")
#             else :                
#                 print(f"Invoice found for {asset['filehash']}")    
#         except Exception as e:
#             print(f"Error reading file {latest_file}: {e}")

# driver.quit()
# print("All downloads processed.")



import os
import time
import csv
from multiprocessing import Pool, cpu_count
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

# INPUT_CSV = "/Users/mac/Desktop/Indigo/1-10000.csv"
# DOWNLOAD_DIR = "/Users/mac/Desktop/Indigo/Downloads"
# OUTPUT_CSV = "/Users/mac/Desktop/Indigo/no_invoice_filehashes10k.csv"

BASE_DIR = os.getenv("GITHUB_WORKSPACE", os.getcwd())
import os

DOWNLOAD_DIR = "/tmp/Downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

INPUT_CSV = "1-10000.csv"
OUTPUT_CSV = "/tmp/myoutput.csv"
# INPUT_CSV = os.path.join(BASE_DIR, "1-10000.csv")
# OUTPUT_CSV = os.path.join(BASE_DIR, "myoutput.csv")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def process_invoice(row):
    filehash = row["filehash"]
    link = row["assetlink"]
    
    # Setup a separate Chrome instance for this process
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    chrome_options.add_argument("--disable-gpu")  # Recommended for headless on some systems
    chrome_options.add_argument("--no-sandbox")   # Good for Linux environments
    chrome_options.add_argument("--disable-dev-shm-usage")  # Avoid limited resource issues

    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    driver = webdriver.Chrome(options=chrome_options)
    
    print(f"Processing {filehash}")
    try:
        existing_files = set(os.listdir(DOWNLOAD_DIR))
        driver.get(link)
        time.sleep(5)
        
        try:
            download_button = driver.find_element(By.TAG_NAME, "a")
            download_button.click()
        except:
            return [filehash, "", "Download Button Not Found"]
        
        # Wait for download
        timeout = 70
        new_file = None
        for _ in range(timeout):
            current_files = set(os.listdir(DOWNLOAD_DIR))
            diff = current_files - existing_files
            if diff:
                candidate_file = list(diff)[0]
                candidate_path = os.path.join(DOWNLOAD_DIR, candidate_file)
                if not candidate_file.endswith(".crdownload") and not candidate_file.startswith(".com.google.Chrome"):
                    new_file = candidate_path
                    time.sleep(3)
                    break
            time.sleep(1)
        
        if not new_file:
            return [filehash, "", "Download Timeout"]
        
        # Process file
        filename = os.path.basename(new_file)
        status = "Unknown"
        try:
            if new_file.lower().endswith(".html"):
                with open(new_file, "r", encoding="utf-8") as f:
                    content = f.read()
                soup = BeautifulSoup(content, "html.parser")
                page_text = soup.get_text(separator=" ", strip=True)
                status = "No Invoice Found" if "No Invoice" in page_text else "Invoice Present"
            elif new_file.lower().endswith(".pdf"):
                reader = PdfReader(new_file)
                text_content = "".join([page.extract_text() or "" for page in reader.pages])
                status = "No Invoice Found" if "No Invoice" in text_content else "Invoice Present"
            else:
                status = "Unsupported File Type"
        except Exception as e:
            status = f"Error: {e}"
        
        # Cleanup
        try:
            os.remove(new_file)
        except:
            pass
        
        return [filehash, filename, status]
    
    finally:
        driver.quit()

def debug_wrapper(args):
    index, row, total_rows = args
    print(f"Processing row {index} / {total_rows} -> filehash: {row['filehash']}")
    result = process_invoice(row)
    print(f"Completed row {index} / {total_rows} -> status: {result[2]}")
    return result


if __name__ == "__main__":
    # Read CSV
    with open(INPUT_CSV, 'r') as f:
        reader = list(csv.DictReader(f))

    total_rows = len(reader)
    print(f"Total rows to process: {total_rows}")

    # Pass total_rows to worker via arguments
    indexed_rows = [(i+1, row, total_rows) for i, row in enumerate(reader)]

    pool_size = min(cpu_count(), 4)
    with Pool(pool_size) as pool:
        results = pool.map(debug_wrapper, indexed_rows)

    # Write output CSV
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["filehash", "filename", "status"])
        writer.writerows(results)

    print("Processing complete.")