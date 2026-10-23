# Urumi MCP Gateway

Urumi is a WooCommerce-backed MCP platform with an authenticated gateway, a
Vue dashboard, and three MCP upstreams: WooCommerce, analytics, and time tools.
The deployment runs locally with Docker Compose or on Kubernetes through the
same Helm chart.

## Local Docker Compose

1. Copy the required settings into `.env` without committing the file:

   ```text
   DB_NAME=wordpress
   DB_USER=urumi_wp
   DB_PASSWORD=<wordpress-password>
   DB_ROOT_PASSWORD=<wordpress-root-password>
   POSTGRES_DB=urumi_gateway
   POSTGRES_USER=urumi_app
   POSTGRES_PASSWORD=<gateway-database-password>
   WOOCOMMERCE_CONSUMER_KEY=<key-created-in-wordpress>
   WOOCOMMERCE_CONSUMER_SECRET=<secret-created-in-wordpress>
   ```

2. Start the complete local stack:

   ```powershell
   docker compose up --build
   ```

   The dashboard is at `http://127.0.0.1:5173`, WordPress is at
   `http://127.0.0.1:8081`, the management API is at
   `http://127.0.0.1:8000`, and the authenticated MCP gateway is at
   `http://127.0.0.1:8003/mcp`.

3. Complete the WordPress installation, install WooCommerce, and create
   REST API credentials. Put those credentials in `.env` and restart the
   `woocommerce` service.

4. Initialize the gateway schema and create an admin key:

   ```powershell
   docker compose exec backend python scripts/create_admin.py
   ```

   Enter the resulting key in the dashboard. The bootstrap process registers
   the three internal MCP servers in PostgreSQL.

Integration checks are stored under `tests/integration/`. They are manual
scripts and are not run automatically when containers start. For example:

```powershell
docker compose exec woocommerce python tests/integration/test_woocommerce_server.py
```

## Local Kubernetes

The chart is designed for Kind, Minikube, or k3d. The local values use
`*.urumi.test` hosts. Point those names at the cluster ingress address (or add
them to the local hosts file), for example:

```text
127.0.0.1 dashboard.urumi.test api.urumi.test store.urumi.test
```

Build the images and load them into the selected cluster:

```powershell
docker build -t urumi-backend:local .
docker build --build-arg VITE_API_BASE=http://api.urumi.test -t urumi-frontend:local .\frontend
kind load docker-image urumi-backend:local urumi-frontend:local
```

Install an ingress controller appropriate for the cluster, then install the
chart with local-only values. Passwords below are examples for a disposable
cluster; use external secret management for any shared environment.

```powershell
helm upgrade --install urumi .\helm\urumi-platform `
  --namespace urumi --create-namespace `
  -f .\helm\urumi-platform\values-local.yaml `
  --set mariadb.password=<wordpress-password> `
  --set mariadb.rootPassword=<wordpress-root-password> `
  --set postgres.password=<gateway-database-password> `
  --set woocommerce.url=http://urumi-wordpress `
  --set woocommerce.publicUrl=http://store.urumi.test `
  --set woocommerce.consumerKey=<woocommerce-key> `
  --set woocommerce.consumerSecret=<woocommerce-secret>
```

Check workloads and render the chart before applying it:

```powershell
helm lint .\helm\urumi-platform
helm template urumi .\helm\urumi-platform -f .\helm\urumi-platform\values-local.yaml `
  --set mariadb.password=test --set mariadb.rootPassword=test-root `
  --set postgres.password=test-postgres `
  --set woocommerce.url=http://urumi-wordpress `
  --set woocommerce.publicUrl=http://store.urumi.test `
  --set woocommerce.consumerKey=test-key `
  --set woocommerce.consumerSecret=test-secret
kubectl get pods,svc,ingress -n urumi
```

The MCP services are `ClusterIP` only and a NetworkPolicy permits their MCP
ports only from the gateway pods. The dashboard and storefront are exposed through stable Ingress hosts. The
dashboard uses same-host `/api` routing, while the API also has its own
`api.<domain>` host for direct clients.

### Kubernetes verification checklist

Use these checks after the chart is installed:

```powershell
kubectl get pods,svc,pvc,ingress -n urumi
kubectl port-forward -n urumi svc/urumi-backend 18000:8000
kubectl port-forward -n urumi svc/urumi-gateway 18003:8003
curl.exe http://127.0.0.1:18000/health
```

Create one admin and one member API key, then verify `/me`, member key
generation, revocation, and the admin-only `/api-keys` endpoint. Connect an
external MCP client to `http://127.0.0.1:18003/mcp` with the
`X-API-Key` header. The gateway should expose prefixed tools from analytics,
time, and WooCommerce.

To demonstrate failure isolation, disable one upstream through the dashboard
or API and confirm its tools disappear while the other tools remain available.
For a dead-pod test, scale an upstream to zero, list gateway tools, call a
different upstream, and then restore the replica:

```powershell
kubectl scale deployment/urumi-analytics -n urumi --replicas=0
kubectl scale deployment/urumi-analytics -n urumi --replicas=1
```

The chart's WordPress volume starts empty in a new Kubernetes namespace.
Complete the normal WordPress installation and install/activate WooCommerce
before testing storefront checkout and order tools. The Docker Compose
environment remains the ready-to-use local store demonstration.

Kind and k3d do not automatically make a host Ollama process reachable from
pods. The local values file now enables an in-cluster Ollama deployment with
the `llama3.2` model and an 8 GiB persistent volume. The first startup
downloads the model and can take several minutes; increase Docker/Kind memory
if the Ollama pod is evicted. Production-like values enable the same workload
with a 20 GiB volume. To use an external model service instead, set
`ollama.enabled=false` and point `chat.ollamaHost` at a routable URL.

## Production-like k3s

Use the same chart with `values-prod.yaml`, replacing image names, DNS hosts,
storage classes, and secret injection:

```powershell
helm upgrade --install urumi .\helm\urumi-platform `
  --namespace urumi --create-namespace `
  -f .\helm\urumi-platform\values-prod.yaml `
  --set postgres.password=<from-secret-manager> `
  --set mariadb.password=<from-secret-manager> `
  --set mariadb.rootPassword=<from-secret-manager> `
  --set woocommerce.url=http://urumi-wordpress `
  --set woocommerce.publicUrl=https://store.example.com `
  --set woocommerce.consumerKey=<from-secret-manager> `
  --set woocommerce.consumerSecret=<from-secret-manager>
```

For production, use a real image registry, a durable storage class, DNS
records for the three Ingress hosts, and a TLS secret or cert-manager. Helm
keeps upgrades and rollback consistent:

```powershell
helm history urumi -n urumi
helm rollback urumi <revision> -n urumi
```

## MCP and chat usage

An external MCP client uses the gateway URL and an `X-API-Key` header. The
client sees names such as `analytics__calculate_conversion_rate` and
`woocommerce__list_orders`; the gateway routes the suffix to the registered
internal server. The dashboard chat sends the same API key to the backend,
which passes it to the gateway, so calls are audited under the logged-in user.

Upstream WooCommerce credentials are Kubernetes/Compose secrets consumed only
by the WooCommerce MCP server. They are not returned by the dashboard or
forwarded from external MCP clients.

## Design and security notes

The management API and MCP gateway are separate processes using the same
PostgreSQL database. The gateway refreshes enabled upstream registrations on
tool listing and call, applies bounded discovery/call timeouts, and records
success or failure in the audit log. Tool names are prefixed with the upstream
name to avoid collisions.

API keys are stored as SHA-256 hashes and can be revoked. Admin-only endpoints
manage upstreams, keys, and audit logs; members can authenticate and use
enabled tools. The current chart isolates MCP server ingress with a
NetworkPolicy and does not expose those Services through Ingress. An admin
adding an untrusted upstream still grants that server a tool-description and
execution path, so upstream URLs should be restricted and reviewed before
production use.
