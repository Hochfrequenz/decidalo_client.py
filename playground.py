#!/usr/bin/env python
"""
Playground script for testing the decidalo client against the real API.

Usage:
    export DECIDALO_API_KEY="your-api-key"
    python playground.py

Or:
    python playground.py --api-key "your-api-key"

With custom base URL:
    python playground.py --api-key "your-api-key" --base-url "https://import.decidalo.dev"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from decidalo_client import (
    DecidaloAPIError,
    DecidaloAuthenticationError,
    DecidaloClient,
)


async def demo_get_users(client: DecidaloClient) -> None:
    """Demonstrate getting users from the API."""
    print("\n[1] Getting users...")
    try:
        users = await client.get_users()
        print(f"    Found {len(users)} users")
        for user in users[:5]:  # Show first 5
            print(f"    - {user.displayName} ({user.email})")
        if len(users) > 5:
            print(f"    ... and {len(users) - 5} more")
    except DecidaloAuthenticationError as e:
        print(f"    Authentication error: {e}")
    except DecidaloAPIError as e:
        print(f"    API error: {e}")


async def demo_get_teams(client: DecidaloClient) -> None:
    """Demonstrate getting teams from the API."""
    print("\n[2] Getting teams...")
    try:
        teams = await client.get_teams()
        print(f"    Found {len(teams)} teams")
        for team in teams[:5]:  # Show first 5
            print(f"    - {team.teamName} (ID: {team.teamID})")
        if len(teams) > 5:
            print(f"    ... and {len(teams) - 5} more")
    except DecidaloAuthenticationError as e:
        print(f"    Authentication error: {e}")
    except DecidaloAPIError as e:
        print(f"    API error: {e}")


async def demo_get_companies(client: DecidaloClient) -> None:
    """Demonstrate getting companies from the API."""
    print("\n[3] Getting companies...")
    try:
        companies = await client.get_companies()
        print(f"    Found {len(companies)} companies")
        for company in companies[:5]:  # Show first 5
            print(f"    - {company.companyName} (ID: {company.companyID})")
        if len(companies) > 5:
            print(f"    ... and {len(companies) - 5} more")
    except DecidaloAuthenticationError as e:
        print(f"    Authentication error: {e}")
    except DecidaloAPIError as e:
        print(f"    API error: {e}")


async def demo_get_projects(client: DecidaloClient) -> None:
    """Demonstrate getting projects from the API."""
    print("\n[4] Getting projects...")
    try:
        projects = await client.get_all_projects()
        print(f"    Found {len(projects)} projects")
        for project in projects[:5]:  # Show first 5
            name = project.properties.name.value if project.properties.name else "N/A"
            print(f"    - {name} (ID: {project.identifier.projectID})")
        if len(projects) > 5:
            print(f"    ... and {len(projects) - 5} more")
    except DecidaloAuthenticationError as e:
        print(f"    Authentication error: {e}")
    except DecidaloAPIError as e:
        print(f"    API error: {e}")


async def demo_get_bookings(client: DecidaloClient) -> None:
    """Demonstrate getting bookings from the API."""
    print("\n[5] Getting bookings...")
    try:
        bookings = await client.get_bookings()
        print(f"    Found {len(bookings)} bookings")
        for booking in bookings[:5]:  # Show first 5
            print(f"    - {booking.subject} (ID: {booking.bookingID}, " f"User: {booking.userID})")
        if len(bookings) > 5:
            print(f"    ... and {len(bookings) - 5} more")
    except DecidaloAuthenticationError as e:
        print(f"    Authentication error: {e}")
    except DecidaloAPIError as e:
        print(f"    API error: {e}")


async def demo_get_absences(client: DecidaloClient) -> None:
    """Demonstrate getting absences from the API."""
    print("\n[6] Getting absences...")
    try:
        result = await client.get_absences()
        absences = result.absences or []
        print(f"    Found {len(absences)} absences")
        for absence in absences[:5]:  # Show first 5
            print(
                f"    - {absence.subject} (ID: {absence.absenceId}, "
                f"User: {absence.userId}, {absence.startDate} - {absence.endDate})"
            )
        if len(absences) > 5:
            print(f"    ... and {len(absences) - 5} more")
    except DecidaloAuthenticationError as e:
        print(f"    Authentication error: {e}")
    except DecidaloAPIError as e:
        print(f"    API error: {e}")


async def demo_get_working_time_patterns(client: DecidaloClient) -> None:
    """Demonstrate getting working time patterns from the API."""
    print("\n[7] Getting working time patterns...")
    try:
        patterns = await client.get_working_time_patterns()
        print(f"    Found {len(patterns)} user working time profiles")
        for pattern in patterns[:5]:  # Show first 5
            user_id = pattern.userIdentity.userID if pattern.userIdentity else "N/A"
            num_patterns = len(pattern.workingTimePatterns) if pattern.workingTimePatterns else 0
            print(f"    - User {user_id}: {num_patterns} working time pattern(s)")
        if len(patterns) > 5:
            print(f"    ... and {len(patterns) - 5} more")
    except DecidaloAuthenticationError as e:
        print(f"    Authentication error: {e}")
    except DecidaloAPIError as e:
        print(f"    API error: {e}")


async def main(api_key: str, base_url: str) -> int:
    """Run playground examples.

    Args:
        api_key: The API key for authentication.
        base_url: The base URL of the API.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print("=" * 60)
    print("Decidalo Client Playground")
    print("=" * 60)
    print(f"Connecting to: {base_url}")
    print("-" * 60)

    try:
        async with DecidaloClient(api_key=api_key, base_url=base_url) as client:
            await demo_get_users(client)
            await demo_get_teams(client)
            await demo_get_companies(client)
            await demo_get_projects(client)
            await demo_get_bookings(client)
            await demo_get_absences(client)
            await demo_get_working_time_patterns(client)

        print("\n" + "=" * 60)
        print("Playground completed successfully!")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Playground script for testing the decidalo client against the real API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Using environment variable
    export DECIDALO_API_KEY="your-api-key"
    python playground.py

    # Using command line argument
    python playground.py --api-key "your-api-key"

    # With custom base URL
    python playground.py --api-key "your-api-key" --base-url "https://import.decidalo.dev"
        """,
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("DECIDALO_API_KEY"),
        help="API key for authentication (default: DECIDALO_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="https://import.decidalo.dev",
        help="Base URL of the API (default: https://import.decidalo.dev)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.api_key:
        print("Error: API key is required.")
        print("Either set the DECIDALO_API_KEY environment variable or use --api-key")
        sys.exit(1)

    exit_code = asyncio.run(main(args.api_key, args.base_url))
    sys.exit(exit_code)
