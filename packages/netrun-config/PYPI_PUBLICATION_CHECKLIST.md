# PyPI Publication Checklist for netrun-config

This checklist guides you through publishing `netrun-config` to PyPI (Python Package Index).

## Pre-Publication Checklist

### 1. Code Quality Validation

- [ ] All tests passing: `pytest --cov=netrun_config`
- [ ] Code formatted: `black netrun_config/ tests/`
- [ ] Linting clean: `ruff check netrun_config/ tests/`
- [ ] Type checking: `mypy netrun_config/`
- [ ] Security scan: `bandit -r netrun_config/`

**Commands:**
```bash
cd Service_63_Unified_Configuration
pytest --cov=netrun_config --cov-report=term-missing
black --check netrun_config/ tests/
ruff check netrun_config/ tests/
mypy netrun_config/
```

---

### 2. Documentation Validation

- [ ] README.md is complete and accurate
- [ ] CHANGELOG.md updated with release notes
- [ ] LICENSE file present (MIT)
- [ ] All examples tested and working
- [ ] API documentation complete

**Verify:**
```bash
ls -la README.md LICENSE CHANGELOG.md
python examples/basic_usage.py
python examples/keyvault_integration.py
```

---

### 3. Version Management

- [ ] Version updated in `pyproject.toml`
- [ ] Version matches in `netrun_config/__init__.py`
- [ ] CHANGELOG.md reflects current version
- [ ] Git tag created matching version

**Update Version:**
```toml
# pyproject.toml
[project]
version = "1.0.0"  # Update this
```

```python
# netrun_config/__init__.py
__version__ = "1.0.0"  # Update this
```

**Create Git Tag:**
```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

---

### 4. Package Build Validation

- [ ] Build tools installed: `pip install --upgrade build twine`
- [ ] Package builds successfully: `python -m build`
- [ ] Distribution files created (`.whl` and `.tar.gz`)
- [ ] Twine check passes: `twine check dist/*`

**Commands:**
```bash
# Install build tools
python -m pip install --upgrade build twine

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build package
python -m build

# Verify distributions
ls -lh dist/
twine check dist/*
```

**Expected Output:**
```
dist/
├── netrun_config-1.0.0-py3-none-any.whl
└── netrun_config-1.0.0.tar.gz
```

---

### 5. Installation Testing

- [ ] Install from wheel: `pip install dist/*.whl`
- [ ] Core imports work: `from netrun_config import BaseConfig, get_settings`
- [ ] Functional tests pass: `python test_install.py`
- [ ] Azure extras install: `pip install dist/*.whl[azure]`

**Commands:**
```bash
# Test in clean virtual environment
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# Install from wheel
pip install dist/netrun_config-1.0.0-py3-none-any.whl

# Test imports
python -c "from netrun_config import BaseConfig, get_settings, Field"
python -c "from netrun_config import ConfigError, ValidationError, KeyVaultError"
python -c "import netrun_config; print(f'Version: {netrun_config.__version__}')"

# Run functional tests
python test_install.py

# Test Azure extras
pip install dist/netrun_config-1.0.0-py3-none-any.whl[azure]
python -c "from netrun_config import KeyVaultMixin"

# Clean up
deactivate
rm -rf test_env
```

---

## PyPI Account Setup

### 6. PyPI Account Configuration

- [ ] PyPI account created: https://pypi.org/account/register/
- [ ] Test PyPI account created: https://test.pypi.org/account/register/
- [ ] Email verified on both accounts
- [ ] Two-factor authentication enabled (recommended)

---

### 7. API Token Generation

**Production PyPI:**
1. Login to https://pypi.org
2. Go to Account Settings → API Tokens
3. Click "Add API token"
4. Token name: `netrun-config-publisher`
5. Scope: "Project: netrun-config" (or "Entire account" for first publish)
6. Copy token (starts with `pypi-`)
7. Store securely in password manager

**Test PyPI:**
1. Login to https://test.pypi.org
2. Repeat steps above for Test PyPI
3. Token will start with `pypi-`

**Store Tokens as GitHub Secrets:**
```bash
# In GitHub repository settings → Secrets and variables → Actions
PYPI_API_TOKEN=pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TEST_PYPI_API_TOKEN=pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Publication Process

### 8. Publish to Test PyPI (Recommended First)

- [ ] Test PyPI API token configured
- [ ] Package uploaded to Test PyPI
- [ ] Test installation from Test PyPI
- [ ] Verify package page: https://test.pypi.org/project/netrun-config/

**Commands:**
```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*

# You'll be prompted for:
# Username: __token__
# Password: pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (Test PyPI token)

# Verify Test PyPI publication
pip index versions netrun-config --index-url https://test.pypi.org/simple/

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ netrun-config

# Test functionality
python -c "from netrun_config import BaseConfig, get_settings; print('Test PyPI installation successful')"
```

---

### 9. Publish to Production PyPI

- [ ] All tests passed on Test PyPI
- [ ] Production PyPI API token configured
- [ ] Final version check (no going back!)
- [ ] Package uploaded to PyPI
- [ ] Installation verified from PyPI

**Commands:**
```bash
# Upload to Production PyPI
twine upload dist/*

# You'll be prompted for:
# Username: __token__
# Password: pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (Production PyPI token)

# Verify PyPI publication
pip index versions netrun-config

# Test installation from PyPI
pip install netrun-config

# Test functionality
python -c "from netrun_config import BaseConfig, get_settings; print('PyPI installation successful')"
```

---

### 10. Automated Publication via GitHub Actions

**Manual Workflow Dispatch (Test PyPI):**
```bash
# In GitHub repository:
# Actions → "Publish netrun-config to PyPI" → Run workflow
# Select: "test" for Test PyPI
```

**Create GitHub Release (Production PyPI):**
```bash
# Create release on GitHub (triggers automatic publication)
gh release create v1.0.0 \
  --title "netrun-config v1.0.0" \
  --notes "See CHANGELOG.md for details" \
  dist/*

# Or via GitHub web interface:
# Releases → Draft a new release → Create tag: v1.0.0
```

**GitHub Actions will automatically:**
1. Validate version matches tag
2. Run full test suite
3. Build distributions
4. Test installation on Python 3.10, 3.11, 3.12
5. Upload to PyPI
6. Attach distributions to GitHub release

---

## Post-Publication Validation

### 11. Verify Publication

- [ ] Package visible on PyPI: https://pypi.org/project/netrun-config/
- [ ] Documentation renders correctly
- [ ] Download statistics tracking
- [ ] GitHub repository link works

**PyPI Package Page Checklist:**
- Project description displays correctly
- License shows as MIT
- Python version classifiers correct (3.10+)
- Homepage/repository links functional
- Installation command visible
- Dependencies listed correctly

---

### 12. Test Installation Across Environments

**Test on multiple Python versions:**
```bash
# Python 3.10
pyenv install 3.10.11
pyenv local 3.10.11
python -m venv venv310
source venv310/bin/activate
pip install netrun-config
python test_install.py
deactivate

# Python 3.11
pyenv install 3.11.4
pyenv local 3.11.4
python -m venv venv311
source venv311/bin/activate
pip install netrun-config
python test_install.py
deactivate

# Python 3.12
pyenv install 3.12.0
pyenv local 3.12.0
python -m venv venv312
source venv312/bin/activate
pip install netrun-config
python test_install.py
deactivate
```

**Test on multiple operating systems:**
- [ ] Linux (Ubuntu 20.04+)
- [ ] macOS (11.0+)
- [ ] Windows (10/11, Server 2019+)

---

### 13. Update Portfolio Projects

- [ ] Update dependencies in consuming projects
- [ ] Replace custom config implementations
- [ ] Update documentation references
- [ ] Run integration tests

**Example Migration:**
```bash
# In consuming project
pip uninstall custom-config
pip install netrun-config

# Update imports
# Old: from config.settings import get_settings
# New: from netrun_config import get_settings
```

---

### 14. Announcement & Documentation

- [ ] Update README badges (PyPI version, downloads)
- [ ] Announce on internal team channels
- [ ] Update Netrun Systems service documentation
- [ ] Create knowledge base article

**Add PyPI Badge to README:**
```markdown
[![PyPI version](https://badge.fury.io/py/netrun-config.svg)](https://badge.fury.io/py/netrun-config)
[![Downloads](https://pepy.tech/badge/netrun-config)](https://pepy.tech/project/netrun-config)
```

---

## Troubleshooting

### Common Issues

**Issue: "Package already exists"**
- **Cause:** Version already published
- **Solution:** Increment version in `pyproject.toml` and `__init__.py`, rebuild

**Issue: "Invalid distribution filename"**
- **Cause:** Incorrect package metadata
- **Solution:** Verify `pyproject.toml` format, rebuild package

**Issue: "twine check failed"**
- **Cause:** README rendering issues (typically RST/Markdown formatting)
- **Solution:** Validate README.md syntax, ensure proper headers

**Issue: "Authentication failed"**
- **Cause:** Incorrect API token
- **Solution:**
  - Username must be `__token__` (exactly)
  - Password is full API token starting with `pypi-`

**Issue: "Import failed after installation"**
- **Cause:** Package structure issues
- **Solution:** Verify `__init__.py` exists, check `pyproject.toml` package discovery

---

## Rollback Procedure

**PyPI does NOT support deleting versions.** If a bad version is published:

1. **Yank the release** (makes it unavailable for new installs):
   ```bash
   # Via PyPI web interface: Manage → Options → Yank release
   # Or via twine (requires admin access)
   ```

2. **Publish corrected version**:
   ```bash
   # Increment version (e.g., 1.0.0 → 1.0.1)
   # Fix issues
   # Rebuild and republish
   ```

3. **Communicate to users**:
   - Update CHANGELOG.md with known issues
   - Post notice on GitHub releases
   - Update documentation

---

## Security Best Practices

- [ ] API tokens stored securely (never in code/git)
- [ ] GitHub Secrets configured for CI/CD
- [ ] Two-factor authentication enabled on PyPI
- [ ] Regular token rotation (every 6 months)
- [ ] Audit package permissions periodically

**Token Storage:**
- Use password manager (1Password, Bitwarden, LastPass)
- Never commit tokens to git
- Use environment variables for local testing
- Rotate tokens if exposed

---

## Success Criteria

Publication is successful when:

1. Package installs via `pip install netrun-config`
2. All imports work without errors
3. Functional tests pass on all supported Python versions
4. Documentation renders correctly on PyPI
5. Download statistics tracking active
6. GitHub repository integrations functional

---

## Next Steps After Publication

1. **Monitor PyPI Download Statistics**: https://pypistats.org/packages/netrun-config
2. **Watch for GitHub Issues**: https://github.com/netrunsystems/netrun-config/issues
3. **Plan Next Release**: Add items to CHANGELOG.md under "Unreleased" section
4. **Iterate Based on Feedback**: Gather user feedback from consuming projects

---

## Reference Links

**PyPI Resources:**
- Production PyPI: https://pypi.org
- Test PyPI: https://test.pypi.org
- Packaging Guide: https://packaging.python.org/
- Twine Documentation: https://twine.readthedocs.io/

**Netrun Systems Resources:**
- GitHub Repository: https://github.com/netrunsystems/netrun-config
- Documentation: https://github.com/netrunsystems/netrun-config#readme
- Issue Tracker: https://github.com/netrunsystems/netrun-config/issues

**Tools:**
- PyPI Statistics: https://pypistats.org/
- Badge Generator: https://shields.io/
- Semantic Versioning: https://semver.org/

---

## Checklist Summary

**Pre-Publication:**
- ✅ Tests passing
- ✅ Documentation complete
- ✅ Version updated
- ✅ Package builds successfully
- ✅ Installation tested

**Publication:**
- ✅ Test PyPI upload
- ✅ Production PyPI upload
- ✅ GitHub release created

**Post-Publication:**
- ✅ Package verified on PyPI
- ✅ Installation tested across environments
- ✅ Documentation updated
- ✅ Announcement made

---

**Last Updated:** 2025-11-24
**Maintainer:** Daniel Garza (daniel@netrunsystems.com)
**Package:** netrun-config v1.0.0
