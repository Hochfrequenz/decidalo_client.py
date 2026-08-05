"""Comprehensive tests for DecidaloClient."""

from __future__ import annotations

from uuid import UUID

import pytest
from aioresponses import aioresponses

from decidalo_client import DecidaloClient
from decidalo_client import models as dm
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
    TextFieldTranslationInput,
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

    async def test_api_key_header_included(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_401_raises_authentication_error(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_403_raises_authentication_error(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_500_raises_api_error(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_400_raises_api_error(self, mock_aiohttp: aioresponses) -> None:
        """Test that 400 status raises DecidaloAPIError."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/User/ImportSync",
            body="Bad Request",
            status=400,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            batch = UserBatchInput(users=[])
            with pytest.raises(DecidaloAPIError) as exc_info:
                await client.import_users_sync(batch)

        assert exc_info.value.status_code == 400


# =============================================================================
# Custom Base URL Tests
# =============================================================================


class TestCustomBaseUrl:
    """Tests for custom base URL functionality."""

    async def test_custom_base_url_is_used(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_trailing_slash_is_stripped(self, mock_aiohttp: aioresponses) -> None:
        """Test that trailing slash in base_url is stripped."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=f"{BASE_URL}/") as client:
            result = await client.get_users()

        assert result == []


# =============================================================================
# User Method Tests
# =============================================================================


class TestGetUsers:
    """Tests for get_users method."""

    async def test_get_users_empty_list(self, mock_aiohttp: aioresponses) -> None:
        """Test get_users returns empty list when no users exist."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_users()

        assert result == []

    async def test_get_users_with_data(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_get_users_with_email_filter(self, mock_aiohttp: aioresponses) -> None:
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


class TestImportUsersSync:
    """Tests for import_users_sync method."""

    async def test_import_users_sync(self, mock_aiohttp: aioresponses) -> None:
        """Test import_users_sync returns full sync result with items."""
        batch_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/User/ImportSync",
            payload={
                "batchID": batch_id,
                "status": "Completed",
                "errorMessage": None,
                "items": [
                    {
                        "rowIndex": 0,
                        "status": "Created",
                        "errorMessage": None,
                        "userID": 42,
                        "email": "new.user@example.com",
                        "employeeID": "EMP003",
                    }
                ],
            },
            status=200,
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
            result = await client.import_users_sync(batch)

        assert result.batchID == UUID(batch_id)
        assert result.status == "Completed"
        assert result.items is not None
        assert len(result.items) == 1
        assert result.items[0].status == "Created"
        assert result.items[0].email == "new.user@example.com"
        assert result.items[0].userID == 42

    async def test_import_users_sync_returns_results_on_500(self, mock_aiohttp: aioresponses) -> None:
        """Test import_users_sync returns UserImportResults when the API responds with HTTP 500.

        Per the OpenAPI spec, ImportSync returns 500 with a structured
        UserImportResults body when one or more items fail. The client must
        surface those per-item results instead of raising a DecidaloAPIError.
        """
        batch_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/User/ImportSync",
            payload={
                "batchID": batch_id,
                "status": "Failed",
                "errorMessage": "One or more items have failed.",
                "items": [
                    {
                        "rowIndex": 0,
                        "status": "Created",
                        "errorMessage": None,
                        "userID": 42,
                        "email": "new.user@example.com",
                        "employeeID": "EMP003",
                    },
                    {
                        "rowIndex": 1,
                        "status": "Failed",
                        "errorMessage": "Invalid email address",
                        "userID": None,
                        "email": "broken",
                        "employeeID": "EMP004",
                    },
                ],
            },
            status=500,
        )

        batch = UserBatchInput(
            users=[
                UserInput(
                    email="new.user@example.com",
                    displayName="New User",
                    employeeID="EMP003",
                ),
                UserInput(
                    email="broken",
                    displayName="Broken User",
                    employeeID="EMP004",
                ),
            ]
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_users_sync(batch)

        assert result.batchID == UUID(batch_id)
        assert result.status == "Failed"
        assert result.items is not None
        assert len(result.items) == 2
        assert result.items[0].status == "Created"
        assert result.items[1].status == "Failed"
        assert result.items[1].errorMessage == "Invalid email address"


class TestImportUsersAsync:
    """Tests for import_users_async method."""

    async def test_import_users_async(self, mock_aiohttp: aioresponses) -> None:
        """Test import_users_async returns batch ID for polling."""
        batch_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/User/ImportAsync",
            payload={"batchID": batch_id},
            status=200,
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

    async def test_get_user_import_status(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_get_teams_empty_list(self, mock_aiohttp: aioresponses) -> None:
        """Test get_teams returns empty list when no teams exist."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Team",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_teams()

        assert result == []

    async def test_get_teams_with_data(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_import_teams_async(self, mock_aiohttp: aioresponses) -> None:
        """Test import_teams_async returns batch ID."""
        batch_id = "660e8400-e29b-41d4-a716-446655440001"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Team",
            payload={"batchID": batch_id},
            status=200,
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

    async def test_import_teams_sync(self, mock_aiohttp: aioresponses) -> None:
        """Test import_teams_sync returns full sync result with items."""
        batch_id = "660e8400-e29b-41d4-a716-446655440001"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Team/ImportSync",
            payload={
                "batchID": batch_id,
                "status": "Completed",
                "errorMessage": None,
                "items": [
                    {
                        "rowIndex": 0,
                        "status": "Created",
                        "errorMessage": None,
                        "teamID": 3,
                        "teamCode": "TEAM003",
                    }
                ],
            },
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

        assert result.batchID == UUID(batch_id)
        assert result.status == "Completed"
        assert result.items is not None
        assert len(result.items) == 1
        assert result.items[0].status == "Created"
        assert result.items[0].teamID == 3
        assert result.items[0].teamCode == "TEAM003"

    async def test_import_teams_sync_returns_results_on_500(self, mock_aiohttp: aioresponses) -> None:
        """Test import_teams_sync returns TeamImportResults when the API responds with HTTP 500.

        Per the OpenAPI spec, ImportSync returns 500 with a structured
        TeamImportResults body when one or more items fail. The client must
        surface those per-item results instead of raising a DecidaloAPIError.
        """
        batch_id = "660e8400-e29b-41d4-a716-446655440001"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Team/ImportSync",
            payload={
                "batchID": batch_id,
                "status": "Failed",
                "errorMessage": "One or more items have failed.",
                "items": [
                    {
                        "rowIndex": 0,
                        "status": "Created",
                        "errorMessage": None,
                        "teamID": 3,
                        "teamCode": "TEAM003",
                    },
                    {
                        "rowIndex": 1,
                        "status": "Failed",
                        "errorMessage": "Team code already exists",
                        "teamID": None,
                        "teamCode": "TEAM004",
                    },
                ],
            },
            status=500,
        )

        teams = [
            TeamInput(teamCode="TEAM003", teamName="Marketing"),
            TeamInput(teamCode="TEAM004", teamName="Sales"),
        ]

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_teams_sync(teams)

        assert result.batchID == UUID(batch_id)
        assert result.status == "Failed"
        assert result.items is not None
        assert len(result.items) == 2
        assert result.items[0].status == "Created"
        assert result.items[1].status == "Failed"
        assert result.items[1].errorMessage == "Team code already exists"


class TestGetTeamImportStatus:
    """Tests for get_team_import_status method."""

    async def test_get_team_import_status(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_get_companies_empty_list(self, mock_aiohttp: aioresponses) -> None:
        """Test get_companies returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Company/Import",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_companies()

        assert result == []

    async def test_get_companies_with_data(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_import_company(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_get_project_by_id(self, mock_aiohttp: aioresponses) -> None:
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
            "creator": {"userID": 1},
            "lastEditor": {"userID": 1},
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

    async def test_get_all_projects_empty(self, mock_aiohttp: aioresponses) -> None:
        """Test get_all_projects returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Project/AllProjects",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_all_projects()

        assert result == []

    async def test_get_all_projects_with_data(self, mock_aiohttp: aioresponses) -> None:
        """Test get_all_projects returns multiple projects."""
        project_data = [
            {
                "identifier": {"projectID": 1, "projectCode": "PROJ001"},
                "properties": {"name": {"value": "Project One"}},
                "keywords": [],
                "creator": {"userID": 1},
                "lastEditor": {"userID": 1},
            },
            {
                "identifier": {"projectID": 2, "projectCode": "PROJ002"},
                "properties": {"name": {"value": "Project Two"}},
                "keywords": [],
                "creator": {"userID": 1},
                "lastEditor": {"userID": 1},
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

    async def test_import_project(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_project_exists_true(self, mock_aiohttp: aioresponses) -> None:
        """Test project_exists returns True when project exists."""
        mock_aiohttp.head(
            f"{BASE_URL}/importapi/Project?projectCode=PROJ001",
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.project_exists(project_code="PROJ001")

        assert result is True

    async def test_project_exists_false(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_get_bookings_empty(self, mock_aiohttp: aioresponses) -> None:
        """Test get_bookings returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Booking",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_bookings()

        assert result == []

    async def test_get_bookings_with_data(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_get_bookings_by_project(self, mock_aiohttp: aioresponses) -> None:
        """Test get_bookings_by_project returns bookings for a project."""
        booking_data = [
            {
                "bookingID": 2,
                "projectID": 1,
                "projectCode": "PROJ001",
                "userID": 20,
                "subject": "Development",
                "bookingType": "Confirmed",
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

    async def test_import_bookings_async(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_get_absences(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_import_absences(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_get_resource_request(self, mock_aiohttp: aioresponses) -> None:
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
                "metrics": {},
                "creationDate": "2024-01-10T08:00:00Z",
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

    async def test_import_resource_request(self, mock_aiohttp: aioresponses) -> None:
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

    async def test_import_role(self, mock_aiohttp: aioresponses) -> None:
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
                roleName=TextFieldTranslationInput(value="Software Engineer"),
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

    async def test_get_working_time_patterns_empty(self, mock_aiohttp: aioresponses) -> None:
        """Test get_working_time_patterns returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkingTimePattern",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_working_time_patterns()

        assert result == []

    async def test_get_working_time_patterns_with_data(self, mock_aiohttp: aioresponses) -> None:
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
            f"{BASE_URL}/importapi/WorkingTimePattern",
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

    async def test_import_working_time_pattern(self, mock_aiohttp: aioresponses) -> None:
        """Test import_working_time_pattern returns import result."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/WorkingTimePattern/Import",
            payload=[
                {
                    "userID": 10,
                    "userWorkingTimePatternResults": [
                        {
                            "userWorkingTimePatternID": 5,
                            "status": {"status": "Created"},
                        }
                    ],
                    "status": {"status": "Created"},
                }
            ],
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


# =============================================================================
# New API endpoint tests (import API spec sync)
# =============================================================================


class TestActivitiesEndpoints:
    """Tests for the activity type and general activity methods."""

    async def test_get_activity_types(self, mock_aiohttp: aioresponses) -> None:
        """Test get_activity_types hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/ActivityType",
            payload=[{"activityTypeID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_activity_types()

        assert len(result) == 1
        assert isinstance(result[0], dm.ActivityTypeResult)
        assert result[0].activityTypeID == 42

    async def test_import_activity_type(self, mock_aiohttp: aioresponses) -> None:
        """Test import_activity_type hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/ActivityType",
            payload={"activityTypeID": 42},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_activity_type(dm.ActivityTypeImportItem())

        assert isinstance(result, dm.ActivityTypeResult)
        assert result.activityTypeID == 42

    async def test_get_general_activities(self, mock_aiohttp: aioresponses) -> None:
        """Test get_general_activities hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/GeneralActivity",
            payload=[{"generalActivityID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_general_activities()

        assert len(result) == 1
        assert isinstance(result[0], dm.GeneralActivityResult)
        assert result[0].generalActivityID == 42

    async def test_import_general_activity(self, mock_aiohttp: aioresponses) -> None:
        """Test import_general_activity hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/GeneralActivity",
            payload={"generalActivityID": 42},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_general_activity(dm.GeneralActivityImportItem())

        assert isinstance(result, dm.GeneralActivityResult)
        assert result.generalActivityID == 42


class TestOrderEndpoints:
    """Tests for the order methods."""

    async def test_get_orders(self, mock_aiohttp: aioresponses) -> None:
        """Test get_orders hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_orders()

        assert isinstance(result, dm.OrderImportOutputBatch)

    async def test_get_order(self, mock_aiohttp: aioresponses) -> None:
        """Test get_order hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order/Single",
            payload={"orderID": 42},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order()

        assert isinstance(result, dm.OrderImportOutput)
        assert result.orderID == 42

    async def test_import_orders(self, mock_aiohttp: aioresponses) -> None:
        """Test import_orders hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Order",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_orders(dm.OrderImportBatch())

        assert isinstance(result, dm.OrderImportBatchResult)

    async def test_get_order_custom_properties(self, mock_aiohttp: aioresponses) -> None:
        """Test get_order_custom_properties hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order/CustomProperties",
            payload=[{"maxLength": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order_custom_properties()

        assert len(result) == 1
        assert isinstance(result[0], dm.CustomProperty)
        assert result[0].maxLength == 42

    async def test_get_order_position(self, mock_aiohttp: aioresponses) -> None:
        """Test get_order_position hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order/Position/Single",
            payload={"orderID": 42},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order_position()

        assert isinstance(result, dm.OrderPositionImportOutput)
        assert result.orderID == 42

    async def test_import_order_positions(self, mock_aiohttp: aioresponses) -> None:
        """Test import_order_positions hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Order/Position",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_order_positions(dm.OrderPositionImportBatch())

        assert isinstance(result, dm.OrderPositionImportBatchResult)

    async def test_get_order_position_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test get_order_position_recording_targets hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order/Position/RecordingTargets",
            payload=[{"orderPositionID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order_position_recording_targets()

        assert len(result) == 1
        assert isinstance(result[0], dm.OrderPositionRecordingTargetOutput)
        assert result[0].orderPositionID == 42

    async def test_import_order_position_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test import_order_position_recording_targets hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Order/Position/RecordingTargets",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_order_position_recording_targets(dm.OrderPositionRecordingTargetImportBatch())

        assert isinstance(result, dm.OrderPositionRecordingTargetImportBatchResult)

    async def test_get_order_position_work_packages(self, mock_aiohttp: aioresponses) -> None:
        """Test get_order_position_work_packages hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order/Position/WorkPackages",
            payload=[{"orderPositionID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order_position_work_packages()

        assert len(result) == 1
        assert isinstance(result[0], dm.OrderPositionWorkPackageOutput)
        assert result[0].orderPositionID == 42

    async def test_import_order_position_work_packages(self, mock_aiohttp: aioresponses) -> None:
        """Test import_order_position_work_packages hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Order/Position/WorkPackages",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_order_position_work_packages(dm.OrderPositionWorkPackageImportBatch())

        assert isinstance(result, dm.OrderPositionWorkPackageImportBatchResult)


class TestWorkPackageEndpoints:
    """Tests for the work package methods."""

    async def test_get_work_packages(self, mock_aiohttp: aioresponses) -> None:
        """Test get_work_packages hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkPackage",
            payload=[
                {
                    "creationDate": "2024-01-01T00:00:00Z",
                    "identifier": {"workPackageID": 1},
                    "lastEditDate": "2024-01-01T00:00:00Z",
                    "project": {"projectID": 1},
                    "properties": {"name": "x", "status": "Planned", "timeRecordingAllowed": True},
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_packages()

        assert len(result) == 1
        assert isinstance(result[0], dm.WorkPackageOutput)

    async def test_get_work_package(self, mock_aiohttp: aioresponses) -> None:
        """Test get_work_package hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkPackage/1",
            payload={
                "creationDate": "2024-01-01T00:00:00Z",
                "identifier": {"workPackageID": 1},
                "lastEditDate": "2024-01-01T00:00:00Z",
                "project": {"projectID": 1},
                "properties": {"name": "x", "status": "Planned", "timeRecordingAllowed": True},
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_package(1)

        assert isinstance(result, dm.WorkPackageOutput)

    async def test_import_work_package(self, mock_aiohttp: aioresponses) -> None:
        """Test import_work_package hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/WorkPackage",
            payload={"workPackageID": 42},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_work_package(dm.WorkPackageInput())

        assert isinstance(result, dm.ImportWorkPackageCommandResult)
        assert result.workPackageID == 42

    async def test_get_work_package_candidates(self, mock_aiohttp: aioresponses) -> None:
        """Test get_work_package_candidates hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkPackage/Candidates",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_package_candidates()

        assert isinstance(result, dm.WorkPackageCandidateBatchInput)

    async def test_import_work_package_candidates(self, mock_aiohttp: aioresponses) -> None:
        """Test import_work_package_candidates hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/WorkPackage/Candidates",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_work_package_candidates(dm.WorkPackageCandidateBatchInput())

        assert isinstance(result, dm.WorkPackageCandidateBatchResult)

    async def test_get_work_package_order_positions(self, mock_aiohttp: aioresponses) -> None:
        """Test get_work_package_order_positions hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkPackage/OrderPositions",
            payload=[{"workPackageID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_package_order_positions()

        assert len(result) == 1
        assert isinstance(result[0], dm.WorkPackageOrderPositionOutput)
        assert result[0].workPackageID == 42

    async def test_import_work_package_order_positions(self, mock_aiohttp: aioresponses) -> None:
        """Test import_work_package_order_positions hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/WorkPackage/OrderPositions",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_work_package_order_positions(dm.WorkPackageOrderPositionImportBatch())

        assert isinstance(result, dm.WorkPackageOrderPositionImportBatchResult)

    async def test_get_work_package_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test get_work_package_recording_targets hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkPackage/RecordingTargets",
            payload=[{"workPackageID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_package_recording_targets()

        assert len(result) == 1
        assert isinstance(result[0], dm.WorkPackageRecordingTargetOutput)
        assert result[0].workPackageID == 42

    async def test_import_work_package_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test import_work_package_recording_targets hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/WorkPackage/RecordingTargets",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_work_package_recording_targets(dm.WorkPackageRecordingTargetImportBatch())

        assert isinstance(result, dm.WorkPackageRecordingTargetImportBatchResult)


class TestTimeRecordingEndpoints:
    """Tests for the time recording methods."""

    async def test_get_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test get_recording_targets hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/TimeRecording/RecordingTargets",
            payload=[{"recordingTargetID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_recording_targets()

        assert len(result) == 1
        assert isinstance(result[0], dm.RecordingTargetOutput)
        assert result[0].recordingTargetID == 42

    async def test_get_user_time_sheet(self, mock_aiohttp: aioresponses) -> None:
        """Test get_user_time_sheet hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/TimeRecording/UserTimeSheet",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_user_time_sheet()

        assert isinstance(result, dm.TimeRecordingImportOutputBatch)

    async def test_import_user_time_sheet(self, mock_aiohttp: aioresponses) -> None:
        """Test import_user_time_sheet hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/TimeRecording/UserTimeSheet",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_user_time_sheet(dm.TimeRecordingImportBatch())

        assert isinstance(result, dm.TimeRecordingImportResult)


class TestProfileExportEndpoints:
    """Tests for the profile export methods."""

    async def test_get_profile_industries(self, mock_aiohttp: aioresponses) -> None:
        """Test get_profile_industries hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Profile/Industries",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_profile_industries()

        assert len(result) == 1
        assert isinstance(result[0], dm.UserIndustryExportOutput)

    async def test_get_profile_languages(self, mock_aiohttp: aioresponses) -> None:
        """Test get_profile_languages hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Profile/Languages",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_profile_languages()

        assert len(result) == 1
        assert isinstance(result[0], dm.UserLanguageExportOutput)

    async def test_get_profile_professional_experience(self, mock_aiohttp: aioresponses) -> None:
        """Test get_profile_professional_experience hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Profile/ProfessionalExperience",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_profile_professional_experience()

        assert len(result) == 1
        assert isinstance(result[0], dm.UserProfessionalExperienceExportOutput)

    async def test_get_profile_publications(self, mock_aiohttp: aioresponses) -> None:
        """Test get_profile_publications hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Profile/Publications",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_profile_publications()

        assert len(result) == 1
        assert isinstance(result[0], dm.UserPublicationExportOutput)

    async def test_get_profile_testimonials(self, mock_aiohttp: aioresponses) -> None:
        """Test get_profile_testimonials hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Profile/Testimonials",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_profile_testimonials()

        assert len(result) == 1
        assert isinstance(result[0], dm.UserTestimonialExportOutput)

    async def test_get_profile_trainings(self, mock_aiohttp: aioresponses) -> None:
        """Test get_profile_trainings hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Profile/Trainings",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_profile_trainings()

        assert len(result) == 1
        assert isinstance(result[0], dm.UserTrainingExportOutput)

    async def test_get_profile_user_skills(self, mock_aiohttp: aioresponses) -> None:
        """Test get_profile_user_skills hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Profile/UserSkills",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_profile_user_skills()

        assert len(result) == 1
        assert isinstance(result[0], dm.UserSkillsOutput)

    async def test_import_profile_user_skills(self, mock_aiohttp: aioresponses) -> None:
        """Test import_profile_user_skills hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Profile/UserSkills",
            payload=[{"userID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_profile_user_skills([dm.UserSkillsImportInput()])

        assert len(result) == 1
        assert isinstance(result[0], dm.UserSkillsImportResult)
        assert result[0].userID == 42


class TestProjectExtendedEndpoints:
    """Tests for the project (extended) methods."""

    async def test_get_project_contacts(self, mock_aiohttp: aioresponses) -> None:
        """Test get_project_contacts hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Project/Contacts",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_project_contacts()

        assert len(result) == 1
        assert isinstance(result[0], dm.ProjectContactsExportOutput)

    async def test_get_project_team_members(self, mock_aiohttp: aioresponses) -> None:
        """Test get_project_team_members hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Project/TeamMembers",
            payload=[{}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_project_team_members()

        assert len(result) == 1
        assert isinstance(result[0], dm.ProjectTeamMembersExportOutput)

    async def test_get_project_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test get_project_recording_targets hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Project/RecordingTargets",
            payload=[{"projectReferenceID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_project_recording_targets()

        assert len(result) == 1
        assert isinstance(result[0], dm.ProjectRecordingTargetOutput)
        assert result[0].projectReferenceID == 42

    async def test_import_project_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test import_project_recording_targets hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Project/RecordingTargets",
            payload={},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_project_recording_targets(dm.ProjectRecordingTargetImportBatch())

        assert isinstance(result, dm.ProjectRecordingTargetImportBatchResult)

    async def test_import_projects(self, mock_aiohttp: aioresponses) -> None:
        """Test import_projects hits the correct endpoint and parses the response."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Project/ImportBatch",
            payload=[{"projectID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_projects(dm.ProjectBatchInput(projects=[]))

        assert len(result) == 1
        assert isinstance(result[0], dm.ProjectReferenceImportResult)
        assert result[0].projectID == 42


class TestResourceRequestContactsEndpoint:
    """Tests for the resource request (extended) methods."""

    async def test_get_resource_request_contacts(self, mock_aiohttp: aioresponses) -> None:
        """Test get_resource_request_contacts hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/ResourceRequest/Contacts",
            payload=[{"contactType": "ProjectManager", "isPrimary": True, "request": {"requestID": 1}, "user": {}}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_resource_request_contacts()

        assert len(result) == 1
        assert isinstance(result[0], dm.ResourceRequestContactOutput)
        assert result[0].isPrimary is True


class TestEmployeeTypesEndpoint:
    """Tests for the user (extended) methods."""

    async def test_get_employee_types(self, mock_aiohttp: aioresponses) -> None:
        """Test get_employee_types hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User/EmployeeTypes",
            payload=[{"employeeTypeID": 42, "employeeTypeName": "x", "isDefault": True, "isExternal": True}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_employee_types()

        assert len(result) == 1
        assert isinstance(result[0], dm.EmployeeTypeOutput)
        assert result[0].employeeTypeID == 42
