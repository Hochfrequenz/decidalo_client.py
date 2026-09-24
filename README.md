# decidalo_client.py

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python Versions (officially) supported](https://img.shields.io/pypi/pyversions/decidalo-client.svg)
![Pypi status badge](https://img.shields.io/pypi/v/decidalo-client)

![Unittests status badge](https://github.com/Hochfrequenz/decidalo_client.py/workflows/Unittests/badge.svg)
![Coverage status badge](https://github.com/Hochfrequenz/decidalo_client.py/workflows/Coverage/badge.svg)
![Linting status badge](https://github.com/Hochfrequenz/decidalo_client.py/workflows/Linting/badge.svg)
![Formatting status badge](https://github.com/Hochfrequenz/decidalo_client.py/workflows/Formatting/badge.svg)

This repository contains two async Python clients for [decidalo](https://decidalo.de/):

| Client | API | Purpose |
|--------|-----|---------|
| `DecidaloClient` (Import Client) | [V3 Import API](https://import.decidalo.dev/index.html) | Bulk-importing data (users, teams, projects, bookings, ...) into decidalo |
| `DecidaloAppClient` (App Client) | App API (`api.decidalo.app`) | Reading data from decidalo: searching people, viewing profiles, skills, certificates, projects |

Use the **Import Client** when you need to push data _into_ decidalo (e.g. syncing users from an HR system).
Use the **App Client** when you need to read data _from_ decidalo (e.g. finding people with specific skills).

> [!IMPORTANT]
> This is a community project and is NOT an official decidalo client.
> It is not affiliated with or endorsed by Data Assessment Solutions GmbH.

## Installation

```bash
pip install decidalo-client
```

## Import Client (`DecidaloClient`)

The Import Client wraps the decidalo V3 Import API ([Swagger UI](https://import.decidalo.dev/index.html)).
It is used for bulk-importing data into decidalo using an API key.

```python
import asyncio
from decidalo_client import DecidaloClient, DecidaloAPIError, DecidaloAuthenticationError

async def main() -> None:
    async with DecidaloClient(api_key="your-api-key") as client:
        # Get all users
        users = await client.get_users()
        for user in users:
            print(f"{user.displayName} ({user.email})")

        # Get all projects
        projects = await client.get_all_projects()
        for project in projects:
            print(f"{project.properties.name.value}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Error Handling

```python
import asyncio
from decidalo_client import DecidaloClient, DecidaloAPIError, DecidaloAuthenticationError

async def main() -> None:
    async with DecidaloClient(api_key="your-api-key") as client:
        try:
            users = await client.get_users()
        except DecidaloAuthenticationError as e:
            print(f"Authentication failed: {e.message}")
        except DecidaloAPIError as e:
            print(f"API error {e.status_code}: {e.message}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Import Client Features

- Async HTTP client built on `aiohttp`
- Type-safe request/response models using `pydantic`, generated from the OpenAPI spec of the Import API
- Every public method of `DecidaloClient` wraps exactly one API operation (see [API Coverage](#api-coverage)): path, query parameters, request body and response type follow the spec, and the keyword arguments are the snake_case names of the query parameters (e.g. `created_on_or_after` for `CreatedOnOrAfter`)
- Query parameters of format `date` take a `datetime.date`, those of format `date-time` a timezone-aware `datetime.datetime`
- Fields the models don't know (e.g. fields the API added to a response) are ignored instead of failing the validation

> [!TIP]
> Because unknown fields are ignored, a misspelled or outdated keyword argument of a request model is dropped silently at runtime, e.g. `OrderImportItem(projectCode="P1")`.
> Let mypy catch such mistakes with the [pydantic mypy plugin](https://docs.pydantic.dev/latest/integrations/mypy/) and `init_forbid_extra`:
>
> ```toml
> [tool.mypy]
> plugins = ["pydantic.mypy"]
>
> [tool.pydantic-mypy]
> init_forbid_extra = true
> ```

### API Coverage

The client covers the V3 Import API as described by [`openapi/v1/swagger.json`](openapi/v1/swagger.json), synced from [import.decidalo.dev](https://import.decidalo.dev/swagger/v1/swagger.json) on 2026-09-24.
The tables are grouped by the tags of the spec (as in the [Swagger UI](https://import.decidalo.dev/index.html)).

<!-- api-coverage:start -->
**83 of 110** operations are implemented.

#### Absence

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Absence` | `get_absences()` |
| `POST /importapi/Absence/Import` | `import_absences()` |

#### ActivityType

| Endpoint | Method |
| --- | --- |
| `GET /importapi/ActivityType` | `get_activity_types()` |
| `POST /importapi/ActivityType` | `import_activity_type()` |

#### Booking

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Booking` | `get_bookings()` |
| `GET /importapi/Booking/BookingAccountingTypes` | not implemented |
| `GET /importapi/Booking/ByProject` | `get_bookings_by_project()` |
| `POST /importapi/Booking/Comments/Batch` | `import_booking_comments()` |
| `GET /importapi/Booking/CustomProperties` | not implemented |
| `POST /importapi/Booking/ImportAsync` | `import_bookings_async()` |
| `GET /importapi/Booking/RejectionReasons` | not implemented |

#### Certificate

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Certificate` | not implemented |

#### Company

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Company` | `get_companies()` |
| `POST /importapi/Company/Import` | `import_company()` |

#### CompanyDeprecated

| Endpoint | Method |
| --- | --- |
| `POST /api/Company/Import` | not implemented (deprecated) |

#### GeneralActivity

| Endpoint | Method |
| --- | --- |
| `GET /importapi/GeneralActivity` | `get_general_activities()` |
| `POST /importapi/GeneralActivity` | `import_general_activity()` |

#### HolidayCalendar

| Endpoint | Method |
| --- | --- |
| `GET /importapi/HolidayCalendar` | `get_holiday_calendars()` |
| `POST /importapi/HolidayCalendar/Import` | `import_holiday_calendars()` |

#### Order

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Order` | `get_orders()` |
| `POST /importapi/Order` | `import_orders()` |
| `GET /importapi/Order/CustomProperties` | `get_order_custom_properties()` |
| `POST /importapi/Order/Position` | `import_order_positions()` |
| `GET /importapi/Order/Position/RecordingTargets` | `get_order_position_recording_targets()` |
| `POST /importapi/Order/Position/RecordingTargets` | `import_order_position_recording_targets()` |
| `GET /importapi/Order/Position/RecordingTypeRates` | `get_order_position_recording_type_rates()` |
| `POST /importapi/Order/Position/RecordingTypeRates` | `import_order_position_recording_type_rates()` |
| `GET /importapi/Order/Position/Single` | `get_order_position()` |
| `GET /importapi/Order/Position/WorkPackages` | `get_order_position_work_packages()` |
| `POST /importapi/Order/Position/WorkPackages` | `import_order_position_work_packages()` |
| `GET /importapi/Order/Single` | `get_order()` |

#### Profile

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Profile/Certificates` | not implemented |
| `GET /importapi/Profile/Industries` | `get_profile_industries()` |
| `GET /importapi/Profile/Languages` | `get_profile_languages()` |
| `GET /importapi/Profile/ProfessionalExperience` | `get_profile_professional_experience()` |
| `GET /importapi/Profile/Publications` | `get_profile_publications()` |
| `GET /importapi/Profile/Roles` | not implemented |
| `GET /importapi/Profile/Testimonials` | `get_profile_testimonials()` |
| `GET /importapi/Profile/Trainings` | `get_profile_trainings()` |
| `GET /importapi/Profile/UserSkills` | `get_profile_user_skills()` |
| `POST /importapi/Profile/UserSkills` | `import_profile_user_skills()` |

#### Project

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Project` | `get_project()` |
| `HEAD /importapi/Project` | `project_exists()` |
| `GET /importapi/Project/AllProjects` | `get_all_projects()` |
| `GET /importapi/Project/BusinessUnits` | not implemented |
| `POST /importapi/Project/Comments/Batch` | `import_project_comments()` |
| `GET /importapi/Project/Contacts` | `get_project_contacts()` |
| `GET /importapi/Project/CustomProperties` | not implemented |
| `GET /importapi/Project/DeliveryModels` | not implemented |
| `POST /importapi/Project/Import` | `import_project()` |
| `POST /importapi/Project/ImportBatch` | `import_projects()` |
| `GET /importapi/Project/LegalEntities` | not implemented |
| `GET /importapi/Project/PracticeAreas` | not implemented |
| `GET /importapi/Project/Priorities` | not implemented |
| `GET /importapi/Project/ProjectStatus` | not implemented |
| `GET /importapi/Project/RecordingTargets` | `get_project_recording_targets()` |
| `POST /importapi/Project/RecordingTargets` | `import_project_recording_targets()` |
| `GET /importapi/Project/ReferenceStatus` | not implemented |
| `GET /importapi/Project/ResourceGroups` | not implemented |
| `GET /importapi/Project/ServiceLines` | not implemented |
| `GET /importapi/Project/TeamMembers` | `get_project_team_members()` |

#### Rate

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Rate` | `get_rates()` |
| `POST /importapi/Rate` | `import_rate()` |

#### RecordingType

| Endpoint | Method |
| --- | --- |
| `GET /importapi/RecordingType` | `get_recording_types()` |
| `POST /importapi/RecordingType` | `import_recording_type()` |

#### ResourceRequest

| Endpoint | Method |
| --- | --- |
| `GET /importapi/ResourceRequest` | not implemented |
| `POST /importapi/ResourceRequest` | `import_resource_request()` |
| `GET /importapi/ResourceRequest/Contacts` | `get_resource_request_contacts()` |
| `GET /importapi/ResourceRequest/CustomProperties` | not implemented |
| `GET /importapi/ResourceRequest/ServiceCategories` | `get_resource_request_service_categories()` |
| `GET /importapi/ResourceRequest/{requestid}` | `get_resource_request()` |

#### Role

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Role` | not implemented |
| `POST /importapi/Role` | `import_role()` |

#### Skill

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Skill` | not implemented |
| `GET /importapi/Skill/UserSkills` | not implemented |

#### Team

| Endpoint | Method |
| --- | --- |
| `GET /importapi/Team` | `get_teams()` |
| `POST /importapi/Team/ImportAsync` | `import_teams_async()` |
| `GET /importapi/Team/ImportStatus` | `get_team_import_status()` |
| `POST /importapi/Team/ImportSync` | `import_teams_sync()` |
| `GET /importapi/Team/Managers` | not implemented |
| `POST /importapi/Team/Managers` | not implemented |

#### TimeRecording

| Endpoint | Method |
| --- | --- |
| `GET /importapi/TimeRecording/RecordingEntries` | `get_recording_entries()` |
| `POST /importapi/TimeRecording/RecordingEntries` | `import_recording_entries()` |
| `GET /importapi/TimeRecording/RecordingTargets` | `get_recording_targets()` |
| `GET /importapi/TimeRecording/UserTimeSheet` | `get_user_time_sheet()` |
| `POST /importapi/TimeRecording/UserTimeSheet` | `import_user_time_sheet()` |

#### User

| Endpoint | Method |
| --- | --- |
| `GET /importapi/User` | `get_users()` |
| `GET /importapi/User/AuthorizationRoles` | `get_authorization_roles()` |
| `GET /importapi/User/CustomProperties` | not implemented |
| `POST /importapi/User/Echo` | not implemented |
| `GET /importapi/User/EmployeeTypes` | `get_employee_types()` |
| `POST /importapi/User/ImportAsync` | `import_users_async()` |
| `GET /importapi/User/ImportStatus` | `get_user_import_status()` |
| `POST /importapi/User/ImportSync` | `import_users_sync()` |
| `POST /importapi/User/ProfileImage` | not implemented |

#### UserHolidayCalendar

| Endpoint | Method |
| --- | --- |
| `GET /importapi/UserHolidayCalendar` | `get_user_holiday_calendars()` |
| `POST /importapi/UserHolidayCalendar/Import` | `import_user_holiday_calendars()` |

#### WorkingTimePattern

| Endpoint | Method |
| --- | --- |
| `GET /importapi/WorkingTimePattern` | `get_working_time_patterns()` |
| `POST /importapi/WorkingTimePattern/Import` | `import_working_time_patterns()` |

#### WorkPackage

| Endpoint | Method |
| --- | --- |
| `GET /importapi/WorkPackage` | `get_work_packages()` |
| `POST /importapi/WorkPackage` | `import_work_package()` |
| `GET /importapi/WorkPackage/Candidates` | `get_work_package_candidates()` |
| `POST /importapi/WorkPackage/Candidates` | `import_work_package_candidates()` |
| `GET /importapi/WorkPackage/CustomProperties` | `get_work_package_custom_properties()` |
| `GET /importapi/WorkPackage/OrderPositions` | `get_work_package_order_positions()` |
| `POST /importapi/WorkPackage/OrderPositions` | `import_work_package_order_positions()` |
| `GET /importapi/WorkPackage/OrderPositions/RecordingTargets` | `get_work_package_order_position_recording_targets()` |
| `GET /importapi/WorkPackage/RecordingTargets` | `get_work_package_recording_targets()` |
| `POST /importapi/WorkPackage/RecordingTargets` | `import_work_package_recording_targets()` |
| `GET /importapi/WorkPackage/{workpackageid}` | `get_work_package()` |
<!-- api-coverage:end -->

## App Client (`DecidaloAppClient`)

The App Client wraps the decidalo App API (`api.decidalo.app`).
It is used for reading data from decidalo — searching for people, viewing profiles, exploring skills, certificates, and projects.

> [!NOTE]
> The App API does not have a public Swagger UI.
> The client was reverse-engineered from the decidalo web application.

### Authentication

The App Client authenticates via OAuth2 (Microsoft SSO) through `login.decidalo.app`.
There are two authentication flows:

1. **Device Code Flow** (interactive, for first-time setup) — prints a URL and code to the console for you to open in a browser.
2. **Refresh Token Flow** (headless, for automation) — reuses a previously obtained refresh token.

```python
import asyncio
from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.auth import DecidaloAuth

async def first_time_login() -> None:
    """Interactive login — run this once to obtain a refresh token."""
    token = await DecidaloAuth.device_code_login()
    # The device code flow prints a URL and code to the console.
    # Open the URL in your browser and enter the code to authenticate.
    print(f"Save this refresh token for future use: {token.refresh_token}")

asyncio.run(first_time_login())
```

Store the refresh token securely (e.g. in an environment variable or a secrets manager).
For subsequent runs, use the refresh token:

```python
token = await DecidaloAuth.refresh("your-saved-refresh-token")
```

### Minimal Working Example

```python
import asyncio
from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.auth import DecidaloAuth

async def main() -> None:
    # Use a refresh token obtained from a previous device_code_login()
    token = await DecidaloAuth.refresh("your-saved-refresh-token")

    async with DecidaloAppClient(token=token) as client:
        # Search for people with specific skills
        results = await client.search.find_people(keywords=["SAP", "Python"])
        for user in results.usersWithMatchedQualities:
            print(f"User {user.userId} (Score: {user.score})")

        # Get a user's profile header
        header = await client.profile.get_header(user_id=42)
        print(f"Profile quality: {header.profileQuality}, last edited by: {header.lastEditor}")

        # Browse available skill categories
        categories = await client.skills.get_categories()
        for cat in categories:
            print(f"Category: {cat.categoryName}")

asyncio.run(main())
```

You can also pass a static Bearer token string directly if you manage tokens yourself:

```python
async with DecidaloAppClient(token="your-bearer-token") as client:
    ...
```

### App Client Features

- Async HTTP client built on `aiohttp` with automatic token refresh
- OAuth2 Device Code Flow and Refresh Token Flow (direct OIDC HTTP, no extra dependency)
- Type-safe Pydantic models for most responses
- Domain-based API structure:
  - **Search** — Find people by skills/keywords, autocomplete user names, get filter fields
  - **Profile** — Read profile headers, skills, certificates, languages, industries, roles, competencies, projects
  - **Projects** — Get project headers, overviews, details, team members, references
  - **Skills** — Autocomplete skills, get levels, categories, skill grids, assessments
  - **Certificates** — Autocomplete certificates, get holders, certificate grids
  - **Roles** — Get roles, check user skills/certificates against role requirements
  - **Teams** — Get team details, find teams by manager, get members under current user

## Development

Clone the repository and install the development environment:

```bash
git clone https://github.com/Hochfrequenz/decidalo_client.py.git
cd decidalo_client.py
uv sync --group dev
```

To sync the Import Client with the current API, download the spec and regenerate the Pydantic models from it:

```bash
curl -o openapi/v1/swagger.json https://import.decidalo.dev/swagger/v1/swagger.json
uv run --group codegen datamodel-codegen --input openapi/v1/swagger.json --output src/decidalo_client/models/_autogenerated.py --input-file-type openapi --output-model-type pydantic_v2.BaseModel --target-python-version 3.11 --use-annotated --use-double-quotes --collapse-root-models --field-constraints --strict-nullable --use-standard-collections --enum-field-as-literal one --extra-fields ignore --set-default-enum-member
uv run --group codegen ruff format src/decidalo_client/models/_autogenerated.py
uv run --group codegen ruff check --select I --fix src/decidalo_client/models/_autogenerated.py
```

Then run the tests: `unittests/test_models.py` checks that the models match the spec, and `unittests/test_api_coverage.py` checks the [API Coverage](#api-coverage) section of this README against the spec and the client.
To print the expected content of that section, run:

```bash
PYTHONPATH=src uv run --group tests python unittests/test_api_coverage.py
```

For detailed information on the development setup (uv configuration, IDE setup, etc.), see the [Hochfrequenz Python Template Repository](https://github.com/Hochfrequenz/python_template_repository).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
