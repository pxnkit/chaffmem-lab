# API guide

Start the local service:

```bash
chaffmem serve
```

Interactive documentation is available at `http://127.0.0.1:8000/docs`.

## Conventions

- JSON requests use versioned typed schemas
- Validation errors use structured FastAPI responses
- Experiment creation accepts an optional idempotency key
- Lists use bounded pagination
- Unknown policy, attack, defense, or backend identifiers are rejected
- Artifact routes accept run identifiers, not arbitrary paths
- Request size is bounded by configuration

## Health

`GET /health` reports process health.

`GET /ready` verifies that the artifact store can be initialized.

## Catalog

`GET /api/v1/policies`

`GET /api/v1/attacks`

`GET /api/v1/defenses`

Catalog entries include stable identifiers and a short behavior description.

## Experiments

`POST /api/v1/experiments` validates a configuration and creates a run.

`GET /api/v1/experiments/{experiment_id}` reads state and normalized configuration.

`POST /api/v1/experiments/{experiment_id}/run` executes the bounded episode.

`POST /api/v1/experiments/{experiment_id}/pause` requests a safe checkpoint.

`POST /api/v1/experiments/{experiment_id}/resume` resumes from the checkpoint.

`POST /api/v1/experiments/{experiment_id}/replay` verifies and reproduces the stored episode.

`GET /api/v1/experiments/{experiment_id}/trace` returns paginated decisions.

`GET /api/v1/experiments/{experiment_id}/metrics` returns trajectory and summary metrics.

`GET /api/v1/experiments/{experiment_id}/artifacts` lists generated artifacts.

## Memory

`POST /api/v1/memories/write` validates and writes one record to the named local store.

`POST /api/v1/memories/query` executes fixed-budget retrieval.

`GET /api/v1/memories/snapshot` returns an auditable snapshot.

## Canaries

`POST /api/v1/canaries/evaluate` evaluates target rank, margin, and a deterministic warning score under the declared canary configuration. The score is not a calibrated probability.

## Example

```bash
curl -X POST http://127.0.0.1:8000/api/v1/experiments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-001" \
  -d '{"config":{"experiment_id":"demo","capacity":16,"top_k":4,"budget":24,"seed":17}}'
```

Use the OpenAPI document as the source of truth for exact fields.
