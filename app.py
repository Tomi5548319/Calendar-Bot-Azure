# Azure web API for Calendar bot
# Made by maCRO Tomi
from __future__ import print_function
from urllib.request import urlopen

from flask import Flask, render_template, request, redirect, url_for
import platform
import requests
import os  # Import the os module.
from datetime import datetime

import datetime
from dotenv import dotenv_values

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def connect(discord_id: int) -> bool:
    """Connects a google account to discord_id
    """
    if discord_id is None:
        return False

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(get_calendar_directory(folder='tokens', file=str(discord_id) + '.json')):
        creds = Credentials.from_authorized_user_file(get_calendar_directory(folder='tokens', file=str(discord_id) + '.json'), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    get_calendar_directory(file='credentials.json'), SCOPES)
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                print("No file credentials.json found")
                return False
        # Save the credentials for the next run
        with open(get_calendar_directory(folder='tokens', file=str(discord_id) + '.json'), 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            return True

        # Prints the start and name of the next 10 events
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

    except HttpError as error:
        print('An error occurred: %s' % error)
        return False
    return True


def disconnect(discord_id: int) -> bool:
    """Disconnects a google account from discord_id
    """
    if discord_id is None:
        return False

    file_route = get_calendar_directory(folder='tokens', file=str(discord_id) + '.json')

    if os.path.exists(file_route):
        os.remove(file_route)
        return True
    return False


app = Flask(__name__)
# TODO create credentials file in home
# TODO create .env file in home (password)


@app.route('/connect/<string:discord_id>/', methods=['GET'])
def connect_discord(discord_id: str):
    try:
        int_discord_id = int(discord_id)

        if connect(int_discord_id):
            return "connected"
    except ValueError:
        return "\"" + str(discord_id) + "\" is not a number"
    return "error occured"


@app.route('/disconnect/', methods=['POST'])
def disconnect_discord():
    try:
        data = request.get_json()
        password = data['password']

        if access_granted(password):
            int_discord_id = int(data['dc_id'])

            if disconnect(int_discord_id):
                return "Disconnected"
            else:
                return "Not connected"
        else:
            print("Incorrect password")
    except Exception as e:
        print(str(e))

    return "error occured"


def get_calendar_directory(folder: str = None, file: str = None, create_file: bool = False) -> str:
    path = '/' if platform.system() == "Linux" else ''

    path += 'home/calendar-bot'

    if folder is not None:
        path += '/' + folder

    if not os.path.exists(path):
        os.makedirs(path)

    if file is not None:
        path += '/' + file
        if create_file:
            f = open(path, "a")
            f.close()

    return path


def log(log_text: str):
    f = open(get_calendar_directory(file='logs.txt', create_file=True), "a")
    f.write(str(datetime.strptime(urlopen('http://just-the-time.appspot.com/').read().strip().decode('utf-8'),
                                  '%Y-%m-%d %H:%M:%S')) + '|' + log_text + '\n')
    f.close()


def access_granted(password: str) -> bool:
    local_pass = dotenv_values(get_calendar_directory(file='.env'))["PASS"]

    return local_pass == password


if __name__ == '__main__':
    app.run()
