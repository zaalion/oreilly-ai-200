import json
import os

from azure.servicebus import ServiceBusClient, ServiceBusMessage


# Define five valid general-knowledge questions for the topic demonstration.
questions = [
    "What is the capital city of Australia?",
    "Which grain is traditionally used to make risotto?",
    "What is the largest mammal in the world?",
    "Which country contains the ancient city of Machu Picchu?",
    "What is the freezing point of water in degrees Celsius?",
]

# Convert each question to JSON and wrap it in a Service Bus message.
messages = []
for question_number, question in enumerate(questions, start=1):
    # Keep the question number in the body so subscribers can name their files.
    body = json.dumps(
        {
            "question_number": question_number,
            "question": question,
        }
    )

    # Set an ID, subject, and content type to describe the message.
    messages.append(
        ServiceBusMessage(
            body,
            message_id=f"topic-question-{question_number}",
            subject="general-question",
            content_type="application/json",
        )
    )

# Connect to the namespace and create a sender for the configured topic.
with ServiceBusClient.from_connection_string(
    os.environ["SERVICEBUS_CONNECTION_STRING"]
) as client:
    with client.get_topic_sender(
        topic_name=os.environ["SERVICEBUS_TOPIC_NAME"]
    ) as sender:
        # Publish each message to every subscription associated with the topic.
        sender.send_messages(messages)

print(f"Published {len(messages)} messages to the topic.")
