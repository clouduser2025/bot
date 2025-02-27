from telethon import TelegramClient
import asyncio

API_ID = 27889863
API_HASH = "df4d440af21594b001dc768518140c6b"
SESSION_FILE = "toi_session_feb"

client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

async def main():
    await client.start()
    print("Session authenticated successfully!")
    await client.disconnect()

asyncio.run(main())