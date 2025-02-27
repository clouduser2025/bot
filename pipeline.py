from telethon import TelegramClient, events
import os
import datetime
import re
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd

# ✅ Replace with your API Credentials from my.telegram.org
API_ID = 27889863
API_HASH = "df4d440af21594b001dc768518140c6b"

# ✅ Persistent session file (avoids repeated phone verification)
SESSION_FILE = "toi_session_feb"

# ✅ Target Telegram Channel
CHANNEL_USERNAME = "the_times_of_india_0"  # Remove '@' symbol

# ✅ Directory to Save PDFs
SAVE_DIR = "./toi_editions"
os.makedirs(SAVE_DIR, exist_ok=True)

# ✅ Get User Input for City Selection
city = input("Enter city name (e.g., Pune, Lucknow): ").strip().title()

# ✅ Today's Date Format (DD-MM-YYYY)
today = datetime.datetime.today().strftime("%d-%m-%Y")

# ✅ Generate Dynamic File Pattern for the Selected City
file_pattern = rf"TOI_{city}_{today}\.pdf"

# ✅ Initialize Telegram Client with a Persistent Session
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

async def download_newspaper_edition():
    """Fetch and download the newspaper PDF from Telegram"""
    await client.start()  # ✅ Logs in and saves session automatically

    latest_pdf_path = None
    async for message in client.iter_messages(CHANNEL_USERNAME):
        if message.file and message.file.name:
            file_name = message.file.name
            if re.search(file_pattern, file_name, re.IGNORECASE):
                print(f"✅ Found {city} Edition: {file_name}")

                # ✅ Download the file
                file_path = os.path.join(SAVE_DIR, file_name)
                await message.download_media(file=file_path)

                print(f"✅ Downloaded: {file_name} -> {file_path}")
                latest_pdf_path = file_path
                break
    else:
        print(f"❌ No edition found for {city} on {today}")

    await client.disconnect()
    return latest_pdf_path

def extract_text_from_pdf(pdf_path):
    """Extract and process text from the newspaper PDF"""
    if not pdf_path:
        print("❌ No valid PDF found for processing.")
        return

    # ✅ Define Output Excel File Path
    output_excel = os.path.splitext(pdf_path)[0] + "_Extracted.xlsx"

    # ✅ Keywords to search
    keywords = ["Public Notice", "Tenders", "Property", "Plot", "Registry"]

    # ✅ Initialize DataFrame to store matched results
    matched_results = []

    # ✅ Function to extract text from a PDF page
    def extract_text_from_page(page):
        try:
            return page.extract_text()  # Extract text if it's a text-based PDF
        except:
            return None

    # ✅ Open PDF and scan each page
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = extract_text_from_page(page)

            if not text:  # If text extraction fails, apply OCR
                image = page.to_image(resolution=300).original  # Convert page to image
                text = pytesseract.image_to_string(image)  # Apply OCR

            # ✅ Split text into paragraphs
            paragraphs = text.split("\n\n")  # Double line breaks separate sections

            # ✅ Search for Keywords in Extracted Text
            for keyword in keywords:
                for idx, paragraph in enumerate(paragraphs):
                    if keyword.lower() in paragraph.lower():
                        # Extract surrounding paragraphs (to get full context)
                        before = paragraphs[idx - 1] if idx > 0 else ""
                        after = paragraphs[idx + 1] if idx < len(paragraphs) - 1 else ""
                        full_section = f"{before}\n\n{paragraph}\n\n{after}"

                        matched_results.append({
                            "Page No.": page_number,
                            "Keyword": keyword,
                            "Extracted Text": full_section.strip()
                        })

    # ✅ Convert matched results to DataFrame
    df_extracted = pd.DataFrame(matched_results)

    # ✅ Save extracted data to Excel
    df_extracted.to_excel(output_excel, index=False)

    print(f"✅ Extraction Completed! Matched keywords with full context saved in {output_excel}")

# ✅ Run the Full Pipeline
with client:
    latest_pdf = client.loop.run_until_complete(download_newspaper_edition())
    extract_text_from_pdf(latest_pdf)
