from pathlib import Path

import pytest

from framework.ai.contracts import DataRow
from framework.ai.integrity import (
    assertion_signatures,
    check_assertions,
    protected_hashes,
    source_files,
)


def generated_file(root: Path, code: str) -> Path:
    path = root / "tests/generated/run/test_example.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code)
    return path


def test_assertion_edits_are_blocked_but_action_locator_changes_are_allowed(tmp_path: Path) -> None:
    path = generated_file(
        tmp_path,
        "def test_case(page):\n"
        "    page.get_by_role('button', name='Old').click()\n    assert 1 == 1\n",
    )
    before = assertion_signatures(tmp_path, "run")
    path.write_text(path.read_text().replace("Old", "New"))
    check_assertions(before, assertion_signatures(tmp_path, "run"))
    path.write_text(path.read_text().replace("assert 1 == 1", "assert True"))
    with pytest.raises(ValueError, match="Frozen assertions"):
        check_assertions(before, assertion_signatures(tmp_path, "run"))


@pytest.mark.parametrize(
    "code",
    [
        "import pytest\npytest.skip('hide')",
        "from pytest import xfail as hide",
        "try:\n    assert False\nexcept Exception:\n    pass",
    ],
)
def test_skip_and_exception_swallowing_are_rejected(tmp_path: Path, code: str) -> None:
    generated_file(tmp_path, code)
    with pytest.raises(ValueError):
        assertion_signatures(tmp_path, "run")


def test_initial_syntax_error_can_be_fixed_but_valid_assertions_cannot_disappear(
    tmp_path: Path,
) -> None:
    path = generated_file(tmp_path, "def broken(:")
    before = assertion_signatures(tmp_path, "run")
    assert list(before.values()) == [None]
    path.write_text("def test_case():\n    assert True\n")
    after = assertion_signatures(tmp_path, "run")
    check_assertions(before, after)
    path.write_text("def broken(:")
    with pytest.raises(ValueError):
        check_assertions(after, assertion_signatures(tmp_path, "run"))


def test_protected_snapshot_detects_additions_and_excludes_runtime_outputs(tmp_path: Path) -> None:
    folder = tmp_path / "framework"
    folder.mkdir()
    (folder / "core.py").write_text("x = 1")
    before = protected_hashes(tmp_path)
    generated_file(tmp_path, "assert True")
    assert protected_hashes(tmp_path) == before
    (folder / "new.py").write_text("x = 2")
    assert protected_hashes(tmp_path) != before


def test_source_snapshot_rejects_outside_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "private.py"
    outside.write_text("synthetic = True")
    root = tmp_path / "workspace"
    (root / "framework").mkdir(parents=True)
    (root / "framework/link.py").symlink_to(outside)
    with pytest.raises(ValueError, match="links"):
        source_files(root)


@pytest.mark.parametrize(
    "title,flag",
    [("", "true"), ("a" * 51, "true"), ("valid", "false")],
    ids=["empty-marked-valid", "long-marked-valid", "valid-marked-invalid"],
)
def test_data_expectations_are_checked_against_rules(title: str, flag: str) -> None:
    with pytest.raises(ValueError, match="expected_valid"):
        DataRow.model_validate(
            {
                "data_id": "ROW_001",
                "title": title,
                "content": "valid",
                "tags": "",
                "comment": "valid",
                "expected_valid": flag,
            }
        )
