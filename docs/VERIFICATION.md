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

검증 예정.

---

## Phase 1.2 — Lambda API 핸들러 (TDD)

검증 예정.

---

## Phase 2 — 프론트엔드

검증 예정.

---

## Phase 3 — 운영 안전망 / CI/CD

검증 예정.
