from typing import Annotated

from fastapi import Depends, Query

from app.constants import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX
from app.services.geocoding import Geocoder, get_geocoder
from app.services.storage import ImageStorage, get_storage

GeocoderDep = Annotated[Geocoder, Depends(get_geocoder)]
StorageDep = Annotated[ImageStorage, Depends(get_storage)]


class Page:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_DEFAULT,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PageDep = Annotated[Page, Depends()]
