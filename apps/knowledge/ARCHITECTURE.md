# CAIP Knowledge Layer Architecture

This document describes the design decisions, schema structure, indexing strategies, and future evolution of the CAIP Knowledge Layer (`apps.knowledge`).

---

## 1. Design Overview
The Knowledge Layer acts as a unified, graph-oriented Repository Intelligence Database. Instead of maintaining distinct databases/tables for files, folders, symbols, technologies, packages, call paths, services, and cloud resources, CAIP represents all these as:
- **`KnowledgeItem` (Nodes)**: Discovered items or entities.
- **`KnowledgeRelationship` (Edges)**: Directed, typed connections between `KnowledgeItem` nodes.

This design provides extreme schema flexibility and supports a wide variety of discovery workers (e.g., directory scanners, tree-sitter symbol extractors, LSP analyzers, AI agents) writing to the same database.

---

## 2. Model Structure

### KnowledgeItem
- **`id`**: Unique UUID.
- **`project`**: Foreign key to `Project`.
- **`repository`**: Nullable foreign key to `Repository`.
- **`artifact`**: Nullable foreign key to `ProjectArtifact`.
- **`analysis_job`**: Nullable foreign key to `AnalysisJob` representing the scan job that produced this node.
- **`item_type`**: `CharField` (max 100). Kept as an open-ended string in the database (with Python constants in code) to ensure new infra or discovery types can be added without database migrations.
- **`value`**: Text value (e.g. file paths, symbol names, service names).
- **`summary`**: Description or summary.
- **`metadata`**: `JSONField` containing arbitrary unstructured data (e.g., file sizes, code line counts, language types).
- **`confidence_score`**: Float value from 0.0 to 1.0.
- **`discovered_by`**: Source classifier enum (`DiscoverySource`).
- **`created_at`**: Creation timestamp.

### KnowledgeRelationship
- **`id`**: Unique UUID.
- **`source_item`**: Foreign key to the source `KnowledgeItem`.
- **`target_item`**: Foreign key to the target `KnowledgeItem`.
- **`analysis_job`**: Nullable foreign key to `AnalysisJob` that created this relationship.
- **`relationship_type`**: `CharField` (max 100). Kept open-ended to allow dynamic discovery of relations.
- **`confidence`**: Float value from 0.0 to 1.0.
- **`metadata`**: `JSONField` for additional relation properties.
- **`discovered_by`**: Source classifier enum (`DiscoverySource`).
- **`created_at`**: Creation timestamp.

---

## 3. Database Indexing & Optimization

### Applied Indexes (django-level)
To optimize graph traversals and repository scans, the following indexes are applied:
- **`KnowledgeItem`**:
  - `(repository, item_type)`: Speeds up filtering for files, directories, or symbols within a specific repository.
  - `(repository, analysis_job)`: Speeds up querying all nodes produced by a specific repository scan job (extremely common during rescans).
  - `(analysis_job)`: Allows quick retrieval of all nodes generated in a scan.
- **`KnowledgeRelationship`**:
  - `(relationship_type)`: Facilitates relation-specific queries.
  - `(discovered_by)`: Speeds up queries filtered by tool type.
  - `(analysis_job)`: Speeds up querying relationships created by a specific scan.
  - `(source_item, relationship_type)`: Speeds up outgoing traversal queries (e.g., "Find all dependencies of item X").
  - `(target_item, relationship_type)`: Speeds up incoming traversal queries (e.g., "Find all files that import symbol Y").

### Future Database Indexes
As metadata queries grow in complexity (e.g., searching for all python files via `metadata->>'language' = 'python'`), we should configure Postgres GIN (Generalized Inverted Index) indexes:
```sql
CREATE INDEX knowledge_item_metadata_gin_idx ON knowledge_knowledgeitem USING GIN(metadata);
CREATE INDEX knowledge_relationship_metadata_gin_idx ON knowledge_knowledgerelationship USING GIN(metadata);
```
This is not required in Phase 1, but should be added when jsonb querying performance becomes critical.

---

## 4. Lifecycle & Soft Deletion Strategy
When repositories are rescanned, older items may no longer exist. Instead of immediately running hard deletes, which breaks historic analysis jobs and references, CAIP plans to implement a lifecycle/soft-deletion status tracking system in Phase 2/3.

### Recommended Lifecycle States
- **`ACTIVE`**: The item is confirmed to exist in the latest repository scan.
- **`STALE`**: The item was not found in the latest scan but is retained to preserve historic data.
- **`ARCHIVED`**: The item is manually or automatically marked as hidden/archived.

This lifecycle state should be tracked as a field (e.g., `status = models.CharField(max_length=20, default='ACTIVE')`) on `KnowledgeItem` and `KnowledgeRelationship`.
