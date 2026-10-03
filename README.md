# TrustPin AI tools

An Agent Skill that teaches AI coding agents to integrate, review, and automate TrustPin certificate pinning in iOS, macOS, Android, Flutter, and React Native apps.

Once installed, ask your agent to "integrate TrustPin", "review our TrustPin integration", or "set up a pin rotation job".

## Install

**Claude Code (plugin)**

```
/plugin marketplace add trustpin-cloud/ai-tools
/plugin install trustpin@trustpin
```

**Claude (web and desktop)**: download `trustpin-integration.skill` from the latest release and add it under Settings, Capabilities, Skills.

**Cursor, GitHub Copilot, Codex, and other agents that read Agent Skills**: copy the skill folder into your project.

```bash
git clone https://github.com/trustpin-cloud/ai-tools
mkdir -p .agents/skills
cp -r ai-tools/skills/trustpin-integration .agents/skills/
```

`.agents/skills/` is the shared project location these agents read. Agent-specific locations also work: `.claude/skills/`, `.cursor/skills/`, `.github/skills/`. Check your agent's documentation if the skill is not picked up.

**Agents without skills support**: keep the folder in the repository and add this line to `AGENTS.md`: "When working with TrustPin or certificate pinning, read `.agents/skills/trustpin-integration/SKILL.md` first."

## What is inside

| Path | Purpose |
|---|---|
| `skills/trustpin-integration/SKILL.md` | Workflow and the rules that hold on every platform |
| `references/swift.md`, `kotlin.md`, `flutter.md`, `react-native.md` | Per-platform integration |
| `references/project-setup.md` | Dashboard steps the developer does |
| `references/cli.md` | CLI, pin rotation, CI, bring-your-own-key signing |
| `references/review-checklist.md` | Auditing an existing integration |
| `references/troubleshooting.md` | Error codes and fixes |
| `scripts/find_hosts.py` | Lists the hosts a codebase connects to |

## What this plugin runs and connects to

- The skill is instructions and reference text. It adds no MCP server, no hooks, and no background process.
- `skills/trustpin-integration/scripts/find_hosts.py` runs only when the agent or you start it. It reads source and config files in your project and prints the hostnames it finds. It makes no network requests and writes no files.
- The skill may tell the agent to run the TrustPin CLI (`trustpin-cli`) if you have installed it. The CLI talks to the TrustPin API using a token you configure yourself. The skill instructs the agent never to ask for that token, the master password, or a private key, and never to publish a configuration without your explicit go-ahead.

## Verified against

TrustPinKit 6.4.0, kotlin-sdk 6.4.0, trustpin_sdk 6.4.0, @trustpin/react-native 6.4.0. See `CHANGELOG.md` for what "verified" covers.

Documentation: https://docs.trustpin.cloud. Technical support: support@trustpin.cloud. Other inquiries: contact@trustpin.cloud. Issues and corrections are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: see [SECURITY.md](SECURITY.md).

Licensed under the TrustPin Binary License Agreement. See [LICENSE](LICENSE).
