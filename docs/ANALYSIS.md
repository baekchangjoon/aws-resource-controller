---
title: 분석 — TempSES
created: 2026-05-25
updated: 2026-05-25
phase: 0
status: living
reading_order: 1
---

# 분석 — TempSES (dev-temp-mail.com)

작성일: 2026-05-25
대상 AWS 계정: 322242916220
주 리전: ap-northeast-2 (Seoul)

## 1. 프로젝트 배경

- 사용자 `dev-temp-mail-user`가 2025-11-02 경 [temp-mail.io](https://temp-mail.io) 스타일의 일회용(disposable) 이메일 서비스를 AWS SES 기반으로 만들려 시작.
- 기획서 원본(`~/Downloads/aws_ses.html`, 로컬 파일 — 저장소엔 포함되지 않음)에 사용자/개발 요구사항이 정리됨.
- 인프라 일부(SES 수신, S3 저장, Lambda 트리거)는 콘솔로 만들었으나, 도메인 로직(파싱 후 저장/표시/API/UI)은 미구현 상태로 중단.
- 학습/포트폴리오 목적이며, 운영 책임은 가벼움 — 그러나 **공개 도메인**이므로 스팸/악성 트래픽 대비는 필요.

## 2. 현재 AWS 인벤토리

전체 인벤토리는 [inventory/INVENTORY.md](../inventory/INVENTORY.md) 참고.

### 보존 대상
| 자원 | 식별자 | 사유 |
|------|--------|------|
| AWS 계정 | 322242916220 | 사용자 계정 |
| IAM 사용자 | `dev-temp-mail-user` | 현재 작업자 |
| 도메인 등록 | `dev-temp-mail.com` | 구매·갱신 비용 발생 |
| Route53 호스티드존 | `Z033790515Q1CCSID8PBQ` | NS 레코드 변경 시 도메인 등록기관 측 추가 작업 발생 |

### 재생성 대상 (Terraform으로 새로 정의)
| 자원 | 비고 |
|------|------|
| S3 버킷 `temp-mail-emails-bucket` | 객체 0개, 삭제·재생성 안전 |
| Lambda `sampleMailReceived` + 서비스 롤 `sampleMailReceived-role-0pct4swr` | 콘솔 자동 생성 흔적 |
| SES Receipt Rule Set `Default` (룰 `Default`) | 재정의 |
| SES 도메인 ID `dev-temp-mail.com` (DKIM/MAIL FROM 포함) | 재검증 필요. 단 Route53 호스티드존을 유지하므로 DNS 변경은 Terraform이 동시 반영 |
| SES 이메일 ID `changjoon.baek@gmail.com` | 필요 시 재검증 |
| Route53 레코드(DKIM CNAME 3, MX, DMARC TXT, MAIL FROM MX/SPF) | Terraform에서 SES 출력에 맞춰 자동 발급/관리 |

### 정리(삭제) 대상 — 과거 잔여물
| 자원 | 생성 시점 | 사유 |
|------|----------|------|
| IAM Role `aws-elasticbeanstalk-ec2-role` | 2017 | Beanstalk 미사용 |
| IAM Role `aws-elasticbeanstalk-service-role` | 2017 | 동상 |
| IAM Role `CrashDetector-role-7ty9zpl9` | 2021 | 미사용 |
| IAM Role `CrashDetector-role-lkz6d7l4` | 2021 | 미사용 |
| IAM Role `CrashDetector0-role-pp2zcylr` | 2021 | 미사용 |
| IAM Role `CodeCatalystWorkflowDevelopmentRole-baekchangjoon` | 2025-02 | 미사용 |
| EC2 Key Pair `baek_aws_trial` | 2021-04 | EC2 인스턴스 0건 |
| Local IAM Policy `AWSLambdaBasicExecutionRole-*` 4건 | 자동 생성 | 새 Lambda 롤이 대체 |

`AWSServiceRoleForXxx` 류 SLR(서비스 링크드 롤)은 AWS가 자동 관리하므로 **건드리지 않음**.

## 3. HTML 기획서 타당성 평가

원본: `~/Downloads/aws_ses.html` (로컬 파일)

### 정합한 부분
| 항목 | 평가 | 근거 |
|------|------|------|
| 아키텍처(SES→S3→Lambda→DDB→API GW→FE) | ✅ 정석적 패턴 | [AWS 블로그 — Receive and process incoming email with Amazon SES](https://aws.amazon.com/blogs/messaging-and-targeting/receive-and-process-incoming-email-with-amazon-ses/) |
| MIME 파싱 위치(Lambda) | ✅ 적절 | SES 직접 invoke는 30s/30MB 한도. S3 경유가 안전 |
| DynamoDB TTL 자동 삭제 | ✅ 적절 | [DynamoDB TTL docs](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html) |
| HTML Sanitization 강조 | ✅ 필수 | XSS 위험 — Mailpile/temp-mail 류 모두 필수 적용 |
| WebSocket/Polling 양자택일 | ✅ 정당 | 학습용은 polling이 단순 |
| S3 Lifecycle/Rate Limit | ✅ 표준 | [S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html), [API GW Usage Plans](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html) |

### 보완 필요
| 번호 | 항목 | 문제 | 권장 수정 |
|------|------|------|----------|
| 1 | "SES → S3 + 동시에 SNS/Lambda" | 이중 트리거는 동기화 복잡 | **S3 단일 액션 + S3 ObjectCreated 이벤트로 Lambda** (현재 인프라가 이미 이 구조). [AWS 문서](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-action-s3.html) |
| 2 | `*@tempdomain.com` Catch-all 표현 | SES Receipt Rule은 도메인 단위 지정으로 catch-all 효과 | Recipients=`dev-temp-mail.com` 하나만 두면 됨 |
| 3 | "SES Sandbox 우려" 암시 | Sandbox는 **outbound 발송 한도만** 제약. inbound와 무관 | 수신에 영향 없음. 회신 발송 기능이 필요해질 때만 Production access 신청 |
| 4 | "Lambda 파싱 800ms" SLA + 현재 timeout 3s | 첨부 큰 메일 시 위험 | **Timeout 60s / Memory 256MB**로 상향 |
| 5 | "DOMPurify로 서버 sanitize" | DOMPurify는 브라우저용 | **Python: [nh3](https://pypi.org/project/nh3/) (Rust 기반 ammonia 바인딩)** 또는 plain text 우선 표시 후 원본 HTML은 격리 iframe |
| 6 | 주소 발급/만료 데이터 모델 부재 | catch-all이라 "활성 주소"를 별도로 관리해야 폐기 가능 | `addresses` 테이블 분리, 미등록 주소로 온 메일은 Lambda에서 drop |
| 7 | SES `ScanEnabled` 활용 누락 | 스팸/바이러스 verdict 헤더가 부여되지만 사용 안 함 | Lambda 진입 시 `X-SES-Spam-Verdict`/`X-SES-Virus-Verdict`=`FAIL` 메일 drop. [docs](https://docs.aws.amazon.com/ses/latest/dg/receiving-email-notifications-contents.html) |
| 8 | 에러 처리(DLQ) 없음 | 파싱 실패 시 메일 소실 | **Lambda Destinations OnFailure → SQS DLQ**. [docs](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async.html#invocation-dlq) |
| 9 | iframe `sandbox`만으로 부족 | 외부 리소스/추적 픽셀 잠재 | **CSP 헤더 + `sandbox` + `referrerpolicy=no-referrer` 결합** |
| 10 | 모니터링/알람 누락 | 학습용도 비용 폭주 가능 | CloudWatch Lambda 에러율 + 비용 예산 알람 |

### 결론
**전체 설계는 타당**. 위 10개 보완점만 반영하면 학습/포트폴리오 수준에서 실제 동작 가능한 서비스가 됨.

## 4. 격차(Gap) 종합

| 컴포넌트 | 상태 | 격차 |
|---------|------|------|
| SES 도메인 검증 | ✅ | 없음 |
| MX/DKIM/DMARC | ✅ | 없음 (Terraform으로 코드화 필요) |
| SES Receipt Rule (S3 저장) | ✅ | 룰을 코드화하면서 Whitelist/Spam verdict 활용으로 재정의 |
| S3 → Lambda 트리거 | ✅ | 동일 |
| Lambda 파싱 기본 | ✅ | 핵심 로직(verdict/whitelist/sanitize/DB write/DLQ) 추가 |
| Lambda timeout 3s | ❌ | 60s/256MB 상향 |
| DynamoDB 2테이블 | ❌ | 신규 생성 |
| DynamoDB TTL | ❌ | 신규 |
| S3 Lifecycle | ❌ | 신규 |
| HTTP API + Lambda 4개 핸들러 | ❌ | 신규 |
| React 정적 SPA | ❌ | 신규 |
| CloudFront + S3 호스팅 | ❌ | 신규 |
| WAF/Rate Limit | ✅ | Phase 3b 완료 — CloudFront WAFv2 + API GW HTTP API stage throttle |
| CloudWatch 알람 | ❌ | Phase 3 |
| Terraform IaC | ❌ | 전체 코드화 |
| TDD/E2E 테스트 | ❌ | 신규 |
| GitHub Actions CI | ❌ | 신규 |

## 5. 운영 가정과 비용 추정

- **트래픽 가정**: 일 활성 주소 100개, 주소당 평균 메일 5건 → 일 500건, 월 15,000건
- **저장 가정**: 메일 평균 50KB, TTL 2h
- **예상 월 비용**:
  - SES inbound 15,000건 × $0.10/1,000 = **$1.50**
  - Lambda(Ingest 15,000 + API 200,000) 초당 짧음 → **<$0.10**
  - DynamoDB(온디맨드, 50,000 ops, 1GB) → **<$1.00**
  - S3(저장 < 1GB, lifecycle로 삭제) → **<$0.05**
  - CloudFront(< 5GB) → **<$0.50**
  - 총 **$3.5/월 미만** (스팸 폭주 시 별도)

근거: [AWS Pricing — SES](https://aws.amazon.com/ses/pricing/), [Lambda](https://aws.amazon.com/lambda/pricing/), [DynamoDB](https://aws.amazon.com/dynamodb/pricing/on-demand/)

## 관련 문서
- [DESIGN.md](DESIGN.md) — 상세 설계
- [ROADMAP.md](ROADMAP.md) — 구현 단계와 TDD 전략
- [TEARDOWN.md](TEARDOWN.md) — 정리 대상 리소스
- [DECISIONS.md](DECISIONS.md) — 사용자 결정 대기 항목
