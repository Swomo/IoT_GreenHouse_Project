import json
import urllib3

http = urllib3.PoolManager()

def lambda_handler(event, context):
    try:
        url = "http://34.199.73.137:80/leaf-ingest"  # Update with your EC2 IP or domain
        headers = {'Content-Type': 'application/json'}

        # Example event expected:
        # {
        #   "leaf_count": 18,
        #   "sector_id": 1
        # }

        leaf_count = event.get("leaf_count")
        sector_id = 1

        if leaf_count is None or sector_id is None:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing leaf_count or sector_id"})
            }

        payload = {
            "leaf_count": leaf_count,
            "sector_id": sector_id
        }

        response = http.request(
            "POST",
            url,
            body=json.dumps(payload).encode("utf-8"),
            headers=headers
        )

        return {
            "statusCode": response.status,
            "body": response.data.decode("utf-8")
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
        }
