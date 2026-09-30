from threading import Lock

from flask import Flask, jsonify, request


# Flask exposes the public webhook endpoint used by the Event Grid subscription.
app = Flask(__name__)

# Store delivery-attempt counts by event ID for the retry demonstration.
delivery_attempts: dict[str, int] = {}
delivery_attempts_lock = Lock()


@app.get("/")
def health_check():
    # Return a simple response that confirms the container is running.
    return "Event Grid receiver is running.", 200


@app.post("/events")
def receive_events():
    # Event Grid sends Event Grid schema events as a JSON array.
    events = request.get_json(force=True)

    for event in events:
        event_type = event.get("eventType")

        # Complete Event Grid's synchronous webhook ownership validation handshake.
        if event_type == "Microsoft.EventGrid.SubscriptionValidationEvent":
            validation_code = event["data"]["validationCode"]
            print("Validated the Event Grid subscription.", flush=True)
            return jsonify({"validationResponse": validation_code}), 200

        event_id = event["id"]
        event_data = event["data"]

        # Count how many times Event Grid has delivered this event to the webhook.
        with delivery_attempts_lock:
            attempt = delivery_attempts.get(event_id, 0) + 1
            delivery_attempts[event_id] = attempt

        print(
            f"Delivery attempt {attempt}: "
            f"{event_data['productName']} has "
            f"{event_data['remainingUnits']} units remaining.",
            flush=True,
        )

        # Return 503 twice for the designated event so Event Grid retries it.
        if event_data.get("simulateRetry") and attempt <= 2:
            print("Returning HTTP 503 to trigger an Event Grid retry.", flush=True)
            return "Temporary processing failure", 503

        # A successful 200 response acknowledges delivery of the event.
        print(f"Accepted event {event_id}.", flush=True)

    return "Events accepted", 200


if __name__ == "__main__":
    # This entry point supports direct local execution of the Flask application.
    app.run(host="0.0.0.0", port=8000)
