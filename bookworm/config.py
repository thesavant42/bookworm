"""Configuration management for Bookworm CLI."""

import os
from pathlib import Path
from typing import List, Optional


def get_config_path() -> Path:
    """Get the path to the Bookworm config file."""
    return Path.home() / ".bookworm" / "servers"


def load_servers(config_path: Optional[Path] = None) -> List[str]:
    """
    Load server URLs from config file.
    
    Returns a list of server URLs, one per line.
    Empty lines and lines starting with '#' are ignored.
    """
    path = config_path or get_config_path()
    
    if not path.exists():
        return []
    
    servers = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            servers.append(line)
    
    return servers


def save_servers(servers: List[str], config_path: Optional[Path] = None) -> None:
    """
    Save server URLs to config file.
    
    Each server URL is written on a separate line.
    """
    path = config_path or get_config_path()
    
    # Create parent directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        for server in servers:
            f.write(f"{server}\n")


def add_server(server: str, config_path: Optional[Path] = None) -> None:
    """Add a server URL to the config file."""
    servers = load_servers(config_path)
    
    if server not in servers:
        servers.append(server)
        save_servers(servers, config_path)


def remove_server(server: str, config_path: Optional[Path] = None) -> None:
    """Remove a server URL from the config file."""
    servers = load_servers(config_path)
    
    if server in servers:
        servers.remove(server)
        save_servers(servers, config_path)
