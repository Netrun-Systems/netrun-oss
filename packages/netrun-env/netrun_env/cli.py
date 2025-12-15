"""
Click-based CLI interface for netrun-env tool.

Provides commands:
- validate: Validate .env against schema
- generate-schema: Generate schema from .env.example
- diff: Compare two environment files
"""

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .validator import EnvValidator
from .schema import SchemaGenerator
from .diff import EnvDiff
from .security import SecurityLevel

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


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx):
    """
    Netrun Environment Validator - Schema-based .env validation tool.

    Provides comprehensive validation, security checks, and comparison
    for environment variable files across all environments.
    """
    ctx.ensure_object(dict)


@main.command()
@click.option(
    '--env',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to .env file to validate'
)
@click.option(
    '--schema',
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help='Path to .env.schema.json file (optional)'
)
@click.option(
    '--security-level',
    type=click.Choice(['development', 'staging', 'production'], case_sensitive=False),
    default='production',
    help='Security level to enforce (default: production)'
)
@click.option(
    '--strict',
    is_flag=True,
    help='Treat warnings as errors'
)
def validate(
    env: Path,
    schema: Optional[Path],
    security_level: str,
    strict: bool
):
    """
    Validate environment file against schema and security rules.

    Examples:

      netrun-env validate --env .env --schema .env.schema.json

      netrun-env validate --env .env.production --security-level production --strict
    """
    click.echo(f"Validating: {env}")
    _log("info", f"CLI validate command started", env_file=str(env), schema_file=str(schema) if schema else None, security_level=security_level)

    # Parse security level
    sec_level = SecurityLevel[security_level.upper()]

    # Create validator
    validator = EnvValidator(security_level=sec_level)

    # Validate
    result = validator.validate_file(env, schema)

    # Output results
    click.echo(str(result))
    _log("info", f"CLI validate command complete", is_valid=result.is_valid)

    # Exit code
    if not result.is_valid:
        sys.exit(1)
    elif strict and result.warnings:
        click.echo("\nX Strict mode: warnings treated as errors", err=True)
        sys.exit(1)

    sys.exit(0)


@main.command()
@click.option(
    '--from',
    'from_file',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to .env.example file'
)
@click.option(
    '--out',
    type=click.Path(path_type=Path),
    required=True,
    help='Path to output .env.schema.json file'
)
@click.option(
    '--overwrite',
    is_flag=True,
    help='Overwrite existing schema file'
)
def generate_schema(from_file: Path, out: Path, overwrite: bool):
    """
    Generate JSON schema from .env.example file.

    Examples:

      netrun-env generate-schema --from .env.example --out .env.schema.json

      netrun-env generate-schema --from .env.example --out schema.json --overwrite
    """
    click.echo(f"Generating schema from: {from_file}")

    # Check if output exists
    if out.exists() and not overwrite:
        click.echo(f"Error: Output file '{out}' already exists. Use --overwrite to replace.", err=True)
        sys.exit(1)

    # Generate schema
    generator = SchemaGenerator()
    schema = generator.generate_schema(from_file)

    # Save schema
    generator.save_schema(schema, out)

    click.echo(f"[OK] Schema generated: {out}")
    click.echo(f"  Variables: {len(schema['variables'])}")

    sys.exit(0)


@main.command()
@click.option(
    '--env1',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to first .env file (baseline)'
)
@click.option(
    '--env2',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to second .env file (target)'
)
@click.option(
    '--format',
    type=click.Choice(['text', 'json'], case_sensitive=False),
    default='text',
    help='Output format (default: text)'
)
@click.option(
    '--no-mask',
    is_flag=True,
    help='Do not mask secret values in output'
)
@click.option(
    '--fail-on-diff',
    is_flag=True,
    help='Exit with error code if differences found'
)
def diff(
    env1: Path,
    env2: Path,
    format: str,
    no_mask: bool,
    fail_on_diff: bool
):
    """
    Compare two environment files.

    Examples:

      netrun-env diff --env1 .env.staging --env2 .env.production

      netrun-env diff --env1 .env.example --env2 .env --format json --no-mask
    """
    # Create diff tool
    differ = EnvDiff(mask_secrets=not no_mask)

    # Generate report
    report = differ.generate_report(env1, env2, output_format=format)

    # Output report
    click.echo(report)

    # Check for differences (if fail-on-diff enabled)
    if fail_on_diff:
        diff_result = differ.compare_files(env1, env2)
        if diff_result.has_differences():
            sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
