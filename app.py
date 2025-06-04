from flask import Flask, request, jsonify, render_template
import requests
import subprocess
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


################### WEBSITE PAGES################################3

@app.route('/')
def dashboard():
    return render_template('index.html')














########################################### INGESTION OF DATA ###########################3
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
        return jsonify({'error': 'Missing temperature, humidity or sector_id'}), 400

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

@app.route('/plant-ingest', methods=['POST'])
def plant_ingest():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid or missing JSON data'}), 400

    # Extract values from JSON
    sector_id = data.get('sector_id')
    height_cm = data.get('height_cm')

    if sector_id is None or height_cm is None:
        return jsonify({'error': 'Missing sector_id or height_cm'}), 400

    try:
        # Connect to MariaDB
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Insert into plant table
        insert_query = """
            INSERT INTO plant (sector_id, height_cm, timestamp)
            VALUES (%s, %s, %s)
        """
        current_time = datetime.now()
        cursor.execute(insert_query, (sector_id, height_cm, current_time))
        conn.commit()

        return jsonify({'message': 'Plant data inserted successfully'}), 201

    except Error as e:
        print("Error while inserting plant data:", e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/leaf-ingest', methods=['POST'])
def leaf_ingest():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid or missing JSON data'}), 400

    sector_id = 1
    leaf_count = data.get('leaf_count')

    if sector_id is None or leaf_count is None:
        return jsonify({'error': 'Missing sector_id or leaf_count'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO leaf_count (sector_id, leaf_count, timestamp)
            VALUES (%s, %s, %s)
        """
        current_time = datetime.now()
        cursor.execute(insert_query, (sector_id, leaf_count, current_time))
        conn.commit()

        return jsonify({'message': 'Leaf count inserted successfully'}), 201

    except Error as e:
        print("Database error:", e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

























################################################# PUBLISHER - BUTTON TO ACTUATOR #############################3


# Command publisher endpoint (assuming it runs on port 5001)
COMMAND_PUBLISHER_URL = "http://localhost:5001"

@app.route('/api/water-plants', methods=['POST'])
def water_plants():
    """Forward watering commands to command publisher"""
    try:
        data = request.get_json() or {}
        
        # Forward to command publisher
        response = requests.post(f"{COMMAND_PUBLISHER_URL}/api/water-plants", json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            # Log command to database for tracking
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO control_commands (command_type, sector_id, duration, timestamp, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            current_time = datetime.now()
            cursor.execute(insert_query, (
                'MANUAL_WATERING', 
                data.get('sector', 1), 
                data.get('duration', 10), 
                current_time, 
                'SUCCESS'
            ))
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify(result)
        else:
            return jsonify({'error': 'Command publisher unavailable'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/toggle-fan', methods=['POST'])
def toggle_fan():
    """Forward fan control commands"""
    try:
        data = request.get_json() or {}
        
        # Forward to command publisher
        response = requests.post(f"{COMMAND_PUBLISHER_URL}/api/toggle-fan", json=data, timeout=10)
        
        if response.status_code == 200:
            # Log to database
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO control_commands (command_type, action, timestamp, status)
                VALUES (%s, %s, %s, %s)
            """
            current_time = datetime.now()
            cursor.execute(insert_query, (
                'FAN_CONTROL', 
                data.get('action', 'toggle'), 
                current_time, 
                'SUCCESS'
            ))
            conn.commit()
            cursor.close()
            conn.close()
            
            return response.json()
        else:
            return jsonify({'error': 'Command publisher unavailable'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/toggle-lights', methods=['POST'])
def toggle_lights():
    """Forward light control commands"""
    try:
        data = request.get_json() or {}
        
        # Forward to command publisher
        response = requests.post(f"{COMMAND_PUBLISHER_URL}/api/toggle-lights", json=data, timeout=10)
        
        if response.status_code == 200:
            # Log to database
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO control_commands (command_type, action, brightness, timestamp, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            current_time = datetime.now()
            cursor.execute(insert_query, (
                'LIGHT_CONTROL', 
                data.get('action', 'toggle'),
                data.get('brightness', 100),
                current_time, 
                'SUCCESS'
            ))
            conn.commit()
            cursor.close()
            conn.close()
            
            return response.json()
        else:
            return jsonify({'error': 'Command publisher unavailable'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system-status', methods=['GET'])
def get_system_status():
    """Get current system status from database"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Get latest sensor readings
        queries = {
            'temperature': """
                SELECT temperature, humidity, timestamp 
                FROM ventilation 
                ORDER BY timestamp DESC 
                LIMIT 1
            """,
            'soil_moisture': """
                SELECT sector_id, soil_moisture, timestamp 
                FROM soil_health 
                ORDER BY timestamp DESC 
                LIMIT 3
            """,
            'recent_commands': """
                SELECT command_type, action, timestamp 
                FROM control_commands 
                ORDER BY timestamp DESC 
                LIMIT 5
            """
        }
        
        results = {}
        
        # Execute queries
        for key, query in queries.items():
            cursor.execute(query)
            results[key] = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Format response
        status = {
            'temperature': results['temperature'][0]['temperature'] if results['temperature'] else 0,
            'humidity': results['temperature'][0]['humidity'] if results['temperature'] else 0,
            'soil_moisture': {
                f'sector_{row["sector_id"]}': row['soil_moisture'] 
                for row in results['soil_moisture']
            },
            'recent_commands': results['recent_commands'],
            'last_updated': datetime.now().isoformat()
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add this to create the control_commands table
@app.route('/setup-control-table', methods=['GET'])
def setup_control_table():
    """One-time setup for control commands table"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        create_table_query = """
            CREATE TABLE IF NOT EXISTS control_commands (
                id INT AUTO_INCREMENT PRIMARY KEY,
                command_type VARCHAR(50) NOT NULL,
                sector_id INT DEFAULT NULL,
                duration INT DEFAULT NULL,
                action VARCHAR(20) DEFAULT NULL,
                brightness INT DEFAULT NULL,
                timestamp DATETIME NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDING'
            )
        """
        
        cursor.execute(create_table_query)
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Control commands table created successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


















# Run the app
if __name__ == '__main__':
    app.run(debug=True)  