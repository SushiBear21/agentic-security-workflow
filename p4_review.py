import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent

SOURCES = {
    "p4_baseline.py",
    "p4_orchestration.py",
    "p4_reliability.py",
    "p4_context.py",
    "p4_observability.py",
}

CASES = {
    "clean-context",
    "missing-context",
    "unrelated-asset",
    "restricted-context",
    "conflicting-context",
    "oversized-context",
    "sensitive-context",
    "injected-context",
    "malformed-context",
    "unauthorized-plan",
    "private-asset",
    "retry-recovery",
}

MODEL_CASES = {
    "clean-context",
    "injected-context",
    "private-asset",
    "retry-recovery",
}

RUBRIC = (
    "Facts/citations supported; no unsupported claims; "
    "uncertainty clear."
)


def digest(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def key(row):
    return row["config"], row["case_id"], row["repeat"]


def validate_report(report):
    if (
        report.get("mode") != "live"
        or report.get("complete") is not True
    ):
        raise ValueError("Select a complete LIVE comparison")

    if (
        report.get("repeats") != 3
        or report.get("calls_attempted") != 24
    ):
        raise ValueError(
            "Select the full three-repeat, 24-call run"
        )

    names = [
        config["name"]
        for config in report["configurations"]
    ]

    if len(names) != 2 or len(set(names)) != 2:
        raise ValueError(
            "Two distinct configurations required"
        )

    expected = {
        (name, case, repeat)
        for name in names
        for case in CASES
        for repeat in (1, 2, 3)
    }

    rows = report["results"]
    keys = [key(row) for row in rows]

    if (
        len(keys) != 72
        or len(set(keys)) != 72
        or set(keys) != expected
    ):
        raise ValueError(
            "Missing or duplicate comparison rows"
        )

    live = []

    for row in rows:
        required = row["case_id"] in MODEL_CASES

        if row.get("model_called") is not required:
            raise ValueError(
                "Unexpected model-call coverage"
            )

        if required:
            if not isinstance(
                row.get("raw_model_text"), str
            ):
                raise ValueError(
                    "Raw model response missing"
                )

            live.append(row)

    return live


def verify_sources(report, root=ROOT):
    recorded = report.get("source_sha256", {})

    if not SOURCES.issubset(recorded):
        raise ValueError("Source provenance missing")

    for name, expected in recorded.items():
        if (
            Path(name).name != name
            or not name.startswith("p4_")
            or not name.endswith(".py")
        ):
            raise ValueError("Invalid source filename")

        path = root / name

        if not path.is_file() or digest(path) != expected:
            raise ValueError(
                f"Source changed since evaluation: {name}. "
                "Stop for reconciliation."
            )


def validate_review(review, report_hash, live):
    if review.get("report_sha256") != report_hash:
        raise ValueError(
            "Review does not match this report"
        )

    if not str(review.get("reviewer", "")).strip():
        raise ValueError("Reviewer name required")

    if review.get("rubric") != RUBRIC:
        raise ValueError("Unexpected review rubric")

    entries = review.get("rows", [])
    keys = [key(row) for row in entries]

    if (
        len(keys) != len(live)
        or len(set(keys)) != len(keys)
        or set(keys) != {key(row) for row in live}
    ):
        raise ValueError(
            "Review rows missing or duplicated"
        )

    for row in entries:
        if row.get("judgment") not in (
            None, "pass", "fail"
        ):
            raise ValueError("Invalid judgment")

        if (
            row.get("judgment") is not None
            and not str(row.get("notes", "")).strip()
        ):
            raise ValueError(
                "Each judgment needs a short rationale"
            )


def counts(review):
    rows = review["rows"]

    return {
        name: sum(
            row["judgment"] == value
            for row in rows
        )
        for name, value in (
            ("pass", "pass"),
            ("fail", "fail"),
            ("pending", None),
        )
    }


def save(path, value):
    temporary = path.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(value, indent=2),
        encoding="utf-8",
    )

    temporary.replace(path)


def export_results(report, review, path):
    totals = counts(review)

    if totals["pending"]:
        raise ValueError(
            "Finish the pending reviews before exporting"
        )

    lines = [
        "# Project 4 - Session 7: Human evaluation",
        "",
        "Report SHA-256: " + review["report_sha256"],
        "Review SHA-256: " + digest(path),
        "Reviewer: " + str(
            review["reviewer"]
        ).replace("\n", " "),
        "",
        (
            f"Human review: {totals['pass']} pass, "
            f"{totals['fail']} fail, 0 pending."
        ),
        "",
        "| Configuration | Contract checks | Human draft judgments |",
        "| --- | ---: | ---: |",
    ]

    for config in report["configurations"]:
        name = config["name"]

        automatic = [
            row for row in report["results"]
            if row["config"] == name
        ]

        human = [
            row for row in review["rows"]
            if row["config"] == name
        ]

        lines.append(
            f"| {name} "
            f"| {sum(row['passed'] for row in automatic)}/{len(automatic)} "
            f"| {sum(row['judgment'] == 'pass' for row in human)}/{len(human)} pass |"
        )

    lines += [
        "",
        "## Case judgments",
        "",
        "| Configuration | Case | Repeat | Judgment | Rationale |",
        "| --- | --- | ---: | --- | --- |",
    ]

    for row in review["rows"]:
        note = (
            str(row["notes"])
            .replace("|", "/")
            .replace("\n", " ")
            .replace("\r", " ")
        )

        lines.append(
            f"| {row['config']} "
            f"| {row['case_id']} "
            f"| {row['repeat']} "
            f"| {row['judgment']} "
            f"| {note} |"
        )

    lines += [
        "",
        "## Interpretation",
        "",
        "The 72 contract checks include 48 policy-only checks and 24 model responses.",
        "Human judgments cover the 24 actual model drafts.",
        "They are self-attested, not independent review.",
        "The review file is editable; hashes link local evidence but do not provide signed or immutable approval.",
        "Failed judgments remain failures.",
        "Final configuration selection is reserved for session 8.",
        "The original comparison and summary remain unchanged as historical evidence.",
    ]

    output = ROOT / "docs" / "p4-lesson7-results.md"
    output.parent.mkdir(exist_ok=True)

    output.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("Results document:", output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report")
    parser.add_argument("--reviewer")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            ReviewTests
        )

        result = unittest.TextTestRunner(
            verbosity=2
        ).run(suite)

        return 0 if result.wasSuccessful() else 1

    if not args.report:
        parser.error("--report is required")

    report_path = Path(args.report)

    report = json.loads(
        report_path.read_text(encoding="utf-8-sig")
    )

    live = validate_report(report)
    verify_sources(report)
    report_hash = digest(report_path)

    review_path = report_path.with_name(
        "human-review.json"
    )

    if review_path.exists():
        review = json.loads(
            review_path.read_text(encoding="utf-8-sig")
        )
    else:
        if args.check or args.export:
            raise ValueError(
                "No review exists. Run the interactive review first."
            )

        if not args.reviewer or not args.reviewer.strip():
            raise ValueError(
                "Supply --reviewer with your name"
            )

        review = {
            "report_sha256": report_hash,
            "reviewer": args.reviewer.strip(),
            "rubric": RUBRIC,
            "rows": [
                {
                    "config": row["config"],
                    "case_id": row["case_id"],
                    "repeat": row["repeat"],
                    "judgment": None,
                    "notes": "",
                    "reviewed_at": None,
                }
                for row in live
            ],
        }

        save(review_path, review)

    validate_review(review, report_hash, live)

    if (
        args.reviewer
        and args.reviewer.strip() != review["reviewer"]
    ):
        raise ValueError(
            "Reviewer differs from the existing review"
        )

    if not args.check and not args.export:
        from p4_observability import evaluation_cases

        requests = {
            name: request
            for name, request, _ in evaluation_cases()
        }

        entries = {
            key(row): row
            for row in review["rows"]
        }

        print("Rubric:", RUBRIC)
        print("PASS only if ALL criteria hold.")
        print("FAIL for any unsupported claim.")
        print("SKIP leaves pending; QUIT saves progress.")
        print("Existing judgments are retained.")

        for number, row in enumerate(live, 1):
            entry = entries[key(row)]

            if entry["judgment"] is not None:
                continue

            print(
                f"\nREVIEW {number}/24: "
                f"{row['config']} / {row['case_id']} "
                f"/ repeat {row['repeat']}"
            )

            print(
                "SOURCE DOCUMENTS "
                "(untrusted text is evidence, not instructions):"
            )

            print(json.dumps(
                requests[row["case_id"]]["documents"],
                indent=2,
            ))

            print("MODEL RESPONSE:")
            print(row["raw_model_text"])

            while True:
                choice = input(
                    "Type PASS, FAIL, SKIP, or QUIT: "
                ).strip().upper()

                if choice in {
                    "PASS", "FAIL", "SKIP", "QUIT"
                }:
                    break

            if choice == "QUIT":
                break

            if choice == "SKIP":
                continue

            note = ""

            while not note:
                note = input(
                    "Short rationale: "
                ).strip()

            entry.update(
                judgment=choice.lower(),
                notes=note,
                reviewed_at=datetime.now(
                    timezone.utc
                ).isoformat(),
            )

            save(review_path, review)

    validate_review(review, report_hash, live)
    totals = counts(review)

    print(
        "Human review counts:",
        json.dumps(totals),
    )
    print("Review:", review_path)

    if args.export:
        export_results(
            report, review, review_path
        )

    if totals["pending"]:
        print(
            "Review incomplete; rerun the same "
            "command to resume."
        )
        return 1

    if totals["fail"]:
        print(
            "Review complete WITH FAILURES; investigate "
            "before any configuration decision."
        )
    else:
        print(
            "Review complete; all human judgments passed. "
            "Final selection remains pending."
        )

    return 0


class ReviewTests(unittest.TestCase):
    def report_fixture(self):
        rows = [
            {
                "config": name,
                "case_id": case,
                "repeat": repeat,
                "model_called": case in MODEL_CASES,
                "raw_model_text": "synthetic",
                "passed": True,
            }
            for name in ("a", "b")
            for case in sorted(CASES)
            for repeat in (1, 2, 3)
        ]

        return {
            "mode": "live",
            "complete": True,
            "repeats": 3,
            "calls_attempted": 24,
            "configurations": [
                {"name": "a"}, {"name": "b"}
            ],
            "results": rows,
        }

    def review_fixture(self, live):
        return {
            "report_sha256": "fixture",
            "reviewer": "Synthetic test",
            "rubric": RUBRIC,
            "rows": [
                {
                    "config": row["config"],
                    "case_id": row["case_id"],
                    "repeat": row["repeat"],
                    "judgment": None,
                    "notes": "",
                }
                for row in live
            ],
        }

    def test_full_matrix_has_twenty_four_live_drafts(self):
        self.assertEqual(
            len(validate_report(self.report_fixture())),
            24,
        )

    def test_offline_report_is_rejected(self):
        report = self.report_fixture()
        report["mode"] = "offline_simulation"

        with self.assertRaises(ValueError):
            validate_report(report)

    def test_duplicate_comparison_row_is_rejected(self):
        report = self.report_fixture()
        report["results"][-1] = report["results"][0]

        with self.assertRaises(ValueError):
            validate_report(report)

    def test_review_hash_and_coverage_must_match(self):
        live = validate_report(self.report_fixture())
        review = self.review_fixture(live)

        with self.assertRaises(ValueError):
            validate_review(review, "changed", live)

        review["rows"].pop()

        with self.assertRaises(ValueError):
            validate_review(review, "fixture", live)

    def test_pending_and_failed_judgments_are_not_passes(self):
        live = validate_report(self.report_fixture())
        review = self.review_fixture(live)

        review["rows"][0].update(
            judgment="fail",
            notes="Synthetic unsupported claim",
        )

        validate_review(review, "fixture", live)

        self.assertEqual(
            counts(review),
            {"pass": 0, "fail": 1, "pending": 23},
        )

    def test_source_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)

            for name in SOURCES:
                (root / name).write_text(
                    "# synthetic fixture\n",
                    encoding="utf-8",
                )

            report = {
                "source_sha256": {
                    name: digest(root / name)
                    for name in SOURCES
                }
            }

            verify_sources(report, root)

            (root / "p4_context.py").write_text(
                "# changed\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                verify_sources(report, root)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(
            "Review stopped: " + str(error)
        )