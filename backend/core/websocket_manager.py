from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._rooms: dict[str, set[str]] = {}
        self._user_connections: dict[str, set[str]] = {}
        self._heartbeat_interval: int = 30
        self._heartbeat_timeout: int = 60
        self._last_heartbeat: dict[str, float] = {}
        self._on_connect_callbacks: list[Callable[[str], Any]] = []
        self._on_disconnect_callbacks: list[Callable[[str], Any]] = []

    @property
    def active_connections(self) -> int:
        return len(self._connections)

    def on_connect(self, callback: Callable[[str], Any]) -> None:
        self._on_connect_callbacks.append(callback)

    def on_disconnect(self, callback: Callable[[str], Any]) -> None:
        self._on_disconnect_callbacks.append(callback)

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        await websocket.accept()
        connection_id = uuid.uuid4().hex
        self._connections[connection_id] = websocket
        self._last_heartbeat[connection_id] = datetime.now(timezone.utc).timestamp()

        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

        for callback in self._on_connect_callbacks:
            try:
                result = callback(connection_id)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("On-connect callback failed: %s", e)

        logger.info(
            "WebSocket connected",
            connection_id=connection_id,
            user_id=user_id,
            active=self.active_connections,
        )
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        websocket = self._connections.pop(connection_id, None)
        self._last_heartbeat.pop(connection_id, None)

        for user_id, conns in self._user_connections.items():
            conns.discard(connection_id)
            if not conns:
                self._user_connections.pop(user_id, None)

        for room, members in self._rooms.items():
            members.discard(connection_id)
            if not members:
                self._rooms.pop(room, None)

        if websocket:
            try:
                await websocket.close()
            except Exception:
                pass

        for callback in self._on_disconnect_callbacks:
            try:
                result = callback(connection_id)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("On-disconnect callback failed: %s", e)

        logger.info(
            "WebSocket disconnected",
            connection_id=connection_id,
            active=self.active_connections,
        )

    async def send_personal(self, connection_id: str, message: dict[str, Any]) -> bool:
        websocket = self._connections.get(connection_id)
        if websocket is None:
            return False
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning("Failed to send personal message: %s", e)
            await self.disconnect(connection_id)
            return False

    async def broadcast(self, message: dict[str, Any], exclude: Optional[set[str]] = None) -> int:
        exclude = exclude or set()
        sent = 0
        for conn_id, websocket in list(self._connections.items()):
            if conn_id in exclude:
                continue
            try:
                await websocket.send_json(message)
                sent += 1
            except Exception as e:
                logger.warning("Broadcast failed for %s: %s", conn_id, e)
                await self.disconnect(conn_id)
        return sent

    async def join_room(self, connection_id: str, room: str) -> None:
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(connection_id)

    async def leave_room(self, connection_id: str, room: str) -> None:
        if room in self._rooms:
            self._rooms[room].discard(connection_id)
            if not self._rooms[room]:
                del self._rooms[room]

    async def send_to_room(self, room: str, message: dict[str, Any]) -> int:
        members = self._rooms.get(room, set())
        sent = 0
        for conn_id in members:
            if await self.send_personal(conn_id, message):
                sent += 1
        return sent

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> int:
        conn_ids = self._user_connections.get(user_id, set())
        sent = 0
        for conn_id in conn_ids:
            if await self.send_personal(conn_id, message):
                sent += 1
        return sent

    async def handle_heartbeat(self, connection_id: str) -> None:
        self._last_heartbeat[connection_id] = datetime.now(timezone.utc).timestamp()

    async def heartbeat_checker(self) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            now = datetime.now(timezone.utc).timestamp()
            stale = [
                cid
                for cid, last in self._last_heartbeat.items()
                if now - last > self._heartbeat_timeout
            ]
            for cid in stale:
                logger.info("Heartbeat timeout, disconnecting %s", cid)
                await self.disconnect(cid)

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
    ) -> None:
        connection_id = await self.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    message = {"type": "text", "data": data}

                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await self.handle_heartbeat(connection_id)
                    await self.send_personal(connection_id, {"type": "pong"})
                elif msg_type == "join_room":
                    await self.join_room(connection_id, message.get("room", ""))
                elif msg_type == "leave_room":
                    await self.leave_room(connection_id, message.get("room", ""))
                elif msg_type == "broadcast":
                    await self.broadcast(
                        message.get("data", {}),
                        exclude={connection_id},
                    )
                elif msg_type == "room_message":
                    await self.send_to_room(
                        message.get("room", ""),
                        message.get("data", {}),
                    )
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected normally: %s", connection_id)
        except Exception as e:
            logger.error("WebSocket error for %s: %s", connection_id, e)
        finally:
            await self.disconnect(connection_id)


connection_manager = ConnectionManager()
