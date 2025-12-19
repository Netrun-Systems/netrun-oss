# netrun-core Installation Test Guide

## Quick Verification

### 1. Build the Package
```bash
cd /data/workspace/github/Netrun_Service_Library_v2/packages/netrun-core
python3 -m build --wheel
```

Expected output:
```
Successfully built netrun_core-1.0.0-py3-none-any.whl
```

### 2. Install Locally
```bash
pip install -e .
```

### 3. Test Import
```bash
python3 -c "import netrun; print('Version:', netrun.__version__)"
```

Expected output:
```
Version: 1.0.0
```

### 4. Verify Namespace Extension
```python
import netrun
print(f"Namespace path: {netrun.__path__}")
print(f"Author: {netrun.__author__}")
print(f"Email: {netrun.__email__}")
```

## Integration Test with Other Packages

After installing other netrun packages, verify namespace sharing:

```python
# Install additional packages
pip install netrun-auth netrun-config

# Test unified namespace
from netrun.auth import JWTAuthMiddleware
from netrun.config import Settings
from netrun.errors import NetrunError

print("All imports successful - namespace package working correctly!")
```

## Publishing to PyPI

### Test PyPI (recommended first)
```bash
python3 -m twine upload --repository testpypi dist/*
```

### Production PyPI
```bash
python3 -m twine upload dist/*
```

## Package Contents Verification

```bash
python3 -m zipfile -l dist/netrun_core-1.0.0-py3-none-any.whl
```

Expected files:
- `netrun/__init__.py` - Namespace initialization with version info
- `netrun/py.typed` - PEP 561 type hint marker
- `netrun_core-1.0.0.dist-info/METADATA` - Package metadata
- `netrun_core-1.0.0.dist-info/WHEEL` - Wheel metadata
- `netrun_core-1.0.0.dist-info/licenses/LICENSE` - MIT License

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'netrun'"
**Solution**: Ensure package is installed: `pip install -e .` or `pip install netrun-core`

### Issue: Version mismatch
**Solution**: Check `netrun.__version__` matches `pyproject.toml` version field

### Issue: Namespace not extending
**Solution**: Verify `__path__ = __import__('pkgutil').extend_path(__path__, __name__)` is in `__init__.py`

### Issue: Type hints not recognized
**Solution**: Ensure `py.typed` file exists in `netrun/` directory

## Requirements

- Python 3.10 or higher
- pip 21.0 or higher
- build package: `pip install build`
- twine (for publishing): `pip install twine`

## Next Steps

After verifying netrun-core works correctly:
1. Install other netrun packages to test namespace sharing
2. Run integration tests with dependent packages
3. Verify no conflicts with existing installations
4. Test in clean virtual environment

---

Created: December 18, 2025
Version: 1.0.0
