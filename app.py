# Azure web API for Calendar bot
# Made by maCRO Tomi
from __future__ import print_function
from urllib.request import urlopen

import requests
from flask import Flask, render_template, request, redirect, url_for, session
import platform
import os  # Import the os module.
from datetime import datetime, timedelta
from dateutil import parser

import json
from dotenv import dotenv_values

# pip install google
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

app = Flask(__name__)
app.secret_key = 'abraka dabra test'
# TODO create credentials file in home
# TODO create .env file in home (password)


@app.route('/', methods=['GET'])
def index():
    return "Site is up!"


@app.route('/oauth2callback/', methods=['GET'])
def oauth2callback():
    try:
        state = session['state']
        discord_id = int(session['dc_id'])

        flow = Flow.from_client_secrets_file(
            get_calendar_directory(file='credentials.json'),
            scopes=SCOPES,
            state=state)
        flow.redirect_uri = url_for('oauth2callback', _external=True)

        authorization_response = request.url
        if authorization_response.startswith('http:'):
            authorization_response = 'https:' + authorization_response[5:]
        flow.fetch_token(authorization_response=authorization_response)

        # Store the credentials in the session.
        # ACTION ITEM for developers:
        #     Store user's access and refresh tokens in your data store if
        #     incorporating this code into your real app.
        credentials = flow.credentials

        # Save the credentials for the next run
        if credentials is not None:
            with open(get_calendar_directory(folder='tokens', file=str(discord_id) + '.json'), 'w') as token:
                token.write(credentials.to_json())

        return "You have successfully connected your google account to the Google Calendar Bot, you may close this window."
    except Warning as w:
        print(str(w))

    return ""


@app.route('/connect/<string:auth_token>/', methods=['GET'])
def connect_discord(auth_token: str):
    """Connects a google account to discord_id
    """

    if auth_token is None:
        return "No token"

    if os.path.exists(get_calendar_directory(folder="incoming_connections", file=str(auth_token)+'.json')):

        with open(get_calendar_directory(folder="incoming_connections", file=str(auth_token)+'.json'), 'r') as f:
            connection = json.load(f)

            int_discord_id = int(connection['dc_id'])
            expiry = parser.parse(connection['expiry'])
            now = parser.parse(datetime.utcnow().isoformat() + 'Z')

        os.remove(get_calendar_directory(folder="incoming_connections", file=str(auth_token) + '.json'))
        if expiry < now:
            return "Link expired, please generate a new one"

        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.

        creds = get_credentials(int_discord_id)
        if creds is not None:
            return "You are already connected"

        return create_credentials(int_discord_id)
    return "Link expired, please generate a new one"


@app.route('/disconnect/', methods=['POST'])
def disconnect_discord():
    try:
        data = request.get_json()
        password = data['password']

        if access_granted(password):
            int_discord_id = int(data['discord_id'])

            if disconnect(int_discord_id):
                return "Disconnected"
            else:
                return "Not connected"
        else:
            return "Incorrect password"
    except Exception as e:
        print(str(e))

    return "error occured"


@app.route('/incoming_connection/', methods=['POST'])
def incoming_connection():
    try:
        data = request.get_json()
        password = data['password']
        dc_id = int(data['discord_id'])
        auth_token = data['auth_token']

        if access_granted(password):
            with open(get_calendar_directory(folder="incoming_connections", file=str(auth_token)+'.json', create_file=True, file_default_content='{}'), 'w') as f:
                connection = {
                    "dc_id": dc_id,
                    "expiry": (datetime.utcnow() + timedelta(minutes=15)).isoformat() + 'Z'
                }
                f.write(json.dumps(connection))
                return "Success"

        else:
            return "Incorrect password"
    except Exception as e:
        print(str(e))

    return "error occured"


@app.route('/is_connected/', methods=['POST'])
def is_connected_dc():
    try:
        data = request.get_json()
        password = data['password']
        dc_id = int(data['discord_id'])

        if access_granted(password):
            return str(get_credentials(dc_id) is not None)

        else:
            return "Incorrect password"
    except Exception as e:
        print(str(e))

    return "error occured"


@app.route('/now/', methods=['POST'])
def event_now():
    try:
        data = request.get_json()
        password = data['password']
        dc_id = int(data['discord_id'])
        event_summary = data['summary']

        if access_granted(password):
            creds = get_credentials(dc_id)
            if creds is None:
                return "No credentials"

            with open(get_calendar_directory(folder="events", file=str(dc_id) + '.json', create_file=True, file_default_content='[]'), "r+") as f:
                events = json.load(f)
                event = {
                    'summary': event_summary,
                    'start': {
                        'dateTime': datetime.utcnow().isoformat() + 'Z'
                    }
                }

                # Add the event and save it, just in case an error occures later
                events.append(event)
                f.seek(0)
                f.write(json.dumps(events))

                page_token = None
                calendar = None
                cal_summary = 'Diary (BOT)'

                service = build('calendar', 'v3', credentials=creds)
                while True:
                    calendar_list = service.calendarList().list(pageToken=page_token, minAccessRole='owner').execute()
                    page_token = calendar_list.get('nextPageToken')

                    for calendar_list_entry in calendar_list['items']:
                        if calendar_list_entry['summary'] == cal_summary:
                            calendar = calendar_list_entry
                            page_token = None
                            break

                    if not page_token:
                        break

                if calendar is None:
                    calendar = service.calendars().insert(body={'summary': cal_summary}).execute()

                if calendar is not None:
                    for event_id, curr_event in enumerate(events[:-1]):
                        # print(str(event['summary']) + ': ' + str(event['start']['dateTime']) + '-' + str(events[event_id + 1]['start']['dateTime']))
                        cal_event = {
                            'summary': curr_event['summary'],
                            'start': curr_event['start'],
                            'end': events[event_id + 1]['start']
                        }

                        service.events().insert(calendarId=calendar['id'], body=cal_event).execute()

                    f.seek(0)
                    f.write(json.dumps([event]))

                    return "Success"
                else:
                    return "Unable to connect to calendar"
        else:
            return "Incorrect password"
    except Exception as e:
        print(str(e))

    return "error occured"


def create_credentials(discord_id: int):
    try:
        flow = InstalledAppFlow.from_client_secrets_file(get_calendar_directory(file='credentials.json'),
                                                         SCOPES)
        flow.redirect_uri = url_for('oauth2callback', _external=True)
        # Generate URL for request to Google's OAuth 2.0 server.
        # Use kwargs to set optional request parameters.
        authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='false')

        # Store the state so the callback can verify the auth server response.
        session['state'] = state
        session['dc_id'] = str(discord_id)

        return redirect(authorization_url)
        # print(response)
    except FileNotFoundError:
        print("No file credentials.json found")
        return False


def token_exists(dc_id: int):
    return os.path.exists(get_calendar_directory(folder='tokens', file=str(dc_id) + '.json'))


def get_credentials(discord_id: int):
    creds = None
    if token_exists(discord_id):
        creds = Credentials.from_authorized_user_file(
                get_calendar_directory(folder='tokens', file=str(discord_id) + '.json'), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return None

    return creds


def get_calendar_directory(folder: str = None, file: str = None, create_file: bool = False, file_default_content: str = None) -> str:
    path = '/' if platform.system() == "Linux" else ''

    path += 'home/calendar-bot'

    if folder is not None:
        path += '/' + folder

    if not os.path.exists(path):
        os.makedirs(path)

    if file is not None:
        path += '/' + file
        if not os.path.exists(path) and create_file:
            f = open(path, "a")
            if file_default_content is not None:
                f.write(file_default_content)
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
    # os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run()


def connect() -> bool:

    # try:
    #     service = build('calendar', 'v3', credentials=creds)
    #
    #     # Call the Calendar API
    #     now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    #     print('Getting the upcoming 10 events')
    #     events_result = service.events().list(calendarId='primary', timeMin=now,
    #                                           maxResults=10, singleEvents=True,
    #                                           orderBy='startTime').execute()
    #     events = events_result.get('items', [])
    #
    #     if not events:
    #         print('No upcoming events found.')
    #         return True
    #
    #     # Prints the start and name of the next 10 events
    #     for event in events:
    #         start = event['start'].get('dateTime', event['start'].get('date'))
    #         print(start, event['summary'])
    #
    # except HttpError as error:
    #     print('An error occurred: %s' % error)
    #     return False
    return True


def disconnect(discord_id: int) -> bool:
    """Disconnects a google account from discord_id
    """
    if discord_id is None:
        return False

    file_route = get_calendar_directory(folder='tokens', file=str(discord_id) + '.json')

    if os.path.exists(file_route):
        creds = get_credentials(discord_id)
        if creds is not None:
            requests.post('https://oauth2.googleapis.com/revoke',
                          params={'token': creds.token},
                          headers={'content-type': 'application/x-www-form-urlencoded'})

            os.remove(file_route)
            return True
    return False
