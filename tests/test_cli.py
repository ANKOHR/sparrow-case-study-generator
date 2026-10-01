import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from sparrow_case_study_generator.cli import atomic_write, main


def demo(tmp_path):
    directory = tmp_path / "demo"
    state = tmp_path / "state.json"
    assert main(["fixtures", "--out", str(directory)]) == 0
    assert main(["run", "--input", str(directory), "--state", str(state)]) == 0
    return directory, state


def test_run_completes_on_fixture(tmp_path, capsys):
    started = time.perf_counter()
    _, state = demo(tmp_path)
    capsys.readouterr()
    assert main(["report", "--state", str(state), "--format", "md"]) == 0
    assert time.perf_counter() - started < 5
    assert "DATA PROVENANCE" in capsys.readouterr().out


def test_cli_smoke_all_subcommands(tmp_path, capsys):
    directory, state = demo(tmp_path)
    for args in (["audit", "--input", str(directory)], ["case", "--input", str(directory), "--id", "000-A"], ["case", "--input", str(directory), "--id", "000-E", "--format", "json"], ["report", "--state", str(state), "--format", "json"]):
        assert main(args) == 0
    for command in ("fixtures", "run", "audit", "case", "report"):
        with pytest.raises(SystemExit) as exc:
            main([command, "--help"])
        assert exc.value.code == 0
    assert "Example:" in capsys.readouterr().out
    assert main(["case", "--input", str(directory), "--id", "000-C"]) == 2


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    state = tmp_path / "state.json"
    assert main(["run", "--input", str(empty), "--state", str(state)]) == 0
    capsys.readouterr()
    assert main(["report", "--state", str(state)]) == 0
    output = capsys.readouterr().out
    assert "publishable: 0" in output
    assert "0.00" in output


def test_malformed_input_named_error(tmp_path, capsys):
    (tmp_path / "records.json").write_text('{\n "records": [bad]\n}', encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "records.json: line 2" in error
    assert "ParseError" in error
    assert "Traceback" not in error


def test_missing_input_named_error(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "absent")]) == 2
    assert "MissingInput" in capsys.readouterr().err
    assert main(["report", "--state", str(tmp_path / "absent.json")]) == 2
    assert "use scsg fixtures" in capsys.readouterr().err


def test_determinism_byte_identical(tmp_path, capsys):
    directory, state = demo(tmp_path)
    before = state.read_bytes()
    assert main(["run", "--input", str(directory), "--state", str(state)]) == 0
    assert state.read_bytes() == before
    for fmt in ("md", "json"):
        path = tmp_path / ("report." + fmt)
        assert main(["report", "--state", str(state), "--format", fmt, "--out", str(path)]) == 0
        first = path.read_bytes()
        assert main(["report", "--state", str(state), "--format", fmt, "--out", str(path)]) == 0
        assert path.read_bytes() == first


def test_report_write_failure_no_partial_files(tmp_path, capsys):
    _, state = demo(tmp_path)
    target = tmp_path / "output"
    target.mkdir()
    before = set(tmp_path.iterdir())
    assert main(["report", "--state", str(state), "--out", str(target)]) == 2
    assert set(tmp_path.iterdir()) == before
    assert target.is_dir()
    assert "WriteOrReadError" in capsys.readouterr().err


def test_schema_error_names_file_and_field(tmp_path, capsys):
    directory, _ = demo(tmp_path)
    path = directory / "records.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["records"][0]["permission"] = "yes"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main(["run", "--input", str(directory)]) == 2
    error = capsys.readouterr().err
    assert "records.json" in error and "permission" in error and "SchemaError" in error


def test_module_entrypoint(tmp_path):
    process = subprocess.run([sys.executable, "-m", "sparrow_case_study_generator.cli", "fixtures", "--out", str(tmp_path / "demo")], capture_output=True, text=True)
    assert process.returncode == 0
    assert "SYNTHETIC" in process.stdout


def test_duplicate_json_keys_named_error(tmp_path, capsys):
    (tmp_path / "records.json").write_text('{"records": [],\n "records": []}', encoding="utf-8")
    assert main(["audit", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "line 2: duplicate JSON key records" in error


def test_fixture_files_header_and_corrupted_expectations_ignored(tmp_path, capsys):
    directory, state = demo(tmp_path)
    for path in directory.iterdir():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["synthetic"] is True
        assert path.read_text(encoding="utf-8").splitlines()[1].startswith('  "_comment": "SYNTHETIC')
    (directory / "expectations.json").write_text('{"synthetic":true,"saved_minutes":"999999"}', encoding="utf-8")
    assert main(["run", "--input", str(directory), "--state", str(state)]) == 0
    capsys.readouterr()
    assert main(["report", "--state", str(state), "--format", "json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["totals"]["minutes"]["saved"] == "1400.00"


def test_atomic_failure_preserves_existing_report(tmp_path, monkeypatch):
    import sparrow_case_study_generator.cli as cli
    target = tmp_path / "report.md"
    target.write_text("old valid report", encoding="utf-8")

    def fail_replace(*args):
        raise PermissionError("simulated locked destination")

    monkeypatch.setattr(cli.os, "replace", fail_replace)
    with pytest.raises(PermissionError):
        atomic_write(target, "new report")
    assert target.read_text(encoding="utf-8") == "old valid report"
    assert list(tmp_path.iterdir()) == [target]


def test_unsupported_input_not_silently_dropped(tmp_path, capsys):
    (tmp_path / "bad.csv").write_text("bad,csv", encoding="utf-8")
    assert main(["audit", "--input", str(tmp_path)]) == 2
    assert "bad.csv" in capsys.readouterr().err


def test_invalid_utf8_names_file_and_line(tmp_path, capsys):
    (tmp_path / "records.json").write_bytes(b'{\n\xff}')
    assert main(["audit", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "records.json: line 2: invalid UTF-8" in error
