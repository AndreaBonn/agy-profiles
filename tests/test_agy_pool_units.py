import os
from pathlib import Path

import pytest

# --- classify -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "HTTP 429.",
        "rate-limit hit",
        "ratelimit",
        "rate_limit",
        "RATE LIMIT",
        "Too Many Requests",
        "usage limit reached",
        "quota exceeded",
        "resource_exhausted",
    ],
)
def test_classify_quota_wordings_are_recognised(pool, text: str) -> None:
    assert pool.classify(returncode=1, tail=text.encode()) == "quota"


@pytest.mark.parametrize("text", ["connection refused on port 4290", "error4295", "segfault"])
def test_classify_429_inside_a_longer_number_is_not_quota(pool, text: str) -> None:
    assert pool.classify(returncode=1, tail=text.encode()) == "error"


def test_classify_invalid_utf8_tail_is_still_classified(pool) -> None:
    assert pool.classify(returncode=1, tail=b"\xff\xfe 429 quota") == "quota"


def test_classify_empty_tail_on_failure_is_a_generic_error(pool) -> None:
    assert pool.classify(returncode=1, tail=b"") == "error"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("not eligible, quota exceeded 429", "ineligible"),
        ("Authentication failed after 429", "auth"),
    ],
)
def test_classify_permanent_conditions_win_over_quota(pool, text: str, expected: str) -> None:
    assert pool.classify(returncode=1, tail=text.encode()) == expected


# --- natural_key / rule_summary -------------------------------------------------------


def test_natural_key_orders_names_without_digits_and_leading_digits(pool) -> None:
    names = ["b", "10x", "a", "2x"]

    assert sorted(names, key=pool.natural_key) == ["2x", "10x", "a", "b"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("intro\n\n# Real Title  \nbody\n", "Real Title"),
        ("## Subheading only\nbody\n", "rule"),
        ("#hashtag is not a heading\n", "rule"),
        ("", "rule"),
    ],
)
def test_rule_summary_returns_first_h1_or_the_stem(
    pool, tmp_path: Path, content: str, expected: str
) -> None:
    path = tmp_path / "rule.md"
    path.write_text(content)

    assert pool.rule_summary(path=path) == expected


# --- build_agents_md ------------------------------------------------------------------


def test_build_agents_md_lists_rules_alphabetically_and_ignores_other_files(
    pool, tmp_path: Path
) -> None:
    (tmp_path / "zeta.md").write_text("# Zeta\n")
    (tmp_path / "alpha.md").write_text("# Alpha\n")
    (tmp_path / "notes.txt").write_text("# Not a rule\n")

    text = pool.build_agents_md(rules_dir=tmp_path)

    assert text.index("| Alpha |") < text.index("| Zeta |")
    assert "Not a rule" not in text


def test_build_agents_md_with_no_rules_has_the_headings_and_no_rows(pool, tmp_path: Path) -> None:
    text = pool.build_agents_md(rules_dir=tmp_path)

    assert "| File | Argomento |" in text
    assert "## Regole sempre attive" in text
    assert "@[" not in text


def test_build_agents_md_inlines_a_rule_that_exactly_fills_the_budget(pool, tmp_path: Path) -> None:
    security = tmp_path / "security.md"
    security.write_text("# S\n" + "x" * pool.AGENTS_MD_BUDGET)
    base = len(pool.build_agents_md(rules_dir=tmp_path).encode())
    exact = pool.AGENTS_MD_BUDGET - base

    security.write_text("# S\n" + "x" * (exact - 4))
    fits = pool.build_agents_md(rules_dir=tmp_path)
    security.write_text("# S\n" + "x" * (exact - 3))
    overflows = pool.build_agents_md(rules_dir=tmp_path)

    assert "@[security]" in fits
    assert "@[security]" not in overflows


def test_build_agents_md_keeps_trying_smaller_rules_after_one_does_not_fit(
    pool, tmp_path: Path
) -> None:
    (tmp_path / "python-stack.md").write_text("# P\n" + "x" * 15_000)
    (tmp_path / "git-workflow.md").write_text("# G\n" + "x" * 15_000)
    (tmp_path / "security.md").write_text("# S\nsmall\n")

    text = pool.build_agents_md(rules_dir=tmp_path)

    assert "@[python-stack]" in text
    assert "@[git-workflow]" not in text
    assert "@[security]" in text


# --- convert_agent --------------------------------------------------------------------


def test_convert_agent_without_closing_delimiter_is_unchanged(pool) -> None:
    text = "---\nname: a\nmodel: x\nbody without closing\n"

    assert pool.convert_agent(text=text) == text


def test_convert_agent_drops_a_dropped_field_that_is_last_in_the_frontmatter(pool) -> None:
    text = "---\nname: a\ntools: Read\n---\nbody\n"

    assert pool.convert_agent(text=text) == "---\nname: a\n---\nbody\n"


def test_convert_agent_drops_an_unindented_yaml_list(pool) -> None:
    text = "---\nname: a\ntools:\n- Read\n- Grep\ndescription: d\n---\nbody\n"

    assert pool.convert_agent(text=text) == "---\nname: a\ndescription: d\n---\nbody\n"


def test_convert_agent_drops_folded_continuation_lines(pool) -> None:
    text = "---\nname: a\ntools: >\n  Read,\n  Grep\ndescription: d\n---\nbody\n"

    assert pool.convert_agent(text=text) == "---\nname: a\ndescription: d\n---\nbody\n"


def test_convert_agent_keeps_similar_and_nested_keys(pool) -> None:
    text = "---\nname: a\nmodel_hint: x\nmetadata:\n  model: y\n---\nbody\n"

    assert pool.convert_agent(text=text) == text


def test_convert_agent_leaves_horizontal_rules_in_the_body_alone(pool) -> None:
    text = "---\nname: a\nmodel: x\n---\nintro\n\n---\n\nmodel: z\n"

    assert pool.convert_agent(text=text) == "---\nname: a\n---\nintro\n\n---\n\nmodel: z\n"


def test_convert_agent_is_idempotent(pool) -> None:
    once = pool.convert_agent(text="---\nname: a\nmodel: x\ntools:\n  - R\n---\nbody\n")

    assert pool.convert_agent(text=once) == once


# --- agy_env --------------------------------------------------------------------------


def test_agy_env_points_home_at_the_account_and_disables_dbus(fresh_pool) -> None:
    before = dict(os.environ)

    env = fresh_pool.agy_env(name="acc7")

    assert env["HOME"] == str(fresh_pool.POOL_DIR / "acc7")
    assert env["DBUS_SESSION_BUS_ADDRESS"] == "disabled"
    assert env["PATH"] == before["PATH"]
    assert dict(os.environ) == before
