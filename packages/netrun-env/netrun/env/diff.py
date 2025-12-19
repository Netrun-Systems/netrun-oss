"""
Environment file comparison and diff functionality.

Provides detailed comparison of environment files to identify:
- Missing variables
- Added variables
- Changed values (with masking for secrets)
"""

from typing import Dict, Set, List, Tuple
from pathlib import Path
from dataclasses import dataclass
import re

from .schema import SchemaGenerator

# Optional netrun-logging integration
_use_netrun_logging = False
_logger = None

try:
    from netrun_logging import get_logger
    _logger = get_logger(__name__)
    _use_netrun_logging = True
except ImportError:
    import logging
    _logger = logging.getLogger(__name__)


def _log(level: str, message: str, **kwargs) -> None:
    """Log message using netrun-logging if available, otherwise standard logging."""
    if _use_netrun_logging:
        log_method = getattr(_logger, level, _logger.info)
        log_method(message, **kwargs)
    else:
        log_method = getattr(_logger, level, _logger.info)
        log_method(f"{message} {kwargs}" if kwargs else message)


@dataclass
class DiffResult:
    """Result of environment file comparison."""
    missing_in_target: Set[str]
    added_in_target: Set[str]
    changed_values: Dict[str, Tuple[str, str]]  # var_name -> (old_value, new_value)

    def has_differences(self) -> bool:
        """Check if any differences exist."""
        return bool(
            self.missing_in_target or
            self.added_in_target or
            self.changed_values
        )

    def __str__(self) -> str:
        """Format diff result as string."""
        if not self.has_differences():
            return "No differences found"

        lines = []

        if self.missing_in_target:
            lines.append(f"\nMissing in target ({len(self.missing_in_target)}):")
            for var in sorted(self.missing_in_target):
                lines.append(f"  - {var}")

        if self.added_in_target:
            lines.append(f"\nAdded in target ({len(self.added_in_target)}):")
            for var in sorted(self.added_in_target):
                lines.append(f"  + {var}")

        if self.changed_values:
            lines.append(f"\nChanged values ({len(self.changed_values)}):")
            for var in sorted(self.changed_values.keys()):
                old_val, new_val = self.changed_values[var]
                lines.append(f"  ~ {var}")
                lines.append(f"      - {old_val}")
                lines.append(f"      + {new_val}")

        return "\n".join(lines)


class EnvDiff:
    """Compares environment files and generates diffs."""

    # Secret detection pattern (reused from security.py)
    SECRET_PATTERN = re.compile(
        r'.*(secret|key|token|password|credential|api_key).*',
        re.IGNORECASE
    )

    def __init__(self, mask_secrets: bool = True):
        """
        Initialize environment diff tool.

        Args:
            mask_secrets: Whether to mask secret values in output
        """
        self.schema_generator = SchemaGenerator()
        self.mask_secrets = mask_secrets

    def mask_value(self, var_name: str, value: str) -> str:
        """
        Mask value if it's a secret.

        Args:
            var_name: Environment variable name
            value: Environment variable value

        Returns:
            Masked or original value
        """
        if not self.mask_secrets:
            return value

        if self.SECRET_PATTERN.match(var_name):
            if len(value) <= 4:
                return "***"
            return f"{value[:2]}...{value[-2:]}"

        return value

    def compare_files(self, file1: Path, file2: Path) -> DiffResult:
        """
        Compare two environment files.

        Args:
            file1: Path to first .env file (baseline)
            file2: Path to second .env file (target)

        Returns:
            DiffResult with comparison details
        """
        _log("info", f"Comparing environment files", file1=str(file1), file2=str(file2))
        # Parse both files
        vars1 = self.schema_generator.parse_env_file(file1)
        vars2 = self.schema_generator.parse_env_file(file2)
        _log("debug", f"Parsed files", vars1_count=len(vars1), vars2_count=len(vars2))

        result = self.compare_variables(vars1, vars2)
        _log("info", f"Comparison complete", has_differences=result.has_differences(),
             missing=len(result.missing_in_target), added=len(result.added_in_target),
             changed=len(result.changed_values))
        return result

    def compare_variables(
        self,
        vars1: Dict[str, str],
        vars2: Dict[str, str]
    ) -> DiffResult:
        """
        Compare two sets of variables.

        Args:
            vars1: First set of variables (baseline)
            vars2: Second set of variables (target)

        Returns:
            DiffResult with comparison details
        """
        keys1 = set(vars1.keys())
        keys2 = set(vars2.keys())

        # Find missing and added variables
        missing = keys1 - keys2
        added = keys2 - keys1

        # Find changed values
        common_keys = keys1 & keys2
        changed = {}

        for key in common_keys:
            if vars1[key] != vars2[key]:
                old_val = self.mask_value(key, vars1[key])
                new_val = self.mask_value(key, vars2[key])
                changed[key] = (old_val, new_val)

        return DiffResult(
            missing_in_target=missing,
            added_in_target=added,
            changed_values=changed
        )

    def generate_report(
        self,
        file1: Path,
        file2: Path,
        output_format: str = "text"
    ) -> str:
        """
        Generate detailed comparison report.

        Args:
            file1: Path to first .env file
            file2: Path to second .env file
            output_format: Output format ('text' or 'json')

        Returns:
            Formatted report string
        """
        diff = self.compare_files(file1, file2)

        if output_format == "json":
            import json
            return json.dumps({
                "file1": str(file1),
                "file2": str(file2),
                "missing_in_target": sorted(list(diff.missing_in_target)),
                "added_in_target": sorted(list(diff.added_in_target)),
                "changed_values": {
                    k: {"old": v[0], "new": v[1]}
                    for k, v in diff.changed_values.items()
                }
            }, indent=2)

        # Text format
        lines = [
            "Environment Comparison Report",
            "=" * 60,
            f"Baseline: {file1}",
            f"Target:   {file2}",
            "=" * 60,
        ]

        if not diff.has_differences():
            lines.append("\nNo differences found - environments are identical")
        else:
            lines.append(str(diff))

        return "\n".join(lines)
