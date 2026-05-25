# 설계 — TempSES

## 1. 시스템 컨텍스트

```
┌──────────────┐  SMTP     ┌────────────────────────┐
│ External MTA │ ────────▶ │ MX inbound-smtp.       │
└──────────────┘           │ ap-northeast-2         │
                           └──────────┬─────────────┘
                                      ▼
                           ┌────────────────────────┐
                           │ SES Receipt Rule       │
                           │ - ScanEnabled (verdict)│
                           │ - Action: S3 Put       │
                           └──────────┬─────────────┘
                                      ▼
                           ┌────────────────────────┐
                           │ S3 emails/<id>.eml     │
                           │ Lifecycle: 1d expire   │
                           └──────────┬─────────────┘
                                      │ ObjectCreated:Put
                                      ▼
   ┌──────────────────────────────────────────────────┐
   │ Lambda: ingest                                   │
   │ 1) verdict FAIL? → drop                          │
   │ 2) DDB.addresses.lookup → 미등록이면 drop          │
   │ 3) MIME parse                                    │
   │ 4) HTML sanitize (nh3)                           │
   │ 5) 첨부 → S3 attachments/<msg_id>/<file>         │
   │ 6) DDB.messages.put                              │
   │ ↳ OnFailure → SQS DLQ                            │
   └──────────────────┬───────────────────────────────┘
                      ▼
       ┌──────────────────────────┐
       │ DynamoDB                 │
       │ - addresses (TTL)        │
       │ - messages   (TTL)       │
       └──────────────┬───────────┘
                      │
   ┌──────────────────▼───────────────────────────────┐
   │ API Gateway (HTTP API)                           │
   │ ┌─────────────────────────────────────────────┐  │
   │ │ POST   /addresses                           │  │ → Lambda: create_address
   │ │ DELETE /addresses/{addr}                    │  │ → Lambda: delete_address
   │ │ GET    /addresses/{addr}/messages?after=    │  │ → Lambda: list_messages
   │ │ GET    /messages/{addr}/{id}/attach/{aid}   │  │ → Lambda: presign_attachment
   │ └─────────────────────────────────────────────┘  │
   └──────────────────┬───────────────────────────────┘
                      ▼
              ┌──────────────────┐
              │ CloudFront + S3  │   정적 SPA (Vite+React)
              │ web/             │
              └──────────────────┘
                      ▲
                      │ HTTPS, 5s polling (Phase 1)
              ┌──────────────────┐
              │ End User (BR)    │
              └──────────────────┘
```

## 2. 도메인/네트워크

- 메일 수신 도메인: `dev-temp-mail.com`
- MAIL FROM 도메인: `bounce.dev-temp-mail.com` (Terraform에서 신규 — 현행 `admin.` 대신 의미 명확화)
- 웹 도메인: 결정 필요 (예: `app.dev-temp-mail.com` 또는 apex). [DECISIONS.md](DECISIONS.md) 항목 D1.

## 3. 데이터 모델 (DynamoDB)

### 3.1 `tempses_addresses`
- 목적: 발급된 임시 주소의 활성 여부 관리. catch-all로 들어오는 메일을 활성 주소로만 필터링.
- PK: `address` (string, 예: `x8f9a@dev-temp-mail.com`)
- 속성
  - `created_at` (ISO 8601)
  - `client_fingerprint` (옵션, IP 해시 + UA 해시) — abuse 추적용
  - `ttl_at` (epoch seconds, 기본 created_at + 2h)
- TTL 키: `ttl_at`
- 읽기/쓰기: PutItem, GetItem만 사용. Query 없음.

### 3.2 `tempses_messages`
- 목적: 파싱·정제된 메일 본문 저장.
- PK: `address`
- SK: `message_id` (ULID — 시간순 정렬 + 유일성)
- 속성
  - `received_at` (ISO 8601)
  - `from` (string)
  - `to` (string, 정규화된 수신 주소)
  - `subject` (string)
  - `body_text` (string)
  - `body_html_safe` (string, sanitize 결과)
  - `s3_raw_key` (string, `emails/<...>.eml`)
  - `attachments` (list of `{aid, filename, size, content_type, s3_key}`)
  - `spam_verdict`, `virus_verdict`, `dkim_verdict`, `spf_verdict` (string)
  - `ttl_at` (epoch seconds)
- TTL 키: `ttl_at`
- 액세스 패턴: `Query(address, KeyConditionExpression='message_id > :after', Limit=N)` — 신규 메일 incremental 조회

### 3.3 ULID
- 라이브러리: [python-ulid](https://pypi.org/project/python-ulid/)
- ULID는 시간순 정렬 + 26자 문자열 + Crockford Base32. 보안 식별자로 부적합하므로 **API 노출 식별자는 ULID 사용**, 첨부 다운로드는 별도 presigned URL.

## 4. S3 버킷

### 4.1 `tempses-mail-{account_id}-{region}`
- 용도: SES 메일 원문 + 첨부파일
- 구조:
  - `emails/<receipt_id>` — SES가 putObject (key는 SES가 결정)
  - `attachments/<message_ulid>/<aid>/<filename>` — Lambda Ingest가 putObject
- 암호화: SSE-S3 (`AES256`)
- 퍼블릭 액세스: 완전 차단
- 라이프사이클:
  - `emails/` prefix: 1일 후 expire
  - `attachments/` prefix: 7일 후 expire (presigned URL 발급 가능 기간 = 7d 한도와 일치)
- 이벤트: `s3:ObjectCreated:Put` (prefix=`emails/`) → Lambda Ingest

### 4.2 `tempses-web-{account_id}`
- 용도: React 빌드 산출물 호스팅
- 퍼블릭 액세스: 완전 차단 (CloudFront OAC로만 접근)
- 라이프사이클: 미설정 (블루-그린 시 별도 prefix 관리)

## 5. Lambda

| 함수 | 런타임 | Memory | Timeout | 트리거 |
|------|--------|--------|---------|--------|
| `tempses-ingest` | Python 3.13 | 256 MB | 60 s | S3 ObjectCreated:Put `emails/` |
| `tempses-api-create-address` | Python 3.13 | 128 MB | 5 s | HTTP API POST `/addresses` |
| `tempses-api-delete-address` | Python 3.13 | 128 MB | 5 s | HTTP API DELETE `/addresses/{addr}` |
| `tempses-api-list-messages` | Python 3.13 | 128 MB | 5 s | HTTP API GET `/addresses/{addr}/messages` |
| `tempses-api-presign-attachment` | Python 3.13 | 128 MB | 5 s | HTTP API GET `/messages/{addr}/{id}/attach/{aid}` |

- 코드 패키지: 각 함수 디렉터리에서 의존성 포함 zip. `nh3`, `python-ulid` 같은 C/Rust 확장은 [Docker 빌드](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html) 또는 [aws-lambda-builders](https://github.com/aws/aws-lambda-builders)로 manylinux 호환 빌드.
- Lambda Layer는 사용하지 않음 (TF에서 단순화). 각 함수 zip에 의존성 포함.
- 환경 변수: 테이블명/버킷명/Region을 주입.
- 권한: 각 함수에 **최소 권한 IAM 롤**. ingest는 DDB Put + S3 GetObject/PutObject(attachments) + SQS SendMessage, api는 DDB GetItem/PutItem/Query/DeleteItem + S3 generate_presigned_url(읽기만).

## 6. API 명세

OpenAPI 3.1 스타일 요약. 전체 명세는 `lambda/api/openapi.yaml`에 추후 동기 작성.

### POST `/addresses`
Request:
```json
{ "local_part_hint": "optional-prefix" }
```
Response 201:
```json
{
  "address": "x8f9a2k@dev-temp-mail.com",
  "expires_at": "2026-05-25T13:00:00Z"
}
```
- 로컬파트: `[a-z0-9]{8}` 난수 (충돌 시 GetItem→재시도)
- 동일 주소 재발급 요청은 409.

### DELETE `/addresses/{addr}`
- 204. addresses 테이블에서 삭제. messages는 TTL에 맡김 (즉시 비우려면 별도 작업 큐 — Phase 2에서 결정).

### GET `/addresses/{addr}/messages?after=<ulid>&limit=50`
Response 200:
```json
{
  "items": [
    { "id": "01HXY...", "from": "...", "subject": "...", "received_at": "...", "has_attachments": true, "body_text": "...", "body_html_safe": "..." }
  ],
  "next_after": "01HXY..."
}
```
- 미등록 주소면 404.
- `after`가 없으면 가장 오래된 것부터 ascending. 클라이언트는 마지막 ID를 저장하고 다음 요청에 전달 (long-polling 흉내).

### GET `/messages/{addr}/{id}/attach/{aid}`
Response 200:
```json
{ "url": "https://...presigned...", "expires_in": 300 }
```
- 5분 유효 presigned GET.

### CORS
- 허용 origin: 결정 필요 (D2 — CloudFront 도메인 + dev `http://localhost:5173`)

## 7. 보안 모델

### 7.1 입력 단계 (수신)
- SES `ScanEnabled=true` — Spam/Virus verdict 부착.
- ingest Lambda는 `mail.headers.X-SES-Spam-Verdict=FAIL` 또는 `X-SES-Virus-Verdict=FAIL`이면 메일 drop. CloudWatch 로그에 `drop_reason` 기록.
- 미등록 수신 주소 drop → catch-all abuse 방어.

### 7.2 본문 처리
- HTML: [nh3](https://pypi.org/project/nh3/)으로 default whitelist + `style/script/object/iframe/embed/link` 제거, `on*` 속성 차단.
- 외부 리소스: `body_html_safe`에서 `<img>` `src` 속성을 제거하거나 `data:` 외 모두 차단 (추적 픽셀 방어). 옵션은 D3.

### 7.3 출력 단계 (브라우저 렌더)
- 본문은 iframe에 `sandbox="allow-same-origin"`만 허용 (script/forms/popups 모두 차단).
- iframe `srcdoc`에 `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline';">`.
- `referrerpolicy="no-referrer"`.

### 7.4 인증 / 권한
- 공개 서비스. 인증 없음.
- 주소 발급은 IP/UA 기반 fingerprint를 기록(분석용)하지만 차단은 WAF 단(Phase 3).

### 7.5 시크릿
- AWS 자격증명: CI/CD는 [OIDC GitHub Actions](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services) — 장기 IAM Key 미사용.
- 로컬 개발은 `dev-temp-mail-user` Access Key 유지.

## 8. 관찰 가능성

- CloudWatch Logs (Lambda) 보존: 7일.
- 메트릭: Lambda Errors, Duration, Throttles, DDB ConsumedRead/Write, S3 4xx.
- 알람:
  - ingest 에러율 > 5% (5분 평균)
  - DLQ depth > 0
  - AWS Budget(월 $10 초과 시 SNS 이메일)
- 트레이싱: X-Ray 활성(Active). 비용 미미.

## 9. 비기능 요건

| 항목 | 목표 |
|------|------|
| 수신→화면 표출 latency | < 10 s p95 (polling 5s 포함) |
| Lambda ingest p95 | < 2 s |
| Availability | 99% (단일 리전, 최선 노력) |
| 비용 | 정상 트래픽 시 < $5/월 |

## 10. 변경 관리

- 모든 인프라 변경은 Terraform PR.
- 모든 코드 변경은 PR + 테스트 통과 필수.
- Lambda 배포는 zip → S3 또는 직접 update (Terraform `aws_lambda_function.source_code_hash`로 변경 감지).

## 관련 문서
- [ANALYSIS.md](ANALYSIS.md)
- [ROADMAP.md](ROADMAP.md)
- [DECISIONS.md](DECISIONS.md)
