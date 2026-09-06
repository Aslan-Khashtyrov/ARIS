# A.R.I.S. architecture and authority map

_Status: source-derived map of `main` on 2026-09-06. This document describes tracked code, not the currently running process state._

## Non-negotiable boundaries

- A.R.I.S. is paper/simulation-only; `real_trading=false` is an invariant.
- No component documented here is authorized to place real orders, transfer funds, or use private exchange methods.
- Secrets, credential files, wallets, runtime journals, and local state are outside the review and remote-control boundary.
- GitHub task text is data, never shell input.
- Process changes require a separate, explicit user instruction naming the exact operation.
- Code changes use a dedicated branch, pull request, complete diff review, and passing safety checks.

## Selected startup path

The tracked launcher `aris_start_safe.sh` selects these top-level components:

| Component | Selected file | Startup role | Operational authority |
|---|---|---|---|
| Main paper engine | `main.py` | Started as a background process | Public market observation and its own simulated state only |
| Spot scanner | `multi_scanner_v03.py` | Started as a background process | Public market observation only |
| Guardian | `guardian_v04.py` | Started as a background process | Monitoring according to its tracked implementation |
| Worker | `aris_worker_v03.py` | Started as a background process | Local `STATUS`/`ANALYZE` queue plus hosted paper services |
| Autopilot | `aris_autopilot_v01.py` | Started as a background process | Supervises an explicit component allowlist; may restart only those local components |
| Termux GitHub controller | `aris_termux_control_v01.py` | Started as a background process | GitHub PING only, from a dedicated detached worktree |
| Foreman | `aris_foreman_v01.py` | Started as a background process | Read-only process/file freshness observation |
| Local core | `aris_local_core_v01.py` | Run in the launcher foreground | Prints a local status/analysis decision; no shell or trading authority |

`aris_start_safe.sh` does not select either legacy command bridge, either retired remote agent, or the updater.

## Worker-hosted paper services

Importing and running `aris_worker_v03.py` currently starts seven daemon supervisors inside one process:

| Supervisor | Module | Role |
|---|---|---|
| Cycle collector | `aris_cycle_collector_v01.py` | Produces public quote snapshots |
| Paper ledger | `aris_paper_ledger_v01.py` | Accounts for simulated cycle results |
| Operational report | `aris_operational_report_v01.py` | Aggregates a subset of runtime health and paper data |
| Cycle metrics | `aris_cycle_metrics_v02.py` | Produces cycle metrics artifacts |
| Cross-exchange analyzer | `aris_cross_exchange_v01.py` | Evaluates public cross-exchange observations |
| Cross paper ledger | `aris_cross_paper_ledger_v01.py` | Accounts for simulated cross-exchange results |
| Low-risk inventory model | `aris_cross_inventory_low_risk_v01.py` | Primary simulated inventory model selected by the worker |

`aris_cross_inventory_ledger_v01.py` is present but not started by the current worker. A worker restart affects all seven hosted services, so worker decomposition must be designed and reviewed before changing process layout.

## Remote and maintenance authority

| Component | Classification | Reads | Writes/actions | Explicitly forbidden |
|---|---|---|---|---|
| `aris_termux_control_v01.py` v0.8 | Active restricted bridge | One allowlisted GitHub PING record | PING status through its detached worktree | Arbitrary files, shell, process control, trading |
| `aris_codex_review_worker_v01.py` | Active restricted review bridge | Tracked repository source for predefined reviews | Redacted review result through its detached worktree | Free-form prompts, workspace writes, project execution, secrets, process control, trading |
| `aris_remote_agent_v01.py` | Retired compatibility stub | No polling or local files | Inert local PING response only | Git writes, backup, health checks, process control, trading |
| `aris_remote_agent_v02.py` | Retired compatibility stub | No polling or local files | Inert local PING response only | Git writes, backup, health checks, process control, trading |
| `aris_bridge_v01.py` | Legacy manual tool; not launcher-selected | Local status/history/log data | Manual backup capability | Must not be exposed to a remote bridge |
| `aris_bridge_v02.py` | Legacy manual tool; not launcher-selected | Local status/history/log data | Manual analysis and backup capability | Must not be exposed to a remote bridge |
| `aris_updater_v02.py` | Manual maintenance tool | Git state and tracked paths | Fast-forward live checkout; rollback on failed validation | Remote invocation or unattended authority |
| `aris_stop_safe.sh` | Manual stop tool | Trusted PID files and `/proc` identity | SIGTERM only after PID and identity validation | Invocation without exact current user authorization |
| `aris_restart_bridges_safe.sh` | Narrow activation tool | Exact bridge process identities | Restarts only the PING controller and launches the read-only Codex bridge | Any A.R.I.S. trading-component change |

The fact that a legacy or maintenance file is tracked does not make it remotely authorized.

## Data and ownership boundaries

Most component interfaces are files rather than Python imports. A future contract inventory must record, for every artifact:

1. exactly one authoritative writer;
2. all readers;
3. schema and version;
4. timestamp format and freshness limit;
5. atomic-write behavior;
6. deduplication/fingerprint rule;
7. paper-only and balance invariants;
8. behavior for missing, malformed, stale, NaN, or infinite values.

Known overlapping areas that need this inventory before refactoring:

- public market feeds in `main.py`, `multi_scanner_v03.py`, and `aris_cycle_collector_v01.py`;
- simulated state in `main.py` and the ledger modules;
- process/freshness observation in guardian, foreman, autopilot, and healthcheck code;
- reporting across operational, cycle, unified, and analysis modules;
- versioned artifact names that do not always match the producing module version.

## Legacy and retirement policy

The following are candidates for dependency review, not immediate deletion:

- older scanners, guardians, workers, cores, bridges, and `arbitrage_v0_1_8.py`;
- `aris_bridge_v01.py` and `aris_bridge_v02.py`;
- the non-selected standard inventory model;
- older or differently versioned reporting artifacts.

Before retiring any tracked file:

1. search all tracked references;
2. check launcher, supervisor, CI, and documentation references;
3. record whether external/manual use is unknown;
4. replace or migrate any owned state contract;
5. add regression coverage;
6. retire it in a small dedicated PR;
7. do not delete runtime data as part of source cleanup.

## Prioritized simplification sequence

1. Keep this authority map current and identify one owner per entrypoint and artifact.
2. Make `aris_worker_v03.py` import-safe by moving startup behind an explicit entrypoint, with tests, without changing service selection.
3. Separate local queue dispatch from hosted service startup in a later PR.
4. Extract low-risk shared utilities first: atomic JSON writes, timestamp parsing, finite-number validation, and fingerprints.
5. Compare market-feed and route-calculation behavior before consolidating implementations.
6. Keep every simulated balance and state format independent until equivalence tests prove a safe migration.
7. Build a retirement dependency matrix and remove only one proven-unused family at a time.

## Required validation gates

Every future PR must run `python -m compileall -q .` and the repository safety workflow. Changes must also run the targeted policy tests named in `AGENTS.md`.

Additional suites should be added to CI before accounting or routing refactors are accepted:

- cycle calculation and funding;
- paper-ledger balance conservation;
- fee and slippage calculations;
- exchange minimums and quantity steps;
- stale/malformed market data;
- cross-exchange and inventory invariants;
- report schema compatibility.

Cleanup, accounting changes, and authority expansion must never be combined in one PR.
