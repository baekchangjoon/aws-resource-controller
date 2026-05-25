# TempSES — AWS SES-backed Disposable Email Service

A learning/portfolio implementation of a [temp-mail.io](https://temp-mail.io)-style service running on the [`dev-temp-mail.com`](https://dev-temp-mail.com) domain.

[한국어 README](README.md) · 🟢 **MVP live**: <https://app-dev.dev-temp-mail.com>

---

## 📖 Start at [`docs/INDEX.md`](docs/INDEX.md)

The index page lists every doc with its **reading order**, **creation timeline**, and **frontmatter schema** in one place.

| If you want… | …go to |
|--------------|--------|
| To start reading | [`docs/INDEX.md`](docs/INDEX.md) → ANALYSIS → DESIGN → ROADMAP |
| Change history | [`CHANGELOG.md`](CHANGELOG.md) |
| Per-phase audit | [`docs/VERIFICATION.md`](docs/VERIFICATION.md) |
| Decisions (D1–D18) | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| Latest session snapshot | [`docs/sessions/2026-05-25.md`](docs/sessions/2026-05-25.md) |
| Contribution guide | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

> Filenames stay semantic (`DESIGN.md`, …) so links don't churn. The authoritative time information lives in each file's YAML frontmatter and in `git log`. See INDEX's "frontmatter field definitions" section for the schema.

---

## Status

| Area | State |
|------|-------|
| Analysis / Design / Roadmap / Decisions / Teardown docs | ✅ |
| Terraform — bootstrap + ddb / ses / ingest_pipeline / api / frontend / route53_records / github_oidc / observability | ✅ |
| Lambda Ingest (TDD, 7 unit tests) | ✅ |
| Lambda API (TDD, 12 unit tests, single routeKey router) | ✅ |
| React SPA (Vitest, 5 unit tests) + S3 + CloudFront | ✅ |
| E2E — backend (SES→Lambda→DDB→API) + Playwright UI | ✅ |
| GitHub Actions CI / CD / E2E (OIDC) + gitleaks + Dependabot | ✅ |
| CloudWatch Alarms + AWS Budgets (via SNS) | ✅ |

Phase-by-phase verification: [`docs/VERIFICATION.md`](docs/VERIFICATION.md). Intentionally deferred items: [`docs/sessions/2026-05-25.md §6`](docs/sessions/2026-05-25.md#6-의도적-보류--향후-작업).

---

## Live snapshot

| Item | Value |
|------|-------|
| Web | <https://app-dev.dev-temp-mail.com> |
| API | <https://q3djghwoh7.execute-api.ap-northeast-2.amazonaws.com> |
| Source repository | <https://github.com/baekchangjoon/aws-resource-controller> |
| AWS account / region | 322242916220 / ap-northeast-2 (ACM in us-east-1) |
| Original spec (local file) | `~/Downloads/aws_ses.html` |

---

## Stack

- **AWS**: SES, S3, Lambda (Python 3.13), DynamoDB, API Gateway HTTP API v2, CloudFront, Route53, IAM, CloudWatch, SNS, AWS Budgets
- **IaC**: Terraform (AWS provider v5)
- **Frontend**: Vite + React + TypeScript
- **Testing**: pytest + moto (Lambda unit), Vitest + Testing Library (web unit), Playwright Chromium (UI E2E), boto3 against the real dev stage (backend integration)
- **CI/CD**: GitHub Actions + AWS OIDC (zero long-lived secrets) + gitleaks + Dependabot

---

## Operating principles

1. Every change goes through a PR — no direct pushes to `main`.
2. TDD: failing test first, then implementation, then refactor.
3. Terraform is the single source of truth for AWS resources — no clicks in the console.
4. All progress is recorded under `docs/` with linked evidence. Living docs keep semantic filenames; snapshots live under `docs/sessions/` with a date suffix.
5. Anything that needs a user decision goes into [`docs/DECISIONS.md`](docs/DECISIONS.md) and gets resolved in batches.

---

## License

[MIT](LICENSE) — see [DECISIONS.md D12](docs/DECISIONS.md#d12-라이선스).
