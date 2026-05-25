# TempSES — AWS SES 기반 일회용 이메일 서비스

[`dev-temp-mail.com`](https://dev-temp-mail.com) 도메인에서 동작하는 [temp-mail.io](https://temp-mail.io) 스타일 서비스의 학습/포트폴리오용 구현.

**기획서 원본**: `~/Downloads/aws_ses.html`

## 현재 상태

🚧 **분석/설계 단계 완료, 구현 시작 전.**

| 단계 | 상태 |
|------|------|
| 인벤토리 수집 | ✅ ([inventory/INVENTORY.md](inventory/INVENTORY.md)) |
| 분석 문서 | ✅ ([docs/ANALYSIS.md](docs/ANALYSIS.md)) |
| 설계 문서 | ✅ ([docs/DESIGN.md](docs/DESIGN.md)) |
| 로드맵 | ✅ ([docs/ROADMAP.md](docs/ROADMAP.md)) |
| 정리 계획 | ✅ ([docs/TEARDOWN.md](docs/TEARDOWN.md)) |
| 의사결정 정리 | ✅ ([docs/DECISIONS.md](docs/DECISIONS.md)) — 13개 항목 대기 |
| 저장소 스캐폴딩 | ⏳ |
| Terraform 스켈레톤 | ⏳ |
| Lambda (TDD) | ⏳ |
| Frontend | ⏳ |
| E2E 테스트 | ⏳ |
| CI/CD | ⏳ |

## 빠른 링크

- [분석](docs/ANALYSIS.md) — 현재 인프라 + 기획서 타당성 평가
- [설계](docs/DESIGN.md) — 아키텍처, DB 스키마, API, 보안 모델
- [로드맵](docs/ROADMAP.md) — Phase 별 작업, TDD/E2E/CI 전략
- [정리 계획](docs/TEARDOWN.md) — 삭제·보존·인수할 AWS 리소스
- [의사결정](docs/DECISIONS.md) — 진행 중 모인 결정 항목

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
