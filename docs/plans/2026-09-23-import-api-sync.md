# Import API Sync (September 2026)

**Goal:** Bring the Import Client (`src/decidalo_client/`) in line with the current decidalo V3 Import API
([live spec](https://import.decidalo.dev/swagger/v1/swagger.json)).

**Status:** Implemented in #100 (branch `feat/sync-import-api-2026-09`), to be released as v0.3.0.

**Out of scope:** The App Client (`src/decidalo_app_client/`), which has no public spec.

---

## Analysis

The local spec `openapi/v1/swagger.json` was last synced in #87 (2026-08-05). A structural diff against the live spec
(ignoring descriptions, summaries and examples) showed:

- Operations: 92 → 110 (18 new, none removed)
- Schemas: 291 → 338 (47 new, none removed, 43 structurally changed)
- Breaking changes of the API:
  - `TimeRecordingEntryStatus`: `Draft` was replaced by `Open`; `Cancelled` and `CancellationSubmitted` were added
  - `OrderImportItem` / `OrderImportOutput`: `projectCode` and `projectReferenceID` were replaced by `projects`
  - `ProjectReferencePropertiesInput` / `-Output`: eight classification fields are `SelectOptionFieldInput`
    instead of `TextFieldInput`
  - `GET /importapi/Order`: `projectCode` and `projectReferenceId` became arrays

The critical problem: 316 of 338 schemas declare `additionalProperties: false`, so datamodel-codegen generated all
models with `extra="forbid"`. Every field the API adds to a response made parsing fail, e.g. `get_users()` on
`UserOverview.lastLoginDate`. The unit tests stayed green because their mocks still used the old response format.

Auditing every client method against all spec versions in the repository revealed long-standing bugs (present since
the initial setup and hidden by mocks that mirrored the same wrong paths and formats):

- `import_teams_async`, `get_companies` and `import_project` called paths that exist in no spec version
- `project_exists` expected HTTP 200, but the API answers 204, so it always returned `False`; it also built its query
  string by hand without URL encoding
- `get_user_import_status` and `get_team_import_status` parsed a single object, but the API returns a list
- Several filters were sent under names that exist in no spec version and were silently ignored: `get_users`
  (`created_since`, `edited_since`), `get_teams` (all four), `get_companies` (all three), `get_bookings` and
  `get_all_projects` (`created_since`, `edited_since`)

In addition, many existing GET methods offered only part of the documented filters, and 27 operations of the previous
spec had never been wrapped.

## Decisions

1. **Unknown fields are ignored** (`--extra-fields ignore` for all models).
   Alternatives: only response models lenient, which datamodel-codegen cannot do (it sets `extra` globally; 34 schemas
   are used in requests *and* responses) and would need a spec preprocessing script; `allow`, which would also send
   unknown fields in requests. Trade-off: request models drop misspelled or outdated keyword arguments silently at
   runtime; the pydantic mypy plugin with `init_forbid_extra = true` catches them statically (documented in the README).
2. **Clean state over backward compatibility.** Unsupported filters are removed instead of being deprecated or mapped:
   the old calls never filtered, and a `DeprecationWarning` is invisible outside of tests.
3. **Scope:** a full sync in one PR (fix, spec sync, adaptation to the breaking changes of the API, filter cleanup,
   parameter parity, 18 new endpoints). The 27 operations that were never wrapped are a follow-up.
4. **Version:** v0.3.0, as a breaking change in 0.x is a minor bump. The version comes from the git tag (hatch-vcs);
   breaking changes and migration notes go into the GitHub release notes (no CHANGELOG.md).
5. **Long-standing bugs are fixed spec-conform**, including the return types (the import status methods return the
   documented lists with all filters instead of a convenience single object).
6. **Every method maps its operation 1:1** (see [the rule below](#the-11-mapping-rule)).
7. **Array parameters** keep the singular spec name and are typed `list[X]` (no union with the scalar type); they are
   sent as repeated query keys (`?projectCode=A&projectCode=B`).
8. **Dates:** parameters of format `date` take a `datetime.date`, those of format `date-time` a timezone-aware
   `datetime.datetime` (sent as ISO 8601). A naive datetime raises `ValueError`, because the API would assume the local
   time of the server; a datetime passed to a date parameter raises `TypeError`. The `date-time` parameters are
   annotated as pydantic's `AwareDatetime` (review feedback): the signature shows the timezone requirement, as in the
   models. For mypy it is a plain `datetime`, and annotations are not validated at runtime, so `_format_datetime` keeps
   the check.
9. **Remaining legacy is removed:** exact spelling of the query keys, `work_package_id` like everywhere else,
   `is not None` checks, query parameters via the request helpers (URL encoding), request arguments that are the
   request body models of the spec (`import_teams_sync(batch)`, `import_bookings_async(batch)`,
   `import_working_time_patterns(patterns)`), pylint remnants, stale docstrings, methods and tests grouped by domain.
10. **The README lists the API coverage** (every operation of the spec, grouped by tag), guarded by a drift test.
11. **Enum defaults are enum members** (`--set-default-enum-member`); plain string defaults caused pydantic serializer
    warnings, e.g. in `import_recording_entries()`.
12. **"Empty on delete":** the four import methods whose delete response is documented as empty
    (`import_activity_type`, `import_general_activity`, `import_rate`, `import_recording_type`) return `X | None`.
13. **Plans are kept** as a record, even when they no longer describe the current state (review feedback); the initial
    setup plan got a note that it is historical.
14. **Date bounds are documented** (review feedback): the docstring of every date filter states whether it includes
    its bound, as the spec documents it. The spec leaves this open for `get_absences(start_date, end_date)`,
    `get_bookings(start_date_before, end_date_after)` and `get_work_packages(start_date_before, end_date_after)`; their
    docstrings say so instead of guessing.

## The 1:1 Mapping Rule

- One public method of `DecidaloClient` wraps exactly one operation of the spec (checked by
  `unittests/test_api_coverage.py`).
- Path, query parameters, request body and return type follow the spec.
- The keyword argument is the snake_case form of the spec name, splitting glued words (`userid` → `user_id`); the query
  key is sent in the exact spelling of the spec; the arguments follow the order of the spec.
- Filters are keyword-only, path parameters are positional.
- Types follow the spec: `int`, `bool` (sent as `true`/`false`), `str`, the generated enums (sent as their value),
  `UUID`, `list[X]` (repeated keys), `date` and `AwareDatetime` (ISO 8601).
- The request argument is the request body model of the spec, named `batch` for batch models and after the domain
  otherwise.

## Implementation

Commits, in order (each green on its own):

- `build: generate models with --extra-fields ignore`
- `feat!: sync OpenAPI spec with the live import API`
- `test: update response mocks to the current API format`
- `refactor: group client methods and tests by domain`
- `chore: remove pylint remnants and tidy up the client tests`
- `refactor: accept list values and query params in all request helpers`
- `fix: call the documented endpoints for team, company and project imports`
- `fix: report existing projects correctly in project_exists`
- `fix!: return the import status lists the API documents`
- `fix!: remove query filters the API does not support`
- `refactor!: align query keys and request signatures with the spec`
- `feat!: type date query parameters as date and datetime`
- `docs: remove the outdated initial setup plan` (reverted later, see decision 13)
- `feat!: expose all documented query filters on existing GET methods`
- `feat: wrap holiday calendar, recording type and rate endpoints`
- `feat: wrap time recording entry and work package endpoints`
- `feat: wrap comment, authorization role and service category endpoints`
- `docs: document the API coverage of the Import Client in the README`
- `build: generate enum members as defaults of enum fields`
- `fix!: return None when the API answers a deletion with an empty body`
- `revert: keep the initial setup plan`
- `docs: mark the initial setup plan as historical`
- `docs: add the plan of the Import API sync` (this document)
- `refactor: annotate date-time parameters as AwareDatetime`
- `docs: state whether the date filters include their bounds`

The parameter parity and the 18 new endpoints were implemented in parallel in separate worktrees and cherry-picked.

The breaking changes for users of the package are listed in the description of #100 (section "Breaking Changes /
Migration"), which also serves as release notes for v0.3.0.

## Tests

- The existing mocks use the current response format, and the tests assert the new fields.
- `unittests/test_models.py`: every schema of the spec has a model (and vice versa), no model forbids extra fields,
  no enum field defaults to a plain string, and the breaking changes of the API are documented.
- `unittests/test_api_coverage.py`: every method calls a documented operation, no operation is wrapped twice, and the
  API coverage section of the README is up to date.
- `unittests/test_client.py`: no parameter is annotated as a plain `datetime`.
- Per method: aioresponses matches the full URL including the query, so the mocks verify the exact query keys; one
  test per method passes all parameters, and the POST tests assert the serialized request body.
- Result: 131 → 198 tests, coverage 95 % → 97 %. Not verified against the live API (no API key available).

## Follow-ups

- Wrap the 27 remaining operations (see the API coverage section of the README).
- `GET /importapi/TimeRecording/RecordingEntries` reports the total row count in the `x-row-count` header, which the
  client does not expose.
- `CommentPropertiesInput` requires `comment` and `creator` even for deletes, although the spec describes them as
  optional in that case.
- Run a read-only smoke test against the live API.
- Verify the undocumented date bounds of `get_absences`, `get_bookings` and `get_work_packages` against the live API
  (decision 14).

## How to Sync Next Time

Follow the "Development" section of the README: download the spec, regenerate the models with the documented command,
then run the tests. `unittests/test_models.py` and `unittests/test_api_coverage.py` point out what has to be updated
(regenerated models, README coverage section, methods calling removed operations).
