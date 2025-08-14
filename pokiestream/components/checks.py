# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

import netifaces

# checks if the interface exists
def check_interface(ifname):
    return ifname in netifaces.interfaces()