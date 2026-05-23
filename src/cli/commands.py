# src/cli/commands.py
from __future__ import annotations

import sys
import click

from src.parsers.registry import detect_format, get_parser
from src.storage.database import get_connection, init_db
from src.storage.repository import LogRepository, RepositoryError


def _get_repo(db_path: str) -> LogRepository:
    """Open a database connection and return a ready repository."""
    conn = get_connection(db_path)
    init_db(conn)
    return LogRepository(conn)


@click.group()
@click.option(
    "--db",
    default="data/logsense.db",
    envvar="DATABASE_PATH",  # also reads from DATABASE_PATH env var
    help="Path to the SQLite database file.",
    show_default=True,
)
@click.pass_context
def cli(ctx: click.Context, db: str) -> None:
    """LogSense — intelligent log analytics engine."""
    # Store the db path in context so every subcommand can access it
    ctx.ensure_object(dict)
    ctx.obj["db"] = db


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format", "fmt",
    default=None,
    help="Log format: apache, nginx, plaintext, json. Auto-detected if omitted.",
)
@click.pass_context
def ingest(ctx: click.Context, path: str, fmt: str) -> None:
    """Parse a log file and store all entries in the database."""
    repo = _get_repo(ctx.obj["db"])

    # Use provided format or detect from file extension
    format_name = fmt or detect_format(path)

    try:
        parser = get_parser(format_name)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Parse every line - collect successes and count skipped lines
    entries = []
    skipped = 0

    with open(path) as f:
        for line in f:
            entry = parser.parse(line)
            if entry:
                entries.append(entry)
            else:
                skipped += 1

    # Save all parsed entries in one transaction
    try:
        count = repo.save_many(entries)
        click.echo(f"Stored {count} entries, skipped {skipped} lines.")
    except RepositoryError as e:
        click.echo(f"Database error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option("--level", default=None, help="Filter by level: INFO, WARN, ERROR, DEBUG.")
@click.option("--since", default=None, help="Show entries after this datetime (ISO 8601).")
@click.option("--until", default=None, help="Show entries before this datetime (ISO 8601).")
@click.option("--ip", default=None, help="Filter by source IP address.")
@click.option("--status", default=None, type=int, help="Filter by HTTP status code.")
@click.option("--limit", default=50, show_default=True, help="Maximum entries to return.")
@click.pass_context
def query(ctx: click.Context, level, since, until, ip, status, limit) -> None:
    """Query stored log entries with optional filters."""
    repo = _get_repo(ctx.obj["db"])

    # Parse datetime strings if provided
    since_dt = None
    until_dt = None

    if since:
        try:
            from datetime import datetime, timezone
            since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
        except ValueError:
            click.echo("Error: --since must be a valid ISO 8601 datetime.", err=True)
            sys.exit(1)

    if until:
        try:
            from datetime import datetime, timezone
            until_dt = datetime.fromisoformat(until).replace(tzinfo=timezone.utc)
        except ValueError:
            click.echo("Error: --until must be a valid ISO 8601 datetime.", err=True)
            sys.exit(1)

    try:
        entries = repo.find(
            level=level,
            since=since_dt,
            until=until_dt,
            source_ip=ip,
            status_code=status,
            limit=limit,
        )
    except RepositoryError as e:
        click.echo(f"Database error: {e}", err=True)
        sys.exit(1)

    if not entries:
        click.echo("No entries found.")
        return

    # Print a simple table
    click.echo(f"{'ID':<6} {'TIMESTAMP':<25} {'LEVEL':<8} {'MESSAGE'}")
    click.echo("-" * 80)
    for e in entries:
        click.echo(f"{e.id:<6} {e.timestamp.isoformat():<25} {e.level:<8} {e.message[:60]}")

        