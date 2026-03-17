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

Install the base package (Import Client only):

```bash
pip install decidalo-client
```

To also use the App Client, install with the `app` extra (this adds the [`msal`](https://github.com/AzureAD/microsoft-authentication-library-for-python) dependency for OAuth2 authentication):

```bash
pip install decidalo-client[app]
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
- Type-safe request/response models using `pydantic`
- All major API endpoints:
  - **Users** - Get users, import users (sync/async), check import status
  - **Teams** - Get teams, import teams (sync/async), check import status
  - **Companies** - Get companies, import companies
  - **Projects** - Get projects, get all projects, import projects, check existence
  - **Bookings** - Get bookings, get bookings by project, import bookings
  - **Absences** - Get absences, import absences
  - **Resource Requests** - Get resource requests, import resource requests
  - **Roles** - Import roles
  - **Working Time Patterns** - Get working time patterns, import working time patterns

## App Client (`DecidaloAppClient`)

The App Client wraps the decidalo App API (`api.decidalo.app`).
It is used for reading data from decidalo — searching for people, viewing profiles, exploring skills, certificates, and projects.

> [!NOTE]
> The App API does not have a public Swagger UI.
> The client was reverse-engineered from the decidalo web application.

### Authentication

The App Client authenticates via OAuth2 (Microsoft SSO) through `login.decidalo.app`.
There are two authentication flows:

1. **Device Code Flow** (interactive, for first-time setup) — opens a browser for login and returns tokens.
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
        for user in results.users:
            print(f"{user.displayName} (Score: {user.matchScore})")

        # Get a user's profile header
        header = await client.profile.get_header(user_id=42)
        print(f"Profile: {header.firstName} {header.lastName}")

        # Browse available skill categories
        categories = await client.skills.get_categories()
        for cat in categories:
            print(f"Category: {cat.name}")

asyncio.run(main())
```

You can also pass a static Bearer token string directly if you manage tokens yourself:

```python
async with DecidaloAppClient(token="your-bearer-token") as client:
    ...
```

### App Client Features

- Async HTTP client built on `aiohttp` with automatic token refresh
- OAuth2 Device Code Flow and Refresh Token Flow via `msal`
- Type-safe Pydantic models for all responses
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
tox -e dev
```

To regenerate the Pydantic models from the OpenAPI spec:

```bash
tox -e codegen
```

For detailed information on the development setup (tox configuration, IDE setup, etc.), see the [Hochfrequenz Python Template Repository](https://github.com/Hochfrequenz/python_template_repository).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
