# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

from types import SimpleNamespace
import ipaddress
import os

def is_valid_cidr(cidr):
    try:
        ipaddress.ip_network(cidr)
        return True
    except ValueError:
        return False

def is_valid_plugin_path(path):
    return isinstance(path, str) and os.path.isfile(path) and (path.endswith(".py") or path.endswith(".lua"))


def validate_config(config):
    errors = []
    warnings = []
    
    def validate_field(path, value, rules):
        def err(msg):
            errors.append(rules.get("message", msg))

        if value is None or (isinstance(value, dict) and not value) or (isinstance(value, SimpleNamespace) and not value.__dict__) or (isinstance(value, list) and not value):
            if rules.get("optional", False):
                warnings.append(f"{path} is set but empty, ignored.")
            else:
                err(f"{path} is required but was empty.")
            return
        
        if "type" in rules and not isinstance(value, rules["type"]):
            err(f"{path} must be of type {rules['type'].__name__}. Got {type(value).__name__}.")
            return
        
        if "values" in rules and isinstance(value, list):
            invalid_values = [v for v in value if v not in rules["values"]]
            for v in invalid_values:
                err(f"{path} contains an invalid value: {v}. Allowed values are: {', '.join(map(str, rules['values']))}.")
        
        if "item_type" in rules and isinstance(value, list):
            type_error = False
            for item in value:
                if not isinstance(item, rules["item_type"]):
                    err(f"{path} contains an invalid value: {item}. Expected type: {rules['item_type'].__name__}.")
                    type_error = True
                    continue
                if "validator" in rules and not rules["validator"](item):
                    err(f"{path} contains an invalid value: {item}. Value failed validation.")
                    type_error = True
                    continue
            if type_error:
                return

        else:
            if "validator" in rules and not rules["validator"](value):
                err(f"{path} contains an invalid value: {value}. Value failed validation.")
                return

        if "range" in rules:
            try:
                if isinstance(value, list):
                    for item in value:
                        if not (rules["range"][0] <= item <= rules["range"][1]):
                            err(f"{path} has an invalid value: {item}. Valid range is {rules['range'][0]}–{rules['range'][1]}.")
                else:
                    if not (rules["range"][0] <= value <= rules["range"][1]):
                        err(f"{path} has an invalid value: {value}. Valid range is {rules['range'][0]}–{rules['range'][1]}.")
            except TypeError:
                err(f"{path} contains an invalid value type. Expected a number within range {rules['range'][0]}–{rules['range'][1]}.")

    rules = {
        "plugin": {"type": dict, "optional": True},
        "plugin.path": {
            "type": str, "optional": True,
            "validator": is_valid_plugin_path,
            "message": "Plugin path must be a valid existing .py or .lua file."
        },
        "plugin.pass_config": {"type": bool, "optional": True},

        "iface": {"type": str},
        "queue_size": {"type": int, "optional": True},

        "filter": {"type": dict, "optional": True},
        "filter.source": {
            "item_type": str, "optional": True,
            "validator": is_valid_cidr,
            "message": "Filter source must be a valid CIDR or a single IP address."
        },
        "filter.destination": {
            "item_type": str, "optional": True,
            "validator": is_valid_cidr,
            "message": "Filter destination must be a valid CIDR or a single IP address."
        },
        "filter.port": {
            "item_type": int, "range": (0, 65535), "optional": True,
            "message": "Filter port must be a valid port number between 0 and 65535."
        },
        "filter.protocol": {
            "item_type": str,
            "values": ["tcp", "udp", "icmp", "ip", "arp", "all"],
            "optional": True,
            "message": "Filter protocol must be one of: tcp, udp, icmp, ip, arp, all."
        },
        "filter.scapy": {
            "type": str, "optional": True,
            "message": "Filter scapy must be a valid scapy filter expression."
        },
        "filter.strict": {
            "type": bool, "optional": True,
            "message": "Filter strict must be a boolean value."
        },

        # Payload filters
        "filter.payload": {"type": dict, "optional": True},

        "filter.payload.dns": {"type": dict, "optional": True},
        "filter.payload.dns.enabled": {"type": bool, "optional": True},
        "filter.payload.dns.ports": {
            "item_type": int, "range": (0, 65535),
            "optional": True,
            "message": "DNS ports must be integers between 0 and 65535."
        },
        "filter.payload.dns.match": {
            "item_type": str,
            "optional": True,
            "validator": lambda v: isinstance(v, str) and len(v) > 0,
            "message": "DNS match entries must be non-empty strings."
        },

        "NOT_RECOMMENDED": {"type": dict, "optional": True},
        "NOT_RECOMMENDED.bypass_polling_delay": {
            "type": bool, "optional": True
        }
    }

    def recurse(namespace, current_path=""):
        for key, value in namespace.__dict__.items():
            path = f"{current_path}.{key}" if current_path else key
            if isinstance(value, SimpleNamespace):
                recurse(value, path)
            else:
                rule = rules.get(path)
                if rule:
                    validate_field(path, value, rule)

    recurse(config)
    return errors, warnings

def config_validation(config):
    validation_errors, validation_warnings = validate_config(config)

    if validation_warnings:
        print("Validation Warnings:")
        for warning in validation_warnings:
            print(f" - {warning}")
            status = True

    if validation_errors:
        print("Validation Errors:")
        for error in validation_errors:
            print(f" - {error}")
            status = False
        
    else:
        status = True

    if status:
        print("All configuration values are passed the validation.")

    return status