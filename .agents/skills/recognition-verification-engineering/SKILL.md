---
name: recognition-verification-engineering
description: Use when designing, implementing, or reviewing vector search, FAISS indexes, embedding compatibility, identity-candidate aggregation, similarity thresholds, recognition observations, or multi-frame identity verification.
---

# Recognition Verification Engineering

Keep recognition as explicit, testable boundaries:

```text
FaceEmbedding -> VectorStore -> SearchResult -> IdentityCandidate
-> RecognitionObservation -> MultiFrameVerifier -> IdentityDecision
```

Business/domain code depends on `VectorStore`, never FAISS. PostgreSQL is the
authoritative enrollment store; every search index is a derived, rebuildable,
immutable runtime revision.

## Ownership

Use `face-pipeline-engineering` for alignment, embedding creation,
normalization ownership, and embedding compatibility metadata. Use the general
vision-pipeline skill when available for realtime scheduling, backpressure,
track lifecycle, and worker resources. This skill begins with a valid
`FaceEmbedding` and owns search semantics, candidate aggregation, temporal
verification, and identity decisions.

## Invariants

- Validate the complete embedding compatibility key before search. An
  incompatibility is `INDEX_INCOMPATIBLE`, never an unknown identity.
- Centralize metric direction, score conversion, threshold comparison, and
  candidate-margin math. Thresholds belong to versioned calibration profiles,
  not to a universal model constant.
- Return project `SearchResult` values. FAISS positions and objects stop at the
  adapter; explicit mapping resolves position to enrollment, identity, and
  person.
- Aggregate multiple enrollment hits into one identity candidate before
  temporal verification.
- A single observation can never produce `VERIFIED`. Keep observations bounded
  by count and time, and require compatible model, collection, and index
  revisions throughout one verification window.
- `UNKNOWN` requires sufficient valid evidence and successful search with no
  qualifying identity. `UNCERTAIN` means valid but conflicting or ambiguous
  evidence. Infrastructure/model/search failures are neither state.
- Build and validate replacement indexes off-path, then atomically activate an
  immutable snapshot. Searches keep using the prior active revision until the
  swap succeeds.
- Cache verified identity on camera/session-scoped track state. Reset on expiry,
  retry, incompatible revision/configuration change, tracking discontinuity, or
  explicit contradictory-evidence policy; do not search every frame.
- Never retain face images in observations or use person identity as a metric
  label.

## Task References

- For `VectorStore`, FAISS, compatibility, metric semantics, mappings, and index
  lifecycle, read [references/vector-index.md](references/vector-index.md).
- For candidate aggregation, observations, state transitions,
  `quality_weighted_vote`, re-verification, metrics, and tests, read
  [references/verification.md](references/verification.md).
- Read both when work spans search and identity verification.

## Review Checklist

- [ ] `VectorStore` abstraction preserved; no FAISS objects leak into domain
- [ ] PostgreSQL remains source of truth; FAISS remains derived
- [ ] compatibility, metric direction, and calibrated threshold are explicit
- [ ] enrollment hits aggregate into identity candidates
- [ ] no single-frame `VERIFIED`; observations are bounded
- [ ] `UNKNOWN` has sufficient valid evidence; `UNCERTAIN` is not an error bucket
- [ ] revision changes reset affected state; transitions are tested
- [ ] failures remain technical failures rather than unknown identity
- [ ] active index replacement is validated and atomic
- [ ] metrics contain no identity labels
