# collaboration_client.py
# © 2025 Colt McVey
# A client for handling real-time collaboration via WebSockets.

import asyncio
import websockets
import json
import uuid
import logging
from PySide6.QtCore import QObject, Signal
from settings_manager import settings_manager

class CollaborationClient(QObject):
    """
    Manages the WebSocket connection for a single notebook.
    This class is now designed to be driven by an external asyncio event loop.
    """
    message_received = Signal(dict)
    user_activity_received = Signal(dict)
    connection_status_changed = Signal(str)

    def __init__(self, notebook_id: str):
        super().__init__()
        self.notebook_id = notebook_id
        base_uri = settings_manager.get("collab_server_uri")
        self.uri = f"{base_uri}/{self.notebook_id}"
        self.client_id = str(uuid.uuid4())
        self.websocket = None
        self.is_running = False
        self._send_queue = asyncio.Queue()
        self._main_task = None

    def start(self):
        """Starts the main asyncio task for this client."""
        if not self.is_running:
            self.is_running = True
            self._main_task = asyncio.create_task(self._run())

    async def _run(self):
        """The main loop that handles connection and message sending/receiving."""
        self.connection_status_changed.emit("Connecting...")
        while self.is_running:
            try:
                # Increase the maximum message size to handle large contexts
                async with websockets.connect(self.uri, max_size=10 * 1024 * 1024) as ws:
                    self.websocket = ws
                    self.connection_status_changed.emit("Connected")
                    
                    consumer_task = asyncio.create_task(self._receive_messages())
                    producer_task = asyncio.create_task(self._send_messages())
                    
                    done, pending = await asyncio.wait(
                        [consumer_task, producer_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    
                    for task in pending:
                        task.cancel()

            except (websockets.exceptions.ConnectionClosed, OSError) as e:
                self.connection_status_changed.emit("Disconnected")
                logging.warning(f"Connection for {self.notebook_id} closed: {e}. Reconnecting...")
            except Exception as e:
                self.connection_status_changed.emit(f"Error")
                logging.error(f"Collaboration client error for {self.notebook_id}: {e}")
            finally:
                self.websocket = None
                if self.is_running:
                    await asyncio.sleep(5)

    async def _receive_messages(self):
        """Task to listen for incoming messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    if data.get("client_id") == self.client_id:
                        continue
                    
                    if data.get("type") == "cursor_update":
                        self.user_activity_received.emit(data)
                    else:
                        self.message_received.emit(data)
                except json.JSONDecodeError:
                    logging.warning(f"Received non-JSON message: {message}")
        except websockets.exceptions.ConnectionClosed:
            logging.info(f"Receive loop for {self.notebook_id} terminated gracefully.")
        except Exception as e:
            logging.error(f"Error in receive loop for {self.notebook_id}: {e}")


    async def _send_messages(self):
        """Task to send messages from the queue."""
        try:
            while True:
                message = await self._send_queue.get()
                if self.websocket:
                    await self.websocket.send(message)
                self._send_queue.task_done()
        except asyncio.CancelledError:
            logging.info(f"Send loop for {self.notebook_id} cancelled.")


    def _queue_message(self, data: dict):
        """Internal method to queue data for sending."""
        if self.is_running:
            data['client_id'] = self.client_id
            self._send_queue.put_nowait(json.dumps(data))

    def send_message(self, data: dict):
        self._queue_message(data)

    def send_cursor_update(self, cell_id: str, cursor_pos: int, selection_end: int):
        data = {"type": "cursor_update", "cell_id": cell_id, "cursor_pos": cursor_pos, "selection_end": selection_end}
        self._queue_message(data)

    def stop(self):
        """Stops the client and cleans up tasks."""
        self.is_running = False
        if self._main_task:
            self._main_task.cancel()
