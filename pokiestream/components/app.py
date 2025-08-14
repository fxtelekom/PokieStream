# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

import asyncio
import threading
import sys
import logging

from scapy.all import sniff
from scapy.config import conf
from pokiestream.components.packets import inspect_packets
from pokiestream.components.config import config
from pokiestream.components.queue import create_queue, queues
from pokiestream.components.checks import check_interface
from pokiestream.components.plugin import load_receiver
from pokiestream.components.udp import start_cleanup_task

# Supress scapy errors.
logging.getLogger("scapy.runtime").setLevel(logging.CRITICAL)

# initialize the sniffer
def run_sniffer():
    try:
        conf.debug_dissector = 2
        sniff(prn=inspect_packets, store=0, iface=config.iface, filter=config.filter.scapy)
    except ValueError as e:
        print(f"There is an error with the sniffer: {e}")

# process the queue
async def process_queue():
    receiver = load_receiver()

    while True:
        if queues['log_queue'].async_q.qsize() > 0:
            data = await queues['log_queue'].async_q.get()
            if receiver:
                if config.plugin.pass_config:
                    await receiver(data, config)
                else:
                    await receiver(data)

            else:
                print(f"{data}")

        if not config.NOT_RECOMMENDED.bypass_polling_delay:
            await asyncio.sleep(0.01)

async def async_main():
    if not check_interface(config.iface):
        print(f"Interface {config.iface} does not exist.")
        sys.exit(1)

    await create_queue('log_queue')

    # start the sniffer in different thread
    sniffer_thread = threading.Thread(target=run_sniffer, daemon=True)
    sniffer_thread.start()

    asyncio.create_task(start_cleanup_task())
    await process_queue()


def main():
    try:
        asyncio.run(async_main())

    except KeyboardInterrupt:
        print("\nExiting gracefully...")
        sys.exit(0)