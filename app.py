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


# #### FOR TESTING ###
# # connects to cloud database from local pc
# db_config = {
#     'host': '34.199.73.137',  # Your EC2 public IP
#     'port': 3306,
#     'user': 'admin',
#     'password': 'StrongPasswordHere',
#     'database': 'greenhouse',
#     'autocommit': True,
#     'connection_timeout': 30,
#     'raise_on_warnings': True
# }


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


COMMAND_PUBLISHER_URL = "http://localhost:5001"

@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    """Get comprehensive dashboard data from database"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Get latest temperature and humidity
        cursor.execute("""
            SELECT temperature, humidity, timestamp 
            FROM ventilation 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        latest_ventilation = cursor.fetchone()
        
        # Get latest soil moisture per sector
        cursor.execute("""
            SELECT DISTINCT s1.sector_id, s1.raw_value, s1.soil_moisture, s1.timestamp
            FROM soil_health s1
            INNER JOIN (
                SELECT sector_id, MAX(timestamp) as max_timestamp
                FROM soil_health
                GROUP BY sector_id
            ) s2 ON s1.sector_id = s2.sector_id AND s1.timestamp = s2.max_timestamp
            ORDER BY s1.sector_id
        """)
        latest_soil = cursor.fetchall()
        
        # Get latest plant heights per sector
        cursor.execute("""
            SELECT DISTINCT p1.sector_id, p1.height_cm, p1.timestamp
            FROM plant p1
            INNER JOIN (
                SELECT sector_id, MAX(timestamp) as max_timestamp
                FROM plant
                GROUP BY sector_id
            ) p2 ON p1.sector_id = p2.sector_id AND p1.timestamp = p2.max_timestamp
            ORDER BY p1.sector_id
        """)
        latest_plants = cursor.fetchall()
        
        # Get latest leaf count
        cursor.execute("""
            SELECT leaf_count, timestamp 
            FROM leaf_count 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        latest_leaf_count = cursor.fetchone()
        
        # Get temperature and humidity trend (last 24 hours, 1 reading per hour)
        cursor.execute("""
            SELECT 
                AVG(temperature) as temperature,
                AVG(humidity) as humidity,
                DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') as hour_timestamp
            FROM ventilation 
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY DATE_FORMAT(timestamp, '%Y-%m-%d %H')
            ORDER BY hour_timestamp ASC
        """)
        temp_trend = cursor.fetchall()
        
        # Get plant growth trend (last 7 days)
        cursor.execute("""
            SELECT sector_id, height_cm, timestamp
            FROM plant 
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY timestamp ASC
        """)
        plant_trend = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Format response
        dashboard_data = {
            'current_conditions': {
                'temperature': float(latest_ventilation['temperature']) if latest_ventilation else 0,
                'humidity': float(latest_ventilation['humidity']) if latest_ventilation else 0,
                'last_updated': latest_ventilation['timestamp'].isoformat() if latest_ventilation else None
            },
            'soil_moisture': {
                'current': {
                    f'sector_{row["sector_id"]}': {
                        'moisture_percent': row['soil_moisture'],
                        'raw_value': row['raw_value'],
                        'status': get_soil_status(row['soil_moisture']),
                        'timestamp': row['timestamp'].isoformat()
                    } for row in latest_soil
                }
            },
            'plant_heights': {
                'current': {
                    f'sector_{row["sector_id"]}': {
                        'height_cm': float(row['height_cm']),
                        'growth_stage': get_growth_stage(float(row['height_cm'])),
                        'timestamp': row['timestamp'].isoformat()
                    } for row in latest_plants
                },
                'trend_7d': [
                    {
                        'sector_id': row['sector_id'],
                        'height_cm': float(row['height_cm']),
                        'timestamp': row['timestamp'].isoformat()
                    } for row in plant_trend
                ]
            },
            'leaf_count': {
                'current': latest_leaf_count['leaf_count'] if latest_leaf_count else 0,
                'timestamp': latest_leaf_count['timestamp'].isoformat() if latest_leaf_count else None
            },
            'environmental_trend': [
                {
                    'temperature': round(float(row['temperature']), 1),
                    'humidity': round(float(row['humidity']), 1),
                    'timestamp': row['hour_timestamp']
                } for row in temp_trend
            ]
        }
        
        return jsonify(dashboard_data)
        
    except Error as e:
        print(f"Database error in dashboard-data: {e}")
        return jsonify({'error': 'Database connection failed'}), 500
    except Exception as e:
        print(f"General error in dashboard-data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get system alerts based on current conditions"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        alerts = []
        
        # Check for dry soil (moisture < 30%)
        cursor.execute("""
            SELECT DISTINCT s1.sector_id, s1.soil_moisture
            FROM soil_health s1
            INNER JOIN (
                SELECT sector_id, MAX(timestamp) as max_timestamp
                FROM soil_health
                GROUP BY sector_id
            ) s2 ON s1.sector_id = s2.sector_id AND s1.timestamp = s2.max_timestamp
            WHERE s1.soil_moisture < 30
        """)
        dry_sectors = cursor.fetchall()
        
        for sector in dry_sectors:
            alerts.append({
                'type': 'warning',
                'message': f'Sector {sector["sector_id"]} soil moisture is low ({sector["soil_moisture"]}%)',
                'action': 'water_needed',
                'sector_id': sector['sector_id']
            })
        
        # Check for very wet soil (moisture > 80%)
        cursor.execute("""
            SELECT DISTINCT s1.sector_id, s1.soil_moisture
            FROM soil_health s1
            INNER JOIN (
                SELECT sector_id, MAX(timestamp) as max_timestamp
                FROM soil_health
                GROUP BY sector_id
            ) s2 ON s1.sector_id = s2.sector_id AND s1.timestamp = s2.max_timestamp
            WHERE s1.soil_moisture > 80
        """)
        wet_sectors = cursor.fetchall()
        
        for sector in wet_sectors:
            alerts.append({
                'type': 'info',
                'message': f'Sector {sector["sector_id"]} soil moisture is very high ({sector["soil_moisture"]}%)',
                'action': 'drainage_needed',
                'sector_id': sector['sector_id']
            })
        
        # Check for high temperature (> 30°C)
        cursor.execute("""
            SELECT temperature FROM ventilation 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        latest_temp = cursor.fetchone()
        
        if latest_temp and latest_temp['temperature'] > 30:
            alerts.append({
                'type': 'warning',
                'message': f'High temperature detected ({latest_temp["temperature"]}°C)',
                'action': 'fan_activation_recommended'
            })
        
        # Check for low temperature (< 18°C)
        if latest_temp and latest_temp['temperature'] < 18:
            alerts.append({
                'type': 'warning',
                'message': f'Low temperature detected ({latest_temp["temperature"]}°C)',
                'action': 'heating_recommended'
            })
        
        # Check for no recent data (last reading > 1 hour ago)
        cursor.execute("""
            SELECT TIMESTAMPDIFF(MINUTE, MAX(timestamp), NOW()) as minutes_since_last
            FROM ventilation
        """)
        last_reading = cursor.fetchone()
        
        if last_reading and last_reading['minutes_since_last'] > 60:
            alerts.append({
                'type': 'warning',
                'message': f'No sensor data received for {last_reading["minutes_since_last"]} minutes',
                'action': 'check_sensor_connectivity'
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({'alerts': alerts, 'count': len(alerts)})
        
    except Error as e:
        print(f"Database error in alerts: {e}")
        return jsonify({'alerts': [], 'count': 0})
    except Exception as e:
        print(f"General error in alerts: {e}")
        return jsonify({'alerts': [], 'count': 0})

@app.route('/api/water-plants', methods=['POST'])
def water_plants():
    """Manual watering command"""
    try:
        data = request.get_json() or {}
        sector = data.get('sector', 1)
        duration = data.get('duration', 10)
        
        # Validate input
        if sector not in [1, 2, 3] or duration < 1 or duration > 60:
            return jsonify({'error': 'Invalid sector (1-3) or duration (1-60 seconds)'}), 400
        
        # Log command to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Create control_commands table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_commands (
                id INT AUTO_INCREMENT PRIMARY KEY,
                command_type VARCHAR(50) NOT NULL,
                sector_id INT DEFAULT NULL,
                duration INT DEFAULT NULL,
                action VARCHAR(20) DEFAULT NULL,
                brightness INT DEFAULT NULL,
                timestamp DATETIME NOT NULL,
                status VARCHAR(20) DEFAULT 'SUCCESS'
            )
        """)
        
        # Insert command log
        insert_query = """
            INSERT INTO control_commands (command_type, sector_id, duration, timestamp, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        current_time = datetime.now()
        cursor.execute(insert_query, ('MANUAL_WATERING', sector, duration, current_time, 'SUCCESS'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Here you would send the actual command to your Arduino
        # For now, we'll simulate success
        return jsonify({
            'success': True,
            'message': f'Watering sector {sector} for {duration} seconds',
            'sector': sector,
            'duration': duration
        })
        
    except Error as e:
        print(f"Database error in water-plants: {e}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        print(f"General error in water-plants: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/toggle-fan', methods=['POST'])
def toggle_fan():
    """Fan control command"""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'toggle')
        
        if action not in ['on', 'off', 'auto', 'toggle']:
            return jsonify({'error': 'Invalid action. Use: on, off, auto, toggle'}), 400
        
        # Log command to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Create table if needed (same as above)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_commands (
                id INT AUTO_INCREMENT PRIMARY KEY,
                command_type VARCHAR(50) NOT NULL,
                sector_id INT DEFAULT NULL,
                duration INT DEFAULT NULL,
                action VARCHAR(20) DEFAULT NULL,
                brightness INT DEFAULT NULL,
                timestamp DATETIME NOT NULL,
                status VARCHAR(20) DEFAULT 'SUCCESS'
            )
        """)
        
        insert_query = """
            INSERT INTO control_commands (command_type, action, timestamp, status)
            VALUES (%s, %s, %s, %s)
        """
        current_time = datetime.now()
        cursor.execute(insert_query, ('FAN_CONTROL', action, current_time, 'SUCCESS'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Fan set to {action.upper()}',
            'action': action
        })
        
    except Exception as e:
        print(f"Error in toggle-fan: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/toggle-lights', methods=['POST'])
def toggle_lights():
    """Light control command"""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'toggle')
        brightness = data.get('brightness', 80)
        
        if action not in ['on', 'off', 'auto', 'toggle']:
            return jsonify({'error': 'Invalid action. Use: on, off, auto, toggle'}), 400
        
        if brightness < 0 or brightness > 100:
            return jsonify({'error': 'Brightness must be between 0-100'}), 400
        
        # Log command to database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_commands (
                id INT AUTO_INCREMENT PRIMARY KEY,
                command_type VARCHAR(50) NOT NULL,
                sector_id INT DEFAULT NULL,
                duration INT DEFAULT NULL,
                action VARCHAR(20) DEFAULT NULL,
                brightness INT DEFAULT NULL,
                timestamp DATETIME NOT NULL,
                status VARCHAR(20) DEFAULT 'SUCCESS'
            )
        """)
        
        insert_query = """
            INSERT INTO control_commands (command_type, action, brightness, timestamp, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        current_time = datetime.now()
        cursor.execute(insert_query, ('LIGHT_CONTROL', action, brightness, current_time, 'SUCCESS'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Lights set to {action.upper()} (brightness: {brightness}%)',
            'action': action,
            'brightness': brightness
        })
        
    except Exception as e:
        print(f"Error in toggle-lights: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get system-wide statistics"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Total readings count
        cursor.execute("SELECT COUNT(*) as count FROM ventilation")
        temp_readings = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM soil_health")
        soil_readings = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM plant")
        plant_readings = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM leaf_count")
        leaf_readings = cursor.fetchone()['count']
        
        # Average conditions (last 24 hours)
        cursor.execute("""
            SELECT 
                AVG(temperature) as avg_temp, 
                AVG(humidity) as avg_humidity,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp,
                MIN(humidity) as min_humidity,
                MAX(humidity) as max_humidity
            FROM ventilation 
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        avg_conditions = cursor.fetchone()
        
        # Average soil moisture by sector (last 24 hours)
        cursor.execute("""
            SELECT 
                sector_id, 
                AVG(soil_moisture) as avg_moisture,
                MIN(soil_moisture) as min_moisture,
                MAX(soil_moisture) as max_moisture,
                COUNT(*) as reading_count
            FROM soil_health 
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            GROUP BY sector_id
            ORDER BY sector_id
        """)
        soil_stats = cursor.fetchall()
        
        # Plant growth statistics
        cursor.execute("""
            SELECT 
                sector_id,
                MAX(height_cm) as current_height,
                MIN(height_cm) as initial_height,
                MAX(height_cm) - MIN(height_cm) as total_growth,
                COUNT(*) as measurement_count
            FROM plant 
            GROUP BY sector_id
            ORDER BY sector_id
        """)
        growth_stats = cursor.fetchall()
        
        # Recent command history
        cursor.execute("""
            SELECT command_type, action, sector_id, timestamp, status
            FROM control_commands 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        recent_commands = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        statistics = {
            'total_readings': {
                'temperature': temp_readings,
                'soil_moisture': soil_readings,
                'plant_height': plant_readings,
                'leaf_count': leaf_readings
            },
            'environmental_stats_24h': {
                'temperature': {
                    'average': round(float(avg_conditions['avg_temp']), 1) if avg_conditions['avg_temp'] else 0,
                    'min': round(float(avg_conditions['min_temp']), 1) if avg_conditions['min_temp'] else 0,
                    'max': round(float(avg_conditions['max_temp']), 1) if avg_conditions['max_temp'] else 0
                },
                'humidity': {
                    'average': round(float(avg_conditions['avg_humidity']), 1) if avg_conditions['avg_humidity'] else 0,
                    'min': round(float(avg_conditions['min_humidity']), 1) if avg_conditions['min_humidity'] else 0,
                    'max': round(float(avg_conditions['max_humidity']), 1) if avg_conditions['max_humidity'] else 0
                }
            },
            'soil_stats_24h': {
                f'sector_{row["sector_id"]}': {
                    'average_moisture': round(float(row['avg_moisture']), 1),
                    'min_moisture': round(float(row['min_moisture']), 1),
                    'max_moisture': round(float(row['max_moisture']), 1),
                    'reading_count': row['reading_count']
                } for row in soil_stats
            },
            'plant_growth_stats': {
                f'sector_{row["sector_id"]}': {
                    'current_height': float(row['current_height']),
                    'initial_height': float(row['initial_height']),
                    'total_growth': float(row['total_growth']),
                    'measurement_count': row['measurement_count']
                } for row in growth_stats
            },
            'recent_commands': [
                {
                    'command': row['command_type'],
                    'action': row['action'],
                    'sector_id': row['sector_id'],
                    'timestamp': row['timestamp'].isoformat(),
                    'status': row['status']
                } for row in recent_commands
            ]
        }
        
        return jsonify(statistics)
        
    except Exception as e:
        print(f"Error in statistics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/test-db', methods=['GET'])
def test_database_connection():
    """Test database connectivity and return basic stats"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) as total FROM ventilation")
        ventilation_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as total FROM soil_health")
        soil_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as total FROM plant")
        plant_count = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as total FROM leaf_count")
        leaf_count = cursor.fetchone()
        
        # Get latest readings
        cursor.execute("""
            SELECT temperature, humidity, timestamp 
            FROM ventilation 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        latest_ventilation = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'Connected successfully ✅',
            'database': 'greenhouse',
            'host': db_config['host'],
            'record_counts': {
                'ventilation': ventilation_count['total'],
                'soil_health': soil_count['total'], 
                'plant': plant_count['total'],
                'leaf_count': leaf_count['total']
            },
            'latest_reading': {
                'temperature': float(latest_ventilation['temperature']) if latest_ventilation else None,
                'humidity': float(latest_ventilation['humidity']) if latest_ventilation else None,
                'timestamp': latest_ventilation['timestamp'].isoformat() if latest_ventilation else None
            }
        })
        
    except Error as e:
        return jsonify({
            'status': 'Connection failed ❌',
            'error': str(e),
            'host': db_config['host']
        }), 500

# Helper functions
def get_soil_status(moisture_percent):
    """Get soil status based on moisture percentage"""
    if moisture_percent < 25:
        return 'DRY'
    elif moisture_percent < 45:
        return 'LOW'
    elif moisture_percent < 70:
        return 'OPTIMAL'
    elif moisture_percent < 85:
        return 'HIGH'
    else:
        return 'SATURATED'

def get_growth_stage(height_cm):
    """Get plant growth stage based on height"""
    if height_cm <= 0:
        return 'No Reading'
    elif height_cm <= 5:
        return 'Seedling'
    elif height_cm <= 15:
        return 'Vegetative'
    elif height_cm <= 25:
        return 'Mature'
    else:
        return 'Overgrown'
















# Run the app
if __name__ == '__main__':
    app.run(debug=True)  