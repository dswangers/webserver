#!/usr/bin/env python

import asyncio
import json
import os
from aiohttp import web, WSMsgType
import aiohttp

# A set to keep track of all connected clients (websockets).
CONNECTED_CLIENTS = set()

async def websocket_handler(request):
    """Handle WebSocket connections using aiohttp"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    # Register the new client
    CONNECTED_CLIENTS.add(ws)
    print(f"Client connected. Total clients: {len(CONNECTED_CLIENTS)}")
    
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                message = msg.data
                print(f"Received message: {message}")
                
                # Broadcast to all other clients
                broadcast_tasks = []
                for client in CONNECTED_CLIENTS:
                    if client != ws and not client.closed:
                        broadcast_tasks.append(client.send_str(message))
                
                if broadcast_tasks:
                    await asyncio.gather(*broadcast_tasks, return_exceptions=True)
                    print(f"Broadcasted message to {len(broadcast_tasks)} other clients.")
            
            elif msg.type == WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}')
                break
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Unregister the client
        if ws in CONNECTED_CLIENTS:
            CONNECTED_CLIENTS.remove(ws)
            print(f"Client disconnected. Total clients: {len(CONNECTED_CLIENTS)}")
    
    return ws

async def health_check(request):
    """Handle health check requests"""
    return web.Response(text="Health Check OK")

async def main():
    """Start the server"""
    # Create aiohttp application
    app = web.Application()
    
    # Add routes
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/ws', websocket_handler)
    
    # Get port from environment
    port = int(os.environ.get("PORT", 10000))
    
    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"Server started at http://0.0.0.0:{port}")
    print("WebSocket endpoint: ws://0.0.0.0:{port}/ws")
    
    # Keep the server running
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer is shutting down.")