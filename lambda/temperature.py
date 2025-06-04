import json
import urllib3

http = urllib3.PoolManager()

def lambda_handler(event, context):
    try:
        url = 'http://34.199.73.137/temperature-ingest'  # Replace with your public IP or domain
        headers = {'Content-Type': 'application/json'}

        # Extract values if payload is inside `event['temperature']`, etc.
        # If the IoT Rule does SELECT *, then the full payload is under event

        payload = {
            'temperature': event.get('temperature'),
            'humidity': event.get('humidity'),
            'sector_id': event.get('sector_id', 1)  # default sector if not passed
        }

        # Optional: Validate values before sending
        if payload['temperature'] is None or payload['humidity'] is None:
            raise ValueError("Missing temperature or humidity in event payload")

        response = http.request(
            'POST',
            url,
            body=json.dumps(payload).encode('utf-8'),
            headers=headers
        )

        return {
            'statusCode': response.status,
            'body': response.data.decode('utf-8')
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
