# Vector Search and Index Revisions

## VectorStore Boundary

Keep per-query search separate from index construction and activation:

```text
VectorStore.search(query, collection_id, top_k) -> SearchResults
IndexRevisionManager: build -> validate -> load/warm -> activate -> retire
```

`VectorStore` returns framework-independent results containing enrollment ID,
score, rank, collection ID, index revision, and compatibility key. It exposes no
FAISS row IDs, index objects, or buffers. A mock/in-memory implementation must
obey the same ordering, compatibility, and failure contract as FAISS.

## Source of Truth and Mapping

PostgreSQL owns persons, identities, enrollments, embedding metadata, and active
revision metadata. The index artifact and its mapping are derived from one
transactionally consistent enrollment snapshot:

```text
FAISS position -> stable enrollment ID -> face identity -> person
```

Persist the index, mapping, compatibility key, vector count, checksum, build
timestamp, and source snapshot/revision together. Validate their cardinality and
checksums before activation. Never infer person identity from a row position.

## Compatibility and Metrics

Require equality of model definition/version or artifact fingerprint,
dimension, normalization, alignment profile, preprocessing profile, distance
metric, and score interpretation. Reject invalid/non-finite query embeddings and
all mismatches before invoking the backend.

One metric policy owns:

- whether higher or lower scores are better;
- deterministic Top-K ordering and tie-breaking;
- threshold qualification, including equality at the boundary;
- best-versus-runner-up margin in a canonical higher-is-better form.

For normalized embeddings with cosine semantics, MVP FAISS may use exact
`IndexFlatIP`; inner product is then the documented cosine score. Do not use that
equivalence for unnormalized vectors. Thresholds bind to the entire compatibility
and calibration profile.

## Immutable Revision Lifecycle

```text
enrollment mutation -> PostgreSQL commit -> BUILDING revision
-> read authoritative snapshot -> compatibility check -> build index + mapping
-> validate/checksum -> READY -> load/warm -> atomic ACTIVE swap
-> reset affected verification windows -> RETIRED old revision
```

`FAILED` revisions never activate. Build outside the search lock. Publish one
immutable `(index, mapping, metadata)` snapshot under a short writer lock or
atomic reference swap. Each query captures one snapshot for its entire call.
Close a retired snapshot only after in-flight readers release it. Continue using
the previous active revision if build, validation, warmup, persistence, or swap
fails.

Distinguish `SEARCH_NO_MATCH`, `SEARCH_FAILURE`, `INDEX_NOT_READY`,
`INDEX_INCOMPATIBLE`, and `INVALID_QUERY_EMBEDDING`. Only no qualifying result
from an otherwise successful compatible search can contribute to an unknown
identity decision.
