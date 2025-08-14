function receiver(packet_log, config)
    local parts = {}
    
    local function add_part(label, value)
        if value ~= nil then
            table.insert(parts, string.format("%s: %s", label, value))
        end
    end

    if packet_log.timestamp then
        table.insert(parts, 1, "["..packet_log.timestamp.."]")
    end

    if packet_log.src_ip or packet_log.dst_ip then
        local conn_str = ""
        if packet_log.src_ip then
            conn_str = conn_str .. packet_log.src_ip
            if packet_log.src_port then
                conn_str = conn_str .. ":" .. packet_log.src_port
            end
        end
        
        conn_str = conn_str .. " -> "
        
        if packet_log.dst_ip then
            conn_str = conn_str .. packet_log.dst_ip
            if packet_log.dst_port then
                conn_str = conn_str .. ":" .. packet_log.dst_port
            end
        end
        
        table.insert(parts, conn_str)
    end

    if packet_log.protocol_name then
        local protocol_str = "Protocol: " .. packet_log.protocol_name
        if packet_log.protocol_num then
            protocol_str = protocol_str .. " (" .. packet_log.protocol_num .. ")"
        end
        table.insert(parts, protocol_str)
    end

    add_part("State", packet_log.state)
    add_part("Session", packet_log.session_id)

    print(table.concat(parts, " "))
    
    return { success = true }
end