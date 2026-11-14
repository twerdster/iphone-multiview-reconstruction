import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("evaluate_tum", Path(__file__).parents[1] / "tools/evaluate_tum.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_known_similarity_and_no_reflection():
    rng = np.random.default_rng(91)
    points = rng.normal(size=(30, 3))
    rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
    reference = 2.7 * points @ rotation.T + [1., -3., 2.]
    scale, recovered, translation = evaluation.align_similarity(points, reference)
    np.testing.assert_allclose(scale, 2.7)
    np.testing.assert_allclose(recovered, rotation, atol=1e-12)
    np.testing.assert_allclose(translation, [1., -3., 2.], atol=1e-12)
    assert np.linalg.det(recovered) > 0


def test_interpolation_rejects_missing_and_large_gap():
    ground_truth = [[1., 0., 0., 0.], [1.01, 1., 2., 3.], [1.20, 3., 4., 5.]]
    indices, centers = evaluation.reference_centers([0.9, 1., 1.005, 1.15, 1.20, 1.3], ground_truth)
    assert indices == [1, 2, 4]
    np.testing.assert_allclose(centers, [[0, 0, 0], [.5, 1, 1.5], [3, 4, 5]])


@pytest.mark.parametrize("points", [np.zeros((4, 3)), np.arange(12.).reshape(4, 3), np.full((4, 3), np.nan)])
def test_invalid_paths_are_rejected(points):
    with pytest.raises(ValueError):
        evaluation.align_similarity(points, points)


def test_unsorted_reference_is_rejected():
    with pytest.raises(ValueError):
        evaluation.reference_centers([1.1], [[1.2, 0, 0, 0], [1., 1, 1, 1]])
