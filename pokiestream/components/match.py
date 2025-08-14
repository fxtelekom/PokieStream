# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

import ipaddress
from pokiestream.components.config import config, has_field
import fnmatch

def get_attr_by_path(obj, path):
    for attr in path.split('.'):
        obj = getattr(obj, attr, None)
        if obj is None:
            return None
    return obj

# matches a source IP address against a list of subnets in the config
def match_subnet(ip, field):
    if not ((has_field("filter.source") and config.filter.source) or (has_field("filter.destination") and config.filter.destination)):
        return True

    subnet_list = getattr(config.filter, field, None)
    if not subnet_list:
        return False

    subnets = [ipaddress.ip_network(subnet) for subnet in subnet_list]
    try:
        return any(ipaddress.ip_address(ip) in subnet for subnet in subnets)
    except ValueError:
        return False

# matches a port against a list of ports in the config
def match_port(port, field="filter.port"):
    if not has_field(field):
        return True

    port_list = get_attr_by_path(config, field)
    if port_list is None:
        return True

    return port in port_list

# matches a protocol against a list of protocols in the config
def match_protocol(protocol):
    if not has_field("filter.protocol") or config.filter.protocol is None:
        return True

    protocol_list = config.filter.protocol
    return protocol.lower() in protocol_list


def match_host(hostname, type_):
    type_ = type_.lower()
    if type_ not in ("dns"):
        return True

    domain_list = None

    if type_ == "dns":
        domain_list = config.filter.payload.dns.match

    if not domain_list:
        return True

    hostname = hostname.lower()
    for pattern in domain_list:
        if fnmatch.fnmatch(hostname, pattern.lower()):
            return True

    return False
