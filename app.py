from flask import Flask, request, jsonify, render_template
import mysql.connector
from mysql.connector import Error
from datetime import datetime
app = Flask(__name__)



db_config = {
    'host': 'localhost',      # or your DB host IP
    'user': 'admin',
    'password': 'StrongPasswordHere',
    'database': 'greenhouse',
}


@app.route('/')
def dashboard():
    return render_template('index.html')


@app.route('/temperature-ingest', methods=['POST'])
def temperature_ingest():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid or missing JSON data'}), 400

    # Extract values from JSON
    temperature = data.get('temperature')
    humidity = data.get('humidity')
    sector_id = 1  # make sure client sends this

    if temperature is None or humidity is None or sector_id is None:
        return jsonify({'error': 'Missing temperature, humidity or sector_id'})>

    try:
        # Connect to MariaDB
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        # Insert into ventilation table
        insert_query = """
            INSERT INTO ventilation (sector_id, temperature, humidity, timestamp)
            VALUES (%s, %s, %s, %s)
        """
        current_time = datetime.now()
        cursor.execute(insert_query, (sector_id, temperature, humidity, current_time))
        conn.commit()

        return jsonify({'message': 'Data inserted successfully'}), 201

    except Error as e:
        print("Error while inserting data:", e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/soil-ingest', methods=['POST'])
def soil_health_ingest():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid or missing JSON data'}), 400

    # Extract values
    raw_value = data.get('raw_value')
    soil_moisture = data.get('soil_moisture')
    sector_id = data.get('sector_id')  # replace or make dynamic if needed

    if raw_value is None or soil_moisture is None or sector_id is None:
        return jsonify({'error': 'Missing raw_value, soil_moisture, or sector_id'}), 400

    try:
        # Connect to MariaDB
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Insert into soil_health table
        insert_query = """
            INSERT INTO soil_health (sector_id, raw_value, soil_moisture, timestamp)
            VALUES (%s, %s, %s, %s)
        """
        current_time = datetime.now()
        cursor.execute(insert_query, (sector_id, raw_value, soil_moisture, current_time))
        conn.commit()

        return jsonify({'message': 'Soil health data inserted successfully'}), 201

    except Error as e:
        print("Error while inserting soil health data:", e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



# Run the app
if __name__ == '__main__':
    app.run(debug=True)  