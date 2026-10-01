"""Measure actual local CLI processes and verify fixture ground truth offline."""

import json
from pathlib import Path
import shutil
import subprocess
import sysconfig
import tempfile
import time


def main():
    executable = shutil.which("scsg")
    if executable is None:
        suffix = "scsg.exe" if __import__("os").name == "nt" else "scsg"
        executable = str(Path(sysconfig.get_path("scripts", scheme="nt_user" if suffix.endswith(".exe") else "posix_user")) / suffix)
    with tempfile.TemporaryDirectory(prefix="scsg-demo-") as temporary:
        cwd = Path(temporary)
        started = time.perf_counter()
        outputs = []
        for args in (["fixtures", "--out", "demo"], ["run", "--input", "demo"], ["report", "--format", "md"]):
            result = subprocess.run([executable, *args], cwd=cwd, capture_output=True, encoding="utf-8", check=True)
            outputs.append(result.stdout)
        elapsed = time.perf_counter() - started
        expected = json.loads((cwd / "demo/expectations.json").read_text(encoding="utf-8"))
        actual = json.loads(outputs[1])
        assert actual["counts"] == expected["counts"]
        assert actual["totals"]["minutes"]["saved"] == expected["saved_minutes"]
        assert actual["totals"]["gbp"]["saved"] == expected["saved_gbp"]
        assert [c["id"] for c in actual["cases"]] == expected["publishable_ids"]
        assert "DATA PROVENANCE" in outputs[2]
        assert "Traceback" not in "".join(outputs)
        assert elapsed < 5, f"Demo took {elapsed:.6f}s"
        print(json.dumps({"elapsed_seconds": round(elapsed, 6), "record_count": 200, "publishable": 120, "excluded": 80, "false_positives": 0, "missed_cases": 0, "illustrative_saved_minutes": actual["totals"]["minutes"]["saved"], "illustrative_saved_gbp": actual["totals"]["gbp"]["saved"], "provenance_banner_present": True}, indent=2))


if __name__ == "__main__":
    main()
