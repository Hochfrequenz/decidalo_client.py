"""Async HTTP client for the Decidalo Import API."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

import aiohttp
from pydantic import TypeAdapter

from decidalo_client.exceptions import (
    DecidaloAPIError,
    DecidaloAuthenticationError,
)
from decidalo_client.models import (
    AbsenceImportResult,
    AbsenceOutputResult,
    ActivityTypeImportItem,
    ActivityTypeResult,
    AuthorizationRoleOutput,
    BatchImportMetadata,
    BookingBatchInput,
    BookingCommentBatchInput,
    BookingCommentImportResult,
    BookingExtendOption,
    BookingImportResult,
    BookingItemOutput,
    CompanyCompleteOutput,
    CustomProperty,
    EmployeeTypeOutput,
    GeneralActivityImportItem,
    GeneralActivityResult,
    GetImportUserWorkingProfileResult,
    HolidayCalendarImportResult,
    HolidayCalendarOutput,
    ImportAbsencesCommand,
    ImportBatchStatusType,
    ImportCompanyCommand,
    ImportCompanyResult,
    ImportHolidayCalendarsCommand,
    ImportPlanningGranularity,
    ImportResourceRequestCommandResult,
    ImportRoleResult,
    ImportUserHolidayCalendarsCommand,
    ImportUserWorkingProfileResult,
    ImportWorkPackageCommandResult,
    OrderImportBatch,
    OrderImportBatchResult,
    OrderImportOutput,
    OrderImportOutputBatch,
    OrderPositionImportBatch,
    OrderPositionImportBatchResult,
    OrderPositionImportOutput,
    OrderPositionRecordingTargetImportBatch,
    OrderPositionRecordingTargetImportBatchResult,
    OrderPositionRecordingTargetOutput,
    OrderPositionRecordingTypeRateImportBatch,
    OrderPositionRecordingTypeRateImportBatchResult,
    OrderPositionRecordingTypeRateOutput,
    OrderPositionWorkPackageImportBatch,
    OrderPositionWorkPackageImportBatchResult,
    OrderPositionWorkPackageOutput,
    ProjectBatchInput,
    ProjectCommentBatchInput,
    ProjectCommentImportResult,
    ProjectContactsExportOutput,
    ProjectRecordingTargetImportBatch,
    ProjectRecordingTargetImportBatchResult,
    ProjectRecordingTargetOutput,
    ProjectReferenceImportResult,
    ProjectReferenceInput,
    ProjectReferenceOutput,
    ProjectTeamMembersExportOutput,
    RateImportItem,
    RateResult,
    RecordingEntryImportItem,
    RecordingEntryImportReadItem,
    RecordingEntryImportResult,
    RecordingTargetOutput,
    RecordingTypeImportItem,
    RecordingTypeResult,
    ResourceRequestContactOutput,
    ResourceRequestInput,
    ResourceRequestOutput,
    RoleImportInput,
    ServiceCategory,
    TeamBatchInput,
    TeamImportAcceptedResponse,
    TeamImportResults,
    TeamOverview,
    TimeRecordingEntryStatus,
    TimeRecordingImportBatch,
    TimeRecordingImportOutputBatch,
    TimeRecordingImportResult,
    UserBatchImportMetadata,
    UserBatchInput,
    UserHolidayCalendarImportResult,
    UserHolidayCalendarOutputItem,
    UserImportAcceptedResponse,
    UserImportResults,
    UserIndustryExportOutput,
    UserLanguageExportOutput,
    UserOverview,
    UserProfessionalExperienceExportOutput,
    UserPublicationExportOutput,
    UserSkillsImportInput,
    UserSkillsImportResult,
    UserSkillsOutput,
    UserTestimonialExportOutput,
    UserTrainingExportOutput,
    UserWorkingProfileInput,
    WorkPackageCandidateBatchInput,
    WorkPackageCandidateBatchResult,
    WorkPackageInput,
    WorkPackageOrderPositionImportBatch,
    WorkPackageOrderPositionImportBatchResult,
    WorkPackageOrderPositionOutput,
    WorkPackageOrderPositionRecordingTargetOutput,
    WorkPackageOutput,
    WorkPackageRecordingTargetImportBatch,
    WorkPackageRecordingTargetImportBatchResult,
    WorkPackageRecordingTargetOutput,
    WorkPackageStatus,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType

DEFAULT_BASE_URL = "https://import.decidalo.dev"


def _flatten_query(params: Mapping[str, str | list[str]] | None) -> list[tuple[str, str]] | None:
    """Flatten query parameters into key-value pairs for aiohttp.

    List values are sent as repeated keys (e.g. ?projectCode=A&projectCode=B),
    which is how the API expects array parameters.

    Args:
        params: The query parameters.

    Returns:
        The flattened key-value pairs, or None if there are no parameters.
    """
    if not params:
        return None
    return [(key, item) for key, value in params.items() for item in ([value] if isinstance(value, str) else value)]


def _format_date(value: date) -> str:
    """Format a value for a query parameter of format "date" (YYYY-MM-DD).

    Args:
        value: The date.

    Returns:
        The ISO 8601 date.

    Raises:
        TypeError: If a datetime is passed. Date parameters carry no time of day.
    """
    if isinstance(value, datetime):
        raise TypeError(f"expected a date, got a datetime: {value!r}")
    return value.isoformat()


def _format_datetime(value: datetime) -> str:
    """Format a value for a query parameter of format "date-time" (ISO 8601 with UTC offset).

    Args:
        value: The timezone-aware datetime.

    Returns:
        The ISO 8601 timestamp including the UTC offset.

    Raises:
        ValueError: If the datetime is naive. The API would interpret it in the
            local time of the server.
    """
    if value.utcoffset() is None:
        raise ValueError(f"timezone-aware datetime required, got a naive datetime: {value!r}")
    return value.isoformat()


class DecidaloClient:
    """Async client for the Decidalo Import API.

    Every public method wraps exactly one operation of the V3 Import API; the
    "API Coverage" section of the README lists which operations are covered.

    The client can be used as an async context manager to ensure proper
    cleanup of resources.

    Example:
        async with DecidaloClient(api_key="your-api-key") as client:
            users = await client.get_users()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the Decidalo client.

        Args:
            api_key: The API key for authentication.
            base_url: The base URL of the API. Defaults to https://import.decidalo.dev.
            session: An optional aiohttp ClientSession to use. If not provided,
                a new session will be created when entering the context manager.
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> DecidaloClient:
        """Enter the async context manager.

        Creates a new aiohttp session if one was not provided in the constructor.

        Returns:
            The client instance.
        """
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager.

        Closes the aiohttp session if it was created by the client.

        Args:
            exc_type: The exception type, if any.
            exc_val: The exception value, if any.
            exc_tb: The exception traceback, if any.
        """
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    def _get_headers(self) -> dict[str, str]:
        """Get the headers for API requests.

        Returns:
            A dictionary of headers including the API key authentication.
        """
        return {
            "X-Api-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
        allowed_error_statuses: set[int] | None = None,
    ) -> str:
        """Handle the API response and raise appropriate exceptions.

        Args:
            response: The aiohttp response object.
            allowed_error_statuses: HTTP status codes >= 400 that should be
                treated as a valid response and returned to the caller instead
                of raising. Used for endpoints that carry a structured body on
                error (e.g. ImportSync returns UserImportResults with HTTP 500).
                Authentication errors (401/403) are always raised.

        Returns:
            The response text if successful.

        Raises:
            DecidaloAuthenticationError: If the response status is 401 or 403.
            DecidaloAPIError: If the response status indicates any other error.
        """
        text = await response.text()

        if response.status in (401, 403):
            raise DecidaloAuthenticationError(
                status_code=response.status,
                message=text or "Authentication failed",
            )

        if allowed_error_statuses and response.status in allowed_error_statuses:
            return text

        if response.status >= 400:
            raise DecidaloAPIError(
                status_code=response.status,
                message=text or f"Request failed with status {response.status}",
            )

        return text

    async def _get(self, path: str, params: Mapping[str, str | list[str]] | None = None) -> str:
        """Make a GET request to the API.

        Args:
            path: The API path (will be appended to base_url).
            params: Optional query parameters. List values are sent as repeated keys.

        Returns:
            The response text.

        Raises:
            RuntimeError: If the client is not in a context manager.
        """
        if self._session is None:
            raise RuntimeError("Client must be used within an async context manager (async with)")

        url = f"{self._base_url}{path}"
        async with self._session.get(url, headers=self._get_headers(), params=_flatten_query(params)) as response:
            return await self._handle_response(response)

    async def _post(
        self,
        path: str,
        data: str | None = None,
        params: Mapping[str, str | list[str]] | None = None,
        allowed_error_statuses: set[int] | None = None,
    ) -> str:
        """Make a POST request to the API.

        Args:
            path: The API path (will be appended to base_url).
            data: Optional JSON string to send as the request body.
            params: Optional query parameters. List values are sent as repeated keys.
            allowed_error_statuses: HTTP status codes >= 400 that should be
                returned to the caller instead of raising (see _handle_response).

        Returns:
            The response text.

        Raises:
            RuntimeError: If the client is not in a context manager.
        """
        if self._session is None:
            raise RuntimeError("Client must be used within an async context manager (async with)")

        url = f"{self._base_url}{path}"
        async with self._session.post(
            url, headers=self._get_headers(), data=data, params=_flatten_query(params)
        ) as response:
            return await self._handle_response(response, allowed_error_statuses)

    async def _head(self, path: str, params: Mapping[str, str | list[str]] | None = None) -> int:
        """Make a HEAD request to the API.

        Args:
            path: The API path (will be appended to base_url).
            params: Optional query parameters. List values are sent as repeated keys.

        Returns:
            The response status code.

        Raises:
            RuntimeError: If the client is not in a context manager.
        """
        if self._session is None:
            raise RuntimeError("Client must be used within an async context manager (async with)")

        url = f"{self._base_url}{path}"
        async with self._session.head(url, headers=self._get_headers(), params=_flatten_query(params)) as response:
            # For HEAD requests, we don't raise on 404 - it means the resource doesn't exist
            if response.status in (401, 403):
                text = await response.text()
                raise DecidaloAuthenticationError(
                    status_code=response.status,
                    message=text or "Authentication failed",
                )
            return response.status

    # =========================================================================
    # User Methods
    # =========================================================================

    async def get_users(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        email: str | None = None,
        top: int | None = None,
        skip: int | None = None,
        country_code: str | None = None,
    ) -> list[UserOverview]:
        """Get users from the API.

        Returns all users in the system, ordered by their user ID. The returned list may be
        empty if no users match the given criteria.

        Args:
            user_id: Filter by internal user ID. If provided, employee_id, email, top and skip
                are ignored.
            employee_id: Filter by external employee ID. Ignored if user_id is provided.
            email: Filter by email address. Ignored if user_id or employee_id is provided.
            top: Maximum number of users to return (paging).
            skip: Number of users to skip (paging).
            country_code: Filter by country code (exact match, case-insensitive). Applied
                independently of user_id, employee_id and email.

        Returns:
            A list of UserOverview objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userid"] = str(user_id)
        if employee_id is not None:
            params["employeeID"] = employee_id
        if email is not None:
            params["email"] = email
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)
        if country_code is not None:
            params["countryCode"] = country_code

        response_text = await self._get("/importapi/User", params)
        adapter = TypeAdapter(list[UserOverview])
        return adapter.validate_json(response_text)

    async def import_users_sync(
        self,
        batch: UserBatchInput,
    ) -> UserImportResults:
        """Import users synchronously.

        The import is processed synchronously. The response contains the result
        for each user in the batch, including any errors.

        Args:
            batch: The batch of users to import.

        Returns:
            A UserImportResults with the batch status and per-item results.

        Note:
            Per the OpenAPI spec, ImportSync returns HTTP 500 with a structured
            UserImportResults body when one or more items fail (others may still
            have succeeded). This status is therefore treated as a valid response
            so callers can inspect the per-item results instead of getting a
            generic DecidaloAPIError.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/User/ImportSync", data, allowed_error_statuses={500})
        return UserImportResults.model_validate_json(response_text)

    async def import_users_async(
        self,
        batch: UserBatchInput,
    ) -> UserImportAcceptedResponse:
        """Import users asynchronously.

        The import is processed asynchronously. The caller can provide a callback URL
        in the batch to be notified about the completion of the import. Otherwise,
        use get_user_import_status() with the returned batch ID to poll the status.

        Args:
            batch: The batch of users to import.

        Returns:
            A UserImportAcceptedResponse with the batch ID.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/User/ImportAsync", data)
        return UserImportAcceptedResponse.model_validate_json(response_text)

    async def get_user_import_status(
        self,
        *,
        top: int | None = None,
        batch_id: UUID | None = None,
        status: ImportBatchStatusType | None = None,
        include_row_results: bool | None = None,
    ) -> list[UserBatchImportMetadata]:
        """Get data about past user imports.

        Args:
            top: Return only the most recent imports (ordered by creation date, descending).
            batch_id: Filter for a specific import batch.
            status: Filter for imports in a specific status.
            include_row_results: Whether to include the individual row results. The response
                can get very big, depending on the number of imported rows. Defaults to False.

        Returns:
            A list of UserBatchImportMetadata objects.
        """
        params: dict[str, str] = {}
        if top is not None:
            params["top"] = str(top)
        if batch_id is not None:
            params["batchid"] = str(batch_id)
        if status is not None:
            params["status"] = status.value
        if include_row_results is not None:
            params["includeRowResults"] = str(include_row_results).lower()

        response_text = await self._get("/importapi/User/ImportStatus", params)
        adapter = TypeAdapter(list[UserBatchImportMetadata])
        return adapter.validate_json(response_text)

    async def get_employee_types(self) -> list[EmployeeTypeOutput]:
        """Get all employee types. Names are returned in English.

        Returns:
            A list of EmployeeTypeOutput objects.
        """
        response_text = await self._get("/importapi/User/EmployeeTypes")
        adapter = TypeAdapter(list[EmployeeTypeOutput])
        return adapter.validate_json(response_text)

    async def get_authorization_roles(self) -> list[AuthorizationRoleOutput]:
        """Get all authorization roles.

        Use the IDs or names of the roles to reference them in other API calls.

        Returns:
            A list of AuthorizationRoleOutput objects.
        """
        response_text = await self._get("/importapi/User/AuthorizationRoles")
        adapter = TypeAdapter(list[AuthorizationRoleOutput])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Team Methods
    # =========================================================================

    async def get_teams(self) -> list[TeamOverview]:
        """Get all teams in the system.

        Returns:
            A list of TeamOverview objects.
        """
        response_text = await self._get("/importapi/Team")
        adapter = TypeAdapter(list[TeamOverview])
        return adapter.validate_json(response_text)

    async def import_teams_async(
        self,
        batch: TeamBatchInput,
    ) -> TeamImportAcceptedResponse:
        """Import teams asynchronously.

        The import is processed asynchronously. The caller can provide a callback URL
        in the batch to be notified about the completion of the import. Otherwise,
        use get_team_import_status() with the returned batch ID to poll the status.

        Args:
            batch: The batch of teams to import.

        Returns:
            A TeamImportAcceptedResponse with the batch ID.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Team/ImportAsync", data)
        return TeamImportAcceptedResponse.model_validate_json(response_text)

    async def import_teams_sync(
        self,
        batch: TeamBatchInput,
    ) -> TeamImportResults:
        """Import teams synchronously.

        The import is processed synchronously. The response contains the result
        for each team in the batch, including any errors.

        Args:
            batch: The batch of teams to import.

        Returns:
            A TeamImportResults with the batch status and per-item results.

        Note:
            Per the OpenAPI spec, ImportSync returns HTTP 500 with a structured
            TeamImportResults body when one or more items fail (others may still
            have succeeded). This status is therefore treated as a valid response
            so callers can inspect the per-item results instead of getting a
            generic DecidaloAPIError.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Team/ImportSync", data, allowed_error_statuses={500})
        return TeamImportResults.model_validate_json(response_text)

    async def get_team_import_status(
        self,
        *,
        top: int | None = None,
        batch_id: UUID | None = None,
        status: ImportBatchStatusType | None = None,
        include_row_results: bool | None = None,
    ) -> list[BatchImportMetadata]:
        """Get data about past team imports.

        Args:
            top: Return only the most recent imports (ordered by creation date, descending).
            batch_id: Filter for a specific import batch.
            status: Filter for imports in a specific status.
            include_row_results: Whether to include the individual row results. The response
                can get very big, depending on the number of imported rows. Defaults to False.

        Returns:
            A list of BatchImportMetadata objects.
        """
        params: dict[str, str] = {}
        if top is not None:
            params["top"] = str(top)
        if batch_id is not None:
            params["batchid"] = str(batch_id)
        if status is not None:
            params["status"] = status.value
        if include_row_results is not None:
            params["includeRowResults"] = str(include_row_results).lower()

        response_text = await self._get("/importapi/Team/ImportStatus", params)
        adapter = TypeAdapter(list[BatchImportMetadata])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Company Methods
    # =========================================================================

    async def get_companies(self) -> list[CompanyCompleteOutput]:
        """Get all companies in the system.

        Returns:
            A list of CompanyCompleteOutput objects.
        """
        response_text = await self._get("/importapi/Company")
        adapter = TypeAdapter(list[CompanyCompleteOutput])
        return adapter.validate_json(response_text)

    async def import_company(
        self,
        company: ImportCompanyCommand,
    ) -> ImportCompanyResult:
        """Create or update a company.

        The endpoint uses the company ID, the company code, and the company name
        to match with existing companies.

        Args:
            company: The company data to import.

        Returns:
            An ImportCompanyResult with the import status.
        """
        data = company.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Company/Import", data)
        return ImportCompanyResult.model_validate_json(response_text)

    # =========================================================================
    # Project Methods
    # =========================================================================

    async def get_project(
        self,
        *,
        project_id: int | None = None,
        project_code: str | None = None,
    ) -> ProjectReferenceOutput:
        """Get a single project from the API.

        Returns the core project data. Either project_id or project_code must be provided.
        For a quick existence check, use project_exists() instead.

        Args:
            project_id: The internal decidalo project ID.
            project_code: The external project code.

        Returns:
            A ProjectReferenceOutput object.
        """
        params: dict[str, str] = {}
        if project_id is not None:
            params["projectid"] = str(project_id)
        if project_code is not None:
            params["projectcode"] = project_code

        response_text = await self._get("/importapi/Project", params)
        return ProjectReferenceOutput.model_validate_json(response_text)

    async def get_all_projects(
        self,
        *,
        project_id: int | None = None,
        project_code: str | None = None,
        only_projects_with_project_code: bool | None = None,
        is_central_project: bool | None = None,
        company_id: int | None = None,
        company_code: str | None = None,
        country_code: str | None = None,
        business_unit_id: int | None = None,
        business_unit_name: str | None = None,
        practice_area_id: int | None = None,
        practice_area_name: str | None = None,
        legal_entity_id: int | None = None,
        legal_entity_name: str | None = None,
        service_line_id: int | None = None,
        service_line_name: str | None = None,
        delivery_model_id: int | None = None,
        delivery_model_name: str | None = None,
        start_date_before: date | None = None,
        end_date_after: date | None = None,
        created_on_or_after: datetime | None = None,
        modified_since: datetime | None = None,
        last_imported_on_or_after: datetime | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[ProjectReferenceOutput]:
        """Get all projects from the API.

        Returns the core project data for all existing projects. All filters are optional
        and AND-combined. Names are matched against the internal or translated name,
        case-insensitive.

        Args:
            project_id: Filter on a single project by its internal ID.
            project_code: Filter on a single project by its external code (an unknown code
                returns an empty list). Ignored if project_id is provided.
            only_projects_with_project_code: If True, projects without a project code are
                filtered out.
            is_central_project: True returns only central projects, False only non-central ones.
            company_id: Filter by the internal ID of the project's company.
            company_code: Filter by the external code of the project's company (every company
                with this code matches). Ignored if company_id is provided.
            country_code: Filter by country code (exact match, case-insensitive).
            business_unit_id: Filter by the internal ID of the project's business unit.
            business_unit_name: Filter by the name of the project's business unit. Ignored if
                business_unit_id is provided.
            practice_area_id: Filter by the internal ID of the project's practice area.
            practice_area_name: Filter by the name of the project's practice area. Ignored if
                practice_area_id is provided.
            legal_entity_id: Filter by the internal ID of the project's legal entity.
            legal_entity_name: Filter by the name of the project's legal entity. Ignored if
                legal_entity_id is provided.
            service_line_id: Filter by the internal ID of the project's service line.
            service_line_name: Filter by the name of the project's service line. Ignored if
                service_line_id is provided.
            delivery_model_id: Filter by the internal ID of the project's delivery model.
            delivery_model_name: Filter by the name of the project's delivery model. Ignored if
                delivery_model_id is provided.
            start_date_before: Only projects starting on or before this date. Projects without
                a start date are also returned.
            end_date_after: Only projects ending on or after this date. Projects without an end
                date are also returned.
            created_on_or_after: Only projects created on or after this point in time
                (timezone-aware).
            modified_since: Only projects last edited on or after this point in time
                (timezone-aware).
            last_imported_on_or_after: Only projects last imported on or after this point in
                time; never-imported projects are excluded (timezone-aware).
            top: Maximum number of projects to return (paging).
            skip: Number of projects to skip (paging).

        Returns:
            A list of ProjectReferenceOutput objects.
        """
        params: dict[str, str] = {}
        if project_id is not None:
            params["projectID"] = str(project_id)
        if project_code is not None:
            params["projectCode"] = project_code
        if only_projects_with_project_code is not None:
            params["onlyProjectsWithProjectCode"] = str(only_projects_with_project_code).lower()
        if is_central_project is not None:
            params["isCentralProject"] = str(is_central_project).lower()
        if company_id is not None:
            params["companyID"] = str(company_id)
        if company_code is not None:
            params["companyCode"] = company_code
        if country_code is not None:
            params["countryCode"] = country_code
        if business_unit_id is not None:
            params["businessUnitID"] = str(business_unit_id)
        if business_unit_name is not None:
            params["businessUnitName"] = business_unit_name
        if practice_area_id is not None:
            params["practiceAreaID"] = str(practice_area_id)
        if practice_area_name is not None:
            params["practiceAreaName"] = practice_area_name
        if legal_entity_id is not None:
            params["legalEntityID"] = str(legal_entity_id)
        if legal_entity_name is not None:
            params["legalEntityName"] = legal_entity_name
        if service_line_id is not None:
            params["serviceLineID"] = str(service_line_id)
        if service_line_name is not None:
            params["serviceLineName"] = service_line_name
        if delivery_model_id is not None:
            params["deliveryModelID"] = str(delivery_model_id)
        if delivery_model_name is not None:
            params["deliveryModelName"] = delivery_model_name
        if start_date_before is not None:
            params["startDateBefore"] = _format_date(start_date_before)
        if end_date_after is not None:
            params["endDateAfter"] = _format_date(end_date_after)
        if created_on_or_after is not None:
            params["createdOnOrAfter"] = _format_datetime(created_on_or_after)
        if modified_since is not None:
            params["modifiedSince"] = _format_datetime(modified_since)
        if last_imported_on_or_after is not None:
            params["lastImportedOnOrAfter"] = _format_datetime(last_imported_on_or_after)
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Project/AllProjects", params)
        adapter = TypeAdapter(list[ProjectReferenceOutput])
        return adapter.validate_json(response_text)

    async def import_project(
        self,
        project: ProjectReferenceInput,
        *,
        booking_extend_option: BookingExtendOption | None = None,
    ) -> ProjectReferenceImportResult:
        """Create or update a project.

        Args:
            project: The project data to import.
            booking_extend_option: How to handle bookings when project dates change.
                If omitted, only the project end date is updated.

        Returns:
            A ProjectReferenceImportResult with the import status.
        """
        params: dict[str, str] = {}
        if booking_extend_option is not None:
            params["bookingExtendOption"] = booking_extend_option.value

        data = project.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Project/Import", data, params=params)
        return ProjectReferenceImportResult.model_validate_json(response_text)

    async def project_exists(
        self,
        *,
        project_id: int | None = None,
        project_code: str | None = None,
    ) -> bool:
        """Check if a project exists.

        Only checks if the project exists, but does not return any project data.
        If you need the project data, use get_project() instead.

        Args:
            project_id: The internal decidalo project ID.
            project_code: The external project code.

        Returns:
            True if the project exists (HTTP 204), False if it does not (HTTP 404).

        Raises:
            DecidaloAPIError: For any other status, e.g. HTTP 400 if neither
                project_id nor project_code is given.
        """
        params: dict[str, str] = {}
        if project_id is not None:
            params["projectid"] = str(project_id)
        if project_code is not None:
            params["projectcode"] = project_code

        status = await self._head("/importapi/Project", params)
        if status == 404:
            return False
        if 200 <= status < 300:
            return True
        raise DecidaloAPIError(status_code=status, message=f"Request failed with status {status}")

    async def get_project_contacts(
        self,
        *,
        project_id: int | None = None,
        project_code: str | None = None,
        user_id: int | None = None,
        employee_id: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[ProjectContactsExportOutput]:
        """Get projects with their contacts.

        Args:
            project_id: Filter by internal project ID.
            project_code: Filter by external project code.
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of ProjectContactsExportOutput objects.
        """
        params: dict[str, str] = {}
        if project_id is not None:
            params["projectId"] = str(project_id)
        if project_code is not None:
            params["projectCode"] = project_code
        if user_id is not None:
            params["userId"] = str(user_id)
        if employee_id is not None:
            params["employeeId"] = employee_id
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Project/Contacts", params)
        adapter = TypeAdapter(list[ProjectContactsExportOutput])
        return adapter.validate_json(response_text)

    async def get_project_team_members(
        self,
        *,
        project_id: int | None = None,
        project_code: str | None = None,
        user_id: int | None = None,
        employee_id: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[ProjectTeamMembersExportOutput]:
        """Get projects with their team members.

        Args:
            project_id: Filter by internal project ID.
            project_code: Filter by external project code.
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of ProjectTeamMembersExportOutput objects.
        """
        params: dict[str, str] = {}
        if project_id is not None:
            params["projectId"] = str(project_id)
        if project_code is not None:
            params["projectCode"] = project_code
        if user_id is not None:
            params["userId"] = str(user_id)
        if employee_id is not None:
            params["employeeId"] = employee_id
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Project/TeamMembers", params)
        adapter = TypeAdapter(list[ProjectTeamMembersExportOutput])
        return adapter.validate_json(response_text)

    async def get_project_recording_targets(
        self,
        *,
        project_reference_id: int | None = None,
        project_code: str | None = None,
    ) -> list[ProjectRecordingTargetOutput]:
        """Get a project's allowed activity types (project-direct recording targets).

        Args:
            project_reference_id: Filter by internal project reference ID.
            project_code: Filter by external project code.

        Returns:
            A list of ProjectRecordingTargetOutput objects.
        """
        params: dict[str, str] = {}
        if project_reference_id is not None:
            params["projectReferenceId"] = str(project_reference_id)
        if project_code is not None:
            params["projectCode"] = project_code

        response_text = await self._get("/importapi/Project/RecordingTargets", params)
        adapter = TypeAdapter(list[ProjectRecordingTargetOutput])
        return adapter.validate_json(response_text)

    async def import_project_recording_targets(
        self,
        batch: ProjectRecordingTargetImportBatch,
    ) -> ProjectRecordingTargetImportBatchResult:
        """Create, update, or remove a project's allowed activity types.

        One row per (project, activity type).

        Args:
            batch: The recording targets to import.

        Returns:
            A ProjectRecordingTargetImportBatchResult with the import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Project/RecordingTargets", data)
        return ProjectRecordingTargetImportBatchResult.model_validate_json(response_text)

    async def import_projects(
        self,
        batch: ProjectBatchInput,
        *,
        booking_extend_option: BookingExtendOption | None = None,
    ) -> list[ProjectReferenceImportResult]:
        """Create, update, or delete a batch of projects.

        Args:
            batch: The batch of projects to import.
            booking_extend_option: How to handle bookings when project dates change.

        Returns:
            A list of ProjectReferenceImportResult objects with the per-project import status.
        """
        params: dict[str, str] = {}
        if booking_extend_option is not None:
            params["bookingExtendOption"] = booking_extend_option.value

        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Project/ImportBatch", data, params=params)
        adapter = TypeAdapter(list[ProjectReferenceImportResult])
        return adapter.validate_json(response_text)

    async def import_project_comments(
        self,
        batch: ProjectCommentBatchInput,
    ) -> list[ProjectCommentImportResult]:
        """Create, update, or delete a batch of project comments.

        The comments of a batch may belong to different projects. They are imported in order
        and independently: a failure on one comment does not abort the rest.

        Args:
            batch: The batch of project comments to import.

        Returns:
            A list of ProjectCommentImportResult objects, one per comment in the order of the batch.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Project/Comments/Batch", data)
        adapter = TypeAdapter(list[ProjectCommentImportResult])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Booking Methods
    # =========================================================================

    async def get_bookings(
        self,
        *,
        booking_id: int | None = None,
        booking_code: str | None = None,
        project_id: int | None = None,
        project_code: str | None = None,
        request_id: int | None = None,
        user_id: int | None = None,
        employee_id: str | None = None,
        users_business_unit_id: int | None = None,
        users_business_unit_name: str | None = None,
        users_practice_area_id: int | None = None,
        users_practice_area_name: str | None = None,
        users_team_id: int | None = None,
        users_team_code: str | None = None,
        users_legal_entity_id: int | None = None,
        users_legal_entity_name: str | None = None,
        start_date_before: date | None = None,
        end_date_after: date | None = None,
        created_on_or_after: datetime | None = None,
        last_updated_on_or_after: datetime | None = None,
        last_imported_on_or_after: datetime | None = None,
        planning_granularity: ImportPlanningGranularity | None = None,
        planning_start_date: date | None = None,
        planning_end_date: date | None = None,
        exclude_daily_planning: bool | None = None,
        top: int | None = None,
        skip: int | None = None,
        email: str | None = None,
    ) -> list[BookingItemOutput]:
        """Get bookings from the API.

        The booked user can be filtered by user_id, employee_id, or email, in that precedence
        order (the first one provided wins).

        Args:
            booking_id: Filter by internal booking ID. Only the booking with this ID is returned.
            booking_code: Filter by external booking code. Ignored if booking_id is provided.
            project_id: Filter by the internal ID of the project linked to the booking.
            project_code: Filter by the code of the project linked to the booking. Ignored if
                project_id is provided.
            request_id: Filter by the internal ID of the resource request linked to the booking.
            user_id: Filter by the internal ID of the booked user.
            employee_id: Filter by the external employee ID of the booked user. Ignored if
                user_id is provided.
            users_business_unit_id: Filter by the business unit of the booked user.
            users_business_unit_name: Filter by the business unit name of the booked user.
                Ignored if users_business_unit_id is provided.
            users_practice_area_id: Filter by the practice area of the booked user.
            users_practice_area_name: Filter by the practice area name of the booked user.
                Ignored if users_practice_area_id is provided.
            users_team_id: Filter by the team of the booked user.
            users_team_code: Filter by the team code of the booked user. Ignored if
                users_team_id is provided.
            users_legal_entity_id: Filter by the legal entity of the booked user.
            users_legal_entity_name: Filter by the legal entity name of the booked user
                (case-insensitive). Ignored if users_legal_entity_id is provided.
            start_date_before: Filter on the start date of the booking. Bookings without a start
                date are also returned.
            end_date_after: Filter on the end date of the booking. Bookings without an end date
                are also returned.
            created_on_or_after: Only bookings created on or after this point in time
                (timezone-aware).
            last_updated_on_or_after: Incremental-sync filter: only bookings last edited on or
                after this point in time (timezone-aware).
            last_imported_on_or_after: Incremental-sync filter: only bookings last imported on or
                after this point in time; never-imported bookings are excluded (timezone-aware).
            planning_granularity: The planning granularity to include in the response (only one
                at a time). Defaults to daily, or none if exclude_daily_planning is True.
            planning_start_date: Inclusive lower bound for the planning data. Has no effect if no
                planning is included.
            planning_end_date: Inclusive upper bound for the planning data. Has no effect if no
                planning is included.
            exclude_daily_planning: Deprecated, use planning_granularity instead. If True, daily
                planning is not included. Ignored if planning_granularity is provided.
            top: Maximum number of bookings to return (paging).
            skip: Number of bookings to skip (paging).
            email: Filter by the email address of the booked user (case-insensitive). Ignored if
                user_id or employee_id is provided. An unknown or ambiguous email yields HTTP 400.

        Returns:
            A list of BookingItemOutput objects.
        """
        params: dict[str, str] = {}
        if booking_id is not None:
            params["BookingID"] = str(booking_id)
        if booking_code is not None:
            params["BookingCode"] = booking_code
        if project_id is not None:
            params["ProjectID"] = str(project_id)
        if project_code is not None:
            params["ProjectCode"] = project_code
        if request_id is not None:
            params["RequestID"] = str(request_id)
        if user_id is not None:
            params["UserID"] = str(user_id)
        if employee_id is not None:
            params["EmployeeID"] = employee_id
        if users_business_unit_id is not None:
            params["UsersBusinessUnitID"] = str(users_business_unit_id)
        if users_business_unit_name is not None:
            params["UsersBusinessUnitName"] = users_business_unit_name
        if users_practice_area_id is not None:
            params["UsersPracticeAreaID"] = str(users_practice_area_id)
        if users_practice_area_name is not None:
            params["UsersPracticeAreaName"] = users_practice_area_name
        if users_team_id is not None:
            params["UsersTeamID"] = str(users_team_id)
        if users_team_code is not None:
            params["UsersTeamCode"] = users_team_code
        if users_legal_entity_id is not None:
            params["UsersLegalEntityID"] = str(users_legal_entity_id)
        if users_legal_entity_name is not None:
            params["UsersLegalEntityName"] = users_legal_entity_name
        if start_date_before is not None:
            params["StartDateBefore"] = _format_date(start_date_before)
        if end_date_after is not None:
            params["EndDateAfter"] = _format_date(end_date_after)
        if created_on_or_after is not None:
            params["CreatedOnOrAfter"] = _format_datetime(created_on_or_after)
        if last_updated_on_or_after is not None:
            params["LastUpdatedOnOrAfter"] = _format_datetime(last_updated_on_or_after)
        if last_imported_on_or_after is not None:
            params["LastImportedOnOrAfter"] = _format_datetime(last_imported_on_or_after)
        if planning_granularity is not None:
            params["PlanningGranularity"] = planning_granularity.value
        if planning_start_date is not None:
            params["PlanningStartDate"] = _format_date(planning_start_date)
        if planning_end_date is not None:
            params["PlanningEndDate"] = _format_date(planning_end_date)
        if exclude_daily_planning is not None:
            params["ExcludeDailyPlanning"] = str(exclude_daily_planning).lower()
        if top is not None:
            params["Top"] = str(top)
        if skip is not None:
            params["Skip"] = str(skip)
        if email is not None:
            params["Email"] = email

        response_text = await self._get("/importapi/Booking", params)
        adapter = TypeAdapter(list[BookingItemOutput])
        return adapter.validate_json(response_text)

    async def get_bookings_by_project(
        self,
        *,
        project_id: int | None = None,
        project_code: str | None = None,
    ) -> list[BookingItemOutput]:
        """Get bookings for a specific project.

        Args:
            project_id: The internal project ID.
            project_code: The external project code.

        Returns:
            A list of BookingItemOutput objects.
        """
        params: dict[str, str] = {}
        if project_id is not None:
            params["projectId"] = str(project_id)
        if project_code is not None:
            params["projectCode"] = project_code

        response_text = await self._get("/importapi/Booking/ByProject", params)
        adapter = TypeAdapter(list[BookingItemOutput])
        return adapter.validate_json(response_text)

    async def import_bookings_async(
        self,
        batch: BookingBatchInput,
    ) -> list[BookingImportResult]:
        """Import a batch of bookings.

        When the booking type property is not set, it won't be changed through the import.
        The default value on creation is 'Reservation'.

        Args:
            batch: The batch of bookings to import.

        Returns:
            A list of BookingImportResult objects with the import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Booking/ImportAsync", data)
        adapter = TypeAdapter(list[BookingImportResult])
        return adapter.validate_json(response_text)

    async def import_booking_comments(
        self,
        batch: BookingCommentBatchInput,
    ) -> list[BookingCommentImportResult]:
        """Create, update, or delete a batch of booking comments.

        The comments of a batch may belong to different bookings. They are imported in order
        and independently: a failure on one comment does not abort the rest.

        Args:
            batch: The batch of booking comments to import.

        Returns:
            A list of BookingCommentImportResult objects, one per comment in the order of the batch.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Booking/Comments/Batch", data)
        adapter = TypeAdapter(list[BookingCommentImportResult])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Absence Methods
    # =========================================================================

    async def get_absences(
        self,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AbsenceOutputResult:
        """Get absences from the API.

        Returns all absences within the given timeframe.
        If no timeframe is provided, all absences are returned.

        Args:
            start_date: If provided, only absences occurring after this point in time
                will be returned (timezone-aware).
            end_date: If provided, only absences occurring before this point in time
                will be returned (timezone-aware).

        Returns:
            An AbsenceOutputResult object containing the list of absences.
        """
        params: dict[str, str] = {}
        if start_date is not None:
            params["startDate"] = _format_datetime(start_date)
        if end_date is not None:
            params["endDate"] = _format_datetime(end_date)

        response_text = await self._get("/importapi/Absence", params)
        return AbsenceOutputResult.model_validate_json(response_text)

    async def import_absences(
        self,
        absences: ImportAbsencesCommand,
    ) -> list[AbsenceImportResult]:
        """Import absences.

        Can be used to create, update, or delete absences. Set the 'delete' flag
        on individual AbsenceImportItem objects to True to delete them.

        Args:
            absences: The absences to import.

        Returns:
            A list of AbsenceImportResult objects with the import status.
        """
        data = absences.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Absence/Import", data)
        adapter = TypeAdapter(list[AbsenceImportResult])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Resource Request Methods
    # =========================================================================

    async def get_resource_request(
        self,
        request_id: int,
        *,
        include_candidates: bool | None = None,
    ) -> ResourceRequestOutput:
        """Get a resource request by ID.

        Args:
            request_id: The internal resource request ID.
            include_candidates: Whether to load the candidates and include them in the resource
                request. Defaults to False.

        Returns:
            A ResourceRequestOutput object.
        """
        params: dict[str, str] = {}
        if include_candidates is not None:
            params["includeCandidates"] = str(include_candidates).lower()

        response_text = await self._get(f"/importapi/ResourceRequest/{request_id}", params)
        return ResourceRequestOutput.model_validate_json(response_text)

    async def import_resource_request(
        self,
        resource_request: ResourceRequestInput,
    ) -> ImportResourceRequestCommandResult:
        """Create, update, or delete a resource request.

        Args:
            resource_request: The resource request data to import.

        Returns:
            An ImportResourceRequestCommandResult with the import status.
        """
        data = resource_request.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/ResourceRequest", data)
        return ImportResourceRequestCommandResult.model_validate_json(response_text)

    async def get_resource_request_contacts(
        self,
        *,
        request_id: int | None = None,
        request_code: str | None = None,
        user_id: int | None = None,
        employee_id: str | None = None,
        skip: int | None = None,
        top: int | None = None,
    ) -> list[ResourceRequestContactOutput]:
        """Get a (filtered) list of resource request contacts.

        Args:
            request_id: Filter by internal resource request ID.
            request_code: Filter by external resource request code.
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            skip: Number of results to skip (paging).
            top: Maximum number of results to return (paging).

        Returns:
            A list of ResourceRequestContactOutput objects.
        """
        params: dict[str, str] = {}
        if request_id is not None:
            params["requestid"] = str(request_id)
        if request_code is not None:
            params["requestcode"] = request_code
        if user_id is not None:
            params["userid"] = str(user_id)
        if employee_id is not None:
            params["employeeid"] = employee_id
        if skip is not None:
            params["skip"] = str(skip)
        if top is not None:
            params["top"] = str(top)

        response_text = await self._get("/importapi/ResourceRequest/Contacts", params)
        adapter = TypeAdapter(list[ResourceRequestContactOutput])
        return adapter.validate_json(response_text)

    async def get_resource_request_service_categories(self) -> list[ServiceCategory]:
        """Get all possible service categories (called "Career Level" in the application UI).

        Reference a service category in imports by its ID (stable across renames), its
        internal name, or any translated name.

        Returns:
            A list of ServiceCategory objects.
        """
        response_text = await self._get("/importapi/ResourceRequest/ServiceCategories")
        adapter = TypeAdapter(list[ServiceCategory])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Role Methods
    # =========================================================================

    async def import_role(
        self,
        role: RoleImportInput,
    ) -> ImportRoleResult:
        """Create or update a role and set the corresponding skills and certificates.

        Can also create new skills and certificates if the name is provided.

        Args:
            role: The role data to import.

        Returns:
            An ImportRoleResult with the import status.
        """
        data = role.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Role", data)
        return ImportRoleResult.model_validate_json(response_text)

    # =========================================================================
    # Working Time Pattern Methods
    # =========================================================================

    async def get_working_time_patterns(
        self,
        *,
        user_id: int | None = None,
    ) -> list[GetImportUserWorkingProfileResult]:
        """Get all working time patterns from the API.

        Args:
            user_id: Optional filter by internal user ID.

        Returns:
            A list of GetImportUserWorkingProfileResult objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["UserId"] = str(user_id)

        response_text = await self._get("/importapi/WorkingTimePattern", params)
        adapter = TypeAdapter(list[GetImportUserWorkingProfileResult])
        return adapter.validate_json(response_text)

    async def import_working_time_patterns(
        self,
        patterns: list[UserWorkingProfileInput],
    ) -> list[ImportUserWorkingProfileResult]:
        """Create or update the working time patterns of a batch of users.

        The input allows only for start dates and no end dates. All working time patterns
        will be created/updated with the given start dates, and then the corresponding
        end dates will be calculated automatically to one day before the next start date.

        Args:
            patterns: The per-user working time patterns to import.

        Returns:
            A list of ImportUserWorkingProfileResult objects with the per-user import status.
        """
        adapter = TypeAdapter(list[UserWorkingProfileInput])
        data = adapter.dump_json(patterns, by_alias=True, exclude_none=True).decode()
        response_text = await self._post("/importapi/WorkingTimePattern/Import", data)
        result_adapter = TypeAdapter(list[ImportUserWorkingProfileResult])
        return result_adapter.validate_json(response_text)

    # =========================================================================
    # Holiday Calendar Methods
    # =========================================================================

    async def get_holiday_calendars(
        self,
        *,
        holiday_list_id: int | None = None,
        holiday_list_code: str | None = None,
        custom: bool | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[HolidayCalendarOutput]:
        """Get the holiday calendars with their holidays.

        Returns both custom calendars and standard calendars sourced from the external
        holiday API. A standard calendar appears once it has been assigned to a user.
        Only custom calendars can be modified via import_holiday_calendars().

        Args:
            holiday_list_id: Filter by the internal holiday calendar ID.
            holiday_list_code: Filter by the holiday calendar code.
            custom: True returns only custom calendars, False only standard ones.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of HolidayCalendarOutput objects.
        """
        params: dict[str, str] = {}
        if holiday_list_id is not None:
            params["holidayListID"] = str(holiday_list_id)
        if holiday_list_code is not None:
            params["holidayListCode"] = holiday_list_code
        if custom is not None:
            params["custom"] = str(custom).lower()
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/HolidayCalendar", params)
        adapter = TypeAdapter(list[HolidayCalendarOutput])
        return adapter.validate_json(response_text)

    async def import_holiday_calendars(
        self,
        holiday_calendars: ImportHolidayCalendarsCommand,
    ) -> list[HolidayCalendarImportResult]:
        """Import custom holiday calendars.

        Can be used to create, update, or delete calendars. A calendar is matched by its
        internal ID or, if no ID is given, by its code. The given holidays replace the
        calendar's complete holiday set. Standard calendars provided by the external holiday
        API (e.g. "DE", "DE-NW") cannot be changed. Deleting a calendar fails while it is
        still assigned to users.

        Args:
            holiday_calendars: The holiday calendars to import.

        Returns:
            A list of HolidayCalendarImportResult objects with the import status.
        """
        data = holiday_calendars.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/HolidayCalendar/Import", data)
        adapter = TypeAdapter(list[HolidayCalendarImportResult])
        return adapter.validate_json(response_text)

    async def get_user_holiday_calendars(
        self,
        *,
        user_id: int | None = None,
    ) -> list[UserHolidayCalendarOutputItem]:
        """Get the holiday calendar periods of all users, or of one user.

        Args:
            user_id: Filter by internal user ID.

        Returns:
            A list of UserHolidayCalendarOutputItem objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userID"] = str(user_id)

        response_text = await self._get("/importapi/UserHolidayCalendar", params)
        adapter = TypeAdapter(list[UserHolidayCalendarOutputItem])
        return adapter.validate_json(response_text)

    async def import_user_holiday_calendars(
        self,
        user_holiday_calendars: ImportUserHolidayCalendarsCommand,
    ) -> list[UserHolidayCalendarImportResult]:
        """Import the holiday calendar periods of users.

        Can be used to create, update, or delete single periods. A period is matched by its
        ID or code; without either, a new one is created. The periods of one user must not
        overlap; an overlapping item fails without affecting the rest of the batch. Gaps are
        allowed and mean that the user has no public holidays on those days.

        Args:
            user_holiday_calendars: The holiday calendar periods to import.

        Returns:
            A list of UserHolidayCalendarImportResult objects with the import status.
        """
        data = user_holiday_calendars.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/UserHolidayCalendar/Import", data)
        adapter = TypeAdapter(list[UserHolidayCalendarImportResult])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Activity Type Methods
    # =========================================================================

    async def get_activity_types(
        self,
        *,
        category: str | None = None,
    ) -> list[ActivityTypeResult]:
        """Get all activity types in the system.

        Args:
            category: Only activity types carrying this aggregation category (exact match,
                case-insensitive). Omitted or blank returns every type.

        Returns:
            A list of ActivityTypeResult objects.
        """
        params: dict[str, str] = {}
        if category is not None:
            params["category"] = category

        response_text = await self._get("/importapi/ActivityType", params)
        adapter = TypeAdapter(list[ActivityTypeResult])
        return adapter.validate_json(response_text)

    async def import_activity_type(
        self,
        activity_type: ActivityTypeImportItem,
    ) -> ActivityTypeResult:
        """Create, update, or delete an activity type.

        Set the 'deleted' flag on the item to delete it.

        Args:
            activity_type: The activity type data to import.

        Returns:
            An ActivityTypeResult with the resulting activity type.
        """
        data = activity_type.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/ActivityType", data)
        return ActivityTypeResult.model_validate_json(response_text)

    # =========================================================================
    # General Activity Methods
    # =========================================================================

    async def get_general_activities(self) -> list[GeneralActivityResult]:
        """Get all general activities in the system.

        Returns:
            A list of GeneralActivityResult objects.
        """
        response_text = await self._get("/importapi/GeneralActivity")
        adapter = TypeAdapter(list[GeneralActivityResult])
        return adapter.validate_json(response_text)

    async def import_general_activity(
        self,
        general_activity: GeneralActivityImportItem,
    ) -> GeneralActivityResult:
        """Create, update, or delete a general activity.

        Set the 'deleted' flag on the item to delete it.

        Args:
            general_activity: The general activity data to import.

        Returns:
            A GeneralActivityResult with the resulting general activity.
        """
        data = general_activity.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/GeneralActivity", data)
        return GeneralActivityResult.model_validate_json(response_text)

    # =========================================================================
    # Recording Type Methods
    # =========================================================================

    async def get_recording_types(self) -> list[RecordingTypeResult]:
        """Get the whole recording type catalog, active and inactive.

        Returns:
            A list of RecordingTypeResult objects.
        """
        response_text = await self._get("/importapi/RecordingType")
        adapter = TypeAdapter(list[RecordingTypeResult])
        return adapter.validate_json(response_text)

    async def import_recording_type(
        self,
        recording_type: RecordingTypeImportItem,
    ) -> RecordingTypeResult:
        """Create, update, or delete a recording type.

        Set the 'deleted' flag on the item to delete it.

        Args:
            recording_type: The recording type data to import.

        Returns:
            A RecordingTypeResult with the resulting recording type.
        """
        data = recording_type.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/RecordingType", data)
        return RecordingTypeResult.model_validate_json(response_text)

    # =========================================================================
    # Rate Methods
    # =========================================================================

    async def get_rates(
        self,
        *,
        category: str | None = None,
    ) -> list[RateResult]:
        """Get the whole rate catalog, active and inactive.

        To find the rate a recording entry is priced from, look up the entry's order
        position with get_order_position_recording_type_rates().

        Args:
            category: Only rates carrying this aggregation category (exact, case-insensitive).

        Returns:
            A list of RateResult objects.
        """
        params: dict[str, str] = {}
        if category is not None:
            params["category"] = category

        response_text = await self._get("/importapi/Rate", params)
        adapter = TypeAdapter(list[RateResult])
        return adapter.validate_json(response_text)

    async def import_rate(
        self,
        rate: RateImportItem,
    ) -> RateResult:
        """Create, update, or delete a rate.

        Set the 'deleted' flag on the item to delete it.

        Args:
            rate: The rate data to import.

        Returns:
            A RateResult with the resulting rate.
        """
        data = rate.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Rate", data)
        return RateResult.model_validate_json(response_text)

    # =========================================================================
    # Order Methods
    # =========================================================================

    async def get_orders(
        self,
        *,
        top: int | None = None,
        skip: int | None = None,
        include_positions: bool | None = None,
        project_reference_id: list[int] | None = None,
        project_code: list[str] | None = None,
        valid_from_on_or_after: date | None = None,
        valid_from_on_or_before: date | None = None,
        expiry_on_or_after: date | None = None,
        expiry_on_or_before: date | None = None,
        order_date_on_or_after: date | None = None,
        order_date_on_or_before: date | None = None,
        delivery_date_on_or_after: date | None = None,
        delivery_date_on_or_before: date | None = None,
        valid_on: date | None = None,
        last_updated_on_or_after: datetime | None = None,
    ) -> OrderImportOutputBatch:
        """Get orders with their positions.

        All filters are optional and AND-combined. The date filters compare the order's own
        dates, so an order without the respective date is not returned (except for valid_on,
        which treats a missing valid-from or expiry date as an open bound).

        Args:
            top: Maximum number of orders to return (paging). Without it, every matching order
                is returned.
            skip: Number of orders to skip (paging).
            include_positions: Whether each order carries its positions. Defaults to True; False
                is a cheaper read when only the order headers are wanted.
            project_reference_id: Only orders linked to any of these internal project IDs.
            project_code: Only orders linked to any of these project codes. Ignored if
                project_reference_id is provided.
            valid_from_on_or_after: Only orders whose valid-from date is on or after this day.
            valid_from_on_or_before: Only orders whose valid-from date is on or before this day.
            expiry_on_or_after: Only orders whose expiry date is on or after this day (e.g. not
                yet expired).
            expiry_on_or_before: Only orders whose expiry date is on or before this day.
            order_date_on_or_after: Only orders whose order date is on or after this day.
            order_date_on_or_before: Only orders whose order date is on or before this day.
            delivery_date_on_or_after: Only orders whose delivery date is on or after this day.
            delivery_date_on_or_before: Only orders whose delivery date is on or before this day.
            valid_on: Only orders that are valid on this day (valid-from <= day <= expiry).
            last_updated_on_or_after: Incremental-sync filter: only orders changed, including their
                positions and rate entries, on or after this point in time (timezone-aware).

        Returns:
            An OrderImportOutputBatch containing the matching orders.
        """
        params: dict[str, str | list[str]] = {}
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)
        if include_positions is not None:
            params["includePositions"] = str(include_positions).lower()
        if project_reference_id is not None:
            params["projectReferenceId"] = [str(v) for v in project_reference_id]
        if project_code is not None:
            params["projectCode"] = [str(v) for v in project_code]
        if valid_from_on_or_after is not None:
            params["validFromOnOrAfter"] = _format_date(valid_from_on_or_after)
        if valid_from_on_or_before is not None:
            params["validFromOnOrBefore"] = _format_date(valid_from_on_or_before)
        if expiry_on_or_after is not None:
            params["expiryOnOrAfter"] = _format_date(expiry_on_or_after)
        if expiry_on_or_before is not None:
            params["expiryOnOrBefore"] = _format_date(expiry_on_or_before)
        if order_date_on_or_after is not None:
            params["orderDateOnOrAfter"] = _format_date(order_date_on_or_after)
        if order_date_on_or_before is not None:
            params["orderDateOnOrBefore"] = _format_date(order_date_on_or_before)
        if delivery_date_on_or_after is not None:
            params["deliveryDateOnOrAfter"] = _format_date(delivery_date_on_or_after)
        if delivery_date_on_or_before is not None:
            params["deliveryDateOnOrBefore"] = _format_date(delivery_date_on_or_before)
        if valid_on is not None:
            params["validOn"] = _format_date(valid_on)
        if last_updated_on_or_after is not None:
            params["lastUpdatedOnOrAfter"] = _format_datetime(last_updated_on_or_after)

        response_text = await self._get("/importapi/Order", params)
        return OrderImportOutputBatch.model_validate_json(response_text)

    async def get_order(
        self,
        *,
        order_id: int | None = None,
        code: str | None = None,
    ) -> OrderImportOutput:
        """Get a single order (with its positions) by ID or code.

        Args:
            order_id: The internal order ID.
            code: The per-tenant order code.

        Returns:
            An OrderImportOutput object.
        """
        params: dict[str, str] = {}
        if order_id is not None:
            params["orderId"] = str(order_id)
        if code is not None:
            params["code"] = code

        response_text = await self._get("/importapi/Order/Single", params)
        return OrderImportOutput.model_validate_json(response_text)

    async def import_orders(
        self,
        batch: OrderImportBatch,
    ) -> OrderImportBatchResult:
        """Create, update, or delete orders with their positions.

        Args:
            batch: The batch of orders to import.

        Returns:
            An OrderImportBatchResult with the per-order import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Order", data)
        return OrderImportBatchResult.model_validate_json(response_text)

    async def get_order_custom_properties(self) -> list[CustomProperty]:
        """Get the tenant's custom order fields.

        Returns:
            A list of CustomProperty objects.
        """
        response_text = await self._get("/importapi/Order/CustomProperties")
        adapter = TypeAdapter(list[CustomProperty])
        return adapter.validate_json(response_text)

    async def get_order_position(
        self,
        *,
        order_position_id: int | None = None,
        order_position_code: str | None = None,
        order_id: int | None = None,
        order_code: str | None = None,
    ) -> OrderPositionImportOutput:
        """Get a single order position by ID, or by code plus its parent order.

        Args:
            order_position_id: The internal order position ID.
            order_position_code: The per-tenant order position code.
            order_id: The internal ID of the parent order.
            order_code: The code of the parent order.

        Returns:
            An OrderPositionImportOutput object.
        """
        params: dict[str, str] = {}
        if order_position_id is not None:
            params["orderPositionId"] = str(order_position_id)
        if order_position_code is not None:
            params["orderPositionCode"] = order_position_code
        if order_id is not None:
            params["orderId"] = str(order_id)
        if order_code is not None:
            params["orderCode"] = order_code

        response_text = await self._get("/importapi/Order/Position/Single", params)
        return OrderPositionImportOutput.model_validate_json(response_text)

    async def import_order_positions(
        self,
        batch: OrderPositionImportBatch,
    ) -> OrderPositionImportBatchResult:
        """Create, update, or delete order positions.

        Each position names its parent order by ID or code.

        Args:
            batch: The batch of order positions to import.

        Returns:
            An OrderPositionImportBatchResult with the per-position import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Order/Position", data)
        return OrderPositionImportBatchResult.model_validate_json(response_text)

    async def get_order_position_recording_targets(
        self,
        *,
        order_position_id: int | None = None,
        order_id: int | None = None,
        order_code: str | None = None,
        order_position_code: str | None = None,
    ) -> list[OrderPositionRecordingTargetOutput]:
        """Get an order position's allowed activity types (direct-recording targets).

        Args:
            order_position_id: The internal order position ID.
            order_id: The internal ID of the parent order.
            order_code: The code of the parent order.
            order_position_code: The per-tenant order position code.

        Returns:
            A list of OrderPositionRecordingTargetOutput objects.
        """
        params: dict[str, str] = {}
        if order_position_id is not None:
            params["orderPositionId"] = str(order_position_id)
        if order_id is not None:
            params["orderId"] = str(order_id)
        if order_code is not None:
            params["orderCode"] = order_code
        if order_position_code is not None:
            params["orderPositionCode"] = order_position_code

        response_text = await self._get("/importapi/Order/Position/RecordingTargets", params)
        adapter = TypeAdapter(list[OrderPositionRecordingTargetOutput])
        return adapter.validate_json(response_text)

    async def import_order_position_recording_targets(
        self,
        batch: OrderPositionRecordingTargetImportBatch,
    ) -> OrderPositionRecordingTargetImportBatchResult:
        """Create, update, or remove order positions' allowed activity types.

        One row per (position, activity type).

        Args:
            batch: The recording targets to import.

        Returns:
            An OrderPositionRecordingTargetImportBatchResult with the import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Order/Position/RecordingTargets", data)
        return OrderPositionRecordingTargetImportBatchResult.model_validate_json(response_text)

    async def get_order_position_work_packages(
        self,
        *,
        order_position_id: int | None = None,
        order_id: int | None = None,
        order_code: str | None = None,
        order_position_code: str | None = None,
    ) -> list[OrderPositionWorkPackageOutput]:
        """Get the work packages currently linked to an order position.

        Args:
            order_position_id: The internal order position ID.
            order_id: The internal ID of the parent order.
            order_code: The code of the parent order.
            order_position_code: The per-tenant order position code.

        Returns:
            A list of OrderPositionWorkPackageOutput objects.
        """
        params: dict[str, str] = {}
        if order_position_id is not None:
            params["orderPositionId"] = str(order_position_id)
        if order_id is not None:
            params["orderId"] = str(order_id)
        if order_code is not None:
            params["orderCode"] = order_code
        if order_position_code is not None:
            params["orderPositionCode"] = order_position_code

        response_text = await self._get("/importapi/Order/Position/WorkPackages", params)
        adapter = TypeAdapter(list[OrderPositionWorkPackageOutput])
        return adapter.validate_json(response_text)

    async def import_order_position_work_packages(
        self,
        batch: OrderPositionWorkPackageImportBatch,
    ) -> OrderPositionWorkPackageImportBatchResult:
        """Add or remove order-position to work-package links.

        One row per (position, work package).

        Args:
            batch: The links to import.

        Returns:
            An OrderPositionWorkPackageImportBatchResult with the import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Order/Position/WorkPackages", data)
        return OrderPositionWorkPackageImportBatchResult.model_validate_json(response_text)

    async def get_order_position_recording_type_rates(
        self,
        *,
        order_position_id: int | None = None,
        order_id: int | None = None,
        order_code: str | None = None,
        order_position_code: str | None = None,
    ) -> list[OrderPositionRecordingTypeRateOutput]:
        """Get what each recording type costs on an order position.

        Args:
            order_position_id: The internal order position ID.
            order_id: The internal ID of the parent order.
            order_code: The code of the parent order.
            order_position_code: The per-tenant order position code.

        Returns:
            A list of OrderPositionRecordingTypeRateOutput objects.
        """
        params: dict[str, str] = {}
        if order_position_id is not None:
            params["orderPositionId"] = str(order_position_id)
        if order_id is not None:
            params["orderId"] = str(order_id)
        if order_code is not None:
            params["orderCode"] = order_code
        if order_position_code is not None:
            params["orderPositionCode"] = order_position_code

        response_text = await self._get("/importapi/Order/Position/RecordingTypeRates", params)
        adapter = TypeAdapter(list[OrderPositionRecordingTypeRateOutput])
        return adapter.validate_json(response_text)

    async def import_order_position_recording_type_rates(
        self,
        batch: OrderPositionRecordingTypeRateImportBatch,
    ) -> OrderPositionRecordingTypeRateImportBatchResult:
        """Set or remove what each recording type costs on an order position.

        One row per (position, recording type).

        Args:
            batch: The prices to import.

        Returns:
            An OrderPositionRecordingTypeRateImportBatchResult with the per-row import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Order/Position/RecordingTypeRates", data)
        return OrderPositionRecordingTypeRateImportBatchResult.model_validate_json(response_text)

    # =========================================================================
    # Work Package Methods
    # =========================================================================

    async def get_work_packages(
        self,
        *,
        work_package_id: int | None = None,
        project_id: int | None = None,
        project_code: str | None = None,
        work_package_code: str | None = None,
        status: WorkPackageStatus | None = None,
        parent_work_package_id: int | None = None,
        time_recording_allowed: bool | None = None,
        start_date_before: date | None = None,
        end_date_after: date | None = None,
        created_on_or_after: datetime | None = None,
        last_updated_on_or_after: datetime | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[WorkPackageOutput]:
        """Get work packages matching the given filters.

        Connected properties may be given by ID or by code (ID wins).

        Args:
            work_package_id: Filter by the internal work package ID.
            project_id: Filter by the internal project ID.
            project_code: Filter by the external project code.
            work_package_code: Filter by the work package code.
            status: Filter by work package status.
            parent_work_package_id: Filter by the parent work package ID.
            time_recording_allowed: Filter by whether time recording is allowed.
            start_date_before: Only work packages starting before this date.
            end_date_after: Only work packages ending after this date.
            created_on_or_after: Incremental-sync filter on the creation timestamp (timezone-aware).
            last_updated_on_or_after: Incremental-sync filter on the update timestamp (timezone-aware).
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of WorkPackageOutput objects.
        """
        params: dict[str, str] = {}
        if work_package_id is not None:
            params["WorkPackageID"] = str(work_package_id)
        if project_id is not None:
            params["ProjectID"] = str(project_id)
        if project_code is not None:
            params["ProjectCode"] = project_code
        if work_package_code is not None:
            params["WorkPackageCode"] = work_package_code
        if status is not None:
            params["Status"] = status.value
        if parent_work_package_id is not None:
            params["ParentWorkPackageID"] = str(parent_work_package_id)
        if time_recording_allowed is not None:
            params["TimeRecordingAllowed"] = str(time_recording_allowed).lower()
        if start_date_before is not None:
            params["StartDateBefore"] = _format_date(start_date_before)
        if end_date_after is not None:
            params["EndDateAfter"] = _format_date(end_date_after)
        if created_on_or_after is not None:
            params["CreatedOnOrAfter"] = _format_datetime(created_on_or_after)
        if last_updated_on_or_after is not None:
            params["LastUpdatedOnOrAfter"] = _format_datetime(last_updated_on_or_after)
        if top is not None:
            params["Top"] = str(top)
        if skip is not None:
            params["Skip"] = str(skip)

        response_text = await self._get("/importapi/WorkPackage", params)
        adapter = TypeAdapter(list[WorkPackageOutput])
        return adapter.validate_json(response_text)

    async def get_work_package(
        self,
        work_package_id: int,
    ) -> WorkPackageOutput:
        """Get a specific work package by ID.

        Args:
            work_package_id: The internal work package ID.

        Returns:
            A WorkPackageOutput object.
        """
        response_text = await self._get(f"/importapi/WorkPackage/{work_package_id}")
        return WorkPackageOutput.model_validate_json(response_text)

    async def import_work_package(
        self,
        work_package: WorkPackageInput,
    ) -> ImportWorkPackageCommandResult:
        """Create, update, or delete a work package.

        Set the 'delete' flag on the input to delete it.

        Args:
            work_package: The work package data to import.

        Returns:
            An ImportWorkPackageCommandResult with the import status.
        """
        data = work_package.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/WorkPackage", data)
        return ImportWorkPackageCommandResult.model_validate_json(response_text)

    async def get_work_package_candidates(
        self,
        *,
        project_id: int | None = None,
        work_package_id: int | None = None,
    ) -> WorkPackageCandidateBatchInput:
        """Get all work package candidate assignments for the tenant.

        The response shape is identical to the import_work_package_candidates()
        request body and can be submitted to it without modification.

        Args:
            project_id: Filter by the internal project ID.
            work_package_id: Filter by the internal work package ID.

        Returns:
            A WorkPackageCandidateBatchInput with the candidate assignments.
        """
        params: dict[str, str] = {}
        if project_id is not None:
            params["projectID"] = str(project_id)
        if work_package_id is not None:
            params["workPackageID"] = str(work_package_id)

        response_text = await self._get("/importapi/WorkPackage/Candidates", params)
        return WorkPackageCandidateBatchInput.model_validate_json(response_text)

    async def import_work_package_candidates(
        self,
        batch: WorkPackageCandidateBatchInput,
    ) -> WorkPackageCandidateBatchResult:
        """Create or delete work package candidate assignments in batch.

        Each item is processed independently; per-item failures do not abort the batch.

        Args:
            batch: The candidate assignments to import.

        Returns:
            A WorkPackageCandidateBatchResult with the per-item import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/WorkPackage/Candidates", data)
        return WorkPackageCandidateBatchResult.model_validate_json(response_text)

    async def get_work_package_order_positions(
        self,
        *,
        work_package_id: int | None = None,
        work_package_code: str | None = None,
    ) -> list[WorkPackageOrderPositionOutput]:
        """Get the order positions currently linked to a work package.

        Args:
            work_package_id: The internal work package ID.
            work_package_code: The work package code.

        Returns:
            A list of WorkPackageOrderPositionOutput objects.
        """
        params: dict[str, str] = {}
        if work_package_id is not None:
            params["workPackageId"] = str(work_package_id)
        if work_package_code is not None:
            params["workPackageCode"] = work_package_code

        response_text = await self._get("/importapi/WorkPackage/OrderPositions", params)
        adapter = TypeAdapter(list[WorkPackageOrderPositionOutput])
        return adapter.validate_json(response_text)

    async def import_work_package_order_positions(
        self,
        batch: WorkPackageOrderPositionImportBatch,
    ) -> WorkPackageOrderPositionImportBatchResult:
        """Add or remove work-package to order-position links.

        One row per (work package, position).

        Args:
            batch: The links to import.

        Returns:
            A WorkPackageOrderPositionImportBatchResult with the import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/WorkPackage/OrderPositions", data)
        return WorkPackageOrderPositionImportBatchResult.model_validate_json(response_text)

    async def get_work_package_recording_targets(
        self,
        *,
        work_package_id: int | None = None,
        work_package_code: str | None = None,
    ) -> list[WorkPackageRecordingTargetOutput]:
        """Get a work package's allowed activity types (recording targets).

        Args:
            work_package_id: The internal work package ID.
            work_package_code: The work package code.

        Returns:
            A list of WorkPackageRecordingTargetOutput objects.
        """
        params: dict[str, str] = {}
        if work_package_id is not None:
            params["workPackageId"] = str(work_package_id)
        if work_package_code is not None:
            params["workPackageCode"] = work_package_code

        response_text = await self._get("/importapi/WorkPackage/RecordingTargets", params)
        adapter = TypeAdapter(list[WorkPackageRecordingTargetOutput])
        return adapter.validate_json(response_text)

    async def import_work_package_recording_targets(
        self,
        batch: WorkPackageRecordingTargetImportBatch,
    ) -> WorkPackageRecordingTargetImportBatchResult:
        """Create, update, or remove a work package's allowed activity types.

        One row per (work package, activity type).

        Args:
            batch: The recording targets to import.

        Returns:
            A WorkPackageRecordingTargetImportBatchResult with the import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/WorkPackage/RecordingTargets", data)
        return WorkPackageRecordingTargetImportBatchResult.model_validate_json(response_text)

    async def get_work_package_custom_properties(self) -> list[CustomProperty]:
        """Get a description of all possible custom properties for work packages.

        Returns:
            A list of CustomProperty objects.
        """
        response_text = await self._get("/importapi/WorkPackage/CustomProperties")
        adapter = TypeAdapter(list[CustomProperty])
        return adapter.validate_json(response_text)

    async def get_work_package_order_position_recording_targets(
        self,
        *,
        work_package_last_updated_on_or_after: datetime | None = None,
        order_position_activity_type_id: int | None = None,
        order_position_activity_type_code: str | None = None,
        order_position_activity_type_target_system_code: str | None = None,
        order_position_activity_type_category: str | None = None,
        work_package_id: int | None = None,
        work_package_code: str | None = None,
        order_position_id: int | None = None,
        order_position_code: str | None = None,
        order_id: int | None = None,
        order_code: str | None = None,
        project_id: int | None = None,
        project_code: str | None = None,
        recording_type_id: int | None = None,
        recording_type_code: str | None = None,
        is_active: bool | None = None,
        is_billable: bool | None = None,
        order_position_last_updated_on_or_after: datetime | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[WorkPackageOrderPositionRecordingTargetOutput]:
        """Get the recording targets of the links between work packages and order positions.

        Time booked on such a pair is attributed to these targets. They are read-only and
        follow from the links (see import_work_package_order_positions() and
        import_order_position_work_packages()) and from the activity types of the order
        position (see import_order_position_recording_targets()). All filters are optional
        and AND-combined. Where an ID and a code are offered for the same entity, the ID wins,
        and an unknown code matches nothing.

        Args:
            work_package_last_updated_on_or_after: Only targets whose work package was last updated
                on or after this point in time (timezone-aware).
            order_position_activity_type_id: Filter by the internal ID of the order position's activity type.
            order_position_activity_type_code: Filter by the code of the order position's activity type.
            order_position_activity_type_target_system_code: Filter by the target system code of the
                order position's activity type.
            order_position_activity_type_category: Filter by the aggregation category of the order
                position's activity type.
            work_package_id: Filter by the internal work package ID.
            work_package_code: Filter by the work package code.
            order_position_id: Filter by the internal order position ID.
            order_position_code: Filter by the per-tenant order position code.
            order_id: Filter by the internal ID of the parent order.
            order_code: Filter by the code of the parent order.
            project_id: Filter by the internal project ID.
            project_code: Filter by the external project code.
            recording_type_id: Filter by the internal recording type ID.
            recording_type_code: Filter by the recording type code.
            is_active: Filter by whether the target is active.
            is_billable: Filter by whether the target is billable.
            order_position_last_updated_on_or_after: Only targets whose order position was last updated
                on or after this point in time (timezone-aware).
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of WorkPackageOrderPositionRecordingTargetOutput objects.
        """
        params: dict[str, str] = {}
        if work_package_last_updated_on_or_after is not None:
            params["WorkPackageLastUpdatedOnOrAfter"] = _format_datetime(work_package_last_updated_on_or_after)
        if order_position_activity_type_id is not None:
            params["OrderPositionActivityTypeID"] = str(order_position_activity_type_id)
        if order_position_activity_type_code is not None:
            params["OrderPositionActivityTypeCode"] = order_position_activity_type_code
        if order_position_activity_type_target_system_code is not None:
            params["OrderPositionActivityTypeTargetSystemCode"] = order_position_activity_type_target_system_code
        if order_position_activity_type_category is not None:
            params["OrderPositionActivityTypeCategory"] = order_position_activity_type_category
        if work_package_id is not None:
            params["WorkPackageID"] = str(work_package_id)
        if work_package_code is not None:
            params["WorkPackageCode"] = work_package_code
        if order_position_id is not None:
            params["OrderPositionID"] = str(order_position_id)
        if order_position_code is not None:
            params["OrderPositionCode"] = order_position_code
        if order_id is not None:
            params["OrderID"] = str(order_id)
        if order_code is not None:
            params["OrderCode"] = order_code
        if project_id is not None:
            params["ProjectID"] = str(project_id)
        if project_code is not None:
            params["ProjectCode"] = project_code
        if recording_type_id is not None:
            params["RecordingTypeID"] = str(recording_type_id)
        if recording_type_code is not None:
            params["RecordingTypeCode"] = recording_type_code
        if is_active is not None:
            params["IsActive"] = str(is_active).lower()
        if is_billable is not None:
            params["IsBillable"] = str(is_billable).lower()
        if order_position_last_updated_on_or_after is not None:
            params["OrderPositionLastUpdatedOnOrAfter"] = _format_datetime(order_position_last_updated_on_or_after)
        if top is not None:
            params["Top"] = str(top)
        if skip is not None:
            params["Skip"] = str(skip)

        response_text = await self._get("/importapi/WorkPackage/OrderPositions/RecordingTargets", params)
        adapter = TypeAdapter(list[WorkPackageOrderPositionRecordingTargetOutput])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Time Recording Methods
    # =========================================================================

    async def get_recording_targets(
        self,
        *,
        project_reference_id: int | None = None,
        project_code: str | None = None,
        work_package_id: int | None = None,
        work_package_code: str | None = None,
        order_position_id: int | None = None,
        order_position_code: str | None = None,
        order_id: int | None = None,
        order_code: str | None = None,
        general_activity_id: int | None = None,
        general_activity_code: str | None = None,
        activity_type_id: int | None = None,
        activity_type_code: str | None = None,
        activity_type_target_system_code: str | None = None,
        general_activity_target_system_code: str | None = None,
        activity_type_category: str | None = None,
        is_active: bool | None = None,
    ) -> list[RecordingTargetOutput]:
        """Get the tenant's recording targets across all subject kinds.

        Covers project, work package, general activity, and order position targets.
        All filters are optional and AND-combined; subject filters accept an ID or a code
        (the ID wins). Only active targets are returned unless is_active is set
        (True = active only, False = inactive only).

        Args:
            project_reference_id: Filter by internal project reference ID.
            project_code: Filter by external project code.
            work_package_id: Filter by internal work package ID.
            work_package_code: Filter by work package code.
            order_position_id: Filter by internal order position ID.
            order_position_code: Filter by order position code.
            order_id: Filter by internal order ID (targets on a position of this order).
            order_code: Filter by order code (targets on a position of the order with this code).
            general_activity_id: Filter by internal general activity ID.
            general_activity_code: Filter by general activity code.
            activity_type_id: Filter by internal activity type ID.
            activity_type_code: Filter by activity type code.
            activity_type_target_system_code: Filter by the target system code of the activity type
                (exact, case-insensitive).
            general_activity_target_system_code: Filter by the target system code of the general
                activity (exact, case-insensitive). Setting both codes matches nothing.
            activity_type_category: Filter by the aggregation category of the activity type (exact,
                case-insensitive).
            is_active: True returns active targets only, False inactive only.

        Returns:
            A list of RecordingTargetOutput objects.
        """
        params: dict[str, str] = {}
        if project_reference_id is not None:
            params["projectReferenceId"] = str(project_reference_id)
        if project_code is not None:
            params["projectCode"] = project_code
        if work_package_id is not None:
            params["workPackageId"] = str(work_package_id)
        if work_package_code is not None:
            params["workPackageCode"] = work_package_code
        if order_position_id is not None:
            params["orderPositionId"] = str(order_position_id)
        if order_position_code is not None:
            params["orderPositionCode"] = order_position_code
        if order_id is not None:
            params["orderId"] = str(order_id)
        if order_code is not None:
            params["orderCode"] = order_code
        if general_activity_id is not None:
            params["generalActivityId"] = str(general_activity_id)
        if general_activity_code is not None:
            params["generalActivityCode"] = general_activity_code
        if activity_type_id is not None:
            params["activityTypeId"] = str(activity_type_id)
        if activity_type_code is not None:
            params["activityTypeCode"] = activity_type_code
        if activity_type_target_system_code is not None:
            params["activityTypeTargetSystemCode"] = activity_type_target_system_code
        if general_activity_target_system_code is not None:
            params["generalActivityTargetSystemCode"] = general_activity_target_system_code
        if activity_type_category is not None:
            params["activityTypeCategory"] = activity_type_category
        if is_active is not None:
            params["isActive"] = str(is_active).lower()

        response_text = await self._get("/importapi/TimeRecording/RecordingTargets", params)
        adapter = TypeAdapter(list[RecordingTargetOutput])
        return adapter.validate_json(response_text)

    async def get_user_time_sheet(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        email: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        work_date_on_or_after: date | None = None,
        work_date_on_or_before: date | None = None,
        order_id: int | None = None,
        order_code: str | None = None,
        project_reference_id: int | None = None,
        project_code: str | None = None,
        work_package_id: int | None = None,
        work_package_code: str | None = None,
        order_position_id: int | None = None,
        order_position_code: str | None = None,
        general_activity_id: int | None = None,
        general_activity_code: str | None = None,
        activity_type_id: int | None = None,
        activity_type_code: str | None = None,
        activity_type_target_system_code: str | None = None,
        general_activity_target_system_code: str | None = None,
        activity_type_category: str | None = None,
        rate_id: int | None = None,
        rate_code: str | None = None,
        rate_category: str | None = None,
        status: list[TimeRecordingEntryStatus] | None = None,
        modified_after: datetime | None = None,
        created_on_or_after: datetime | None = None,
        last_updated_on_or_after: datetime | None = None,
        last_imported_on_or_after: datetime | None = None,
    ) -> TimeRecordingImportOutputBatch:
        """Get a user's timesheet.

        Every filter besides the owner (user_id, employee_id, or email) is optional and
        AND-combined. The entry filters narrow the recording entries only; the working times
        always follow the date range alone. Where a filter can be given by ID or by code, the ID
        wins. work_date_on_or_after and work_date_on_or_before win over start_date and end_date,
        and last_updated_on_or_after wins over modified_after.

        Args:
            user_id: The internal user ID of the owner.
            employee_id: The external employee ID of the owner.
            email: The email address of the owner.
            start_date: Inclusive lower bound on the work date. Ignored if work_date_on_or_after
                is provided.
            end_date: Inclusive upper bound on the work date. Ignored if work_date_on_or_before
                is provided.
            work_date_on_or_after: Inclusive lower bound on the work date. Wins over start_date.
            work_date_on_or_before: Inclusive upper bound on the work date. Wins over end_date.
            order_id: Only entries recorded against a position of this order.
            order_code: Only entries recorded against a position of the order with this code.
            project_reference_id: Only entries whose subject belongs to this project, directly,
                through its work package, or through its order position.
            project_code: Same as project_reference_id, addressed by the project code.
            work_package_id: Only entries recorded against this work package.
            work_package_code: Only entries recorded against the work package with this code.
            order_position_id: Only entries recorded against this order position.
            order_position_code: Only entries recorded against the order position with this code.
            general_activity_id: Only entries recorded against this general activity.
            general_activity_code: Only entries recorded against the general activity with this
                code.
            activity_type_id: Only entries whose target uses this activity type.
            activity_type_code: Only entries whose target uses the activity type with this code.
            activity_type_target_system_code: Only entries whose activity type carries this target
                system code (exact, case-insensitive).
            general_activity_target_system_code: Only entries whose general activity carries this
                target system code (exact, case-insensitive). Setting both codes matches nothing.
            activity_type_category: Only entries whose activity type carries this aggregation
                category (exact, case-insensitive).
            rate_id: Only entries priced from this catalog rate, i.e. the rate their order position
                prices the default (work-time) recording type from.
            rate_code: Same as rate_id, addressed by the rate's unique code.
            rate_category: Only entries whose rate carries this aggregation category (exact,
                case-insensitive).
            status: Only entries in these states. Omitted returns every state.
            modified_after: Only entries last edited strictly after this point in time. Ignored if
                last_updated_on_or_after is provided (timezone-aware).
            created_on_or_after: Only entries created on or after this point in time
                (timezone-aware).
            last_updated_on_or_after: Only entries last edited on or after this point in time.
                Wins over modified_after (timezone-aware).
            last_imported_on_or_after: Only entries last written by the Import API on or after this
                point in time; never-imported entries are excluded (timezone-aware).

        Returns:
            A TimeRecordingImportOutputBatch with the user's entries and work times.
        """
        params: dict[str, str | list[str]] = {}
        if user_id is not None:
            params["userId"] = str(user_id)
        if employee_id is not None:
            params["employeeId"] = employee_id
        if email is not None:
            params["email"] = email
        if start_date is not None:
            params["startDate"] = _format_date(start_date)
        if end_date is not None:
            params["endDate"] = _format_date(end_date)
        if work_date_on_or_after is not None:
            params["workDateOnOrAfter"] = _format_date(work_date_on_or_after)
        if work_date_on_or_before is not None:
            params["workDateOnOrBefore"] = _format_date(work_date_on_or_before)
        if order_id is not None:
            params["orderId"] = str(order_id)
        if order_code is not None:
            params["orderCode"] = order_code
        if project_reference_id is not None:
            params["projectReferenceId"] = str(project_reference_id)
        if project_code is not None:
            params["projectCode"] = project_code
        if work_package_id is not None:
            params["workPackageId"] = str(work_package_id)
        if work_package_code is not None:
            params["workPackageCode"] = work_package_code
        if order_position_id is not None:
            params["orderPositionId"] = str(order_position_id)
        if order_position_code is not None:
            params["orderPositionCode"] = order_position_code
        if general_activity_id is not None:
            params["generalActivityId"] = str(general_activity_id)
        if general_activity_code is not None:
            params["generalActivityCode"] = general_activity_code
        if activity_type_id is not None:
            params["activityTypeId"] = str(activity_type_id)
        if activity_type_code is not None:
            params["activityTypeCode"] = activity_type_code
        if activity_type_target_system_code is not None:
            params["activityTypeTargetSystemCode"] = activity_type_target_system_code
        if general_activity_target_system_code is not None:
            params["generalActivityTargetSystemCode"] = general_activity_target_system_code
        if activity_type_category is not None:
            params["activityTypeCategory"] = activity_type_category
        if rate_id is not None:
            params["rateId"] = str(rate_id)
        if rate_code is not None:
            params["rateCode"] = rate_code
        if rate_category is not None:
            params["rateCategory"] = rate_category
        if status is not None:
            params["status"] = [v.value for v in status]
        if modified_after is not None:
            params["modifiedAfter"] = _format_datetime(modified_after)
        if created_on_or_after is not None:
            params["createdOnOrAfter"] = _format_datetime(created_on_or_after)
        if last_updated_on_or_after is not None:
            params["lastUpdatedOnOrAfter"] = _format_datetime(last_updated_on_or_after)
        if last_imported_on_or_after is not None:
            params["lastImportedOnOrAfter"] = _format_datetime(last_imported_on_or_after)

        response_text = await self._get("/importapi/TimeRecording/UserTimeSheet", params)
        return TimeRecordingImportOutputBatch.model_validate_json(response_text)

    async def import_user_time_sheet(
        self,
        batch: TimeRecordingImportBatch,
    ) -> TimeRecordingImportResult:
        """Import a user's timesheet.

        Args:
            batch: The timesheet entries and work times to import.

        Returns:
            A TimeRecordingImportResult with the per-item import status.
        """
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/TimeRecording/UserTimeSheet", data)
        return TimeRecordingImportResult.model_validate_json(response_text)

    async def get_recording_entries(
        self,
        *,
        top: int | None = None,
        skip: int | None = None,
        user_id: list[int] | None = None,
        employee_id: list[str] | None = None,
        email: list[str] | None = None,
        work_date_on_or_after: date | None = None,
        work_date_on_or_before: date | None = None,
        created_on_or_after: datetime | None = None,
        last_updated_on_or_after: datetime | None = None,
        last_imported_on_or_after: datetime | None = None,
        users_business_unit_id: int | None = None,
        users_business_unit_name: str | None = None,
        users_practice_area_id: int | None = None,
        users_practice_area_name: str | None = None,
        users_team_id: int | None = None,
        users_team_code: str | None = None,
        users_legal_entity_id: int | None = None,
        users_legal_entity_name: str | None = None,
        users_country_code: str | None = None,
        order_id: int | None = None,
        order_code: str | None = None,
        project_reference_id: int | None = None,
        project_code: str | None = None,
        work_package_id: int | None = None,
        work_package_code: str | None = None,
        order_position_id: int | None = None,
        order_position_code: str | None = None,
        general_activity_id: int | None = None,
        general_activity_code: str | None = None,
        activity_type_id: int | None = None,
        activity_type_code: str | None = None,
        activity_type_target_system_code: str | None = None,
        general_activity_target_system_code: str | None = None,
        activity_type_category: str | None = None,
        rate_id: int | None = None,
        rate_code: str | None = None,
        rate_category: str | None = None,
        status: list[TimeRecordingEntryStatus] | None = None,
        recording_entry_id: int | None = None,
        recording_entry_code: str | None = None,
    ) -> list[RecordingEntryImportReadItem]:
        """Get recording entries across users, in the shape import_recording_entries() accepts.

        A flat list in which every entry names its own owner; working times are only returned
        by get_user_time_sheet(). All filters are optional and AND-combined, except for the
        owner filters user_id, employee_id and email, which are OR-combined with each other.
        Where an ID and a code or name are offered for the same entity, the ID wins, and a code
        or name matching nothing yields no entries. Without filters, the tenant's whole history
        is returned, so page it with top and skip.

        Args:
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).
            user_id: Only entries of the users with these internal IDs.
            employee_id: Only entries of the users with these external employee IDs.
            email: Only entries of the users with these email addresses.
            work_date_on_or_after: Inclusive lower bound on the work date.
            work_date_on_or_before: Inclusive upper bound on the work date.
            created_on_or_after: Only entries created on or after this point in time (timezone-aware).
            last_updated_on_or_after: Incremental-sync filter: only entries last edited on or after
                this point in time (timezone-aware).
            last_imported_on_or_after: Incremental-sync filter: only entries the Import API last wrote
                on or after this point in time, excluding never-imported entries (timezone-aware).
            users_business_unit_id: Only entries whose owner is in this business unit.
            users_business_unit_name: Only entries whose owner is in the business unit with this name.
            users_practice_area_id: Only entries whose owner is in this practice area.
            users_practice_area_name: Only entries whose owner is in the practice area with this name.
            users_team_id: Only entries whose owner is in this team.
            users_team_code: Only entries whose owner is in the team with this code.
            users_legal_entity_id: Only entries whose owner belongs to this legal entity.
            users_legal_entity_name: Only entries whose owner belongs to the legal entity with this name.
            users_country_code: Only entries whose owner carries this country code (exact, case-insensitive).
            order_id: Only entries recorded against a position of this order.
            order_code: Only entries recorded against a position of the order with this code.
            project_reference_id: Only entries whose subject belongs to this project, directly,
                through its work package, or through its order position.
            project_code: Only entries whose subject belongs to the project with this code.
            work_package_id: Only entries recorded against this work package.
            work_package_code: Only entries recorded against the work package with this code.
            order_position_id: Only entries recorded against this order position.
            order_position_code: Only entries recorded against the order position with this code.
            general_activity_id: Only entries recorded against this general activity.
            general_activity_code: Only entries recorded against the general activity with this code.
            activity_type_id: Only entries whose target uses this activity type.
            activity_type_code: Only entries whose target uses the activity type with this code.
            activity_type_target_system_code: Only entries whose activity type carries this target
                system code (exact, case-insensitive). An alternative to
                general_activity_target_system_code; setting both matches nothing.
            general_activity_target_system_code: Only entries whose general activity carries this
                target system code (exact, case-insensitive).
            activity_type_category: Only entries whose activity type carries this aggregation category
                (exact, case-insensitive).
            rate_id: Only entries whose recording target prices its work time from this catalog rate.
            rate_code: Only entries whose recording target prices its work time from the rate with this code.
            rate_category: Only entries whose work-time rate carries this aggregation category
                (exact, case-insensitive).
            status: Only entries in these states. If omitted, entries in every state are returned.
            recording_entry_id: Only the entry with this internal ID.
            recording_entry_code: Only entries with this external key (unique per user, so several
                owners may match).

        Returns:
            A list of RecordingEntryImportReadItem objects.
        """
        params: dict[str, str | list[str]] = {}
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)
        if user_id is not None:
            params["userId"] = [str(v) for v in user_id]
        if employee_id is not None:
            params["employeeId"] = employee_id
        if email is not None:
            params["email"] = email
        if work_date_on_or_after is not None:
            params["workDateOnOrAfter"] = _format_date(work_date_on_or_after)
        if work_date_on_or_before is not None:
            params["workDateOnOrBefore"] = _format_date(work_date_on_or_before)
        if created_on_or_after is not None:
            params["createdOnOrAfter"] = _format_datetime(created_on_or_after)
        if last_updated_on_or_after is not None:
            params["lastUpdatedOnOrAfter"] = _format_datetime(last_updated_on_or_after)
        if last_imported_on_or_after is not None:
            params["lastImportedOnOrAfter"] = _format_datetime(last_imported_on_or_after)
        if users_business_unit_id is not None:
            params["usersBusinessUnitId"] = str(users_business_unit_id)
        if users_business_unit_name is not None:
            params["usersBusinessUnitName"] = users_business_unit_name
        if users_practice_area_id is not None:
            params["usersPracticeAreaId"] = str(users_practice_area_id)
        if users_practice_area_name is not None:
            params["usersPracticeAreaName"] = users_practice_area_name
        if users_team_id is not None:
            params["usersTeamId"] = str(users_team_id)
        if users_team_code is not None:
            params["usersTeamCode"] = users_team_code
        if users_legal_entity_id is not None:
            params["usersLegalEntityId"] = str(users_legal_entity_id)
        if users_legal_entity_name is not None:
            params["usersLegalEntityName"] = users_legal_entity_name
        if users_country_code is not None:
            params["usersCountryCode"] = users_country_code
        if order_id is not None:
            params["orderId"] = str(order_id)
        if order_code is not None:
            params["orderCode"] = order_code
        if project_reference_id is not None:
            params["projectReferenceId"] = str(project_reference_id)
        if project_code is not None:
            params["projectCode"] = project_code
        if work_package_id is not None:
            params["workPackageId"] = str(work_package_id)
        if work_package_code is not None:
            params["workPackageCode"] = work_package_code
        if order_position_id is not None:
            params["orderPositionId"] = str(order_position_id)
        if order_position_code is not None:
            params["orderPositionCode"] = order_position_code
        if general_activity_id is not None:
            params["generalActivityId"] = str(general_activity_id)
        if general_activity_code is not None:
            params["generalActivityCode"] = general_activity_code
        if activity_type_id is not None:
            params["activityTypeId"] = str(activity_type_id)
        if activity_type_code is not None:
            params["activityTypeCode"] = activity_type_code
        if activity_type_target_system_code is not None:
            params["activityTypeTargetSystemCode"] = activity_type_target_system_code
        if general_activity_target_system_code is not None:
            params["generalActivityTargetSystemCode"] = general_activity_target_system_code
        if activity_type_category is not None:
            params["activityTypeCategory"] = activity_type_category
        if rate_id is not None:
            params["rateId"] = str(rate_id)
        if rate_code is not None:
            params["rateCode"] = rate_code
        if rate_category is not None:
            params["rateCategory"] = rate_category
        if status is not None:
            params["status"] = [v.value for v in status]
        if recording_entry_id is not None:
            params["recordingEntryId"] = str(recording_entry_id)
        if recording_entry_code is not None:
            params["recordingEntryCode"] = recording_entry_code

        response_text = await self._get("/importapi/TimeRecording/RecordingEntries", params)
        adapter = TypeAdapter(list[RecordingEntryImportReadItem])
        return adapter.validate_json(response_text)

    async def import_recording_entries(
        self,
        entries: list[RecordingEntryImportItem],
    ) -> list[RecordingEntryImportResult]:
        """Import recording entries across users, in the shape get_recording_entries() returns.

        Every entry names its own owner. It is created, updated, or deleted depending on its
        identifier (the recording entry ID, else the per-user recording entry code) and its
        'deleted' flag. The entries are processed independently: a failure is reported in the
        entry's own result and the other entries are still imported.

        Args:
            entries: The recording entries to import.

        Returns:
            A list of RecordingEntryImportResult objects with the per-entry import status.
        """
        adapter = TypeAdapter(list[RecordingEntryImportItem])
        data = adapter.dump_json(entries, by_alias=True, exclude_none=True).decode()
        response_text = await self._post("/importapi/TimeRecording/RecordingEntries", data)
        result_adapter = TypeAdapter(list[RecordingEntryImportResult])
        return result_adapter.validate_json(response_text)

    # =========================================================================
    # Profile Export Methods
    # =========================================================================

    async def get_profile_industries(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        industry_id: int | None = None,
        industry_code: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[UserIndustryExportOutput]:
        """Get users with their assigned industries.

        Args:
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            industry_id: Filter by internal industry ID.
            industry_code: Filter by industry code.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of UserIndustryExportOutput objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userID"] = str(user_id)
        if employee_id is not None:
            params["employeeID"] = employee_id
        if industry_id is not None:
            params["industryID"] = str(industry_id)
        if industry_code is not None:
            params["industryCode"] = industry_code
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Profile/Industries", params)
        adapter = TypeAdapter(list[UserIndustryExportOutput])
        return adapter.validate_json(response_text)

    async def get_profile_languages(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        language_id: int | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[UserLanguageExportOutput]:
        """Get users with their spoken languages.

        Args:
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            language_id: Filter by internal language ID.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of UserLanguageExportOutput objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userID"] = str(user_id)
        if employee_id is not None:
            params["employeeID"] = employee_id
        if language_id is not None:
            params["languageID"] = str(language_id)
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Profile/Languages", params)
        adapter = TypeAdapter(list[UserLanguageExportOutput])
        return adapter.validate_json(response_text)

    async def get_profile_professional_experience(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[UserProfessionalExperienceExportOutput]:
        """Get users with their professional experiences.

        Args:
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of UserProfessionalExperienceExportOutput objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userID"] = str(user_id)
        if employee_id is not None:
            params["employeeID"] = employee_id
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Profile/ProfessionalExperience", params)
        adapter = TypeAdapter(list[UserProfessionalExperienceExportOutput])
        return adapter.validate_json(response_text)

    async def get_profile_publications(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[UserPublicationExportOutput]:
        """Get users with their publications.

        Args:
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of UserPublicationExportOutput objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userID"] = str(user_id)
        if employee_id is not None:
            params["employeeID"] = employee_id
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Profile/Publications", params)
        adapter = TypeAdapter(list[UserPublicationExportOutput])
        return adapter.validate_json(response_text)

    async def get_profile_testimonials(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[UserTestimonialExportOutput]:
        """Get users with their testimonials.

        Args:
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of UserTestimonialExportOutput objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userID"] = str(user_id)
        if employee_id is not None:
            params["employeeID"] = employee_id
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Profile/Testimonials", params)
        adapter = TypeAdapter(list[UserTestimonialExportOutput])
        return adapter.validate_json(response_text)

    async def get_profile_trainings(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        training_reference_id: int | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[UserTrainingExportOutput]:
        """Get users with their trainings.

        Args:
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            training_reference_id: Filter by internal training reference ID.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).

        Returns:
            A list of UserTrainingExportOutput objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userID"] = str(user_id)
        if employee_id is not None:
            params["employeeID"] = employee_id
        if training_reference_id is not None:
            params["trainingReferenceID"] = str(training_reference_id)
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)

        response_text = await self._get("/importapi/Profile/Trainings", params)
        adapter = TypeAdapter(list[UserTrainingExportOutput])
        return adapter.validate_json(response_text)

    async def get_profile_user_skills(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        team_id: int | None = None,
        team_code: str | None = None,
        business_unit_id: int | None = None,
        business_unit_name: str | None = None,
        country_code: str | None = None,
        legal_entity_id: int | None = None,
        legal_entity_name: str | None = None,
        practice_area_id: int | None = None,
        practice_area_name: str | None = None,
        service_line_id: int | None = None,
        service_line_name: str | None = None,
        top: int | None = None,
        skip: int | None = None,
        modified_since: datetime | None = None,
    ) -> list[UserSkillsOutput]:
        """Get users with their assessed skills.

        All filters are optional and AND-combined.

        Args:
            user_id: Filter by internal user ID.
            employee_id: Filter by external employee ID.
            team_id: Filter by internal team ID.
            team_code: Filter by team code.
            business_unit_id: Filter by internal business unit ID.
            business_unit_name: Filter by business unit name.
            country_code: Filter by country code.
            legal_entity_id: Filter by internal legal entity ID.
            legal_entity_name: Filter by legal entity name.
            practice_area_id: Filter by internal practice area ID.
            practice_area_name: Filter by practice area name.
            service_line_id: Filter by internal service line ID.
            service_line_name: Filter by service line name.
            top: Maximum number of results to return (paging).
            skip: Number of results to skip (paging).
            modified_since: Only skills modified since this point in time (timezone-aware).

        Returns:
            A list of UserSkillsOutput objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userID"] = str(user_id)
        if employee_id is not None:
            params["employeeID"] = employee_id
        if team_id is not None:
            params["teamID"] = str(team_id)
        if team_code is not None:
            params["teamCode"] = team_code
        if business_unit_id is not None:
            params["businessUnitID"] = str(business_unit_id)
        if business_unit_name is not None:
            params["businessUnitName"] = business_unit_name
        if country_code is not None:
            params["countryCode"] = country_code
        if legal_entity_id is not None:
            params["legalEntityID"] = str(legal_entity_id)
        if legal_entity_name is not None:
            params["legalEntityName"] = legal_entity_name
        if practice_area_id is not None:
            params["practiceAreaID"] = str(practice_area_id)
        if practice_area_name is not None:
            params["practiceAreaName"] = practice_area_name
        if service_line_id is not None:
            params["serviceLineID"] = str(service_line_id)
        if service_line_name is not None:
            params["serviceLineName"] = service_line_name
        if top is not None:
            params["top"] = str(top)
        if skip is not None:
            params["skip"] = str(skip)
        if modified_since is not None:
            params["modifiedSince"] = _format_datetime(modified_since)

        response_text = await self._get("/importapi/Profile/UserSkills", params)
        adapter = TypeAdapter(list[UserSkillsOutput])
        return adapter.validate_json(response_text)

    async def import_profile_user_skills(
        self,
        users: list[UserSkillsImportInput],
    ) -> list[UserSkillsImportResult]:
        """Add, update, or remove the assessed skills of a batch of users.

        Args:
            users: The per-user skill assignments to import.

        Returns:
            A list of UserSkillsImportResult objects with the per-user import status.
        """
        adapter = TypeAdapter(list[UserSkillsImportInput])
        data = adapter.dump_json(users, by_alias=True, exclude_none=True).decode()
        response_text = await self._post("/importapi/Profile/UserSkills", data)
        result_adapter = TypeAdapter(list[UserSkillsImportResult])
        return result_adapter.validate_json(response_text)
