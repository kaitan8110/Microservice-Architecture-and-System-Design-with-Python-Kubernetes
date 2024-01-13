import os
import json
from email.message import EmailMessage
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def service_gmail():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def create_message(sender, to, subject, message_text):
    message = EmailMessage()
    message.set_content(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    body = {'raw': raw}
    return body

def send_message(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message)
                   .execute())
        print('Message Id: %s' % message['id'])
        return message
    except HttpError as error:
        print(f'An error occurred: {error}')

def notification(message):
    try:
        message = json.loads(message)
        mp3_fid = message["mp3_fid"]
        sender_address = os.environ.get("GMAIL_ADDRESS")
        receiver_address = message["username"]
        subject = "MP3 Download"
        message_text = f"mp3 file_id: {mp3_fid} is now ready!"

        service = service_gmail()
        if service:
            msg = create_message(sender_address, receiver_address, subject, message_text)
            send_message(service, "me", msg)

    except Exception as err:
        print(err)

# import smtplib, os, json
# from email.message import EmailMessage

# def notification(message):
#     try:
#         message = json.loads(message)
#         mp3_fid = message["mp3_fid"]
#         sender_address = os.environ.get("GMAIL_ADDRESS")
#         sender_password = os.environ.get("GMAIL_PASSWORD")
#         receiver_address = message["username"]

#         msg = EmailMessage()
#         msg.set_content(f"mp3 file_id: {mp3_fid} is now ready!")
#         msg["Subject"] = "MP3 Download"
#         msg["From"] = sender_address
#         msg["To"] = receiver_address

#         session = smtplib.SMTP("smtp.gmail.com")
#         session.starttls()
#         session.login(sender_address, sender_password)
#         session.send_message(msg, sender_address, receiver_address)
#         session.quit()
#         print("Mail Sent")

#     except Exception as err:
#         print(err)
#         return err
    
    



        