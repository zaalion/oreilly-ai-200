import json
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.servicebus import ServiceBusClient
from openai import OpenAI


# Subscription 02 expects one copy of each of the five published messages.
EXPECTED_MESSAGES = 5

# Keep this subscriber's answers separate from Subscription 01's answers.
OUTPUT_DIRECTORY = Path(__file__).resolve().parent / "topic_sub_answer_02"

# Use the Azure identity from az login to obtain a Microsoft Foundry access token.
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)

# Create the OpenAI client for the Microsoft Foundry endpoint.
openai_client = OpenAI(
    base_url=os.environ["OPENAI_ENDPOINT"],
    api_key=token_provider,
)
chat_deployment = os.environ["CHAT_DEPLOYMENT"]

# Create the subscriber's output directory if it does not exist.
OUTPUT_DIRECTORY.mkdir(exist_ok=True)
processed_count = 0

# Connect to the Service Bus namespace using the configured connection string.
with ServiceBusClient.from_connection_string(
    os.environ["SERVICEBUS_CONNECTION_STRING"]
) as client:
    # Open a receiver for Subscription 02 under the configured topic.
    with client.get_subscription_receiver(
        topic_name=os.environ["SERVICEBUS_TOPIC_NAME"],
        subscription_name=os.environ["SERVICEBUS_SUBSCRIPTION_02"],
        max_wait_time=10,
    ) as receiver:
        # Continue until all five subscription messages are completed.
        while processed_count < EXPECTED_MESSAGES:
            # Receive and process one subscription message at a time.
            messages = receiver.receive_messages(
                max_message_count=1,
                max_wait_time=10,
            )

            if not messages:
                # Keep waiting because the demonstration expects five messages.
                print(
                    f"Waiting for messages "
                    f"({processed_count}/{EXPECTED_MESSAGES} processed)..."
                )
                continue

            message = messages[0]
            try:
                # Parse the JSON body and retrieve the question details.
                payload = json.loads(str(message))
                question_number = int(payload["question_number"])
                question = str(payload["question"])

                # Ask gpt-5-mini to answer the received general-knowledge question.
                response = openai_client.responses.create(
                    model=chat_deployment,
                    instructions=(
                        "Answer the general-knowledge question accurately and "
                        "concisely."
                    ),
                    input=question,
                )

                # Save the question and answer in a file named by question number.
                output_file = OUTPUT_DIRECTORY / f"{question_number}.txt"
                output_file.write_text(
                    f"Question:\n{question}\n\nAnswer:\n{response.output_text}\n",
                    encoding="utf-8",
                )

                # Complete removes this subscription's copy of the message.
                receiver.complete_message(message)
                processed_count += 1
                print(f"Completed question {question_number}: {output_file.name}")

            except Exception as error:
                # Return a failed message to Subscription 02 for a later retry.
                receiver.abandon_message(message)
                print(f"Processing failed; message returned to subscription: {error}")

print(f"Processed all {EXPECTED_MESSAGES} messages from Subscription 02.")
