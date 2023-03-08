import requests
import json
import psycopg2
from datetime import datetime, timedelta
import time

while(True):
    # Define database connection details
    server = 'localhost'
    database = 'BorderScan'
    driver = None  # You may need to change the driver name based on your configuration

    # Define API endpoint and headers
    url = 'https://belarusborder.by/info/monitoring-new?token=test&checkpointId=a9173a85-3fc0-424c-84f0-defa632481e4'
    headers = {'Content-type': 'application/json'}

    # Connect to database
    conn = psycopg2.connect(host="localhost", database="BorderScan", user="postgres", password="263716", port=5432)
    cursor = conn.cursor()
    print('Connected to the database.')

    # Define function to insert data into database
    def insert_data(registration_date, regnum):
        query = f"INSERT INTO CarQueue (registration_date, regnum, last_checked) VALUES ('{registration_date}', '{regnum}', (SELECT NOW() AT TIME ZONE 'Europe/Minsk'))"
        cursor.execute(query)
        conn.commit()

    # Define function to update data in database
    def update_data(registration_date, regnum):
        query = f"UPDATE CarQueue SET last_checked=(SELECT NOW() AT TIME ZONE 'Europe/Minsk') WHERE registration_date='{registration_date}' AND regnum='{regnum}'"
        cursor.execute(query)
        conn.commit()

    # Define function to check if data already exists in database
    def check_data(registration_date, regnum):
        query = f"SELECT COUNT(*) FROM CarQueue WHERE registration_date='{registration_date}' AND regnum='{regnum}'"
        cursor.execute(query)
        row = cursor.fetchone()
        return row[0] > 0

    # Main loop to periodically fetch data from API and insert into database
    data = {}
    while True:
        try:
            # Send GET request to API endpoint and parse JSON response
            print('Sending the request...')
            response = requests.get(url, headers=headers)
            data = json.loads(response.text)
            print('Response received.')

            # Loop through carLiveQueue and insert new data into database
            for car in data['carLiveQueue']:
                registration_date = datetime.strptime(car['registration_date'], '%H:%M:%S %d.%m.%Y')
                regnum = car['regnum']
                if check_data(registration_date, regnum):
                    update_data(registration_date, regnum)
                else:
                    insert_data(registration_date, regnum)

        except Exception as e:
            print('Error:', e)
            print('Data:', data)
            print('Waiting for 5 minutes...')
            time.sleep(300)
            break

        # Wait for 5 minutes before making another request
        print('Waiting for 5 minutes...')
        time.sleep(300)