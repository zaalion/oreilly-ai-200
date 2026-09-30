import json
import os

from azure.servicebus import ServiceBusClient, ServiceBusSubQueue


# Connect to the Service Bus namespace using the connection string from PowerShell.
with ServiceBusClient.from_connection_string(
    os.environ["SERVICEBUS_CONNECTION_STRING"]
) as client:
    # Open a receiver for the queue's dead-letter subqueue, not the active queue.
    with client.get_queue_receiver(
        queue_name=os.environ["SERVICEBUS_QUEUE_NAME"],
        sub_queue=ServiceBusSubQueue.DEAD_LETTER,
        max_wait_time=10,
    ) as receiver:
        # Read up to ten dead-letter messages and wait up to ten seconds for data.
        messages = receiver.receive_messages(
            max_message_count=10,
            max_wait_time=10,
        )

        if not messages:
            print("The dead-letter queue contains no messages.")

        # Display the metadata and body of each message that was found.
        for message in messages:
            body = str(message)

            print("\nDead-letter message")
            print("-------------------")
            print(f"Message ID: {message.message_id}")
            print(f"Reason: {message.dead_letter_reason}")
            print(f"Error description: {message.dead_letter_error_description}")

            try:
                # Parse the JSON body written by queue_sender.py.
                payload = json.loads(body)
                print(f"Question number: {payload['question_number']}")
                print(f"Question: {payload['question']}")
            except (json.JSONDecodeError, KeyError, TypeError):
                # Display the raw body if it is not in the expected JSON format.
                print(f"Body: {body}")

            # Return the message to the dead-letter queue after displaying it.
            receiver.abandon_message(message)
