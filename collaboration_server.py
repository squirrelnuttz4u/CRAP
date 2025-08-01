# collaboration_server.py
# © 2025 Colt McVey
# A simple WebSocket server for real-time notebook collaboration.

import asyncio
import websockets
import json
import logging
from typing import Set, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# In-memory storage for connected clients per document/notebook room.
ROOMS: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}

async def register(websocket: websockets.WebSocketServerProtocol, notebook_id: str):
    """Adds a user to a specific notebook's room."""
    if notebook_id not in ROOMS:
        ROOMS[notebook_id] = set()
    ROOMS[notebook_id].add(websocket)
    logging.info(f"Client {websocket.remote_address} joined room '{notebook_id}'. Total clients in room: {len(ROOMS[notebook_id])}")

async def unregister(websocket: websockets.WebSocketServerProtocol, notebook_id: str):
    """Removes a user from a notebook's room."""
    if notebook_id in ROOMS and websocket in ROOMS[notebook_id]:
        ROOMS[notebook_id].remove(websocket)
        logging.info(f"Client {websocket.remote_address} left room '{notebook_id}'.")
        # Clean up empty rooms
        if not ROOMS[notebook_id]:
            del ROOMS[notebook_id]

async def broadcast_change(message: str, notebook_id: str, sender: websockets.WebSocketServerProtocol):
    """Broadcasts a message to all clients in a room except the sender."""
    if notebook_id in ROOMS:
        # Create a list of tasks to send messages concurrently
        tasks = [
            asyncio.create_task(client.send(message))
            for client in ROOMS[notebook_id]
            if client != sender
        ]
        if tasks:
            await asyncio.wait(tasks)

async def collaboration_handler(websocket: websockets.WebSocketServerProtocol, path: str):
    """
    Handles incoming WebSocket connections and messages.
    The 'path' is now passed as a second argument by the websockets library.
    """
    notebook_id = path.strip('/')
    
    if not notebook_id:
        logging.error("Connection attempt with no notebook_id.")
        return

    try:
        await register(websocket, notebook_id)
        
        # Listen for messages from this client
        async for message in websocket:
            try:
                data = json.loads(message)
                await broadcast_change(message, notebook_id, websocket)
            except json.JSONDecodeError:
                logging.warning(f"Received invalid JSON from {websocket.remote_address}: {message}")

    except websockets.exceptions.ConnectionClosedError:
        logging.info(f"Connection closed by client {websocket.remote_address}.")
    finally:
        # Ensure the client is unregistered when the connection is closed for any reason
        if notebook_id:
            await unregister(websocket, notebook_id)

async def main():
    """Starts the WebSocket server."""
    host = "localhost"
    port = 8765
    async with websockets.serve(collaboration_handler, host, port, max_size=10 * 1024 * 1024):
        logging.info(f"Collaboration server started at ws://{host}:{port}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutting down.")
