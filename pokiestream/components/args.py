# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

import argparse

parser = argparse.ArgumentParser(description="PokieStream - A simple and fast packet sniffer with plugins.")
parser.add_argument("-c", "--config", help="Path to the config file", default="config.yml")
args = parser.parse_args()