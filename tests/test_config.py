"""Tests for endpoint configuration parsing and validation."""

import pytest
import yaml
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path to import collector
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector import load_config


def test_load_valid_config():
    """Test loading a valid configuration file."""
    config_data = {
        'endpoints': [
            {
                'name': 'Test Endpoint',
                'url': 'https://example.com',
                'method': 'GET',
                'interval_seconds': 30,
                'timeout_seconds': 5
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        # Temporarily replace CONFIG_PATH
        import collector
        original_path = collector.CONFIG_PATH
        collector.CONFIG_PATH = temp_path
        
        endpoints = load_config()
        
        assert len(endpoints) == 1
        assert endpoints[0]['name'] == 'Test Endpoint'
        assert endpoints[0]['url'] == 'https://example.com'
        assert endpoints[0]['method'] == 'GET'
        assert endpoints[0]['interval_seconds'] == 30
        assert endpoints[0]['timeout_seconds'] == 5
        
        collector.CONFIG_PATH = original_path
    finally:
        os.unlink(temp_path)


def test_load_config_with_defaults():
    """Test that default values are applied correctly."""
    config_data = {
        'endpoints': [
            {
                'name': 'Test Endpoint',
                'url': 'https://example.com'
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        import collector
        original_path = collector.CONFIG_PATH
        collector.CONFIG_PATH = temp_path
        
        endpoints = load_config()
        
        assert endpoints[0]['method'] == 'GET'
        assert endpoints[0]['interval_seconds'] == 60
        assert endpoints[0]['timeout_seconds'] == 5
        
        collector.CONFIG_PATH = original_path
    finally:
        os.unlink(temp_path)


def test_load_config_missing_name():
    """Test that missing name raises an error."""
    config_data = {
        'endpoints': [
            {
                'url': 'https://example.com'
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        import collector
        original_path = collector.CONFIG_PATH
        collector.CONFIG_PATH = temp_path
        
        with pytest.raises(ValueError, match="must have 'name' and 'url'"):
            load_config()
        
        collector.CONFIG_PATH = original_path
    finally:
        os.unlink(temp_path)


def test_load_config_missing_url():
    """Test that missing url raises an error."""
    config_data = {
        'endpoints': [
            {
                'name': 'Test Endpoint'
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        import collector
        original_path = collector.CONFIG_PATH
        collector.CONFIG_PATH = temp_path
        
        with pytest.raises(ValueError, match="must have 'name' and 'url'"):
            load_config()
        
        collector.CONFIG_PATH = original_path
    finally:
        os.unlink(temp_path)


def test_load_config_missing_endpoints_key():
    """Test that missing endpoints key raises an error."""
    config_data = {}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        import collector
        original_path = collector.CONFIG_PATH
        collector.CONFIG_PATH = temp_path
        
        with pytest.raises(ValueError, match="must contain 'endpoints' key"):
            load_config()
        
        collector.CONFIG_PATH = original_path
    finally:
        os.unlink(temp_path)

