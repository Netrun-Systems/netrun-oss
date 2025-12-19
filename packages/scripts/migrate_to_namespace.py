#!/usr/bin/env python3
"""
Namespace Migration Script for Netrun Service Library v2

Automates the conversion of existing packages from flat structure (netrun_*)
to namespace structure (netrun.*) with backwards compatibility shims.

Usage:
    # Dry run (preview changes)
    python migrate_to_namespace.py --dry-run

    # Migrate all packages
    python migrate_to_namespace.py

    # Migrate specific package
    python migrate_to_namespace.py --package netrun-errors

    # Skip compatibility shims
    python migrate_to_namespace.py --skip-shim

Author: Netrun Systems
Version: 1.0.0
License: MIT
"""

import argparse
import logging
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Raised when migration encounters an error."""
    pass


class PackageMigrator:
    """Handles migration of a single package to namespace structure."""

    def __init__(
        self,
        package_dir: Path,
        dry_run: bool = False,
        skip_shim: bool = False,
    ):
        """
        Initialize the package migrator.

        Args:
            package_dir: Path to the package directory
            dry_run: If True, preview changes without writing
            skip_shim: If True, skip compatibility shim creation
        """
        self.package_dir = package_dir
        self.dry_run = dry_run
        self.skip_shim = skip_shim
        self.backup_dir: Optional[Path] = None
        self.changes: List[str] = []
        self.errors: List[str] = []

        # Extract package name from directory
        self.package_name = package_dir.name
        if not self.package_name.startswith("netrun-"):
            raise MigrationError(f"Package {self.package_name} is not a netrun package")

        # Derive subpackage name (e.g., "netrun-errors" -> "errors")
        self.subpackage_name = self.package_name.replace("netrun-", "")
        self.old_module_name = f"netrun_{self.subpackage_name.replace('-', '_')}"
        self.new_module_path = f"netrun/{self.subpackage_name.replace('-', '_')}"

        logger.info(f"Initialized migrator for {self.package_name}")
        logger.info(f"  Old module: {self.old_module_name}")
        logger.info(f"  New module: {self.new_module_path}")

    def create_backup(self) -> None:
        """Create a timestamped backup of the package directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.package_name}.backup.{timestamp}"
        self.backup_dir = self.package_dir.parent / backup_name

        if not self.dry_run:
            shutil.copytree(self.package_dir, self.backup_dir)
            logger.info(f"Created backup: {self.backup_dir}")
            self.changes.append(f"Backup created: {self.backup_dir}")
        else:
            logger.info(f"[DRY RUN] Would create backup: {self.backup_dir}")

    def find_source_directory(self) -> Optional[Path]:
        """
        Find the existing source directory.

        Returns:
            Path to source directory or None if not found
        """
        old_src_dir = self.package_dir / self.old_module_name
        if old_src_dir.exists() and old_src_dir.is_dir():
            return old_src_dir

        logger.warning(f"Source directory not found: {old_src_dir}")
        return None

    def create_namespace_structure(self, old_src_dir: Path) -> Path:
        """
        Create the new namespace directory structure.

        Args:
            old_src_dir: Path to existing source directory

        Returns:
            Path to new namespace directory
        """
        # Create netrun/ directory
        netrun_dir = self.package_dir / "netrun"

        # Create subpackage directory
        new_src_dir = self.package_dir / self.new_module_path.replace("/", Path().__class__.__module__.split('.')[0])
        # Convert to proper path
        parts = self.new_module_path.split("/")
        new_src_dir = self.package_dir / parts[0] / parts[1]

        if not self.dry_run:
            netrun_dir.mkdir(exist_ok=True)
            new_src_dir.parent.mkdir(parents=True, exist_ok=True)

            # Create __init__.py for namespace package
            namespace_init = netrun_dir / "__init__.py"
            if not namespace_init.exists():
                namespace_init.write_text(
                    '"""Netrun namespace package."""\n'
                    '__path__ = __import__("pkgutil").extend_path(__path__, __name__)\n'
                )
                self.changes.append(f"Created namespace __init__.py: {namespace_init}")

            logger.info(f"Created namespace structure: {new_src_dir}")
            self.changes.append(f"Created directory: {new_src_dir}")
        else:
            logger.info(f"[DRY RUN] Would create: {new_src_dir}")

        return new_src_dir

    def move_source_files(self, old_src_dir: Path, new_src_dir: Path) -> None:
        """
        Move source files from old to new directory structure.

        Args:
            old_src_dir: Path to existing source directory
            new_src_dir: Path to new namespace directory
        """
        if not self.dry_run:
            # Move all files
            for item in old_src_dir.iterdir():
                dest = new_src_dir / item.name
                shutil.move(str(item), str(dest))
                self.changes.append(f"Moved: {item.name} -> {dest}")

            # Remove old directory
            old_src_dir.rmdir()
            logger.info(f"Moved source files from {old_src_dir} to {new_src_dir}")
        else:
            file_count = len(list(old_src_dir.iterdir()))
            logger.info(f"[DRY RUN] Would move {file_count} files to {new_src_dir}")

    def update_imports_in_file(self, file_path: Path) -> int:
        """
        Update import statements in a single file.

        Args:
            file_path: Path to Python file

        Returns:
            Number of imports updated
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            original_content = content
            updates = 0

            # Pattern 1: from netrun_xxx import ...
            pattern1 = re.compile(
                rf'\bfrom\s+{re.escape(self.old_module_name)}(\.[a-zA-Z0-9_]+)*\s+import\b'
            )

            def replace_from_import(match):
                nonlocal updates
                full_match = match.group(0)
                submodule = match.group(1) or ""
                new_import = f"from netrun.{self.subpackage_name.replace('-', '_')}{submodule} import"
                updates += 1
                return new_import

            content = pattern1.sub(replace_from_import, content)

            # Pattern 2: import netrun_xxx
            pattern2 = re.compile(
                rf'\bimport\s+{re.escape(self.old_module_name)}(\.[a-zA-Z0-9_]+)*\b'
            )

            def replace_import(match):
                nonlocal updates
                submodule = match.group(1) or ""
                new_import = f"import netrun.{self.subpackage_name.replace('-', '_')}{submodule}"
                updates += 1
                return new_import

            content = pattern2.sub(replace_import, content)

            # Write updated content
            if content != original_content:
                if not self.dry_run:
                    file_path.write_text(content, encoding="utf-8")
                    self.changes.append(f"Updated imports in {file_path.name}: {updates} changes")
                else:
                    logger.info(f"[DRY RUN] Would update {updates} imports in {file_path.name}")

            return updates

        except Exception as e:
            error_msg = f"Error updating imports in {file_path}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return 0

    def update_all_imports(self, source_dir: Path) -> int:
        """
        Update imports in all Python files.

        Args:
            source_dir: Path to source directory

        Returns:
            Total number of imports updated
        """
        total_updates = 0
        python_files = list(source_dir.rglob("*.py"))

        logger.info(f"Updating imports in {len(python_files)} Python files...")

        for py_file in python_files:
            updates = self.update_imports_in_file(py_file)
            total_updates += updates

        return total_updates

    def update_pyproject_toml(self) -> None:
        """Update pyproject.toml with new package structure and dependencies."""
        pyproject_path = self.package_dir / "pyproject.toml"

        if not pyproject_path.exists():
            logger.warning(f"pyproject.toml not found: {pyproject_path}")
            return

        try:
            content = pyproject_path.read_text(encoding="utf-8")
            original_content = content
            changes = []

            # Update packages declaration
            packages_pattern = re.compile(
                rf'packages\s*=\s*\["{re.escape(self.old_module_name)}"\]'
            )
            if packages_pattern.search(content):
                content = packages_pattern.sub(
                    f'packages = ["{self.new_module_path}"]',
                    content
                )
                changes.append("Updated packages declaration")

            # Update version to 2.0.0 (major breaking change)
            version_pattern = re.compile(r'version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"')
            if version_pattern.search(content):
                content = version_pattern.sub('version = "2.0.0"', content)
                changes.append("Bumped version to 2.0.0")

            # Add netrun-core dependency if not present
            if "netrun-core" not in content:
                # Find dependencies section
                deps_pattern = re.compile(
                    r'(dependencies\s*=\s*\[)(.*?)(\])',
                    re.DOTALL
                )
                match = deps_pattern.search(content)
                if match:
                    deps_content = match.group(2)
                    # Add netrun-core as first dependency
                    new_deps = f'\n    "netrun-core>=1.0.0",{deps_content}'
                    content = deps_pattern.sub(
                        rf'\g<1>{new_deps}\g<3>',
                        content
                    )
                    changes.append("Added netrun-core>=1.0.0 dependency")

            # Update test coverage paths
            content = content.replace(
                f'--cov={self.old_module_name}',
                f'--cov={self.new_module_path.replace("/", ".")}'
            )
            content = content.replace(
                f'source = ["{self.old_module_name}"]',
                f'source = ["{self.new_module_path.replace("/", ".")}"]'
            )

            if content != original_content:
                if not self.dry_run:
                    pyproject_path.write_text(content, encoding="utf-8")
                    logger.info(f"Updated pyproject.toml: {', '.join(changes)}")
                    self.changes.extend([f"pyproject.toml: {c}" for c in changes])
                else:
                    logger.info(f"[DRY RUN] Would update pyproject.toml: {', '.join(changes)}")

        except Exception as e:
            error_msg = f"Error updating pyproject.toml: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)

    def create_compatibility_shim(self) -> None:
        """Create backwards compatibility shim for old import path."""
        if self.skip_shim:
            logger.info("Skipping compatibility shim creation (--skip-shim)")
            return

        shim_dir = self.package_dir / self.old_module_name
        shim_init = shim_dir / "__init__.py"

        shim_content = f'''"""
Backwards compatibility shim for {self.old_module_name}.

DEPRECATED: This import path is deprecated. Use 'from netrun.{self.subpackage_name.replace('-', '_')}' instead.
This compatibility layer will be removed in version 3.0.0.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    f"Importing from '{self.old_module_name}' is deprecated. "
    f"Use 'from netrun.{self.subpackage_name.replace('-', '_')}' instead. "
    "This compatibility layer will be removed in version 3.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from new location
from netrun.{self.subpackage_name.replace('-', '_')} import *  # noqa: F401, F403

# Preserve __all__ if it exists
try:
    from netrun.{self.subpackage_name.replace('-', '_')} import __all__
except ImportError:
    pass
'''

        if not self.dry_run:
            shim_dir.mkdir(exist_ok=True)
            shim_init.write_text(shim_content)
            logger.info(f"Created compatibility shim: {shim_init}")
            self.changes.append(f"Created shim: {shim_init}")
        else:
            logger.info(f"[DRY RUN] Would create compatibility shim: {shim_init}")

    def validate_migration(self, new_src_dir: Path) -> bool:
        """
        Validate that migration was successful.

        Args:
            new_src_dir: Path to new source directory

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating migration...")
        validation_errors = []

        # Check that new directory exists and has files
        if not new_src_dir.exists():
            validation_errors.append(f"New source directory not found: {new_src_dir}")
        else:
            python_files = list(new_src_dir.rglob("*.py"))
            if not python_files:
                validation_errors.append(f"No Python files found in {new_src_dir}")
            else:
                logger.info(f"✓ Found {len(python_files)} Python files in new location")

        # Check that old directory is gone
        old_src_dir = self.package_dir / self.old_module_name
        if old_src_dir.exists() and not self.skip_shim:
            # Should only exist as shim
            if not (old_src_dir / "__init__.py").exists():
                validation_errors.append(f"Old directory still exists: {old_src_dir}")

        # Validate Python syntax in migrated files
        if new_src_dir.exists():
            for py_file in new_src_dir.rglob("*.py"):
                try:
                    compile(py_file.read_text(encoding="utf-8"), str(py_file), "exec")
                except SyntaxError as e:
                    validation_errors.append(f"Syntax error in {py_file}: {e}")

        # Check pyproject.toml was updated
        pyproject = self.package_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            if self.old_module_name in content and self.new_module_path not in content:
                validation_errors.append("pyproject.toml still references old module name")
            else:
                logger.info("✓ pyproject.toml updated correctly")

        if validation_errors:
            logger.error("Validation failed:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            self.errors.extend(validation_errors)
            return False

        logger.info("✓ Validation passed")
        return True

    def migrate(self) -> bool:
        """
        Execute the full migration process.

        Returns:
            True if migration successful, False otherwise
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Starting migration: {self.package_name}")
            logger.info(f"{'='*60}\n")

            # Step 1: Create backup
            self.create_backup()

            # Step 2: Find source directory
            old_src_dir = self.find_source_directory()
            if not old_src_dir:
                raise MigrationError(f"Source directory not found for {self.package_name}")

            # Step 3: Create namespace structure
            new_src_dir = self.create_namespace_structure(old_src_dir)

            # Step 4: Move source files
            self.move_source_files(old_src_dir, new_src_dir)

            # Step 5: Update imports
            total_imports = self.update_all_imports(new_src_dir)
            logger.info(f"Updated {total_imports} import statements")

            # Step 6: Update pyproject.toml
            self.update_pyproject_toml()

            # Step 7: Create compatibility shim
            self.create_compatibility_shim()

            # Step 8: Validate migration
            if not self.dry_run:
                if not self.validate_migration(new_src_dir):
                    raise MigrationError("Validation failed")

            logger.info(f"\n{'='*60}")
            logger.info(f"Migration completed: {self.package_name}")
            logger.info(f"{'='*60}\n")

            return True

        except Exception as e:
            error_msg = f"Migration failed for {self.package_name}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False

    def rollback(self) -> bool:
        """
        Rollback migration using backup.

        Returns:
            True if rollback successful, False otherwise
        """
        if not self.backup_dir or not self.backup_dir.exists():
            logger.error("No backup found for rollback")
            return False

        try:
            logger.warning(f"Rolling back {self.package_name}...")

            # Remove current directory
            shutil.rmtree(self.package_dir)

            # Restore from backup
            shutil.copytree(self.backup_dir, self.package_dir)

            logger.info(f"Rollback completed: {self.package_name}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def print_summary(self) -> None:
        """Print migration summary."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Migration Summary: {self.package_name}")
        logger.info(f"{'='*60}")
        logger.info(f"Changes made: {len(self.changes)}")
        for change in self.changes[:10]:  # Show first 10
            logger.info(f"  - {change}")
        if len(self.changes) > 10:
            logger.info(f"  ... and {len(self.changes) - 10} more")

        if self.errors:
            logger.error(f"\nErrors encountered: {len(self.errors)}")
            for error in self.errors:
                logger.error(f"  - {error}")

        logger.info(f"\n{'='*60}\n")


def discover_packages(packages_dir: Path) -> List[Path]:
    """
    Discover all netrun-* packages in the packages directory.

    Args:
        packages_dir: Path to packages directory

    Returns:
        List of package directory paths
    """
    packages = []

    for item in packages_dir.iterdir():
        if item.is_dir() and item.name.startswith("netrun-"):
            # Skip if already migrated (check for netrun/ subdirectory)
            netrun_subdir = item / "netrun"
            if netrun_subdir.exists():
                logger.info(f"Skipping {item.name} (already migrated)")
                continue

            packages.append(item)

    return sorted(packages)


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate Netrun packages to namespace structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview all changes without writing
  python migrate_to_namespace.py --dry-run

  # Migrate all packages
  python migrate_to_namespace.py

  # Migrate specific package
  python migrate_to_namespace.py --package netrun-errors

  # Migrate without compatibility shims
  python migrate_to_namespace.py --skip-shim

  # Migrate specific package with preview
  python migrate_to_namespace.py --package netrun-errors --dry-run
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )

    parser.add_argument(
        "--package",
        type=str,
        help="Migrate only the specified package (e.g., netrun-errors)",
    )

    parser.add_argument(
        "--skip-shim",
        action="store_true",
        help="Skip creation of backwards compatibility shims",
    )

    parser.add_argument(
        "--packages-dir",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Path to packages directory (default: ../)",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate packages directory
    if not args.packages_dir.exists():
        logger.error(f"Packages directory not found: {args.packages_dir}")
        sys.exit(1)

    logger.info(f"Netrun Namespace Migration Script v1.0.0")
    logger.info(f"Packages directory: {args.packages_dir.absolute()}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"Compatibility shims: {'DISABLED' if args.skip_shim else 'ENABLED'}\n")

    # Discover or select packages
    if args.package:
        package_dir = args.packages_dir / args.package
        if not package_dir.exists():
            logger.error(f"Package not found: {package_dir}")
            sys.exit(1)
        packages = [package_dir]
    else:
        packages = discover_packages(args.packages_dir)

    if not packages:
        logger.warning("No packages found to migrate")
        sys.exit(0)

    logger.info(f"Found {len(packages)} package(s) to migrate:")
    for pkg in packages:
        logger.info(f"  - {pkg.name}")
    logger.info("")

    # Execute migrations
    successful = []
    failed = []

    for package_dir in packages:
        try:
            migrator = PackageMigrator(
                package_dir=package_dir,
                dry_run=args.dry_run,
                skip_shim=args.skip_shim,
            )

            if migrator.migrate():
                successful.append(package_dir.name)
                migrator.print_summary()
            else:
                failed.append(package_dir.name)

        except Exception as e:
            logger.error(f"Fatal error migrating {package_dir.name}: {e}")
            failed.append(package_dir.name)

    # Print final summary
    logger.info(f"\n{'='*60}")
    logger.info("FINAL SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total packages: {len(packages)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")

    if successful:
        logger.info("\nSuccessful migrations:")
        for pkg in successful:
            logger.info(f"  ✓ {pkg}")

    if failed:
        logger.error("\nFailed migrations:")
        for pkg in failed:
            logger.error(f"  ✗ {pkg}")

    logger.info(f"\n{'='*60}\n")

    # Exit with appropriate code
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
