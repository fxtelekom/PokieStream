# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

import culsans as janus
from pokiestream.components.config import config

queues = {}

# Create an asyncio queue using janus
async def async_queue():
    if not config.queue_size:
        config.queue_size = 10000
    queue = janus.Queue(maxsize=config.queue_size)

    return queue

# used to map multiple queues to different names
async def create_queue(name):
    queue = await async_queue()
    queues[name] = queue
