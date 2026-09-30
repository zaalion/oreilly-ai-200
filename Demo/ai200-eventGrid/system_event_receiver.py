import json
import os
import time

from azure.eventgrid import EventGridEvent
from azure.storage.queue import QueueClient, TextBase64DecodePolicy


# Connect to the Storage queue used as the Event Grid event handler.
queue_client = QueueClient.from_connection_string(
    conn_str=os.environ["STORAGE_CONNECTION_STRING"],
    queue_name=os.environ["EVENT_QUEUE_NAME"],
    # Event Grid Base64-encodes events delivered to Azure Storage queues.
    message_decode_policy=TextBase64DecodePolicy(),
)

# Event delivery is asynchronous, so poll the queue for up to 60 seconds.
deadline = time.monotonic() + 60
received_event = False

while time.monotonic() < deadline and not received_event:
    # Make one visible message temporarily invisible while it is processed.
    messages = queue_client.receive_messages(
        messages_per_page=1,
        visibility_timeout=30,
    )

    for message in messages:
        # Convert the Storage Queue message into a typed Event Grid event object.
        event = EventGridEvent.from_json(message)

        print("\nSystem event received")
        print("---------------------")
        print(f"Event ID: {event.id}")
        print(f"Event type: {event.event_type}")
        print(f"Subject: {event.subject}")
        print(f"Event time: {event.event_time}")
        print("Data:")
        print(json.dumps(event.data, indent=2))

        # Delete the queue message only after it has been displayed successfully.
        queue_client.delete_message(message)
        received_event = True
        break

    if not received_event:
        print("Waiting for the BlobCreated event...")
        time.sleep(5)

if not received_event:
    raise TimeoutError("No matching BlobCreated event arrived within 60 seconds.")

# Release the queue client's network resources.
queue_client.close()
