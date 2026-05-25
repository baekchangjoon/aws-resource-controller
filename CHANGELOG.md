# Changelog

All notable changes to TempSES are documented here. Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### 2026-05-25 — Phase 0 완료, Phase 1 시작

#### 문서화
- [`docs/ANALYSIS.md`](docs/ANALYSIS.md) — 현재 인프라 분석 + HTML 기획서 타당성 평가 + 격차 정리
- [`docs/DESIGN.md`](docs/DESIGN.md) — 시스템 컨텍스트, DB 스키마, API 명세, 보안 모델, 관찰가능성
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — Phase별 작업, TDD 절차, E2E/CI 전략, repo layout
- [`docs/TEARDOWN.md`](docs/TEARDOWN.md) — 보존/삭제/인수 리소스 명세 + 실행 절차
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — 13개 사용자 결정 항목 + 3개 파생 결정
- [`README.md`](README.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`LICENSE`](LICENSE)

#### 리포지토리
- `git init`, 초기 디렉터리 구조 (`terraform/`, `lambda/`, `web/`, `tests/`, `.github/`)
- `.gitignore`, `.editorconfig`, 서브 .gitignore (terraform, lambda, web)
- GitHub repo 생성: https://github.com/baekchangjoon/aws-resource-controller (public, MIT)

#### 기존 AWS 리소스 정리 (Teardown)
- S3 bucket `temp-mail-emails-bucket` 삭제 (객체 6건 포함)
- Lambda `sampleMailReceived` + 서비스 롤 `sampleMailReceived-role-0pct4swr` 삭제
- SES 도메인 ID `dev-temp-mail.com` 삭제 (재생성됨)
- SES Receipt Rule Set `Default` 삭제 (비활성 후)
- 기존 Route53 레코드 7건 삭제 (DKIM CNAME 3, MX, DMARC, admin.* MX/TXT)

#### Terraform 인프라
**부트스트랩** ([`terraform/bootstrap/`](terraform/bootstrap/))
- S3 state bucket `tempses-tfstate-322242916220` (versioning + SSE-S3 + PAB)
- DynamoDB lock table `tempses-tflock`

**dev 환경** ([`terraform/envs/dev/`](terraform/envs/dev/))
- S3 backend로 state 관리
- AWS Provider 2개 (ap-northeast-2 + us-east-1 for CloudFront ACM)
- 기존 Route53 호스티드존 `Z033790515Q1CCSID8PBQ` 데이터 참조

**모듈** ([`terraform/modules/`](terraform/modules/))
| 모듈 | 자원 | 비고 |
|------|------|------|
| `ddb` | `tempses-dev-addresses`, `tempses-dev-messages` (TTL=ttl_at) | PAY_PER_REQUEST |
| `ingest_pipeline` | S3 mail bucket + lifecycle + SES policy + SQS DLQ + Lambda IAM role | emails/ 1d, attachments/ 7d |
| `ses` | 도메인 ID + DKIM + MAIL FROM `bounce.dev-temp-mail.com` + Receipt Rule Set `tempses-dev-rules` (활성) | catch-all → S3 |
| `route53_records` | MX, DKIM ×3, MAIL FROM MX/SPF, DMARC | 기존 호스티드존에 발급 |

**Apply 결과**: 21 resources created, SES verification SUCCESS, DKIM SUCCESS, MAIL FROM SUCCESS.

#### 다음 단계
- Lambda Ingest 코드 TDD ([Phase 1.1](docs/ROADMAP.md#11-ingest-lambda))
- API Gateway + Lambda 핸들러 TDD ([Phase 1.2](docs/ROADMAP.md#12-api-lambda))
- React 프론트엔드 ([Phase 2](docs/ROADMAP.md#phase-2--프론트엔드))
- GitHub Actions CI/CD ([Phase ROADMAP §CI/CD](docs/ROADMAP.md#cicd-github-actions))

## 관련 링크
- [Terraform S3 backend docs](https://developer.hashicorp.com/terraform/language/settings/backends/s3)
- [Receive and process incoming email with Amazon SES (AWS blog)](https://aws.amazon.com/blogs/messaging-and-targeting/receive-and-process-incoming-email-with-amazon-ses/)
- [DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
