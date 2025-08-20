# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

from pokiestream.components.queue import queues
import time
import heapq
import uuid6
from datetime import datetime, timezone
from threading import Lock
import asyncio

def put_data_to_queue(data, name='log_queue'):
    if data:
        queues[name].sync_q.put(data)

class TCPSessionManager:
    def __init__(self, session_timeout=60):
        self.sessions = {} 
        self.expiration_heap = []
        self.lock = Lock()
        self.cleanup_lock = asyncio.Lock()
        self.session_timeout = session_timeout

    def _create_canonical_id(self, src_ip, src_port, dst_ip, dst_port):
        return (src_ip, src_port, dst_ip, dst_port) if (src_ip, src_port) < (dst_ip, dst_port) else (dst_ip, dst_port, src_ip, src_port)

    def track_session_sync(self, src_ip, src_port, dst_ip, dst_port, flags):
        now = time.time()
        conn_key = self._create_canonical_id(src_ip, src_port, dst_ip, dst_port)
        session_id = None

        with self.lock:
            sess = self.sessions.get(conn_key)

            if flags & 0x02 and not (flags & 0x10):
                if sess is None:
                    session_id = str(uuid6.uuid7())
                    self.sessions[conn_key] = {
                        "session_id": session_id,
                        "initiator": (src_ip, src_port),
                        "state": "NEW",
                        "expiration": now + self.session_timeout
                    }
                    heapq.heappush(self.expiration_heap, (now + self.session_timeout, conn_key))
                    return "NEW", session_id

                return None, None

            if sess and sess["state"] == "NEW":
                if (src_ip, src_port) != sess["initiator"]:
                    sess["state"] = "ESTABLISHED"
                    sess["expiration"] = now + self.session_timeout
                    heapq.heappush(self.expiration_heap, (sess["expiration"], conn_key))
                    return "ESTABLISHED", sess["session_id"]

            if sess and (flags & 0x01):
                session_id = sess["session_id"]
                del self.sessions[conn_key]
                return "CLOSE", session_id

            if sess and (flags & 0x04):
                session_id = sess["session_id"]
                del self.sessions[conn_key]
                return "ABORT", session_id

            return None, None

    async def cleanup_sessions(self):
        now = time.time()
        expired_sessions = []

        async with self.cleanup_lock:
            with self.lock:
                while self.expiration_heap and self.expiration_heap[0][0] <= now:
                    expiry_time, conn_key = heapq.heappop(self.expiration_heap)
                    if conn_key in self.sessions and self.sessions[conn_key]["expiration"] == expiry_time:
                        expired_sessions.append((conn_key, self.sessions.pop(conn_key)))

        for key, sess in expired_sessions:
            src_ip, src_port, dst_ip, dst_port = key
            data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": 6, "protocol_name": "TCP", "state": "EXPIRED", "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f"), "session_id": sess["session_id"], "payload": None }
            put_data_to_queue(data, name='log_queue')

    # Cleanup expired sessions
    async def cleanup_sessions(self):
        now = time.time()
        expired_sessions = []

        async with self.cleanup_lock:
            with self.lock:
                while self.expiration_heap and self.expiration_heap[0][0] <= now:
                    expiry_time, key = heapq.heappop(self.expiration_heap)
                    if key in self.sessions and self.sessions[key]["expiration"] == expiry_time:
                        expired_sessions.append((key, self.sessions.pop(key)))

        for key, sess in expired_sessions:
            src_ip, src_port, dst_ip, dst_port = key
            data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": 6, "protocol_name": "TCP", "state": "EXPIRED", "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f"), "session_id": sess["session_id"], "payload": None}
            put_data_to_queue(data, name='log_queue')


tcp_session_manager = TCPSessionManager()

# Start cleanup task
async def start_cleanup_task():
    while True:
        await tcp_session_manager.cleanup_sessions()
        await asyncio.sleep(1)
