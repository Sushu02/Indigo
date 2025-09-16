# import os
# import time
# import csv
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options

# INPUT_CSV = "/Users/mac/Desktop/Indigo/input.csv"
# DOWNLOAD_DIR = "/Users/mac/Desktop/Indigo/Downloads"
# OUTPUT_CSV = "/Users/mac/Desktop/Indigo/no_invoice_filehashes.csv"

# os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# chrome_options = Options()
# chrome_options.add_experimental_option("prefs", {
#     "download.default_directory": DOWNLOAD_DIR,
#     "download.prompt_for_download": False,
#     "directory_upgrade": True,
#     "safebrowsing.enabled": True
# })

# driver = webdriver.Chrome(options=chrome_options)

# with open(INPUT_CSV, mode='r') as infile, open(OUTPUT_CSV, mode='w', newline='') as outfile:
#     reader = csv.DictReader(infile)
#     writer = csv.writer(outfile)
#     writer.writerow(["filehash", "filename", "status"])  # header

#     for row in reader:
#         filehash = row["filehash"]
#         link = row["assetlink"]

#         print(f"\nProcessing filehash: {filehash}")

#         driver.get(link)
#         time.sleep(5)  # Wait for page to fully load

#         try:
#             download_button = driver.find_element(By.TAG_NAME, "a")
#             download_button.click()
#             print(f"Clicked download for: {filehash}")
#         except Exception as e:
#             print(f"Could not click download for {filehash}: {e}")
#             writer.writerow([filehash, "", "Download Button Not Found"])
#             continue

#         # Wait for file to fully download
#         timeout = 60  # 60 seconds timeout
#         file_found = False
#         for _ in range(timeout):
#             files = os.listdir(DOWNLOAD_DIR)
#             if files:
#                 latest_file = max(
#                     [os.path.join(DOWNLOAD_DIR, f) for f in files],
#                     key=os.path.getctime
#                 )
#                 if not latest_file.endswith(".crdownload"):
#                     file_found = True
#                     break
#             time.sleep(1)

#         if not file_found:
#             print(f"Download timeout for {filehash}")
#             writer.writerow([filehash, "", "Download Timeout"])
#             continue

#         # Extract content and check for "No Invoice"
#         try:
#             with open(latest_file, "r", encoding="utf-8") as f:
#                 content = f.read()

#             if "No Invoice" in content:
#                 status = "No Invoice Found"
#                 print(f"'No Invoice' found for {filehash}")
#             else:
#                 status = "Invoice Present"
#                 print(f"Invoice found for {filehash}")

#             filename = os.path.basename(latest_file)
#             writer.writerow([filehash, filename, status])

#         except Exception as e:
#             print(f"Error reading file {latest_file}: {e}")
#             writer.writerow([filehash, "", f"Error Reading File: {e}"])

#         # Clean up: Delete the downloaded file
#         try:
#             os.remove(latest_file)
#             print(f"Deleted file: {filename}")
#         except Exception as e:
#             print(f"Error deleting file {filename}: {e}")

# driver.quit()
# print("\nProcessing complete. Results saved in:", OUTPUT_CSV)


import os
import time
import csv
from multiprocessing import Pool, cpu_count
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

INPUT_CSV = "/Users/mac/Desktop/Indigo/1-10000.csv"
DOWNLOAD_DIR = "/Users/mac/Desktop/Indigo/Downloads"
OUTPUT_CSV = "/Users/mac/Desktop/Indigo/no_invoice_filehashes10k.csv"

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


if __name__ == "__main__":
    # Read CSV
    with open(INPUT_CSV, 'r') as f:
        reader = list(csv.DictReader(f))
    
    # Use a pool of processes
    pool_size = min(cpu_count(), 4)  # Adjust according to your system
    with Pool(pool_size) as pool:
        results = pool.map(process_invoice, reader)
    
    # Write output CSV
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["filehash", "filename", "status"])
        writer.writerows(results)
    
    print("Processing complete.")
