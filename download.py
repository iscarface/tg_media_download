import os
from telethon import TelegramClient
from telethon.tl.types import (
    InputMessagesFilterPhotos,
    InputMessagesFilterVideo,
    InputMessagesFilterDocument,
)
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Environment variables
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
group_invite_link = os.getenv("TELEGRAM_GROUP_INVITE_LINK")
google_auth_path = os.getenv(
    "GOOGLE_AUTH_PATH"
)  # Path to client_secrets.json for Google Drive
google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# Initialize Telegram client
client = TelegramClient("session_name", api_id, api_hash)


def authenticate_google_drive():
    gauth = GoogleAuth()

    # Attempt to load the credentials file
    if os.path.exists(google_auth_path):
        gauth.LoadCredentialsFile(google_auth_path)

    # Authenticate if no valid credentials are found
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()  # Opens browser for authentication
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()

    # Save the credentials file for future use
    gauth.SaveCredentialsFile(google_auth_path)

    return GoogleDrive(gauth)


# Upload a file to Google Drive
def upload_file_to_drive(drive, file_path):
    file_name = os.path.basename(file_path)
    gfile = drive.CreateFile(
        {
            "title": file_name,
            "parents": (
                [{"id": google_drive_folder_id}] if google_drive_folder_id else []
            ),
        }
    )
    gfile.SetContentFile(file_path)
    gfile.Upload()
    print(f"Uploaded {file_name} to Google Drive")


# Get group ID
async def get_group_id(invite_link):
    """
    Retrieves the group ID for a given invite link or group username.

    Args:
        invite_link (str): The Telegram group invite link or username.

    Returns:
        dict: A dictionary containing group ID and title.
    """
    await client.start()
    entity = await client.get_entity(invite_link)

    # Prepare the dictionary with the information we need
    group_info = {"group_id": entity.id, "title": entity.title}

    # Include access_hash if it exists
    if hasattr(entity, "access_hash"):
        group_info["access_hash"] = entity.access_hash

    return group_info


# Download and upload media
async def download_and_upload_media(group_id, drive):
    # Ensure directory exists
    os.makedirs("downloads", exist_ok=True)

    print("Connecting to Telegram...")
    await client.start()
    print("Connected!")

    print(f"Downloading and uploading media from group ID: {group_id}")
    async for message in client.iter_messages(
        group_id, filter=InputMessagesFilterPhotos()
    ):
        if message.photo:
            file_path = await client.download_media(message.photo, file="downloads/")
            print("Downloaded:", file_path)
            upload_file_to_drive(drive, file_path)

    async for message in client.iter_messages(
        group_id, filter=InputMessagesFilterVideo()
    ):
        if message.video:
            file_path = await client.download_media(message.video, file="downloads/")
            print("Downloaded:", file_path)
            upload_file_to_drive(drive, file_path)

    async for message in client.iter_messages(
        group_id, filter=InputMessagesFilterDocument()
    ):
        if message.document:
            file_path = await client.download_media(message.document, file="downloads/")
            print("Downloaded:", file_path)
            upload_file_to_drive(drive, file_path)

    print("All media processed!")


# Main script
if __name__ == "__main__":

    async def main():
        # Authenticate Google Drive
        print("Authenticating Google Drive...")
        drive = authenticate_google_drive()

        # Get group details
        group_info = await get_group_id(group_invite_link)
        group_id = group_info["group_id"]
        print(f"Group ID: {group_id}, Title: {group_info['title']}")

        # Download and upload media from the group
        await download_and_upload_media(group_id, drive)

    # Run the Telegram-related tasks
    with client:
        client.loop.run_until_complete(main())
