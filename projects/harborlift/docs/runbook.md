# Runbook

## Preconditions

- Docker running, ports 5441/5442/8181 free.
- Python 3.12+ with `requirements.txt` installed.

## Execute

```bash
docker compose up -d
python -m harborlift.lab
```

Expected: every step `ok`; `web/last_run.json` and `web/report.html` are rewritten.

## During the run

The lab freezes both databases before the snapshot. Any write returns
`cannot execute INSERT in a read-only transaction` and is recorded as an expected rejection.

## Rollback drill

The lab stops the target app, unfreezes the source, restarts the app against the source and validates
the checksum plus a successful write. The target stays frozen until the next run resets it.

## Teardown

`scripts/teardown.sh` removes only this compose project (containers and volumes).

## Failure handling

If restore fails, the target stays frozen and the source is never unfrozen; the report records the
failed step and the recovery point remains the snapshot.
