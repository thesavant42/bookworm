"""config.py: Configuration management for bookworm CLI"""

import json
import os
from pathlib import Path
from typing import List, Optional


CONFIG_DIR = Path.home() / '.bookworm'
CONFIG_FILE = CONFIG_DIR / 'config.json'


class Config:
    """Configuration manager for bookworm"""

    def __init__(self):
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return self._default_config()

    def _default_config(self) -> dict:
        """Return default configuration"""
        return {
            'opds_servers': [],
            'default_server': None,
            'download_format': 'epub',
            'output_directory': str(Path.home() / 'Downloads' / 'books'),
        }

    def save(self):
        """Save configuration to file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self._config, f, indent=2)

    @property
    def opds_servers(self) -> List[str]:
        """Get list of configured OPDS servers"""
        return self._config.get('opds_servers', [])

    @opds_servers.setter
    def opds_servers(self, value: List[str]):
        """Set list of OPDS servers"""
        self._config['opds_servers'] = value
        self.save()

    @property
    def default_server(self) -> Optional[str]:
        """Get default OPDS server URL"""
        return self._config.get('default_server')

    @default_server.setter
    def default_server(self, value: Optional[str]):
        """Set default OPDS server"""
        self._config['default_server'] = value
        self.save()

    @property
    def download_format(self) -> str:
        """Get preferred download format"""
        return self._config.get('download_format', 'epub')

    @download_format.setter
    def download_format(self, value: str):
        """Set preferred download format"""
        self._config['download_format'] = value
        self.save()

    @property
    def output_directory(self) -> str:
        """Get default output directory"""
        return self._config.get('output_directory', str(Path.home() / 'Downloads' / 'books'))

    @output_directory.setter
    def output_directory(self, value: str):
        """Set default output directory"""
        self._config['output_directory'] = value
        self.save()

    def add_server(self, url: str):
        """Add a server to the configured list"""
        if url not in self._config['opds_servers']:
            self._config['opds_servers'].append(url)
            self.save()

    def remove_server(self, url: str):
        """Remove a server from the configured list"""
        if url in self._config['opds_servers']:
            self._config['opds_servers'].remove(url)
            self.save()


# Global config instance
config = Config()
