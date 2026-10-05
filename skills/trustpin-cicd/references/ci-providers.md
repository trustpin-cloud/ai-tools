# Other CI systems

Source: https://docs.trustpin.cloud/cli/devops-guide. Written from the guide plus common practice for each service. Confirm service details against the provider's current documentation, and follow the guide for how to supply the token and signing credentials.

## The same job everywhere

1. Install the CLI. The guide installs it with Homebrew on the runner, and `trustpin-integration`'s `references/cli.md` section 2 shows a pinned download with a digest check. Prefer a pinned version.
2. Authenticate from the provider's secret store and rehearse signing with `--dry-run`.
3. Record the configuration version, run `projects refresh-certs --domain <fqdn> --remove-expired`, and compare the version. Exit quietly when it is unchanged.
4. Sign only when it changed, behind approval for production.
5. Run `projects jws --verify`.

To refresh every host in a project, read the domains from `projects config` and loop `refresh-certs` over them, then sign once after the last domain, as the guide's all-domains script does.

## Per service

**GitHub Actions**: `schedule` plus `workflow_dispatch`, repository or environment secrets, a `concurrency` group, and a protected `environment` with required reviewers on the signing job. The guide has a scheduled workflow example to follow.

**GitLab CI**: a pipeline schedule, protected and masked CI/CD variables, and a manual job (`when: manual`) in a protected environment for signing.

**Azure DevOps**: a scheduled trigger, a variable group linked to Key Vault, and an environment with approvals before the signing stage.

**Jenkins**: a cron trigger, the Credentials plugin with credential bindings, and an `input` step before signing.

**CircleCI**: a scheduled pipeline, a restricted context for the secrets, and an approval job before signing.

**Mobile CI (Xcode Cloud, Codemagic, Bitrise)**: use these for the release gate only. Confirm that the published configuration is current (`projects get` shows the stored and published versions, and `projects jws --verify` confirms what is live), and for RASP-protected apps regenerate the embedded configuration before each build (`projects jws --output-file`, see `references/cli.md` section 8). Keep signing in a separate, approved job.

## Archiving

For an audit trail, `trustpin-cli projects jws <org> <project> --output-file <path>` saves the published signed configuration, and `--decode` shows what it contains. The guide suggests keeping dated copies.
