# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

import yaml
from types import SimpleNamespace
from copy import deepcopy
from pokiestream.components.validator import config_validation
import sys
from pokiestream.components.args import args

CONFIG = args.config if args.config else "config.yml"

DEFAULTS = {
    "NOT_RECOMMENDED": {
        "bypass_polling_delay": False,
    },

    "filter": {
        "scapy": "",
        "strict": False,
        "payload": {
            "dns": {
                "enabled": False,
                "ports": [],
                "match": []
            }
        }
    },

    "plugin": {
        "pass_config": False
    }
}

def merge_defaults(defaults, user_config):
    if user_config is None:
        return deepcopy(defaults)
    
    if not isinstance(defaults, dict) or not isinstance(user_config, dict):
        return user_config

    merged = deepcopy(defaults)

    for key, value in user_config.items():
        if key in merged:
            if value is None or (isinstance(value, dict) and not value) or (isinstance(value, SimpleNamespace) and not value.__dict__):
                continue
            if isinstance(value, SimpleNamespace):
                merged[key] = merge_defaults(merged[key], value.__dict__)
            else:
                merged[key] = merge_defaults(merged[key], value)
        else:
            merged[key] = value

    return merged

# converts a dict to a namespace
def dtn(d):
    if not isinstance(d, dict):
        return d.strip() if isinstance(d, str) else d
    return SimpleNamespace(**{k: dtn(v) for k, v in d.items()})

# loads the config.yml
def load_config(yml):
    config_dict = yaml.safe_load(yml)
    return dtn(config_dict["config"])


try:
    config = load_config(open(CONFIG).read())
except FileNotFoundError:
    print(f"Config file {CONFIG} not found. Please create a config.yml file or specify a config file with the --config option.")
    sys.exit(1)

# Check the configuration values before merging any defaults
if not config_validation(config):
    sys.exit(1)

config_dict = config.__dict__
merged_config = merge_defaults(DEFAULTS, config_dict)
config = dtn(merged_config)

def has_field(path):
    keys = path.split(".")
    current = config
    try:
        for key in keys:
            current = getattr(current, key)
        return True
    except AttributeError:
        return False