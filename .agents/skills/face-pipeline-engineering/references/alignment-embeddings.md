# Alignment, Embeddings, and Compatibility

Read this reference for face alignment, AdaFace/ArcFace, embedding normalization,
or vector-search preparation and review.

## Alignment Boundary

`FaceAligner` consumes a face image/crop, validated named landmarks, and an
alignment compatibility profile. It returns an aligned face plus retained source
provenance. Output size, landmark template, color order, interpolation, and affine
convention belong to the embedding model compatibility profile—not SCRFD.

Test landmark ordering, affine mapping, output dimensions, inverse expectations,
and degenerate/collinear landmarks independently of detector or GPU inference.

## Embedding Contract

Return a framework-independent domain value containing:

```text
vector
dimension
normalized
model_definition_id
model_version
preprocessing_profile
alignment_profile
normalization_profile
distance_metric
source provenance and timestamp
```

Validate expected dimension, finite values, and compatibility metadata. Do not
expose ONNX Runtime/TensorRT tensors or silently coerce malformed vectors.

## Normalization Ownership

Assign L2 normalization to exactly one layer—prefer the embedder adapter when the
model compatibility profile requires it. Record the result as normalized. Reject
zero-norm, NaN, Inf, and wrong-dimensional vectors. A downstream vector store must
validate normalization metadata but must not normalize the vector again.

Test deterministic output and numerical tolerance:

```python
norm = float(np.linalg.norm(vector))
if not np.isfinite(norm) or norm <= epsilon:
    raise InvalidEmbeddingError("embedding cannot be L2-normalized")
normalized = vector / norm
```

## Compatibility Before Search

Equal dimension does not make embedding spaces compatible. A search collection or
index namespace must bind all of:

- exact embedding model definition and version/artifact fingerprint;
- embedding dimension;
- preprocessing and alignment profiles;
- normalization profile;
- distance metric and score interpretation.

Reject add/search operations when any compatibility field differs. Model upgrades
require re-embedding the gallery into a new compatible index and an explicit switch;
never mix old and new model vectors because both are 512-dimensional.

For cosine similarity, use one documented representation—for example normalized
vectors with inner product—and calibrate thresholds per compatibility profile.
AdaFace must not choose identities, and a FAISS adapter must not know SCRFD.

## Tests

CPU-only tests cover affine transformation, landmark degeneracy, expected aligned
size, embedding dimension/finite checks, zero-vector handling, one-time L2
normalization, metadata preservation, compatibility mismatch rejection, distance
metric behavior, and model-version/index isolation.
