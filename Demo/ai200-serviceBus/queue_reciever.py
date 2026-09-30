import json
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.servicebus import ServiceBusClient
from openai import OpenAI


# Stop after the ten messages produced by queue_sender.py have been settled.
EXPECTED_MESSAGES = 10

# Store generated answers beside this script, regardless of the current directory.
OUTPUT_DIRECTORY = Path(__file__).resolve().parent / "queue_answers"

# These phrases identify the intentionally unsafe classroom message.
INJECTION_PHRASES = (
    "ignore all previous instructions",
    "reveal your system prompt",
    "reveal your instructions",
)


# Use a distinct exception so the receiver can dead-letter only rejected prompts.
class PromptInjectionDetected(Exception):
    pass


def validate_question(question: str) -> None:
    # Case-insensitive matching makes the demonstration independent of capitalization.
    normalized_question = question.casefold()
    if any(phrase in normalized_question for phrase in INJECTION_PHRASES):
        raise PromptInjectionDetected("The question contains prompt-injection text.")


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

# Create the answer directory if it does not already exist.
OUTPUT_DIRECTORY.mkdir(exist_ok=True)
processed_count = 0

# Connect to Service Bus using the namespace connection string.
with ServiceBusClient.from_connection_string(
    os.environ["SERVICEBUS_CONNECTION_STRING"]
) as client:
    # Open a peek-lock receiver for the active queue.
    with client.get_queue_receiver(
        queue_name=os.environ["SERVICEBUS_QUEUE_NAME"],
        max_wait_time=10,
    ) as receiver:
        # Continue until nine messages are completed and one is dead-lettered.
        while processed_count < EXPECTED_MESSAGES:
            # Receive one message at a time so it can be validated and settled.
            messages = receiver.receive_messages(
                max_message_count=1,
                max_wait_time=10,
            )

            if not messages:
                # Keep waiting because the demonstration expects exactly ten messages.
                print(
                    f"Waiting for messages "
                    f"({processed_count}/{EXPECTED_MESSAGES} processed)..."
                )
                continue

            message = messages[0]
            try:
                # Parse the JSON body and retrieve its question number and text.
                payload = json.loads(str(message))
                question_number = int(payload["question_number"])
                question = str(payload["question"])

                validate_question(question)

                # Send only validated questions to the deployed language model.
                response = openai_client.responses.create(
                    model=chat_deployment,
                    instructions=(
                        "Answer the general-knowledge question accurately and "
                        "concisely."
                    ),
                    input=question,
                )

                # Write the original question and generated answer to a numbered file.
                output_file = OUTPUT_DIRECTORY / f"{question_number}.txt"
                output_file.write_text(
                    f"Question:\n{question}\n\nAnswer:\n{response.output_text}\n",
                    encoding="utf-8",
                )

                # Complete removes the successfully processed message from the queue.
                receiver.complete_message(message)
                processed_count += 1
                print(f"Completed question {question_number}: {output_file.name}")

            except PromptInjectionDetected as error:
                # Move the rejected message to the dead-letter subqueue for inspection.
                receiver.dead_letter_message(
                    message,
                    reason="PromptInjectionDetected",
                    error_description=str(error),
                )
                processed_count += 1
                print(f"Dead-lettered rejected message: {error}")

            except Exception as error:
                # Abandon returns other failed messages to the active queue for retry.
                receiver.abandon_message(message)
                print(f"Processing failed; message returned to queue: {error}")

print(f"Settled all {EXPECTED_MESSAGES} queue messages.")
