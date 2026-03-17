"""Search domain client."""

from __future__ import annotations

from pydantic import TypeAdapter

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.models.search import (
    GlobalSearchRequest,
    GlobalSearchResponse,
    MetamodelFilter,
    SearchKeyword,
    UserForAutocomplete,
)


class SearchDomain:
    """Methods for searching people and autocompleting names."""

    def __init__(self, http: HttpHelper) -> None:
        self._http = http

    # pylint: disable=too-many-arguments
    async def find_people(
        self,
        keywords: list[str],
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        filters: list[MetamodelFilter] | None = None,
        use_text_search: bool = False,
        resource_request_id: int | None = None,
    ) -> GlobalSearchResponse:
        """Search for people by skills/keywords."""
        request = GlobalSearchRequest(
            keywords=[SearchKeyword(keyword=k) for k in keywords],
            startDate=start_date,
            endDate=end_date,
            metamodelFilters=filters or [],
            useTextSearch=use_text_search,
            resourceRequestID=resource_request_id,
        )
        data = request.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._http.post("/api/Search/GlobalSearch", data=data)
        return GlobalSearchResponse.model_validate_json(response_text)

    async def autocomplete_user(self, pattern: str) -> list[UserForAutocomplete]:
        """Autocomplete user names by pattern."""
        response_text = await self._http.get(
            "/api/Search/GetSearchUsersForAutocomplete", params={"pattern": pattern}
        )
        adapter = TypeAdapter(list[UserForAutocomplete])
        return adapter.validate_json(response_text)

    async def get_filter_fields(self) -> str:
        """Get valid filter field definitions for use in find_people() metamodelFilters."""
        return await self._http.get("/api/UiView/GlobalSearchFilter")
