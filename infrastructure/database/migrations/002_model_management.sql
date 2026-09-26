CREATE TABLE IF NOT EXISTS model_definitions (
    id text PRIMARY KEY,
    data jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS model_artifacts (
    id text PRIMARY KEY,
    data jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS model_versions (
    id text PRIMARY KEY,
    model_definition_id text NOT NULL REFERENCES model_definitions(id),
    version_label text NOT NULL,
    data jsonb NOT NULL,
    UNIQUE (model_definition_id, version_label)
);
CREATE TABLE IF NOT EXISTS model_deployments (
    id text PRIMARY KEY,
    model_version_id text NOT NULL REFERENCES model_versions(id),
    data jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS model_deployments_version_idx
    ON model_deployments(model_version_id);

CREATE TABLE IF NOT EXISTS model_assignments (
  model_type text PRIMARY KEY,
  deployment_id text NOT NULL REFERENCES model_deployments(id)
);
