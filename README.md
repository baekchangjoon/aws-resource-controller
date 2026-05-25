# TempSES — AWS SES 기반 일회용 이메일 서비스

[`dev-temp-mail.com`](https://dev-temp-mail.com) 도메인의 [temp-mail.io](https://temp-mail.io) 스타일 서비스 — 학습/포트폴리오용 구현.

🟢 **MVP 운영 중**: <https://app-dev.dev-temp-mail.com>

---

## 📖 문서 시작점 → [`docs/INDEX.md`](docs/INDEX.md)

INDEX 한 곳에 **읽는 순서**, **생성 타임라인**, **frontmatter 메타 정의**가 모여 있습니다.

| 목적 | 어디로 |
|------|--------|
| 처음 읽기 | [`docs/INDEX.md`](docs/INDEX.md) → ANALYSIS → DESIGN → ROADMAP 순 |
| 시간순 변경 이력 | [`CHANGELOG.md`](CHANGELOG.md) |
| Phase별 검증 audit | [`docs/VERIFICATION.md`](docs/VERIFICATION.md) |
| 의사결정 (D1~D18) | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| 가장 최근 세션 스냅샷 | [`docs/sessions/2026-05-25.md`](docs/sessions/2026-05-25.md) |
| 기여 가이드 | [`CONTRIBUTING.md`](CONTRIBUTING.md) |

> 개별 문서 파일명은 의미 기반(`DESIGN.md` 등)으로 안정적이고, 시간 정보는 각 파일 상단 YAML frontmatter와 git log가 정답입니다. 자세한 규칙은 INDEX의 "frontmatter 필드 정의" 참고.

---

## 진행 상태

| 영역 | 상태 |
|------|------|
| 분석 / 설계 / 로드맵 / 결정 / 정리 문서 | ✅ |
| Terraform — bootstrap + ddb/ses/ingest_pipeline/api/frontend/route53_records/github_oidc | ✅ |
| Lambda Ingest (TDD, 7 단위 테스트) | ✅ |
| Lambda API (TDD, 12 단위 테스트, 단일 routeKey 라우터) | ✅ |
| React SPA (Vitest 5 단위 테스트) + S3 + CloudFront | ✅ |
| E2E — 백엔드(SES→Lambda→DDB→API) + Playwright UI | ✅ |
| GitHub Actions CI/CD/E2E (OIDC) | ✅ |

검증 결과는 [`docs/VERIFICATION.md`](docs/VERIFICATION.md), 의도적 보류 사항은 [`docs/sessions/2026-05-25.md §6`](docs/sessions/2026-05-25.md#6-의도적-보류--향후-작업).

---

## 운영 스냅샷

| 항목 | 값 |
|------|----|
| 웹 | <https://app-dev.dev-temp-mail.com> |
| API | <https://q3djghwoh7.execute-api.ap-northeast-2.amazonaws.com> |
| GitHub 리포지토리 | <https://github.com/baekchangjoon/aws-resource-controller> |
| AWS 계정 / 리전 | 322242916220 / ap-northeast-2 (ACM은 us-east-1) |
| 기획서 원본 (로컬) | `~/Downloads/aws_ses.html` |

---

## 기술 스택

- **AWS**: SES, S3, Lambda(Python 3.13), DynamoDB, API Gateway HTTP API v2, CloudFront, Route53, IAM, CloudWatch
- **IaC**: Terraform (AWS Provider v5)
- **Frontend**: Vite + React + TypeScript
- **테스트**: pytest+moto (Lambda 단위), Vitest+Testing Library (웹 단위), Playwright Chromium (UI E2E), boto3+실제 AWS dev stage (백엔드 통합)
- **CI/CD**: GitHub Actions + AWS OIDC (장기 시크릿 0개)

---

## 운영 원칙

1. 모든 변경은 PR — main 직접 push 금지
2. TDD: 실패 테스트 → 구현 → 리팩토링
3. IaC: Terraform이 단일 진실 원천 — 콘솔 변경 금지
4. 진행 내용은 `docs/` 마크다운에 근거(링크) 포함 기록 — 살아있는 문서는 이름 유지, 스냅샷은 `docs/sessions/`로 날짜 분리
5. 의사결정 필요 항목은 [`docs/DECISIONS.md`](docs/DECISIONS.md)에 모아 일괄 처리

---

## 라이선스

[MIT](LICENSE) — [DECISIONS.md D12](docs/DECISIONS.md#d12-라이선스)
