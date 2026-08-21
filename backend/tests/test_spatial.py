from app.services.spatial import cluster_coordinates

# Real-world reference points, ~tens of meters apart around a single SF block.
SF_A = {"lat": 37.7749, "lon": -122.4194}
SF_B = {"lat": 37.77495, "lon": -122.41945}  # a few meters from SF_A
SF_C = {"lat": 37.7750, "lon": -122.4195}    # a few meters from SF_A/B
NYC = {"lat": 40.7128, "lon": -74.0060}      # thousands of km away


def test_empty_input():
    result = cluster_coordinates([])
    assert result == {"clusters": [], "noise_points": []}


def test_single_point_is_noise():
    result = cluster_coordinates([SF_A])
    assert result["clusters"] == []
    assert result["noise_points"] == [SF_A]


def test_two_nearby_points_form_a_cluster():
    result = cluster_coordinates([SF_A, SF_B])
    assert len(result["clusters"]) == 1
    assert result["clusters"][0]["size"] == 2
    assert result["noise_points"] == []


def test_dense_cluster_plus_one_far_outlier():
    result = cluster_coordinates([SF_A, SF_B, SF_C, NYC])
    assert len(result["clusters"]) == 1
    assert result["clusters"][0]["size"] == 3
    assert result["clusters"][0]["percentage"] == 75.0
    assert result["noise_points"] == [NYC]


def test_two_far_apart_singletons_are_both_noise():
    result = cluster_coordinates([SF_A, NYC])
    assert result["clusters"] == []
    assert len(result["noise_points"]) == 2


def test_centroid_is_average_of_members():
    result = cluster_coordinates([SF_A, SF_B])
    centroid = result["clusters"][0]["centroid"]
    assert abs(centroid["lat"] - (SF_A["lat"] + SF_B["lat"]) / 2) < 1e-6
    assert abs(centroid["lon"] - (SF_A["lon"] + SF_B["lon"]) / 2) < 1e-6


def test_eps_threshold_respected():
    # ~111m apart (0.001 deg latitude) -- should NOT cluster at a 50m eps,
    # but SHOULD cluster once eps is widened past that distance.
    near_but_outside_default_eps = {"lat": 37.7749 + 0.001, "lon": -122.4194}

    tight = cluster_coordinates([SF_A, near_but_outside_default_eps], eps_meters=50.0)
    assert tight["clusters"] == []

    loose = cluster_coordinates([SF_A, near_but_outside_default_eps], eps_meters=200.0)
    assert len(loose["clusters"]) == 1


def test_min_samples_respected():
    # 3 tightly-packed points, but min_samples=4 means none of them has
    # enough neighbors to form a cluster.
    result = cluster_coordinates([SF_A, SF_B, SF_C], min_samples=4)
    assert result["clusters"] == []
    assert len(result["noise_points"]) == 3
