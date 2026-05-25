# 단계 검증 (Verification Log)

각 Phase 종료 시 **계획·설계·결정**에 부합하는지 점검한 결과를 기록한다. 다음 Phase는 이 점검을 통과한 뒤 시작한다.

---

## Phase 0 — 저장소 + Terraform 인프라 베이스라인

**검증 일시**: 2026-05-25
**검증 대상**: 디렉터리 구조, 문서, GitHub repo, Terraform 부트스트랩 + dev 환경, 21개 AWS 리소스

### ✅ 일치 사항

| 점검 항목 | 기준 | 실제 |
|----------|------|------|
| repo-layout | [ROADMAP §repo-layout](ROADMAP.md#repo-layout) | `terraform/{bootstrap,envs,modules}/`, `lambda/{ingest,api}/`, `web/`, `tests/e2e/`, `.github/workflows/` 모두 존재 |
| `.gitignore`, `.editorconfig` | [ROADMAP Phase 0](ROADMAP.md#phase-0--저장소--terraform-셋업) | 존재, 표준 패턴 |
| Terraform backend (S3+DDB) | [DECISIONS D5](DECISIONS.md#d5-terraform-상태-백엔드) | S3 `tempses-tfstate-322242916220` + DDB `tempses-tflock` |
| 보존 리소스 data 블록 | [ANALYSIS §2 보존](ANALYSIS.md#보존-대상), [TEARDOWN §B](TEARDOWN.md) | `data "aws_route53_zone" "primary"` 사용 |
| terraform fmt -check | [ROADMAP CI 단계](ROADMAP.md#cicd-github-actions) | PASS |
| terraform validate | 동상 | PASS (3개 모듈) |
| DDB addresses 스키마 | [DESIGN §3.1](DESIGN.md#31-tempses_addresses) | PK=`address`(S), TTL=`ttl_at` ENABLED |
| DDB messages 스키마 | [DESIGN §3.2](DESIGN.md#32-tempses_messages) | PK=`address`(S), SK=`message_id`(S), TTL=`ttl_at` ENABLED |
| S3 메일 버킷 암호화/PAB | [DESIGN §4.1](DESIGN.md#41-tempses-mail-account_id-region) | SSE-S3 AES256, 4가지 Public Access Block 모두 true |
| S3 lifecycle | 동상 | `emails/` 1일, `attachments/` 7일 |
| SES 도메인 검증 | [DESIGN §2](DESIGN.md#2-도메인네트워크) | Verification SUCCESS, DKIM SUCCESS, MAIL FROM SUCCESS |
| SES Rule Set 활성화 | [DECISIONS D6](DECISIONS.md#d6-ses-receipt-rule-set-활성화-방식) | `tempses-dev-rules`가 active |
| 웹 서브도메인 | [DECISIONS D1](DECISIONS.md#d1-웹-도메인-매핑) | `app-dev.dev-temp-mail.com` |
| 개인 메일 ID 보존 | [DECISIONS D4](DECISIONS.md#d4-ses-이메일-id-changjoonbaekgmailcom) | `changjoon.baek@gmail.com` Status=SUCCESS (TF 외부) |
| 단일 stage(dev) | [DECISIONS D9](DECISIONS.md#d9-개발-stage-분리) | `envs/dev/` 활성, `envs/prod/`는 디렉터리만 존재 |
| GitHub repo | [DECISIONS D10/D12](DECISIONS.md#d10-github-저장소) | https://github.com/baekchangjoon/aws-resource-controller (public, MIT) |
| 커밋 컨벤션 | [DECISIONS D11](DECISIONS.md#d11-commitpr-컨벤션) | Conventional Commits 적용 (3개 커밋) |

### ⚠️ 불일치 → 조치

| 항목 | 계획 | 실제 | 조치 |
|------|------|------|------|
| S3 메일 버킷 이름 패턴 | DESIGN §4.1 `tempses-mail-{account_id}-{region}` | `tempses-dev-mail-322242916220` (stage prefix 포함, region 미포함) | DESIGN.md를 실제 패턴(`{name_prefix}-mail-{account_id}`)로 수정. 이유: stage 분리(D9)와 정합성. region은 ARN에 이미 포함 |
| HTML sanitize 라이브러리 | DESIGN §7.2 `nh3` (Rust 기반) | Lambda 빌드에 Docker 필요 → 학습 단순화 부족 | [DECISIONS D17](DECISIONS.md#d17-html-sanitize-라이브러리)로 `bleach`(순수 Python) 변경. DESIGN.md §7.2 갱신 |
| tflint 설치/실행 | ROADMAP Phase 0 테스트 항목 | 미설치 | CI 단계(Phase 5)에 GitHub Actions로 위임. 로컬 설치는 선택 |

### 🟡 의도적 보류 (Phase 0에서 다루지 않음 — 차후 단계)

| 항목 | 다룰 단계 |
|------|----------|
| `outputs.tf`의 CloudFront 도메인 / API 엔드포인트 | Phase 1 (api), Phase 2 (frontend) |
| Lambda 함수 정의 | Phase 1.1 (ingest), Phase 1.2 (api) |
| WAF, 알람, Budget | Phase 3 |

### 결론

**Phase 0 통과** ✅ — 차이는 모두 명세 갱신(DESIGN.md, DECISIONS.md)으로 흡수하고 다음 단계 진행.

---

## Phase 1.1 — Lambda Ingest (TDD)

**검증 일시**: 2026-05-25
**대상**: [`lambda/ingest/`](../lambda/ingest/), 배포된 `tempses-dev-ingest` Lambda + S3 트리거

### ✅ 단위 테스트 (TDD)

[ROADMAP §1.1](ROADMAP.md#11-ingest-lambda)에 정의한 8개 시나리오 중 7개를 단위 테스트로 구현 (#8 DLQ는 인프라 구성 단계에서 검증).

| 테스트 | 의도 | 결과 |
|--------|------|------|
| `test_drop_when_spam_verdict_fail` | SES `X-SES-Spam-Verdict: FAIL` 메일은 폐기 | PASS |
| `test_drop_when_virus_verdict_fail` | SES `X-SES-Virus-Verdict: FAIL` 메일은 폐기 | PASS |
| `test_drop_when_address_not_active` | `addresses` 테이블 미등록 수신자는 폐기 (catch-all abuse 방어) | PASS |
| `test_happy_path_text_only` | text/plain 메일은 정상 저장 + TTL 부여 | PASS |
| `test_html_sanitized_removes_script_and_img_src` | `<script>/<style>` 본문과 `<img src>` 모두 제거 ([D3](DECISIONS.md#d3-외부-이미지리소스-정책)) | PASS |
| `test_attachment_uploaded_to_s3` | 첨부파일은 `attachments/<message_id>/...`에 별도 저장 | PASS |
| `test_idempotent_on_duplicate_s3_event` | 같은 S3 객체 이벤트 재처리 시 중복 PutItem 차단 (`attribute_not_exists` 조건) | PASS |

품질 게이트: `ruff format`, `ruff check`, `mypy --strict` 모두 통과.

### ✅ 배포 검증

| 항목 | 기준 | 실제 |
|------|------|------|
| Lambda 함수 | `python3.13`, timeout 60s, memory 256MB ([DESIGN §5](DESIGN.md#5-lambda)) | 일치 |
| 환경변수 | `MAIL_BUCKET`, `ADDRESSES_TABLE`, `MESSAGES_TABLE`, `MESSAGE_TTL_SECONDS` | 일치 |
| S3 트리거 | `s3:ObjectCreated:Put` + prefix `emails/` | 일치 |
| 비동기 OnFailure | SQS DLQ로 라우팅 | `aws_lambda_function_event_invoke_config`로 적용 |
| CloudWatch Logs 보존 | 7일 | `/aws/lambda/tempses-dev-ingest` 7일 |
| IAM 최소 권한 | DDB `addresses`/`messages` 한정, S3 prefix 분리 | 일치 |

### ✅ Smoke 테스트 ([tests/e2e/smoke_ingest.py](../tests/e2e/smoke_ingest.py))

S3에 직접 합성 EML을 업로드 → Lambda 트리거 → DDB 기록 확인. **PASS** (sanitize 결과까지 검증).

### ✅ Real SES E2E ([tests/e2e/e2e_ses_to_inbox.py](../tests/e2e/e2e_ses_to_inbox.py))

`boto3 ses.send_email(FROM=changjoon.baek@gmail.com, TO=e2e-*@dev-temp-mail.com)` → 90초 내 DDB에서 메시지 발견. **PASS**.
- `spam_verdict=PASS`, `virus_verdict=PASS` 정상 채워짐
- DKIM/SPF는 SES 내부 트랜짓이라 verdict 비어있음 (외부 발신자라면 채워짐)

### 결론

**Phase 1.1 통과** ✅ — 메일 수신 파이프라인이 설계대로 동작.

---

## Phase 1.2 — Lambda API 핸들러 (TDD)

**검증 일시**: 2026-05-25
**대상**: [`lambda/api/`](../lambda/api/), [`terraform/modules/api/`](../terraform/modules/api/), HTTP API `q3djghwoh7.execute-api.ap-northeast-2.amazonaws.com`

### ✅ 단위 테스트

[ROADMAP §1.2](ROADMAP.md#12-api-lambda) 시나리오 6개에 라우팅/CORS 보강 → 총 **12개 PASS**.

| 테스트 | 결과 |
|--------|------|
| `test_create_address_returns_201` | PASS |
| `test_create_address_retries_on_random_collision` | PASS |
| `test_create_address_with_hint_collision_returns_409` | PASS |
| `test_delete_address_returns_204` | PASS |
| `test_delete_address_unknown_returns_404` | PASS |
| `test_list_messages_empty` | PASS |
| `test_list_messages_pagination_after_cursor` | PASS |
| `test_list_messages_unknown_address_returns_404` | PASS |
| `test_presign_attachment_returns_signed_url` | PASS |
| `test_presign_unknown_message_returns_404` | PASS |
| `test_unknown_route_returns_404` | PASS |
| `test_cors_origin_header_present` | PASS |

품질 게이트: `ruff format`, `ruff check`, `mypy --strict` 모두 통과.

### ✅ 구조 결정 (D18)

DESIGN.md §5의 4개 Lambda 분할을 **단일 Lambda + routeKey 라우터**로 변경. 이유: 콜드스타트 1회, IAM 1세트, 로그그룹 1개로 운영 단순화. [DECISIONS D18](DECISIONS.md#d18-api-lambda-구조--단일-vs-분할) 기록.

### ✅ 배포 검증

| 항목 | 기준 | 실제 |
|------|------|------|
| Lambda | `python3.13`, timeout 10s, memory 256MB | 일치 |
| API Gateway | HTTP API v2.0 페이로드 | `aws_apigatewayv2_api.api`, `aws_apigatewayv2_integration` payload_format_version=2.0 |
| 4개 라우트 | POST/DELETE/GET 명세대로 | for_each 매핑으로 일치 |
| CORS | `http://localhost:5173` 허용 ([D2](DECISIONS.md#d2-cors-허용-origin)) | `cors_configuration.allow_origins = ["http://localhost:5173"]` |
| IAM 최소 권한 | addresses GetItem/PutItem/DeleteItem, messages GetItem/Query, S3 GetObject on `attachments/*` | 일치 |
| CloudWatch Logs 보존 | 7일 | 일치 |

### ✅ 전체 API + Ingest E2E ([tests/e2e/e2e_api_full_loop.py](../tests/e2e/e2e_api_full_loop.py))

1. `POST /addresses` → `94d31aaf@dev-temp-mail.com` 발급, 201
2. `boto3 ses.send_email` → 발신 성공
3. `GET /addresses/.../messages` (polling 90s) → 1 item with correct `from`/`subject`/`body_text`
4. `DELETE /addresses/...` → 204
5. `GET /addresses/.../messages` after delete → 404

**ALL OK**

### 결론

**Phase 1.2 통과** ✅ — API가 설계대로 동작하며, 사용자 시나리오(주소 발급 → 메일 수신 → 조회 → 삭제) 전체가 정상.

---

## Phase 2 — 프론트엔드

검증 예정.

---

## Phase 3 — 운영 안전망 / CI/CD

검증 예정.
