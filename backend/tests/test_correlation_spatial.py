from app.services.conclusion import generate_conclusion
from app.services.correlation import detect_static_landmarks


class FakeFootprint:
    def __init__(self, entries):
        self._entries = entries

    @property
    def entries(self):
        return self._entries

    @property
    def count(self):
        return len(self._entries)

    def all_coordinates(self):
        coords = []
        for e in self._entries:
            coords.extend(e["entities"].get("coordinates", []))
            if e.get("has_gps"):
                coords.append({"lat": e["metadata"]["gps_lat"], "lon": e["metadata"]["gps_lon"]})
        return coords


def _entry(gps=None, streets=None):
    metadata = {}
    has_gps = False
    if gps:
        metadata = {"gps_lat": gps[0], "gps_lon": gps[1]}
        has_gps = True
    return {
        "id": "x",
        "text": "",
        "entities": {"streets": streets or [], "coordinates": []},
        "metadata": metadata,
        "time_context": None,
        "has_gps": has_gps,
    }


def test_dense_gps_cluster_becomes_routine_exposure_landmark():
    entries = [
        _entry(gps=(37.7749, -122.4194)),
        _entry(gps=(37.77495, -122.41945)),
        _entry(gps=(37.7750, -122.4195)),
    ]
    landmarks = detect_static_landmarks(FakeFootprint(entries))

    routine = [lm for lm in landmarks if lm.get("signal") == "routine_exposure"]
    assert len(routine) == 1
    assert routine[0]["appearances"] == 3


def test_noise_points_become_one_aggregate_anomalous_disclosure_landmark():
    entries = [
        _entry(gps=(37.7749, -122.4194)),
        _entry(gps=(40.7128, -74.0060)),
        _entry(gps=(51.5074, -0.1278)),
    ]
    landmarks = detect_static_landmarks(FakeFootprint(entries))

    coord_landmarks = [lm for lm in landmarks if lm["type"] == "coordinates"]
    anomalous = [lm for lm in coord_landmarks if lm.get("signal") == "anomalous_disclosure"]
    assert len(coord_landmarks) == 1  # never one finding per noise point
    assert len(anomalous) == 1
    assert anomalous[0]["appearances"] == 3


def test_mixed_routine_and_anomalous_are_separate_findings():
    entries = [
        _entry(gps=(37.7749, -122.4194)),
        _entry(gps=(37.77495, -122.41945)),
        _entry(gps=(40.7128, -74.0060)),
    ]
    landmarks = detect_static_landmarks(FakeFootprint(entries))

    coord_landmarks = [lm for lm in landmarks if lm["type"] == "coordinates"]
    signals = {lm["signal"] for lm in coord_landmarks}
    assert signals == {"routine_exposure", "anomalous_disclosure"}


def test_street_landmark_detection_unaffected_by_spatial_change():
    entries = [_entry(streets=["Market Street"]) for _ in range(3)]
    landmarks = detect_static_landmarks(FakeFootprint(entries))

    street_landmarks = [lm for lm in landmarks if lm["type"] == "street"]
    assert len(street_landmarks) == 1
    assert street_landmarks[0]["value"] == "market street"


def test_fewer_than_two_entries_returns_empty():
    assert detect_static_landmarks(FakeFootprint([_entry(gps=(1.0, 2.0))])) == []


def test_conclusion_handles_anomalous_disclosure_landmark_without_crashing():
    landmarks = [{
        "type": "coordinates",
        "value": {"noise_count": 3},
        "appearances": 3,
        "percentage": 30.0,
        "classification": "Anomalous Disclosure (GPS)",
        "signal": "anomalous_disclosure",
    }]

    result = generate_conclusion([], [], landmarks, 0.0)

    assert "3 of your photos" in result


def test_conclusion_handles_routine_exposure_landmark_without_crashing():
    landmarks = [{
        "type": "coordinates",
        "value": {"lat": 37.7749, "lon": -122.4194},
        "appearances": 3,
        "percentage": 75.0,
        "classification": "Routine Exposure (GPS)",
        "signal": "routine_exposure",
    }]

    result = generate_conclusion([], [], landmarks, 0.0)

    assert "37.7749" in result
