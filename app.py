from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
import datetime
import re
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import uvicorn
import logging

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
    today = datetime.datetime.today().date()
    file_pattern = rf"TOI_{city}_{today.strftime('%d-%m-%Y')}\.pdf"
    steps_output = {"steps": [], "status": "completed", "extracted_results": []}

    try:
        # Step 1: Find PDF
        steps_output["steps"].append({"step": "Finding PDF", "status": "started"})
        logger.info("Searching for PDF in Telegram channel")
        file_name = None
        async for message in client.iter_messages(CHANNEL_USERNAME):
            if message.file and message.file.name:
                if re.search(file_pattern, message.file.name, re.IGNORECASE):
                    file_name = message.file.name
                    steps_output["steps"].append({"step": "Finding PDF", "status": "success", "filename": file_name})
                    logger.info(f"Found PDF: {file_name}")
                    break
        if not file_name:
            steps_output["steps"].append({"step": "Finding PDF", "status": "failed", "error": f"No PDF found for {city} on {today.strftime('%d-%m-%Y')}"})
            logger.warning(f"No PDF found matching pattern: {file_pattern}")
            raise HTTPException(status_code=404, detail=steps_output)

        # Step 2: Download PDF
        steps_output["steps"].append({"step": "Downloading PDF", "status": "started"})
        file_path = os.path.join(SAVE_DIR, file_name)
        logger.info(f"Constructed file_path: {file_path}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        logger.info(f"Attempting to download to: {file_path}")
        await message.download_media(file=file_path)
        logger.info(f"Download completed, checking: {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"Download failed - file not found at: {file_path}")
            raise FileNotFoundError(f"Download failed - file not found at: {file_path}")
        steps_output["steps"].append({"step": "Downloading PDF", "status": "success", "file_path": file_path})
        logger.info(f"Downloaded: {file_path}")

        # Step 3: Extract Text
        steps_output["steps"].append({"step": "Extracting Text", "status": "started"})
        keywords = ["Public Notice", "Tenders", "Property", "Plot", "Registry"]
        matched_results = []
        logger.info(f"Extracting text from {file_path} with keywords: {keywords}")

        with pdfplumber.open(file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() if page.extract_text() else pytesseract.image_to_string(page.to_image(resolution=300).original)
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

        return steps_output

    except Exception as e:
        steps_output["steps"].append({"step": "Processing", "status": "failed", "error": str(e)})
        steps_output["status"] = "failed"
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=steps_output)

@app.get("/")
async def root():
    return {"message": "Newspaper Extraction API is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)