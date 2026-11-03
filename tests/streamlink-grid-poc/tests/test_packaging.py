# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
"""Guard the PEP 639 license metadata against an incompatible build backend."""

from pathlib import Path
import re


PROJECT = Path(__file__).resolve().parents[1]


def test_pep639_license_metadata_requires_setuptools_77_or_newer():
    pyproject = (PROJECT / "pyproject.toml").read_text(encoding="utf-8")
    build_system = re.search(r"(?ms)^\[build-system\]\s*(.*?)(?=^\[|\Z)", pyproject)
    assert build_system is not None
    requirement = re.search(
        r"(?m)^requires\s*=\s*\[\s*['\"]setuptools>=([0-9.]+)['\"]\s*\]",
        build_system.group(1),
    )
    assert requirement is not None
    backend_minimum = tuple(int(part) for part in requirement.group(1).split("."))
    assert backend_minimum + (0,) * (2 - len(backend_minimum)) >= (77, 0)
    assert re.search(r'(?m)^license\s*=\s*"AGPL-3\.0-only"\s*$', pyproject)
    assert re.search(r'(?m)^license-files\s*=\s*\["LICENSE"\]\s*$', pyproject)
