# Integration Templates

Templates for integrating netrun-logging into Netrun Systems portfolio projects.

## Quick Integration

1. Install package: `pip install netrun-logging`
2. Copy the template for your project
3. Modify configuration as needed
4. Replace existing logging setup

## Project Templates

| Project | Template | Framework | Special Features |
|---------|----------|-----------|-----------------|
| Intirkon | `intirkon.py` | FastAPI | Multi-tenant, Azure |
| Netrun CRM | `netrun_crm.py` | FastAPI | Lead scoring, email |
| Intirkast | `intirkast.py` | FastAPI | Content platform |
| Wilbur | `wilbur.py` | FastAPI | Charlotte bridge |
| SecureVault | `securevault.py` | FastAPI | Security audit |
| DungeonMaster | `dungeonmaster.py` | FastAPI | Game server |
| GhostGrid | `ghostgrid.py` | FastAPI | FSO network sim |
| Intirfix | `intirfix.py` | FastAPI | Service dispatch |
| Netrun Site | `netrun_site.py` | Next.js API | Marketing site |
| EISCORE | `eiscore.py` | Unreal/Python | Game engine |
| Service Library | `service_library.py` | Scripts | Documentation |

## Migration Guide

### Before (Standard logging)

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Message")
```

### After (netrun-logging)

```python
from netrun_logging import configure_logging, get_logger
configure_logging(app_name="my-app")
logger = get_logger(__name__)
logger.info("Message")  # Now outputs JSON with correlation ID support
```
