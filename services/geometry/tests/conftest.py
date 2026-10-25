from collections.abc import Iterator

import pytest

from partwright_geometry import LocalGeometry


@pytest.fixture(scope="session")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()
