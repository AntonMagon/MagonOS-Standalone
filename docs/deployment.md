# Deployment

## Production entrypoint

Use the standalone WSGI app through gunicorn:

```bash
cd /Users/anton/Desktop/MagonOS-Standalone
./scripts/run_deploy.sh
```

## Required environment

- `MAGON_STANDALONE_DB_PATH` - SQLite file path
- `PORT` or `MAGON_STANDALONE_PORT` - bind port
- `MAGON_STANDALONE_HOST` - bind host, default `0.0.0.0`
- `MAGON_STANDALONE_DEFAULT_QUERY` - default operator pipeline query
- `MAGON_STANDALONE_DEFAULT_COUNTRY` - default country code
- `MAGON_STANDALONE_INTEGRATION_TOKEN` - optional feedback ingest token
- `MAGON_STANDALONE_BOOTSTRAP_FIXTURE` - optional one-time fixture seed for empty DBs

## Notes

- This is a deployable standalone runtime, not Odoo.
- SQLite is acceptable for one-node deployment and internal staging.
- If `MAGON_STANDALONE_BOOTSTRAP_FIXTURE` is set and the DB does not yet exist, the deploy entrypoint seeds it once before gunicorn starts.
- Horizontal scale is not solved here; SQLite remains the constraint.
- `scripts/run_platform.sh` is the local product entrypoint.
- `scripts/run_deploy.sh` is the production/server entrypoint.
