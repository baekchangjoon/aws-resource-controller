# Changelog

All notable changes to TempSES are documented here. Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### 2026-05-25 — Phase 2 완료 (React 프론트엔드 + CloudFront 배포)

- [`web/`](web/) — Vite + React + TypeScript SPA
  - 마운트 시 자동 주소 발급, 5초 polling으로 인박스 갱신
  - 메일 본문은 `sandbox=""` iframe + CSP + `referrerpolicy=no-referrer` 격리 렌더
  - 인박스 페이지네이션 (커서 기반)
  - 5개 Vitest 단위 테스트 모두 PASS
- [`terraform/modules/frontend/`](terraform/modules/frontend/)
  - ACM 인증서 (us-east-1, DNS 검증)
  - Private S3 `tempses-dev-web-322242916220` + CloudFront OAC
  - CloudFront `E36YDK2L5SPTL7` + SPA fallback (403/404 → index.html)
  - Route53 A/ALIAS `app-dev.dev-temp-mail.com`
- API 모듈 CORS에 `https://app-dev.dev-temp-mail.com` 추가
- [`web/deploy.sh`](web/deploy.sh): vite build → S3 sync → CloudFront 무효화
- **검증**: https://app-dev.dev-temp-mail.com → 200

### 2026-05-25 — Phase 1.2 완료 (Lambda API + HTTP API Gateway + E2E)

- [`lambda/api/src/handler.py`](lambda/api/src/handler.py) — Python 3.13 단일 Lambda + routeKey 라우터 ([D18](docs/DECISIONS.md#d18))
  - `POST /addresses` — 충돌 시 자동 재시도(랜덤) 또는 409(hint)
  - `DELETE /addresses/{address}` — 204 or 404
  - `GET /addresses/{address}/messages?after=&limit=` — `attribute_not_exists` 조건과 SK 페이지네이션
  - `GET /messages/{addr}/{id}/attach/{aid}` — presigned URL 5분
  - CORS 헤더 + JSON 응답 + Decimal serializer
- 12개 단위 테스트 ([`tests/test_handler.py`](lambda/api/tests/test_handler.py)) PASS, moto 기반
- 품질 게이트: ruff/mypy 모두 통과
- [`build.sh`](lambda/api/build.sh) — 의존성 없는 단순 zip
- Terraform [`modules/api/`](terraform/modules/api/): IAM 롤 + Lambda + CloudWatch Log Group + HTTP API + 4개 라우트(for_each) + CORS + Lambda permission
- [`tests/e2e/e2e_api_full_loop.py`](tests/e2e/e2e_api_full_loop.py): POST → SES 발송 → polling → DELETE → 404 확인. **ALL OK**

### 2026-05-25 — Phase 1.1 완료 (Lambda Ingest TDD + E2E)

- [`lambda/ingest/src/handler.py`](lambda/ingest/src/handler.py) — Python 3.13 Lambda
  - SES verdict 게이트 (spam/virus FAIL drop)
  - 활성 주소 화이트리스트 (`addresses` GetItem)
  - MIME 파싱 + bleach HTML sanitize (D17)
  - 첨부파일 S3 별도 저장 (`attachments/<message_id>/`)
  - 결정적 `message_id` (S3 LastModified + S3 key SHA-256) → 재처리 idempotent
  - DDB PutItem with `attribute_not_exists` 조건
- 7개 단위 테스트 ([`tests/test_handler.py`](lambda/ingest/tests/test_handler.py)) PASS, moto 기반
- 품질 게이트: ruff format/check, mypy --strict 모두 통과
- [`build.sh`](lambda/ingest/build.sh) — manylinux2014 wheel로 zip 빌드 (Docker 없음)
- Terraform `ingest_pipeline` 모듈 확장: Lambda function + CloudWatch Logs + S3 이벤트 통지 + Lambda permission + 비동기 OnFailure → DLQ
- 스모크 테스트 + 실제 SES E2E 테스트 통과 ([VERIFICATION.md §1.1](docs/VERIFICATION.md))

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
