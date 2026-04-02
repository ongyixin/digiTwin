// Vector indexes (HNSW, cosine, 3072 dims for gemini-embedding-001)
CREATE VECTOR INDEX decision_embedding IF NOT EXISTS
FOR (d:Decision) ON (d.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX assumption_embedding IF NOT EXISTS
FOR (a:Assumption) ON (a.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX evidence_embedding IF NOT EXISTS
FOR (e:Evidence) ON (e.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX document_embedding IF NOT EXISTS
FOR (d:Document) ON (d.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}};

// Fulltext index for keyword search
CREATE FULLTEXT INDEX knowledge_fulltext IF NOT EXISTS
FOR (d:Decision|a:Assumption|e:Evidence|t:Task)
ON EACH [d.title, d.summary, a.text, e.content_summary, t.title];

// Property indexes for frequent filters
CREATE INDEX decision_status IF NOT EXISTS FOR (d:Decision) ON (d.status);
CREATE INDEX task_status IF NOT EXISTS FOR (t:Task) ON (t.status);
CREATE INDEX approval_status IF NOT EXISTS FOR (a:Approval) ON (a.status);
CREATE INDEX person_email IF NOT EXISTS FOR (p:Person) ON (p.email);

// Scope/tenant indexes for permission-scoped retrieval
CREATE INDEX decision_workspace IF NOT EXISTS FOR (d:Decision) ON (d.workspace);
CREATE INDEX decision_tenant IF NOT EXISTS FOR (d:Decision) ON (d.tenant);
CREATE INDEX assumption_tenant IF NOT EXISTS FOR (a:Assumption) ON (a.tenant);
CREATE INDEX evidence_tenant IF NOT EXISTS FOR (e:Evidence) ON (e.tenant);

// Timestamp indexes for Twin Diff queries
CREATE INDEX decision_created_at IF NOT EXISTS FOR (d:Decision) ON (d.created_at);
CREATE INDEX assumption_created_at IF NOT EXISTS FOR (a:Assumption) ON (a.created_at);
CREATE INDEX evidence_created_at IF NOT EXISTS FOR (e:Evidence) ON (e.created_at);
CREATE INDEX task_created_at IF NOT EXISTS FOR (t:Task) ON (t.created_at);
CREATE INDEX approval_created_at IF NOT EXISTS FOR (ap:Approval) ON (ap.created_at);

// Artifact provenance vector index (768-dim, matches Gemini embedding)
CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX symbol_embedding IF NOT EXISTS
FOR (s:Symbol) ON (s.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX policy_embedding IF NOT EXISTS
FOR (p:Policy) ON (p.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX requirement_embedding IF NOT EXISTS
FOR (r:Requirement) ON (r.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 3072, `vector.similarity_function`: 'cosine'}};

// Artifact composite indexes for filtered retrieval
CREATE INDEX artifact_workspace_type IF NOT EXISTS FOR (a:Artifact) ON (a.workspace_id, a.type);
CREATE INDEX artifact_ingested_at IF NOT EXISTS FOR (a:Artifact) ON (a.ingested_at);
CREATE INDEX artifact_sensitivity IF NOT EXISTS FOR (a:Artifact) ON (a.sensitivity);
CREATE INDEX artifact_status IF NOT EXISTS FOR (a:Artifact) ON (a.status);

// ArtifactVersion indexes
CREATE INDEX artifact_version_artifact_id IF NOT EXISTS FOR (av:ArtifactVersion) ON (av.artifact_id);
CREATE INDEX artifact_version_ingested_at IF NOT EXISTS FOR (av:ArtifactVersion) ON (av.ingested_at);

// Chunk indexes
CREATE INDEX chunk_artifact_version IF NOT EXISTS FOR (c:Chunk) ON (c.artifact_version_id);
CREATE INDEX chunk_sequence IF NOT EXISTS FOR (c:Chunk) ON (c.sequence);

// Section indexes
CREATE INDEX section_artifact_version IF NOT EXISTS FOR (s:Section) ON (s.artifact_version_id);

// Fulltext index extended for artifact entity types
CREATE FULLTEXT INDEX artifact_knowledge_fulltext IF NOT EXISTS
FOR (d:Decision|a:Assumption|e:Evidence|t:Task|p:Policy|r:Requirement|pg:ProductGoal)
ON EACH [d.title, d.summary, a.text, e.content_summary, t.title, p.title, r.title, pg.title];

// Repository / GitHub
CREATE INDEX repository_workspace IF NOT EXISTS FOR (r:Repository) ON (r.workspace_id);
CREATE INDEX symbol_file_path IF NOT EXISTS FOR (s:Symbol) ON (s.file_path);
CREATE INDEX symbol_kind IF NOT EXISTS FOR (s:Symbol) ON (s.kind);
