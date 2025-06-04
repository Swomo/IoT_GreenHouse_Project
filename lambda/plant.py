import json
import urllib3

http = urllib3.PoolManager()

def lambda_handler(event, context):
    url = 'http://34.199.73.137/plant-ingest'  # Replace with your actual EC2 IP
    headers = {'Content-Type': 'application/json'}

    try:
        # Extract plant height data
        plant_data = event.get('plant_heights', {})

        responses = []

        for plant_id, plant in plant_data.items():
            sector_id = plant.get('sector')
            height_cm = plant.get('height_cm')

            # Optional: Skip if no reading
            if height_cm is None or height_cm == -1:
                continue

            payload = {
                'sector_id': sector_id,
                'height_cm': height_cm
            }

            # Send POST request to Flask endpoint
            response = http.request(
                'POST',
                url,
                body=json.dumps(payload).encode('utf-8'),
                headers=headers
            )

            responses.append({
                'sector_id': sector_id,
                'status': response.status,
                'response': response.data.decode('utf-8')
            })

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data forwarded to /plant-ingest',
                'results': responses
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
