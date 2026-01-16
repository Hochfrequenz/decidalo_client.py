"""Comprehensive tests for DecidaloClient."""

from __future__ import annotations

from uuid import UUID

import pytest
from aioresponses import aioresponses

from decidalo_client import DecidaloClient
from decidalo_client.exceptions import DecidaloAPIError, DecidaloAuthenticationError
from decidalo_client.models import (
    AbsenceImportItem,
    BookingInput,
    BookingType,
    ImportAbsencesCommand,
    ImportCompanyCommand,
    ProjectReferenceIdentityInput,
    ProjectReferenceInput,
    ProjectReferencePropertiesInput,
    ResourceRequestInput,
    ResourceRequestPropertiesInput,
    ResourceRequestStatus,
    RoleIdentityInput,
    RoleImportInput,
    RolePropertiesInput,
    TeamBatchInput,
    TeamInput,
    TextFieldInput,
    UserBatchInput,
    UserIdentityInput,
    UserInput,
    UserWorkingProfileInput,
    WorkingProfileInput,
)

BASE_URL = "https://import.decidalo.dev"
API_KEY = "test-api-key"


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestContextManager:
    """Tests for async context manager functionality."""

    async def test_aenter_creates_session(self) -> None:
        """Test that __aenter__ creates an aiohttp session."""
        client = DecidaloClient(api_key=API_KEY, base_url=BASE_URL)
        assert client._session is None

        async with client:
            assert client._session is not None

    async def test_aexit_closes_session(self) -> None:
        """Test that __aexit__ closes the session."""
        client = DecidaloClient(api_key=API_KEY, base_url=BASE_URL)

        async with client:
            session = client._session
            assert session is not None

        assert client._session is None

    async def test_context_manager_returns_client(self) -> None:
        """Test that the context manager returns the client instance."""
        client = DecidaloClient(api_key=API_KEY, base_url=BASE_URL)

        async with client as ctx_client:
            assert ctx_client is client

    async def test_request_without_context_raises_error(self) -> None:
        """Test that making requests without context manager raises RuntimeError."""
        client = DecidaloClient(api_key=API_KEY, base_url=BASE_URL)
        with pytest.raises(RuntimeError, match="must be used within an async context manager"):
            await client.get_users()


# =============================================================================
# Authentication Tests
# =============================================================================


class TestAuthentication:
    """Tests for authentication functionality."""

    async def test_api_key_header_included(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test that X-Api-Key header is included in requests."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            await client.get_users()

        # Verify the request was made with proper headers
        calls = list(mock_aiohttp.requests.values())
        assert len(calls) > 0
        request = calls[0][0]
        # aioresponses stores kwargs, headers are in kwargs
        assert request.kwargs["headers"]["X-Api-Key"] == API_KEY

    async def test_401_raises_authentication_error(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test that 401 status raises DecidaloAuthenticationError."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            body="Unauthorized",
            status=401,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            with pytest.raises(DecidaloAuthenticationError) as exc_info:
                await client.get_users()

        assert exc_info.value.status_code == 401

    async def test_403_raises_authentication_error(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test that 403 status raises DecidaloAuthenticationError."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            body="Forbidden",
            status=403,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            with pytest.raises(DecidaloAuthenticationError) as exc_info:
                await client.get_users()

        assert exc_info.value.status_code == 403


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling functionality."""

    async def test_500_raises_api_error(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test that 500 status raises DecidaloAPIError."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            body="Internal Server Error",
            status=500,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            with pytest.raises(DecidaloAPIError) as exc_info:
                await client.get_users()

        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in exc_info.value.message

    async def test_400_raises_api_error(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test that 400 status raises DecidaloAPIError."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/User",
            body="Bad Request",
            status=400,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            batch = UserBatchInput(users=[])
            with pytest.raises(DecidaloAPIError) as exc_info:
                await client.import_users_async(batch)

        assert exc_info.value.status_code == 400


# =============================================================================
# Custom Base URL Tests
# =============================================================================


class TestCustomBaseUrl:
    """Tests for custom base URL functionality."""

    async def test_custom_base_url_is_used(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test that a custom base_url parameter works."""
        custom_url = "https://custom.api.example.com"
        mock_aiohttp.get(
            f"{custom_url}/importapi/User",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=custom_url) as client:
            result = await client.get_users()

        assert result == []

    async def test_trailing_slash_is_stripped(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test that trailing slash in base_url is stripped."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            payload=[],
            status=200,
        )

        async with DecidaloClient(
            api_key=API_KEY, base_url=f"{BASE_URL}/"
        ) as client:
            result = await client.get_users()

        assert result == []


# =============================================================================
# User Method Tests
# =============================================================================


class TestGetUsers:
    """Tests for get_users method."""

    async def test_get_users_empty_list(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_users returns empty list when no users exist."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_users()

        assert result == []

    async def test_get_users_with_data(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_users returns parsed user data."""
        user_data = [
            {
                "userID": 1,
                "email": "john.doe@example.com",
                "displayName": "John Doe",
                "employeeID": "EMP001",
                "employeeTypeID": 1,
                "employeeTypeName": "Employee",
                "includeInResourceManagement": True,
                "hasLogin": True,
                "creationDate": "2024-01-01T00:00:00Z",
                "lastEditDate": "2024-01-15T00:00:00Z",
            },
            {
                "userID": 2,
                "email": "jane.smith@example.com",
                "displayName": "Jane Smith",
                "employeeID": "EMP002",
                "employeeTypeID": 1,
                "employeeTypeName": "Employee",
                "includeInResourceManagement": True,
                "hasLogin": True,
                "creationDate": "2024-01-02T00:00:00Z",
                "lastEditDate": "2024-01-16T00:00:00Z",
            },
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            payload=user_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_users()

        assert len(result) == 2
        assert result[0].userID == 1
        assert result[0].email == "john.doe@example.com"
        assert result[1].userID == 2
        assert result[1].displayName == "Jane Smith"

    async def test_get_users_with_email_filter(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_users with email filter parameter."""
        user_data = [
            {
                "userID": 1,
                "email": "john.doe@example.com",
                "displayName": "John Doe",
                "employeeTypeID": 1,
                "employeeTypeName": "Employee",
                "includeInResourceManagement": True,
                "hasLogin": True,
                "creationDate": "2024-01-01T00:00:00Z",
                "lastEditDate": "2024-01-15T00:00:00Z",
            }
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User?email=john.doe%40example.com",
            payload=user_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_users(email="john.doe@example.com")

        assert len(result) == 1
        assert result[0].email == "john.doe@example.com"


class TestImportUsersAsync:
    """Tests for import_users_async method."""

    async def test_import_users_async(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_users_async returns batch ID."""
        batch_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/User",
            payload={"batchID": batch_id},
            status=202,
        )

        batch = UserBatchInput(
            users=[
                UserInput(
                    email="new.user@example.com",
                    displayName="New User",
                    employeeID="EMP003",
                )
            ]
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_users_async(batch)

        assert result.batchID == UUID(batch_id)


class TestGetUserImportStatus:
    """Tests for get_user_import_status method."""

    async def test_get_user_import_status(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_user_import_status returns batch status."""
        batch_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User/ImportStatus?batchId={batch_id}",
            payload={
                "batchID": batch_id,
                "status": {
                    "status": "Completed",
                    "errorMessage": None,
                },
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_user_import_status(UUID(batch_id))

        assert result.batchID == UUID(batch_id)
        assert result.status.status.value == "Completed"


# =============================================================================
# Team Method Tests
# =============================================================================


class TestGetTeams:
    """Tests for get_teams method."""

    async def test_get_teams_empty_list(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_teams returns empty list when no teams exist."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Team",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_teams()

        assert result == []

    async def test_get_teams_with_data(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_teams returns parsed team data."""
        team_data = [
            {
                "teamID": 1,
                "teamCode": "TEAM001",
                "teamName": "Engineering",
                "managerUserID": 10,
            },
            {
                "teamID": 2,
                "teamCode": "TEAM002",
                "teamName": "Sales",
                "managerUserID": 20,
            },
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Team",
            payload=team_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_teams()

        assert len(result) == 2
        assert result[0].teamID == 1
        assert result[0].teamName == "Engineering"
        assert result[1].teamCode == "TEAM002"


class TestImportTeamsAsync:
    """Tests for import_teams_async method."""

    async def test_import_teams_async(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_teams_async returns batch ID."""
        batch_id = "660e8400-e29b-41d4-a716-446655440001"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Team",
            payload={"batchID": batch_id},
            status=202,
        )

        batch = TeamBatchInput(
            teams=[
                TeamInput(
                    teamCode="TEAM003",
                    teamName="Marketing",
                )
            ]
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_teams_async(batch)

        assert result.batchID == UUID(batch_id)


class TestImportTeamsSync:
    """Tests for import_teams_sync method."""

    async def test_import_teams_sync(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_teams_sync returns imported teams."""
        team_data = [
            {
                "teamID": 3,
                "teamCode": "TEAM003",
                "teamName": "Marketing",
            }
        ]
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Team/ImportSync",
            payload=team_data,
            status=200,
        )

        teams = [
            TeamInput(
                teamCode="TEAM003",
                teamName="Marketing",
            )
        ]

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_teams_sync(teams)

        assert len(result) == 1
        assert result[0].teamID == 3
        assert result[0].teamName == "Marketing"


class TestGetTeamImportStatus:
    """Tests for get_team_import_status method."""

    async def test_get_team_import_status(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_team_import_status returns batch metadata."""
        batch_id = "660e8400-e29b-41d4-a716-446655440001"
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Team/ImportStatus?batchId={batch_id}",
            payload={
                "batchID": batch_id,
                "status": {
                    "status": "Processing",
                },
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_team_import_status(UUID(batch_id))

        assert result.batchID == UUID(batch_id)


# =============================================================================
# Company Method Tests
# =============================================================================


class TestGetCompanies:
    """Tests for get_companies method."""

    async def test_get_companies_empty_list(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_companies returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Company/Import",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_companies()

        assert result == []

    async def test_get_companies_with_data(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_companies returns parsed company data."""
        company_data = [
            {
                "companyID": 1,
                "companyName": "Acme Inc",
                "companyCode": "ACME001",
                "isCustomer": True,
            },
            {
                "companyID": 2,
                "companyName": "TechCorp",
                "companyCode": "TECH001",
                "isCustomer": False,
            },
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Company/Import",
            payload=company_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_companies()

        assert len(result) == 2
        assert result[0].companyID == 1
        assert result[0].companyName == "Acme Inc"
        assert result[1].isCustomer is False


class TestImportCompany:
    """Tests for import_company method."""

    async def test_import_company(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_company returns import result."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Company/Import",
            payload={
                "companyID": 3,
                "status": {
                    "status": "Created",
                },
            },
            status=200,
        )

        company = ImportCompanyCommand(
            companyName="NewCorp",
            companyCode="NEW001",
            isCustomer=True,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_company(company)

        assert result.companyID == 3
        assert result.status is not None


# =============================================================================
# Project Method Tests
# =============================================================================


class TestGetProject:
    """Tests for get_project method."""

    async def test_get_project_by_id(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_project returns project data by ID."""
        project_data = {
            "identifier": {
                "projectID": 1,
                "projectCode": "PROJ001",
            },
            "properties": {
                "name": {"value": "Test Project"},
            },
            "keywords": [],
        }
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Project?projectId=1",
            payload=project_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_project(project_id=1)

        assert result.identifier.projectID == 1
        assert result.identifier.projectCode == "PROJ001"


class TestGetAllProjects:
    """Tests for get_all_projects method."""

    async def test_get_all_projects_empty(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_all_projects returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Project/AllProjects",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_all_projects()

        assert result == []

    async def test_get_all_projects_with_data(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_all_projects returns multiple projects."""
        project_data = [
            {
                "identifier": {"projectID": 1, "projectCode": "PROJ001"},
                "properties": {"name": {"value": "Project One"}},
                "keywords": [],
            },
            {
                "identifier": {"projectID": 2, "projectCode": "PROJ002"},
                "properties": {"name": {"value": "Project Two"}},
                "keywords": [],
            },
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Project/AllProjects",
            payload=project_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_all_projects()

        assert len(result) == 2
        assert result[0].identifier.projectID == 1
        assert result[1].identifier.projectCode == "PROJ002"


class TestImportProject:
    """Tests for import_project method."""

    async def test_import_project(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_project returns import result."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Project",
            payload={
                "projectID": 3,
                "projectCode": "PROJ003",
                "success": True,
            },
            status=200,
        )

        project = ProjectReferenceInput(
            identifier=ProjectReferenceIdentityInput(projectCode="PROJ003"),
            properties=ProjectReferencePropertiesInput(
                name=TextFieldInput(value="New Project"),
            ),
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_project(project)

        assert result.projectID == 3
        assert result.success is True


class TestProjectExists:
    """Tests for project_exists method."""

    async def test_project_exists_true(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test project_exists returns True when project exists."""
        mock_aiohttp.head(
            f"{BASE_URL}/importapi/Project?projectCode=PROJ001",
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.project_exists(project_code="PROJ001")

        assert result is True

    async def test_project_exists_false(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test project_exists returns False when project doesn't exist."""
        mock_aiohttp.head(
            f"{BASE_URL}/importapi/Project?projectCode=NONEXISTENT",
            status=404,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.project_exists(project_code="NONEXISTENT")

        assert result is False


# =============================================================================
# Booking Method Tests
# =============================================================================


class TestGetBookings:
    """Tests for get_bookings method."""

    async def test_get_bookings_empty(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_bookings returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Booking",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_bookings()

        assert result == []

    async def test_get_bookings_with_data(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_bookings returns parsed booking data."""
        booking_data = [
            {
                "bookingID": 1,
                "bookingCode": "BOOK001",
                "userID": 10,
                "subject": "Project Work",
                "startDate": "2024-01-01",
                "endDate": "2024-01-31",
                "capacity": 1.0,
                "bookingType": "Confirmed",
            },
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Booking",
            payload=booking_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_bookings()

        assert len(result) == 1
        assert result[0].bookingID == 1
        assert result[0].subject == "Project Work"
        assert result[0].bookingType == BookingType.Confirmed


class TestGetBookingsByProject:
    """Tests for get_bookings_by_project method."""

    async def test_get_bookings_by_project(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_bookings_by_project returns bookings for a project."""
        booking_data = [
            {
                "bookingID": 2,
                "projectID": 1,
                "projectCode": "PROJ001",
                "userID": 20,
                "subject": "Development",
            },
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Booking/ByProject?projectId=1",
            payload=booking_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_bookings_by_project(project_id=1)

        assert len(result) == 1
        assert result[0].projectID == 1


class TestImportBookingsAsync:
    """Tests for import_bookings_async method."""

    async def test_import_bookings_async(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_bookings_async returns import results."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Booking/ImportAsync",
            payload=[
                {
                    "bookingID": 3,
                    "userID": 30,
                    "importStatus": {"status": "Created"},
                }
            ],
            status=200,
        )

        bookings = [
            BookingInput(
                bookingCode="BOOK003",
                userID=30,
                subject="New Booking",
            )
        ]

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_bookings_async(bookings)

        assert len(result) == 1
        assert result[0].bookingID == 3


# =============================================================================
# Absence Method Tests
# =============================================================================


class TestGetAbsences:
    """Tests for get_absences method."""

    async def test_get_absences(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_absences returns absence data."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Absence",
            payload={
                "absences": [
                    {
                        "absenceId": 1,
                        "userId": 10,
                        "startDate": "2024-02-01",
                        "endDate": "2024-02-05",
                        "subject": "Vacation",
                    }
                ]
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_absences()

        assert result.absences is not None
        assert len(result.absences) == 1
        assert result.absences[0].absenceId == 1


class TestImportAbsences:
    """Tests for import_absences method."""

    async def test_import_absences(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_absences returns import results."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Absence/Import",
            payload=[
                {
                    "absenceId": 2,
                    "userId": 20,
                    "startDate": "2024-03-01",
                    "endDate": "2024-03-05",
                    "importStatus": {"status": "Created"},
                }
            ],
            status=200,
        )

        absences = ImportAbsencesCommand(
            absences=[
                AbsenceImportItem(
                    userId=20,
                    startDate="2024-03-01",
                    endDate="2024-03-05",
                    subject="Conference",
                )
            ]
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_absences(absences)

        assert len(result) == 1
        assert result[0].absenceId == 2


# =============================================================================
# Resource Request Method Tests
# =============================================================================


class TestGetResourceRequest:
    """Tests for get_resource_request method."""

    async def test_get_resource_request(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_resource_request returns request data."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/ResourceRequest/123",
            payload={
                "identifier": {"requestID": 123},
                "status": "Open",
                "properties": {
                    "title": "Senior Developer",
                    "requestedCandidateCount": 2,
                },
                "lastEditDate": "2024-01-15T10:00:00Z",
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_resource_request(123)

        assert result.identifier.requestID == 123
        assert result.status == ResourceRequestStatus.Open


class TestImportResourceRequest:
    """Tests for import_resource_request method."""

    async def test_import_resource_request(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_resource_request returns import result."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/ResourceRequest",
            payload={
                "requestID": 124,
                "status": {"status": "Created"},
            },
            status=200,
        )

        request = ResourceRequestInput(
            status=ResourceRequestStatus.Open,
            properties=ResourceRequestPropertiesInput(
                title="New Developer Request",
                requestedCandidateCount=1,
            ),
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_resource_request(request)

        assert result.requestID == 124


# =============================================================================
# Role Method Tests
# =============================================================================


class TestImportRole:
    """Tests for import_role method."""

    async def test_import_role(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_role returns import result."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Role",
            payload={
                "roleID": 10,
                "success": True,
            },
            status=200,
        )

        role = RoleImportInput(
            identifier=RoleIdentityInput(roleCode="ROLE001"),
            properties=RolePropertiesInput(
                roleName=TextFieldInput(value="Software Engineer"),
            ),
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_role(role)

        assert result.roleID == 10
        assert result.success is True


# =============================================================================
# Working Time Pattern Method Tests
# =============================================================================


class TestGetWorkingTimePatterns:
    """Tests for get_working_time_patterns method."""

    async def test_get_working_time_patterns_empty(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_working_time_patterns returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkingTimePattern/Import",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_working_time_patterns()

        assert result == []

    async def test_get_working_time_patterns_with_data(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_working_time_patterns returns pattern data."""
        pattern_data = [
            {
                "userIdentity": {"userID": 10, "employeeID": "EMP010"},
                "workingTimePatterns": [
                    {
                        "userWorkingTimePatternID": 1,
                        "startDate": "2024-01-01",
                        "hoursPerWeek": 40.0,
                        "hoursPerDay": 8.0,
                    }
                ],
            }
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkingTimePattern/Import",
            payload=pattern_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_working_time_patterns()

        assert len(result) == 1
        assert result[0].userIdentity is not None
        assert result[0].userIdentity.userID == 10


class TestImportWorkingTimePattern:
    """Tests for import_working_time_pattern method."""

    async def test_import_working_time_pattern(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test import_working_time_pattern returns import result."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/WorkingTimePattern/Import",
            payload={
                "userID": 10,
                "userWorkingTimePatternResults": [
                    {
                        "userWorkingTimePatternID": 5,
                        "status": {"status": "Created"},
                    }
                ],
                "status": {"status": "Created"},
            },
            status=200,
        )

        pattern = UserWorkingProfileInput(
            userIdentity=UserIdentityInput(userID=10),
            workingTimePatterns=[
                WorkingProfileInput(
                    startDate="2024-06-01",
                    hoursPerWeek=40.0,
                    hoursPerDay=8.0,
                )
            ],
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_working_time_pattern(pattern)

        assert result.userID == 10
        assert result.userWorkingTimePatternResults is not None
        assert len(result.userWorkingTimePatternResults) == 1
