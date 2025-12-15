"""
Filesystem Fixtures for Pytest Testing
Netrun Systems - Service #70 Unified Test Fixtures

Provides temporary directory and file fixtures for filesystem testing.
Automatically cleans up after tests to prevent disk space pollution.

Usage:
    def test_file_operations(temp_directory):
        test_file = temp_directory / "test.txt"
        test_file.write_text("content")
        assert test_file.exists()
        # Directory automatically cleaned up after test

Fixtures:
    - temp_directory: Temporary directory for file operations
    - temp_file: Temporary file with optional content
    - temp_json_file: Temporary JSON file with data
    - temp_yaml_file: Temporary YAML file with data
    - temp_repo_structure: Mock repository structure for testing
"""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Generator

# Graceful netrun-logging integration (optional)
_use_netrun_logging = False
_logger = None
try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)


@pytest.fixture
def temp_directory(tmp_path: Path) -> Path:
    """
    Create temporary directory for file operations.

    Provides isolated directory that's automatically cleaned up.
    Use for testing file I/O, directory operations, and file processing.

    Args:
        tmp_path: Pytest's built-in temporary directory fixture

    Returns:
        Path: Temporary directory path

    Example:
        def test_directory_operations(temp_directory):
            subdir = temp_directory / "subdir"
            subdir.mkdir()
            assert subdir.exists()

            test_file = subdir / "file.txt"
            test_file.write_text("test content")
            assert test_file.read_text() == "test content"
    """
    return tmp_path


@pytest.fixture
def temp_file(temp_directory: Path):
    """
    Factory for creating temporary files with optional content.

    Returns function that creates file in temporary directory.

    Args:
        temp_directory: Temporary directory fixture

    Returns:
        Callable: Function that creates temporary file

    Example:
        def test_file_processing(temp_file):
            file_path = temp_file("test.txt", "file content")
            assert file_path.exists()
            assert file_path.read_text() == "file content"

            # Binary file
            bin_path = temp_file("data.bin", b"\\x00\\x01\\x02", binary=True)
            assert bin_path.read_bytes() == b"\\x00\\x01\\x02"
    """
    def _create_file(
        filename: str,
        content: Any = "",
        binary: bool = False
    ) -> Path:
        file_path = temp_directory / filename

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if binary:
            file_path.write_bytes(content if isinstance(content, bytes) else content.encode())
        else:
            file_path.write_text(str(content))

        return file_path

    return _create_file


@pytest.fixture
def temp_json_file(temp_directory: Path):
    """
    Factory for creating temporary JSON files with data.

    Args:
        temp_directory: Temporary directory fixture

    Returns:
        Callable: Function that creates JSON file

    Example:
        def test_json_config(temp_json_file):
            data = {"key": "value", "number": 42}
            json_path = temp_json_file("config.json", data)

            with open(json_path) as f:
                loaded = json.load(f)
            assert loaded["key"] == "value"
    """
    def _create_json_file(filename: str, data: Dict[str, Any]) -> Path:
        file_path = temp_directory / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        return file_path

    return _create_json_file


@pytest.fixture
def temp_yaml_file(temp_directory: Path):
    """
    Factory for creating temporary YAML files with data.

    Args:
        temp_directory: Temporary directory fixture

    Returns:
        Callable: Function that creates YAML file

    Example:
        def test_yaml_config(temp_yaml_file):
            data = {"service": {"name": "test", "port": 8080}}
            yaml_path = temp_yaml_file("config.yaml", data)

            import yaml
            with open(yaml_path) as f:
                loaded = yaml.safe_load(f)
            assert loaded["service"]["name"] == "test"
    """
    def _create_yaml_file(filename: str, data: Dict[str, Any]) -> Path:
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed - install with: pip install pyyaml")

        file_path = temp_directory / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

        return file_path

    return _create_yaml_file


@pytest.fixture
def temp_repo_structure(temp_directory: Path):
    """
    Create mock repository structure for testing.

    Creates typical project structure with directories and files
    for testing repository operations, file discovery, etc.

    Args:
        temp_directory: Temporary directory fixture

    Returns:
        Path: Root directory of mock repository

    Example:
        def test_repo_discovery(temp_repo_structure):
            # Repository structure already created
            src_dir = temp_repo_structure / "src"
            assert src_dir.exists()

            py_files = list(src_dir.rglob("*.py"))
            assert len(py_files) > 0
    """
    # Create directory structure
    directories = [
        "src",
        "src/app",
        "src/app/models",
        "src/app/services",
        "src/app/api",
        "tests",
        "tests/unit",
        "tests/integration",
        "docs",
        "scripts",
    ]

    for dir_path in directories:
        (temp_directory / dir_path).mkdir(parents=True, exist_ok=True)

    # Create sample files
    files = {
        "README.md": "# Test Repository\n\nTest repository structure.",
        "pyproject.toml": "[project]\nname = 'test-project'\nversion = '1.0.0'\n",
        "requirements.txt": "pytest>=7.0.0\nfastapi>=0.100.0\n",
        ".gitignore": "__pycache__/\n*.pyc\n.env\n",
        "src/__init__.py": "",
        "src/app/__init__.py": "",
        "src/app/models/__init__.py": "",
        "src/app/models/user.py": "class User:\n    pass\n",
        "src/app/services/__init__.py": "",
        "src/app/services/user_service.py": "class UserService:\n    pass\n",
        "src/app/api/__init__.py": "",
        "src/app/api/routes.py": "from fastapi import APIRouter\n",
        "tests/__init__.py": "",
        "tests/conftest.py": "import pytest\n",
        "tests/unit/__init__.py": "",
        "tests/unit/test_user.py": "def test_user():\n    pass\n",
        "tests/integration/__init__.py": "",
        "tests/integration/test_api.py": "def test_api():\n    pass\n",
    }

    for file_path, content in files.items():
        full_path = temp_directory / file_path
        full_path.write_text(content)

    return temp_directory


@pytest.fixture
def temp_config_file(temp_directory: Path):
    """
    Create temporary configuration file for testing.

    Args:
        temp_directory: Temporary directory fixture

    Returns:
        Path: Path to config file

    Example:
        def test_config_loading(temp_config_file):
            config = load_config(temp_config_file)
            assert config.app_name == "TestApp"
    """
    config_path = temp_directory / "config.json"
    config_data = {
        "app_name": "TestApp",
        "version": "1.0.0",
        "environment": "testing",
        "database": {
            "url": "postgresql://test:test@localhost:5432/test",
            "pool_size": 5
        },
        "redis": {
            "host": "localhost",
            "port": 6379
        }
    }

    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=2)

    return config_path


@pytest.fixture
def temp_log_file(temp_directory: Path) -> Path:
    """
    Create temporary log file for testing logging functionality.

    Args:
        temp_directory: Temporary directory fixture

    Returns:
        Path: Path to log file

    Example:
        def test_logging(temp_log_file):
            import logging

            handler = logging.FileHandler(temp_log_file)
            logger = logging.getLogger("test")
            logger.addHandler(handler)

            logger.info("Test message")

            log_content = temp_log_file.read_text()
            assert "Test message" in log_content
    """
    log_path = temp_directory / "test.log"
    log_path.touch()  # Create empty file
    return log_path


@pytest.fixture
def temp_csv_file(temp_directory: Path):
    """
    Factory for creating temporary CSV files with data.

    Args:
        temp_directory: Temporary directory fixture

    Returns:
        Callable: Function that creates CSV file

    Example:
        def test_csv_processing(temp_csv_file):
            headers = ["name", "age", "email"]
            rows = [
                ["Alice", "30", "alice@example.com"],
                ["Bob", "25", "bob@example.com"]
            ]
            csv_path = temp_csv_file("users.csv", headers, rows)

            import csv
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                users = list(reader)
            assert len(users) == 2
    """
    def _create_csv_file(filename: str, headers: list, rows: list) -> Path:
        import csv

        file_path = temp_directory / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        return file_path

    return _create_csv_file


@pytest.fixture
def temp_binary_file(temp_directory: Path):
    """
    Factory for creating temporary binary files.

    Args:
        temp_directory: Temporary directory fixture

    Returns:
        Callable: Function that creates binary file

    Example:
        def test_binary_processing(temp_binary_file):
            data = b"\\x89PNG\\r\\n\\x1a\\n"  # PNG header
            png_path = temp_binary_file("image.png", data)

            with open(png_path, 'rb') as f:
                header = f.read(8)
            assert header == data
    """
    def _create_binary_file(filename: str, data: bytes) -> Path:
        file_path = temp_directory / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return file_path

    return _create_binary_file
