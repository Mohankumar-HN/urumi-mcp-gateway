# Urumi MCP Gateway

Urumi is a WooCommerce-backed MCP platform with an authenticated gateway, a
Vue dashboard, and three MCP upstreams: WooCommerce, analytics, and time tools.
The deployment runs locally with Docker Compose or on Kubernetes through the
same Helm chart.

## Final project status and requirement coverage

This project is functionally complete for the mandatory assignment scope and was
validated against the actual runtime behavior. The summary below separates what
was fully demonstrated from what remains limited by the local Docker/Kind
resource environment.

Requirement coverage:

- Fully demonstrated: 11 of 14 mandatory items
- Chart/configuration complete but environment-limited: 3 of 14
- Not implemented as bonus functionality: 0 additional features beyond the
  mandatory scope
- Final completed percentage for mandatory behavior: approximately 79% fully
  demonstrated and 100% implemented/documented within the project scope

| Requirement | Status | Notes |
| --- | --- | --- |
| WooCommerce-backed store | Complete | WordPress + WooCommerce ran successfully in Docker Compose and Kubernetes. |
| Five WooCommerce MCP tools | Complete | Product list/create and order list/get/update tools were validated. |
| Three aggregated upstreams | Complete | Analytics, time, and WooCommerce were registered and routed through the gateway. |
| Authenticated MCP gateway | Complete | API-key authentication, tool routing, and auditing were validated. |
| Admin/member roles | Complete | Admin-only management and member restrictions were tested. |
| API-key creation and revocation | Complete | Member key generation and admin revocation behavior were implemented. |
| Audit logs | Complete | Successful and failed tool calls are stored and viewed by admins. |
| Dashboard chat through gateway | Complete locally | Docker Compose chat was verified with host Ollama. |
| Two-user workflow | Complete | Separate admin/member actions were validated. |
| External MCP client | Complete | An authenticated external client connected to the gateway and invoked tools. |
| Upstream disable/dead-pod isolation | Complete | Disabled or scaled-to-zero upstreams were isolated without breaking healthy upstreams. |
| Local Kubernetes deployment | Complete | Helm chart, Services, Secrets, PVCs, probes, and NetworkPolicy were validated. |
| Production-like k3s deployment | Chart-ready, not live-verified | The same chart supports a production-like configuration, but no separate k3s cluster was used for a live test. |
| Kubernetes Ingress | Manifest-ready, not live-verified | Ingress renders correctly, but was not fully exercised because the local Kind/Docker environment lacked enough memory for an ingress controller. |
| In-cluster Ollama chat | Configured, not verified locally | Helm support exists for an in-cluster Ollama model service, but the local machine could not complete the model pull due to Docker/Kind resource limits. |

Known limitations and constraints:

- The project intentionally keeps Vue instead of migrating to React; the
  current single-file dashboard is working and the migration would be a larger,
  separate rewrite for no functional benefit.
- The assignment's bonus items were intentionally not implemented.
- Kubernetes ingress and in-cluster Ollama chat remain environment-dependent.
- The local machine memory was insufficient to run both the full Kubernetes stack
  and a large Ollama model pull reliably, so those items were documented as
  configuration-ready but not fully proven in this environment.

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

### Place an order locally

After completing the WordPress and WooCommerce setup, open the storefront at
`http://127.0.0.1:8081`, add a product to the cart, complete checkout using
the test payment flow, and confirm the order in WooCommerce admin. The order
tools can then be exercised through the dashboard or an authenticated MCP
client. Kubernetes uses the same workflow after WordPress initialization and
Ingress setup; port-forwarding is the fallback when no Ingress controller is
available.

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

To use the dashboard chat, enter a gateway API key in the dashboard, connect
the gateway, and submit a product, order, analytics, or current-time question
in the chat panel. The backend creates an authenticated MCP session to the
gateway, discovers the available tools, lets Ollama choose and call tools, and
returns the final answer. Tool calls made by chat are recorded in the audit
log under the authenticated user. Docker Compose chat was verified with the
host Ollama service. Kubernetes chat requires the in-cluster Ollama resources
described above or another reachable model endpoint.

Upstream WooCommerce credentials are Kubernetes/Compose secrets consumed only
by the WooCommerce MCP server. They are not returned by the dashboard or
forwarded from external MCP clients.

## System design and tradeoffs

The platform separates the management API, the authenticated MCP gateway, the
dashboard, the WooCommerce MCP server, two additional MCP servers, and the
stateful PostgreSQL, MariaDB, and WordPress components. Docker Compose and
the Helm chart use the same application images and service boundaries so local
validation and production-like deployment follow the same architecture.

The gateway discovers enabled upstreams and prefixes each tool with its
upstream name, for example `analytics__calculate_conversion_rate`. This
avoids collisions between servers that expose the same tool name. Calls are
routed by the prefix, use bounded timeouts, and record success or failure.
Failure isolation is preferred over all-or-nothing discovery: an unavailable
upstream is marked unavailable while healthy upstream tools remain usable.

The tradeoff is operational simplicity over maximum isolation. The gateway
uses one PostgreSQL database and one gateway process, which makes the
assignment deployment easy to operate, but a larger production installation
would normally add replicas, managed databases, centralized logs, external
secret management, and stronger per-tenant quotas. WooCommerce REST API
credentials are kept by the WooCommerce MCP server because it provides a
small, standard integration surface without exposing store credentials to
clients.

For production, replace local images with registry images, use a durable
storage class, configure DNS and TLS for the Ingress hosts, inject secrets
from a secret manager, and run the same Helm chart with production values.

## Threat model

- **Shared upstream credentials:** members can call enabled tools through the
  gateway but cannot read or export the WooCommerce credential. The credential
  is stored in a Kubernetes/Compose secret and used only by the server-side
  WooCommerce MCP process. A compromised upstream or administrator still
  requires separate operational controls and secret rotation.
- **Client-token forwarding:** external API keys authenticate users to the
  gateway and are not forwarded to upstream servers. Upstream authentication
  is selected by the gateway/server configuration, preventing an upstream
  from receiving unrelated client credentials.
- **Untrusted upstreams:** an upstream can return misleading tool
  descriptions or tool output. Administrators must review upstream URLs before
  enabling them. The model is instructed to treat tool output as data, not
  instructions, and upstreams can be disabled or isolated when unhealthy.
- **Member-to-member access:** API keys are hashed, revocable, and associated
  with users. Members can use tools and create their own key, but
  administrator-only upstream, key-listing, revocation, and audit-management
  operations are protected by role checks.
- **Network exposure:** MCP upstream Services are internal `ClusterIP`
  Services and the NetworkPolicy permits their MCP ports only from gateway
  pods. In production, Ingress, TLS, database access, and Kubernetes RBAC
  still require cluster-level hardening.

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
