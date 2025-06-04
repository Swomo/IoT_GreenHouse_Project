import json
import urllib3

http = urllib3.PoolManager()

def lambda_handler(event, context):
    try:
        url = 'http://34.199.73.137/soil-ingest'  # Replace with your real endpoint
        headers = {'Content-Type': 'application/json'}

        sensors = event.get('soil_sensors', {})
        results = []

        for sensor_key in ['sensor_a', 'sensor_b', 'sensor_c']:
            sensor_data = sensors.get(sensor_key)
            if sensor_data:
                payload = {
                    "sector_id": sensor_data.get("sector"),
                    "raw_value": sensor_data.get("raw_value"),
                    "soil_moisture": sensor_data.get("moisture_percent"),
                    "timestamp": event.get("timestamp")
                }

                # Send HTTP POST to Flask app
                response = http.request(
                    'POST',
                    url,
                    body=json.dumps(payload).encode('utf-8'),
                    headers=headers
                )

                results.append({
                    "sensor": sensor_key,
                    "statusCode": response.status,
                    "response": response.data.decode('utf-8')
                })

        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
