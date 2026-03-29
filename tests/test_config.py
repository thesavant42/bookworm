"""Tests for the config module"""

import pytest
import json
import tempfile
from pathlib import Path

# Temporarily override config paths for testing
import config as config_module

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory"""
    original_dir = config_module.CONFIG_DIR
    config_module.CONFIG_DIR = tmp_path
    config_module.CONFIG_FILE = tmp_path / 'config.json'
    yield tmp_path
    config_module.CONFIG_DIR = original_dir
    config_module.CONFIG_FILE = config_module.CONFIG_DIR / 'config.json'

@pytest.fixture
def config(temp_config_dir):
    """Create a fresh config instance"""
    return config_module.Config()


class TestConfig:
    """Tests for Config class"""

    def test_default_config(self, temp_config_dir):
        """Test default configuration values"""
        cfg = config_module.Config()
        assert cfg.opds_servers == []
        assert cfg.default_server is None
        assert cfg.download_format == 'epub'
        assert cfg.output_directory is not None

    def test_add_server(self, config):
        """Test adding a server"""
        config.add_server('http://example.com/opds')
        assert 'http://example.com/opds' in config.opds_servers

    def test_remove_server(self, config):
        """Test removing a server"""
        config.add_server('http://example.com/opds')
        config.remove_server('http://example.com/opds')
        assert 'http://example.com/opds' not in config.opds_servers

    def test_set_default_server(self, config):
        """Test setting default server"""
        config.default_server = 'http://example.com/opds'
        assert config.default_server == 'http://example.com/opds'

    def test_set_download_format(self, config):
        """Test setting download format"""
        config.download_format = 'pdf'
        assert config.download_format == 'pdf'

    def test_set_output_directory(self, config):
        """Test setting output directory"""
        test_dir = '/tmp/books'
        config.output_directory = test_dir
        assert config.output_directory == test_dir

    def test_persist_config(self, temp_config_dir):
        """Test that config persists to file"""
        cfg = config_module.Config()
        cfg.add_server('http://example.com/opds')
        cfg.default_server = 'http://example.com/opds'
        
        # Create new instance to verify persistence
        cfg2 = config_module.Config()
        assert 'http://example.com/opds' in cfg2.opds_servers
        assert cfg2.default_server == 'http://example.com/opds'
