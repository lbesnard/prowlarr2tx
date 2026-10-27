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
| `transmission.*` | `host` (name or URL such as `https://tx.example.org`), `port` (default 9091, or 443 for https), `protocol`/`path` (optional), `username`, `password`, `download_dir` |
| `search.*` | `query`, `min_grabs`, `max_results` |

### Finding `api_key`, `indexer_id` and `category_id`

These values are specific to **your** Prowlarr instance, so you must look them up.
Both IDs are sent to Prowlarr's `/api/v1/search` as `indexerIds` and `categories`.

**`api_key`**: Prowlarr > *Settings > General > Security > API Key*.

**`indexer_id`**: the numeric ID Prowlarr assigned when you added the indexer. It is
not shown in the main list, so query the API:

```sh
curl -s -H "X-Api-Key: $KEY" http://prowlarr.example:9696/api/v1/indexer \
  | jq -r '.[] | "\(.id)\t\(.name)"'
```

IDs are per-installation: the same tracker has a different ID on another setup, and
deleting and re-adding an indexer gives it a new ID.

**`category_id`**: a Newznab/Torznab category number. The standard ones are the same
everywhere:

| id | category | id | category |
| --- | --- | --- | --- |
| 1000 | Console | 5000 | TV |
| 2000 | Movies | 6000 | XXX |
| 3000 | Audio | 7000 | Books |
| 4000 | PC | 8000 | Other |

Each has sub-categories (e.g. `2040` Movies/HD, `5030` TV/SD, `1000` Console incl. its
children). The tracker's *own* custom categories (IDs of `100000` and above) are
specific to that indexer and your setup. To list what an indexer supports:

```sh
curl -s -H "X-Api-Key: $KEY" http://prowlarr.example:9696/api/v1/indexer/<indexer_id> \
  | jq -r '.capabilities.categories[] | "\(.id)\t\(.name)"'
```

A `category_id` the indexer does not support returns
no results, so if a job finds "0 items", check the pair first. A quick test in the
Prowlarr *Search* page with the same indexer, category and query should list what the
job will see.

Only one indexer and one category per job: create several job files for more.
`min_grabs` only has an effect if the indexer reports grab counts (usually
private trackers; many public ones report none, so nothing passes the threshold).

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

### Tab completion

Subcommands, options and job names (`prowlarr2tx run <TAB>`) complete. Add to `~/.zshrc`
(or `~/.bashrc`, using `bash`):

```sh
eval "$(prowlarr2tx completion zsh)"
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
