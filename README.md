# PokieStream

PokieStream is a lightweight network traffic monitoring program designed for simplicity and extensibility. Inspired by `conntrack`, it provides real-time packet inspection with plugin support, allowing for customizable logging and analysis.

## Inspiration

PokieStream was highly inspired by `conntrack`. It was mainly created to provide an extensible conntrack-like network monitoring tool. Thanks to the plugin system, the tool allows anyone to extend its features and process the data however they want. For example, you can write logs to a database or stream them to a cloud monitoring service like DataDog.

For more information about plugins and how to develop them, read [docs/plugin-how-to.md](docs/plugin-how-to.md).

## Features

- **Protocol Support**: Monitors TCP, UDP, and ICMP traffic
- **Flexible Filtering**: Filter by source/destination IP, port, or protocol
- **Payload Inspection**: Supports DNS payload filtering (UDP only)
- **Plugin System**: Extend functionality with custom plugins in Python or Lua
- **UDP Session Tracking**: Tracks UDP sessions and expires them when they are idle
- **TCP Session Tracking**: Tracks TCP sessions and logs all lifecycle events (SYN,SYN-ACK,ACK,FIN,RST)

Due to the stateless nature of UDP, we can't really track UDP connections like we can with TCP. Therefore we use the Source IP, Source Port, Destination IP and Destination Port to create a unique session identifier. While this is not a true session, it is a simple and effective way to track UDP sessions and many applications and stateful firewalls use a similar approach.

All UDP and TCP session has a unique UUID v7 identifier which can be used to track the connection lifecycle.

While each packet has a timestamp, the UUID can be also used to sort the packets in the order they were received. Thanks to UUID v7.

## Configuration

PokieStream is configured via `config.yaml`.

The application will try to load the config from `config.yaml` in the current directory.
A config file can also be specified with the `--config` or `-c` flag.

### Interface

PokieStream supports both SPAN and TAP interfaces.

```yaml
iface: "eth0"  # Network interface to monitor
```

### Queue Size

PokieStream supports a configurable queue size.

```yaml
queue_size: 10000  # Queue size (default: 10000)
```

### Plugins

PokieStream supports python and lua plugins to extend its functionality. There is also a default plugin called `plain` which performs an RDNS lookup on the IP address and prints the packet information to the console.

```yaml
plugin:
  path: "plugins/plain.py" # The plugin to use
  pass_config: False # Whether to pass the config to the plugin
```

`pass_config` is useful if you want to pass the config to the plugin. The config will be passed as the second argument to the plugin. (more on [docs/plugin-how-to.md](docs/plugin-how-to.md))

### Filters

PokieStream supports filters to filter the packets before processing them.

Filters are completely optional and can be fully disabled by removing the `filter` section from the config file

```yaml
filter:
  strict: False # Whether to use strict filtering 
  protocol: # The protocols to monitor (can be multiple)
    - udp
    - tcp
    - icmp
  source: # The source IP addresses to monitor (can be a subnet or a single IP, multiple can be specified)
    - 192.168.1.0/24
    - 172.16.0.0/16
  destination: # The destination IP addresses(es) to monitor (can be a subnet or a single IP, multiple can be specified)
    - 1.1.1.1
    - 1.0.0.1
  port: # The ports to monitor (can be multiple)
    - 80
    - 443
  payload:
    dns:
      enabled: True
      ports:
        - 53
      match:
        - "example.com"
        - "*.mydomain.com"

  scapy: "tcp and (port 80 or port 443)" # scapy filter expression
```

`strict`: If set to True, both source and destination must match, if set to False, either source or destination is enough to match and log the packet.

`protocol`: The protocols to monitor (can be multiple)

`source`: The source IP addresses to monitor (can be a subnet or a single IP, multiple can be specified)

`destination`: The destination IP addresseses to monitor (can be a subnet or a single IP, multiple can be specified)

`port`: The ports to monitor (can be multiple)

`payload`: The payload filters are useful if you want to filter by the payload of the packet. A payload filter is a subfilter of the main filter.
This means that the payload filter will only be applied to the packets that match the main filter first.
For example, if you want to filter by the DNS packet, you need to enable port 53 and the udp protocol on the main filter.
You also need to enable the payload filter itself. A payload filter supports port and domain matching.
For example if you want to log all DNS packets on port 53 but you only want to log if *.example.com is in the DNS request you can do that.
Although payload filters are useful, this application is not designed to be a full featured packet analyzer. It's main goal is
to be a simple and fast tool to monitor traffic just like conntrack but with plugins and extensible features.

*If you need a full featured packet analyzer, you should use a tool like Wireshark, Tshark or Scapy (which PokieStream is based on).*

`scapy`: The scapy filter expression to monitor.

## Performance & Limitations

PokieStream is built for speed and efficiency, but like any system, it has certain tradeoffs and limitations.

The application is highly asynchronous and uses a sync-async queue to process the packets. Since Scapy is not async compatible, we use a dedicated thread to capture packets and write them into the queue. An async loop then retrieves packets from the queue, forwarding them to the specified plugin, or, if no plugin is loaded, printing the RAW packet data to the console.

PokieStream implements a heap-based tracking system for UDP connections to efficiently track and expire "sessions". This system uses O(log n) time complexity for tracking and O(1) for expiration, making it more efficient than a hash table or dictionary.

This architecture ensures high performance and efficiency while enabling asynchronous packet processing. It’s extremely useful for plugins that involve IO heavy tasks, such as database writes or streaming to cloud services.

While, the most part of the application is async, the packet capture is done in a sync thread which means the packet capture is a single threaded process. However as Scapy runs in a different thread, it means the main thread is not blocked by the packet capture process.

The packets are forwarded as soon as possible to the plugin, however if the queue is empty we add a 10ms delay to the polling interval to prevent the program from using too much CPU. This should not cause any issues in a real world use case. If you want to bypass this delay, you can disable this polling delay in the config.

```yaml
    NOT_RECOMMENDED:
        bypass_polling_delay: False
```

As we use a local queue, we need to make sure that the plugin can keep up with the packet processing speed. The default queue size is 10000 entries. If the queue gets full, the program will start to drop packets. Keep in mind that delayed packets will NOT have a delayed timestamp, they will have the timestamp of when they were received, it will just be processed later.

### TODOS

This program is far from perfect and has many limitations right now. There are already plans for future development:

- Adding an availability to send packet logs to plugins as bulk instead of one by one
- Official plugins for TimescaleDB and InfluxDB
- Adding more payload filters: SNI,TCP DNS, HTTP Host...

If you have any suggestions or ideas for future development, please let me know via GitHub issues or by joining the [FXTELEKOM](https://discord.com/invite/n2WmGaEn3H) Discord server.
