# Namespace Migration Quick Reference

## One-Command Migrations

```bash
# Test first (always!)
python3 migrate_to_namespace.py --dry-run

# Migrate all packages
python3 migrate_to_namespace.py

# Migrate one package
python3 migrate_to_namespace.py --package netrun-errors
```

## Command Options

| Command | Description |
|---------|-------------|
| `--dry-run` | Preview without changes |
| `--package NAME` | Migrate specific package |
| `--skip-shim` | No compatibility shim |
| `-v` | Verbose logging |

## Pre-Migration Checklist

- [ ] Git commit current state
- [ ] Run tests (ensure they pass)
- [ ] Run dry run first
- [ ] Review dry run output

## Post-Migration Checklist

- [ ] Review migration summary
- [ ] Run tests: `cd netrun-{pkg} && python3 -m pytest`
- [ ] Build package: `python3 -m build`
- [ ] Test new imports: `python3 -c "from netrun.{pkg} import ..."`
- [ ] Update documentation
- [ ] Commit changes

## What Changes

### Directory Structure
```
BEFORE                      AFTER
netrun_errors/             netrun/
  __init__.py                __init__.py (namespace)
  base.py                    errors/
  auth.py                      __init__.py
  ...                          base.py
                               auth.py
                               ...
                             netrun_errors/  (shim)
                               __init__.py
```

### Imports
```python
# BEFORE
from netrun_errors import NetrunException
from netrun_errors.auth import InvalidCredentialsError

# AFTER
from netrun.errors import NetrunException
from netrun.errors.auth import InvalidCredentialsError
```

### pyproject.toml
```toml
# BEFORE
version = "1.1.0"
packages = ["netrun_errors"]

# AFTER
version = "2.0.0"
packages = ["netrun/errors"]
dependencies = ["netrun-core>=1.0.0", ...]
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Migration fails | Check logs, review errors, fix issues, retry |
| Tests fail | Update missed imports, check for dynamic imports |
| Syntax errors | Review import patterns, fix manually |
| Old imports fail | Check compatibility shim was created |

## Rollback

```bash
# Remove migrated package
rm -rf netrun-errors

# Restore from backup
mv netrun-errors.backup.20251218_143022 netrun-errors
```

## Migration Order

Recommended order (dependencies):

1. **No deps**: netrun-errors, netrun-logging
2. **Low deps**: netrun-config, netrun-env
3. **Medium deps**: netrun-auth, netrun-cors
4. **High deps**: netrun-rbac, netrun-oauth

## Support

- **Full Guide**: `README_MIGRATION.md`
- **Design Docs**: `../NAMESPACE_DESIGN.md`
- **Issues**: Create repo issue
- **Contact**: dev@netrunsystems.com

---

**Version**: 1.0.0 | **Updated**: 2025-12-18 | **Author**: Netrun Systems
