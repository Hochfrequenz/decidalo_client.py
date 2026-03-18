# decidalo_app_client: Design Spec

**Date:** 2026-03-17
**Status:** Draft (one open question; see Auth section)

## Context

`decidalo_client.py` already provides a Python client for the Import API (`import.decidalo.dev`).
This spec defines a second client — `decidalo_app_client` — for the App API (`api.decidalo.app`),
living in the same repository as a separate package.

The App API is undocumented and reverse-engineered from HAR captures. The full endpoint analysis
lives in the sibling repository `decidalo-api` (not part of this repo) at
`docs/superpowers/specs/2026-03-17-decidalo-api-design.md`. A local clone of that repo is required
to read the reference spec; it is not embedded here.

**Primary use case:** Find people with specific skills or certificates, read profiles, explore project teams.

---

## Package Structure

```
src/
  decidalo_client/              # existing, unchanged
  decidalo_app_client/
    __init__.py                 # exports DecidaloAppClient, TokenResponse
    client.py                   # DecidaloAppClient + context manager
    auth.py                     # Device Code Flow + Refresh Token
    exceptions.py               # AppAPIError, AppAuthError
    _http.py                    # HttpHelper class (internal)
    models/
      __init__.py               # re-exports all public models
      search.py                 # GlobalSearchRequest, GlobalSearchResponse, SearchUser, ...
      profile.py                # ProfileHeader, SkillsPreview, ProfileProject, ...
      projects.py               # ProjectHeader, ProjectOverview, TeamMember, ...
      skills.py                 # Skill, SkillCategory, SkillLevel, SkillAssessment, ...
      certificates.py           # Certificate, CertificateHolder, ...
      roles.py                  # Role, RoleSkillCheck, RoleCertCheck, ...
      teams.py                  # TeamDetails, ...
      metamodel.py              # ViewMetamodelResult, MetamodelRow (internal helpers)
    domains/
      search.py                 # SearchDomain
      profile.py                # ProfileDomain
      projects.py               # ProjectsDomain
      skills.py                 # SkillsDomain
      certificates.py           # CertsDomain
      roles.py                  # RolesDomain
      teams.py                  # TeamsDomain
unittests/
  test_app_client_auth.py       # excluded from coverage (see Testing section)
  test_app_client_metamodel.py  # unit tests for resolve_row()
  test_app_client_search.py
  test_app_client_profile.py
  test_app_client_projects.py
  test_app_client_skills.py
  test_app_client_certificates.py
  test_app_client_roles.py
  test_app_client_teams.py
```

---

## Build & Tooling Changes

`decidalo_app_client` is a second package inside the same repo and the same wheel. The existing
hatchling build uses `only-include = ["src"]`, so the new package is picked up automatically —
no structural change to `pyproject.toml` is needed.

The following changes are required:

- **`pyproject.toml` `[project.optional-dependencies]`**: Add `msal` under a new `app` extra:
  `app = ["msal"]`. Users install it with `pip install decidalo-client[app]`. This keeps `msal`
  out of the dependency set for existing Import API consumers who do not need the App client.
  After editing `pyproject.toml`, regenerate `requirements.txt` by running:
  `pip-compile --extra app --output-file=requirements.txt pyproject.toml`
  (`requirements.txt` is pip-compiled and must not be hand-edited; it is installed by all tox
  envs via `-r requirements.txt`, so this single regeneration makes `msal` available at test,
  lint, and type-check time without modifying any tox env's `deps`).
- **`tox.ini` — `pylint`**: Add `decidalo_app_client` (bare module name, same form as the
  existing `pylint decidalo_client`; relies on `PYTHONPATH = {toxinidir}/src`).
- **`tox.ini` — `mypy`**: Add `src/decidalo_app_client` (src-prefixed path, same form as the
  existing `mypy ... src/decidalo_client`).
- **`tox.ini` — coverage**: Add `*/decidalo_app_client/auth.py` to both `coverage html` and
  `coverage report` omit patterns so that untestable auth logic does not pull coverage below 80%.
  (`unittests/*` is already omitted, covering test files automatically.)

---

## Authentication

The App API uses OAuth2 Bearer tokens from `https://login.decidalo.app` (IdentityServer4 → Microsoft SSO).
ROPC is not available.

**OAuth2 library:** `msal` (Microsoft Authentication Library). It supports Device Code Flow natively,
handles token caching internally during a session, and is the canonical library for Microsoft identity.
Added as a new dependency.

### `auth.py` — `DecidaloAuth`

**Device Code Flow** (initial, interactive):
```python
token: TokenResponse = await DecidaloAuth.device_code_login()
```
Prints a code and URL for the user to open in a browser. Polls until completion.

**Refresh Token Flow** (headless, subsequent use):
```python
token: TokenResponse = await DecidaloAuth.refresh(refresh_token="...")
```

**`TokenResponse`** (Pydantic model):
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None
    expires_at: datetime          # UTC datetime, not Unix timestamp or ISO string
```

The library does not persist tokens. Callers are responsible for secure storage.

### `DecidaloAppClient` constructor

```python
DecidaloAppClient(token: str | TokenResponse)
```

- Raw `str` → treated as a permanent access token; refresh is **disabled**.
- `TokenResponse` → refresh is **enabled** if `refresh_token` is not `None`.

**Auto-refresh strategy:** Before every request, `expires_at` is compared to `datetime.now(UTC)`.
If the token is expired (or expires within 60 seconds), a silent refresh is attempted using the
`refresh_token`. If the refresh fails (expired refresh token, revoked, network error), an
`AppAuthError` is raised immediately — no retry of the original request.

```python
async with DecidaloAppClient(token=token_response) as client:
    results = await client.search.find_people(keywords=["SAP"])
```

**Open question (blocks final approval):** Whether Device Code Flow works against
`login.decidalo.app` with Microsoft SSO must be verified live. `auth.py` will be implemented
as designed but must be manually tested before the PR is merged. The spec status remains Draft
until this is confirmed.

---

## Internal HTTP Layer

`_http.py` defines `HttpHelper`, a class (not a bare module) instantiated once by `DecidaloAppClient`
and passed by reference to all domain objects. It holds no session itself — it receives the
session from `DecidaloAppClient` via a setter called in `__aenter__`. Session lifecycle (create
in `__aenter__`, close in `__aexit__`) remains the sole responsibility of `DecidaloAppClient`,
exactly as in the existing `DecidaloClient`.

```python
class HttpHelper:
    def set_session(self, session: aiohttp.ClientSession, get_token: Callable[[], str]) -> None: ...
    async def get(self, path: str, params: dict | None = None) -> str: ...
    async def post(self, path: str, data: str | None = None) -> str: ...
```

`get_token` is a callable that `DecidaloAppClient` provides; `HttpHelper` calls it before each
request to obtain the current (possibly refreshed) Bearer token.

---

## Exceptions

`AppAPIError` and `AppAuthError` are **independent** of the existing `decidalo_client` exception
hierarchy. They do not extend `DecidaloClientError`. Both packages are separate products that
happen to share a repo; callers use them independently.

```python
class AppAPIError(Exception):
    def __init__(self, status_code: int, message: str): ...

class AppAuthError(Exception):
    """Raised when authentication fails or cannot be refreshed."""
```

---

## Metamodel Parsing

Several endpoints return a generic column-based structure instead of named fields.

### Pattern 1 — `viewMetamodelResult`
Used by: `Profile/{id}/Header`, `Profile/{id}/EmployeeInfoSection`, `ProjectReference/{id}/Header`, etc.
```json
{ "viewMetamodelResult": [
    { "columnName": "FirstName", "columnID": 42, "data": "Max", "label": "Vorname" }
]}
```

### Pattern 2 — Integer-keyed `data`
Used by: `Profile/{id}/ProjectsSection`, `Profile/{id}/ProfessionalExperienceSection`,
`ProjectReference/GetProjectReferences`, etc.
```json
{ "entityColumns": [{ "viewMetamodelEntryID": 154, "column": { "columnName": "ProjectName" }}],
  "data": [{ "154": "Projekt XYZ", "181": "2024-01-01" }] }
```

### `resolve_row()` — Pattern 2

```python
def resolve_row(columns: list[EntityColumn], row: dict[str, Any]) -> dict[str, Any]:
    """Maps integer string keys to columnName values, using the entityColumns from the same response."""
```

`resolve_row()` resolves **dynamically** from the `entityColumns` the API returns alongside each
`data` row — it does not use hardcoded column ID maps. If a key in `row` has no matching
`viewMetamodelEntryID` in `columns`, a `KeyError` is raised. Hard failure is intentional:
silent data loss is worse, and an unexpected key means the API has changed.

### Pattern 1 — `viewMetamodelResult` column names

For Pattern 1 endpoints, the `columnName` values (e.g. `"FirstName"`, `"LastName"`) are known
from the HAR capture and hardcoded in the domain model per endpoint. If the API changes a
`columnName`, the domain model will fail to populate the relevant field (Pydantic will raise or
leave it as `None` depending on the field definition). This is also considered acceptable for v1.

Domain modules call both helpers internally and return semantically named Pydantic models.
Callers never see integer keys or raw `viewMetamodelResult` arrays.

---

## Domain Methods

### `client.search`
| Method | API endpoint |
|--------|-------------|
| `find_people(keywords, start_date, end_date, filters)` | `POST /api/Search/GlobalSearch` |
| `autocomplete_user(pattern)` | `GET /api/Search/GetSearchUsersForAutocomplete` |
| `get_filter_fields()` | `GET /api/UiView/GlobalSearchFilter` |

Note: `get_filter_fields()` is included here (not excluded as `UiView/BookingOverview` is) because
it is required to construct valid `metamodelFilters` for `find_people()`.

### `client.skills`
| Method | API endpoint |
|--------|-------------|
| `autocomplete(pattern)` | `GET /api/Skill/AutocompleteSkill` |
| `get_grid(filters, page)` | `POST /api/Skill/Grid` |
| `get_categories()` | `GET /api/Skill/Categories` |
| `get_levels()` | `GET /api/Skill/SkillLevels` |
| `get_mappings(skill_id)` | `GET /api/Skill/Mappings/{skillId}` |
| `get_assessments(filters)` | `POST /api/SkillLists/Assessments` |
| `get_lists()` | `GET /api/SkillLists` |

### `client.profile`
| Method | API endpoint |
|--------|-------------|
| `get_header(user_id)` | `GET /api/Profile/{id}/Header` |
| `get_skills_preview(user_id)` | `GET /api/Profile/{id}/SkillsPreview` — **provisional**: HAR sample was truncated; response shape (whether `skillName`/`skillId` are present) must be verified live before the Pydantic model is finalised |
| `get_roles(user_id)` | `GET /api/Profile/{id}/RolesSection` |
| `get_projects(user_id)` | `GET /api/Profile/{id}/ProjectsSection` |
| `get_certificates(user_id)` | `GET /api/Profile/{id}/Certificates` |
| `get_languages(user_id)` | `GET /api/Profile/{id}/LanguageSection` |
| `get_industries(user_id)` | `GET /api/Profile/{id}/IndustrySection` |
| `get_professional_experience(user_id)` | `GET /api/Profile/{id}/ProfessionalExperienceSection` |
| `get_employee_info(user_id)` | `GET /api/Profile/{id}/EmployeeInfoSection` |
| `get_core_competencies(user_id)` | `GET /api/Profile/{id}/CoreCompetencies` |
| `get_language_levels()` | `GET /api/Profile/LanguageLevels` |

### `client.projects`
| Method | API endpoint |
|--------|-------------|
| `get_references(filters, page)` | `POST /api/ProjectReference/GetProjectReferences` |
| `get_header(project_id)` | `GET /api/ProjectReference/{id}/Header` |
| `get_overview(project_id)` | `GET /api/ProjectReference/{id}/Overview` |
| `get_details(project_id)` | `GET /api/ProjectReference/{id}/Details` |
| `get_team(project_id)` | `GET /api/ProjectReference/{id}/TeamMembers` |
| `get_contacts(project_id)` | `GET /api/ProjectReference/{id}/ProjectContacts` |
| `get_all_team_members_for_user(user_id)` | `GET /api/ProjectReference/GetAllVisibleProjectTeamMembersForContact/{userId}` |
| `get_filter_fields()` | `GET /api/UiView/ProjectReferencesGrid` |

Note: `get_filter_fields()` is included (not excluded as `UiView/BookingOverview` is) because
it is required to construct valid filters for `get_references()`.

### `client.certificates`
| Method | API endpoint |
|--------|-------------|
| `autocomplete(pattern, count)` | `GET /api/Certificates/Autocomplete` |
| `get_grid(filters, page)` | `POST /api/Certificates/GetCertificates` |
| `get(certificate_id)` | `GET /api/Certificates/{id}` |
| `get_holders(certificate_id, page_size, page_index)` | `GET /api/Certificates/{id}/CertificateHolders` |

### `client.roles`
| Method | API endpoint |
|--------|-------------|
| `get(role_id)` | `GET /api/Role/{roleId}` |
| `check_user_skills(role_id, user_id)` | `GET /api/Role/{roleId}/User/{userId}/Skills` |
| `check_user_certificates(role_id, user_id)` | `GET /api/Role/{roleId}/User/{userId}/Certificates` |

### `client.teams`
| Method | API endpoint |
|--------|-------------|
| `get_details(team_id)` | `GET /api/Teams/{id}/TeamDetails` |
| `get_by_manager(manager_id)` | `GET /api/Teams/GetTeamsByManager/{managerId}` |
| `get_members_under_current_user()` | `GET /api/Teams/TeamMembersUnderCurrentUser` |
| `get_resource_group_members()` | `GET /api/ResourceGroup/GetResourceGroupsMembersByManager` |

---

## Testing

- `aioresponses` mocks all HTTP calls — no real API calls in tests.
- Test files are split per domain (one file per domain + one for metamodel + one for auth).
- **`auth.py` is excluded from coverage measurement** in `tox.ini` (add to `omit`). Device Code
  Flow and Token Refresh cannot be meaningfully tested without a live OIDC server; coverage
  exclusion is explicit and intentional.
- **Two test levels:**
  1. Unit tests for `resolve_row()` in `test_app_client_metamodel.py`.
  2. Per-domain integration tests that mock a full API response (derived from `api_extracted.json`)
     and assert the returned Pydantic model is correctly populated.
- Auth is mocked in domain tests: `DecidaloAppClient` receives a raw `access_token: str` directly,
  disabling refresh logic entirely.
- `test_app_client_auth.py` exists as a placeholder only (documents manual test steps); it is
  already excluded from coverage because `unittests/*` is in the existing omit pattern.
  The source file `src/decidalo_app_client/auth.py` is additionally excluded via
  `*/decidalo_app_client/auth.py` in the `tox.ini` omit patterns.

---

## Out of Scope

The following discovered endpoints are explicitly not implemented:

- `Permissions/*` — authorization checks for UI rendering
- `Customization/*` — user UI preferences
- `StatusAutomation/*` — workflow automation config
- `UiView/BookingOverview` — booking UI config (other `UiView/*` endpoints are included; see domain tables)
- `Profile/{id}/ChangesSinceRejection` — approval workflow
- `Profile/{id}/Status`, `Profile/{id}/AccountInfo` — internal profile management
- `User/{id}/VisibleMenuItems` — navigation config
- `Shortlist` — unknown, likely UI state
- AI Agent (`decidalo-v3-prod-vrm-agent-container.azurewebsites.net`) — auth requirements unconfirmed
