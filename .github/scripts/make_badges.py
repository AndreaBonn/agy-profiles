"""Write shields.io endpoint JSON for the test-count and coverage badges."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

JUNIT_PATH = Path("test-results.xml")
COVERAGE_PATH = Path("coverage.json")
BADGES_DIR = Path("badges")

JUNIT_KEYS = ("tests", "failures", "errors", "skipped")
COVERAGE_COLORS = ((90.0, "brightgreen"), (80.0, "green"), (60.0, "yellow"))
FALLBACK_COVERAGE_COLOR = "red"
NOT_AVAILABLE = "N/A"


def make_badge(*, label: str, message: str, color: str) -> dict[str, Any]:
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def read_junit_totals(*, junit_path: Path) -> dict[str, int] | None:
    """Sum the counters of a JUnit XML file; None if it is missing or unreadable."""
    if not junit_path.is_file():
        return None
    try:
        root = ET.parse(junit_path).getroot()
        suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
        return {key: sum(int(suite.attrib.get(key, 0)) for suite in suites) for key in JUNIT_KEYS}
    except (ET.ParseError, ValueError):
        return None


def build_test_badge(*, junit_path: Path) -> dict[str, Any]:
    """Count passed tests; skipped tests are not passed, and zero passed is never green."""
    totals = read_junit_totals(junit_path=junit_path)
    if totals is None:
        return make_badge(label="tests", message=NOT_AVAILABLE, color="lightgrey")
    bad = totals["failures"] + totals["errors"]
    passed = totals["tests"] - bad - totals["skipped"]
    if bad:
        return make_badge(label="tests", message=f"{passed}/{totals['tests']} passed", color="red")
    color = "brightgreen" if passed else "lightgrey"
    return make_badge(label="tests", message=f"{passed} passed", color=color)


def read_coverage_display(*, coverage_path: Path) -> str | None:
    """Total coverage as ``coverage json`` displays it; None if missing or unreadable."""
    if not coverage_path.is_file():
        return None
    try:
        display = str(json.loads(coverage_path.read_text())["totals"]["percent_covered_display"])
        float(display)
    except (KeyError, TypeError, ValueError):
        return None
    return display


def build_coverage_badge(*, coverage_path: Path) -> dict[str, Any]:
    """The color follows the displayed (rounded) value, so message and color agree."""
    display = read_coverage_display(coverage_path=coverage_path)
    if display is None:
        return make_badge(label="coverage", message=NOT_AVAILABLE, color="lightgrey")
    percent = float(display)
    color = next(
        (name for threshold, name in COVERAGE_COLORS if percent >= threshold),
        FALLBACK_COVERAGE_COLOR,
    )
    return make_badge(label="coverage", message=f"{display}%", color=color)


def write_badges(*, junit_path: Path, coverage_path: Path, out_dir: Path) -> None:
    """Write both badges, or exit non-zero without writing if a report is unusable.

    A run that broke before producing its reports must fail the step, so the
    publish job never replaces good badges with N/A ones.
    """
    badges = {
        "test-badge.json": build_test_badge(junit_path=junit_path),
        "coverage-badge.json": build_coverage_badge(coverage_path=coverage_path),
    }
    if any(badge["message"] == NOT_AVAILABLE for badge in badges.values()):
        raise SystemExit("make_badges: missing or unreadable report, no badge written")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, badge in badges.items():
        (out_dir / name).write_text(json.dumps(badge))


if __name__ == "__main__":
    write_badges(junit_path=JUNIT_PATH, coverage_path=COVERAGE_PATH, out_dir=BADGES_DIR)
