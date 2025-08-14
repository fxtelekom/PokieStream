import socket
import asyncio
import time
from collections import namedtuple

COLORS = {
    "NEW": "\033[94m",
    "ESTABLISHED": "\033[92m",
    "CLOSE": "\033[91m",
    "ABORT": "\033[1;91m",
    "UNKNOWN": "\033[93m",
    "RESET": "\033[0m",
}

rdns_cache = {}
CACHE_TTL = 120 

async def reverse_dns(ip):
    now = time.time()
    if ip in rdns_cache:
        hostname, ts = rdns_cache[ip]
        if now - ts < CACHE_TTL:
            return hostname
        rdns_cache.pop(ip, None)
    
    try:
        hostname = await asyncio.to_thread(socket.gethostbyaddr, ip)
        hostname = hostname[0]
    except Exception:
        hostname = None
    
    rdns_cache[ip] = (hostname, now)
    return hostname

Packet = namedtuple("Packet", [
    "src_ip", "dst_ip", "src_port", "dst_port",
    "protocol_num", "protocol_name", "state",
    "timestamp", "session_id", "payload"
])

async def receiver(data):
    packet = Packet(**data)
    src_ip, dst_ip, src_port, dst_port, proto_num, proto_name, state, timestamp, session_id, payload = packet

    rdns = await reverse_dns(dst_ip)
    dst_display = f"{dst_ip} ({rdns})" if rdns else dst_ip

    color = COLORS.get(state, COLORS["UNKNOWN"])

    if proto_name.upper() == "ICMP":
        line = (
            f"{color}[{timestamp}] {src_ip} -> {dst_display} "
            f"Protocol: {proto_name} ({proto_num}){COLORS['RESET']}"
        )
    else:
        line = (
            f"{color}[{timestamp}] {src_ip}:{src_port} -> {dst_display}:{dst_port} "
            f"Protocol: {proto_name} ({proto_num}), State: {state}, Session: {session_id}{COLORS['RESET']}"
        )

    if payload:
        if payload.get("host"):
            line += f", Host: {payload['host']}"
        if payload.get("dns"):
            line += f", DNS: {payload['dns']}"

    print(line)