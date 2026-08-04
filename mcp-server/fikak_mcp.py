#!/usr/bin/env python3
"""
MCP Server for the Fikak Platform (local Docker + Frappe stack).

This server lets an LLM client (e.g. Claude Desktop) manage the local
Fikak Docker Compose stack and interact with the Frappe backend it runs:
checking service health, starting/stopping the stack, and submitting a
task (Frappe ToDo) to the running platform.

Transport: stdio (this is a local, single-user integration that shells
out to the `docker` CLI on the machine it runs on - see MCP best
practices for stdio vs streamable HTTP).
"""

import asyncio
import ipaddress
import json
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Configuration (environment variables - set these in claude_desktop_config.json
# or a .env file loaded by your shell before launching the server)
# ---------------------------------------------------------------------------

# Absolute path to the fikak_app repo clone that contains the compose file
# (e.g. "/Users/you/fikak_app"). Required for start/stop/status.
FIKAK_REPO_PATH = os.environ.get("FIKAK_REPO_PATH", "").strip()

# Compose file name, relative to FIKAK_REPO_PATH.
FIKAK_COMPOSE_FILE = os.environ.get("FIKAK_COMPOSE_FILE", "docker-compose.unified.yml")

# Frappe backend base URL (the frappe_backend / nginx entry point).
FIKAK_BASE_URL = os.environ.get("FIKAK_BASE_URL", "http://localhost:8000").rstrip("/")

# Frappe credentials used by fikak_submit_task to authenticate.
# Defaults match Frappe's standard admin account; password must be supplied.
FIKAK_ADMIN_USERNAME = os.environ.get("FIKAK_ADMIN_USERNAME", "Administrator")
FIKAK_ADMIN_PASSWORD = os.environ.get("FIKAK_ADMIN_PASSWORD", "")

HTTP_TIMEOUT = 10.0
COMPOSE_COMMAND_TIMEOUT = 30.0
# `up -d` blocks until any `depends_on: condition: service_healthy` chains are
# satisfied (e.g. frappe_configurator -> frappe_backend), which routinely takes
# well over 30s, so it gets its own, longer budget.
COMPOSE_UP_TIMEOUT = 150.0
# `stop`/`down` send SIGTERM and wait up to 10s per container before SIGKILL, so a
# ~10-service stack needs far more than the default read-only budget.
COMPOSE_STOP_TIMEOUT = 180.0

mcp = FastMCP("fikak_mcp")


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


def _repo_error() -> Optional[str]:
    """Validate FIKAK_REPO_PATH / compose file, returning an error message or None."""
    if not FIKAK_REPO_PATH:
        return (
            "Error: FIKAK_REPO_PATH is not set. Set it to the absolute path of your "
            "fikak_app clone (the directory containing "
            f"{FIKAK_COMPOSE_FILE}), e.g. in claude_desktop_config.json's "
            '"env" block: {"FIKAK_REPO_PATH": "/Users/you/fikak_app"}.'
        )
    repo = Path(FIKAK_REPO_PATH)
    compose_path = repo / FIKAK_COMPOSE_FILE
    if not compose_path.is_file():
        return (
            f"Error: Compose file not found at {compose_path}. Check that "
            "FIKAK_REPO_PATH points at your fikak_app clone and that "
            f"{FIKAK_COMPOSE_FILE} exists there."
        )
    return None


async def _run_compose(*args: str, timeout: float = COMPOSE_COMMAND_TIMEOUT) -> Dict[str, Any]:
    """Run `docker compose -f <file> <args>` in the repo directory.

    Returns a dict with keys: returncode, stdout, stderr. Raises FileNotFoundError
    if the `docker` executable is not on PATH.
    """
    cmd = ["docker", "compose", "-f", FIKAK_COMPOSE_FILE, *args]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=FIKAK_REPO_PATH,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"`{' '.join(cmd)}` timed out after {timeout}s") from None

    return {
        "returncode": proc.returncode,
        "stdout": stdout_bytes.decode(errors="replace"),
        "stderr": stderr_bytes.decode(errors="replace"),
    }


def _parse_compose_ps(stdout: str) -> List[Dict[str, str]]:
    """Parse `docker compose ps --all --format json` output.

    Compose >= 2.21.0 emits JSON Lines - one object per line. Older versions
    emit a single JSON array instead (optionally pretty-printed across many
    lines). Both shapes are handled: try the whole output as one JSON value
    first (matches the array case, since json.loads tolerates embedded
    newlines within a single value), then fall back to line-by-line NDJSON.
    """
    raw_entries: List[Any] = []
    stripped = stdout.strip()
    if stripped:
        try:
            whole = json.loads(stripped)
        except json.JSONDecodeError:
            whole = None
        if isinstance(whole, list):
            raw_entries = whole
        else:
            for line in stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    raw_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    services = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        health = entry.get("Health") or ""
        state = entry.get("State") or "unknown"
        services.append(
            {
                "name": entry.get("Name", entry.get("Service", "unknown")),
                "service": entry.get("Service", ""),
                "state": state,
                "health": health,
                "status": entry.get("Status", ""),
                "exit_code": str(entry.get("ExitCode", "")),
            }
        )
    return services


def _is_settled(service: Dict[str, str]) -> bool:
    """True if a service is running and healthy, or is the configurator's one-shot exit.

    `docker-compose.unified.yml` defines `frappe_configurator` with
    `condition: service_completed_successfully`, so it exits by design once it has
    done its job - that must count as settled, not "not running". This is scoped to
    that one service specifically: any *other* exited service (including code 0 from
    a graceful `docker compose stop`) is genuinely not running and must not be
    reported as ready, or a fully stopped platform would summarize as healthy.
    """
    if service["state"] == "running":
        return service["health"] in ("", "healthy")
    return (
        service["service"] == "frappe_configurator"
        and service["state"] == "exited"
        and service["exit_code"] == "0"
    )


def _summarize_services(services: List[Dict[str, str]]) -> str:
    if not services:
        return "no services found"
    settled = sum(1 for s in services if _is_settled(s))
    unhealthy = [s["name"] for s in services if s["state"] == "running" and s["health"] == "unhealthy"]
    not_settled = [s["name"] for s in services if not _is_settled(s) and s["name"] not in unhealthy]
    parts = [f"{settled}/{len(services)} services ready"]
    if unhealthy:
        parts.append(f"unhealthy: {', '.join(unhealthy)}")
    if not_settled:
        parts.append(f"not ready: {', '.join(not_settled)}")
    return "; ".join(parts)


async def _check_backend_reachable() -> Dict[str, Any]:
    """Probe the Frappe login page to see if the backend is answering HTTP requests."""
    url = f"{FIKAK_BASE_URL}/login"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(url)
            return {"reachable": True, "status_code": resp.status_code}
    except httpx.RequestError as e:
        return {"reachable": False, "error": f"{type(e).__name__}: {e}"}


class FikakAuthError(Exception):
    """Raised when Frappe login fails."""


class FikakConnectionError(Exception):
    """Raised when the Frappe backend cannot be reached at all."""


def _is_loopback_host(hostname: Optional[str]) -> bool:
    if not hostname:
        return False
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _assert_base_url_safe_for_credentials(url: str) -> None:
    """Refuse to send the admin password over plaintext HTTP to a non-local host."""
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and _is_loopback_host(parsed.hostname):
        return
    raise FikakAuthError(
        f"Error: Refusing to send Frappe credentials to {url} - it is not HTTPS and not a "
        "localhost/127.0.0.1 address, which would send the admin password in cleartext over "
        "the network. Set FIKAK_BASE_URL to an https:// URL, or use http:// only for local "
        "addresses (localhost, 127.0.0.1, ::1)."
    )


# Frappe embeds a `frappe.csrf_token = "...";` assignment in the /app page's inline
# script for authenticated sessions; there is no dedicated REST endpoint for it.
_CSRF_TOKEN_RE = re.compile(r'frappe\.csrf_token\s*=\s*"([0-9a-fA-F]+)"')


async def _frappe_get_csrf_token(client: httpx.AsyncClient) -> Optional[str]:
    """Best-effort fetch of the current session's CSRF token from the Frappe desk boot payload.

    Returns None if it can't be found (e.g. developer_mode=1 disables CSRF enforcement
    entirely, or the page shape differs) - callers should treat a missing token as
    "no CSRF header to send" rather than an error, since the site may not require one.
    """
    try:
        resp = await client.get(f"{FIKAK_BASE_URL}/app")
    except httpx.RequestError:
        return None
    match = _CSRF_TOKEN_RE.search(resp.text)
    return match.group(1) if match else None


async def _frappe_login(client: httpx.AsyncClient) -> Optional[str]:
    """Authenticate the given httpx client against Frappe, storing the session cookie.

    Returns the session's CSRF token if one could be found (needed for subsequent
    POST/PUT/DELETE requests when CSRF enforcement is active), or None otherwise.
    """
    if not FIKAK_ADMIN_PASSWORD:
        raise FikakAuthError(
            "Error: FIKAK_ADMIN_PASSWORD is not set. Set it to the ADMIN_PASSWORD value "
            "from your fikak_app .env file (in claude_desktop_config.json's \"env\" block)."
        )
    _assert_base_url_safe_for_credentials(FIKAK_BASE_URL)
    try:
        resp = await client.post(
            f"{FIKAK_BASE_URL}/api/method/login",
            json={"usr": FIKAK_ADMIN_USERNAME, "pwd": FIKAK_ADMIN_PASSWORD},
        )
    except httpx.RequestError as e:
        raise FikakConnectionError(
            f"Error: Could not reach Fikak backend at {FIKAK_BASE_URL} ({type(e).__name__}: {e}). "
            "Is the platform running? Try fikak_get_status or fikak_start_platform first."
        ) from e

    if resp.status_code != 200:
        raise FikakAuthError(
            f"Error: Frappe login failed with status {resp.status_code}. Check that "
            "FIKAK_ADMIN_USERNAME/FIKAK_ADMIN_PASSWORD match the credentials in your "
            ".env file."
        )

    return await _frappe_get_csrf_token(client)


async def _frappe_create_doc(doctype: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Log in and create a Frappe document, returning the created document's fields."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        csrf_token = await _frappe_login(client)
        headers = {"X-Frappe-CSRF-Token": csrf_token} if csrf_token else {}
        try:
            resp = await client.post(
                f"{FIKAK_BASE_URL}/api/resource/{doctype}", json=data, headers=headers
            )
        except httpx.RequestError as e:
            raise FikakConnectionError(
                f"Error: Could not reach Fikak backend at {FIKAK_BASE_URL} while creating "
                f"the {doctype}: {type(e).__name__}: {e}"
            ) from e

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Error: Failed to create {doctype} (status {resp.status_code}): {resp.text[:500]}"
            )
        payload = resp.json()
        return payload.get("data", payload)


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------

class FikakStatusInput(BaseModel):
    """Input model for checking Fikak platform status."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    )


class FikakStartInput(BaseModel):
    """Input model for starting the Fikak platform."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    wait_for_healthy: bool = Field(
        default=True,
        description="If true, poll service health after starting and wait until all services "
        "are healthy or the timeout elapses. If false, return immediately after issuing the "
        "start command.",
    )
    timeout_seconds: int = Field(
        default=180,
        description="Maximum seconds to wait for services to become healthy when "
        "wait_for_healthy is true.",
        ge=30,
        le=600,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    )


class FikakStopInput(BaseModel):
    """Input model for stopping the Fikak platform."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    remove_containers: bool = Field(
        default=False,
        description="If false (default), stop containers but keep them and their data volumes "
        "(equivalent to `docker compose stop`) so a later fikak_start_platform is fast. If true, "
        "remove containers and networks (`docker compose down`) while still preserving named "
        "volumes (database/site data is not deleted either way).",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    )


class TaskPriority(str, Enum):
    """Priority levels for a Fikak task (Frappe ToDo)."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class FikakSubmitTaskInput(BaseModel):
    """Input model for submitting a task to the Fikak platform."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    description: str = Field(
        ...,
        description="The task text, e.g. 'Review the financing application for user 1000000000'",
        min_length=1,
        max_length=1000,
    )
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    due_date: Optional[str] = Field(
        default=None,
        description="Due date in YYYY-MM-DD format, e.g. '2026-08-15'. Omit for no due date.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    assign_to: Optional[str] = Field(
        default=None,
        description="Email/username of the Frappe user to assign the task to. Defaults to the "
        "authenticated user (FIKAK_ADMIN_USERNAME) if omitted.",
        max_length=140,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description cannot be empty or whitespace only")
        return v.strip()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="fikak_get_status",
    annotations={
        "title": "Get Fikak Platform Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fikak_get_status(params: FikakStatusInput) -> str:
    """Report the current status of the local Fikak platform (Docker services + Frappe backend).

    Checks two things: (1) the Docker Compose services defined in the Fikak stack -
    which containers exist, whether they are running, and their health check state;
    and (2) whether the Frappe backend actually answers HTTP requests at
    FIKAK_BASE_URL (default http://localhost:8000). It does NOT modify anything.

    Args:
        params (FikakStatusInput): Validated input parameters containing:
            - response_format (ResponseFormat): 'markdown' or 'json' (default: markdown)

    Returns:
        str: Status report. In JSON format, the schema is:
        {
            "docker_available": bool,
            "services": [
                {"name": str, "service": str, "state": str, "health": str, "status": str}
            ],
            "summary": str,
            "backend": {"reachable": bool, "status_code": int} or {"reachable": false, "error": str}
        }
        Or "Error: <message>" if FIKAK_REPO_PATH is misconfigured or Docker is unavailable.

    Examples:
        - Use when: "What is the status of my Fikak Platform?" -> params with defaults
        - Use when: "Is the backend up?" -> params with defaults, check the backend field
        - Don't use when: you want to start the platform (use fikak_start_platform instead)

    Error Handling:
        - Returns "Error: FIKAK_REPO_PATH is not set..." if the repo path env var is missing
        - Returns "Error: Docker is not installed or not on PATH..." if `docker` cannot be found
        - Returns "Error: `docker compose ps` failed..." with stderr if Docker is installed but
          the daemon is down or the command otherwise errors (distinct from an unstarted stack,
          which returns "no services found" instead)
        - Backend unreachable is reported in the result, not raised as an error (the platform
          may simply not be started yet - see fikak_start_platform)
    """
    err = _repo_error()
    if err:
        return err

    try:
        result = await _run_compose("ps", "--all", "--format", "json")
    except FileNotFoundError:
        return (
            "Error: Docker is not installed or not on PATH. Install Docker Desktop and make "
            "sure it is running before checking Fikak platform status."
        )
    except TimeoutError as e:
        return f"Error: {e}"

    if result["returncode"] != 0:
        return f"Error: `docker compose ps` failed:\n{result['stderr'][-2000:]}"

    services = _parse_compose_ps(result["stdout"])
    backend = await _check_backend_reachable()
    summary = _summarize_services(services)

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "docker_available": True,
                "services": services,
                "summary": summary,
                "backend": backend,
            },
            indent=2,
        )

    lines = ["# Fikak Platform Status", "", f"**Summary**: {summary}", ""]
    if services:
        lines.append("## Services")
        for s in services:
            health_str = f" ({s['health']})" if s["health"] else ""
            lines.append(f"- **{s['name']}**: {s['state']}{health_str} - {s['status']}")
    else:
        lines.append("No services found. The platform has not been started yet - "
                      "try fikak_start_platform.")
    lines.append("")
    lines.append("## Backend")
    if backend.get("reachable"):
        lines.append(f"- Reachable at {FIKAK_BASE_URL} (HTTP {backend['status_code']})")
    else:
        lines.append(f"- Not reachable at {FIKAK_BASE_URL}: {backend.get('error', 'unknown error')}")
    return "\n".join(lines)


@mcp.tool(
    name="fikak_start_platform",
    annotations={
        "title": "Start Fikak Platform",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fikak_start_platform(params: FikakStartInput) -> str:
    """Start the Fikak platform's Docker services (`docker compose up -d`).

    This brings up all containers defined in the Fikak Docker Compose stack
    (MariaDB, Redis, the Frappe backend, workers, scheduler, Socket.IO, and the
    frontend/proxy). It is idempotent: running it when services are already up
    has no additional effect. It does NOT create the Frappe site or install the
    custom fikak_app - if this is the very first run, use the repo's ./setup.sh
    and ./install-fikak-app.sh scripts for that one-time initialization first.

    Args:
        params (FikakStartInput): Validated input parameters containing:
            - wait_for_healthy (bool): poll until services are healthy (default: True)
            - timeout_seconds (int): max seconds to wait, 30-600 (default: 180)
            - response_format (ResponseFormat): 'markdown' or 'json' (default: markdown)

    Returns:
        str: Result report. In JSON format, the schema is:
        {
            "started": bool,
            "services": [
                {"name": str, "service": str, "state": str, "health": str, "status": str}
            ],
            "summary": str,
            "timed_out": bool
        }
        Or "Error: <message>" if FIKAK_REPO_PATH is misconfigured or Docker is unavailable.

    Examples:
        - Use when: "Start the Fikak Platform" -> params with defaults
        - Use when: "Start Fikak and don't wait for it to be ready" -> wait_for_healthy=False
        - Don't use when: the site doesn't exist yet (run ./setup.sh manually first)
        - Don't use when: you want to check status without starting anything (use fikak_get_status)

    Error Handling:
        - Returns "Error: FIKAK_REPO_PATH is not set..." if the repo path env var is missing
        - Returns "Error: Docker is not installed or not on PATH..." if `docker` cannot be found
        - Returns "Error: `docker compose up` failed..." with stderr if the command itself fails
        - If services don't reach healthy state within timeout_seconds, returns a report with
          "timed_out": true rather than raising - check which services are unhealthy
    """
    err = _repo_error()
    if err:
        return err

    try:
        up_result = await _run_compose("up", "-d", timeout=COMPOSE_UP_TIMEOUT)
    except FileNotFoundError:
        return "Error: Docker is not installed or not on PATH. Install Docker Desktop first."
    except TimeoutError as e:
        return f"Error: {e}"

    if up_result["returncode"] != 0:
        return f"Error: `docker compose up -d` failed:\n{up_result['stderr'][-2000:]}"

    timed_out = False
    services: List[Dict[str, str]] = []
    try:
        if params.wait_for_healthy:
            elapsed = 0
            interval = 5
            while True:
                ps_result = await _run_compose("ps", "--all", "--format", "json")
                services = _parse_compose_ps(ps_result["stdout"])
                if services and all(_is_settled(s) for s in services):
                    break
                if elapsed >= params.timeout_seconds:
                    timed_out = True
                    break
                await asyncio.sleep(interval)
                elapsed += interval
        else:
            ps_result = await _run_compose("ps", "--all", "--format", "json")
            services = _parse_compose_ps(ps_result["stdout"])
    except FileNotFoundError:
        return "Error: Docker is not installed or not on PATH. Install Docker Desktop first."
    except TimeoutError as e:
        return f"Error: {e}"

    summary = _summarize_services(services)

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {"started": True, "services": services, "summary": summary, "timed_out": timed_out},
            indent=2,
        )

    lines = ["# Fikak Platform Start", "", f"**Summary**: {summary}"]
    if timed_out:
        lines.append(f"**Warning**: Timed out after {params.timeout_seconds}s waiting for all "
                      "services to become healthy. They may still be starting - check again "
                      "with fikak_get_status.")
    lines.append("")
    lines.append("## Services")
    for s in services:
        health_str = f" ({s['health']})" if s["health"] else ""
        lines.append(f"- **{s['name']}**: {s['state']}{health_str} - {s['status']}")
    return "\n".join(lines)


@mcp.tool(
    name="fikak_stop_platform",
    annotations={
        "title": "Stop Fikak Platform",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def fikak_stop_platform(params: FikakStopInput) -> str:
    """Stop the Fikak platform's Docker services.

    By default runs `docker compose stop` (containers are stopped but kept, so a
    later fikak_start_platform is fast). If remove_containers is true, runs
    `docker compose down` instead, which removes containers and networks but
    still preserves named volumes - your database and site files are not deleted
    either way.

    Args:
        params (FikakStopInput): Validated input parameters containing:
            - remove_containers (bool): use `down` instead of `stop` (default: False)
            - response_format (ResponseFormat): 'markdown' or 'json' (default: markdown)

    Returns:
        str: Result report. In JSON format, the schema is:
        {"stopped": bool, "containers_removed": bool, "message": str}
        In markdown format, a one-line confirmation. Or "Error: <message>" on failure.

    Examples:
        - Use when: "Stop the Fikak Platform" -> params with defaults
        - Use when: "Tear down the Fikak containers" -> remove_containers=True
        - Don't use when: you only want to check status (use fikak_get_status)

    Error Handling:
        - Returns "Error: FIKAK_REPO_PATH is not set..." if the repo path env var is missing
        - Returns "Error: `docker compose ...` failed..." with stderr if the command fails
    """
    err = _repo_error()
    if err:
        return err

    subcommand = "down" if params.remove_containers else "stop"
    try:
        result = await _run_compose(subcommand, timeout=COMPOSE_STOP_TIMEOUT)
    except FileNotFoundError:
        return "Error: Docker is not installed or not on PATH. Install Docker Desktop first."
    except TimeoutError as e:
        return f"Error: {e}"

    if result["returncode"] != 0:
        return f"Error: `docker compose {subcommand}` failed:\n{result['stderr'][-2000:]}"

    action = "stopped and containers removed" if params.remove_containers else "stopped"
    message = f"Fikak platform {action}. Data volumes are preserved."

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {"stopped": True, "containers_removed": params.remove_containers, "message": message},
            indent=2,
        )
    return message


@mcp.tool(
    name="fikak_submit_task",
    annotations={
        "title": "Submit Task to Fikak Platform",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def fikak_submit_task(params: FikakSubmitTaskInput) -> str:
    """Submit a task to the Fikak platform, creating a Frappe ToDo record.

    This authenticates against the running Frappe backend (FIKAK_BASE_URL) using
    FIKAK_ADMIN_USERNAME/FIKAK_ADMIN_PASSWORD, then creates a ToDo document - Frappe's
    built-in task/reminder doctype, available on every Frappe site regardless of
    which custom apps (e.g. fikak_app) are installed. The platform must already be
    running (see fikak_start_platform / fikak_get_status).

    Args:
        params (FikakSubmitTaskInput): Validated input parameters containing:
            - description (str): the task text, 1-1000 characters
            - priority (TaskPriority): 'Low', 'Medium', or 'High' (default: Medium)
            - due_date (Optional[str]): due date as YYYY-MM-DD, or omitted for none
            - assign_to (Optional[str]): user to assign the task to, defaults to the
              authenticated admin user if omitted
            - response_format (ResponseFormat): 'markdown' or 'json' (default: markdown)

    Returns:
        str: Result report. In JSON format, the schema is:
        {
            "name": str,          # the ToDo document's ID, e.g. "d4f8a1c2b3"
            "description": str,
            "priority": str,
            "status": str,        # always "Open" for a newly created task
            "date": str or null,
            "url": str            # link to view the task in the Frappe desk
        }
        Or "Error: <message>" if authentication or creation fails.

    Examples:
        - Use when: "Submit a task to my platform" -> prompts for a description, then
          params with that description and defaults
        - Use when: "Add a high-priority task to review the KYC queue" ->
          description="Review the KYC queue", priority="High"
        - Don't use when: the platform isn't running yet (use fikak_start_platform first)

    Error Handling:
        - Returns "Error: FIKAK_ADMIN_PASSWORD is not set..." if credentials are missing
        - Returns "Error: Could not reach Fikak backend..." if the platform isn't running
        - Returns "Error: Frappe login failed..." if credentials are wrong
        - Returns "Error: Failed to create ToDo..." with the backend's response on other failures
    """
    data: Dict[str, Any] = {
        "description": params.description,
        "priority": params.priority.value,
    }
    if params.due_date:
        data["date"] = params.due_date
    if params.assign_to:
        data["allocated_to"] = params.assign_to

    try:
        doc = await _frappe_create_doc("ToDo", data)
    except (FikakAuthError, FikakConnectionError) as e:
        return str(e)
    except RuntimeError as e:
        return str(e)

    name = doc.get("name", "unknown")
    result = {
        "name": name,
        "description": doc.get("description", params.description),
        "priority": doc.get("priority", params.priority.value),
        "status": doc.get("status", "Open"),
        "date": doc.get("date"),
        "url": f"{FIKAK_BASE_URL}/app/todo/{name}",
    }

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(result, indent=2)

    lines = [
        "# Task Submitted",
        "",
        f"- **ID**: {result['name']}",
        f"- **Description**: {result['description']}",
        f"- **Priority**: {result['priority']}",
        f"- **Status**: {result['status']}",
    ]
    if result["date"]:
        lines.append(f"- **Due date**: {result['date']}")
    lines.append(f"- **Link**: {result['url']}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
