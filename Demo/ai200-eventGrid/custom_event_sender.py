import os

from azure.core.credentials import AzureKeyCredential
from azure.eventgrid import EventGridEvent, EventGridPublisherClient


# Create a publisher that authenticates with the custom topic's access key.
publisher = EventGridPublisherClient(
    endpoint=os.environ["EVENTGRID_TOPIC_ENDPOINT"],
    credential=AzureKeyCredential(os.environ["EVENTGRID_TOPIC_KEY"]),
)

# These events exercise event-type, subject, and advanced data filtering.
events = [
    EventGridEvent(
        subject="/products/laptop-100",
        event_type="Contoso.Inventory.StockChanged",
        data={
            "productName": "Laptop 100",
            "warehouse": "east",
            "remainingUnits": 3,
            "simulateRetry": False,
        },
        data_version="1.0",
    ),
    EventGridEvent(
        subject="/products/monitor-200",
        event_type="Contoso.Inventory.StockChanged",
        data={
            "productName": "Monitor 200",
            "warehouse": "east",
            "remainingUnits": 25,
            "simulateRetry": False,
        },
        data_version="1.0",
    ),
    EventGridEvent(
        subject="/products/mouse-300",
        event_type="Contoso.Inventory.PriceChanged",
        data={
            "productName": "Mouse 300",
            "warehouse": "east",
            "remainingUnits": 2,
            "simulateRetry": False,
        },
        data_version="1.0",
    ),
    EventGridEvent(
        subject="/products/keyboard-400",
        event_type="Contoso.Inventory.StockChanged",
        data={
            "productName": "Keyboard 400",
            "warehouse": "east",
            "remainingUnits": 2,
            "simulateRetry": True,
        },
        data_version="1.0",
    ),
    EventGridEvent(
        subject="/suppliers/adapter-500",
        event_type="Contoso.Inventory.StockChanged",
        data={
            "productName": "Adapter 500",
            "warehouse": "east",
            "remainingUnits": 1,
            "simulateRetry": False,
        },
        data_version="1.0",
    ),
]

# Publish events separately so each matching event has an independent delivery result.
for event in events:
    publisher.send(event)
    print(
        f"Published {event.event_type}: {event.subject} "
        f"(remaining units: {event.data['remainingUnits']})"
    )

# Release the publisher's network resources.
publisher.close()
