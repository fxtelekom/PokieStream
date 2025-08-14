# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

from scapy.all import *
from scapy.layers.inet import IP, TCP, UDP
from datetime import datetime, timezone
from pokiestream.components.match import match_subnet, match_port, match_protocol, match_host
from pokiestream.components.udp import udp_session_manager
from pokiestream.components.queue import queues
from pokiestream.components.config import config
import uuid6

connections = {}

# write data to queue synchronously as scapy is synchronous
def put_data_to_queue(data, name='log_queue'):
    if data:
        queues[name].sync_q.put(data)

# function to inspect packets with scapy
def inspect_packets(packet):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")
    data = None

    try:
        # check if the packet has a TCP or UDP layer, everything else is ignored
        if TCP in packet or UDP in packet or ICMP in packet:
            # check if the packet has an IP layer
            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst
                prot_num = packet[IP].proto                    

                # check if the source or destination IP matches any of the subnets in the config
                match_sources = match_subnet(src_ip, "source") or match_subnet(dst_ip, "destination")

                # check if the source and destination IP matches any of the subnets in the config
                if config.filter.strict:
                    match_sources = match_subnet(src_ip, "source") and match_subnet(dst_ip, "destination")

                if match_sources:                        
                    # log udp only if its set in the config file and its a UDP packet
                    if match_protocol("udp") and packet.haslayer(UDP):
                        src_port = packet[UDP].sport
                        dst_port = packet[UDP].dport
                        if match_port(dst_port):
                            # Now we check if DNS is enabled in the config
                            udp_state, session_id = udp_session_manager.track_session_sync(src_ip, src_port, dst_ip, dst_port)

                            # We dont log if the session is not new as it's tracked and will be logged when it expires
                            if udp_state is None:
                                return

                            if udp_state == "NEW":
                                if config.filter.payload.dns.enabled:
                                    if match_port(dst_port, "filter.payload.dns.ports"):
                                        # We check if its really a DNS request and if there is at least one question in it.
                                        if packet.haslayer(DNS):
                                            dns_layer = packet.getlayer(DNS)
                                            # We check if there is at least one question in the DNS request
                                            if dns_layer.qdcount > 0 and dns_layer.qd is not None:
                                                queried_domain = dns_layer.qd.qname.decode("utf-8").rstrip(".")
                                                # We check if the queried domain matches any of the domains in the config
                                                if match_host(queried_domain, "dns"):
                                                    data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": prot_num, "protocol_name": "UDP", "state": udp_state, "timestamp": timestamp, "session_id": session_id, "payload": {"dns": queried_domain}}
                                                    
                                                    put_data_to_queue(data)
                                                    return

                            data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": prot_num, "protocol_name": "UDP", "state": udp_state, "timestamp": timestamp, "session_id": session_id, "payload": None}
                            
                            put_data_to_queue(data)
                            return

                    # log tcp only if its set in the config file and it has a TCP header
                    if match_protocol("tcp") and packet.haslayer(TCP):
                        src_port = packet[TCP].sport
                        dst_port = packet[TCP].dport
                        if match_port(dst_port):
                            connection_id = f"{src_ip}:{src_port}-{dst_ip}:{dst_port}"
                            flags = packet[TCP].flags

                            # check if the packet is a SYN
                            if flags & 0x02:
                                if connection_id not in connections:
                                    connection_uuid = str(uuid6.uuid7())
                                    connections[connection_id] = {"status": "NEW", "uuid": connection_uuid}
                                    data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": prot_num, "protocol_name": "TCP", "state": "NEW", "timestamp": timestamp, "session_id": connection_uuid, "payload": None}
                                    
                                    put_data_to_queue(data)
                                    return

                            # check if the packet is an ACK (we assume that the connection is establised from the previous packet SYN flag)
                            elif flags & 0x10: 
                                conn_info = connections.get(connection_id)
                                if conn_info and conn_info["status"] == "NEW":
                                    connections[connection_id]["status"] = "ESTABLISHED"
                                    connection_uuid = conn_info["uuid"]
                                    data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": prot_num, "protocol_name": "TCP", "state": "ESTABLISHED", "timestamp": timestamp, "session_id": connection_uuid, "payload": None}
                                    
                                    put_data_to_queue(data)
                                    return

                            # check if the packet is a FIN  
                            if flags & 0x01:
                                if connection_id in connections:
                                    connection_uuid = connections[connection_id]["uuid"]
                                    data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": prot_num, "protocol_name": "TCP", "state": "CLOSE", "timestamp": timestamp, "session_id": connection_uuid, "payload": None}
                                    connections.pop(connection_id, None)
                                    
                                    put_data_to_queue(data)
                                    return

                            # check if the packet is a RST
                            if flags & 0x04:
                                if connection_id in connections:
                                    connection_uuid = connections[connection_id]["uuid"]
                                    data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": src_port, "dst_port": dst_port, "protocol_num": prot_num, "protocol_name": "TCP", "state": "ABORT", "timestamp": timestamp, "session_id": connection_uuid, "payload": None}
                                    connections.pop(connection_id, None)
                                    
                                    put_data_to_queue(data)
                                    return

                            put_data_to_queue(data)
                            return

                    if match_protocol("icmp") and packet.haslayer(ICMP):
                        if match_subnet(src_ip, "source") or match_subnet(dst_ip, "destination"):
                            data = {"src_ip": src_ip, "dst_ip": dst_ip, "src_port": None, "dst_port": None, "protocol_num": prot_num, "protocol_name": "ICMP", "state": None, "timestamp": timestamp, "session_id": None, "payload": None}
                            
                            put_data_to_queue(data)
                            return

    except Exception as e:
        print(e)