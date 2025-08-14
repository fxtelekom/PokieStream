# Plugin How To

## Development

PokieStream plugins are written in Python or Lua and are loaded by the application. We use a simple plugin system to load the plugins and call them for each packet.

The plugin is loaded from the path specified in the config file. Then it will be checked if it has an async `receiver` function for Python or `receiver` function for Lua. If it doesn't, the plugin will not be loaded and the application will exit with an error.

The `receiver` function will receive the packet as the first argument. The packet log is a simple dictionary with the following elements:

- `src_ip`: The source IP address
- `dst_ip`: The destination IP address
- `src_port`: The source port
- `dst_port`: The destination port
- `protocol_num`: The protocol number
- `protocol_name`: The protocol name
- `state`: The state of the connection (NEW, ESTABLISHED, CLOSE, EXPIRED)
- `timestamp`: The UTC timestamp of the packet
- `session_id`: The UUID v7 session ID of the connection
- `payload`: The payload of the packet

For simplicity, we always use the same packet log format for all packets, even if some information is not available. For example, if the packet is ICMP, some fields like **src_port** and **dst_port** will be None/nil.

`payload` is only available if a payload filter is enabled in the config, else it will be None/nil.

### Configuartions in Plugins

The config object is passed as the second argument if `pass_config` is set to True in the config file.

In Python this is a Namespace object and all fields can be accessed as attributes.

```python
async def receiver(packet_log, config):
    print(config.filter.strict)
```

In Lua this is a table and all fields can be accessed as table keys.

```lua
function receiver(packet_log, config)
    print(config.filter.strict)
end
```

## Your first Python plugin

To create your first Python plugin, you need to create a new file called `myplugin.py`. The file should contain a `receiver` function that will receive the packet log as the first argument.

```python

async def receiver(packet_log):
    print(packet_log)

```

You can then specify the path to your plugin in the config file.

### Example payload data

Payload filters are currently only designed to be used for packets that contain a hostname. For example, DNS packets.

If you enable DNS payload filter, the payload data will be available in the packet log as `payload`.
The payload will contain a dictionary with the same name as the filter, so for example if you enable the DNS payload filter, the data will be called `dns`.

```python

async def receiver(packet_log):

    # Print the payload data
    print(packet_log["payload"])
    # Will print out: {'dns': 'example.com'}
```

## Your first Lua plugin

To create your first Lua plugin, you need to create a new file called `myplugin.lua`. The file should contain a `receiver` function that will receive the packet log as the first argument.

Python handles None values gracefully, but in Lua you need to check if a value is nil, otherwise it will throw an error.

```lua

function receiver(packet_log)
    local parts = {}
    if packet_log.timestamp then
        table.insert(parts, "["..packet_log.timestamp.."]")
    end
    print(table.concat(parts, " "))
end

```

You can then specify the path to your plugin in the config file.

## Security Considerations

- Plugins run with same permissions as main application
- Validate all inputs in security-sensitive plugins

## Performance

As the application is built with Python, the better choice for plugins is Python as you can directly write async functions. However you should keep in mind that Python GIL still exist and there is no real multithreading in this scenario.

Lua in the other hand does not have a native async support. We use `asyncio.to_thread()` to run each Lua process in a separate OS thread, which allows an almost full multithreading. While the GIL is released during Lua execution, thread switching will still have some overhead.

Both Python and Lua can be a good choice for plugins, it depends on your use case and the packet count. For extremely high packet throughput, Lua may be a better choice as it enables near parallel multithreading, though each Lua execution creates a new OS thread with significantly higher memory overhead than Python's async coroutines.

For I/O bound tasks like database or API calls, Python is clearly the winner due to its true async capabilities that can efficiently handle concurrent operations. For pure CPU bound tasks like packet analysis, Lua's multithreading will provide better performance.

There are already plans to implement a bulk processing mode for plugins, which will allow you to recieve and process multiple packets at once based on the packet count in the queue. This can be handy if you want to send the packet logs to a database or a cloud service. Of course, you can also implement your own bulk processing logic in the plugin.
