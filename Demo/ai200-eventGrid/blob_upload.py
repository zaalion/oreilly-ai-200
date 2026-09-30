import os
from datetime import UTC, datetime

from azure.storage.blob import BlobServiceClient


# Connect to the storage account created for the system-event demonstration.
blob_service = BlobServiceClient.from_connection_string(
    os.environ["STORAGE_CONNECTION_STRING"]
)
container_name = os.environ["BLOB_CONTAINER_NAME"]

# Use a timestamp so each run creates new blobs and new BlobCreated events.
timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

# Upload a text file that matches the event subscription's .txt subject filter.
text_blob_name = f"notes/event-grid-{timestamp}.txt"
text_blob = blob_service.get_blob_client(container_name, text_blob_name)
text_blob.upload_blob(
    b"This text file should produce a delivered BlobCreated event.\n",
    overwrite=False,
)
print(f"Uploaded matching blob: {text_blob_name}")

# Upload a JSON file that creates a system event but is removed by the .txt filter.
json_blob_name = f"notes/event-grid-{timestamp}.json"
json_blob = blob_service.get_blob_client(container_name, json_blob_name)
json_blob.upload_blob(
    b'{"message":"This BlobCreated event should be filtered out."}\n',
    overwrite=False,
)
print(f"Uploaded filtered blob: {json_blob_name}")

# Close the underlying HTTP transport used by the storage client.
blob_service.close()
