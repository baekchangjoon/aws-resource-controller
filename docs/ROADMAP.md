# 로드맵 — TempSES

## 진행 원칙
1. **분석/설계 문서가 먼저 합의된 후 코드 작성** (현 단계).
2. **의사결정 무관한 부분부터 진행**. 결정 필요 항목은 [DECISIONS.md](DECISIONS.md)에 모아 일괄 처리.
3. **TDD**: red → green → refactor. 모든 production 코드 변경은 실패 테스트가 선행되어야 한다.
4. **E2E**: 가능한 한 실제 SES/S3/DDB를 사용. 로컬 단위 테스트는 [moto](https://github.com/getmoto/moto)로 AWS API mock.
5. **모든 진행 결과는 `docs/` 마크다운에 기록**, 외부 자료는 링크로 인용.
6. **모든 변경은 PR 단위**. main 직접 push 금지.

## Phase 0 — 저장소 + Terraform 셋업

산출물:
- [x] 저장소 디렉터리 구조 ([repo-layout 참고](#repo-layout))
- [x] `.gitignore`, `.editorconfig`, `pre-commit` 훅(선택)
- [ ] Terraform `backend` (S3 + DynamoDB lock) — 결정 D5
- [ ] AWS Provider, `data` blocks로 보존 리소스 참조
- [ ] `outputs.tf` (CloudFront 도메인, API 엔드포인트)

테스트:
- `terraform fmt -check`, `terraform validate`, `tflint` (CI).

## Phase 1 — 백엔드 MVP (TDD)

### 1.1 ingest Lambda

테스트 우선 (모두 `pytest`):
1. `test_drop_when_spam_verdict_fail` — verdict FAIL 메일은 DDB write가 호출되지 않음.
2. `test_drop_when_virus_verdict_fail`
3. `test_drop_when_address_not_active` — `addresses` GetItem 결과가 None → drop.
4. `test_happy_path_text_only` — plain text 메일 한 통이 DDB에 정상 기록.
5. `test_html_sanitized` — `<script>` 포함 메일이 sanitize 후 저장.
6. `test_attachment_uploaded_to_s3` — 첨부파일이 별도 S3 prefix로 저장.
7. `test_idempotent_on_duplicate_object_event` — 같은 S3 이벤트 두 번 수신 시 중복 PutItem 없음.
8. `test_dlq_on_unexpected_exception` — Lambda destinations에 OnFailure 설정됨(인프라 검증).

의존성:
- `nh3`, `python-ulid`, `boto3`(provided by runtime).
- 빌드: `pip install -t build/ -r requirements.txt` 후 zip.

### 1.2 API Lambda

테스트 우선:
1. `test_create_address_returns_201` + 형식 검증.
2. `test_create_address_collision_retries`.
3. `test_delete_address_204`, `test_delete_unknown_404`.
4. `test_list_messages_empty`.
5. `test_list_messages_after_cursor` (sort key 페이징).
6. `test_presign_attachment_returns_signed_url` — `boto3.generate_presigned_url` 결과의 호스트/만료시간 확인.

### 1.3 Terraform 모듈

- `modules/ingest_pipeline` — S3 bucket + event notification + Lambda + DLQ + Permission.
- `modules/api` — HTTP API + Lambda integrations + CORS.
- `modules/ddb` — 두 테이블 + TTL.
- `modules/ses` — Domain identity + DKIM + MAIL FROM + Receipt Rule Set (활성화는 별도 단계 — D6).
- `modules/route53_records` — SES tokens를 받아 CNAME/TXT/MX 발급.

Terraform 단위 테스트: [Terratest](https://terratest.gruntwork.io/) 또는 [tflint](https://github.com/terraform-linters/tflint) + `terraform plan -detailed-exitcode`. 학습용이므로 **plan 검증과 `terraform validate`**로 시작.

## Phase 2 — 프론트엔드

테스트 우선 ([Vitest](https://vitest.dev/) + [Testing Library](https://testing-library.com/docs/react-testing-library/intro)):
1. `<AddressBar />` 렌더링, 복사 버튼이 navigator.clipboard.writeText 호출.
2. `<Inbox />` polling 훅이 5s 주기로 fetch 호출, 새 메시지 append.
3. `<MessageView />` HTML 본문이 iframe srcdoc로 렌더, sandbox 속성 검증.
4. `<NewAddressButton />` 클릭 시 POST → 인박스 초기화.

빌드 산출물 → S3 `tempses-web` 버킷, CloudFront 캐시 무효화는 GitHub Actions 워크플로의 마지막 step.

## Phase 3 — 운영 안전망 (선택)

- CloudWatch 알람 (Lambda Errors, DLQ depth).
- AWS Budgets($10/월 알림).
- WAF: API GW 앞단 (IP rate limit 100req/5min) — 비용 추가($5/월) → D7.
- SES production access 신청 — 회신 발송 기능 추가 시.

## E2E 테스트 전략

### 옵션
| 옵션 | 장점 | 단점 |
|------|------|------|
| A. LocalStack | 무료, 빠름 | SES Inbound는 LocalStack [Pro](https://docs.localstack.cloud/aws/services/ses/)에만 부분 지원 |
| B. 실제 AWS, 별도 stage(`dev`) | 진짜 동작 검증 | 비용 약간, secret 관리 |
| **C. 하이브리드(권장)** | 단위는 moto, E2E는 실제 AWS dev stage | 약간 복잡 |

### 권장: C
- Terraform `stage` 변수(`prod`, `dev`)로 동일 코드 두 환경 배포.
- E2E 시나리오 (`tests/e2e/test_inbox.py` 예시):
  1. `POST /addresses` → 임시 주소 수령.
  2. boto3로 SES를 통해 자기 자신에게 메일 발송 (Production access 필요 없음 — 검증된 주소끼리는 sandbox에서도 발송 가능).
  3. polling으로 `GET /addresses/{addr}/messages` 호출.
  4. 30초 이내에 메시지 1건 등장 + `body_text` 일치.
  5. tear-down: 메시지/주소 강제 삭제.
- 런타임: GitHub Actions `e2e` 잡, PR label `run-e2e` 시 또는 main 머지 후 nightly.

## CI/CD (GitHub Actions)

[OIDC로 IAM 역할 가정](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) — 장기 시크릿 미사용.

워크플로 파일:
- `.github/workflows/ci.yml` — PR 대상
  1. lint(`ruff`, `mypy`, `eslint`, `tsc`)
  2. unit test (`pytest`, `vitest`)
  3. `terraform fmt -check`, `terraform validate`, `tflint`
  4. `terraform plan -lock=false` (artifact로 업로드)
- `.github/workflows/cd.yml` — main push 대상
  1. build & test (위와 동일)
  2. lambda zip 빌드 → S3 업로드
  3. `terraform apply` (자동 승인은 dev stage만, prod는 manual approval)
  4. CloudFront 무효화
- `.github/workflows/e2e.yml` — `run-e2e` 라벨 또는 nightly cron
  1. dev stage에 deploy
  2. E2E 시나리오 실행
  3. tear-down

브랜치 보호: main에 PR 필요, status checks(ci, terraform plan, tests) 통과, 1 approval.

## 일정 추정 (학습 페이스)
- Phase 0: 0.5d
- Phase 1: 2d (Lambda 2종 + Terraform 모듈 + 단위 테스트)
- Phase 2: 1d (React + tests + 배포)
- Phase 3: 0.5d (선택)
- E2E + CI: 0.5d

총 약 4~4.5일.

## repo-layout

```
aws-resource-controller/
├── README.md
├── docs/
│   ├── ANALYSIS.md
│   ├── DESIGN.md
│   ├── ROADMAP.md
│   ├── TEARDOWN.md
│   └── DECISIONS.md
├── inventory/
│   └── INVENTORY.md
├── terraform/
│   ├── backend.tf
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── ses/
│   │   ├── ingest_pipeline/
│   │   ├── ddb/
│   │   ├── api/
│   │   ├── frontend/
│   │   └── route53_records/
│   └── envs/
│       ├── dev/
│       └── prod/
├── lambda/
│   ├── ingest/
│   │   ├── src/handler.py
│   │   ├── requirements.txt
│   │   └── tests/
│   └── api/
│       ├── src/{create_address,delete_address,list_messages,presign_attachment}.py
│       ├── requirements.txt
│       └── tests/
├── web/
│   ├── index.html
│   ├── src/
│   ├── tests/
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   └── e2e/
└── .github/
    └── workflows/
        ├── ci.yml
        ├── cd.yml
        └── e2e.yml
```

## 관련 문서
- [ANALYSIS.md](ANALYSIS.md), [DESIGN.md](DESIGN.md), [TEARDOWN.md](TEARDOWN.md), [DECISIONS.md](DECISIONS.md)
