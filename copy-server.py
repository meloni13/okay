from flask import Flask, request, Response
import boto3
import threading
import csv


app = Flask(__name__)
lock = threading.Lock()

S3_BUCKET = "1233521057-in-bucket"  # Replace with your S3 bucket name
AWS_REGION = "us-east-1"  # Replace with your AWS region
ASU_ID = "1233521057"  # Replace with your ASU ID
SIMPLEDB_DOMAIN = f"{ASU_ID}-simpleDB"  # SimpleDB domain

sdb_client = boto3.client("sdb", region_name=AWS_REGION)

# Initialize Boto3 S3 Client
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
)


### --------------------- SIMPLEDB SETUP --------------------- ###
def create_simpledb_domain():
    """Creates a SimpleDB domain if it does not exist."""
    try:
        sdb_client.create_domain(DomainName=SIMPLEDB_DOMAIN)
        print(f"SimpleDB domain '{SIMPLEDB_DOMAIN}' is ready.")
    except Exception as e:
        print(f"Error creating SimpleDB domain: {e}")

def populate_simpledb(csv_file):
    """Loads classification results from CSV into SimpleDB."""
    try:
        with open(csv_file, "r") as file:
            reader = csv.reader(file)
            first_row = next(reader)  # Read the first row

            # If the first row contains column names, ignore it
            if first_row[0].lower() == "image" and first_row[1].lower() == "results":
                print("Skipping CSV header row")
            else:
                file.seek(0)  # Reset file pointer if first row is valid data
                reader = csv.reader(file)

            for row in reader:
                if len(row) != 2:
                    print(f"Skipping invalid row: {row}")
                    continue

                filename, prediction = row
                filename = filename.strip().lower()  # Normalize filename
                prediction = prediction.strip()

                sdb_client.put_attributes(
                    DomainName=SIMPLEDB_DOMAIN,
                    ItemName=filename,  # **Use the correct filename instead of "image"**
                    Attributes=[{"Name": "prediction", "Value": prediction, "Replace": True}]
                )
        print("✅ SimpleDB population complete.")
    except Exception as e:
        print(f"❌ Error populating SimpleDB: {e}")


def get_classification_result(filename):
    """Fetches recognition result from SimpleDB based on filename."""
    try:
        filename = filename.strip().lower()  # Ensure normalization
        print(f"🔍 Querying SimpleDB for filename: {filename}")

        response = sdb_client.get_attributes(
            DomainName=SIMPLEDB_DOMAIN,
            ItemName=filename,
            AttributeNames=["prediction"]
        )

        print(f"📡 SimpleDB Response: {response}")

        if "Attributes" in response and response["Attributes"]:
            prediction = response["Attributes"][0]["Value"]
            print(f"✅ Found Prediction: {prediction}")
            return prediction

    except Exception as e:
        print(f"❌ Error querying SimpleDB: {e}")

    print("❌ Filename not found in SimpleDB.")
    return "Unknown"


### --------------------- IMAGE UPLOAD TO S3 + SIMPLEDB LOOKUP --------------------- ###
@app.route("/", methods=["POST"])
def upload_image():
    """Handles image uploads, stores in S3, and fetches classification results from SimpleDB."""
    if "inputFile" not in request.files:
        return Response("No file part in the request", status=400)

    file = request.files["inputFile"]
    filename = file.filename
    filename = filename.replace(".jpg", "")
    if filename == "":
        return Response("No selected file", status=400)

    try:
        # Lock to handle concurrency safely
        with lock:
            # Upload file to S3
            s3_client.upload_fileobj(file, S3_BUCKET, filename)

            # Fetch classification result from SimpleDB
            classification = get_classification_result(filename)

        # Return plain text response: "<filename>:<prediction>"
        return Response(f"{filename}:{classification}", mimetype="text/plain", status=200)

    except Exception as e:
        return Response(str(e), status=500)

### --------------------- MAIN SERVER --------------------- ###
if __name__ == "__main__":

    app.run(host="0.0.0.0", port=8000)
