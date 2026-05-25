# Changelog

All notable changes to TempSES are documented here. Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### 2026-05-25 — 비용 폭주 방어 (D19)

[DECISIONS D19](docs/DECISIONS.md#d19-비용-폭주ddos--abuse-방어-깊이)의 채택안 (a) "다층 방어 모두 적용"을 코드로 실현. WAF + API throttle이 막지 못하는 **SES inbound abuse + Lambda concurrency 폭주** 경로에 대한 보호.

1. **Lambda reserved concurrency**
   - `tempses-dev-ingest`: 동시 10
   - `tempses-dev-api`: 동시 20
   - 폭주 시 함수 비용 + 하류 DDB 트래픽 상한 보장.

2. **AWS Cost Anomaly Detection** — `aws_ce_anomaly_monitor` + `aws_ce_anomaly_subscription`
   - DIMENSIONAL on SERVICE, threshold `ANOMALY_TOTAL_IMPACT_ABSOLUTE >= $5`, frequency IMMEDIATE, 이메일 알림.
   - ML 기반 비정상 spike 감지 → fixed-threshold budget이 놓치는 sudden cost spike도 잡음.

3. **SES inbound flood 조기 경보** — [`observability` 모듈](terraform/modules/observability/)의 `ingest_invocations_spike` 알람
   - `AWS/Lambda` `Invocations` (Sum) on ingest 함수, 5분 200건 초과 시 SNS → 이메일.

4. **Budget kill-switch** — Budget 100% 도달 시 SES Rule Set 자동 비활성화
   - 새 SNS topic `tempses-dev-budget-breach` (policy로 `budgets.amazonaws.com` publish 허용).
   - AWS Budgets `tempses-dev-monthly`에 100% ACTUAL 알림 추가, subscriber로 위 topic 포함.
   - Lambda [`lambda/budget_killswitch/`](lambda/budget_killswitch/) — SNS 수신 시 `ses.set_active_receipt_rule_set()` 호출로 active rule set 제거. inbound mail 전체 중단.
   - 복구: `aws ses set-active-receipt-rule-set --rule-set-name tempses-dev-rules`.

5. **OIDC 권한** — github_oidc allow list에 `ce:*` 추가 (Cost Anomaly Detection 관리).
6. **CD 빌드** — `cd.yml`에 killswitch Lambda zip 빌드 step 추가.
7. **문서** — [DECISIONS D19](docs/DECISIONS.md#d19-비용-폭주ddos--abuse-방어-깊이) 신규, [VERIFICATION Phase 3c](docs/VERIFICATION.md#phase-3c--비용-폭주-방어) 신규.

### 2026-05-25 — WAF + API throttling (D7 보류 해제)

[DECISIONS D7](docs/DECISIONS.md#d7-waf-도입-시점)에 보류로 잠겨있던 "WAF + IP rate limit"을 코드로 실현.

- **새 모듈** [`terraform/modules/waf/`](terraform/modules/waf/) — CloudFront-scope (`us-east-1`) WAFv2 web ACL.
  - Priority 1: AWS Managed `CommonRuleSet` (OWASP — SQLi/XSS/path traversal).
  - Priority 2: AWS Managed `KnownBadInputsRuleSet`.
  - Priority 3: IP rate-based block — **2000 req / 5min / source IP** (override 가능, `var.rate_limit`).
  - Default: Allow. 모든 룰 CloudWatch metrics + sample 활성.
- **CloudFront attach** — [`terraform/modules/frontend/`](terraform/modules/frontend/)에 `web_acl_arn` 변수 추가, `aws_cloudfront_distribution.web.web_acl_id`로 연결.
- **API Gateway HTTP API stage throttling** — `aws_apigatewayv2_stage.default.default_route_settings`에 `throttling_rate_limit=50`, `throttling_burst_limit=100`. HTTP API v2가 WAFv2 attach를 지원하지 않으므로 stage 전체 RPS 상한으로 보강.
- **OIDC 권한** — github_oidc의 customer-managed policy allow list에 `wafv2:*` 추가 (CD가 WAF 리소스 관리 가능).
- 문서 갱신: [DECISIONS D7](docs/DECISIONS.md#d7-waf-도입-시점) ✅, [VERIFICATION Phase 3b](docs/VERIFICATION.md#phase-3b--waf--api-throttling) 신규 섹션.

### 2026-05-25 (저녁) — Dependabot 메이저 PR 정리 + OIDC 권한 축소 + SNS 인증 confirm

세션 후반 작업. 추천 후속 큐의 5건을 일괄 정리.

1. **Dependabot 메이저 PR 3건 처리**
   - [#17](https://github.com/baekchangjoon/aws-resource-controller/pull/17) `lambda/api` ruff `~0.9 → ~0.15` — 코드 변경 없이 CI green → squash merge.
   - [#18](https://github.com/baekchangjoon/aws-resource-controller/pull/18) `web` React 18 → **React 19 메이저** — `JSX` namespace가 `React.JSX` 아래로 이동되어 `tsc`가 깨짐. `web/src/App.tsx`에 `import type { JSX } from "react"` 추가로 fix. 로컬 typecheck + vitest 5/5 + `vite build` 모두 PASS 확인 후 머지.
   - [#19](https://github.com/baekchangjoon/aws-resource-controller/pull/19) `lambda/ingest` mypy 1.14 → **2.1 메이저** + pytest/pytest-cov/moto/boto3/ruff bump — 새 mypy가 `bleach` stub을 인식하면서 기존 `# type: ignore[import-untyped]`가 unused-ignore 에러로 잡힘. `lambda/ingest/src/handler.py`에서 주석 제거 fix 후 머지.

2. **OIDC 배포 롤 권한 축소** — [#20](https://github.com/baekchangjoon/aws-resource-controller/pull/20)
   - AWS-managed `AdministratorAccess` attachment 제거.
   - customer-managed `tempses-dev-github-deploy` policy로 교체. allow list: `acm/apigateway/budgets/cloudfront/cloudwatch/dynamodb/iam/lambda/logs/route53/s3/ses/sns/sqs` + `sts:GetCallerIdentity` + `tag:GetResources`.
   - 명시 deny: `account:*`, `organizations:*`, `iam:Create/Delete/UpdateUser`, `iam:Create/DeleteAccessKey`, `iam:*LoginProfile`, `iam:*UserPolicy`.
   - 배포 검증: 머지 직후 CD ([Run 26389961140](https://github.com/baekchangjoon/aws-resource-controller/actions/runs/26389961140)) 성공으로 attachment 교체, 이어 dispatch CD ([Run 26390034718](https://github.com/baekchangjoon/aws-resource-controller/actions/runs/26390034718))가 **새 policy만으로** 다시 성공 → 권한 축소 안전.

3. **SNS 알람 이메일 구독 정상화**
   - 초기 `terraform apply -replace`로 만든 구독이 confirmation 직후 곧장 Unsubscribe로 풀리는 현상 재현 — Gmail 등 메일 클라이언트의 자동 link prefetch가 confirmation 메일의 `UnsubscribeURL`까지 따라가는 [잘 알려진 SNS 함정](https://docs.aws.amazon.com/sns/latest/dg/sns-email-notifications.html).
   - 우회: 새 confirmation 메일의 `SubscribeURL`을 클릭 대신 복사해 받아, `aws sns confirm-subscription --token … --authenticate-on-unsubscribe true` 로 API confirm.
   - 검증: `get-subscription-attributes` 결과 `PendingConfirmation=false`, **`ConfirmationWasAuthenticated=true`**. 이후 unsubscribe도 AWS 자격증명 인증을 요구하므로 prefetch에 더 이상 노출되지 않음. 테스트 publish 메일(MessageId `1f79a33b-be41-54f6-ae0f-c1b5b8e8869f`) 정상 수신 확인.



추천 우선순위([§ 보류 항목 분석](docs/sessions/2026-05-25.md#6-의도적-보류--향후-작업)) 1~5번 일괄 완료.

1. **Dependabot 활성화** — [`.github/dependabot.yml`](.github/dependabot.yml)
   - 매주 월요일 01:00 KST에 github-actions / pip(ingest, api, e2e) / npm(web) / terraform(bootstrap, envs/dev) 갱신 PR
   - 그룹 정책으로 관련 업데이트 묶기 → 첫 실행에서 16개 PR 생성됨

2. **Node 24 마이그레이션** — 4개 워크플로 모두에 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"` 추가
   - 2026-06-02 default 변경 전 안전 전환

3. **CloudWatch Alarms + AWS Budgets** — [`terraform/modules/observability/`](terraform/modules/observability/)
   - Lambda Errors (ingest/api), DLQ depth, API 5xx 4종 알람
   - Budget $10/월, 50%/80%/100% 알림
   - SNS topic `tempses-dev-alerts` → 이메일 구독 (사용자가 confirmation 클릭 필요)

4. **docs lint CI** — [`scripts/lint_docs.py`](scripts/lint_docs.py) + ci.yml `docs` 잡
   - frontmatter 필수 필드 검증 (`title/created/updated/status`)
   - 살아있는 문서는 `phase/reading_order` 추가 필요
   - 상대 링크 dead-link / 리포지토리 escape 검증
   - 첫 실행이 `~/Downloads/aws_ses.html` dead-link를 잡아 ANALYSIS.md 수정

5. **README 영문판** — [`README.en.md`](README.en.md), Korean 본판과 상호 링크

### 2026-05-25 — gitleaks 시크릿 스캔 워크플로 추가

- [`.github/workflows/security.yml`](.github/workflows/security.yml): PR / main push / 주간 cron / 수동 dispatch
  - [`gitleaks/gitleaks-action@v2`](https://github.com/gitleaks/gitleaks-action) (public repo는 라이선스 불필요)
  - 전체 히스토리 스캔 (`fetch-depth: 0`), PR에 leak 발견 시 자동 코멘트
- 로컬 사전 검증: `gitleaks v8.30.1` — 16 commits, **no leaks** ✅
- 첫 실행 (Run #26385235053): success

### 2026-05-25 — E2E 워크플로 + Playwright MCP 라이브 검증

- [`.github/workflows/e2e.yml`](.github/workflows/e2e.yml): workflow_dispatch / PR label `run-e2e` / nightly 16:00 UTC
  - OIDC 인증 → terraform init → Playwright Chromium 설치 → `test_browser_full_journey.py` 실행
  - 실패 시 traces/screenshots 아티팩트 업로드
  - **첫 실행** (Run #26382903554): PASS, 1m5s
- Playwright MCP 인터랙티브 검증 ([docs/PROGRESS.md §5](docs/PROGRESS.md#5-라이브-검증-playwright-mcp-2026-05-25))
  - 라이브 사이트 직접 조작 → SES 발송 → 인박스 도착 → iframe 보안 속성 + sanitize 결과 확인
  - 스크린샷 4장 ([docs/screenshots/](docs/screenshots/))
- [`docs/PROGRESS.md`](docs/PROGRESS.md): 전체 세션 진행 흐름 종합 보고서

### 2026-05-25 — Phase 3a 완료 (Playwright 브라우저 E2E)

- [`tests/e2e/test_browser_full_journey.py`](tests/e2e/test_browser_full_journey.py): 헤드리스 Chromium으로 사용자 전체 시나리오 검증
  - `https://app-dev.dev-temp-mail.com` 접속 → 자동 주소 발급
  - SES 실제 발송 → 5초 폴링이 인박스 업데이트
  - iframe sandbox/referrerpolicy 검증 + 본문 텍스트 확인
- 실행 결과: 10초 이내 PASS

### 2026-05-25 — Phase 3 완료 (GitHub Actions CI/CD + OIDC)

- CI Run #26381616695 SUCCESS, CD Run #26381616696 SUCCESS
- `terraform apply` → Lambda 빌드 → web 빌드 → S3 sync → CloudFront 무효화 자동화 완료

### 2026-05-25 — Phase 3 진행 (GitHub Actions CI/CD + OIDC)

- [`terraform/modules/github_oidc/`](terraform/modules/github_oidc/) — IAM OIDC provider + deploy role
  - Trust policy 제한: `repo:baekchangjoon/aws-resource-controller:ref:refs/heads/main` + `pull_request`
  - 학습용 단일 계정이라 `AdministratorAccess` 부여 (production은 정책 분할 필요)
- Repo variable `AWS_DEPLOY_ROLE_ARN` 설정 완료
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — PR/push 트리거: ingest/api/web/terraform 4개 잡 병렬
- [`.github/workflows/cd.yml`](.github/workflows/cd.yml) — main push 트리거: Lambda 빌드 → terraform apply → web 빌드 → S3 sync → CloudFront invalidation

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
