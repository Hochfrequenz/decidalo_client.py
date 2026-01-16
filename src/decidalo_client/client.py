"""Async HTTP client for the Decidalo Import API."""

from __future__ import annotations

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
    BookingBatchInput,
    BookingImportResult,
    BookingInput,
    BookingItemOutput,
    CompanyCompleteOutput,
    GetImportUserWorkingProfileResult,
    ImportAbsencesCommand,
    ImportCompanyCommand,
    ImportCompanyResult,
    ImportResourceRequestCommandResult,
    ImportRoleResult,
    ImportUserWorkingProfileResult,
    ProjectReferenceImportResult,
    ProjectReferenceInput,
    ProjectReferenceOutput,
    ResourceRequestInput,
    ResourceRequestOutput,
    RoleImportInput,
    TeamBatchInput,
    TeamImportAcceptedResponse,
    TeamInput,
    TeamOverview,
    UserBatchImportMetadata,
    UserBatchInput,
    UserImportAcceptedResponse,
    UserImportBatchResult,
    UserOverview,
    UserWorkingProfileInput,
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

    async def _handle_response(self, response: aiohttp.ClientResponse) -> str:
        """Handle the API response and raise appropriate exceptions.

        Args:
            response: The aiohttp response object.

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

    async def _post(self, path: str, data: str | None = None) -> str:
        """Make a POST request to the API.

        Args:
            path: The API path (will be appended to base_url).
            data: Optional JSON string to send as the request body.

        Returns:
            The response text.

        Raises:
            RuntimeError: If the client is not in a context manager.
        """
        if self._session is None:
            raise RuntimeError("Client must be used within an async context manager (async with)")

        url = f"{self._base_url}{path}"
        async with self._session.post(url, headers=self._get_headers(), data=data) as response:
            return await self._handle_response(response)

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
        response_text = await self._post("/importapi/User", data)
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
    ) -> list[TeamOverview]:
        """Import teams synchronously.

        The import is processed synchronously. This method waits for the import
        to complete before returning. Any callback URL in the batch is ignored.

        Args:
            teams: The list of teams to import.

        Returns:
            A list of TeamOverview objects representing the imported teams.
        """
        batch = TeamBatchInput(teams=teams)
        data = batch.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/Team/ImportSync", data)
        adapter = TypeAdapter(list[TeamOverview])
        return adapter.validate_json(response_text)

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
        employee_id: str | None = None,
        user_id: int | None = None,
    ) -> list[GetImportUserWorkingProfileResult]:
        """Get all working time patterns from the API.

        Args:
            employee_id: Filter by external employee ID.
            user_id: Optional filter by internal user ID.

        Returns:
            A list of GetImportUserWorkingProfileResult objects.
        """
        params: dict[str, str] = {}
        if employee_id is not None:
            params["employeeId"] = employee_id
        if user_id is not None:
            params["userId"] = str(user_id)

        response_text = await self._get("/importapi/WorkingTimePattern/Import", params or None)
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
        data = pattern.model_dump_json(by_alias=True, exclude_none=True)
        response_text = await self._post("/importapi/WorkingTimePattern/Import", data)
        return ImportUserWorkingProfileResult.model_validate_json(response_text)
