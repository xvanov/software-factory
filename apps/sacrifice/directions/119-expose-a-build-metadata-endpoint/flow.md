# Flow — identifying a running instance

## Flow A — an operator asks a deployed instance what it is

1. The operator (or the smoke gate, or a load balancer probe) issues
   `GET /api/meta` against a running instance, with no credentials.
2. The instance responds `200` with a JSON body containing `service` and
   `version`.
3. The operator reads `service` to confirm the right application answered — a
   misrouted DNS record or a wrong tunnel points at a different service, and that
   has happened here before.
4. The operator reads `version` to confirm which build is serving. If it does not
   match the commit they expected to have deployed, the deploy did not take
   effect and they escalate.

## Flow B — the same request before any user exists

1. A freshly booted instance has an empty database and no accounts.
2. `GET /api/meta` still returns `200` with the same body — it reads no user
   state and touches no tables, so it answers correctly on a cold instance.
3. This is what makes it usable as a boot check: it distinguishes "the process is
   up and is the build I expect" from "the process is up" (which `/api/health`
   already covers).
