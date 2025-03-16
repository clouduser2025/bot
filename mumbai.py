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
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

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

# Directory to Save PDFs
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
    allow_origins=["https://iysinfo.com", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/process-newspaper/")
async def process_newspaper(request: CityRequest):
    city = request.city.strip().title()
    # Hardcode date for testing to match the screenshot
    today = datetime.datetime.strptime("11-03-2025", "%d-%m-%Y").date()
    # Uncomment the line below for live use
    # today = datetime.datetime.today().date()
    
    # Define patterns for current, old, and new file formats with the correct date format (dd.mm.yyyy) and space
    current_pattern = rf"TOI {city} {today.strftime('%d.%m.%Y')}\.pdf"
    old_pattern = rf"TOI {city} Tim\.\.\. {today.strftime('%d.%m.%Y')}\.pdf"
    new_pattern = rf"TOI {city} Times {today.strftime('%d.%m.%Y')}\.pdf"
    
    steps_output = {"steps": [], "status": "completed", "extracted_results": []}

    try:
        # Step 1: Find PDF
        steps_output["steps"].append({"step": "Finding PDF", "status": "started"})
        logger.info("Searching for PDF in Telegram channel")
        file_name = None
        message_to_download = None
        
        async for message in client.iter_messages(CHANNEL_USERNAME):
            if message.file and message.file.name:
                # First try the current pattern
                if re.search(current_pattern, message.file.name, re.IGNORECASE):
                    file_name = message.file.name
                    message_to_download = message
                # If not found, try old or new patterns
                elif (re.search(old_pattern, message.file.name, re.IGNORECASE) or 
                      re.search(new_pattern, message.file.name, re.IGNORECASE)):
                    file_name = message.file.name
                    message_to_download = message
        
        if file_name:
            steps_output["steps"].append({"step": "Finding PDF", "status": "success", "filename": file_name, "pattern": "current" if re.search(current_pattern, file_name, re.IGNORECASE) else "old/new"})
            logger.info(f"Found PDF with {'current' if re.search(current_pattern, file_name, re.IGNORECASE) else 'old/new'} pattern: {file_name}")
        else:
            steps_output["steps"].append({
                "step": "Finding PDF",
                "status": "failed",
                "error": f"No PDF found for {city} on {today.strftime('%d.%m.%Y')} with patterns {current_pattern}, {old_pattern}, or {new_pattern}"
            })
            logger.warning(f"No PDF found matching patterns: {current_pattern}, {old_pattern}, or {new_pattern}")
            raise HTTPException(status_code=404, detail=steps_output)

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

        # Step 3: Extract Text using pdf2image and pytesseract
        steps_output["steps"].append({"step": "Extracting Text", "status": "started"})
        keywords = ["Public Notice", "Tenders", "Property", "Plot", "Registry"]
        matched_results = []
        logger.info(f"Extracting text from {file_path} with keywords: {keywords}")

        # Convert PDF to images
        images = convert_from_path(file_path, dpi=300)
        for page_number, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image)
            paragraphs = text.split("\n\n")
            for keyword in keywords:
                for idx, paragraph in enumerate(paragraphs):
                    if keyword.lower() in paragraph.lower():
                        before = paragraphs[idx - 1] if idx > 0 else ""
                        after = paragraphs[idx + 1] if idx < len(paragraphs) - 1 else ""
                        full_section = f"{before}\n\n{paragraph}\n\n{after}".strip()
                        matched_results.append({
                            "Date": today.strftime('%Y-%m-%d'),
                            "Page No.": page_number,
                            "Keyword": keyword,
                            "City": city,
                            "Extracted Text": full_section
                        })

        steps_output["steps"].append({
            "step": "Extracting Text",
            "status": "success",
            "records_extracted": len(matched_results)
        })
        steps_output["extracted_results"] = matched_results
        logger.info(f"Extracted {len(matched_results)} records")

        # Step 4: Save to Excel
        steps_output["steps"].append({"step": "Saving to Excel", "status": "started"})
        df = pd.DataFrame(matched_results)
        excel_path = os.path.join(SAVE_DIR, f"TOI_{city}_{today.strftime('%d-%m-%Y')}_extracted.xlsx")
        df.to_excel(excel_path, index=False)
        steps_output["steps"].append({
            "step": "Saving to Excel",
            "status": "success",
            "excel_path": excel_path
        })
        logger.info(f"Saved extracted data to {excel_path}")

        # Step 5: Delete the PDF file
        os.remove(file_path)
        steps_output["steps"].append({"step": "Deleting PDF", "status": "success", "file_path": file_path})
        logger.info(f"Deleted PDF file: {file_path}")

        return steps_output

    except Exception as e:
        steps_output["steps"].append({"step": "Processing", "status": "failed", "error": str(e)})
        steps_output["status"] = "failed"  # Fixed: Changed from steps_output["status": "failed" to steps_output["status"] = "failed"
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=steps_output)

@app.get("/")
async def root():
    return {"message": "Newspaper Extraction API is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)