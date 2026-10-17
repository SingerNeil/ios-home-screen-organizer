import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from unjiggle_rebuilt import core


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.layout = core.make_demo_layout()

    def test_demo_layout_is_analyzable(self):
        report = core.diagnose(self.layout)
        self.assertEqual(report["counts"]["apps"], 28)
        self.assertEqual(report["counts"]["pages"], 3)
        self.assertGreaterEqual(report["score"], 0)
        self.assertLessEqual(report["score"], 100)

    def test_digest_is_stable(self):
        self.assertEqual(core.digest(self.layout), core.digest(self.layout))
        self.assertNotEqual(core.digest(self.layout), core.digest({"pages": []}))

    def test_every_preset_is_non_destructive_and_compact(self):
        source = core.digest(self.layout)
        for preset in ("focus", "relax", "minimal", "beautiful"):
            value = core.plan(self.layout, preset)
            self.assertEqual(value["sourceHash"], source)
            self.assertEqual(core.digest(self.layout), source)
            self.assertLessEqual(value["after"]["counts"]["pages"], value["before"]["counts"]["pages"])
            self.assertEqual(value["sourceApps"], sorted(icon.bundle_id for icon in core.flatten_icons(value["proposed"])))

    def test_folder_payload_is_preserved_by_preview(self):
        folder = {"displayName": "Work", "listType": "folder", "iconLists": [[{"displayIdentifier": "com.example.one", "custom": 42}]]}
        layout = [[folder, {"displayIdentifier": "com.example.two", "custom": "kept"}]]
        value = core.plan(layout, "focus")
        items = [item for page in value["proposed"] for item in page]
        self.assertIn(folder, items)

    def test_backup_round_trip(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(core, "APP_SUPPORT", Path(folder)):
            record = core.backup_record({"udid": "test"}, self.layout, "unit-test")
            self.assertEqual(record["layoutHash"], core.digest(self.layout))
            self.assertEqual(core.list_backups()[0]["id"], record["id"])

    def test_plist_json_codec_preserves_binary_and_dates(self):
        value = {"when": datetime(2026, 10, 17, 9, 30, tzinfo=timezone.utc), "blob": b"\x00\xff", "pages": self.layout}
        encoded = core.to_jsonable(value)
        decoded = core.from_jsonable(encoded)
        self.assertEqual(decoded, value)
        self.assertEqual(core.digest(decoded), core.digest(value))


if __name__ == "__main__":
    unittest.main()
