import datetime as dt
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_feed
from compute import analyze
import post_text
import providers


RUN_TIME = dt.datetime(2026, 11, 23, 18, tzinfo=dt.timezone.utc)


def bars(end="2026-11-20"):
    return pd.DataFrame(
        {"Close": range(100, 112), "Volume": [1000] * 12},
        index=pd.bdate_range(end=end, periods=12),
    )


class ObservationWindowTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            **build_feed.load_config(), "window_short": 2, "window_long": 4,
            "sectors": {"XLK": "Technology", "XLF": "Financials"},
        }

    def build_with_bars(self, prices):
        with patch.object(providers.yf, "download", return_value=pd.concat(prices, axis=1)):
            return build_feed.build(self.cfg, generated_at=RUN_TIME)

    def test_full_snapshot_uses_observation_date(self):
        result = self.build_with_bars({"SPY": bars(), "XLK": bars(), "XLF": bars()})
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["data"]["as_of"], "2026-11-20")
        self.assertEqual(len(result["data"]["sectors"]), 2)

    def test_sector_missing_window_start_is_excluded_even_with_same_end_date(self):
        prices = bars()
        incomplete = prices.drop(prices.index[-3])
        result = self.build_with_bars({"SPY": prices, "XLK": prices, "XLF": incomplete})
        self.assertEqual(result["status"], "partial")
        self.assertIn("XLF", result["notes"])
        self.assertEqual([r["etf"] for r in result["data"]["sectors"]], ["XLK"])

    def test_stale_benchmark_or_provider_failure_is_unavailable(self):
        result = self.build_with_bars({"SPY": bars("2026-11-17"), "XLK": bars()})
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["data"]["as_of"])
        with patch.object(providers.yf, "download", side_effect=OSError):
            result = build_feed.build(self.cfg, generated_at=RUN_TIME)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["data"]["sectors"], [])

    def test_direction_uses_unrounded_score_and_draft_respects_directions(self):
        returns = {
            "SPY": {"ret_short": 0, "ret_long": 0},
            "XLK": {"ret_short": 0.504, "ret_long": 0.504},
            "XLF": {"ret_short": 0.1, "ret_long": 0.1},
        }
        board = analyze(returns, self.cfg["sectors"], "SPY", 0.5)
        self.assertEqual(board["sectors"][0]["flow_score"], 0.5)
        self.assertEqual(board["rotating_in"], ["Technology"])
        self.assertEqual(board["rotating_out"], [])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out"
            output.mkdir()
            (output / "sector_rotation.json").write_text(json.dumps({"data": {**board, "as_of": "2026-11-20"}}))
            with patch.object(post_text, "ROOT", root), patch("builtins.print"):
                post_text.main()
            draft = (output / "post.txt").read_text(encoding="utf-8")
            self.assertIn("Technology", draft)
            self.assertNotIn("Leaning OUT", draft)
            self.assertNotIn("Financials", draft)


if __name__ == "__main__":
    unittest.main()
