# Azure web API for Calendar bot
# Made by maCRO Tomi
from __future__ import print_function
from urllib.request import urlopen

from flask import Flask, render_template, request, redirect, url_for, session
import platform
import os  # Import the os module.
from datetime import datetime

import datetime
from dotenv import dotenv_values

# pip install google
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

app = Flask(__name__)
app.secret_key = 'abraka dabra test'
# TODO create credentials file in home
# TODO create .env file in home (password)


@app.route('/', methods=['GET'])
def index():
    return "Site is up!"


@app.route('/oauth2callback/', methods=['GET'])
def oauth2callback():
    print("OAuth2 done")
    state = session['state']
    flow = Flow.from_client_secrets_file(
        get_calendar_directory(file='credentials.json'),
        scopes=SCOPES,
        state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_response = request.url
    if authorization_response.startswith('http:'):
        authorization_response = 'https:' + authorization_response[5:]
    print(authorization_response)
    flow.fetch_token(authorization_response=authorization_response)

    # Store the credentials in the session.
    # ACTION ITEM for developers:
    #     Store user's access and refresh tokens in your data store if
    #     incorporating this code into your real app.
    credentials = flow.credentials
    print(str(credentials.to_json()))
    return "OAuth2 done"


@app.route('/connect/<string:discord_id>/', methods=['GET'])
def connect_discord(discord_id: str):
    try:
        int_discord_id = int(discord_id)

        """Connects a google account to discord_id
            """
        print("Here")
        if discord_id is None:
            return False

        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(get_calendar_directory(folder='tokens', file=str(discord_id) + '.json')):
            creds = Credentials.from_authorized_user_file(
                get_calendar_directory(folder='tokens', file=str(discord_id) + '.json'), SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(get_calendar_directory(file='credentials.json'),
                                                                     SCOPES)
                    flow.redirect_uri = url_for('oauth2callback', _external=True)
                    print("Starting")
                    # Generate URL for request to Google's OAuth 2.0 server.
                    # Use kwargs to set optional request parameters.
                    authorization_url, state = flow.authorization_url(
                        # Enable offline access so that you can refresh an access token without
                        # re-prompting the user for permission. Recommended for web server apps.
                        access_type='offline',
                        # Enable incremental authorization. Recommended as a best practice.
                        include_granted_scopes='true')

                    # Store the state so the callback can verify the auth server response.
                    session['state'] = state

                    return redirect(authorization_url)
                    # print(response)
                except FileNotFoundError:
                    print("No file credentials.json found")
                    return False
            # Save the credentials for the next run
            if creds is not None:
                with open(get_calendar_directory(folder='tokens', file=str(discord_id) + '.json'), 'w') as token:
                    token.write(creds.to_json())
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
    # os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run()


def connect(discord_id: int) -> bool:


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
        os.remove(file_route)
        return True
    return False
