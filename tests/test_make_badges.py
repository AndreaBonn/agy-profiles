import importlib.util
import json
import runpy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "make_badges.py"
NOT_AVAILABLE_TESTS = {"schemaVersion": 1, "label": "tests", "message": "N/A", "color": "lightgrey"}
NOT_AVAILABLE_COVERAGE = {
    "schemaVersion": 1,
    "label": "coverage",
    "message": "N/A",
    "color": "lightgrey",
}


@pytest.fixture(scope="module")
def badges():
    spec = importlib.util.spec_from_file_location("make_badges", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_junit(*, path: Path, tests: int, failures: int = 0, errors: int = 0, skipped: int = 0):
    path.write_text(
        '<?xml version="1.0"?><testsuites>'
        f'<testsuite name="pytest" tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}"></testsuite></testsuites>'
    )


def write_coverage(*, path: Path, display: str):
    path.write_text(
        json.dumps(
            {"totals": {"percent_covered": float(display), "percent_covered_display": display}}
        )
    )


def test_test_badge_all_passed_is_green(badges, tmp_path):
    junit = tmp_path / "junit.xml"
    write_junit(path=junit, tests=164)

    assert badges.build_test_badge(junit_path=junit) == {
        "schemaVersion": 1,
        "label": "tests",
        "message": "164 passed",
        "color": "brightgreen",
    }


def test_test_badge_with_failures_shows_ratio_and_red(badges, tmp_path):
    junit = tmp_path / "junit.xml"
    write_junit(path=junit, tests=10, failures=2, errors=1)

    badge = badges.build_test_badge(junit_path=junit)

    assert badge["message"] == "7/10 passed"
    assert badge["color"] == "red"


def test_test_badge_failures_and_skipped_together(badges, tmp_path):
    junit = tmp_path / "junit.xml"
    write_junit(path=junit, tests=10, failures=1, skipped=2)

    badge = badges.build_test_badge(junit_path=junit)

    assert badge["message"] == "7/10 passed"
    assert badge["color"] == "red"


def test_test_badge_skipped_are_not_counted_as_passed(badges, tmp_path):
    junit = tmp_path / "junit.xml"
    write_junit(path=junit, tests=10, skipped=3)

    badge = badges.build_test_badge(junit_path=junit)

    assert badge["message"] == "7 passed"
    assert badge["color"] == "brightgreen"


@pytest.mark.parametrize(("tests", "skipped"), [(0, 0), (4, 4)])
def test_test_badge_nothing_passed_is_grey_not_green(badges, tmp_path, tests, skipped):
    junit = tmp_path / "junit.xml"
    write_junit(path=junit, tests=tests, skipped=skipped)

    badge = badges.build_test_badge(junit_path=junit)

    assert badge["message"] == "0 passed"
    assert badge["color"] == "lightgrey"


def test_test_badge_single_testsuite_root(badges, tmp_path):
    junit = tmp_path / "junit.xml"
    junit.write_text('<testsuite tests="5" failures="0" errors="0" skipped="0"></testsuite>')

    assert badges.build_test_badge(junit_path=junit)["message"] == "5 passed"


def test_test_badge_missing_file_is_not_available(badges, tmp_path):
    assert badges.build_test_badge(junit_path=tmp_path / "missing.xml") == NOT_AVAILABLE_TESTS


@pytest.mark.parametrize("content", ["", "not xml at all", "<testsuite tests='x'></testsuite>"])
def test_test_badge_unreadable_file_is_not_available(badges, tmp_path, content):
    junit = tmp_path / "junit.xml"
    junit.write_text(content)

    assert badges.build_test_badge(junit_path=junit) == NOT_AVAILABLE_TESTS


@pytest.mark.parametrize(
    ("display", "color"),
    [
        ("100", "brightgreen"),
        ("90", "brightgreen"),
        ("85.5", "green"),
        ("60", "yellow"),
        ("59.9", "red"),
    ],
)
def test_coverage_badge_color_follows_displayed_value(badges, tmp_path, display, color):
    cov = tmp_path / "coverage.json"
    write_coverage(path=cov, display=display)

    badge = badges.build_coverage_badge(coverage_path=cov)

    assert badge["color"] == color
    assert badge["message"] == f"{display}%"


def test_coverage_badge_rounded_display_decides_the_color(badges, tmp_path):
    cov = tmp_path / "coverage.json"
    cov.write_text(
        json.dumps({"totals": {"percent_covered": 89.6, "percent_covered_display": "90"}})
    )

    badge = badges.build_coverage_badge(coverage_path=cov)

    assert badge["message"] == "90%"
    assert badge["color"] == "brightgreen"


def test_coverage_badge_missing_file_is_not_available(badges, tmp_path):
    assert (
        badges.build_coverage_badge(coverage_path=tmp_path / "missing.json")
        == NOT_AVAILABLE_COVERAGE
    )


@pytest.mark.parametrize("content", ["", "{not json", "{}", '{"totals": {}}'])
def test_coverage_badge_unreadable_file_is_not_available(badges, tmp_path, content):
    cov = tmp_path / "coverage.json"
    cov.write_text(content)

    assert badges.build_coverage_badge(coverage_path=cov) == NOT_AVAILABLE_COVERAGE


def test_write_badges_creates_both_json_files(badges, tmp_path):
    junit = tmp_path / "junit.xml"
    cov = tmp_path / "coverage.json"
    write_junit(path=junit, tests=3)
    write_coverage(path=cov, display="100")
    out = tmp_path / "badges"

    badges.write_badges(junit_path=junit, coverage_path=cov, out_dir=out)

    assert json.loads((out / "test-badge.json").read_text())["message"] == "3 passed"
    assert json.loads((out / "coverage-badge.json").read_text())["message"] == "100%"


def test_running_the_script_writes_badges_from_the_default_report_paths(tmp_path, monkeypatch):
    write_junit(path=tmp_path / "test-results.xml", tests=3)
    write_coverage(path=tmp_path / "coverage.json", display="100")
    monkeypatch.chdir(tmp_path)

    runpy.run_path(str(SCRIPT), run_name="__main__")

    assert json.loads((tmp_path / "badges" / "test-badge.json").read_text())["message"] == (
        "3 passed"
    )


@pytest.mark.parametrize("missing", ["junit", "coverage"])
def test_write_badges_refuses_to_write_when_an_input_is_missing(badges, tmp_path, missing):
    junit = tmp_path / "junit.xml"
    cov = tmp_path / "coverage.json"
    if missing != "junit":
        write_junit(path=junit, tests=3)
    if missing != "coverage":
        write_coverage(path=cov, display="100")
    out = tmp_path / "badges"

    with pytest.raises(SystemExit) as exc:
        badges.write_badges(junit_path=junit, coverage_path=cov, out_dir=out)

    assert exc.value.code != 0
    assert not out.exists()
