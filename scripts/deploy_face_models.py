"""Local operator CLI: validate, warm up, register and assign approved face ONNX models.

Uses the same registry service and adapter factory as API/worker; requires local
operator access to .env. Does not create browser sessions or bypass HTTP auth.
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from control_api.model_bootstrap import build_model_registry
from dotenv import load_dotenv
from fr_domain.model_management import DeploymentBackend, ModelManifest
from vision_worker.model_delivery import PendingModelDeployment, ProductionAdapterFactory
from vision_worker.model_runtime import (
    InferenceRuntimeResolver,
    ModelArtifacts,
    RuntimeCapabilities,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("data/models/retinaface-adaface"))
    parser.add_argument("--version", default="mobilenet-adaface-trial-v1")
    args = parser.parse_args()
    load_dotenv(".env")
    registry = build_model_registry()
    prepared = []
    previous = registry.assignments()
    try:
        # Prepare both roles before changing either production assignment.
        for name in ("retinaface-mobilenet025", "adaface-ir18-webface4m"):
            path = args.directory / (name + ".onnx")
            manifest = ModelManifest.model_validate_json(
                (args.directory / (name + ".json")).read_text()
            )
            definition = next((d for d in registry.list_definitions() if d.name == name), None)
            if definition is None:
                definition = registry.create_definition(
                    name, manifest.model_type, "ONNX", "Local CCTV trial"
                )
            version = next(
                (v for v in registry.list_versions(definition.id) if v.version == args.version),
                None,
            )
            if version is None:
                version = registry.create_version(
                    definition.id, args.version, path.name, path.read_bytes(), manifest
                )
            if version.manifest != manifest:
                raise ValueError("EXISTING_VERSION_PROFILE_MISMATCH")
            deployment = registry.create_deployment(version.id, DeploymentBackend.ONNX_CPU, "FP32")
            pending = PendingModelDeployment(
                deployment.id,
                manifest.model_type,
                DeploymentBackend.ONNX_CPU,
                path,
                version.checksum,
                version.version,
                "FP32",
                manifest,
                model_definition_id=definition.id,
                model_version_id=version.id,
            )
            resolved = InferenceRuntimeResolver().resolve(
                DeploymentBackend.ONNX_CPU,
                ModelArtifacts(onnx=True),
                RuntimeCapabilities.cpu_only(),
            )
            candidate = ProductionAdapterFactory().prepare(pending, resolved)
            try:
                candidate.warmup()
                candidate.health_check()
            finally:
                candidate.close()
            prepared.append((deployment, resolved, manifest.model_type))
        receipt = {"previous_assignments": previous, "deployments": []}
        for deployment, resolved, role in prepared:
            registry.request_activation(deployment.id)
            active = registry.record_activation(
                deployment.id,
                success=True,
                resolved_backend=resolved.backend,
                execution_provider=resolved.execution_provider,
            )
            registry.assign(role, active.id)
            receipt["deployments"].append(asdict(active))
            print(role.value, active.id, active.status.value)
        receipt_path = args.directory / "deployment-receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print("Receipt:", receipt_path)
    finally:
        connection = getattr(registry.repository, "_connection", None)
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
