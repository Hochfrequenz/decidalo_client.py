# decidalo_client.py

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python Versions (officially) supported](https://img.shields.io/pypi/pyversions/decidalo_client.svg)
![Pypi status badge](https://img.shields.io/pypi/v/decidalo_client)

![Unittests status badge](https://github.com/Hochfrequenz/decidalo_client.py/workflows/Unittests/badge.svg)
![Coverage status badge](https://github.com/Hochfrequenz/decidalo_client.py/workflows/Coverage/badge.svg)
![Linting status badge](https://github.com/Hochfrequenz/decidalo_client.py/workflows/Linting/badge.svg)
![Formatting status badge](https://github.com/Hochfrequenz/decidalo_client.py/workflows/Formatting/badge.svg)

An async Python client for the [decidalo](https://decidalo.de/) V3 Import API.

> [!IMPORTANT]
> This is a community project and is not an official decidalo client.
> It is not affiliated with or endorsed by decidalo GmbH.

## Installation

```bash
pip install decidalo_client
```

## Usage

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

## Features

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
