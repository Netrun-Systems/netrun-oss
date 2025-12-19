"""
Pytest configuration and fixtures for namespace package import tests.

This module provides fixtures for testing the netrun namespace package
structure, including temporary installations, package discovery, and
cross-package dependency validation.
"""

import importlib
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator, List
import pytest


@pytest.fixture(scope="session")
def package_root() -> Path:
    """Return the absolute path to the packages directory."""
    return Path(__file__).parent.parent.resolve()


@pytest.fixture(scope="session")
def available_packages(package_root: Path) -> List[str]:
    """
    Discover all available netrun packages in the repository.

    Returns:
        List of package names (e.g., ['netrun-auth', 'netrun-config'])
    """
    packages = []
    for pkg_dir in package_root.iterdir():
        if pkg_dir.is_dir() and pkg_dir.name.startswith("netrun-"):
            pyproject = pkg_dir / "pyproject.toml"
            if pyproject.exists():
                packages.append(pkg_dir.name)
    return sorted(packages)


@pytest.fixture(scope="session")
def installed_packages() -> List[str]:
    """
    Get list of actually installed netrun packages.

    Returns:
        List of installed package names
    """
    import pkg_resources

    installed = []
    for dist in pkg_resources.working_set:
        if dist.project_name.startswith("netrun-"):
            installed.append(dist.project_name)
    return sorted(installed)


@pytest.fixture
def temp_install_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test installations.

    Yields:
        Temporary directory path
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def isolated_python_env(temp_install_dir: Path) -> Generator[dict, None, None]:
    """
    Create an isolated Python environment for testing package installations.

    Yields:
        Dictionary with 'python' and 'pip' executable paths
    """
    venv_path = temp_install_dir / "venv"

    # Create virtual environment
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_path)],
        check=True,
        capture_output=True
    )

    # Determine executable paths (platform-specific)
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"

    yield {
        "python": str(python_exe),
        "pip": str(pip_exe),
        "venv_path": str(venv_path)
    }


@pytest.fixture
def install_package(isolated_python_env: dict, package_root: Path):
    """
    Factory fixture for installing packages in isolated environment.

    Usage:
        install_package("netrun-auth")
    """
    def _install(package_name: str, editable: bool = True) -> subprocess.CompletedProcess:
        """Install a package in the isolated environment."""
        package_path = package_root / package_name

        if not package_path.exists():
            raise ValueError(f"Package not found: {package_name}")

        pip_cmd = [isolated_python_env["pip"], "install"]
        if editable:
            pip_cmd.append("-e")
        pip_cmd.append(str(package_path))

        return subprocess.run(
            pip_cmd,
            check=True,
            capture_output=True,
            text=True
        )

    return _install


@pytest.fixture
def import_in_subprocess(isolated_python_env: dict):
    """
    Factory fixture for testing imports in a subprocess.

    Usage:
        result = import_in_subprocess("import netrun.auth")
    """
    def _import(import_statement: str) -> subprocess.CompletedProcess:
        """Execute an import statement in the isolated environment."""
        return subprocess.run(
            [isolated_python_env["python"], "-c", import_statement],
            capture_output=True,
            text=True
        )

    return _import


@pytest.fixture
def check_module_exists():
    """
    Fixture to check if a module exists without importing it.

    Usage:
        exists = check_module_exists("netrun.auth")
    """
    def _check(module_name: str) -> bool:
        """Check if a module exists in the current environment."""
        spec = importlib.util.find_spec(module_name)
        return spec is not None

    return _check


@pytest.fixture
def reload_module():
    """
    Fixture to reload a module (useful for testing dynamic imports).

    Usage:
        reload_module("netrun.auth")
    """
    def _reload(module_name: str):
        """Reload a module if it's already imported."""
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)

    return _reload


@pytest.fixture
def package_metadata():
    """
    Fixture to get package metadata.

    Usage:
        metadata = package_metadata("netrun-auth")
    """
    def _get_metadata(package_name: str) -> dict:
        """Get package metadata from pyproject.toml."""
        import tomllib  # Python 3.11+

        package_root = Path(__file__).parent.parent.resolve()
        pyproject_path = package_root / package_name / "pyproject.toml"

        if not pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found for {package_name}")

        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)

    return _get_metadata


@pytest.fixture
def python_version():
    """Current Python version as tuple."""
    return sys.version_info[:2]


@pytest.fixture(params=["3.10", "3.11", "3.12"])
def supported_python_versions(request):
    """Parametrized fixture for testing across Python versions."""
    return request.param


@pytest.fixture
def mock_namespace_package(temp_install_dir: Path):
    """
    Create a mock namespace package structure for testing.

    Usage:
        namespace_dir = mock_namespace_package("netrun", ["auth", "config"])
    """
    def _create_namespace(namespace: str, subpackages: List[str]) -> Path:
        """Create mock namespace package structure."""
        namespace_dir = temp_install_dir / namespace
        namespace_dir.mkdir(parents=True)

        # Create __init__.py for namespace (PEP 420 or pkgutil style)
        init_file = namespace_dir / "__init__.py"
        init_file.write_text(
            "# Namespace package\n"
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n"
        )

        # Create subpackages
        for subpkg in subpackages:
            subpkg_dir = namespace_dir / subpkg
            subpkg_dir.mkdir()
            subpkg_init = subpkg_dir / "__init__.py"
            subpkg_init.write_text(f'"""Mock {namespace}.{subpkg} package."""\n')

        return namespace_dir

    return _create_namespace


@pytest.fixture(autouse=True)
def reset_import_state():
    """
    Reset import state before and after each test.

    This ensures that tests don't interfere with each other through
    cached module imports.
    """
    # Record initial module state
    initial_modules = set(sys.modules.keys())

    yield

    # Clean up any netrun modules imported during test
    netrun_modules = [
        name for name in sys.modules.keys()
        if name.startswith("netrun")
    ]
    for module_name in netrun_modules:
        if module_name not in initial_modules:
            del sys.modules[module_name]


# Markers for categorizing tests
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "namespace: Tests specific to namespace package functionality"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring multiple packages"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take significant time to run"
    )
    config.addinivalue_line(
        "markers", "requires_install: Tests that require package installation"
    )
    config.addinivalue_line(
        "markers", "backwards_compat: Backwards compatibility tests"
    )
