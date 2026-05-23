from types import SimpleNamespace

from django.test import SimpleTestCase

from api.data.prepare_datasets import has_invalid_loudness as normalized_has_invalid_loudness
from api.data.remove_duplicates import has_invalid_loudness as dedup_has_invalid_loudness
from api.views import (
    PRIMARY_FEATURE_WEIGHT,
    SECONDARY_FEATURE_WEIGHT,
    RecommendationView,
)


class DatasetLoudnessFilteringTests(SimpleTestCase):
    def test_prepare_datasets_flags_extreme_loudness_values(self):
        loudness_idx = 11
        row = [""] * 20
        row[loudness_idx] = "-100000"

        self.assertTrue(normalized_has_invalid_loudness(row))

        row[loudness_idx] = "-99999.999"
        self.assertFalse(normalized_has_invalid_loudness(row))

    def test_remove_duplicates_flags_extreme_loudness_values(self):
        self.assertTrue(dedup_has_invalid_loudness({"loudness": "-100001"}))
        self.assertFalse(dedup_has_invalid_loudness({"loudness": "-42"}))


class RecommendationStrategySelectionTests(SimpleTestCase):
    def setUp(self):
        self.view = RecommendationView()
        self.ref_track = SimpleNamespace(
            danceability=0.8,
            energy=0.9,
            valence=0.7,
        )

    def test_greatest_variation_selects_two_largest_std_deviation_features(self):
        metas = [
            SimpleNamespace(feature="danceability", median=0.5, std_deviation=0.2),
            SimpleNamespace(feature="energy", median=0.4, std_deviation=0.5),
            SimpleNamespace(feature="valence", median=0.3, std_deviation=0.3),
        ]

        selected = self.view._select_greatest_variation_feature(self.ref_track, metas)

        self.assertEqual([feature["feature"] for feature in selected["features"]], ["energy", "valence"])
        self.assertEqual(selected["features"][0]["weight"], PRIMARY_FEATURE_WEIGHT)
        self.assertEqual(selected["features"][1]["weight"], SECONDARY_FEATURE_WEIGHT)
        self.assertEqual(selected["feature"], "energy")

    def test_distance_from_cluster_median_vector_uses_all_available_features(self):
        median_map = {
            "danceability": 0.6,
            "energy": 0.5,
            "loudness": -10.0,
            "tempo": 120.0,
            "valence": 0.4,
            "acousticness": 0.3,
            "instrumentalness": 0.1,
            "liveness": 0.2,
            "speechiness": 0.05,
        }
        track = SimpleNamespace(
            danceability=0.8,
            energy=0.9,
            loudness=-8.0,
            tempo=124.0,
            valence=0.7,
            acousticness=0.4,
            instrumentalness=0.3,
            liveness=0.5,
            speechiness=0.08,
        )

        vector = self.view._build_distance_from_cluster_median_vector(track, median_map)

        self.assertAlmostEqual(vector["danceability"], 0.2)
        self.assertAlmostEqual(vector["tempo"], 4.0)
        self.assertAlmostEqual(vector["speechiness"], 0.03)

    def test_furthest_from_median_selects_two_largest_standardized_distances(self):
        metas = [
            SimpleNamespace(feature="danceability", median=0.7, std_deviation=0.1),
            SimpleNamespace(feature="energy", median=0.3, std_deviation=0.2),
            SimpleNamespace(feature="valence", median=0.6, std_deviation=0.5),
        ]

        selected = self.view._select_furthest_from_median_feature(self.ref_track, metas)

        self.assertEqual([feature["feature"] for feature in selected["features"]], ["energy", "danceability"])
        self.assertEqual(selected["features"][0]["weight"], PRIMARY_FEATURE_WEIGHT)
        self.assertEqual(selected["features"][1]["weight"], SECONDARY_FEATURE_WEIGHT)
        self.assertEqual(selected["feature"], "energy")
