"""Comprehensive tests for DecidaloClient."""

from __future__ import annotations

from uuid import UUID

import pytest
from aioresponses import aioresponses

from decidalo_client import DecidaloClient
from decidalo_client import models as dm
from decidalo_client.exceptions import DecidaloAPIError, DecidaloAuthenticationError

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
            batch = dm.UserBatchInput(users=[])
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
# Request Helper Tests
# =============================================================================


def requested_urls(mock: aioresponses) -> list[str]:
    """Return the URLs of all requests recorded by the aioresponses mock, in request order."""
    return [str(url) for _, url in mock.requests]


class TestRequestHelpers:
    """Tests for the internal request helpers."""

    async def test_get_sends_list_values_as_repeated_keys(self, mock_aiohttp: aioresponses) -> None:
        """Test that list values are sent as repeated query keys, as the API expects for arrays."""
        mock_aiohttp.get(f"{BASE_URL}/importapi/Order?projectCode=A&projectCode=B&top=5", payload={}, status=200)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            await client._get("/importapi/Order", {"projectCode": ["A", "B"], "top": "5"})

        assert requested_urls(mock_aiohttp) == [f"{BASE_URL}/importapi/Order?projectCode=A&projectCode=B&top=5"]

    async def test_get_without_params_sends_no_query(self, mock_aiohttp: aioresponses) -> None:
        """Test that empty query parameters do not produce a query string."""
        mock_aiohttp.get(f"{BASE_URL}/importapi/Team", payload=[], status=200)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            await client._get("/importapi/Team", {})

        assert requested_urls(mock_aiohttp) == [f"{BASE_URL}/importapi/Team"]

    async def test_post_sends_query_params(self, mock_aiohttp: aioresponses) -> None:
        """Test that _post sends query parameters alongside the body."""
        mock_aiohttp.post(f"{BASE_URL}/importapi/Project/Import?bookingExtendOption=UpdateBookingDatesOnly", payload={})

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            await client._post(
                "/importapi/Project/Import", "{}", params={"bookingExtendOption": "UpdateBookingDatesOnly"}
            )

        assert requested_urls(mock_aiohttp) == [
            f"{BASE_URL}/importapi/Project/Import?bookingExtendOption=UpdateBookingDatesOnly"
        ]

    async def test_head_url_encodes_query_params(self, mock_aiohttp: aioresponses) -> None:
        """Test that _head URL-encodes query parameter values."""
        mock_aiohttp.head(f"{BASE_URL}/importapi/Project?projectcode=A%26B%23C", status=204)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            status = await client._head("/importapi/Project", {"projectcode": "A&B#C"})

        assert status == 204
        assert requested_urls(mock_aiohttp) == [f"{BASE_URL}/importapi/Project?projectcode=A%26B%23C"]


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
                "lastLoginDate": "2026-09-01T08:00:00Z",
                "isImported": True,
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
                "lastLoginDate": None,
                "isImported": False,
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
        assert result[0].lastLoginDate is not None
        assert result[0].lastLoginDate.year == 2026
        assert result[1].userID == 2
        assert result[1].displayName == "Jane Smith"
        assert result[1].lastLoginDate is None

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
                "lastLoginDate": "2026-09-01T08:00:00Z",
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

        batch = dm.UserBatchInput(
            users=[
                dm.UserInput(
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

        batch = dm.UserBatchInput(
            users=[
                dm.UserInput(
                    email="new.user@example.com",
                    displayName="New User",
                    employeeID="EMP003",
                ),
                dm.UserInput(
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

        batch = dm.UserBatchInput(
            users=[
                dm.UserInput(
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
        """Test get_user_import_status returns the list of matching import batches."""
        batch_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User/ImportStatus?batchid={batch_id}",
            payload=[
                {
                    "batchID": batch_id,
                    "creationDate": "2026-09-01T08:00:00Z",
                    "startDate": "2026-09-01T08:00:01Z",
                    "endDate": "2026-09-01T08:00:05Z",
                    "status": {"status": "Completed", "errorMessage": None},
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_user_import_status(batch_id=UUID(batch_id))

        assert len(result) == 1
        assert isinstance(result[0], dm.UserBatchImportMetadata)
        assert result[0].batchID == UUID(batch_id)
        assert result[0].status is not None
        assert result[0].status.status == dm.ImportBatchStatusType.Completed

    async def test_get_user_import_status_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_user_import_status sends all filters and parses the row results."""
        batch_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User/ImportStatus?top=5&batchid={batch_id}&status=Failed&includeRowResults=true",
            payload=[
                {
                    "batchID": batch_id,
                    "status": {"status": "Failed", "errorMessage": "One or more items have failed."},
                    "rowResults": [
                        {"rowIndex": 0, "status": "Failed", "errorMessage": "Invalid email", "email": "broken"},
                    ],
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_user_import_status(
                top=5,
                batch_id=UUID(batch_id),
                status=dm.ImportBatchStatusType.Failed,
                include_row_results=True,
            )

        assert result[0].rowResults is not None
        assert result[0].rowResults[0].status == dm.ImportItemStatusType.Failed
        assert result[0].rowResults[0].errorMessage == "Invalid email"


class TestEmployeeTypesEndpoint:
    """Tests for the get_employee_types method."""

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
        """Test import_teams_async posts to /Team/ImportAsync and returns the batch ID."""
        batch_id = "660e8400-e29b-41d4-a716-446655440001"
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Team/ImportAsync",
            payload={"batchID": batch_id},
            status=200,
        )

        batch = dm.TeamBatchInput(
            teams=[
                dm.TeamInput(
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
            dm.TeamInput(
                teamCode="TEAM003",
                teamName="Marketing",
            )
        ]

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_teams_sync(dm.TeamBatchInput(teams=teams))

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
            dm.TeamInput(teamCode="TEAM003", teamName="Marketing"),
            dm.TeamInput(teamCode="TEAM004", teamName="Sales"),
        ]

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_teams_sync(dm.TeamBatchInput(teams=teams))

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
        """Test get_team_import_status returns the list of matching import batches."""
        batch_id = "660e8400-e29b-41d4-a716-446655440001"
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Team/ImportStatus?batchid={batch_id}",
            payload=[{"batchID": batch_id, "status": {"status": "Processing"}}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_team_import_status(batch_id=UUID(batch_id))

        assert len(result) == 1
        assert isinstance(result[0], dm.BatchImportMetadata)
        assert result[0].batchID == UUID(batch_id)
        assert result[0].status is not None
        assert result[0].status.status == dm.ImportBatchStatusType.Processing

    async def test_get_team_import_status_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_team_import_status sends all filters and parses the team row results."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Team/ImportStatus?top=3&status=Completed&includeRowResults=false",
            payload=[
                {
                    "batchID": "660e8400-e29b-41d4-a716-446655440001",
                    "status": {"status": "Completed"},
                    "rowResults": [{"rowIndex": 0, "status": "Created", "teamID": 3, "teamCode": "TEAM003"}],
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_team_import_status(
                top=3, status=dm.ImportBatchStatusType.Completed, include_row_results=False
            )

        assert result[0].rowResults is not None
        assert result[0].rowResults[0].teamCode == "TEAM003"


# =============================================================================
# Company Method Tests
# =============================================================================


class TestGetCompanies:
    """Tests for get_companies method."""

    async def test_get_companies_empty_list(self, mock_aiohttp: aioresponses) -> None:
        """Test get_companies returns empty list."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Company",
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
            f"{BASE_URL}/importapi/Company",
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

        company = dm.ImportCompanyCommand(
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
                "businessUnit": {"id": 3, "value": "Consulting"},
                "accountingType": {"id": 1, "value": "Billable"},
            },
            "keywords": [],
            "creator": {"userID": 1},
            "lastEditor": {"userID": 1},
        }
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Project?projectid=1",
            payload=project_data,
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_project(project_id=1)

        assert result.identifier.projectID == 1
        assert result.identifier.projectCode == "PROJ001"
        assert result.properties.businessUnit == dm.SelectOptionFieldInput(id=3, value="Consulting")
        assert result.properties.accountingType == dm.SelectOptionFieldInput(id=1, value="Billable")


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
                "properties": {
                    "name": {"value": "Project Two"},
                    "projectStatus": {"id": 2, "value": "Active"},
                },
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
        assert result[1].properties.projectStatus is not None
        assert result[1].properties.projectStatus.value == "Active"


class TestImportProject:
    """Tests for import_project method."""

    async def test_import_project(self, mock_aiohttp: aioresponses) -> None:
        """Test import_project posts to /Project/Import and returns the import result."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Project/Import",
            payload={
                "projectID": 3,
                "projectCode": "PROJ003",
                "success": True,
                "status": "Created",
            },
            status=200,
        )

        project = dm.ProjectReferenceInput(
            identifier=dm.ProjectReferenceIdentityInput(projectCode="PROJ003"),
            properties=dm.ProjectReferencePropertiesInput(
                name=dm.TextFieldInput(value="New Project"),
            ),
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_project(project)

        assert result.projectID == 3
        assert result.success is True
        assert result.status == dm.ImportItemStatusType.Created

    async def test_import_project_with_booking_extend_option(self, mock_aiohttp: aioresponses) -> None:
        """Test import_project sends the booking extend option as query parameter."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Project/Import?bookingExtendOption=RedistributePersonDays",
            payload={"projectID": 3, "success": True},
            status=200,
        )

        project = dm.ProjectReferenceInput(
            identifier=dm.ProjectReferenceIdentityInput(projectCode="PROJ003"),
            properties=dm.ProjectReferencePropertiesInput(name=dm.TextFieldInput(value="New Project")),
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_project(
                project, booking_extend_option=dm.BookingExtendOption.RedistributePersonDays
            )

        assert result.projectID == 3


class TestProjectExists:
    """Tests for project_exists method."""

    async def test_project_exists_true(self, mock_aiohttp: aioresponses) -> None:
        """Test project_exists returns True for HTTP 204, which the API returns for an existing project."""
        mock_aiohttp.head(
            f"{BASE_URL}/importapi/Project?projectcode=PROJ001",
            status=204,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.project_exists(project_code="PROJ001")

        assert result is True

    async def test_project_exists_by_id(self, mock_aiohttp: aioresponses) -> None:
        """Test project_exists sends the project ID as query parameter."""
        mock_aiohttp.head(
            f"{BASE_URL}/importapi/Project?projectid=1",
            status=204,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.project_exists(project_id=1)

        assert result is True

    async def test_project_exists_false(self, mock_aiohttp: aioresponses) -> None:
        """Test project_exists returns False when project doesn't exist."""
        mock_aiohttp.head(
            f"{BASE_URL}/importapi/Project?projectcode=NONEXISTENT",
            status=404,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.project_exists(project_code="NONEXISTENT")

        assert result is False

    @pytest.mark.parametrize("status", [400, 500])
    async def test_project_exists_raises_on_unexpected_status(self, mock_aiohttp: aioresponses, status: int) -> None:
        """Test project_exists raises instead of reporting a missing project for other error statuses."""
        mock_aiohttp.head(f"{BASE_URL}/importapi/Project", status=status)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            with pytest.raises(DecidaloAPIError) as exc_info:
                await client.project_exists()

        assert exc_info.value.status_code == status

    async def test_project_exists_url_encodes_project_code(self, mock_aiohttp: aioresponses) -> None:
        """Test project_exists URL-encodes the project code instead of splitting it at '&'."""
        mock_aiohttp.head(f"{BASE_URL}/importapi/Project?projectcode=R%26D", status=204)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.project_exists(project_code="R&D")

        assert result is True
        assert requested_urls(mock_aiohttp) == [f"{BASE_URL}/importapi/Project?projectcode=R%26D"]


class TestProjectEndpoints:
    """Tests for the project contacts, team members, recording targets and batch import methods."""

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
            payload=[
                {"projectReferenceID": 42, "recordingTypes": [{"recordingTypeID": 3, "recordingTypeCode": "TRAVEL"}]}
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_project_recording_targets()

        assert len(result) == 1
        assert isinstance(result[0], dm.ProjectRecordingTargetOutput)
        assert result[0].projectReferenceID == 42
        assert result[0].recordingTypes == [
            dm.RecordingTypeReferenceOutput(recordingTypeID=3, recordingTypeCode="TRAVEL")
        ]

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

    async def test_import_projects_with_booking_extend_option(self, mock_aiohttp: aioresponses) -> None:
        """Test import_projects sends the booking extend option as query parameter."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Project/ImportBatch?bookingExtendOption=UpdateBookingsAndPlanning",
            payload=[{"projectID": 42}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_projects(
                dm.ProjectBatchInput(projects=[]),
                booking_extend_option=dm.BookingExtendOption.UpdateBookingsAndPlanning,
            )

        assert result[0].projectID == 42


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
        assert result[0].bookingType == dm.BookingType.Confirmed


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
            dm.BookingInput(
                bookingCode="BOOK003",
                userID=30,
                subject="New Booking",
            )
        ]

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_bookings_async(dm.BookingBatchInput(elements=bookings))

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
                        "minutesPerDay": 240.0,
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
        assert result.absences[0].minutesPerDay == 240.0


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
                    "minutesPerDay": 480.0,
                    "importStatus": {"status": "Created"},
                }
            ],
            status=200,
        )

        absences = dm.ImportAbsencesCommand(
            absences=[
                dm.AbsenceImportItem(
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
        assert result[0].minutesPerDay == 480.0


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
                "accountingType": {"accountingTypeID": 1, "accountingTypeName": "Billable"},
                "serviceCategory": {"serviceCategoryID": 4, "serviceCategoryName": "Senior Consultant"},
                "creationDate": "2024-01-10T08:00:00Z",
                "lastEditDate": "2024-01-15T10:00:00Z",
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_resource_request(123)

        assert result.identifier.requestID == 123
        assert result.status == dm.ResourceRequestStatus.Open
        assert result.accountingType is not None
        assert result.accountingType.accountingTypeName == "Billable"
        assert result.serviceCategory is not None
        assert result.serviceCategory.serviceCategoryID == 4


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

        request = dm.ResourceRequestInput(
            status=dm.ResourceRequestStatus.Open,
            properties=dm.ResourceRequestPropertiesInput(
                title="New Developer Request",
                requestedCandidateCount=1,
            ),
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_resource_request(request)

        assert result.requestID == 124


class TestResourceRequestContactsEndpoint:
    """Tests for the get_resource_request_contacts method."""

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

        role = dm.RoleImportInput(
            identifier=dm.RoleIdentityInput(roleCode="ROLE001"),
            properties=dm.RolePropertiesInput(
                roleName=dm.TextFieldTranslationInput(value="Software Engineer"),
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


class TestImportWorkingTimePatterns:
    """Tests for import_working_time_patterns method."""

    async def test_import_working_time_patterns(self, mock_aiohttp: aioresponses) -> None:
        """Test import_working_time_patterns sends the list of patterns and returns the per-user results."""
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

        pattern = dm.UserWorkingProfileInput(
            userIdentity=dm.UserIdentityInput(userID=10),
            workingTimePatterns=[
                dm.WorkingProfileInput(
                    startDate="2024-06-01",
                    hoursPerWeek=40.0,
                    hoursPerDay=8.0,
                )
            ],
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_working_time_patterns([pattern])

        assert len(result) == 1
        assert result[0].userID == 10
        assert result[0].userWorkingTimePatternResults is not None
        assert len(result[0].userWorkingTimePatternResults) == 1


# =============================================================================
# Activity Type and General Activity Method Tests
# =============================================================================


class TestActivitiesEndpoints:
    """Tests for the activity type and general activity methods."""

    async def test_get_activity_types(self, mock_aiohttp: aioresponses) -> None:
        """Test get_activity_types hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/ActivityType",
            payload=[{"activityTypeID": 42, "code": "DEV", "category": "Consulting", "targetSystemCode": "SAP-DEV"}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_activity_types()

        assert len(result) == 1
        assert isinstance(result[0], dm.ActivityTypeResult)
        assert result[0].activityTypeID == 42
        assert result[0].category == "Consulting"
        assert result[0].targetSystemCode == "SAP-DEV"

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
            payload=[
                {
                    "generalActivityID": 42,
                    "code": "TRAINING",
                    "targetSystemCode": "SAP-TRN",
                    "recordingTargetID": 7,
                    "recordingTypeIDs": [1, 2],
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_general_activities()

        assert len(result) == 1
        assert isinstance(result[0], dm.GeneralActivityResult)
        assert result[0].generalActivityID == 42
        assert result[0].recordingTargetID == 7
        assert result[0].recordingTypeIDs == [1, 2]

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


# =============================================================================
# Order Method Tests
# =============================================================================


class TestOrderEndpoints:
    """Tests for the order methods."""

    async def test_get_orders(self, mock_aiohttp: aioresponses) -> None:
        """Test get_orders hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order",
            payload={
                "orders": [
                    {
                        "orderID": 42,
                        "code": "ORDER-1",
                        "projects": [{"projectReferenceID": 7, "projectCode": "PROJ001"}],
                        "validFromDate": "2026-01-01",
                        "expiryDate": "2026-12-31",
                        "positions": [{"orderPositionID": 1, "rateID": 5, "rateCode": "RATE-1"}],
                    }
                ]
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_orders()

        assert isinstance(result, dm.OrderImportOutputBatch)
        assert result.orders is not None
        order = result.orders[0]
        assert order.projects == [dm.OrderProjectImportItem(projectReferenceID=7, projectCode="PROJ001")]
        assert order.expiryDate is not None
        assert order.expiryDate.year == 2026
        assert order.positions is not None
        assert order.positions[0].rateCode == "RATE-1"

    async def test_get_order(self, mock_aiohttp: aioresponses) -> None:
        """Test get_order hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order/Single",
            payload={"orderID": 42, "projects": [{"projectCode": "PROJ001"}], "validFromDate": "2026-01-01"},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order()

        assert isinstance(result, dm.OrderImportOutput)
        assert result.orderID == 42
        assert result.projects == [dm.OrderProjectImportItem(projectCode="PROJ001")]

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
            payload={"orderID": 42, "orderPositionID": 1, "rateID": 5, "rateCode": "RATE-1"},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order_position()

        assert isinstance(result, dm.OrderPositionImportOutput)
        assert result.orderID == 42
        assert result.rateID == 5
        assert result.rateCode == "RATE-1"

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
            payload=[
                {
                    "orderPositionID": 42,
                    "orderPositionCode": "POS-1",
                    "orderID": 1,
                    "orderCode": "ORDER-1",
                    "recordingTypes": [{"recordingTypeID": 3, "recordingTypeCode": "TRAVEL"}],
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order_position_recording_targets()

        assert len(result) == 1
        assert isinstance(result[0], dm.OrderPositionRecordingTargetOutput)
        assert result[0].orderPositionID == 42
        assert result[0].orderCode == "ORDER-1"
        assert result[0].recordingTypes == [
            dm.RecordingTypeReferenceOutput(recordingTypeID=3, recordingTypeCode="TRAVEL")
        ]

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


# =============================================================================
# Work Package Method Tests
# =============================================================================


class TestWorkPackageEndpoints:
    """Tests for the work package methods."""

    async def test_get_work_packages(self, mock_aiohttp: aioresponses) -> None:
        """Test get_work_packages hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkPackage",
            payload=[
                {
                    "creationDate": "2024-01-01T00:00:00Z",
                    "identifier": {"workPackageID": 1, "workPackageCode": "WP-1"},
                    "lastEditDate": "2024-01-01T00:00:00Z",
                    "project": {"projectID": 1},
                    "properties": {"name": "x", "status": "Planned", "timeRecordingAllowed": True, "sortOrder": 2},
                    "customProperties": {"costCenter": "4711"},
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_packages()

        assert len(result) == 1
        assert isinstance(result[0], dm.WorkPackageOutput)
        assert result[0].identifier.workPackageCode == "WP-1"
        assert result[0].properties.sortOrder == 2
        assert result[0].customProperties == {"costCenter": "4711"}

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
            payload=[{"workPackageID": 42, "recordingTypes": [{"recordingTypeID": 3, "recordingTypeCode": "TRAVEL"}]}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_package_recording_targets()

        assert len(result) == 1
        assert isinstance(result[0], dm.WorkPackageRecordingTargetOutput)
        assert result[0].workPackageID == 42
        assert result[0].recordingTypes == [
            dm.RecordingTypeReferenceOutput(recordingTypeID=3, recordingTypeCode="TRAVEL")
        ]

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


# =============================================================================
# Time Recording Method Tests
# =============================================================================


class TestTimeRecordingEndpoints:
    """Tests for the time recording methods."""

    async def test_get_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test get_recording_targets hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/TimeRecording/RecordingTargets",
            payload=[
                {
                    "recordingTargetID": 42,
                    "orderID": 1,
                    "orderCode": "ORDER-1",
                    "recordingTypes": [{"recordingTypeID": 3, "recordingTypeCode": "TRAVEL"}],
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_recording_targets()

        assert len(result) == 1
        assert isinstance(result[0], dm.RecordingTargetOutput)
        assert result[0].recordingTargetID == 42
        assert result[0].orderCode == "ORDER-1"
        assert result[0].recordingTypes == [
            dm.RecordingTypeReferenceOutput(recordingTypeID=3, recordingTypeCode="TRAVEL")
        ]

    async def test_get_user_time_sheet(self, mock_aiohttp: aioresponses) -> None:
        """Test get_user_time_sheet hits the correct endpoint and parses the response."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/TimeRecording/UserTimeSheet",
            payload={
                "entries": [
                    {
                        "recordingEntryID": 1,
                        "userID": 10,
                        "workDate": "2026-09-01",
                        "timeMinutes": 480,
                        "status": "Open",
                        "recordingTypeValues": [{"recordingTypeCode": "TRAVEL", "value": 1.5}],
                        "orderID": 3,
                        "rateCode": "RATE-1",
                        "creationDate": "2026-09-01T17:00:00Z",
                        "lastEditDate": "2026-09-02T08:00:00Z",
                    }
                ],
                "workTimes": [],
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_user_time_sheet()

        assert isinstance(result, dm.TimeRecordingImportOutputBatch)
        assert result.entries is not None
        entry = result.entries[0]
        assert entry.status == dm.TimeRecordingEntryStatus.Open
        assert entry.recordingTypeValues == [dm.RecordingEntryTypeValueImport(recordingTypeCode="TRAVEL", value=1.5)]
        assert entry.rateCode == "RATE-1"

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


# =============================================================================
# Profile Export Method Tests
# =============================================================================


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
