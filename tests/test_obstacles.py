
from app.terrain.obstacles import create_obstacle_note


def test_obstacle_note_unreviewed():
    note = create_obstacle_note("P003")

    assert note["parcel_id"] == "P003"
    assert note["obstacle_type"] is None
    assert note["review_note"] is None
    assert note["review_status"] == "NOT_REVIEWED"
    assert note["reviewer_id"] is None
