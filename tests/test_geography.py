import pytest

from cordon.features.geography import classify_zone

CRZ = {161, 230}


@pytest.mark.parametrize(
    ("location_id", "borough", "distance_km", "expected"),
    [
        (161, "Manhattan", 0.0, "crz"),  # listed CRZ zone wins over everything
        (138, "Queens", 7.4, "excluded"),  # LaGuardia airport
        (142, "Manhattan", 0.5, "border_ring"),
        (33, "Brooklyn", 2.99, "border_ring"),
        (24, "Manhattan", 3.9, "upper_manhattan_bronx"),
        (18, "Bronx", 13.3, "upper_manhattan_bronx"),  # Bronx is never a far control
        (7, "Queens", 3.3, "intermediate"),
        (26, "Brooklyn", 8.0, "intermediate"),  # 8 km boundary is inclusive
        (14, "Brooklyn", 8.01, "far_control"),
        (5, "Staten Island", 22.1, "far_control"),
    ],
)
def test_classify_zone_follows_preregistered_order(
    location_id: int, borough: str, distance_km: float, expected: str
) -> None:
    assert classify_zone(location_id, borough, distance_km, CRZ) == expected
