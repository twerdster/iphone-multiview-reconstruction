import numpy as np
import pycolmap
import pytest

from multiview.reconstruction import camera_cv, write_ply


def test_colmap_radial_camera_matches_opencv_projection():
    import cv2
    camera = pycolmap.Camera(model="SIMPLE_RADIAL", width=640, height=480, params=[500., 320., 240., .08])
    points = np.array([[.1, .2, 1.], [-.3, .1, 2.], [.5, -.4, 3.]])
    k, distortion = camera_cv(camera, 1.)
    actual = cv2.projectPoints(points, np.zeros(3), np.zeros(3), k, distortion)[0][:, 0]
    assert np.max(np.abs(actual-camera.img_from_cam(points))) < 1e-9
    scaled, _ = camera_cv(camera, .5)
    assert scaled[0, 0] == 250 and scaled[2, 2] == 1


def test_ply_preserves_finite_geometry_and_colors(tmp_path):
    path = tmp_path / "cloud.ply"
    write_ply(path, [[1.25, 2.5, -3.]], [[10, 20, 255]])
    assert "element vertex 1" in path.read_text()
    assert path.read_text().splitlines()[-1] == "1.25 2.5 -3 10 20 255"


def test_nonfinite_geometry_rejected(tmp_path):
    with pytest.raises(ValueError, match="Non-finite"):
        write_ply(tmp_path / "cloud.ply", [[np.nan, 0, 1]], [[0, 0, 0]])


def test_stereo_rectification_world_transform_round_trip():
    import cv2
    from multiview.reconstruction import rectified_to_world
    rotation = cv2.Rodrigues(np.array([.2, -.1, .3]))[0]
    rectification = cv2.Rodrigues(np.array([-.1, .04, .02]))[0]
    translation = np.array([.5, -.2, .8])
    world = np.array([[1., 2., 5.], [-.2, .5, 3.]])
    rectified = (world @ rotation.T + translation) @ rectification.T
    assert np.max(np.abs(rectified_to_world(rectified, rectification, rotation, translation)-world)) < 1e-12


def test_rectification_axis_is_checked_from_projection():
    import cv2
    from multiview.reconstruction import horizontal_positive_disparity
    k = np.array([[500., 0, 320], [0, 500, 240], [0, 0, 1]])
    _, _, _, projection, _, _, _ = cv2.stereoRectify(k, np.zeros(5), k, np.zeros(5),
        (640, 480), np.eye(3), np.array([-.3, -.3, 0.]), alpha=0)
    assert not horizontal_positive_disparity(projection)
    _, _, _, projection, _, _, _ = cv2.stereoRectify(k, np.zeros(5), k, np.zeros(5),
        (640, 480), np.eye(3), np.array([-.3, 0., 0.]), alpha=0)
    assert horizontal_positive_disparity(projection)


def test_q_reprojection_and_world_transform_with_rotated_camera():
    import cv2
    from multiview.reconstruction import rectified_to_world
    k = np.array([[500., 0, 320], [0, 500, 240], [0, 0, 1]])
    rotation = cv2.Rodrigues(np.array([.2, -.1, .3]))[0]
    translation = np.array([.5, -.2, .8])
    relative_rotation = cv2.Rodrigues(np.array([.02, -.04, .01]))[0]
    relative_translation = np.array([-.3, .01, .005])
    rectification, _, pleft, pright, q, _, _ = cv2.stereoRectify(k, np.zeros(5), k, np.zeros(5),
        (640, 480), relative_rotation, relative_translation, alpha=0)
    world = np.array([.2, -.1, 4.])
    point = rectification @ (rotation @ world + translation)
    projected_left = pleft @ np.r_[point, 1.]
    projected_right = pright @ np.r_[point, 1.]
    left, right = projected_left[:2]/projected_left[2], projected_right[:2]/projected_right[2]
    reprojected = q @ np.array([left[0], left[1], left[0]-right[0], 1.])
    recovered = rectified_to_world(reprojected[:3]/reprojected[3], rectification, rotation, translation)
    assert np.max(np.abs(recovered-world)) < 1e-10


def test_large_strided_coordinate_array_avoids_batched_blas():
    from multiview.reconstruction import transform_rows
    rng = np.random.default_rng(44)
    points = rng.normal(size=(480, 640, 3)).astype(np.float32)[:, ::-1, :]
    matrix = np.array([[.9, -.2, .1], [.1, .8, -.3], [-.2, .1, 1.1]], dtype=np.float64, order='F')
    actual = transform_rows(points, matrix)
    expected = np.stack([sum(points[..., j].astype(np.float64)*matrix[j, k] for j in range(3)) for k in range(3)], axis=-1)
    assert actual.dtype == np.float64 and actual.shape == points.shape
    assert np.max(np.abs(actual-expected)) < 2e-15
