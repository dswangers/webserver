#!/usr/bin/env python

import asyncio
import websockets
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# A set to keep track of all connected clients (websockets).
CONNECTED_CLIENTS = set()

async def handler(websocket, path):
    """
    This function is called for each new client that connects.
    It registers the client, handles incoming messages, and unregisters
    on disconnection.
    """
    # Register the new client by adding it to our set.
    CONNECTED_CLIENTS.add(websocket)
    logger.info(f"Client connected from {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")
    
    try:
        # This loop runs forever for each client, waiting for messages.
        # When the client disconnects, the loop will exit.
        async for message in websocket:
            logger.info(f"Received message from a client: {message}")
            
            # Here, we will broadcast the received message to all other clients.
            # We create a list of tasks to send the message concurrently.
            broadcast_tasks = []
            for client in CONNECTED_CLIENTS:
                # We don't want to send the message back to the sender.
                if client != websocket:
                    # Create a coroutine to send the message and add it to our list.
                    broadcast_tasks.append(client.send(message))
            
            # Run all the send tasks concurrently.
            if broadcast_tasks:
                await asyncio.wait(broadcast_tasks)
                logger.info(f"Broadcasted message to {len(broadcast_tasks)} other clients.")

    except websockets.exceptions.ConnectionClosedError:
        logger.info(f"A client connection was closed unexpectedly.")
    except websockets.exceptions.ConnectionClosedOK:
        logger.info(f"A client connection was closed normally.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Unregister the client upon disconnection.
        # Use a check to prevent errors if the client is already gone.
        if websocket in CONNECTED_CLIENTS:
            CONNECTED_CLIENTS.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(CONNECTED_CLIENTS)}")

async def process_request(path, request_headers):
    """
    Handle HTTP requests that aren't WebSocket upgrades.
    This will handle browsers visiting the URL directly.
    """
    # Check if this is a WebSocket upgrade request
    if request_headers.get("upgrade", "").lower() == "websocket":
        return None  # Let websockets handle it
    
    # Return a simple HTML page for regular HTTP requests
    html_response = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Server</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 600px; margin: 0 auto; }
            .status { color: green; font-weight: bold; }
            code { background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WebSocket Server</h1>
            <p class="status">✅ Server is running!</p>
            <p>This is a WebSocket server. To connect, use:</p>
            <code>ws://your-domain.com/</code>
            <p>Or for local testing:</p>
            <code>ws://localhost:10000/</code>
        </div>
    </body>
    </html>
    """
    
    return websockets.http11.Response(
        200, "OK", 
        html_response.encode('utf-8'),
        [("Content-Type", "text/html")]
    )

async def main():
    """
    The main function to start the WebSocket server.
    """
    # The host '0.0.0.0' tells the server to listen on all available
    # network interfaces, not just localhost. This is crucial for
    # allowing other computers on your network or the internet to connect.
    host = "0.0.0.0"
    
    # Render provides the port to use in the 'PORT' environment variable.
    # We read it from there, defaulting to 10000 for local testing.
    port = int(os.environ.get("PORT", 10000))

    # Start the WebSocket server with the request processor
    start_server = websockets.serve(
        handler,
        host,
        port,
        process_request=process_request,
        # Make the server more tolerant of different request types
        ping_interval=20,
        ping_timeout=20,
        close_timeout=10,
        max_size=2**20,
        max_queue=2**5,
        read_limit=2**16,
        write_limit=2**16,
    )
    
    async with start_server:
        logger.info(f"WebSocket server started at ws://{host}:{port}")
        logger.info(f"You can visit https://webserver-kepb.onrender.com in your browser")
        # The server will run forever until the program is stopped.
        await asyncio.Future()

if __name__ == "__main__":
    # Before running, make sure you have the library installed:
    # pip install websockets
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nServer is shutting down.")