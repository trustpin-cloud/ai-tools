---
name: trustpin-cicd
description: Set up, review, or troubleshoot CI/CD automation for TrustPin certificate pins with trustpin-cli. Covers scheduled pin refresh, automatic pinning when an AWS ACM certificate renews (EventBridge and Lambda), CodeBuild and CodePipeline jobs, GitHub Actions, GitLab CI, Azure DevOps, Jenkins, CircleCI, release gates, and embedded-configuration regeneration. Use whenever the user wants TrustPin pin rotation, pin refresh, or signing and publishing automated in a pipeline or on AWS, or asks about running trustpin-cli in CI. To add the SDK to an app, use trustpin-integration instead.
license: TrustPin Binary License Agreement. See LICENSE
metadata:
  skill-version: "1.1.0"
  verified-against: "trustpin-cli 6.0.0"
  docs: https://docs.trustpin.cloud/cli/devops-guide
---

# TrustPin CI/CD automation

This skill designs and writes pipeline definitions that keep TrustPin certificate pins current, with `trustpin-cli`. It does not add the SDK to an app (that is the `trustpin-integration` skill).

TrustPin's CLI documentation is the source of truth: the DevOps guide (https://docs.trustpin.cloud/cli/devops-guide), the command reference (https://docs.trustpin.cloud/cli/commands), the installation page (https://docs.trustpin.cloud/cli/installation), and the overview (https://docs.trustpin.cloud/cli/overview). This skill summarizes them and adds guardrails. If the guide or `trustpin-cli --help` differs from this skill, follow the guide and tell the user what differed.

## Before you start

1. Load the `trustpin-integration` skill and read its `references/cli.md`. Its safety rules apply here without exception:
   - Never ask for, read, print, or write an API token, master password, or private key.
   - Never run `trustpin-cli projects sign` without the user's explicit go-ahead in this conversation.
   - Never fix a failure by weakening pinning.
2. Do not create cloud resources, run commands that change an AWS account or any other system, deploy infrastructure, or enable a pipeline. You write the pipeline definition and, when the repository already uses infrastructure as code, the matching definitions. The user creates the secrets, applies the infrastructure, and turns the pipeline on.
3. If the user named a target (for example `aws`, `github`, `gitlab`), use it. Otherwise detect it from the repository (`buildspec.yml`, `template.yaml`, CDK, Terraform, `.github/workflows/`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`, `.circleci/config.yml`) and confirm before writing anything.

## Ask only what you cannot find

- What to automate: a scheduled pin refresh, pinning when an AWS ACM certificate renews, a release gate, embedded-configuration regeneration (only for apps the user states are protected by RASP), or a host inventory check.
- Which TrustPin project for which environment (one project per app and environment is the documented practice) and which hosts.
- The key mode: cloud-managed key with a master password, or bring your own key (BYOK). The ACM renewal flow in the guide assumes BYOK.
- Who approves a production publish, and whether the job should publish at all or stop after staging.

## Design the job

Keep staging separate from signing. The order:

1. Install the CLI pinned to a version, with the digest verified (`references/cli.md`, section 2).
2. Authenticate, then rehearse signing with `--dry-run` early, so bad credentials fail before anything is staged.
3. Stage with `projects refresh-certs` (the guide's recommended method), or `cleanup` plus `upsert` when the host is not observable by TrustPin. Detect whether the configuration version changed and exit quietly when it did not.
4. Sign only when something changed, behind an approval step for production. Signing an unchanged configuration is rejected by the API, so do not sign blindly.
5. Confirm with `projects jws --verify`, and alert on failure.

Treat every non-zero exit code as a failure and stop. Do not tolerate API errors from staging commands: a swallowed error can leave the new pin out of a configuration that then gets published. Decide whether something changed from the version before and after, or from the commands' JSON output, never by matching text.

Also: allow one run at a time, grant the job only the access it needs, and make it runnable by hand for the first test.

Two facts about the CLI that shape the design:

- The API token is user-scoped: it reaches every project that user may access, and it can expire. Suggest creating it from an account that has only the access the pipeline needs (a suggestion; check TrustPin's documentation on token permissions), and plan for rotating it.
- `projects jws` exits 0 with empty output when nothing has been published yet, so a release gate must check for non-empty output as well as `--verify`.

An unattended job that signs publishes to every installed app with no human involved. Say so plainly whenever you propose one, and offer the safer variant: stage in the job, then sign in a separate step that needs approval. Never present unattended signing as the only option.

## Pick the provider reference

- AWS, including ACM renewal, EventBridge, Lambda, CodeBuild, CodePipeline, and S3 with CloudFront for a self-hosted configuration: read `references/aws.md`.
- GitHub Actions, GitLab CI, Azure DevOps, Jenkins, CircleCI, and mobile CI services: read `references/ci-providers.md`.

## Secrets

Do not copy credential-handling commands into pipeline files. Wire each secret through the provider's own secret store, by name, and use the variable names and options in TrustPin's DevOps guide (read it for the current ones). Never write a secret value, never echo one, and never put one in a template parameter, a plain environment setting, or a repository file.

## Finish

1. Validate what you can without side effects: parse the YAML or JSON, and use the provider's linter if it is installed. Do not run the pipeline and do not invoke cloud functions, because the guide's test invocation runs the full flow, including publishing.
2. Report: the files you created or changed, the jobs and their order, the secrets the user must create (by purpose, never by value), where the approval gate is, how to run it by hand for a first test, and what you did not check, including that you did not run the pipeline or touch any cloud account.
3. Do not claim that the pipeline makes the app compliant with any standard, and do not quote uptime figures.
