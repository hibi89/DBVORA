"""Pure PostgreSQL metadata optimization review must never execute changes."""
import unittest
from dbvora.optimization_review import review_statistics, ReviewError


def sample(*, live=4000, dead=2000, heap=10 * 1024**2,
           indexes=40 * 1024**2):
    return {"status": "observed", "estimated_live_rows": live,
            "estimated_dead_rows": dead, "heap_bytes": heap,
            "index_bytes": indexes,
            "row_count_provenance": "pg_stat_user_tables_estimate_not_exact",
            "storage_provenance": "pg_relation_size_and_pg_indexes_size"}


class OptimizationReviewTests(unittest.TestCase):
    def test_estimated_dead_row_review_only(self):
        report = review_statistics(sample(indexes=4096))
        self.assertEqual([item["code"] for item in report["rules"]],
                         ["REVIEW_ESTIMATED_DEAD_ROWS"])
        self.assertFalse(report["automatic_actions"])
        self.assertFalse(report["recoverable_bytes_claimed"])

    def test_high_index_share_review_only(self):
        report = review_statistics(sample(live=40000, dead=0, heap=5 * 1024**2))
        self.assertEqual([item["code"] for item in report["rules"]],
                         ["REVIEW_INDEX_ALLOCATION"])

    def test_both_rules_preserve_fixed_evidence(self):
        report = review_statistics(sample())
        self.assertEqual(len(report["rules"]), 2)
        self.assertEqual([item["severity"] for item in report["rules"]],
                         ["review_only", "review_only"])
        self.assertNotIn("sql", repr(report).lower())

    def test_no_statistics_never_fabricates_a_recommendation(self):
        self.assertEqual(review_statistics(None)["status"], "not_collected")
        self.assertEqual(review_statistics(None)["rules"], [])
        for reason in ("pg_statistics_unavailable", "relation_not_in_statistics_view"):
            report = review_statistics({"status": "unavailable", "reason": reason})
            self.assertEqual(report["status"], "unavailable")
            self.assertFalse(report["rules"])

    def test_threshold_below_cutoff_no_recommendation(self):
        for data in (sample(live=4000, dead=999, indexes=4096),
                     sample(live=4001, dead=1000, indexes=4096),
                     sample(live=0, dead=0, indexes=1),
                     sample(live=0, dead=0, heap=1, indexes=33 * 1024**2)):
            with self.subTest(data=data):
                output = review_statistics(data)
                if data["index_bytes"] == 33 * 1024**2:
                    self.assertIn("REVIEW_INDEX_ALLOCATION",
                                  [x["code"] for x in output["rules"]])
                else:
                    self.assertEqual(output["rules"], [])

    def test_boolean_and_negative_metrics_fail_closed(self):
        for field in ("estimated_live_rows", "estimated_dead_rows",
                      "heap_bytes", "index_bytes"):
            for value in (True, -1, 2**63):
                row = sample()
                row[field] = value
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ReviewError, "INVALID_STATISTICS"):
                        review_statistics(row)

    def test_nonstandard_metadata_cannot_be_echoed(self):
        row = sample()
        row["credentials"] = "PASSWORD_LEAK"
        with self.assertRaisesRegex(ReviewError, "INVALID_STATISTICS"):
            review_statistics(row)

    def test_unknown_status_or_reason_fail_closed(self):
        for info in ({"status": "signed"}, {"status": "unavailable",
                     "reason": "password=secret"}, []):
            with self.assertRaisesRegex(ReviewError, "INVALID_STATISTICS"):
                review_statistics(info)


if __name__ == "__main__":
    unittest.main()
