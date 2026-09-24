"""Comprehensive tests for DecidaloClient."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta, timezone
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
    """Return the URLs of all requests recorded by the aioresponses mock.

    aioresponses normalizes the URLs, i.e. the query parameters are sorted.
    """
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


class TestDateQueryParameters:
    """Tests for query parameters of format date and date-time."""

    async def test_dates_and_datetimes_are_sent_in_iso_format(self, mock_aiohttp: aioresponses) -> None:
        """Test that dates are sent as YYYY-MM-DD and datetimes with their UTC offset."""
        url = (
            f"{BASE_URL}/importapi/WorkPackage?StartDateBefore=2026-01-31&EndDateAfter=2026-01-01"
            "&CreatedOnOrAfter=2026-01-01T00:00:00%2B00:00&LastUpdatedOnOrAfter=2026-01-01T12:30:00%2B02:00"
        )
        mock_aiohttp.get(url, payload=[], status=200)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            await client.get_work_packages(
                start_date_before=date(2026, 1, 31),
                end_date_after=date(2026, 1, 1),
                created_on_or_after=datetime(2026, 1, 1, tzinfo=UTC),
                last_updated_on_or_after=datetime(2026, 1, 1, 12, 30, tzinfo=timezone(timedelta(hours=2))),
            )

        assert len(requested_urls(mock_aiohttp)) == 1

    async def test_get_absences_sends_datetimes(self, mock_aiohttp: aioresponses) -> None:
        """Test get_absences sends its time range as ISO 8601 timestamps."""
        url = f"{BASE_URL}/importapi/Absence?startDate=2026-02-01T00:00:00%2B00:00&endDate=2026-02-28T00:00:00%2B00:00"
        mock_aiohttp.get(url, payload={"absences": []}, status=200)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_absences(
                start_date=datetime(2026, 2, 1, tzinfo=UTC), end_date=datetime(2026, 2, 28, tzinfo=UTC)
            )

        assert result.absences == []

    async def test_naive_datetime_is_rejected(self) -> None:
        """Test that a datetime without timezone is rejected, as the API would assume its local time."""
        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            with pytest.raises(ValueError, match="timezone-aware datetime required"):
                await client.get_profile_user_skills(modified_since=datetime(2026, 1, 1))

    async def test_datetime_for_date_parameter_is_rejected(self) -> None:
        """Test that a datetime passed to a date parameter is rejected instead of silently truncated."""
        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            with pytest.raises(TypeError, match="expected a date, got a datetime"):
                await client.get_user_time_sheet(start_date=datetime(2026, 1, 1, tzinfo=UTC))


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

    async def test_get_users_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_users sends every filter under the query key of the spec."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/User?userid=1&employeeID=EMP001&email=john.doe%40example.com"
            "&top=10&skip=20&countryCode=DE",
            payload=[
                {
                    "userID": 1,
                    "email": "john.doe@example.com",
                    "displayName": "John Doe",
                    "employeeID": "EMP001",
                    "countryCode": "DE",
                    "employeeTypeID": 1,
                    "employeeTypeName": "Employee",
                    "includeInResourceManagement": True,
                    "hasLogin": True,
                    "creationDate": "2024-01-01T00:00:00Z",
                    "lastEditDate": "2024-01-15T00:00:00Z",
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_users(
                user_id=1,
                employee_id="EMP001",
                email="john.doe@example.com",
                top=10,
                skip=20,
                country_code="DE",
            )

        assert len(result) == 1
        assert result[0].userID == 1
        assert result[0].employeeID == "EMP001"
        assert result[0].countryCode == "DE"


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

    async def test_get_all_projects_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_all_projects sends every filter under the query key of the spec."""
        url = (
            f"{BASE_URL}/importapi/Project/AllProjects?projectID=1&projectCode=PROJ001"
            "&onlyProjectsWithProjectCode=true&isCentralProject=false&companyID=2&companyCode=CUST-1"
            "&countryCode=DE&businessUnitID=3&businessUnitName=Consulting&practiceAreaID=4"
            "&practiceAreaName=Energy&legalEntityID=5&legalEntityName=ACME-GmbH&serviceLineID=6"
            "&serviceLineName=Development&deliveryModelID=7&deliveryModelName=Onsite"
            "&startDateBefore=2026-12-31&endDateAfter=2026-01-01&createdOnOrAfter=2025-01-01T00:00:00%2B00:00"
            "&modifiedSince=2026-09-01T08:30:00%2B00:00&lastImportedOnOrAfter=2026-09-01T00:00:00%2B00:00"
            "&top=25&skip=50"
        )
        mock_aiohttp.get(
            url,
            payload=[
                {
                    "identifier": {"projectID": 1, "projectCode": "PROJ001"},
                    "properties": {"name": {"value": "Project One"}},
                    "keywords": [],
                    "creator": {"userID": 1},
                    "lastEditor": {"userID": 1},
                    "lastImportedDate": "2026-09-02T10:00:00Z",
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_all_projects(
                project_id=1,
                project_code="PROJ001",
                only_projects_with_project_code=True,
                is_central_project=False,
                company_id=2,
                company_code="CUST-1",
                country_code="DE",
                business_unit_id=3,
                business_unit_name="Consulting",
                practice_area_id=4,
                practice_area_name="Energy",
                legal_entity_id=5,
                legal_entity_name="ACME-GmbH",
                service_line_id=6,
                service_line_name="Development",
                delivery_model_id=7,
                delivery_model_name="Onsite",
                start_date_before=date(2026, 12, 31),
                end_date_after=date(2026, 1, 1),
                created_on_or_after=datetime(2025, 1, 1, tzinfo=UTC),
                modified_since=datetime(2026, 9, 1, 8, 30, tzinfo=UTC),
                last_imported_on_or_after=datetime(2026, 9, 1, tzinfo=UTC),
                top=25,
                skip=50,
            )

        assert len(result) == 1
        assert result[0].identifier.projectCode == "PROJ001"
        assert result[0].lastImportedDate == datetime(2026, 9, 2, 10, 0, tzinfo=UTC)


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

    async def test_get_bookings_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_bookings sends every filter under the query key of the spec."""
        url = (
            f"{BASE_URL}/importapi/Booking?BookingID=1&BookingCode=BOOK001&ProjectID=7&ProjectCode=PROJ001"
            "&RequestID=123&UserID=10&EmployeeID=EMP001&UsersBusinessUnitID=3&UsersBusinessUnitName=Consulting"
            "&UsersPracticeAreaID=4&UsersPracticeAreaName=Energy&UsersTeamID=5&UsersTeamCode=TEAM-A"
            "&UsersLegalEntityID=6&UsersLegalEntityName=ACME-GmbH&StartDateBefore=2026-12-31"
            "&EndDateAfter=2026-01-01&CreatedOnOrAfter=2026-01-01T00:00:00%2B00:00"
            "&LastUpdatedOnOrAfter=2026-09-01T08:30:00%2B00:00&LastImportedOnOrAfter=2026-09-01T00:00:00%2B00:00"
            "&PlanningGranularity=Weekly&PlanningStartDate=2026-09-01&PlanningEndDate=2026-09-30"
            "&ExcludeDailyPlanning=true&Top=50&Skip=100&Email=john.doe%40example.com"
        )
        mock_aiohttp.get(
            url,
            payload=[
                {
                    "bookingID": 1,
                    "bookingCode": "BOOK001",
                    "userID": 10,
                    "subject": "Project Work",
                    "projectID": 7,
                    "requestID": 123,
                    "bookingType": "Confirmed",
                    "weeklyPlanning": [{"dateInWeek": "2026-09-07", "hoursPerWeek": 20.0}],
                    "lastImportedDate": "2026-09-02T10:00:00Z",
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_bookings(
                booking_id=1,
                booking_code="BOOK001",
                project_id=7,
                project_code="PROJ001",
                request_id=123,
                user_id=10,
                employee_id="EMP001",
                users_business_unit_id=3,
                users_business_unit_name="Consulting",
                users_practice_area_id=4,
                users_practice_area_name="Energy",
                users_team_id=5,
                users_team_code="TEAM-A",
                users_legal_entity_id=6,
                users_legal_entity_name="ACME-GmbH",
                start_date_before=date(2026, 12, 31),
                end_date_after=date(2026, 1, 1),
                created_on_or_after=datetime(2026, 1, 1, tzinfo=UTC),
                last_updated_on_or_after=datetime(2026, 9, 1, 8, 30, tzinfo=UTC),
                last_imported_on_or_after=datetime(2026, 9, 1, tzinfo=UTC),
                planning_granularity=dm.ImportPlanningGranularity.Weekly,
                planning_start_date=date(2026, 9, 1),
                planning_end_date=date(2026, 9, 30),
                exclude_daily_planning=True,
                top=50,
                skip=100,
                email="john.doe@example.com",
            )

        assert len(result) == 1
        assert result[0].bookingID == 1
        assert result[0].requestID == 123
        assert result[0].weeklyPlanning == [dm.WeeklyPlanningItem(dateInWeek=date(2026, 9, 7), hoursPerWeek=20.0)]
        assert result[0].lastImportedDate == datetime(2026, 9, 2, 10, 0, tzinfo=UTC)


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

    async def test_get_resource_request_with_candidates(self, mock_aiohttp: aioresponses) -> None:
        """Test get_resource_request sends includeCandidates and parses the candidates."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/ResourceRequest/123?includeCandidates=true",
            payload={
                "identifier": {"requestID": 123},
                "status": "Open",
                "properties": {"title": "Senior Developer", "requestedCandidateCount": 1},
                "metrics": {},
                "candidates": [
                    {
                        "user": {"userID": 10, "employeeID": "EMP001"},
                        "status": {"statusID": 1, "statusName": "Proposed", "statusCategory": "Idle"},
                    }
                ],
                "creationDate": "2024-01-10T08:00:00Z",
                "lastEditDate": "2024-01-15T10:00:00Z",
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_resource_request(123, include_candidates=True)

        assert result.identifier.requestID == 123
        assert result.candidates is not None
        assert result.candidates[0].user.userID == 10
        assert result.candidates[0].status.statusCategory == dm.StatusOptionCategory.Idle


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
# Holiday Calendar Method Tests
# =============================================================================


class TestHolidayCalendarEndpoints:
    """Tests for the holiday calendar and user holiday calendar methods."""

    async def test_get_holiday_calendars(self, mock_aiohttp: aioresponses) -> None:
        """Test get_holiday_calendars parses custom and standard calendars with their holidays."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/HolidayCalendar",
            payload=[
                {
                    "holidayListID": 7,
                    "holidayListCode": "HF-LEIPZIG",
                    "calendarName": "Leipzig office",
                    "custom": True,
                    "countryCode": "DE",
                    "holidays": [
                        {"date": "2026-10-31", "name": "Reformation Day"},
                        {"date": "2026-11-18", "name": "Day of Repentance and Prayer"},
                    ],
                },
                {
                    "holidayListID": 1,
                    "holidayListCode": "DE-SN",
                    "calendarName": "Saxony",
                    "custom": False,
                    "countryCode": "DE",
                    "holidays": [{"date": "2026-12-25", "name": "Christmas Day"}],
                },
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_holiday_calendars()

        assert len(result) == 2
        assert isinstance(result[0], dm.HolidayCalendarOutput)
        assert result[0].holidayListID == 7
        assert result[0].holidayListCode == "HF-LEIPZIG"
        assert result[0].calendarName == "Leipzig office"
        assert result[0].custom is True
        assert result[0].countryCode == "DE"
        assert result[0].holidays == [
            dm.HolidayOutput(date=date(2026, 10, 31), name="Reformation Day"),
            dm.HolidayOutput(date=date(2026, 11, 18), name="Day of Repentance and Prayer"),
        ]
        assert result[1].holidayListCode == "DE-SN"
        assert result[1].custom is False

    async def test_get_holiday_calendars_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_holiday_calendars sends all filters with the query keys of the spec."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/HolidayCalendar?holidayListID=7&holidayListCode=HF-LEIPZIG&custom=true&top=10&skip=20",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_holiday_calendars(
                holiday_list_id=7, holiday_list_code="HF-LEIPZIG", custom=True, top=10, skip=20
            )

        assert result == []

    async def test_import_holiday_calendars(self, mock_aiohttp: aioresponses) -> None:
        """Test import_holiday_calendars sends the calendars and parses the per-calendar results."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/HolidayCalendar/Import",
            payload=[
                {"holidayListID": 7, "holidayListCode": "HF-LEIPZIG", "importStatus": {"status": "Created"}},
                {
                    "holidayListID": 8,
                    "holidayListCode": "HF-DRESDEN",
                    "importStatus": {
                        "status": "Failed",
                        "errorMessage": "The calendar is still assigned to the users 10, 11.",
                    },
                },
            ],
            status=200,
        )
        holiday_calendars = dm.ImportHolidayCalendarsCommand(
            holidayCalendars=[
                dm.HolidayCalendarImportItem(
                    holidayListCode="HF-LEIPZIG",
                    calendarName="Leipzig office",
                    countryCode="DE",
                    holidays=[dm.HolidayInput(date=date(2026, 10, 31), name="Reformation Day")],
                ),
                dm.HolidayCalendarImportItem(holidayListID=8, delete=True),
            ]
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_holiday_calendars(holiday_calendars)

        body = json.loads(next(iter(mock_aiohttp.requests.values()))[0].kwargs["data"])
        assert body == {
            "holidayCalendars": [
                {
                    "holidayListCode": "HF-LEIPZIG",
                    "calendarName": "Leipzig office",
                    "countryCode": "DE",
                    "holidays": [{"date": "2026-10-31", "name": "Reformation Day"}],
                    "delete": False,
                },
                {"holidayListID": 8, "delete": True},
            ]
        }
        assert len(result) == 2
        assert isinstance(result[0], dm.HolidayCalendarImportResult)
        assert result[0].holidayListID == 7
        assert result[0].importStatus == dm.ImportItemStatus(status=dm.ImportItemStatusType.Created)
        assert result[1].holidayListCode == "HF-DRESDEN"
        assert result[1].importStatus is not None
        assert result[1].importStatus.status == dm.ImportItemStatusType.Failed
        assert result[1].importStatus.errorMessage == "The calendar is still assigned to the users 10, 11."

    async def test_get_user_holiday_calendars(self, mock_aiohttp: aioresponses) -> None:
        """Test get_user_holiday_calendars parses the holiday calendar periods of the users."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/UserHolidayCalendar",
            payload=[
                {
                    "userHolidayCalendarID": 3,
                    "userHolidayCalendarCode": "UHC-10-2025",
                    "userID": 10,
                    "employeeID": "EMP010",
                    "holidayListID": 2,
                    "holidayListCode": "DE-BY",
                    "startDate": "2025-01-01",
                    "endDate": "2025-12-31",
                },
                {
                    "userHolidayCalendarID": 4,
                    "userHolidayCalendarCode": "UHC-10-2026",
                    "userID": 10,
                    "employeeID": "EMP010",
                    "holidayListID": 1,
                    "holidayListCode": "DE-SN",
                    "startDate": "2026-01-01",
                    "endDate": None,
                },
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_user_holiday_calendars()

        assert len(result) == 2
        assert isinstance(result[0], dm.UserHolidayCalendarOutputItem)
        assert result[0].userHolidayCalendarCode == "UHC-10-2025"
        assert result[0].holidayListCode == "DE-BY"
        assert result[0].endDate == date(2025, 12, 31)
        assert result[1].userID == 10
        assert result[1].employeeID == "EMP010"
        assert result[1].startDate == date(2026, 1, 1)
        assert result[1].endDate is None

    async def test_get_user_holiday_calendars_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_user_holiday_calendars sends the user filter with the query key of the spec."""
        mock_aiohttp.get(f"{BASE_URL}/importapi/UserHolidayCalendar?userID=10", payload=[], status=200)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_user_holiday_calendars(user_id=10)

        assert result == []

    async def test_import_user_holiday_calendars(self, mock_aiohttp: aioresponses) -> None:
        """Test import_user_holiday_calendars sends the periods and parses the per-period results."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/UserHolidayCalendar/Import",
            payload=[
                {
                    "userHolidayCalendarID": 4,
                    "userHolidayCalendarCode": "UHC-10-2026",
                    "userID": 10,
                    "employeeID": "EMP010",
                    "holidayListID": 1,
                    "holidayListCode": "DE-SN",
                    "startDate": "2026-01-01",
                    "endDate": "2026-12-31",
                    "importStatus": {"status": "Created"},
                }
            ],
            status=200,
        )
        user_holiday_calendars = dm.ImportUserHolidayCalendarsCommand(
            userHolidayCalendars=[
                dm.UserHolidayCalendarImportItem(
                    userHolidayCalendarCode="UHC-10-2026",
                    employeeID="EMP010",
                    holidayListCode="DE-SN",
                    startDate=date(2026, 1, 1),
                    endDate=date(2026, 12, 31),
                )
            ]
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_user_holiday_calendars(user_holiday_calendars)

        body = json.loads(next(iter(mock_aiohttp.requests.values()))[0].kwargs["data"])
        assert body == {
            "userHolidayCalendars": [
                {
                    "userHolidayCalendarCode": "UHC-10-2026",
                    "employeeID": "EMP010",
                    "holidayListCode": "DE-SN",
                    "startDate": "2026-01-01",
                    "endDate": "2026-12-31",
                    "delete": False,
                }
            ]
        }
        assert len(result) == 1
        assert isinstance(result[0], dm.UserHolidayCalendarImportResult)
        assert result[0].userHolidayCalendarID == 4
        assert result[0].userID == 10
        assert result[0].holidayListID == 1
        assert result[0].endDate == date(2026, 12, 31)
        assert result[0].importStatus == dm.ImportItemStatus(status=dm.ImportItemStatusType.Created)


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

    async def test_get_activity_types_with_category(self, mock_aiohttp: aioresponses) -> None:
        """Test get_activity_types sends the category filter under the query key of the spec."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/ActivityType?category=Consulting",
            payload=[{"activityTypeID": 42, "code": "DEV", "category": "Consulting"}],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_activity_types(category="Consulting")

        assert len(result) == 1
        assert result[0].activityTypeID == 42
        assert result[0].category == "Consulting"

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
# Recording Type Method Tests
# =============================================================================


class TestRecordingTypeEndpoints:
    """Tests for the recording type methods."""

    async def test_get_recording_types(self, mock_aiohttp: aioresponses) -> None:
        """Test get_recording_types parses active and inactive recording types."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/RecordingType",
            payload=[
                {
                    "recordingTypeID": 1,
                    "code": "WORK",
                    "name": "Work time",
                    "recordingColumnType": "WorkTime",
                    "unitLabel": "h",
                    "isDefault": True,
                    "isActive": True,
                    "isDeletable": False,
                    "translations": [{"languageID": 1, "name": "Arbeitszeit"}, {"languageID": 2, "name": "Work time"}],
                },
                {
                    "recordingTypeID": 3,
                    "code": "TRAVEL",
                    "name": "Travel distance",
                    "recordingColumnType": "TravelDistance",
                    "unitLabel": "km",
                    "isDefault": False,
                    "isActive": False,
                    "isDeletable": True,
                    "translations": [],
                },
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_recording_types()

        assert len(result) == 2
        assert isinstance(result[0], dm.RecordingTypeResult)
        assert result[0].code == "WORK"
        assert result[0].recordingColumnType == dm.RecordingColumnType.WorkTime
        assert result[0].isDefault is True
        assert result[0].translations == [
            dm.RecordingTypeTranslationDto(languageID=1, name="Arbeitszeit"),
            dm.RecordingTypeTranslationDto(languageID=2, name="Work time"),
        ]
        assert result[1].recordingColumnType == dm.RecordingColumnType.TravelDistance
        assert result[1].unitLabel == "km"
        assert result[1].isActive is False
        assert result[1].isDeletable is True

    async def test_import_recording_type(self, mock_aiohttp: aioresponses) -> None:
        """Test import_recording_type sends the recording type and parses the resulting one."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/RecordingType",
            payload={
                "recordingTypeID": 3,
                "code": "TRAVEL",
                "name": "Travel distance",
                "recordingColumnType": "TravelDistance",
                "unitLabel": "km",
                "isDefault": False,
                "isActive": True,
                "isDeletable": True,
                "translations": [{"languageID": 2, "name": "Travel distance"}],
            },
            status=200,
        )
        recording_type = dm.RecordingTypeImportItem(
            code="TRAVEL",
            recordingColumnType=dm.RecordingColumnType.TravelDistance,
            unitLabel="km",
            isActive=True,
            translations=[dm.RecordingTypeTranslationDto(languageID=2, name="Travel distance")],
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_recording_type(recording_type)

        body = json.loads(next(iter(mock_aiohttp.requests.values()))[0].kwargs["data"])
        assert body == {
            "code": "TRAVEL",
            "recordingColumnType": "TravelDistance",
            "unitLabel": "km",
            "isActive": True,
            "translations": [{"languageID": 2, "name": "Travel distance"}],
        }
        assert isinstance(result, dm.RecordingTypeResult)
        assert result.recordingTypeID == 3
        assert result.name == "Travel distance"
        assert result.recordingColumnType == dm.RecordingColumnType.TravelDistance
        assert result.isDeletable is True


# =============================================================================
# Rate Method Tests
# =============================================================================


class TestRateEndpoints:
    """Tests for the rate methods."""

    async def test_get_rates(self, mock_aiohttp: aioresponses) -> None:
        """Test get_rates parses the rate catalog."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Rate",
            payload=[
                {
                    "rateID": 5,
                    "code": "RATE-SENIOR",
                    "category": "Consulting",
                    "label": "Senior Consultant",
                    "amount": 1250.0,
                    "currencyCode": "EUR",
                    "unit": "PersonDay",
                    "isActive": True,
                    "rateCardCount": 2,
                    "orderPositionCount": 14,
                },
                {
                    "rateID": 6,
                    "code": "RATE-TRAVEL",
                    "category": "Travel",
                    "label": "Travel time",
                    "amount": 80.5,
                    "currencyCode": "EUR",
                    "unit": "Hour",
                    "isActive": False,
                    "rateCardCount": 0,
                    "orderPositionCount": 0,
                },
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_rates()

        assert len(result) == 2
        assert isinstance(result[0], dm.RateResult)
        assert result[0].code == "RATE-SENIOR"
        assert result[0].category == "Consulting"
        assert result[0].amount == 1250.0
        assert result[0].currencyCode == "EUR"
        assert result[0].unit == dm.RateUnit.PersonDay
        assert result[0].rateCardCount == 2
        assert result[0].orderPositionCount == 14
        assert result[1].unit == dm.RateUnit.Hour
        assert result[1].isActive is False

    async def test_get_rates_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_rates sends the category filter with the query key of the spec."""
        mock_aiohttp.get(f"{BASE_URL}/importapi/Rate?category=Consulting", payload=[], status=200)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_rates(category="Consulting")

        assert result == []

    async def test_import_rate(self, mock_aiohttp: aioresponses) -> None:
        """Test import_rate sends the rate and parses the resulting one."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Rate",
            payload={
                "rateID": 5,
                "code": "RATE-SENIOR",
                "category": "Consulting",
                "label": "Senior Consultant",
                "amount": 1250.0,
                "currencyCode": "EUR",
                "unit": "PersonDay",
                "isActive": True,
                "rateCardCount": 0,
                "orderPositionCount": 0,
            },
            status=200,
        )
        rate = dm.RateImportItem(
            code="RATE-SENIOR",
            category="Consulting",
            label="Senior Consultant",
            amount=1250.0,
            currencyCode="EUR",
            unit=dm.RateUnit.PersonDay,
            isActive=True,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_rate(rate)

        body = json.loads(next(iter(mock_aiohttp.requests.values()))[0].kwargs["data"])
        assert body == {
            "code": "RATE-SENIOR",
            "category": "Consulting",
            "label": "Senior Consultant",
            "amount": 1250.0,
            "currencyCode": "EUR",
            "unit": "PersonDay",
            "isActive": True,
        }
        assert isinstance(result, dm.RateResult)
        assert result.rateID == 5
        assert result.unit == dm.RateUnit.PersonDay
        assert result.orderPositionCount == 0


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

    async def test_get_orders_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_orders sends every filter under the query key of the spec."""
        url = (
            f"{BASE_URL}/importapi/Order?top=10&skip=0&includePositions=false&projectReferenceId=7"
            "&projectCode=PROJ001&validFromOnOrAfter=2026-01-01&validFromOnOrBefore=2026-03-31"
            "&expiryOnOrAfter=2026-12-01&expiryOnOrBefore=2026-12-31&orderDateOnOrAfter=2025-11-01"
            "&orderDateOnOrBefore=2025-12-31&deliveryDateOnOrAfter=2026-02-01&deliveryDateOnOrBefore=2026-02-28"
            "&validOn=2026-06-15&lastUpdatedOnOrAfter=2026-09-01T00:00:00%2B00:00"
        )
        mock_aiohttp.get(
            url,
            payload={
                "orders": [
                    {
                        "orderID": 42,
                        "code": "ORDER-1",
                        "projects": [{"projectReferenceID": 7, "projectCode": "PROJ001"}],
                        "orderDate": "2025-11-15",
                        "deliveryDate": "2026-02-15",
                        "validFromDate": "2026-01-01",
                        "expiryDate": "2026-12-31",
                        "lastEditDate": "2026-09-02T08:00:00Z",
                    }
                ]
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_orders(
                top=10,
                skip=0,
                include_positions=False,
                project_reference_id=[7],
                project_code=["PROJ001"],
                valid_from_on_or_after=date(2026, 1, 1),
                valid_from_on_or_before=date(2026, 3, 31),
                expiry_on_or_after=date(2026, 12, 1),
                expiry_on_or_before=date(2026, 12, 31),
                order_date_on_or_after=date(2025, 11, 1),
                order_date_on_or_before=date(2025, 12, 31),
                delivery_date_on_or_after=date(2026, 2, 1),
                delivery_date_on_or_before=date(2026, 2, 28),
                valid_on=date(2026, 6, 15),
                last_updated_on_or_after=datetime(2026, 9, 1, tzinfo=UTC),
            )

        assert result.orders is not None
        order = result.orders[0]
        assert order.orderID == 42
        assert order.deliveryDate == date(2026, 2, 15)
        assert order.positions is None

    async def test_get_orders_with_several_projects(self, mock_aiohttp: aioresponses) -> None:
        """Test get_orders sends several values of the array filters as repeated query keys."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order?projectReferenceId=7&projectReferenceId=8"
            "&projectCode=PROJ001&projectCode=PROJ002",
            payload={"orders": [{"orderID": 42}, {"orderID": 43}]},
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_orders(project_reference_id=[7, 8], project_code=["PROJ001", "PROJ002"])

        assert result.orders is not None
        assert [order.orderID for order in result.orders] == [42, 43]
        assert requested_urls(mock_aiohttp) == [
            f"{BASE_URL}/importapi/Order?projectCode=PROJ001&projectCode=PROJ002"
            "&projectReferenceId=7&projectReferenceId=8"
        ]

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


class TestGetOrderPositionRecordingTypeRates:
    """Tests for get_order_position_recording_type_rates method."""

    async def test_get_order_position_recording_type_rates(self, mock_aiohttp: aioresponses) -> None:
        """Test get_order_position_recording_type_rates parses own rates and factors of another recording type."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order/Position/RecordingTypeRates",
            payload=[
                {
                    "orderPositionID": 42,
                    "recordingTypeID": 1,
                    "recordingTypeCode": "WORK",
                    "mode": "OwnRate",
                    "amount": 150.0,
                    "unit": "Hour",
                    "rateID": 5,
                    "rateCode": "RATE-SENIOR",
                },
                {
                    "orderPositionID": 42,
                    "recordingTypeID": 2,
                    "recordingTypeCode": "TRAVELTIME",
                    "mode": "FactorOfRate",
                    "factor": 0.5,
                    "baseRecordingTypeID": 1,
                    "baseRecordingTypeCode": "WORK",
                },
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order_position_recording_type_rates()

        assert len(result) == 2
        assert isinstance(result[0], dm.OrderPositionRecordingTypeRateOutput)
        assert result[0].orderPositionID == 42
        assert result[0].mode == dm.RecordingTypePricingMode.OwnRate
        assert result[0].amount == 150.0
        assert result[0].unit == dm.RateUnit.Hour
        assert result[0].rateID == 5
        assert result[0].rateCode == "RATE-SENIOR"
        assert result[1].mode == dm.RecordingTypePricingMode.FactorOfRate
        assert result[1].factor == 0.5
        assert result[1].baseRecordingTypeID == 1
        assert result[1].baseRecordingTypeCode == "WORK"
        assert result[1].amount is None

    async def test_get_order_position_recording_type_rates_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_order_position_recording_type_rates sends all filters with the query keys of the spec."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/Order/Position/RecordingTypeRates"
            "?orderPositionId=42&orderId=1&orderCode=ORDER-1&orderPositionCode=POS-1",
            payload=[],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_order_position_recording_type_rates(
                order_position_id=42, order_id=1, order_code="ORDER-1", order_position_code="POS-1"
            )

        assert result == []


class TestImportOrderPositionRecordingTypeRates:
    """Tests for import_order_position_recording_type_rates method."""

    async def test_import_order_position_recording_type_rates(self, mock_aiohttp: aioresponses) -> None:
        """Test import_order_position_recording_type_rates sends the prices and parses the per-row results."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/Order/Position/RecordingTypeRates",
            payload={
                "rates": [
                    {
                        "orderPositionID": 42,
                        "recordingTypeID": 1,
                        "recordingTypeCode": "WORK",
                        "status": {"status": "Created"},
                    },
                    {
                        "orderPositionID": 42,
                        "recordingTypeID": 2,
                        "recordingTypeCode": "TRAVELTIME",
                        "status": {"status": "Updated"},
                    },
                    {
                        "orderPositionID": 42,
                        "recordingTypeID": 3,
                        "recordingTypeCode": "TRAVEL",
                        "status": {"status": "Deleted"},
                    },
                ]
            },
            status=200,
        )
        batch = dm.OrderPositionRecordingTypeRateImportBatch(
            rates=[
                dm.OrderPositionRecordingTypeRateImportItem(
                    orderCode="ORDER-1",
                    orderPositionCode="POS-1",
                    recordingTypeCode="WORK",
                    mode=dm.RecordingTypePricingMode.OwnRate,
                    amount=150.0,
                    unit=dm.RateUnit.Hour,
                ),
                dm.OrderPositionRecordingTypeRateImportItem(
                    orderPositionID=42,
                    recordingTypeCode="TRAVELTIME",
                    mode=dm.RecordingTypePricingMode.FactorOfRate,
                    factor=0.5,
                    baseRecordingTypeCode="WORK",
                ),
                dm.OrderPositionRecordingTypeRateImportItem(
                    orderPositionID=42, recordingTypeCode="TRAVEL", deleted=True
                ),
            ]
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_order_position_recording_type_rates(batch)

        body = json.loads(next(iter(mock_aiohttp.requests.values()))[0].kwargs["data"])
        assert body == {
            "rates": [
                {
                    "orderCode": "ORDER-1",
                    "orderPositionCode": "POS-1",
                    "recordingTypeCode": "WORK",
                    "mode": "OwnRate",
                    "amount": 150.0,
                    "unit": "Hour",
                },
                {
                    "orderPositionID": 42,
                    "recordingTypeCode": "TRAVELTIME",
                    "mode": "FactorOfRate",
                    "factor": 0.5,
                    "baseRecordingTypeCode": "WORK",
                },
                {"orderPositionID": 42, "recordingTypeCode": "TRAVEL", "deleted": True},
            ]
        }
        assert isinstance(result, dm.OrderPositionRecordingTypeRateImportBatchResult)
        assert result.rates is not None
        assert [rate.recordingTypeCode for rate in result.rates] == ["WORK", "TRAVELTIME", "TRAVEL"]
        assert result.rates[0].status == dm.ImportItemStatus(status=dm.ImportItemStatusType.Created)
        assert result.rates[1].status == dm.ImportItemStatus(status=dm.ImportItemStatusType.Updated)
        assert result.rates[2].status == dm.ImportItemStatus(status=dm.ImportItemStatusType.Deleted)


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


class TestGetWorkPackageCustomProperties:
    """Tests for get_work_package_custom_properties method."""

    async def test_get_work_package_custom_properties(self, mock_aiohttp: aioresponses) -> None:
        """Test get_work_package_custom_properties parses a text property and a value list property."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkPackage/CustomProperties",
            payload=[
                {
                    "propertyName": "costCenter",
                    "dataType": "String",
                    "dataFormat": "String",
                    "isRequired": True,
                    "maxLength": 20,
                    "options": None,
                    "defaultOptionValue": None,
                },
                {
                    "propertyName": "billingType",
                    "dataType": "ValueList",
                    "dataFormat": "Number",
                    "isRequired": False,
                    "maxLength": None,
                    "options": [{"value": 1, "label": "Time and material"}, {"value": 2, "label": "Fixed price"}],
                    "defaultOptionValue": 1,
                },
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_package_custom_properties()

        assert len(result) == 2
        assert isinstance(result[0], dm.CustomProperty)
        assert result[0].propertyName == "costCenter"
        assert result[0].dataType == dm.CustomPropertyDataType.String
        assert result[0].isRequired is True
        assert result[0].maxLength == 20
        assert result[0].options is None
        assert result[1].propertyName == "billingType"
        assert result[1].dataType == dm.CustomPropertyDataType.ValueList
        assert result[1].dataFormat == dm.CustomPropertyDataFormat.Number
        assert result[1].options == [
            dm.CustomPropertyOption(value=1, label="Time and material"),
            dm.CustomPropertyOption(value=2, label="Fixed price"),
        ]
        assert result[1].defaultOptionValue == 1


class TestGetWorkPackageOrderPositionRecordingTargets:
    """Tests for get_work_package_order_position_recording_targets method."""

    async def test_get_work_package_order_position_recording_targets(self, mock_aiohttp: aioresponses) -> None:
        """Test get_work_package_order_position_recording_targets parses the recording targets of the links."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/WorkPackage/OrderPositions/RecordingTargets",
            payload=[
                {
                    "recordingTargetID": 99,
                    "workPackageID": 11,
                    "workPackageCode": "WP-11",
                    "workPackageLastEditDate": "2026-09-01T08:00:00Z",
                    "projectID": 7,
                    "projectCode": "PROJ001",
                    "orderPositionID": 42,
                    "orderPositionCode": "POS-1",
                    "orderPositionLastEditDate": "2026-09-02T09:30:00Z",
                    "orderID": 1,
                    "orderCode": "ORDER-1",
                    "activityTypeID": 4,
                    "activityTypeCode": "DEV",
                    "recordingTypes": [
                        {"recordingTypeID": 1, "recordingTypeCode": "WORK"},
                        {"recordingTypeID": 3, "recordingTypeCode": "TRAVEL"},
                    ],
                    "isBillable": True,
                    "isActive": True,
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_package_order_position_recording_targets()

        assert len(result) == 1
        target = result[0]
        assert isinstance(target, dm.WorkPackageOrderPositionRecordingTargetOutput)
        assert target.recordingTargetID == 99
        assert target.workPackageCode == "WP-11"
        assert target.workPackageLastEditDate == datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
        assert target.projectCode == "PROJ001"
        assert target.orderPositionCode == "POS-1"
        assert target.orderPositionLastEditDate == datetime(2026, 9, 2, 9, 30, tzinfo=UTC)
        assert target.orderCode == "ORDER-1"
        assert target.activityTypeCode == "DEV"
        assert target.recordingTypes == [
            dm.RecordingTypeReferenceOutput(recordingTypeID=1, recordingTypeCode="WORK"),
            dm.RecordingTypeReferenceOutput(recordingTypeID=3, recordingTypeCode="TRAVEL"),
        ]
        assert target.isBillable is True
        assert target.isActive is True

    async def test_get_work_package_order_position_recording_targets_with_all_filters(
        self, mock_aiohttp: aioresponses
    ) -> None:
        """Test get_work_package_order_position_recording_targets sends all filters with the query keys of the spec."""
        url = (
            f"{BASE_URL}/importapi/WorkPackage/OrderPositions/RecordingTargets"
            "?WorkPackageLastUpdatedOnOrAfter=2026-09-01T00:00:00%2B00:00"
            "&OrderPositionActivityTypeID=4&OrderPositionActivityTypeCode=DEV"
            "&OrderPositionActivityTypeTargetSystemCode=SAP-DEV&OrderPositionActivityTypeCategory=Consulting"
            "&WorkPackageID=11&WorkPackageCode=WP-11&OrderPositionID=42&OrderPositionCode=POS-1"
            "&OrderID=1&OrderCode=ORDER-1&ProjectID=7&ProjectCode=PROJ001"
            "&RecordingTypeID=1&RecordingTypeCode=WORK&IsActive=true&IsBillable=false"
            "&OrderPositionLastUpdatedOnOrAfter=2026-09-02T00:00:00%2B00:00&Top=50&Skip=100"
        )
        mock_aiohttp.get(url, payload=[], status=200)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_work_package_order_position_recording_targets(
                work_package_last_updated_on_or_after=datetime(2026, 9, 1, tzinfo=UTC),
                order_position_activity_type_id=4,
                order_position_activity_type_code="DEV",
                order_position_activity_type_target_system_code="SAP-DEV",
                order_position_activity_type_category="Consulting",
                work_package_id=11,
                work_package_code="WP-11",
                order_position_id=42,
                order_position_code="POS-1",
                order_id=1,
                order_code="ORDER-1",
                project_id=7,
                project_code="PROJ001",
                recording_type_id=1,
                recording_type_code="WORK",
                is_active=True,
                is_billable=False,
                order_position_last_updated_on_or_after=datetime(2026, 9, 2, tzinfo=UTC),
                top=50,
                skip=100,
            )

        assert result == []


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

    async def test_get_recording_targets_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_recording_targets sends every filter under the query key of the spec."""
        url = (
            f"{BASE_URL}/importapi/TimeRecording/RecordingTargets?projectReferenceId=7&projectCode=PROJ001"
            "&workPackageId=11&workPackageCode=WP-1&orderPositionId=21&orderPositionCode=POS-1&orderId=1"
            "&orderCode=ORDER-1&generalActivityId=31&generalActivityCode=TRAINING&activityTypeId=42"
            "&activityTypeCode=DEV&activityTypeTargetSystemCode=SAP-DEV&generalActivityTargetSystemCode=SAP-TRN"
            "&activityTypeCategory=Consulting&isActive=false"
        )
        mock_aiohttp.get(
            url,
            payload=[
                {
                    "recordingTargetID": 42,
                    "orderID": 1,
                    "orderCode": "ORDER-1",
                    "orderPositionID": 21,
                    "orderPositionCode": "POS-1",
                    "activityTypeID": 42,
                    "activityTypeCode": "DEV",
                    "isActive": False,
                }
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_recording_targets(
                project_reference_id=7,
                project_code="PROJ001",
                work_package_id=11,
                work_package_code="WP-1",
                order_position_id=21,
                order_position_code="POS-1",
                order_id=1,
                order_code="ORDER-1",
                general_activity_id=31,
                general_activity_code="TRAINING",
                activity_type_id=42,
                activity_type_code="DEV",
                activity_type_target_system_code="SAP-DEV",
                general_activity_target_system_code="SAP-TRN",
                activity_type_category="Consulting",
                is_active=False,
            )

        assert len(result) == 1
        assert result[0].orderPositionCode == "POS-1"
        assert result[0].isActive is False

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

    async def test_get_user_time_sheet_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_user_time_sheet sends every filter under the query key of the spec."""
        url = (
            f"{BASE_URL}/importapi/TimeRecording/UserTimeSheet?userId=10&employeeId=EMP001"
            "&email=john.doe%40example.com&startDate=2026-09-01&endDate=2026-09-30"
            "&workDateOnOrAfter=2026-09-01&workDateOnOrBefore=2026-09-30&orderId=3&orderCode=ORDER-1"
            "&projectReferenceId=7&projectCode=PROJ001&workPackageId=11&workPackageCode=WP-1"
            "&orderPositionId=21&orderPositionCode=POS-1&generalActivityId=31&generalActivityCode=TRAINING"
            "&activityTypeId=42&activityTypeCode=DEV&activityTypeTargetSystemCode=SAP-DEV"
            "&generalActivityTargetSystemCode=SAP-TRN&activityTypeCategory=Consulting&rateId=5"
            "&rateCode=RATE-1&rateCategory=Senior&status=Submitted&status=Confirmed"
            "&modifiedAfter=2026-09-01T00:00:00%2B00:00&createdOnOrAfter=2026-08-01T00:00:00%2B00:00"
            "&lastUpdatedOnOrAfter=2026-09-02T12:00:00%2B00:00&lastImportedOnOrAfter=2026-09-03T00:00:00%2B00:00"
        )
        mock_aiohttp.get(
            url,
            payload={
                "entries": [
                    {
                        "recordingEntryID": 1,
                        "userID": 10,
                        "workDate": "2026-09-15",
                        "timeMinutes": 480,
                        "status": "Submitted",
                        "orderID": 3,
                        "rateID": 5,
                        "rateCode": "RATE-1",
                        "rateCategory": "Senior",
                        "activityTypeCategory": "Consulting",
                        "lastImportedDate": "2026-09-16T08:00:00Z",
                    }
                ],
                "workTimes": [],
            },
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_user_time_sheet(
                user_id=10,
                employee_id="EMP001",
                email="john.doe@example.com",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 30),
                work_date_on_or_after=date(2026, 9, 1),
                work_date_on_or_before=date(2026, 9, 30),
                order_id=3,
                order_code="ORDER-1",
                project_reference_id=7,
                project_code="PROJ001",
                work_package_id=11,
                work_package_code="WP-1",
                order_position_id=21,
                order_position_code="POS-1",
                general_activity_id=31,
                general_activity_code="TRAINING",
                activity_type_id=42,
                activity_type_code="DEV",
                activity_type_target_system_code="SAP-DEV",
                general_activity_target_system_code="SAP-TRN",
                activity_type_category="Consulting",
                rate_id=5,
                rate_code="RATE-1",
                rate_category="Senior",
                status=[dm.TimeRecordingEntryStatus.Submitted, dm.TimeRecordingEntryStatus.Confirmed],
                modified_after=datetime(2026, 9, 1, tzinfo=UTC),
                created_on_or_after=datetime(2026, 8, 1, tzinfo=UTC),
                last_updated_on_or_after=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
                last_imported_on_or_after=datetime(2026, 9, 3, tzinfo=UTC),
            )

        assert result.entries is not None
        entry = result.entries[0]
        assert entry.status == dm.TimeRecordingEntryStatus.Submitted
        assert entry.rateCategory == "Senior"
        assert entry.activityTypeCategory == "Consulting"
        assert result.workTimes == []

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


class TestGetRecordingEntries:
    """Tests for get_recording_entries method."""

    async def test_get_recording_entries(self, mock_aiohttp: aioresponses) -> None:
        """Test get_recording_entries parses the entries of different users and recording targets."""
        mock_aiohttp.get(
            f"{BASE_URL}/importapi/TimeRecording/RecordingEntries",
            payload=[
                {
                    "recordingEntryID": 1001,
                    "recordingEntryCode": "EXT-1001",
                    "userID": 10,
                    "employeeID": "EMP010",
                    "email": "jane.doe@example.com",
                    "recordingTargetID": 99,
                    "activityTypeID": 4,
                    "activityTypeCode": "DEV",
                    "projectReferenceID": 7,
                    "projectCode": "PROJ001",
                    "workPackageID": 11,
                    "workPackageCode": "WP-11",
                    "orderPositionID": 42,
                    "orderPositionCode": "POS-1",
                    "workDate": "2026-09-01",
                    "startTime": "09:00:00",
                    "endTime": "17:30:00",
                    "timeMinutes": 480,
                    "pauseMinutes": 30,
                    "description": "Implemented the holiday calendar import",
                    "status": "Submitted",
                    "sourceDescription": "Import API",
                    "recordingTypeValues": [{"recordingTypeID": 3, "recordingTypeCode": "TRAVEL", "value": 42.5}],
                    "isImported": True,
                    "orderID": 1,
                    "orderCode": "ORDER-1",
                    "lastEditDate": "2026-09-02T08:00:00Z",
                    "activityTypeCategory": "Consulting",
                    "rateID": 5,
                    "rateCode": "RATE-SENIOR",
                    "rateCategory": "Consulting",
                    "creationDate": "2026-09-01T17:30:00Z",
                    "lastImportedDate": "2026-09-02T08:00:00Z",
                },
                {
                    "recordingEntryID": 1002,
                    "userID": 11,
                    "employeeID": "EMP011",
                    "email": "john.doe@example.com",
                    "recordingTargetID": 12,
                    "generalActivityID": 8,
                    "generalActivityCode": "TRAINING",
                    "workDate": "2026-09-02",
                    "timeMinutes": 240,
                    "status": "Confirmed",
                    "recordingTypeValues": [],
                    "isImported": False,
                    "lastEditDate": "2026-09-03T10:15:00Z",
                    "creationDate": "2026-09-02T16:00:00Z",
                    "lastImportedDate": None,
                },
            ],
            status=200,
        )

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_recording_entries()

        assert len(result) == 2
        entry = result[0]
        assert isinstance(entry, dm.RecordingEntryImportReadItem)
        assert entry.recordingEntryCode == "EXT-1001"
        assert entry.email == "jane.doe@example.com"
        assert entry.workPackageCode == "WP-11"
        assert entry.orderPositionCode == "POS-1"
        assert entry.workDate == date(2026, 9, 1)
        assert entry.startTime == "09:00:00"
        assert entry.timeMinutes == 480
        assert entry.pauseMinutes == 30
        assert entry.status == dm.TimeRecordingEntryStatus.Submitted
        assert entry.recordingTypeValues == [
            dm.RecordingEntryTypeValueImport(recordingTypeID=3, recordingTypeCode="TRAVEL", value=42.5)
        ]
        assert entry.rateCode == "RATE-SENIOR"
        assert entry.lastEditDate == datetime(2026, 9, 2, 8, 0, tzinfo=UTC)
        assert entry.lastImportedDate == datetime(2026, 9, 2, 8, 0, tzinfo=UTC)
        assert result[1].generalActivityCode == "TRAINING"
        assert result[1].status == dm.TimeRecordingEntryStatus.Confirmed
        assert result[1].isImported is False
        assert result[1].lastImportedDate is None

    async def test_get_recording_entries_with_all_filters(self, mock_aiohttp: aioresponses) -> None:
        """Test get_recording_entries sends all filters with the query keys of the spec, arrays as repeated keys."""
        url = (
            f"{BASE_URL}/importapi/TimeRecording/RecordingEntries?top=100&skip=200"
            "&userId=10&userId=11&employeeId=EMP010&employeeId=EMP011"
            "&email=jane.doe%40example.com&email=john.doe%40example.com"
            "&workDateOnOrAfter=2026-09-01&workDateOnOrBefore=2026-09-30"
            "&createdOnOrAfter=2026-09-01T00:00:00%2B00:00&lastUpdatedOnOrAfter=2026-09-02T00:00:00%2B00:00"
            "&lastImportedOnOrAfter=2026-09-03T00:00:00%2B00:00"
            "&usersBusinessUnitId=2&usersBusinessUnitName=Consulting"
            "&usersPracticeAreaId=3&usersPracticeAreaName=Energy&usersTeamId=4&usersTeamCode=TEAM001"
            "&usersLegalEntityId=5&usersLegalEntityName=ACME&usersCountryCode=DE"
            "&orderId=1&orderCode=ORDER-1&projectReferenceId=7&projectCode=PROJ001"
            "&workPackageId=11&workPackageCode=WP-11&orderPositionId=42&orderPositionCode=POS-1"
            "&generalActivityId=8&generalActivityCode=TRAINING&activityTypeId=9&activityTypeCode=DEV"
            "&activityTypeTargetSystemCode=SAP-DEV&generalActivityTargetSystemCode=SAP-TRN"
            "&activityTypeCategory=Consulting&rateId=6&rateCode=RATE-SENIOR&rateCategory=Senior"
            "&status=Submitted&status=Confirmed&recordingEntryId=1001&recordingEntryCode=EXT-1001"
        )
        mock_aiohttp.get(url, payload=[], status=200)

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.get_recording_entries(
                top=100,
                skip=200,
                user_id=[10, 11],
                employee_id=["EMP010", "EMP011"],
                email=["jane.doe@example.com", "john.doe@example.com"],
                work_date_on_or_after=date(2026, 9, 1),
                work_date_on_or_before=date(2026, 9, 30),
                created_on_or_after=datetime(2026, 9, 1, tzinfo=UTC),
                last_updated_on_or_after=datetime(2026, 9, 2, tzinfo=UTC),
                last_imported_on_or_after=datetime(2026, 9, 3, tzinfo=UTC),
                users_business_unit_id=2,
                users_business_unit_name="Consulting",
                users_practice_area_id=3,
                users_practice_area_name="Energy",
                users_team_id=4,
                users_team_code="TEAM001",
                users_legal_entity_id=5,
                users_legal_entity_name="ACME",
                users_country_code="DE",
                order_id=1,
                order_code="ORDER-1",
                project_reference_id=7,
                project_code="PROJ001",
                work_package_id=11,
                work_package_code="WP-11",
                order_position_id=42,
                order_position_code="POS-1",
                general_activity_id=8,
                general_activity_code="TRAINING",
                activity_type_id=9,
                activity_type_code="DEV",
                activity_type_target_system_code="SAP-DEV",
                general_activity_target_system_code="SAP-TRN",
                activity_type_category="Consulting",
                rate_id=6,
                rate_code="RATE-SENIOR",
                rate_category="Senior",
                status=[dm.TimeRecordingEntryStatus.Submitted, dm.TimeRecordingEntryStatus.Confirmed],
                recording_entry_id=1001,
                recording_entry_code="EXT-1001",
            )

        assert result == []


class TestImportRecordingEntries:
    """Tests for import_recording_entries method."""

    async def test_import_recording_entries(self, mock_aiohttp: aioresponses) -> None:
        """Test import_recording_entries sends the entries as a JSON array and parses the per-entry results."""
        mock_aiohttp.post(
            f"{BASE_URL}/importapi/TimeRecording/RecordingEntries",
            payload=[
                {"recordingEntryID": 1001, "recordingEntryCode": "EXT-1001", "status": {"status": "Created"}},
                {
                    "recordingEntryID": 999,
                    "recordingEntryCode": None,
                    "status": {"status": "Failed", "errorMessage": "Recording entry 999 does not exist."},
                },
            ],
            status=200,
        )
        entries = [
            dm.RecordingEntryImportItem(
                recordingEntryCode="EXT-1001",
                employeeID="EMP010",
                activityTypeCode="DEV",
                workPackageCode="WP-11",
                orderPositionCode="POS-1",
                workDate=date(2026, 9, 1),
                startTime="09:00:00",
                endTime="17:30:00",
                timeMinutes=480,
                pauseMinutes=30,
                description="Implemented the holiday calendar import",
                status=dm.TimeRecordingEntryStatus.Submitted,
                recordingTypeValues=[dm.RecordingEntryTypeValueImport(recordingTypeCode="TRAVEL", value=42.5)],
            ),
            dm.RecordingEntryImportItem(
                recordingEntryID=999,
                userID=10,
                description="Code review",
                status=dm.TimeRecordingEntryStatus.Confirmed,
            ),
        ]

        async with DecidaloClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = await client.import_recording_entries(entries)

        body = json.loads(next(iter(mock_aiohttp.requests.values()))[0].kwargs["data"])
        assert body == [
            {
                "recordingEntryCode": "EXT-1001",
                "employeeID": "EMP010",
                "activityTypeCode": "DEV",
                "workPackageCode": "WP-11",
                "orderPositionCode": "POS-1",
                "workDate": "2026-09-01",
                "startTime": "09:00:00",
                "endTime": "17:30:00",
                "timeMinutes": 480,
                "pauseMinutes": 30,
                "description": "Implemented the holiday calendar import",
                "status": "Submitted",
                "recordingTypeValues": [{"recordingTypeCode": "TRAVEL", "value": 42.5}],
            },
            {"recordingEntryID": 999, "userID": 10, "description": "Code review", "status": "Confirmed"},
        ]
        assert len(result) == 2
        assert isinstance(result[0], dm.RecordingEntryImportResult)
        assert result[0].recordingEntryID == 1001
        assert result[0].recordingEntryCode == "EXT-1001"
        assert result[0].status == dm.ImportItemStatus(status=dm.ImportItemStatusType.Created)
        assert result[1].status is not None
        assert result[1].status.status == dm.ImportItemStatusType.Failed
        assert result[1].status.errorMessage == "Recording entry 999 does not exist."


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
