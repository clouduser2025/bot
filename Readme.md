4️⃣ Automate Daily Downloads
To run this script automatically every day, set up a scheduler.

📌 Windows (Task Scheduler)
Open Task Scheduler → Create Basic Task.
Name it "TOI Pune Download".
Set Trigger → Daily at 7:00 AM.
Set Action → Start a Program.
Select python.exe and add the script path (toi_pune_bot.py).
Click Finish.

📌 How This Works
✅ User selects city
✅ Automatically downloads today's TOI newspaper
✅ Uses the downloaded PDF as input for text extraction
✅ Searches for keywords & extracts full sections of text
✅ Saves extracted data in an Excel file next to the PDF

O/p:
✅ Found Pune Edition: TOI_Pune_11-02-2025.pdf
✅ Downloaded: TOI_Pune_11-02-2025.pdf -> ./toi_editions/TOI_Pune_11-02-2025.pdf
✅ Extraction Completed! Matched keywords with full context saved in ./toi_editions/TOI_Pune_11-02-2025_Extracted.xlsx

C:\Users\shafe>python C:\Users\shafe\automationbot\pipeline.py
Enter city name (e.g., Pune, Lucknow): PUNE
✅ Found Pune Edition: TOI_Pune_11-02-2025.pdf
✅ Downloaded: TOI_Pune_11-02-2025.pdf -> ./toi_editions\TOI_Pune_11-02-2025.pdf
✅ Extraction Completed! Matched keywords with full context saved in ./toi_editions\TOI_Pune_11-02-2025_Extracted.xlsx

installation :
pip install python-telegram-bot telethon requests
pip install pdfplumber pandas nltk openpyxl
pip install telethon requests

navigate:
cd C:\Users\shafe\automationbot
python C:\Users\shafe\automationbot\pune.py
python C:\Users\shafe\automationbot\ext.py
python C:\Users\shafe\automationbot\pipeline.py


telethon
pdfplumber
pytesseract
pillow
pandas
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
import datetime
import re
import pandas as pd
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import uvicorn
import logging
import mysql.connector
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from openpyxl import load_workbook, Workbook

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Newspaper Extraction API", version="0.1.0")

# Telegram API Credentials
API_ID = 27889863
API_HASH = "df4d440af21594b001dc768518140c6b"
PHONE_NUMBER = "+919423780567"
SESSION_FILE = "toi_session_feb"
CHANNEL_USERNAME = "the_times_of_india_0"

# Directory to Save PDFs and Excel files
SAVE_DIR = r"C:\Users\shafe\automationbot\toi_editions"
os.makedirs(SAVE_DIR, exist_ok=True)
logger.info(f"SAVE_DIR set to: {SAVE_DIR}")

# Initialize Telegram Client
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, "r") as f:
        session_str = f.read().strip()
    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
else:
    client = TelegramClient(StringSession(), API_ID, API_HASH)

# Input Model
class CityRequest(BaseModel):
    city: str

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await client.start(phone=PHONE_NUMBER)
        logger.info("Telegram client connected!")
        if not os.path.exists(SESSION_FILE):
            session_str = client.session.save()
            with open(SESSION_FILE, "w") as f:
                f.write(session_str)
            logger.info(f"Session saved to {SESSION_FILE}")
        yield
    except Exception as e:
        logger.error(f"Error in lifespan: {str(e)}", exc_info=True)
    finally:
        await client.disconnect()
        logger.info("Telegram client disconnected!")

app = FastAPI(title="Newspaper Extraction API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tool.iysinfo.com", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def connect_to_db():
    """Helper function to establish or re-establish a MySQL connection."""
    return mysql.connector.connect(
        host="sg-nme-web616.main-hosting.eu",
        user="u803905913_autobot_user",
        password="AutoBot@123devend",
        database="u803905913_autobot_ai",
        connection_timeout=300
    )

def append_to_excel(excel_path, data, first_write=False):
    """Append data to an Excel file incrementally."""
    if first_write:
        # Create new Excel file with headers
        wb = Workbook()
        ws = wb.active
        ws.append(["Date", "Page No.", "Keyword", "City", "Extracted Text"])
        for row in data:
            ws.append([row["Date"], row["Page No."], row["Keyword"], row["City"], row["Extracted Text"]])
        wb.save(excel_path)
    else:
        # Append to existing Excel file
        wb = load_workbook(excel_path)
        ws = wb.active
        for row in data:
            ws.append([row["Date"], row["Page No."], row["Keyword"], row["City"], row["Extracted Text"]])
        wb.save(excel_path)

@app.post("/process-newspaper/")
async def process_newspaper(request: CityRequest):
    city = request.city.strip().title()
    today = datetime.datetime.today().date()
    
    # Simplified pattern: Match TOI, city, and DD-MM, ignore the rest
    simplified_pattern = rf"TOI.*{city}.*{today.strftime('%d-%m')}"
    
    steps_output = {"steps": [], "status": "completed", "extracted_results": []}
    db_connection = None
    cursor = None
    file_path = None
    excel_path = os.path.join(SAVE_DIR, f"TOI_{city}_{today.strftime('%d-%m-%Y')}_extracted.xlsx")

    try:
        # Step 1: Find PDF
        steps_output["steps"].append({"step": "Finding PDF", "status": "started"})
        logger.info("Searching for PDF in Telegram channel")
        file_name = None
        message_to_download = None
        
        # Debug: Log all filenames to verify channel content
        async for message in client.iter_messages(CHANNEL_USERNAME):
            if message.file and message.file.name:
                logger.info(f"Found file in channel: {message.file.name}")
                # Check simplified pattern
                if re.search(simplified_pattern, message.file.name, re.IGNORECASE):
                    file_name = message.file.name
                    message_to_download = message
                    logger.info(f"Matched with simplified pattern: {file_name}")
        
        if file_name:
            steps_output["steps"].append({
                "step": "Finding PDF",
                "status": "success",
                "filename": file_name,
                "matched_pattern": "simplified"
            })
            logger.info(f"Found PDF with simplified pattern: {file_name}")
        else:
            error_msg = f"No PDF found for {city} on {today.strftime('%d-%m-%Y')} with pattern {simplified_pattern}"
            steps_output["steps"].append({"step": "Finding PDF", "status": "failed", "error": error_msg})
            logger.warning(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        # Step 2: Download PDF
        steps_output["steps"].append({"step": "Downloading PDF", "status": "started"})
        file_path = os.path.join(SAVE_DIR, file_name)
        logger.info(f"Constructed file_path: {file_path}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        logger.info(f"Attempting to download to: {file_path}")
        await message_to_download.download_media(file=file_path)
        logger.info(f"Download completed, checking: {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"Download failed - file not found at: {file_path}")
            raise FileNotFoundError(f"Download failed - file not found at: {file_path}")
        steps_output["steps"].append({"step": "Downloading PDF", "status": "success", "file_path": file_path})
        logger.info(f"Downloaded: {file_path}")

        # Step 3: Extract Text and Save to Excel Page-by-Page
        steps_output["steps"].append({"step": "Extracting Text and Saving to Excel", "status": "started"})
        keywords = ["Public Notice", "Tenders", "Property", "Plot", "Registry"]
        total_records = 0
        page_number = 1
        total_pages = 0
        first_write = True

        while True:
            image_path = os.path.join(SAVE_DIR, f"page_{page_number}.png")
            try:
                # Convert one page at a time
                logger.info(f"Converting page {page_number} to image")
                images = convert_from_path(file_path, dpi=300, first_page=page_number, last_page=page_number)
                if not images:  # No more pages
                    logger.info(f"No more pages found after page {page_number - 1}")
                    break

                image = images[0]
                image.save(image_path)
                logger.info(f"Converted page {page_number} to image: {image_path}")
                
                logger.info(f"Extracting text from page {page_number}")
                text = pytesseract.image_to_string(image)
                paragraphs = text.split("\n\n")
                page_results = []
                for keyword in keywords:
                    for idx, paragraph in enumerate(paragraphs):
                        if keyword.lower() in paragraph.lower():
                            before = paragraphs[idx - 1] if idx > 0 else ""
                            after = paragraphs[idx + 1] if idx < len(paragraphs) - 1 else ""
                            full_section = f"{before}\n\n{paragraph}\n\n{after}".strip()
                            page_results.append({
                                "Date": today.strftime('%Y-%m-%d'),
                                "Page No.": page_number,
                                "Keyword": keyword,
                                "City": city,
                                "Extracted Text": full_section
                            })

                # Append to Excel immediately
                if page_results:
                    append_to_excel(excel_path, page_results, first_write)
                    total_records += len(page_results)
                    logger.info(f"Saved {len(page_results)} records from page {page_number} to {excel_path}")
                    first_write = False
                else:
                    logger.info(f"No records found on page {page_number}")

                # Delete the image after processing
                os.remove(image_path)
                logger.info(f"Deleted image: {image_path}")
                total_pages += 1
                page_number += 1
                images = None  # Clear memory

            except Exception as e:
                logger.warning(f"Error processing page {page_number}: {str(e)}", exc_info=True)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    logger.info(f"Deleted image due to error: {image_path}")
                break

        steps_output["steps"].append({
            "step": "Extracting Text and Saving to Excel",
            "status": "success",
            "total_pages": total_pages,
            "records_extracted": total_records
        })
        steps_output["extracted_results"] = []  # Not storing in memory
        logger.info(f"Extracted and saved {total_records} records from {total_pages} pages to {excel_path}")

        # Step 4: Insert into MySQL Database
        steps_output["steps"].append({"step": "Inserting into Database", "status": "started"})
        try:
            db_connection = connect_to_db()
            cursor = db_connection.cursor()
            insert_query = """
                INSERT INTO autobot_extraction_table (processed_date, page_number, keyword, city, extracted_text)
                VALUES (%s, %s, %s, %s, %s)
            """
            logger.info(f"Reading Excel file: {excel_path}")
            df = pd.read_excel(excel_path)
            for _, row in df.iterrows():
                values = (
                    row["Date"],
                    row["Page No."],
                    row["Keyword"],
                    row["City"],
                    row["Extracted Text"]
                )
                cursor.execute(insert_query, values)
            db_connection.commit()
            steps_output["steps"].append({
                "step": "Inserting into Database",
                "status": "success",
                "records_inserted": len(df)
            })
            logger.info(f"Inserted {len(df)} records into database")
        except mysql.connector.Error as db_err:
            logger.warning(f"Database error: {str(db_err)}", exc_info=True)
            if db_connection:
                db_connection.close()
            db_connection = connect_to_db()
            cursor = db_connection.cursor()
            try:
                logger.info(f"Retrying database insertion after error")
                for _, row in df.iterrows():
                    values = (
                        row["Date"],
                        row["Page No."],
                        row["Keyword"],
                        row["City"],
                        row["Extracted Text"]
                    )
                    cursor.execute(insert_query, values)
                db_connection.commit()
                steps_output["steps"].append({
                    "step": "Inserting into Database",
                    "status": "success",
                    "records_inserted": len(df)
                })
                logger.info(f"Inserted {len(df)} records into database after retry")
            except mysql.connector.Error as retry_err:
                steps_output["steps"].append({
                    "step": "Inserting into Database",
                    "status": "failed",
                    "error": f"Failed to insert into database after retry: {str(retry_err)}"
                })
                logger.error(f"Failed to insert into database after retry: {str(retry_err)}", exc_info=True)

        # Step 5: Delete the PDF file
        os.remove(file_path)
        steps_output["steps"].append({"step": "Deleting PDF", "status": "success", "file_path": file_path})
        logger.info(f"Deleted PDF file: {file_path}")

        # Step 6: Delete the Excel file
        steps_output["steps"].append({"step": "Deleting Excel", "status": "started"})
        if os.path.exists(excel_path):
            os.remove(excel_path)
            steps_output["steps"].append({"step": "Deleting Excel", "status": "success", "excel_path": excel_path})
            logger.info(f"Deleted Excel file: {excel_path}")
        else:
            steps_output["steps"].append({"step": "Deleting Excel", "status": "failed", "error": f"Excel file not found at: {excel_path}"})
            logger.warning(f"Excel file not found for deletion: {excel_path}")

        return steps_output

    except Exception as e:
        steps_output["steps"].append({"step": "Processing", "status": "failed", "error": str(e)})
        steps_output["status"] = "failed"
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted PDF file due to error: {file_path}")
        if os.path.exists(excel_path):
            os.remove(excel_path)
            logger.info(f"Deleted Excel file due to error: {excel_path}")
        raise HTTPException(status_code=500, detail=steps_output)
    finally:
        if db_connection and db_connection.is_connected():
            cursor.close()
            db_connection.close()
            logger.info("Database connection closed")

@app.get("/")
async def root():
    return {"message": "Newspaper Extraction API is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)