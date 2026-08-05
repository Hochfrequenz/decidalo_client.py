"""Async HTTP client for the Decidalo Import API."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import aiohttp
from pydantic import TypeAdapter

from decidalo_client.exceptions import (
    DecidaloAPIError,
    DecidaloAuthenticationError,
    DecidaloClientError,
)
from decidalo_client.models import (
    AbsenceImportResult,
    AbsenceOutputResult,
    ActivityTypeImportItem,
    ActivityTypeResult,
    BookingBatchInput,
    BookingExtendOption,
    BookingImportResult,
    BookingInput,
    BookingItemOutput,
    CompanyCompleteOutput,
    CustomProperty,
    EmployeeTypeOutput,
    GeneralActivityImportItem,
    GeneralActivityResult,
    GetImportUserWorkingProfileResult,
    ImportAbsencesCommand,
    ImportCompanyCommand,
    ImportCompanyResult,
    ImportResourceRequestCommandResult,
    ImportRoleResult,
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
    OrderPositionWorkPackageImportBatch,
    OrderPositionWorkPackageImportBatchResult,
    OrderPositionWorkPackageOutput,
    ProjectBatchInput,
    ProjectContactsExportOutput,
    ProjectRecordingTargetImportBatch,
    ProjectRecordingTargetImportBatchResult,
    ProjectRecordingTargetOutput,
    ProjectReferenceImportResult,
    ProjectReferenceInput,
    ProjectReferenceOutput,
    ProjectTeamMembersExportOutput,
    RecordingTargetOutput,
    ResourceRequestContactOutput,
    ResourceRequestInput,
    ResourceRequestOutput,
    RoleImportInput,
    TeamBatchInput,
    TeamImportAcceptedResponse,
    TeamImportResults,
    TeamInput,
    TeamOverview,
    TimeRecordingImportBatch,
    TimeRecordingImportOutputBatch,
    TimeRecordingImportResult,
    UserBatchImportMetadata,
    UserBatchInput,
    UserImportAcceptedResponse,
    UserImportBatchResult,
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
    WorkPackageOutput,
    WorkPackageRecordingTargetImportBatch,
    WorkPackageRecordingTargetImportBatchResult,
    WorkPackageRecordingTargetOutput,
    WorkPackageStatus,
)

if TYPE_CHECKING:
    from types import TracebackType

DEFAULT_BASE_URL = "https://import.decidalo.dev"


class DecidaloClient:  # pylint: disable=too-many-public-methods
    """Async client for the Decidalo Import API.

    This client provides methods to interact with the Decidalo Import API,
    including operations for users, teams, companies, projects, bookings,
    absences, resource requests, roles, and working time patterns.

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

    async def _get(self, path: str, params: dict[str, str] | None = None) -> str:
        """Make a GET request to the API.

        Args:
            path: The API path (will be appended to base_url).
            params: Optional query parameters.

        Returns:
            The response text.

        Raises:
            RuntimeError: If the client is not in a context manager.
        """
        if self._session is None:
            raise RuntimeError("Client must be used within an async context manager (async with)")

        url = f"{self._base_url}{path}"
        async with self._session.get(url, headers=self._get_headers(), params=params) as response:
            return await self._handle_response(response)

    async def _post(
        self,
        path: str,
        data: str | None = None,
        allowed_error_statuses: set[int] | None = None,
    ) -> str:
        """Make a POST request to the API.

        Args:
            path: The API path (will be appended to base_url).
            data: Optional JSON string to send as the request body.
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
        async with self._session.post(url, headers=self._get_headers(), data=data) as response:
            return await self._handle_response(response, allowed_error_statuses)

    async def _head(self, path: str) -> int:
        """Make a HEAD request to the API.

        Args:
            path: The API path (will be appended to base_url).

        Returns:
            The response status code.

        Raises:
            RuntimeError: If the client is not in a context manager.
        """
        if self._session is None:
            raise RuntimeError("Client must be used within an async context manager (async with)")

        url = f"{self._base_url}{path}"
        async with self._session.head(url, headers=self._get_headers()) as response:
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

    async def get_users(  # pylint: disable=too-many-arguments
        self,
        *,
        employee_id: str | None = None,
        user_id: int | None = None,
        email: str | None = None,
        created_since: str | None = None,
        edited_since: str | None = None,
    ) -> list[UserOverview]:
        """Get users from the API.

        Returns all users in the system. The returned list may be empty if no users
        match the given criteria.

        Args:
            employee_id: Filter by external employee ID.
            user_id: Filter by internal user ID. If provided, the email filter is ignored.
            email: Filter by email address. Must be an exact match (case insensitive).
            created_since: Filter users created since this date (ISO format).
            edited_since: Filter users edited since this date (ISO format).

        Returns:
            A list of UserOverview objects.
        """
        params: dict[str, str] = {}
        if employee_id is not None:
            params["employeeId"] = employee_id
        if user_id is not None:
            params["userId"] = str(user_id)
        if email is not None:
            params["email"] = email
        if created_since is not None:
            params["createdSince"] = created_since
        if edited_since is not None:
            params["editedSince"] = edited_since

        response_text = await self._get("/importapi/User", params or None)
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
        batch_id: UUID,
    ) -> UserImportBatchResult:
        """Get the status of a user import batch.

        Args:
            batch_id: The ID of the batch to check.

        Returns:
            A UserImportBatchResult with the current status.
        """
        response_text = await self._get("/importapi/User/ImportStatus", {"batchId": str(batch_id)})
        return UserImportBatchResult.model_validate_json(response_text)

    # =========================================================================
    # Team Methods
    # =========================================================================

    async def get_teams(
        self,
        *,
        team_id: int | None = None,
        team_code: str | None = None,
        created_since: str | None = None,
        edited_since: str | None = None,
    ) -> list[TeamOverview]:
        """Get teams from the API.

        Returns all teams in the system.

        Args:
            team_id: Filter by internal team ID.
            team_code: Filter by external team code.
            created_since: Filter teams created since this date (ISO format).
            edited_since: Filter teams edited since this date (ISO format).

        Returns:
            A list of TeamOverview objects.
        """
        params: dict[str, str] = {}
        if team_id is not None:
            params["teamId"] = str(team_id)
        if team_code is not None:
            params["teamCode"] = team_code
        if created_since is not None:
            params["createdSince"] = created_since
        if edited_since is not None:
            params["editedSince"] = edited_since

        response_text = await self._get("/importapi/Team", params or None)
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
        response_text = await self._post("/importapi/Team", data)
        return TeamImportAcceptedResponse.model_validate_json(response_text)

    async def import_teams_sync(
        self,
        teams: list[TeamInput],
    ) -> TeamImportResults:
        """Import teams synchronously.

        The import is processed synchronously. The response contains the result
        for each team in the batch, including any errors.

        Args:
            teams: The list of teams to import.

        Returns:
            A TeamImportResults with the batch status and per-item results.

        Note:
            Per the OpenAPI spec, ImportSync returns HTTP 500 with a structured
            TeamImportResults body when one or more items fail (others may still
            have succeeded). This status is therefore treated as a valid response
            so callers can inspect the per-item results instead of getting a
            generic DecidaloAPIError.
        """
        batch = TeamBatchInput(teams=teams)
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Team/ImportSync", data, allowed_error_statuses={500})
        return TeamImportResults.model_validate_json(response_text)

    async def get_team_import_status(
        self,
        batch_id: UUID,
    ) -> UserBatchImportMetadata:
        """Get the status of a team import batch.

        Args:
            batch_id: The ID of the batch to check.

        Returns:
            A UserBatchImportMetadata with the current status.
        """
        response_text = await self._get("/importapi/Team/ImportStatus", {"batchId": str(batch_id)})
        return UserBatchImportMetadata.model_validate_json(response_text)

    # =========================================================================
    # Company Methods
    # =========================================================================

    async def get_companies(
        self,
        *,
        company_id: int | None = None,
        company_code: str | None = None,
        company_name: str | None = None,
    ) -> list[CompanyCompleteOutput]:
        """Get companies from the API.

        Returns all companies in the system.

        Args:
            company_id: Filter by internal company ID.
            company_code: Filter by external company code.
            company_name: Filter by company name.

        Returns:
            A list of CompanyCompleteOutput objects.
        """
        params: dict[str, str] = {}
        if company_id is not None:
            params["companyId"] = str(company_id)
        if company_code is not None:
            params["companyCode"] = company_code
        if company_name is not None:
            params["companyName"] = company_name

        response_text = await self._get("/importapi/Company/Import", params or None)
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
            params["projectId"] = str(project_id)
        if project_code is not None:
            params["projectCode"] = project_code

        response_text = await self._get("/importapi/Project", params or None)
        return ProjectReferenceOutput.model_validate_json(response_text)

    async def get_all_projects(
        self,
        *,
        created_since: str | None = None,
        edited_since: str | None = None,
    ) -> list[ProjectReferenceOutput]:
        """Get all projects from the API.

        Returns the core project data for all existing projects.

        Args:
            created_since: Filter projects created since this date (ISO format).
            edited_since: Filter projects edited since this date (ISO format).

        Returns:
            A list of ProjectReferenceOutput objects.
        """
        params: dict[str, str] = {}
        if created_since is not None:
            params["createdSince"] = created_since
        if edited_since is not None:
            params["editedSince"] = edited_since

        response_text = await self._get("/importapi/Project/AllProjects", params or None)
        adapter = TypeAdapter(list[ProjectReferenceOutput])
        return adapter.validate_json(response_text)

    async def import_project(
        self,
        project: ProjectReferenceInput,
    ) -> ProjectReferenceImportResult:
        """Import or update a project.

        Args:
            project: The project data to import.

        Returns:
            A ProjectReferenceImportResult with the import status.
        """
        data = project.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Project", data)
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
            True if the project exists, False otherwise.
        """
        params: dict[str, str] = {}
        if project_id is not None:
            params["projectId"] = str(project_id)
        if project_code is not None:
            params["projectCode"] = project_code

        # Build query string manually for HEAD request
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        path = f"/importapi/Project?{query_string}" if query_string else "/importapi/Project"

        status = await self._head(path)
        return status == 200

    # =========================================================================
    # Booking Methods
    # =========================================================================

    async def get_bookings(  # pylint: disable=too-many-arguments
        self,
        *,
        employee_id: str | None = None,
        user_id: int | None = None,
        booking_id: int | None = None,
        booking_code: str | None = None,
        created_since: str | None = None,
        edited_since: str | None = None,
    ) -> list[BookingItemOutput]:
        """Get bookings from the API.

        Args:
            employee_id: Filter by external employee ID.
            user_id: Filter by internal user ID.
            booking_id: Filter by internal booking ID.
            booking_code: Filter by external booking code.
            created_since: Filter bookings created since this date (ISO format).
            edited_since: Filter bookings edited since this date (ISO format).

        Returns:
            A list of BookingItemOutput objects.
        """
        params: dict[str, str] = {}
        if employee_id is not None:
            params["employeeId"] = employee_id
        if user_id is not None:
            params["userId"] = str(user_id)
        if booking_id is not None:
            params["bookingId"] = str(booking_id)
        if booking_code is not None:
            params["bookingCode"] = booking_code
        if created_since is not None:
            params["createdSince"] = created_since
        if edited_since is not None:
            params["editedSince"] = edited_since

        response_text = await self._get("/importapi/Booking", params or None)
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

        response_text = await self._get("/importapi/Booking/ByProject", params or None)
        adapter = TypeAdapter(list[BookingItemOutput])
        return adapter.validate_json(response_text)

    async def import_bookings_async(
        self,
        bookings: list[BookingInput],
    ) -> list[BookingImportResult]:
        """Import a batch of bookings.

        When the booking type property is not set, it won't be changed through the import.
        The default value on creation is 'Reservation'.

        Args:
            bookings: The list of bookings to import.

        Returns:
            A list of BookingImportResult objects with the import status.
        """
        batch = BookingBatchInput(elements=bookings)
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Booking/ImportAsync", data)
        adapter = TypeAdapter(list[BookingImportResult])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Absence Methods
    # =========================================================================

    async def get_absences(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AbsenceOutputResult:
        """Get absences from the API.

        Returns all absences within the given timeframe.
        If no timeframe is provided, all absences are returned.

        Args:
            start_date: If provided, only absences occurring after this date will be returned.
            end_date: If provided, only absences occurring before this date will be returned.

        Returns:
            An AbsenceOutputResult object containing the list of absences.
        """
        params: dict[str, str] = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        response_text = await self._get("/importapi/Absence", params or None)
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
    ) -> ResourceRequestOutput:
        """Get a resource request by ID.

        Args:
            request_id: The internal resource request ID.

        Returns:
            A ResourceRequestOutput object.
        """
        response_text = await self._get(f"/importapi/ResourceRequest/{request_id}")
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

        The correct endpoint per the OpenAPI spec is GET /importapi/WorkingTimePattern.
        Note: the API only supports filtering by UserId, not by employeeId.

        Args:
            user_id: Optional filter by internal user ID.

        Returns:
            A list of GetImportUserWorkingProfileResult objects.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["UserId"] = str(user_id)

        response_text = await self._get("/importapi/WorkingTimePattern", params or None)
        adapter = TypeAdapter(list[GetImportUserWorkingProfileResult])
        return adapter.validate_json(response_text)

    async def import_working_time_pattern(
        self,
        pattern: UserWorkingProfileInput,
    ) -> ImportUserWorkingProfileResult:
        """Create or update a working time pattern.

        The input allows only for start dates and no end dates. All working time patterns
        will be created/updated with the given start dates, and then the corresponding
        end dates will be calculated automatically to one day before the next start date.

        Args:
            pattern: The working time pattern data to import.

        Returns:
            An ImportUserWorkingProfileResult with the import status.
        """
        adapter = TypeAdapter(list[UserWorkingProfileInput])
        data = adapter.dump_json([pattern], by_alias=True, exclude_none=True).decode()
        response_text = await self._post("/importapi/WorkingTimePattern/Import", data)
        result_adapter = TypeAdapter(list[ImportUserWorkingProfileResult])
        results = result_adapter.validate_json(response_text)
        if not results:
            raise DecidaloClientError("API returned empty result for import_working_time_pattern")
        return results[0]

    # =========================================================================
    # Activity Type Methods
    # =========================================================================

    async def get_activity_types(self) -> list[ActivityTypeResult]:
        """Get all activity types in the system.

        Returns:
            A list of ActivityTypeResult objects.
        """
        response_text = await self._get("/importapi/ActivityType")
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
    # Order Methods
    # =========================================================================

    async def get_orders(
        self,
        *,
        project_reference_id: int | None = None,
        project_code: str | None = None,
    ) -> OrderImportOutputBatch:
        """Get orders with their positions.

        Args:
            project_reference_id: Filter by the internal project reference ID.
            project_code: Filter by the external project code.

        Returns:
            An OrderImportOutputBatch containing the matching orders.
        """
        params: dict[str, str] = {}
        if project_reference_id is not None:
            params["projectReferenceId"] = str(project_reference_id)
        if project_code is not None:
            params["projectCode"] = project_code

        response_text = await self._get("/importapi/Order", params or None)
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

        response_text = await self._get("/importapi/Order/Single", params or None)
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

        response_text = await self._get("/importapi/Order/Position/Single", params or None)
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

        response_text = await self._get("/importapi/Order/Position/RecordingTargets", params or None)
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

        response_text = await self._get("/importapi/Order/Position/WorkPackages", params or None)
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
        start_date_before: str | None = None,
        end_date_after: str | None = None,
        created_on_or_after: str | None = None,
        last_updated_on_or_after: str | None = None,
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
            start_date_before: Only work packages starting before this date (ISO format).
            end_date_after: Only work packages ending after this date (ISO format).
            created_on_or_after: Incremental-sync filter on creation timestamp (ISO format).
            last_updated_on_or_after: Incremental-sync filter on update timestamp (ISO format).
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
            params["StartDateBefore"] = start_date_before
        if end_date_after is not None:
            params["EndDateAfter"] = end_date_after
        if created_on_or_after is not None:
            params["CreatedOnOrAfter"] = created_on_or_after
        if last_updated_on_or_after is not None:
            params["LastUpdatedOnOrAfter"] = last_updated_on_or_after
        if top is not None:
            params["Top"] = str(top)
        if skip is not None:
            params["Skip"] = str(skip)

        response_text = await self._get("/importapi/WorkPackage", params or None)
        adapter = TypeAdapter(list[WorkPackageOutput])
        return adapter.validate_json(response_text)

    async def get_work_package(
        self,
        workpackage_id: int,
    ) -> WorkPackageOutput:
        """Get a specific work package by ID.

        Args:
            workpackage_id: The internal work package ID.

        Returns:
            A WorkPackageOutput object.
        """
        response_text = await self._get(f"/importapi/WorkPackage/{workpackage_id}")
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

        response_text = await self._get("/importapi/WorkPackage/Candidates", params or None)
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

        response_text = await self._get("/importapi/WorkPackage/OrderPositions", params or None)
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

        response_text = await self._get("/importapi/WorkPackage/RecordingTargets", params or None)
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
        general_activity_id: int | None = None,
        general_activity_code: str | None = None,
        activity_type_id: int | None = None,
        activity_type_code: str | None = None,
        is_active: bool | None = None,
    ) -> list[RecordingTargetOutput]:
        """Get the tenant's recording targets across all subject kinds.

        Covers project, work package, general activity, and order position targets.
        All filters are optional and AND-combined. Only active targets are returned
        unless is_active is set (True = active only, False = inactive only).

        Args:
            project_reference_id: Filter by internal project reference ID.
            project_code: Filter by external project code.
            work_package_id: Filter by internal work package ID.
            work_package_code: Filter by work package code.
            order_position_id: Filter by internal order position ID.
            general_activity_id: Filter by internal general activity ID.
            general_activity_code: Filter by general activity code.
            activity_type_id: Filter by internal activity type ID.
            activity_type_code: Filter by activity type code.
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
        if general_activity_id is not None:
            params["generalActivityId"] = str(general_activity_id)
        if general_activity_code is not None:
            params["generalActivityCode"] = general_activity_code
        if activity_type_id is not None:
            params["activityTypeId"] = str(activity_type_id)
        if activity_type_code is not None:
            params["activityTypeCode"] = activity_type_code
        if is_active is not None:
            params["isActive"] = str(is_active).lower()

        response_text = await self._get("/importapi/TimeRecording/RecordingTargets", params or None)
        adapter = TypeAdapter(list[RecordingTargetOutput])
        return adapter.validate_json(response_text)

    async def get_user_time_sheet(
        self,
        *,
        user_id: int | None = None,
        employee_id: str | None = None,
        email: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> TimeRecordingImportOutputBatch:
        """Get a user's timesheet.

        Args:
            user_id: The internal user ID.
            employee_id: The external employee ID.
            email: The user's email address.
            start_date: Only entries on or after this date (ISO format).
            end_date: Only entries on or before this date (ISO format).

        Returns:
            A TimeRecordingImportOutputBatch with the user's entries and work times.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["userId"] = str(user_id)
        if employee_id is not None:
            params["employeeId"] = employee_id
        if email is not None:
            params["email"] = email
        if start_date is not None:
            params["startDate"] = start_date
        if end_date is not None:
            params["endDate"] = end_date

        response_text = await self._get("/importapi/TimeRecording/UserTimeSheet", params or None)
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

        response_text = await self._get("/importapi/Profile/Industries", params or None)
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

        response_text = await self._get("/importapi/Profile/Languages", params or None)
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

        response_text = await self._get("/importapi/Profile/ProfessionalExperience", params or None)
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

        response_text = await self._get("/importapi/Profile/Publications", params or None)
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

        response_text = await self._get("/importapi/Profile/Testimonials", params or None)
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

        response_text = await self._get("/importapi/Profile/Trainings", params or None)
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
        modified_since: str | None = None,
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
            modified_since: Only skills modified since this date (ISO format).

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
            params["modifiedSince"] = modified_since

        response_text = await self._get("/importapi/Profile/UserSkills", params or None)
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

    # =========================================================================
    # Project (extended) Methods
    # =========================================================================

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

        response_text = await self._get("/importapi/Project/Contacts", params or None)
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

        response_text = await self._get("/importapi/Project/TeamMembers", params or None)
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

        response_text = await self._get("/importapi/Project/RecordingTargets", params or None)
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
        path = "/importapi/Project/ImportBatch"
        if booking_extend_option is not None:
            path = f"{path}?bookingExtendOption={booking_extend_option.value}"
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post(path, data)
        adapter = TypeAdapter(list[ProjectReferenceImportResult])
        return adapter.validate_json(response_text)

    # =========================================================================
    # Resource Request (extended) Methods
    # =========================================================================

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

        response_text = await self._get("/importapi/ResourceRequest/Contacts", params or None)
        adapter = TypeAdapter(list[ResourceRequestContactOutput])
        return adapter.validate_json(response_text)

    # =========================================================================
    # User (extended) Methods
    # =========================================================================

    async def get_employee_types(self) -> list[EmployeeTypeOutput]:
        """Get all employee types. Names are returned in English.

        Returns:
            A list of EmployeeTypeOutput objects.
        """
        response_text = await self._get("/importapi/User/EmployeeTypes")
        adapter = TypeAdapter(list[EmployeeTypeOutput])
        return adapter.validate_json(response_text)
