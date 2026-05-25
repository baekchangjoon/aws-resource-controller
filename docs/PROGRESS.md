# TempSES 진행 보고서 (2026-05-25)

> 한 세션에서 분석 → 설계 → 인프라 → Lambda(TDD) → 프론트 → CI/CD → E2E까지 마친 작업 기록.
> 본 문서는 진행 흐름을 한눈에 보고, 각 단계의 근거(파일/링크/실행 결과)를 추적하기 위한 종합 보고서입니다.
> 단계별 상세 검증 결과는 [`VERIFICATION.md`](VERIFICATION.md), 변경 이력은 [`../CHANGELOG.md`](../CHANGELOG.md).

## 한 줄 요약

`https://app-dev.dev-temp-mail.com/`에서 동작하는 일회용 이메일 서비스(TempSES)를 **Terraform IaC + Python Lambda(TDD) + React SPA + GitHub Actions CI/CD/E2E**로 구축. 26+ AWS 리소스, 24개 단위 테스트, 4개 E2E 시나리오, 6개 GitHub Actions 잡 모두 GREEN.

---

## 1. 진행 흐름 다이어그램

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Day 0  현재 인프라 인벤토리 (콘솔로 만든 잔재물)                            │
│   └─ inventory/INVENTORY.md                                              │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Day 1 · 분석 & 설계 (사용자 결정 13건 일괄 응답: "모두 추천대로")            │
│   ├─ docs/ANALYSIS.md      현재상태 + HTML 기획서 평가 + 격차              │
│   ├─ docs/DESIGN.md        DB 스키마, API, 보안 모델, 비기능 요건           │
│   ├─ docs/ROADMAP.md       Phase, TDD 절차, E2E/CI 전략                   │
│   ├─ docs/TEARDOWN.md      보존/삭제/인수 명세                             │
│   └─ docs/DECISIONS.md     결정 D1~D18                                    │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Phase 0  Terraform 베이스라인                                             │
│   ├─ bootstrap (S3 state + DDB lock)                                     │
│   ├─ envs/dev 21 resources: SES + S3 + DDB + DLQ + IAM + Route53         │
│   └─ 기존 콘솔 리소스 정리(S3/Lambda/SES rule/old DNS records)              │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Phase 1.1  Lambda Ingest (TDD)                                           │
│   ├─ 7 pytest 시나리오 → red → green → refactor                            │
│   ├─ bleach + script/style 사전 정리 → XSS/픽셀 차단                       │
│   ├─ S3 LastModified 기반 결정적 message_id → idempotent                  │
│   └─ Real SES E2E PASS (tests/e2e/e2e_ses_to_inbox.py)                   │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Phase 1.2  Lambda API + HTTP API Gateway (TDD)                           │
│   ├─ 12 pytest 시나리오 (충돌 재시도, 페이지네이션, presigned URL, CORS)     │
│   ├─ 단일 Lambda + routeKey 라우터 (D18)                                   │
│   └─ Full-loop E2E (tests/e2e/e2e_api_full_loop.py): POST→SES→GET→DELETE  │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Phase 2  React SPA (Vite + TS) + CloudFront                              │
│   ├─ 5 vitest 시나리오 (mount/polling/iframe/refresh/copy)                 │
│   ├─ S3+CloudFront+ACM(us-east-1)+OAC+Route53 alias                       │
│   └─ https://app-dev.dev-temp-mail.com → HTTP 200                         │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Phase 3  GitHub Actions CI/CD                                            │
│   ├─ OIDC 롤(tempses-dev-github-deploy) + AdministratorAccess (학습용)    │
│   ├─ ci.yml: ingest/api/web/terraform 4잡 병렬                            │
│   └─ cd.yml: build → terraform apply → S3 sync → CloudFront 무효화        │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Phase 3a  E2E (브라우저 + 백엔드)                                          │
│   ├─ Playwright 브라우저 시나리오 (헤드리스 chromium)                       │
│   ├─ Playwright MCP로 라이브 인터랙티브 검증 ← 본 세션 추가                  │
│   └─ e2e.yml 워크플로 (수동/라벨/nightly cron)                              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 산출물 목록

### 인프라 (Terraform)
| 위치 | 책임 |
|------|------|
| [`terraform/bootstrap/`](../terraform/bootstrap/) | state 백엔드(S3+DDB lock) |
| [`terraform/envs/dev/`](../terraform/envs/dev/) | dev stage 진입점, 백엔드 설정, 7개 모듈 연결 |
| [`terraform/modules/ddb/`](../terraform/modules/ddb/) | addresses + messages 테이블 (TTL) |
| [`terraform/modules/ingest_pipeline/`](../terraform/modules/ingest_pipeline/) | S3 메일 버킷 + lifecycle + DLQ + Lambda + 트리거 |
| [`terraform/modules/ses/`](../terraform/modules/ses/) | 도메인/DKIM/MAIL FROM/Receipt Rule Set |
| [`terraform/modules/route53_records/`](../terraform/modules/route53_records/) | MX/DKIM/SPF/DMARC 발급 |
| [`terraform/modules/api/`](../terraform/modules/api/) | HTTP API + 4개 라우트 + Lambda + CORS |
| [`terraform/modules/frontend/`](../terraform/modules/frontend/) | ACM(us-east-1) + S3 + CloudFront + OAC + Route53 alias |
| [`terraform/modules/github_oidc/`](../terraform/modules/github_oidc/) | GitHub Actions OIDC 신뢰 + 배포 롤 |

### 애플리케이션 코드
| 위치 | 책임 |
|------|------|
| [`lambda/ingest/`](../lambda/ingest/) | SES → S3 → DDB 파이프라인 처리, 7 단위 테스트 |
| [`lambda/api/`](../lambda/api/) | HTTP API 핸들러 (단일 routeKey 라우터), 12 단위 테스트 |
| [`web/`](../web/) | Vite + React + TS SPA, 5 단위 테스트 |

### 테스트
| 위치 | 종류 | 비고 |
|------|------|------|
| `lambda/{ingest,api}/tests/` | pytest (moto) | 단위 |
| `web/tests/` | vitest (jsdom) | 단위 |
| `tests/e2e/smoke_ingest.py` | 직접 S3 업로드 → DDB | 백엔드 스모크 |
| `tests/e2e/e2e_ses_to_inbox.py` | 실제 SES → DDB | 백엔드 통합 |
| `tests/e2e/e2e_api_full_loop.py` | 실제 API+SES 전체 | 통합 |
| `tests/e2e/test_browser_full_journey.py` | Playwright(Chromium) | UI 전체 시나리오 |

### CI/CD
| 위치 | 트리거 | 책임 |
|------|--------|------|
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | PR, main push | lint + 단위 테스트 + terraform validate |
| [`.github/workflows/cd.yml`](../.github/workflows/cd.yml) | main push, manual | Lambda 빌드 + apply + 웹 배포 + CF 무효화 |
| [`.github/workflows/e2e.yml`](../.github/workflows/e2e.yml) | manual, PR label `run-e2e`, nightly | Playwright 브라우저 E2E |

### 문서
| 위치 | 책임 |
|------|------|
| [`README.md`](../README.md) | 진입점, 상태 표, 빠른 링크 |
| [`CHANGELOG.md`](../CHANGELOG.md) | 시간순 변경 이력 |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | Conventional Commits, PR 체크리스트 |
| [`docs/ANALYSIS.md`](ANALYSIS.md) | 현재 상태 + HTML 기획서 평가 + 격차 |
| [`docs/DESIGN.md`](DESIGN.md) | 아키텍처, DB, API, 보안 모델 |
| [`docs/ROADMAP.md`](ROADMAP.md) | Phase별 TDD/CI/E2E 전략 |
| [`docs/DECISIONS.md`](DECISIONS.md) | D1~D18 의사결정 |
| [`docs/TEARDOWN.md`](TEARDOWN.md) | 보존/삭제/인수 |
| [`docs/VERIFICATION.md`](VERIFICATION.md) | Phase별 검증 보고 |
| [`docs/PROGRESS.md`](PROGRESS.md) | (이 문서) 진행 종합 |

---

## 3. 운영 환경 스냅샷

| 항목 | 값 |
|------|----|
| AWS 계정 | 322242916220 |
| 주 리전 | ap-northeast-2 (Seoul) |
| ACM 리전 | us-east-1 (CloudFront 요구사항) |
| 웹 URL | https://app-dev.dev-temp-mail.com |
| API 엔드포인트 | https://q3djghwoh7.execute-api.ap-northeast-2.amazonaws.com |
| CloudFront ID | E36YDK2L5SPTL7 |
| GitHub Repo | https://github.com/baekchangjoon/aws-resource-controller (public, MIT) |
| OIDC 배포 롤 | `arn:aws:iam::322242916220:role/tempses-dev-github-deploy` (repo var `AWS_DEPLOY_ROLE_ARN`) |

---

## 4. CI/CD 실행 이력 (최근)

| Run | 워크플로 | 결과 | 소요 |
|-----|---------|------|------|
| 26381560443 | CI | success | 32s |
| 26381560457 | CD | **failure** (백엔드 profile 문제) | 35s |
| 26381616695 | CI | success | 29s |
| 26381616696 | CD | success (fix 후) | 1m38s |
| 26381733453 | CI | success | 32s |
| 26381733454 | CD | success | 1m40s |
| 26382903554 | **E2E** (workflow_dispatch) | success | 1m5s |

### CD 실패 원인 ([커밋 f9555e6](https://github.com/baekchangjoon/aws-resource-controller/commit/f9555e6))
- `terraform/envs/dev/backend.tf`에 `profile = "default"`가 하드코딩
- GitHub Actions 러너에 그 named profile이 없어 `failed to get shared config profile` 발생
- **해결**: `profile` 라인을 backend.tf + providers.tf에서 모두 제거 → AWS SDK 기본 자격증명 체인이 CI(env var) / 로컬(default profile)에서 자동 동작

### Secrets / Vars 현황
- **Secrets**: 없음 (장기 시크릿 0)
- **Variables**: `AWS_DEPLOY_ROLE_ARN` 1개 (OIDC 배포 롤 ARN)
- 모든 권한은 GitHub OIDC + IAM 신뢰 정책의 `sub` 클레임 제한으로 제어

---

## 5. 라이브 검증 (Playwright MCP, 2026-05-25)

GitHub Actions의 자동 E2E와는 별도로, 본 세션에서 **Playwright MCP**로 라이브 사이트를 직접 인터랙티브하게 검증.

### 단계
1. `browser_navigate` → https://app-dev.dev-temp-mail.com (Title: "TempSES — 일회용 이메일")
2. 자동 발급된 주소 캡처: `77929b72@dev-temp-mail.com` ([screenshot](screenshots/01_initial.png))
3. `aws sesv2 send-email`로 외부에서 메일 발송 (XSS payload 포함):
   ```html
   <p>Sent via <strong>Playwright MCP</strong> interactive run.</p>
   <script>alert("xss")</script>
   <img src="https://tracker.example.com/pixel.png"/>
   ```
4. `browser_wait_for` → 5초 폴링이 인박스 갱신, 1분 내 메일 도착 ([screenshot](screenshots/02_inbox.png))
5. `browser_click` → 메일 선택 → iframe 렌더 ([screenshot](screenshots/03_message_view.png))
6. `browser_evaluate`로 iframe srcdoc 검사:
   - `sandbox=""` ✅
   - `referrerpolicy="no-referrer"` ✅
   - `<script>` 태그 제거됨 ✅
   - `alert("xss")` 텍스트 제거됨 ✅
   - `tracker.example.com` 흔적 제거됨 ✅
   - CSP `default-src 'none'; img-src data:` 메타 존재 ✅
   - 안전 콘텐츠 ("Playwright MCP") 보존 ✅
7. "새 주소 발급" 클릭 → 새 주소 `ae87d3ad@dev-temp-mail.com`, 인박스 클리어 ([screenshot](screenshots/04_new_address.png))

### 결론
**모든 보안/UX 요구사항이 라이브 환경에서 충족.** 서버 sanitize(bleach) + 클라이언트 iframe sandbox + CSP의 다층 방어가 실제 작동.

---

## 6. 의도적 보류 / 향후 작업

| 항목 | 사유 | 다음 단계에서 다룰 만한 시점 |
|------|------|----------------------------|
| WAF + IP rate limit | $5/월 추가, 학습 우선순위 낮음 ([D7](DECISIONS.md#d7-waf-도입-시점)) | 실제 트래픽 노출 시 |
| SES production access | 회신 발송 미사용 ([D8](DECISIONS.md#d8-ses-production-신청)) | 본인 답장 기능 추가할 때 |
| CloudWatch Alarms / Budgets | 학습 단순화 | 운영 시작 시 |
| prod 환경 (envs/prod) | 단일 stage 학습 | 사용자 트래픽 받기 시작할 때 |
| OIDC 롤 권한 축소 | AdministratorAccess는 학습용 ([modules/github_oidc/main.tf](../terraform/modules/github_oidc/main.tf)) | 다중 계정 사용 시 |
| GitHub Actions Node 24 마이그레이션 | 6/2/2026 default 변경 예고 | 그 전에 |

---

## 7. 비용 (2026-05-25 기준 추정)

[ANALYSIS §5](ANALYSIS.md#5-운영-가정과-비용-추정) 산식:
- SES inbound + Lambda + DDB(on-demand) + S3 + CloudFront ≈ **월 $3 미만** (정상 트래픽)
- 추가: ACM 무료, Route53 호스티드존 0.5$/월, S3 state $0.10/월 미만

학습/포트폴리오 용도로는 충분히 저렴.

---

## 8. 다음에 사용자가 할 일

1. 브라우저로 https://app-dev.dev-temp-mail.com 직접 사용해보기
2. (선택) 다른 이메일 클라이언트에서 무작위 주소로 메일 보내보기 — 어차피 catch-all이지만 활성 주소만 통과
3. (선택) GitHub Actions 탭에서 E2E 워크플로 수동 실행해서 자동 검증 확인
4. (선택) 위 §6 "보류" 항목 중 관심 있는 것 진행
