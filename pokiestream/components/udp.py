# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

from pokiestream.components.queue import queues
from datetime import datetime, timezone
import time
import heapq
import threading
import asyncio
import uuid6

UDP_IDLE_TIMEOUT = 120
UDP_DNS_TIMEOUT = 30

def put_data_to_queue(data, name='log_queue'):
    if data:
        queues[name].sync_q.put(data)

# UDP session manager to track UDP sessions and handle expiration based on idle timeout
class UDPSessionManager:
    def __init__(self):
        self.sessions = {}
        self.expiration_heap = []
        self.lock = threading.Lock()  
        self.cleanup_lock = asyncio.Lock() 

    # Track a new UDP session or update an existing one
    def track_session_sync(self, src_ip, src_port, dst_ip, dst_port):
        now = time.time()
        key = (src_ip, src_port, dst_ip, dst_port)
        expiration_time = now + (UDP_DNS_TIMEOUT if dst_port == 53 else UDP_IDLE_TIMEOUT)

        with self.lock:
            if key not in self.sessions:
                connection_uuid = str(uuid6.uuid7())
                self.sessions[key] = {
                    "first_seen": now,
                    "last_seen": now,
                    "packets": 1,
                    "session_id": connection_uuid,
                    "expiration": expiration_time
                }
                heapq.heappush(self.expiration_heap, (expiration_time, key))
                return "NEW", connection_uuid
            else:
                sess = self.sessions[key]
                sess["last_seen"] = now
                sess["packets"] += 1
                sess["expiration"] = expiration_time
                return None, sess["session_id"]

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
            data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": 17, "protocol_name": "UDP", "state": "EXPIRED", "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f"), "session_id": sess["session_id"], "payload": None }
            put_data_to_queue(data, name='log_queue')


udp_session_manager = UDPSessionManager()

# Start the cleanup task
async def start_cleanup_task():
    while True:
        await udp_session_manager.cleanup_sessions()
        await asyncio.sleep(1)