import psycopg2
import requests
import json
import datetime as dt
from datetime import datetime
import pytz
import os

# Define database connection details
server = 'localhost'
database = 'BorderScan'
driver = None  # You may need to change the driver name based on your configuration
conn = psycopg2.connect(host="localhost", database="BorderScan", user="postgres", password="263716", port=5432)
cursor = conn.cursor()
# Set up Telegram Bot API
bot_token = os.environ.get("BOT_TOKEN")
bot_url = 'https://api.telegram.org/bot{}'.format(bot_token)

# Set up timezones
minsk_timezone = pytz.timezone('Europe/Minsk')
utc_timezone = pytz.timezone('UTC')

# Define command handlers
def handle_count(chat_id):
    day_from = datetime.now(minsk_timezone).replace(tzinfo=None).replace(microsecond=0).replace(' ', 'T') - dt.timedelta(minutes=5)
    query = f"\
            SELECT COUNT(*) as count\
            FROM CarQueue\
            WHERE last_checked > '{day_from}'\
            "
    cursor.execute(query)
    rows = cursor.fetchall()
    count = rows[0].count
    message = 'Count of currently registered cars: {}'.format(count)
    send_message(chat_id, message)

def handle_score(chat_id, date):
    day_from = datetime.now(minsk_timezone).replace(tzinfo=None).replace(microsecond=0) - dt.timedelta(days=1)
    day_to = datetime.now(minsk_timezone).replace(tzinfo=None).replace(microsecond=0)
    if(date != None):
        day_from = datetime.strptime(date, '%d.%m.%Y').replace(hour=0, minute=0, second=0, microsecond=0)
        day_to = day_from + dt.timedelta(days=1)
    query = f"\
            SELECT registration_date, regnum, last_checked\
            FROM CarQueue\
            WHERE registration_date > '{day_from}' AND registration_date < '{day_to}'\
            "
    cursor.execute(query)
    rows = cursor.fetchall()
    day_count = len(rows)
    hour_rate = day_count / 24
    message = 'Cars went through within a day: {}\nHourly: {}'.format(day_count, hour_rate)
    send_message(chat_id, message)

def handle_rating(chat_id):
    query = """
            SELECT TOP 10 regnum, COUNT(*) as count
            FROM CarQueue
            GROUP BY regnum
            ORDER BY count DESC
            """
    cursor.execute(query)
    rows = cursor.fetchall()
    message = 'Top 10 car registrations:\n'
    for row in rows:
        message += '{} - {}\n'.format(row.regnum, row.count)
    send_message(chat_id, message)

def handle_info(chat_id, rownum):
    query = """
            SELECT TOP 10 registration_date, regnum, last_checked
            FROM CarQueue
            WHERE regnum = ?
            ORDER BY registration_date DESC
            """
    cursor.execute(query, rownum)
    rows = cursor.fetchall()
    message = 'Last 10 car registrations with regnum {}:\n'.format(rownum)
    for row in rows:
        message += '{} - {} - {}\n'.format(row.registration_date, row.regnum, row.last_checked)
    send_message(chat_id, message)

def handle_last(chat_id, rownum):
    query = """
            SELECT TOP 1 registration_date, regnum, last_checked
            FROM CarQueue
            WHERE regnum = ?
            ORDER BY registration_date DESC
            """
    cursor.execute(query, rownum)
    row = cursor.fetchone()
    last_checked = minsk_timezone.localize(row.last_checked)
    message = 'Last car registration with regnum {}:\n'.format(rownum)
    if row:
        message += '{} - {} - {}\n'.format(row.registration_date, row.regnum, row.last_checked)
        current_time = datetime.now(minsk_timezone)
        if last_checked < current_time - dt.timedelta(minutes=5):
            message += 'Last checked more than 5 minutes ago'
    else:
        message += 'No car registrations found with regnum {}'.format(rownum)
    send_message(chat_id, message)

# Define message sender
def send_message(chat_id, message):
    url = '{}/sendMessage'.format(bot_url)
    data = {'chat_id': chat_id, 'text': message}
    response = requests.post(url, json=data)
    return response.json()

# Set up webhook handler
def handle_webhook(data):
    update = json.loads(data)
    chat_id = update['message']['chat']['id']
    text = update['message']['text']
    if text.startswith('/rating'):
        handle_rating(chat_id)
    elif text.startswith('/info'):
        split = text.split()
        if(len(split) != 2):
            send_message(chat_id, 'Incorrect number of parameters, expected required "regnum"')
            return
        handle_info(chat_id, split[1])
    elif text.startswith('/last'):
        split = text.split()
        if(len(split) != 2):
            send_message(chat_id, 'Incorrect number of parameters, expected required "regnum"')
            return
        handle_last(chat_id, split[1])
    elif text.startswith('/score'):
        split = text.split()
        if(len(split) == 1):
            handle_score(chat_id, None)
        elif(len(split) == 2):
            handle_score(chat_id, split[1])
        else:
            send_message(chat_id, 'Incorrect number of parameters, expected not required "date" in format "dd.mm.yyyy"')
    elif text.startswith('/count'):
        handle_count(chat_id)

# Start webhook listener
import subprocess
import re

# Run the ngrok command and capture the output
output = subprocess.check_output(['ngrok', 'http', '50077', '--host-header=50077'])

# Convert the output to a string and split it by newlines
output_str = output.decode('utf-8')
output_lines = output_str.split('\n')

# Find the line that contains the ngrok URL
url_line = next(line for line in output_lines if 'Forwarding' in line)

# Extract the ngrok URL from the line
ngrok_url = url_line.split(' ')[1]

webhook_url = ngrok_url
webhook_listen_url = '{}:443/'.format(webhook_url)

def start_webhook():
    url = '{}/setWebhook?url={}'.format(bot_url, webhook_url)
    response = requests.post(url)
    print(response.json())

def stop_webhook():
    url = '{}/deleteWebhook'.format(bot_url)
    response = requests.post(url)
    print(response.json())

def handle_request(request):
    data = request.get_data().decode('utf-8')
    handle_webhook(data)
    return 'OK'

start_webhook()

from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['POST'])
def index():
    try:
        handle_request(request)
    finally:
        return ""

if __name__ == '__main__':
    app.run(port=50077)