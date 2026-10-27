# prowlarr2tx

Periodically search [Prowlarr](https://prowlarr.com) and send popular results
(by grab count) to [Transmission](https://transmissionbt.com). Each search is a
**job**, defined by one JSON file.

## Jobs

Put one file per job in `~/.config/prowlarr2tx/jobs/` (see
[`examples/job.example.json`](examples/job.example.json)):

| key | meaning |
| --- | --- |
| `interval_hours` | how often the daemon runs this job (default 1) |
| `state` | name of the state file, default = job name. Jobs using the same name share history, so two indexers never download the same item twice |
| `prowlarr.*` | `url`, `api_key`, `indexer_id`, `category_id`, `timeout` |
| `transmission.*` | `host`, `port`, `username`, `password`, `download_dir` |
| `search.*` | `query`, `min_grabs`, `max_results` |

The API key can instead be set with `PROWLARR2TX_API_KEY_<JOBNAME>` (job name upper-cased).

## Usage

Install with [uv](https://docs.astral.sh/uv/) (recommended, isolated and on your PATH):

```sh
uv tool install git+https://github.com/lbesnard/prowlarr2tx   # from GitHub
uv tool install .                                             # from a local clone
uv tool upgrade prowlarr2tx                                   # later, to update
```

Or run without installing: `uvx --from . prowlarr2tx list`. Plain `pip install .` also works.

```sh
prowlarr2tx list
prowlarr2tx run              # all jobs, once
prowlarr2tx run bfunk        # one job (name or path to a .json)
prowlarr2tx daemon           # all jobs forever, on their intervals
```

State lives in `~/.local/state/prowlarr2tx/<state>.json` and is written
atomically (a full disk can no longer empty it). A corrupt state file is moved
to `*.corrupt` and the job refuses to run rather than starting from scratch.
Logs rotate (5 MB x 3) in `~/.local/state/prowlarr2tx/logs/`, with API keys redacted.
Override locations with `PROWLARR2TX_CONFIG_DIR`, `PROWLARR2TX_STATE_DIR`, `PROWLARR2TX_LOG_DIR`.

## Docker

```sh
mkdir -p config/jobs state logs
cp examples/job.example.json config/jobs/myjob.json   # edit it
docker compose up -d --build
docker compose logs -f
```

Volumes: `./config` (read-only jobs), `./state` (history), `./logs`. Point them
elsewhere with `PROWLARR2TX_CONFIG`, `PROWLARR2TX_STATE`, `PROWLARR2TX_LOGS`,
e.g. `PROWLARR2TX_CONFIG=~/.config/prowlarr2tx`. The container runs as your
UID/GID (`export UID GID` if your shell does not) so mounted state is writable.
Compose uses host networking so LAN names like `*.home` resolve; remove it if
you use IPs or set `dns:`/`extra_hosts:`.

One-off run in the container: `docker compose run --rm prowlarr2tx run`.

## Tests

```sh
uv run --extra test pytest
```
