# Evidence storage boundary

The MVP uses a local-filesystem implementation of `BlobStorage`. Runtime configuration
must choose its root directory. No production path or credential is committed. S3/MinIO
implementations must preserve the same put/get/delete contract.
