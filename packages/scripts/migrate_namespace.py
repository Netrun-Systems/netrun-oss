#!/usr/bin/env python3
"""
Automated namespace package migration script for Netrun packages.

This script migrates packages from netrun_* to netrun.* namespace structure.
"""
import shutil
import subprocess
from pathlib import Path
from typing import Dict

# Package mapping: old_name -> new_namespace
PACKAGE_MAPPING: Dict[str, str] = {
    "netrun-cors": "cors",
    "netrun-env": "env",
    "netrun-oauth": "oauth",
    "netrun-pytest-fixtures": "testing",
    "netrun-dogfood": "dogfood",
}

COMPATIBILITY_SHIM_TEMPLATE = '''"""
DEPRECATED: Import from netrun.{subpackage} instead.

This compatibility shim will be removed in version 3.0.0.
Update your imports:
    # Old (deprecated):
    from {old_import} import ...

    # New:
    from netrun.{subpackage} import ...

Migration Guide:
    1. Replace all imports:
       - from {old_import} import ... → from netrun.{subpackage} import ...

    2. Update requirements.txt or pyproject.toml:
       - Add: netrun-core>=2.0.0
       - Update: {package_name}>=2.0.0

    3. Run tests to verify compatibility

Author: Netrun Systems
Version: 2.0.0 (Compatibility Shim)
Date: 2025-12-18
"""
import warnings

warnings.warn(
    "{old_import} is deprecated. Use 'from netrun.{subpackage} import ...' instead. "
    "This compatibility module will be removed in version 3.0.0. "
    "See migration guide: https://docs.netrunsystems.com/{subpackage}/migration",
    DeprecationWarning,
    stacklevel=2
)

# Re-export all public APIs from netrun.{subpackage}
from netrun.{subpackage} import *
from netrun.{subpackage} import __all__
'''


def migrate_package(package_name: str, subpackage: str):
    """Migrate a single package to namespace structure."""
    print(f"\n{'='*60}")
    print(f"Migrating {package_name} to netrun.{subpackage}")
    print(f"{'='*60}")

    package_dir = Path(f"/data/workspace/github/Netrun_Service_Library_v2/packages/{package_name}")
    if not package_dir.exists():
        print(f"ERROR: Package directory {package_dir} not found!")
        return False

    old_module = package_name.replace("-", "_")
    old_module_dir = package_dir / old_module

    if not old_module_dir.exists():
        print(f"ERROR: Source directory {old_module_dir} not found!")
        return False

    # Step 1: Create namespace directory structure
    print(f"Step 1: Creating netrun/{subpackage}/ directory structure...")
    namespace_dir = package_dir / "netrun" / subpackage
    namespace_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Copy source files
    print(f"Step 2: Copying source files to netrun/{subpackage}/...")
    for item in old_module_dir.iterdir():
        if item.name == "__pycache__":
            continue
        dest = namespace_dir / item.name
        if item.is_file():
            shutil.copy2(item, dest)
            print(f"  Copied: {item.name}")
        elif item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
            print(f"  Copied directory: {item.name}")

    # Step 3: Update imports in __init__.py
    print(f"Step 3: Updating imports in netrun/{subpackage}/__init__.py...")
    init_file = namespace_dir / "__init__.py"
    if init_file.exists():
        content = init_file.read_text()
        # Replace old imports with new namespace imports
        updated_content = content.replace(f"from {old_module}.", f"from netrun.{subpackage}.")
        updated_content = updated_content.replace(f'version = "1.', f'version = "2.')
        updated_content = updated_content.replace(f'__version__ = "1.', f'__version__ = "2.')
        init_file.write_text(updated_content)
        print("  Updated imports and version")

    # Step 4: Create py.typed marker
    print("Step 4: Creating py.typed marker...")
    (namespace_dir / "py.typed").touch()
    print("  Created py.typed")

    # Step 5: Create compatibility shim
    print("Step 5: Creating compatibility shim...")
    shim_content = COMPATIBILITY_SHIM_TEMPLATE.format(
        subpackage=subpackage,
        old_import=old_module,
        package_name=package_name
    )
    shim_file = package_dir / old_module / "__init__.py"
    shim_file.write_text(shim_content)
    print(f"  Created compatibility shim at {old_module}/__init__.py")

    # Step 6: Update pyproject.toml
    print("Step 6: Updating pyproject.toml...")
    pyproject_file = package_dir / "pyproject.toml"
    if pyproject_file.exists():
        content = pyproject_file.read_text()

        # Update build backend
        if "setuptools" in content:
            content = content.replace('[build-system]\nrequires = ["setuptools', '[build-system]\nrequires = ["hatchling"]')
            content = content.replace('build-backend = "setuptools.build_meta"', 'build-backend = "hatchling.build"')

        # Update version
        content = content.replace('version = "1.', 'version = "2.')

        # Add netrun-core dependency
        if "dependencies = [" in content and "netrun-core" not in content:
            content = content.replace(
                "dependencies = [\n",
                "dependencies = [\n    \"netrun-core>=2.0.0\",\n"
            )

        # Update packages configuration for hatchling
        if "[tool.setuptools.packages.find]" in content:
            # Remove setuptools config
            lines = content.split("\n")
            new_lines = []
            skip_until_blank = False
            for line in lines:
                if "[tool.setuptools.packages.find]" in line or "[tool.setuptools.package-data]" in line:
                    skip_until_blank = True
                    continue
                if skip_until_blank and (line.strip() == "" or line.startswith("[")):
                    skip_until_blank = False
                if not skip_until_blank:
                    new_lines.append(line)
            content = "\n".join(new_lines)

        # Add hatchling build configuration
        if "[tool.hatch.build.targets.wheel]" not in content:
            # Find [project.urls] section and add before it
            urls_index = content.find("[project.urls]")
            if urls_index > 0:
                before_urls = content[:urls_index]
                after_urls = content[urls_index:]
                hatch_config = f'\n[tool.hatch.build.targets.wheel]\npackages = ["netrun", "{old_module}"]\n\n[tool.hatch.build.targets.sdist]\ninclude = [\n    "/netrun",\n    "/{old_module}",\n    "/tests",\n    "README.md",\n    "pyproject.toml",\n]\n\n'
                content = before_urls + hatch_config + after_urls

        # Update coverage source
        content = content.replace(f'source = ["{old_module}"]', f'source = ["netrun.{subpackage}"]')
        content = content.replace(f'--cov={old_module}', f'--cov=netrun.{subpackage}')

        # Update development status to Production/Stable
        content = content.replace(
            '"Development Status :: 4 - Beta"',
            '"Development Status :: 5 - Production/Stable"'
        )

        pyproject_file.write_text(content)
        print("  Updated pyproject.toml")

    print(f"\n✅ Migration complete for {package_name}!")
    return True


def build_package(package_name: str):
    """Build the migrated package."""
    print(f"\nBuilding {package_name}...")
    package_dir = Path(f"/data/workspace/github/Netrun_Service_Library_v2/packages/{package_name}")

    result = subprocess.run(
        ["python3", "-m", "build"],
        cwd=package_dir,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"✅ {package_name} built successfully!")
        # Show last few lines of output
        lines = result.stdout.split("\n")
        for line in lines[-5:]:
            if line.strip():
                print(f"  {line}")
        return True
    else:
        print(f"❌ {package_name} build failed!")
        print(result.stderr)
        return False


def main():
    """Main migration workflow."""
    print("\n" + "="*60)
    print("Netrun Namespace Package Migration")
    print("="*60)

    success_count = 0
    failed_packages = []

    for package_name, subpackage in PACKAGE_MAPPING.items():
        if migrate_package(package_name, subpackage):
            if build_package(package_name):
                success_count += 1
            else:
                failed_packages.append(f"{package_name} (build failed)")
        else:
            failed_packages.append(f"{package_name} (migration failed)")

    # Summary
    print("\n" + "="*60)
    print("Migration Summary")
    print("="*60)
    print(f"Total packages: {len(PACKAGE_MAPPING)}")
    print(f"Successfully migrated and built: {success_count}")
    print(f"Failed: {len(failed_packages)}")

    if failed_packages:
        print("\nFailed packages:")
        for pkg in failed_packages:
            print(f"  - {pkg}")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
