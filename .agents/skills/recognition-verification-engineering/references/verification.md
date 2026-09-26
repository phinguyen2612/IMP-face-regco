# Multi-frame Identity Verification

## Candidate and Observation Contracts

Aggregate enrollment-level hits by person before verification. For each person,
retain the best metric-normalized score, supporting enrollment count, best
enrollment ID/score, deterministic rank, and runner-up margin. Use one documented
aggregation rule; do not let repeated enrollment vectors become independent
votes for the same person.

`RecognitionObservation` contains camera/session/track/frame provenance,
timestamp, quality score, ordered identity candidates, collection ID, embedding
compatibility/model revision, index revision, and configuration/calibration
revision. It contains no images or backend objects. Dedupe frame/sample IDs and
bound the window by `max_frames` and `timeout_ms`.

## Deterministic quality_weighted_vote

Normalize metric output to a higher-is-better similarity before verification.
For each valid observation:

1. A candidate qualifies only when its score satisfies the centralized
   similarity threshold and its canonical margin satisfies
   `min_candidate_margin`.
2. The observation casts at most one identity vote: its highest-ranked
   qualifying identity. Missing/no qualifying candidates cast no identity vote
   but remain valid no-match evidence.
3. Vote weight is `clamp(quality_score, 0, 1)`. Weighted similarity for an
   identity is `sum(weight * score) / sum(weight)` over its qualifying votes.
4. Identity consistency is `qualifying vote count / valid observation count`;
   no-match observations therefore reduce consistency.
5. Deterministic ties use aggregated score, best enrollment score, then stable
   person ID order.

`VERIFIED` requires at least `min_good_frames` valid observations, at least two
independent qualifying observations for one identity, consistency at or above
`identity_consistency`, weighted similarity at or above the similarity
threshold, and every winning vote's margin at or above the configured margin.
One exceptional score cannot bypass these conditions.

## State Semantics

- `PENDING`: the current compatible window has fewer than the required valid
  observations and has not expired.
- `VERIFIED`: all requirements above pass; `person_id` is required.
- `UNKNOWN`: the window has sufficient valid observations and all searches
  succeeded, but no identity reaches the similarity/consistency criteria.
- `UNCERTAIN`: sufficient valid observations conflict or remain margin-ambiguous,
  or a window with some valid evidence reaches count/timeout without a reliable
  conclusion. It is not an exception state.

Technical failures do not enter the observation window. They produce explicit
errors and retry/degraded-health behavior.

Retry moves `UNKNOWN` or `UNCERTAIN` to a fresh `PENDING` window. Verified TTL,
tracking discontinuity, configuration/calibration change, embedding compatibility
change, collection change, or index revision change also starts a fresh window.
Track expiration destroys the state. Never vote across revisions.

## Tests and Metrics

CPU tests cover VectorStore parity, exact Top-K order, metric direction,
threshold equality, compatibility failures, mapping, multi-enrollment
aggregation, empty/no-match search, observation bounds/timeouts, quality
weighting, candidate margins, every allowed state transition, retry/TTL/track
expiry, and model/index/config revision invalidation. Include concurrent search
and atomic revision-swap tests for the adapter.

Metrics include search attempts/latency/failures; observation count; pending,
verified, unknown, and uncertain decisions; verification resets; and active
collection/index revision. Use fixed reason labels only, never person identity.
