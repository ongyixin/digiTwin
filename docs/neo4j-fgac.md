# Neo4j Enterprise Fine-Grained Access Control for digiTwin

## Overview

digiTwin enforces permissions at the application layer via the permission graph (Role, Permission,
Resource, Scope nodes in Neo4j). This document describes how to add Neo4j Enterprise Edition's
fine-grained access control (FGAC) as a second enforcement layer, so the database itself
participates in access control rather than trusting application logic alone.

## Prerequisites

- Neo4j Enterprise Edition (community edition does not support FGAC)
- Update `docker-compose.yml` image to `neo4j:5.18.1-enterprise` (or latest Enterprise)
- Set `NEO4J_ACCEPT_LICENSE_AGREEMENT=yes` in the neo4j service environment

## Built-in Roles to Map

| digiTwin Role       | Neo4j Role       | Permissions                              |
|---------------------|------------------|------------------------------------------|
| admin               | admin            | Full read/write                          |
| analyst             | reader           | Read all labels                          |
| pm                  | reader           | Read all; custom write for AgentAction   |
| agent               | editor           | Read + write AgentAction, Task, Approval |
| compliance_reviewer | reader           | Read Decision, Evidence, Approval        |

## Step 1: Create Custom Roles

```cypher
CREATE ROLE analyst;
GRANT TRAVERSE ON GRAPH * NODES Decision, Assumption, Evidence, Meeting TO analyst;
GRANT TRAVERSE ON GRAPH * RELATIONSHIPS * TO analyst;
GRANT READ {*} ON GRAPH * NODES Decision, Assumption, Evidence TO analyst;

CREATE ROLE pm;
GRANT ROLE analyst TO pm;
GRANT WRITE ON GRAPH * NODES AgentAction TO pm;
GRANT WRITE ON GRAPH * NODES Task TO pm;
```

## Step 2: SSO Configuration (OIDC)

Add to `neo4j.conf` or Neo4j Helm values:

```
dbms.security.authentication_providers=oidc-provider,native
dbms.security.authorization_providers=oidc-provider,native

dbms.security.oidc.provider.display_name=Your IdP
dbms.security.oidc.provider.auth_flow=pkce
dbms.security.oidc.provider.well_known_discovery_uri=https://your-idp.example.com/.well-known/openid-configuration
dbms.security.oidc.provider.audience=digitwin-neo4j
dbms.security.oidc.provider.claims.username=sub
dbms.security.oidc.provider.claims.groups=groups
dbms.security.oidc.provider.authorization.group_to_role_mapping=\
  "admins"=admin;\
  "analysts"=analyst;\
  "pms"=pm
```

## Step 3: Property-Level Access Control (Neo4j 5.9+)

Restrict who can read the `embedding` property (prevents raw vector exfiltration):

```cypher
DENY READ {embedding} ON GRAPH * NODES Decision TO PUBLIC;
GRANT READ {embedding} ON GRAPH * NODES Decision TO embedding_reader;
```

## Step 4: Workspace / Tenant Isolation

Use label-based property filters for tenant isolation (application layer does this by
setting `tenant` on nodes; FGAC can enforce it at the DB level with property predicates
in Enterprise):

```cypher
-- Future: when Neo4j supports property-predicate DENY
DENY TRAVERSE ON GRAPH * NODES Decision WHERE tenant <> $current_tenant TO analyst;
```

Until property-predicate DENY is GA, enforce tenant isolation at the application layer
via the `WHERE node.tenant = $tenant` Cypher clause in `retrieval_service.py`.

## Recommended Architecture

```
User Request
    ↓
FastAPI (resolve JWT, look up user_id)
    ↓
PermissionService.check_permission() — app-level graph traversal
    ↓
Neo4j Driver connection (OIDC JWT forwarded as bearer token)
    ↓
Neo4j FGAC role check — DB-level enforcement
    ↓
Cypher query with WHERE tenant=$t AND workspace=$w — row-level filter
```

This three-layer approach means a compromised application cannot bypass DB-level access
controls, and application bugs cannot expose cross-tenant data.
