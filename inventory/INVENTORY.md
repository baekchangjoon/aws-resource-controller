# AWS 리소스 인벤토리

- **계정**: 322242916220 (alias 없음)
- **주 사용자**: `dev-temp-mail-user` (마지막 로그인 2026-05-24)
- **주 리전**: ap-northeast-2 (Seoul)
- **스캔 일시**: 2026-05-24
- **MFA**: 활성 (계정 디바이스 7개)

## 한눈에 보기 — 운영 중인 서비스

이 계정은 **`dev-temp-mail.com` 임시 메일 서비스** 하나만 실제 운영 중입니다. 전체 흐름:

```
Internet → MX(inbound-smtp.ap-northeast-2) → SES Receipt Rule "Default"
       → S3 (temp-mail-emails-bucket/emails/) → Lambda (sampleMailReceived)
```

## 1. SES (ap-northeast-2)

| 항목 | 값 |
|------|----|
| Production Access | **❌ Sandbox** (요청 필요) |
| 일일 발송 한도 | 200통 / 1 TPS |
| 최근 24h 발송량 | 0 |
| Enforcement | HEALTHY |
| Suppression | 0건 |
| Dedicated IP | 없음 |
| 설정 세트 | 없음 |

**검증된 ID 2개**
- `dev-temp-mail.com` (DOMAIN, DKIM SUCCESS, MAIL FROM=`admin.dev-temp-mail.com`)
- `changjoon.baek@gmail.com` (EMAIL_ADDRESS)

**수신 규칙 (Receipt Rule Set: `Default`)**
- Rule `Default` — Recipients: `dev-temp-mail.com` → S3Action(`temp-mail-emails-bucket`, prefix=`emails/`), ScanEnabled=true

## 2. S3

| 버킷 | 리전 | 객체 | 암호화 | 퍼블릭 | 버저닝 | 라이프사이클 |
|------|------|------|--------|--------|--------|--------------|
| `temp-mail-emails-bucket` | ap-northeast-2 | 0 (prefix `emails/`) | AES256 | 완전 차단 | 미설정 | **❌ 없음** |

## 3. Lambda (ap-northeast-2)

| 함수명 | 런타임 | 핸들러 | 메모리 | 타임아웃 | 트리거 |
|--------|--------|--------|--------|----------|--------|
| `sampleMailReceived` | python3.13 | `lambda_function.lambda_handler` | 128MB | **3초** | S3 `temp-mail-emails-bucket` ObjectCreated |

- 환경변수: 없음
- 마지막 수정: 2025-11-02

## 4. Route53

| Hosted Zone | 레코드 | 비고 |
|-------------|--------|------|
| `dev-temp-mail.com.` (Z033790515Q1CCSID8PBQ) | 9개 | MX → SES inbound, DKIM 3개, DMARC, MAIL FROM 도메인 |

**주요 레코드**
- `dev-temp-mail.com` MX → `10 inbound-smtp.ap-northeast-2.amazonaws.com`
- `_dmarc` TXT → `v=DMARC1;p=quarantine;rua=mailto:changjoon.baek@gmail.com`
- DKIM CNAME 3개 (SES 자동 발급)
- `admin.dev-temp-mail.com` MX + SPF (MAIL FROM 도메인)

## 5. 네트워크 (VPC, ap-northeast-2)

- VPC: `vpc-28a52a43` (기본, 172.31.0.0/16)
- 서브넷 4개 (AZ a/b/c/d)
- IGW: `igw-770f7d1f`
- NAT Gateway: 없음
- 보안 그룹: 2개

## 6. IAM 요약

- **IAM 사용자**: 1명 (`dev-temp-mail-user`)
- **롤**: 17개 (대부분 AWS 서비스 링크드 롤 + 2017년 Beanstalk 잔여물)
- **로컬 정책**: 4개 (모두 Lambda 기본 실행 롤)
- **MFA 디바이스**: 7개 활성

## 7. 다른 리전 — 잔여 리소스 없음

us-east-1, us-west-2, ap-northeast-1, ap-southeast-1, eu-west-1 모두 EC2/Lambda/RDS **0건**.

## 8. 운영 중이 아닌 리소스

- **EC2**: 인스턴스 0, EBS 0, EIP 0, 스냅샷 0, 본인 AMI 0
- **EC2 Key Pair**: `baek_aws_trial` (2021-04-25 생성, 미사용 추정)
- **RDS, DynamoDB, ECR, SQS, SNS, API Gateway, CloudFront**: 모두 0건
- **오래된 IAM 롤** (검토 대상):
  - `aws-elasticbeanstalk-ec2-role`, `aws-elasticbeanstalk-service-role` (2017)
  - `CrashDetector-role-*` 3개 (2021)
  - `CodeCatalystWorkflowDevelopmentRole-baekchangjoon` (2025-02)

---

## 즉시 점검 권장 항목

| 우선순위 | 항목 | 이유 |
|---------|------|------|
| 🔴 높음 | SES Sandbox 해제 신청 | 외부 발신이 막혀 있음 (필요시) |
| 🟡 중간 | Lambda timeout 3초 → 15~30초 | 메일 처리 중 외부 호출 시 타임아웃 위험 |
| 🟡 중간 | S3 라이프사이클 정책 추가 | 메일 영구 보관 시 비용 누적 |
| 🟡 중간 | S3 버저닝 검토 | 메일 덮어쓰기 보호 필요시 활성화 |
| 🟢 낮음 | 미사용 IAM 롤 정리 | 2017/2021 잔여물, 보안 표면 축소 |
| 🟢 낮음 | Key Pair `baek_aws_trial` 정리 | 2021년 생성, EC2 없음 |
| 🟢 낮음 | CloudWatch Billing Alarm | 비용 알람 미설정 가능성 |
