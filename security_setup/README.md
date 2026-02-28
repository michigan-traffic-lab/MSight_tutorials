# MSight Recommended Security Setup

## Introduction 🔎

This document describes the recommended security architecture and configuration options for deploying **MSight** in development and production environments. It provides practical guidance for securing communication, authentication, authorization, and service exposure when using the MSight ecosystem with infrastructure components.

In this example, we focus on a single node—the local image node—and demonstrate its interaction with the Pub/Sub services.

## Basic Setup 🐳

In this example, we configure a single node—the local image node—to interact with the backend services. The complete setup includes a YAML file that defines the service topology and container configuration:

```
version: "3.9"

services:
  redis:
    image: redis
    container_name: redis
    ports:
      - "127.0.0.1:6380:6380"
    volumes:
      - ./users.acl:/usr/local/etc/redis/users.acl:ro
      - ./redis.conf:/usr/local/etc/redis/redis.conf:ro
      - ./certs:/usr/local/etc/redis/certs:ro
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    restart: unless-stopped

  nats-server:
    image: nats:latest
    # container_name: nats-server
    ports:
      - "127.0.0.1:4222:4222"
      - "127.0.0.1:8222:8222"
    command: >
      -p 4222
      -m 8222
      -c /etc/nats/nats-sip.conf
    restart: always
    volumes:
      - ./nats-server.conf:/etc/nats/nats-sip.conf
      - ./certs:/etc/nats/certs:ro


  msight_image_node:
    image: michigantrafficlab/msight-core:latest
    network_mode: host
    restart: unless-stopped
    depends_on:
      - redis
    command: ["msight_launch_local_image", "-n", "test_local", "-pt", "local", "--sensor-name", "local_image", "-p", "/msight/images/myphoto.jpg"]
    volumes:
      - ./certs:/usr/local/etc/redis/certs:ro
      - ./images:/msight/images:ro
    env_file:
      - .env
```

From this Docker Compose configuration, we can observe that the topology consists of a single application node (`msight_image_node`) supported by two infrastructure services: Redis for state storage and lightweight coordination, and NATS for message-based Pub/Sub communication. Although this represents the simplest possible MSight deployment topology, the focus of this guide is on properly configuring the Pub/Sub layer and the node’s messaging components to ensure secure information exchange.

To run this example, pull the full folder, rename the `.env-example` file to `.env` and then do 

```
docker compose up
```

 

## Redis Access Control List (ACL) Configuration 🔐

The Redis Access Control is defined in the `users.acl` file, which explicitly specifies authentication and authorization boundaries for each user:

```
user default off
user msight on >RatOxTigerRabbitDragonSnakeHorseSheep +@read +@write +@pubsub +@connection -@dangerous -@admin -@scripting ~* &*
```

This configuration performs the following security actions:

* `user default off` disables the anonymous default user, ensuring that all clients must authenticate.
* `user msight on >...` creates and enables the `msight` user with the specified password.
* `+@read +@write +@pubsub +@connection` grants only the command categories required for normal application operation (data access, pub/sub messaging, and connection management).
* `-@dangerous -@admin -@scripting` explicitly removes high-risk command categories, preventing execution of operations such as `FLUSHALL`, `CONFIG`, `SHUTDOWN`, `DEBUG`, `MODULE`, and `EVAL`.
* `~*` defines the allowed key pattern (all keys in this example; this can be restricted in stricter deployments).
* `&*` defines the allowed Pub/Sub channel pattern (all channels; similarly restrictable to a namespace such as `msight.*`).

Together, these rules enforce the principle of least privilege while still allowing the node to perform required read/write and Pub/Sub operations. In production deployments, it is recommended to further narrow the key (`~pattern`) and channel (`&pattern`) scopes to a dedicated namespace (e.g., `~msight:*` and `&msight.*`) to prevent cross-application interference.

For the MSight node, we need to setup username and password to access the service, this is done by setting up the environment variables, you can see in the .env file these two line:

```
MSIGHT_REDIS_MESSAGE_BROKER_USERNAME=msight
MSIGHT_REDIS_MESSAGE_BROKER_PASSWORD=RatOxTigerRabbitDragonSnakeHorseSheep
```

Which inform the MSight node to use the username msight and password to access Redis server.

## TLS on Redis 🔒

To ensure encrypted communication between MSight nodes and Redis, TLS must be enabled on the Redis server. This requires generating a Certificate Authority (CA) certificate and a server certificate signed by that CA.

The following example generates a local CA and a Redis server certificate suitable for localhost deployments:

```
mkdir -p certs
cd certs

# Generate CA private key
openssl genrsa -out ca.key 4096

# Generate self-signed CA certificate
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -subj "/CN=Redis-Local-CA" \
  -out ca.crt

# Generate server private key
openssl genrsa -out server.key 4096

# Create server CSR configuration with SAN entries
cat > server.cnf <<'EOF'
[ req ]
default_bits       = 4096
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = req_ext

[ dn ]
CN = redis

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = localhost
IP.1  = 127.0.0.1
EOF

# Generate certificate signing request
openssl req -new -key server.key -out server.csr -config server.cnf

# Sign server certificate with CA
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 3650 -sha256 -extensions req_ext -extfile server.cnf

# Restrict private key permissions (recommended)
chmod 600 server.key ca.key
```

After this step, the `certs` directory contains:

* `ca.crt` – Certificate Authority certificate (used by clients to verify the server)
* `ca.key` – CA private key (must be kept secure and never distributed)
* `server.crt` – Redis server certificate
* `server.key` – Redis server private key (must remain confidential)

Redis must then be configured with TLS enabled (e.g., using `tls-port` and disabling the plaintext `port`).

On the MSight client side, enable TLS and provide the CA certificate so the client can verify the Redis server identity:

```
MSIGHT_REDIS_MESSAGE_BROKER_USE_TLS=true
MSIGHT_REDIS_MESSAGE_BROKER_TLS_CA_CERT_FILE=/usr/local/etc/redis/certs/ca.crt
```

These settings instruct the MSight node to establish an encrypted TLS connection and verify the Redis server certificate using the specified CA certificate. In production deployments, the CA certificate should be securely distributed, and private keys must never be exposed or committed to version control.

## Make Redis Accessible Only to a Specific Interface 🌐

In Docker, Redis exposure can be further restricted by binding the published container port to a specific host interface in `docker-compose.yaml`. For example:

```
ports:
  - "127.0.0.1:6380:6380"
```

This configuration binds Redis to the loopback interface (`127.0.0.1`) only. As a result:

* Redis is not exposed on `0.0.0.0` and cannot be accessed from external machines.
* Only local processes on the host can connect to the published port.
* The attack surface is significantly reduced compared to publishing on all interfaces.

For even stricter isolation in multi-container deployments, Redis can be placed on a dedicated internal Docker network and **not published to the host at all**, allowing only explicitly attached services to communicate with it. Combining interface binding, TLS, and ACL restrictions provides layered defense for MSight deployments.

## Configuring NATS 📡

NATS should be configured with the same security principles applied to Redis: authentication, authorization, encrypted transport, and limited network exposure.

Below is an example `nats-server.conf` configuration enabling username/password authentication and server-side TLS (without requiring client certificates):

```
authorization {
  users = [
    {
      user: "msight"
      password: "RatOxTigerRabbitDragonSnakeHorseSheep"
      permissions: {
        publish:   [">"]
        subscribe: [">"]
      }
    }
  ]
}

# TLS enabled (server presents certificate; clients verify it)
tls {
  cert_file: "/etc/nats/certs/server.crt"
  key_file:  "/etc/nats/certs/server.key"
  ca_file:   "/etc/nats/certs/ca.crt"

  # IMPORTANT: Do NOT enable the following unless mutual TLS (mTLS) is required
  # verify: true
  # verify_and_map: true
}
```

### 🔐 Authorization

The `authorization` block defines authenticated users and their subject-level permissions:

* `user` / `password` – credentials required by clients.
* `publish` – subjects the user is allowed to publish to.
* `subscribe` – subjects the user is allowed to subscribe to.

In this example, `">"` grants access to all subjects. For production deployments, it is strongly recommended to restrict permissions to a dedicated namespace such as `"msight.>"` to enforce subject isolation.

### 🔒 TLS Encryption

The `tls` block enables encrypted communication:

* The server presents `server.crt` signed by the trusted CA.
* Clients verify the server identity using `ca.crt`.
* Client certificates are not required because `verify` and `verify_and_map` are not enabled.

This provides transport encryption and server authentication while keeping operational complexity minimal.

### 🌐 MSight Client Environment Configuration

To enable secure communication from the MSight node, configure the following environment variables:

```
MSIGHT_NATS_USERNAME=msight
MSIGHT_NATS_PASSWORD=RatOxTigerRabbitDragonSnakeHorseSheep
MSIGHT_NATS_USE_TLS=true
MSIGHT_NATS_TLS_CA_CERT_FILE=/usr/local/etc/redis/certs/ca.crt
```

These variables instruct the MSight node to authenticate using the configured credentials and establish a TLS-encrypted connection to the NATS server.

### 🛡 Restricting Network Exposure

As with Redis, NATS should be bound only to a specific interface to reduce exposure. In `docker-compose.yaml`:

```
ports:
  - "127.0.0.1:4222:4222"
  - "127.0.0.1:8222:8222"
```

This ensures:

* NATS is not publicly exposed.
* Only local processes can access the messaging layer.
* The monitoring port (8222) is also restricted.

---

## Conclusion ✅

This document outlines a secure-by-default configuration for MSight deployments, covering Redis and NATS hardening through:

* 🔐 TLS-encrypted communication
* 👤 Explicit authentication using usernames and passwords
* 🎯 Fine-grained authorization (ACLs and subject permissions)
* 🌐 Interface-restricted network exposure
* 🛡 Principle of least privilege enforcement

Even in a minimal single-node topology, these protections establish a strong security foundation. As MSight deployments scale to distributed, multi-node environments, the same layered approach—encryption, authentication, authorization, and isolation—should be consistently applied to maintain system integrity and prevent unauthorized access.

Security should not be treated as an afterthought but as an architectural property embedded into every layer of the MSight infrastructure.
