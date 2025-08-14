# SPDX-License-Identifier: AGPL-3.0
# Copyright (C) 2025  FXTELEKOM

import importlib.util
import sys
import os
import asyncio
from lupa import LuaRuntime
from pokiestream.components.config import config

def convert_config_for_lua(config):
    if hasattr(config, '__dict__'): 
        return {k: convert_config_for_lua(v) for k, v in vars(config).items()}
    elif isinstance(config, (list, tuple)):
        return [convert_config_for_lua(x) for x in config]
    else:
        return config

def load_python_plugin(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Plugin file not found: {path}")

    module_name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        raise ImportError(f"Cannot load spec from: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "receiver"):
        raise AttributeError(f"Python plugin must implement async 'receiver(data, config)'")

    if not asyncio.iscoroutinefunction(module.receiver):
        raise TypeError("Python plugin receiver must be async function")

    return module.receiver

def load_lua_plugin(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Lua plugin file not found: {path}")

    lua = LuaRuntime()
    with open(path, 'r') as f:
        lua_code = f.read()

    lua.execute(lua_code)
    lua_receiver = lua.globals().receiver

    if not lua_receiver:
        raise AttributeError("Lua plugin must implement 'receiver(data, config)'")

    def async_receiver(data, config=None):
        async def _run():
            if config and config.plugin.pass_config:
                return await asyncio.to_thread(lua_receiver, data, convert_config_for_lua(config))
            else:
                return await asyncio.to_thread(lua_receiver, data)
        return _run()

    return async_receiver

def load_receiver():
    path = config.plugin.path
    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".py":
            receiver = load_python_plugin(path)
            print(f"Python plugin loaded: {os.path.basename(path)}")
            return receiver
        elif ext == ".lua":
            receiver = load_lua_plugin(path)
            print(f"Lua plugin loaded: {os.path.basename(path)}")
            return receiver
        else:
            raise ValueError(f"Unsupported plugin type: {ext}")

    except Exception as e:
        raise ValueError(f"Failed to load plugin: {e}")