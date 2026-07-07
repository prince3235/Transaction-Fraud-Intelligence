# Required Repository Secrets

To ensure the GitHub Actions workflows run successfully, you need to configure the following secrets in your repository settings (**Settings → Secrets and variables → Actions**).

- `ANTHROPIC_API_KEY`: Required for the LLM copilot functionality. This is needed by the integration test workflow (`compose-integration-test.yml`) to verify AI endpoints.
- Any DVC remote credentials (e.g., `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or `GCS` equivalents) if a cloud DVC remote is configured.

*Note: The `GITHUB_TOKEN` is automatically provided by GitHub Actions and does not need to be added manually. It is used in the docker-build-push workflow for pushing packages to the GitHub Container Registry.*
