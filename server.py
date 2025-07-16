#!/usr/bin/env python

import asyncio
import websockets
import json
import os # Import the os module

# A set to keep track of all connected clients (websockets).
CONNECTED_CLIENTS = set()

async def process_request(path, request_headers):
    """
    This function handles Render's health check requests.
    If it's a standard HTTP request (not a WebSocket upgrade), it responds with 200 OK.
    """
    # Check if this is a WebSocket upgrade request
    upgrade_header = request_headers.headers.get("Upgrade", "").lower()
    connection_header = request_headers.headers.get("Connection", "").lower()
    
    # If it's not a WebSocket upgrade request, treat it as a health check
    if upgrade_header != "websocket" or "upgrade" not in connection_header:
        # Return 200 OK for health checks (both GET and HEAD requests)
        return (websockets.http11.Response(200, "OK", b"Health Check OK"), None)
    
    # If it is a WebSocket upgrade request, let the default handler process it
    return None

async def handler(websocket, path):
    """
    This function is called for each new client that connects.
    It registers the client, handles incoming messages, and unregisters
    on disconnection.
    """
    # Register the new client by adding it to our set.
    CONNECTED_CLIENTS.add(websocket)
    print(f"Client connected from {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")
    
    try:
        # This loop runs forever for each client, waiting for messages.
        # When the client disconnects, the loop will exit.
        async for message in websocket:
            print(f"Received message from a client: {message}")
            
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
                print(f"Broadcasted message to {len(broadcast_tasks)} other clients.")

    except websockets.exceptions.ConnectionClosedError:
        print(f"A client connection was closed unexpectedly.")
    except websockets.exceptions.ConnectionClosedOK:
        print(f"A client connection was closed normally.")
    finally:
        # Unregister the client upon disconnection.
        # Use a check to prevent errors if the client is already gone.
        if websocket in CONNECTED_CLIENTS:
            CONNECTED_CLIENTS.remove(websocket)
            print(f"Client disconnected. Total clients: {len(CONNECTED_CLIENTS)}")

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

    # Start the WebSocket server with the new health check handler.
    # The `process_request` argument is called for every incoming connection.
    async with websockets.serve(handler, host, port, process_request=process_request):
        print(f"WebSocket server started at ws://{host}:{port}")
        # The server will run forever until the program is stopped.
        await asyncio.Future()

if __name__ == "__main__":
    # Before running, make sure you have the library installed:
    # pip install websockets
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer is shutting down.")