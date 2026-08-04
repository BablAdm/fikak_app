# Fikak MCP Server

A local (stdio) MCP server that lets Claude manage your Fikak Docker Compose
stack and interact with the Frappe backend it runs.

## Tools

| Tool | Maps to | What it does |
|---|---|---|
| `fikak_get_status` | "What is the status of my Fikak Platform?" | Reports Docker service health + whether the Frappe backend answers HTTP requests. Read-only. |
| `fikak_start_platform` | "Start the Fikak Platform" | Runs `docker compose up -d` and optionally waits for services to become healthy. |
| `fikak_stop_platform` | "Stop the Fikak Platform" | Runs `docker compose stop` (or `down` if asked to remove containers). Data volumes are always preserved. |
| `fikak_submit_task` | "Submit a task to my platform" | Creates a Frappe `ToDo` document via the REST API. Works on any Frappe site, including before the custom `fikak_app` is installed. |

`fikak_start_platform` brings up existing containers — it does **not** create
the Frappe site or install `fikak_app`. For first-time setup, run
`./setup.sh` and `./install-fikak-app.sh` from the repo root yourself first.

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   cd mcp-server
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Find your `ADMIN_PASSWORD` (needed for `fikak_submit_task`):

   ```bash
   grep '^ADMIN_PASSWORD=' /path/to/fikak_app/.env | cut -d= -f2-
   ```

3. Add the server to your Claude Desktop config
   (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

   ```json
   {
     "mcpServers": {
       "fikak": {
         "command": "/absolute/path/to/fikak_app/mcp-server/venv/bin/python3",
         "args": ["/absolute/path/to/fikak_app/mcp-server/fikak_mcp.py"],
         "env": {
           "FIKAK_REPO_PATH": "/absolute/path/to/fikak_app",
           "FIKAK_BASE_URL": "http://localhost:8000",
           "FIKAK_ADMIN_USERNAME": "Administrator",
           "FIKAK_ADMIN_PASSWORD": "<paste the ADMIN_PASSWORD from step 2>"
         }
       }
     }
   }
   ```

4. Restart Claude Desktop. You should now be able to say things like:
   - "What is the status of my Fikak Platform?"
   - "Start the Fikak Platform"
   - "Submit a task to my platform: review the KYC queue, high priority"

## Configuration reference

See `.env.example` for all environment variables. `FIKAK_REPO_PATH` and
`FIKAK_ADMIN_PASSWORD` are the two you must set; everything else has a
sensible default matching the unified Docker Compose stack.

## Testing without Claude Desktop

```bash
source venv/bin/activate
export FIKAK_REPO_PATH=/absolute/path/to/fikak_app
export FIKAK_ADMIN_PASSWORD=<your admin password>
npx @modelcontextprotocol/inspector python3 fikak_mcp.py
```

This opens a browser UI where you can call each tool directly and inspect
its input schema and output.

## Notes

- This server shells out to the `docker` CLI on the machine it runs on, so it
  must run **locally on the same machine as Docker Desktop** — not in a
  remote/cloud session. stdio transport (used here) is exactly for this kind
  of local, single-user integration.
- `fikak_submit_task` creates a Frappe `ToDo`, not an ERPNext `Task` — `ToDo`
  is a core Frappe doctype available on every site, so the tool works
  regardless of whether the custom `fikak_app`/ERPNext app is installed yet.
