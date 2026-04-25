from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

BuildingId = Annotated[str, StringConstraints(pattern=r"^HAUS-\d{1,4}$")]
