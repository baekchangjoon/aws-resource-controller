# 의사결정 — TempSES

진행 중 모인 결정 항목을 한 번에 답변받기 위해 모은다. 답이 정해진 항목부터는 본 문서에 결과를 기록한다.

> 진행 원칙: 의사결정이 필요한 곳은 보류, 무관한 부분부터 구현. 사용자가 일괄 응답한 후 결정에 따라 구현 재개.

---

## ✅ 결정 완료

### 초기 결정 (2026-05-25, 사전 합의)

| 코드 | 항목 | 결정 |
|------|------|------|
| D-A | 목표 수준 | 학습/포트폴리오용 |
| D-B | IaC 도구 | Terraform |
| D-C | Frontend 스택 | Vite + React + TypeScript |
| D-D | 보존 리소스 | 계정 / IAM 사용자 `dev-temp-mail-user` / 도메인 `dev-temp-mail.com` / Route53 호스티드존 `Z033790515Q1CCSID8PBQ` |
| D-E | 진행 방식 | 분석/설계 문서 선행 → TDD → E2E → CI |

### 일괄 결정 (2026-05-25, "모두 추천대로")

| 코드 | 항목 | 결정 | 영향/근거 |
|------|------|------|----------|
| **D1** | 웹 도메인 | `app.dev-temp-mail.com` 서브도메인 | ACM 인증서 자동 발급. apex 트래픽과 분리 |
| **D2** | CORS 허용 origin | CloudFront 도메인 + `http://localhost:5173` (dev) | 최소 권한 원칙 |
| **D3** | 외부 이미지 처리 | 모두 제거 (`<img src>` 차단) | 추적 픽셀 방어, 가장 안전 |
| **D4** | SES 이메일 ID `changjoon.baek@gmail.com` | 유지 (Terraform이 import) | 본인 발송 E2E 테스트용 |
| **D5** | Terraform 백엔드 | S3 + DynamoDB lock | 표준 패턴, 학습 가치 |
| **D6** | SES Receipt Rule 활성화 | Terraform이 관리 | 코드/상태 일관성 |
| **D7** | WAF 도입 시점 | Phase 3 보류 | 학습 우선순위 낮음, 비용 절감 |
| **D8** | SES Production 신청 | 보류 | 회신 기능은 MVP 범위 외 |
| **D9** | dev/prod stage 분리 | `envs/dev`, `envs/prod` 두 환경 | E2E를 dev에서 안전 실행 |
| **D10** | GitHub 저장소 공개 | public | 포트폴리오 노출 |
| **D11** | 커밋 컨벤션 | [Conventional Commits](https://www.conventionalcommits.org/) | 자동 changelog 가능 |
| **D12** | 라이선스 | MIT | 가장 단순/관대 |
| **D13** | 로컬 dev stack | moto(단위) + 실제 AWS dev stage(E2E) 하이브리드 | 무료 단위 + 실서비스 검증 |

---

## 결정 결과가 만들어내는 다음 파생 결정

향후 구현 중 새로 생기는 결정 항목은 이 섹션에 추가하고, 답변 후 위로 이동.

### D14. Terraform 부트스트랩 방식
백엔드 S3/DDB는 닭과 달걀 문제. 어떻게 만들지.
- (a) **bootstrap 모듈을 로컬 state로 생성 → 본 모듈은 S3 backend** (추천)
- (b) AWS CLI 스크립트로 백엔드 리소스 수동 생성

→ (a)로 진행 (추천 자체 적용).

### D15. Lambda 의존성 빌드 방식
`nh3`, `python-ulid` 같은 C/Rust 확장.
- (a) **Docker(`public.ecr.aws/lambda/python:3.13`) 기반 빌드** (추천)
- (b) macOS 로컬 빌드 후 zip (manylinux 호환 안 됨)

→ (a)로 진행.

### D16. dev 환경 도메인
- (a) **`app-dev.dev-temp-mail.com`** (추천, 별도 ACM)
- (b) CloudFront 기본 도메인만

→ (a)로 진행.

### D18. API Lambda 구조 — 단일 vs 분할
DESIGN.md §5에 4개 Lambda를 명시했지만 실제 배포 시 운영 부담이 큼.
- (a) **단일 Lambda + routeKey 라우터** (추천) — 콜드스타트 1회, IAM 1세트, 로그그룹 1개
- (b) 엔드포인트별 4개 Lambda — 권한 최소화는 더 엄밀하지만 boilerplate ↑

→ **(a)** 단일 Lambda. 권한 분리는 필요 시 향후 분할. DESIGN.md §5 갱신 예정.

### D17. HTML sanitize 라이브러리
Lambda Ingest의 HTML 정제 라이브러리.
- (a) `nh3` (Rust 기반 ammonia 바인딩) — 빠르고 활발히 유지되지만 Lambda 배포에 Docker 빌드 필요
- (b) **`bleach` (순수 Python)** — 약간 느리고 유지보수 페이스 느림. zip 빌드만으로 충분
- (c) 자체 구현 (html.parser + 화이트리스트)

→ **(b)** 학습 단순화. `pip install -t build/ -r requirements.txt` 한 줄로 패키징 가능. 성능 차이는 메일 수신 트래픽 수준에서 무시 가능. [bleach security advisories](https://github.com/mozilla/bleach/security/advisories) 모니터링 필요.

---

## 미해결

(현재 없음)
