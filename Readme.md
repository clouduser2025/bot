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
