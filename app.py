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
import asyncio
import uvicorn
from fastapi.responses import FileResponse
app = FastAPI(title="Newspaper Extraction API", version="0.1.0")

# Telegram API Credentials
API_ID = 27889863
API_HASH = "df4d440af21594b001dc768518140c6b"
SESSION_FILE = "toi_session_feb"
CHANNEL_USERNAME = "the_times_of_india_0"

# Directory to Save PDFs
SAVE_DIR = "./toi_editions"
os.makedirs(SAVE_DIR, exist_ok=True)

# Initialize Telegram Client
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# Global variable to store the latest downloaded file path
latest_file_path = None

# Input Model
class CityRequest(BaseModel):
    city: str

# Lifespan event handler for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to Telegram
    await client.start()
    print("Telegram client connected!")
    yield
    # Shutdown: Disconnect from Telegram
    await client.disconnect()
    print("Telegram client disconnected!")

# Create FastAPI app with lifespan
app = FastAPI(title="Newspaper Extraction API", version="0.1.0", lifespan=lifespan)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002"],  # Add both ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 1. Find PDF API
@app.post("/find-pdf/")
async def find_pdf(request: CityRequest):
    """Find a PDF in the Telegram channel based on city name."""
    city = request.city.strip().title()
    today = datetime.datetime.today().strftime("%d-%m-%Y")
    file_pattern = rf"TOI_{city}_{today}\.pdf"

    try:
        async for message in client.iter_messages(CHANNEL_USERNAME):
            if message.file and message.file.name:
                file_name = message.file.name
                if re.search(file_pattern, file_name, re.IGNORECASE):
                    return {"message": f"PDF found for {city}", "filename": file_name}
        raise HTTPException(status_code=404, detail=f"No PDF found for {city} on {today}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# 2. Download PDF API (Finds and Downloads Automatically)
@app.post("/download-pdf/")
async def download_pdf(request: CityRequest):
    """Find and download the PDF for the given city automatically."""
    global latest_file_path
    city = request.city.strip().title()
    today = datetime.datetime.today().strftime("%d-%m-%Y")
    file_pattern = rf"TOI_{city}_{today}\.pdf"

    try:
        async for message in client.iter_messages(CHANNEL_USERNAME):
            if message.file and message.file.name:
                file_name = message.file.name
                if re.search(file_pattern, file_name, re.IGNORECASE):
                    file_path = os.path.join(SAVE_DIR, file_name)
                    await message.download_media(file=file_path)
                    latest_file_path = file_path  # Store for extraction
                    return {"message": f"Downloaded {city} edition", "file_path": file_path}
        raise HTTPException(status_code=404, detail=f"No PDF found for {city} on {today}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# 3. Extract Text API (Automatically Uses Latest Downloaded File)
@app.post("/extract-text/")
async def extract_text():
    """Extract text from the most recently downloaded PDF and save to Excel."""
    global latest_file_path
    if not latest_file_path or not os.path.exists(latest_file_path):
        raise HTTPException(status_code=400, detail="No PDF downloaded yet. Run /download-pdf/ first.")

    try:
        output_excel = os.path.splitext(latest_file_path)[0] + "_Extracted.xlsx"
        keywords = ["Public Notice", "Tenders", "Property", "Plot", "Registry"]
        matched_results = []

        def extract_text_from_page(page):
            try:
                return page.extract_text()
            except:
                return None

        with pdfplumber.open(latest_file_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = extract_text_from_page(page)
                if not text:
                    image = page.to_image(resolution=300).original
                    text = pytesseract.image_to_string(image)

                paragraphs = text.split("\n\n")
                for keyword in keywords:
                    for idx, paragraph in enumerate(paragraphs):
                        if keyword.lower() in paragraph.lower():
                            before = paragraphs[idx - 1] if idx > 0 else ""
                            after = paragraphs[idx + 1] if idx < len(paragraphs) - 1 else ""
                            full_section = f"{before}\n\n{paragraph}\n\n{after}"
                            matched_results.append({
                                "Page No.": page_number,
                                "Keyword": keyword,
                                "Extracted Text": full_section.strip()
                            })

        df_extracted = pd.DataFrame(matched_results)
        df_extracted.to_excel(output_excel, index=False)
        return {"message": "Extraction completed!", "excel_file": output_excel}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

# Add a route to serve Excel files
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(SAVE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)

# Health Check
@app.get("/")
async def root():
    return {"message": "Newspaper Extraction API is running!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)