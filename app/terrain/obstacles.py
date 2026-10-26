
from dataclasses import asdict, dataclass
from typing import Literal


ReviewStatus = Literal[
    "NOT_REVIEWED",
    "REVIEWED",
    "NEEDS_FOLLOW_UP",
]


@dataclass
class ObstacleNote:
    parcel_id: str
    obstacle_type: str | None = None
    review_note: str | None = None
    review_status: ReviewStatus = "NOT_REVIEWED"
    reviewer_id: str | None = None

    def to_dict(self):
        return asdict(self)


def create_obstacle_note(parcel_id: str) -> dict:
    """Create an empty human-review record.

    No obstacle is assumed or fabricated.
    """
    return ObstacleNote(
        parcel_id=parcel_id
    ).to_dict()
