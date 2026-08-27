from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from kosmo.contracts.sdd.ids import ProjectId
from kosmo.infrastructure.codegen.workspace import (
    DEFAULT_TEMPLATE_DIR,
    LocalWorkspaceManager,
)


@pytest.mark.unit
def test_default_template_directory_exists_and_has_required_files() -> None:
    # Arrange & Act
    template_path = DEFAULT_TEMPLATE_DIR

    # Assert
    assert template_path.exists(), f"Template directory does not exist at {template_path}"
    assert template_path.is_dir()

    expected_files = [
        "package.json",
        "tsconfig.json",
        "next.config.ts",
        "drizzle.config.ts",
        "vitest.config.ts",
        "eslint.config.mjs",
        "postcss.config.mjs",
        "kosmo-conventions.md",
        "src/app/layout.tsx",
        "src/app/page.tsx",
        "src/app/globals.css",
        "src/db/schema.ts",
        "src/db/index.ts",
        "src/lib/utils.ts",
        "tests/setup.ts",
        "tests/example.test.ts",
        ".opencode/skills/kosmo-implementation/SKILL.md",
        ".opencode/skills/kosmo-testing/SKILL.md",
        ".opencode/skills/kosmo-drizzle/SKILL.md",
        ".opencode/skills/kosmo-nextjs/SKILL.md",
        ".opencode/skills/tdd/SKILL.md",
    ]

    for expected_file in expected_files:
        file_path = template_path / expected_file
        assert file_path.exists(), f"Expected template file '{expected_file}' is missing."


@pytest.mark.unit
def test_package_json_structure_and_dependencies() -> None:
    # Arrange
    pkg_file = DEFAULT_TEMPLATE_DIR / "package.json"

    # Act
    content = json.loads(pkg_file.read_text(encoding="utf-8"))

    # Assert — Scripts
    scripts = content.get("scripts", {})
    assert "dev" in scripts
    assert "build" in scripts
    assert "start" in scripts
    assert "lint" in scripts
    assert "test" in scripts
    assert "db:push" in scripts

    # Assert — Dependencies
    deps = content.get("dependencies", {})
    assert "next" in deps
    assert "react" in deps
    assert "react-dom" in deps
    assert "drizzle-orm" in deps
    assert "better-sqlite3" in deps
    assert "clsx" in deps
    assert "bootstrap" in deps
    assert "lucide-react" in deps

    # Assert — DevDependencies
    dev_deps = content.get("devDependencies", {})
    assert "typescript" in dev_deps
    assert "@types/node" in dev_deps
    assert "@types/react" in dev_deps
    assert "@types/react-dom" in dev_deps
    assert "@types/better-sqlite3" in dev_deps
    assert "drizzle-kit" in dev_deps
    assert "vitest" in dev_deps
    assert "eslint" in dev_deps
    assert "@eslint/js" in dev_deps
    assert "typescript-eslint" in dev_deps


@pytest.mark.unit
def test_tsconfig_json_has_strict_configuration() -> None:
    # Arrange
    tsconfig_file = DEFAULT_TEMPLATE_DIR / "tsconfig.json"

    # Act
    content = json.loads(tsconfig_file.read_text(encoding="utf-8"))
    compiler_options = content.get("compilerOptions", {})

    # Assert
    assert compiler_options.get("strict") is True
    assert compiler_options.get("noEmit") is True
    assert compiler_options.get("moduleResolution") == "bundler"
    paths = compiler_options.get("paths", {})
    assert "@/*" in paths
    assert paths["@/*"] == ["./src/*"]


@pytest.mark.unit
def test_template_directory_structure_completeness() -> None:
    # Arrange
    template_path = DEFAULT_TEMPLATE_DIR

    # Act & Assert
    assert (template_path / "src" / "app").is_dir()
    assert (template_path / "src" / "components").is_dir()
    assert (template_path / "src" / "db").is_dir()
    assert (template_path / "src" / "lib").is_dir()
    assert (template_path / "tests").is_dir()
    assert (template_path / "public").is_dir()


@pytest.mark.unit
def test_drizzle_and_vitest_and_eslint_configurations() -> None:
    # Arrange
    drizzle_cfg = (DEFAULT_TEMPLATE_DIR / "drizzle.config.ts").read_text(encoding="utf-8")
    vitest_cfg = (DEFAULT_TEMPLATE_DIR / "vitest.config.ts").read_text(encoding="utf-8")
    eslint_cfg = (DEFAULT_TEMPLATE_DIR / "eslint.config.mjs").read_text(encoding="utf-8")
    conventions = (DEFAULT_TEMPLATE_DIR / "kosmo-conventions.md").read_text(encoding="utf-8")

    # Assert — Drizzle
    assert "sqlite" in drizzle_cfg
    assert "drizzle-kit" in drizzle_cfg
    assert "schema.ts" in drizzle_cfg

    # Assert — Vitest
    assert "vitest/config" in vitest_cfg
    assert "setupFiles" in vitest_cfg
    assert "@" in vitest_cfg

    # Assert — ESLint flat config
    assert "@eslint/js" in eslint_cfg
    assert "typescript-eslint" in eslint_cfg
    assert "no-explicit-any" in eslint_cfg

    # Assert — Conventions
    assert "Next.js 16" in conventions
    assert "Drizzle ORM" in conventions
    assert "Vitest" in conventions


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_workspace_manager_copies_default_template() -> None:
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_root:
        manager = LocalWorkspaceManager(
            workspaces_root=tmp_root,
            git_init=False,
        )
        project_id = ProjectId("prj_template_test")

        # Act
        ws = await manager.ensure_workspace(project_id)

        # Assert
        assert ws.workspace_dir is not None
        ws_dir = Path(ws.workspace_dir)

        assert (ws_dir / "package.json").exists()
        assert (ws_dir / "tsconfig.json").exists()
        assert (ws_dir / "next.config.ts").exists()
        assert (ws_dir / "drizzle.config.ts").exists()
        assert (ws_dir / "vitest.config.ts").exists()
        assert (ws_dir / "eslint.config.mjs").exists()
        assert (ws_dir / "postcss.config.mjs").exists()
        assert (ws_dir / "kosmo-conventions.md").exists()
        assert (ws_dir / "src" / "app" / "layout.tsx").exists()
        assert (ws_dir / "src" / "app" / "page.tsx").exists()
        assert (ws_dir / "src" / "app" / "globals.css").exists()
        assert (ws_dir / "src" / "db" / "schema.ts").exists()
        assert (ws_dir / "src" / "db" / "index.ts").exists()
        assert (ws_dir / "src" / "lib" / "utils.ts").exists()
        assert (ws_dir / "tests" / "setup.ts").exists()
        assert (ws_dir / "tests" / "example.test.ts").exists()

        # Check manifest
        assert "package.json" in ws.manifest_files
        assert "src/app/layout.tsx" in ws.manifest_files
        assert "src/db/schema.ts" in ws.manifest_files
        assert "tests/example.test.ts" in ws.manifest_files
