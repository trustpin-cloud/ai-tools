# AWS

Sources: TrustPin's DevOps guide (https://docs.trustpin.cloud/cli/devops-guide, section "AWS ACM: Automated Certificate Pinning on Renewal"), the command reference (https://docs.trustpin.cloud/cli/commands), the installation page (https://docs.trustpin.cloud/cli/installation), the CLI overview (https://docs.trustpin.cloud/cli/overview), AWS's documentation of ACM events (https://docs.aws.amazon.com/acm/latest/userguide/supported-events.html), and lessons from a working production deployment. Nothing here was run by this skill against an AWS account. Confirm AWS service details against the current AWS documentation.

## Contents

1. Choose a pattern
2. ACM renewal, event-driven
3. The simpler refresh-certs variant
4. What the Lambda needs
5. Writing the function
6. ACM rotates the key on every renewal, and every region has its own key
7. Scheduled refresh on AWS
8. Self-hosted configuration on S3 and CloudFront
9. Test safely
10. Infrastructure as code

## 1. Choose a pattern

| The user's situation | Pattern |
|---|---|
| The certificate lives in ACM and renews automatically | Sections 2 and 3: an EventBridge rule on the ACM event runs a Lambda |
| Any certificate, on a timetable | Section 7: a scheduled refresh |
| The domain is served from several regions or through CloudFront | Sections 2 and 7 together (see section 6) |
| The signed configuration is hosted on the user's own CDN | Section 8, on top of any pattern |

In production the best result combines the event (fast reaction to a renewal) with a schedule (a backstop for drift and for anything the event misses).

## 2. ACM renewal, event-driven

When ACM renews a certificate, an EventBridge rule detects it and starts a Lambda that updates the TrustPin pins and publishes.

Use the event as AWS documents it. ACM publishes `ACM Certificate Available` on issuance, renewal, import, and reimport. The certificate ARN is in the top-level `resources` array, and the kind of event is in `detail.Action`. A rule that matches renewals of specific certificates:

```json
{
  "source": ["aws.acm"],
  "detail-type": ["ACM Certificate Available"],
  "resources": ["<certificate ARN>", "<another certificate ARN>"],
  "detail": { "Action": ["RENEWAL"] }
}
```

If TrustPin's DevOps guide shows different names for the detail type or for the fields, follow the AWS documentation above, because the rule matches AWS's events. `ISSUANCE` fires for a new certificate. `IMPORT` and `REIMPORT` apply to certificates the user imported (a reimport can change the key). Ask the user whether to include them.

The function's flow, per the guide:

```
ACM certificate becomes available (renewal)
  -> EventBridge rule
  -> Lambda function:
       1. resolve which monitored certificate fired (resources[0])
       2. either refresh-certs (section 3), or get the certificate from ACM,
          extract the SPKI SHA-256 pin, cleanup, and upsert
       3. sign with the BYOK key
```

Prerequisites from the guide: an ACM certificate with automatic renewal, a TrustPin project that uses BYOK, the BYOK private key and the TrustPin API token both stored in AWS Secrets Manager.

## 3. The simpler refresh-certs variant

If the renewed certificate is served publicly, the guide's simpler alternative replaces the ACM export, the SPKI extraction, the date conversion, and the separate cleanup:

1. `trustpin-cli projects refresh-certs <org> <project> --domain <fqdn> --remove-expired`
2. Sign, only if something changed (see section 5).

The function then needs no `acm:GetCertificate` permission and no cryptography library. EventBridge only tells it when to refresh. It also replaces any custom lookup of Certificate Transparency through a third-party API, which adds a dependency and rate limits. Keep the full extraction flow only when the certificate is served on a private endpoint TrustPin cannot reach, or when it must be pinned before it goes live.

**Timing:** TrustPin's lookup pins the live certificate plus every unexpired issuance found in Certificate Transparency, and it can pin a certificate issued ahead of its deployment, so the renewed certificate can often be pinned as soon as it is issued. `refresh-certs` also fails closed: if the lookup finds nothing, it changes nothing. A scheduled refresh (section 7) is a reasonable backstop if a run at renewal time finds nothing. Let the user decide.

## 4. What the Lambda needs

Least privilege:

- `secretsmanager:GetSecretValue` on exactly two secrets: the API token and the BYOK private key.
- `acm:GetCertificate` and `acm:DescribeCertificate` on exactly the monitored certificates, only for the full extraction flow (not the refresh-certs variant).
- Permission for EventBridge to invoke the function, scoped to each rule (one permission per rule).
- Log permissions, and a log group with a retention period.

Secrets handling:

- The secrets are read inside the function at run time. They never go in the template, in a parameter, in plain environment settings, in the repository, or in logs. Pass only the secret ARNs (or names) to the function.
- Let the infrastructure code create the secret containers without values, and have the user set the values out of band. The state then never holds a secret.
- The BYOK secret must be a PEM private key that contains only the `EC PRIVATE KEY` block. A key generated with `openssl ecparam -genkey` also prints an `EC PARAMETERS` block, which must be removed (a lesson from a working deployment, not in the guide).
- Use the variable names and options TrustPin's guide gives for supplying the token to the CLI.

## 5. Writing the function

From the guide and from a working deployment:

- **Runtime.** The guide uses a custom runtime (`provided.al2023`, handler `bootstrap`) with a shell script. A managed runtime such as Python works well too: `boto3` is already available, and the SPKI pin needs a cryptography library only in the full extraction flow. Choose a runtime that AWS currently supports, and check the support dates in the AWS documentation, because older runtimes get deprecated. With Terraform, the AWS provider version must know the runtime identifier, so a new runtime can require a provider upgrade. Package native wheels for the Lambda platform (for example `pip install --platform manylinux2014_x86_64 --only-binary=:all:`). Use 120 seconds and 256 MB as a starting point, as the guide does.
- **Bundle the CLI** in the deployment package and call it by absolute path. Bundle `trustpin-cli-linux-x64` for x86_64 or `trustpin-cli-linux-arm64` for ARM, pinned to a version with its SHA-256 digest verified (`trustpin-integration`'s `references/cli.md` section 2), not the `latest` download.
- **Writable home.** Lambda's file system is read-only except `/tmp`. Set `HOME` to `/tmp` for the CLI process so it can write its configuration.
- **Clean up.** `/tmp` survives between invocations while the execution environment stays warm. Delete the key file and any CLI configuration file in a `finally` block, so a token or key never lingers.
- **Fail on any non-zero exit.** Do not treat API errors from `upsert` or `cleanup` as success. A swallowed error can publish a configuration that lacks the new pin, and the next certificate switch then breaks pinning in installed apps. Handle the documented no-op signals through the JSON output (`upsert` reports `action` as `added`, `updated`, or `no_change`, and `cleanup` reports `data.removed_pins`), not by tolerating exit codes. Surface the failure so the invocation fails visibly.
- **Sign only when something changed.** Publishing an unchanged configuration is rejected by the API (an HTTP 400 error, exit code 2), a lesson from a working deployment. After an ACM renewal there is always a new pin, but a scheduled run often has nothing to publish. The most robust test is to compare the project's configuration version before and after staging (`projects get --output json`, `data.project.config_version`), per project, and sign only the projects that changed. That counts every kind of change: added pins, updated expiries (`upsert` reports `updated`), and removed pins (`cleanup` reports a non-zero `data.removed_pins`). Parse the JSON. Do not match substrings of the output.
- **Recovery after a failed sign.** If signing fails after staging, the staged changes stay unpublished, and later runs see no new change, so nothing is published again. Give the function a manual way to sign anyway (for example a flag in the test payload that the scheduled trigger never sets), and make the failed invocation visible.
- **Do not feed already-expired certificates to `upsert`.** A third-party certificate source can list expired certificates. `cleanup` removes their pins and the next run adds them again, so the version changes on every run and the job signs every time. Filter them out first, or use `refresh-certs`, which handles it.
- **Several certificates, several projects.** One function can serve several certificates and projects. Keep a non-secret mapping from certificate ARN to domain in the configuration. On an event, look up the domain from `resources[0]`, upsert into every project, then sign each project once after all its upserts. Fail clearly when the ARN is not in the mapping.
- **Network calls need timeouts.** Without one, a hung call runs until the function times out.

## 6. ACM rotates the key on every renewal, and every region has its own key

ACM generates a new key pair at every renewal and does not support key reuse, so the SPKI pin changes every time. To avoid pinning failures in installed apps:

- Keep the old and new pins active together during the overlap.
- The guide recommends 7 to 14 days of overlap for mobile apps. Apps that users open rarely need a longer overlap. For server-to-server use with guaranteed refresh, hours to days can be enough.
- `refresh-certs` maintains the overlap for you: its lookup returns every unexpired issuance TrustPin can see, so the new certificate is pinned alongside the one still being served, and the old pin stays until it expires.
- Never remove an unexpired pin to "clean up". `cleanup` and `--remove-expired` remove only expired pins. `--remove-expired` applies to the single domain named, and `cleanup` sweeps the whole project.

Every ACM certificate has its own key pair, and certificates are regional. A domain served from several regions, or from CloudFront (whose certificate lives in us-east-1) alongside regional load balancers, has several valid certificates with different SPKI pins. Pin all of them, not only the one the event names. A scheduled `refresh-certs` finds them through Certificate Transparency, which is the reason to keep a schedule next to the event.

## 7. Scheduled refresh on AWS

For any certificate, or as the backstop in sections 3 and 6:

- An EventBridge scheduled rule or EventBridge Scheduler invokes the same Lambda, or starts a CodeBuild project that reads a `buildspec.yml` in the repository. A common interval for the backstop is every 12 hours. The user chooses it.
- Or add the job as a CodeBuild action in CodePipeline, with a manual approval action before the signing stage.
- CodeBuild can map secrets from Secrets Manager or Parameter Store into the build environment (see the `env` section of the buildspec reference in the AWS documentation), so nothing is stored in the repository or in `buildspec.yml`. Grant the build role read access to those secrets only.
- A pipeline that runs on another CI service reaches AWS through OpenID Connect and a role with a narrow policy, not long-lived access keys.

The job follows the order in `SKILL.md`: pinned CLI install, dry-run preflight, refresh, change detection, sign behind approval, verify. Give the scheduled rule a name that matches its interval, so it does not mislead whoever reads the console later.

## 8. Self-hosted configuration on S3 and CloudFront

Only when the user hosts the signed configuration themselves (the SDK's configuration URL points to their CDN; that SDK side is out of scope for these skills, see the SDK documentation). The guide's deployment flow after signing:

1. Download the signed configuration: `trustpin-cli projects jws <org> <project> --output-file <path>`.
2. Verify it: `trustpin-cli projects jws <org> <project> --verify`, and abort the deployment if it fails.
3. Upload the file to the bucket, with a cache policy the user chooses.
4. Invalidate the CloudFront path if needed.

Add those steps to the job after signing. The job role then also needs write access to that one bucket path and permission to create the invalidation.

## 9. Test safely

To test the deployed function, invoke it with a payload that mimics the event: `source`, `detail-type`, a `resources` array holding a monitored certificate ARN, and `detail.Action`. Give the CLI call a read timeout longer than the function's timeout. That invocation runs the whole flow, including signing and publishing, so it publishes a configuration. Only suggest it with the user's explicit go-ahead, after `projects sign --dry-run` has passed, and prefer a test project. Never invoke the function yourself.

Test the scheduled path the same way, with a payload that is not an ACM event. A scheduled run that finds no changes must not sign.

## 10. Infrastructure as code

The guide uses AWS SAM. If the repository already uses Terraform, CDK, or CloudFormation, write the equivalent in that tool and keep the same permissions and event pattern. A typical set of resources: the function and its role, the policy with the scoped permissions above, one EventBridge rule with its target and invoke permission for ACM renewals, a second rule with its target and invoke permission for the schedule, the two secret containers, and a log group with retention. Write the files only. The user reviews them and runs the deployment.
