import contextlib
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from p4_observability import run_comparison, verified_summary
from p4_review import digest
from tower.release_record import CONFIGURATIONS, load, main, manifest, packet, write


class ReleaseRecordTests(unittest.TestCase):
    def test_live_holdout_binds_review_and_scan(self):
        client = Mock()

        def converse(**kwargs):
            source = json.loads(kwargs["messages"][0]["content"][0]["text"])["documents"][0]
            draft = {
                "status": "answered", "action": "propose_review",
                "applicability": "needs_review", "facts": source["facts"],
                "citations": [source["id"]], "summary": verified_summary(source["facts"]),
            }
            return {"output": {"message": {"content": [{"text": json.dumps(draft)}]}},
                    "usage": {"inputTokens": 100, "outputTokens": 100}, "stopReason": "end_turn"}

        client.converse.side_effect = converse
        configs = [dict(name=name, temperature=value, model_id="fake-model",
                        input_price=0.06, output_price=0.24)
                   for name, value in CONFIGURATIONS.items()]
        image = "sha256:" + "a" * 64
        now = datetime.now(timezone.utc)
        with TemporaryDirectory() as temp:
            root = Path(temp)
            with contextlib.redirect_stdout(StringIO()):
                run_comparison(configs, 1, client, 1, root / "run", holdout=True, release_id=image)
            self.assertEqual(client.converse.call_count, 4)
            report = root / "run/comparison.json"
            reviewer_packet = packet(report, "Owner")
            reviewer_packet["reviewer"] = "Second reviewer"
            for row in reviewer_packet["rows"]:
                row.update(judgment="pass", source_id="EV-001",
                           rationale="Fixture source supports the stated exposure and criticality.")
            review = root / "review.json"
            write(review, reviewer_packet)
            scan = root / "scan.json"
            write(scan, {"CreatedAt": now.isoformat(), "ArtifactType": "container_image",
                         "Metadata": {"ImageID": image},
                         "Results": [{"Class": "os-pkgs"}, {"Class": "lang-pkgs"}]})
            result = manifest(report, review, scan, image, "Owner", now)
            self.assertTrue(all(result["gates"].values()), result)
            with self.assertRaisesRegex(ValueError, "Image ID differs"):
                manifest(report, review, scan, "sha256:" + "b" * 64, "Owner", now)

            manifest_path = root / "manifest.json"
            write(manifest_path, result)
            for decision, expected in (("approve", 0), ("reject", 1)):
                approval = root / f"{decision}.json"
                output = root / f"{decision}-record.json"
                write(approval, {"approver": "Release reviewer", "decision": decision,
                                 "manifest_sha256": digest(manifest_path)})
                args = ["release_record", "finalize", "--report", str(report), "--owner", "Owner",
                        "--review", str(review), "--scan", str(scan), "--image-id", image,
                        "--manifest", str(manifest_path), "--approval", str(approval), "--output", str(output)]
                with patch("sys.argv", args):
                    self.assertEqual(main(), expected)
                self.assertFalse(load(output)["production_authorized"])
