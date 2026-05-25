# TempSES — AWS SES 기반 일회용 이메일 서비스

[`dev-temp-mail.com`](https://dev-temp-mail.com) 도메인에서 동작하는 [temp-mail.io](https://temp-mail.io) 스타일 서비스의 학습/포트폴리오용 구현.

**기획서 원본**: `~/Downloads/aws_ses.html`

## 현재 상태

🟢 **MVP 전체 완료** — https://app-dev.dev-temp-mail.com 에서 동작 가능.

| 단계 | 상태 |
|------|------|
| 인벤토리 수집 | ✅ ([inventory/INVENTORY.md](inventory/INVENTORY.md)) |
| 분석/설계/로드맵/정리/결정 문서 | ✅ ([docs/](docs/)) |
| 저장소 스캐폴딩 + GitHub | ✅ ([repo](https://github.com/baekchangjoon/aws-resource-controller)) |
| 기존 AWS 리소스 정리 | ✅ |
| Terraform: 부트스트랩 (state backend) | ✅ |
| Terraform: ddb 모듈 (TTL) | ✅ |
| Terraform: ingest_pipeline 모듈 (S3 + DLQ + IAM) | ✅ |
| Terraform: ses 모듈 (도메인 + DKIM + MAIL FROM + Rule Set) | ✅ |
| Terraform: route53_records 모듈 | ✅ |
| Terraform: api 모듈 (HTTP API + Lambda) | ✅ |
| Terraform: frontend 모듈 (S3 + CloudFront + ACM) | ✅ |
| Lambda Ingest 코드 (TDD) | ✅ ([VERIFICATION §1.1](docs/VERIFICATION.md#phase-11--lambda-ingest-tdd)) |
| Lambda API 핸들러 코드 (TDD) | ✅ ([VERIFICATION §1.2](docs/VERIFICATION.md#phase-12--lambda-api-핸들러-tdd)) |
| React 프론트엔드 | ✅ ([VERIFICATION §2](docs/VERIFICATION.md#phase-2--프론트엔드)) — https://app-dev.dev-temp-mail.com |
| E2E 테스트 | ✅ ([VERIFICATION §3a](docs/VERIFICATION.md#phase-3a--e2e-브라우저--백엔드)) |
| GitHub Actions CI/CD | ✅ ([VERIFICATION §3](docs/VERIFICATION.md#phase-3--cicd-github-actions)) |

진행 내역은 [`CHANGELOG.md`](CHANGELOG.md) 참고. 전체 진행 흐름 + 라이브 검증 결과는 [`docs/PROGRESS.md`](docs/PROGRESS.md).

## 빠른 링크

- [분석](docs/ANALYSIS.md) — 현재 인프라 + 기획서 타당성 평가
- [설계](docs/DESIGN.md) — 아키텍처, DB 스키마, API, 보안 모델
- [로드맵](docs/ROADMAP.md) — Phase 별 작업, TDD/E2E/CI 전략
- [정리 계획](docs/TEARDOWN.md) — 삭제·보존·인수할 AWS 리소스
- [의사결정](docs/DECISIONS.md) — 진행 중 모인 결정 항목
- [진행 보고서](docs/PROGRESS.md) — 전체 흐름 + 라이브 검증 + 운영 스냅샷
- [단계별 검증](docs/VERIFICATION.md) — Phase별 audit 로그

## 운영 원칙

1. 모든 변경은 PR.
2. TDD: 실패 테스트 → 구현 → 리팩토링.
3. IaC: Terraform이 단일 진실 원천.
4. 모든 진행 내용은 `docs/` 마크다운에 근거(링크) 포함 기록.
5. 의사결정 필요 항목은 [DECISIONS.md](docs/DECISIONS.md)에 모아 일괄 처리.

## 기술 스택

- AWS: SES, S3, Lambda(Python 3.13), DynamoDB, API Gateway HTTP API, CloudFront, Route53, IAM, CloudWatch
- IaC: Terraform (AWS Provider v5)
- Frontend: Vite + React + TypeScript
- 테스트: pytest + moto(단위), Vitest + Testing Library(웹), 실제 AWS dev stage(E2E)
- CI: GitHub Actions (OIDC 기반 IAM 가정)

## 라이선스

미정 — [DECISIONS.md D12](docs/DECISIONS.md#d12-라이선스) 참조.
