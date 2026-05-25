# 정리(Teardown) — 기존 AWS 리소스

본 문서는 **Terraform으로 재생성하기 전 삭제할 리소스**와, **유지할 리소스**를 명시한다.

> ⚠️ 모든 삭제 명령은 사용자 확인 후 실행. 본 문서는 명세이고, 실제 실행은 별도 PR 또는 운영 작업에서 진행.

## A. 보존 (절대 건드리지 않음)

| 자원 | 식별자 |
|------|--------|
| AWS 계정 | 322242916220 |
| IAM 사용자 | `dev-temp-mail-user` (+ 그 Access Key) |
| 도메인 등록 | `dev-temp-mail.com` (Route53 Registered Domains) |
| Route53 Hosted Zone | `Z033790515Q1CCSID8PBQ` (`dev-temp-mail.com.`) — Zone 자체는 유지하되 **DNS 레코드는 Terraform이 인수**함 |
| AWS 서비스 링크드 롤 | `AWSServiceRoleFor*` 일체 — AWS가 자동 관리 |
| MFA 디바이스 | 7개 그대로 |

## B. Terraform이 인수(import)할 리소스

Terraform `import` 또는 `data` 블록으로 참조한다. Apply 시 변경이 발생하면 PR 검토 단계에서 plan을 확인한다.

| 자원 | TF 인수 방식 | 비고 |
|------|--------------|------|
| Route53 Hosted Zone `Z033790515Q1CCSID8PBQ` | `data "aws_route53_zone"` | NS 변경 위험 회피. 레코드만 관리. |
| DNS 레코드 9건(MX/DKIM/DMARC/SPF) | 신규 발급 후 `terraform apply`로 덮어쓰기 | 기존 레코드와 동일 값이면 변경 없음 |

## C. 삭제 (Terraform 적용 전 또는 후에 수동 정리)

### C.1 SES 관련 (재생성)
| 자원 | 명령 |
|------|------|
| SES 도메인 ID `dev-temp-mail.com` | `aws sesv2 delete-email-identity --email-identity dev-temp-mail.com --region ap-northeast-2` |
| SES 이메일 ID `changjoon.baek@gmail.com` | 유지 또는 삭제(D4 결정). 유지 시 Terraform이 import |
| Receipt Rule Set `Default` (활성) | 비활성화 후 삭제: `aws ses set-active-receipt-rule-set --region ap-northeast-2` (no arg) → `aws ses delete-receipt-rule-set --rule-set-name Default --region ap-northeast-2` |

### C.2 S3
| 자원 | 명령 |
|------|------|
| 버킷 `temp-mail-emails-bucket` (객체 0건 확인됨) | `aws s3 rb s3://temp-mail-emails-bucket --force` |

### C.3 Lambda + 서비스 롤
| 자원 | 명령 |
|------|------|
| Lambda `sampleMailReceived` | `aws lambda delete-function --function-name sampleMailReceived --region ap-northeast-2` |
| 서비스 롤 `sampleMailReceived-role-0pct4swr` | (롤 정책 detach 후) `aws iam delete-role --role-name sampleMailReceived-role-0pct4swr` |

### C.4 오래된 IAM 롤 (미사용 잔여물)
| 롤 | 정리 |
|---|------|
| `aws-elasticbeanstalk-ec2-role` | 2017년 Beanstalk 흔적 — 삭제 |
| `aws-elasticbeanstalk-service-role` | 동상 — 삭제 |
| `CrashDetector-role-7ty9zpl9` | 2021년 미사용 — 삭제 |
| `CrashDetector-role-lkz6d7l4` | 동상 — 삭제 |
| `CrashDetector0-role-pp2zcylr` | 동상 — 삭제 |
| `CodeCatalystWorkflowDevelopmentRole-baekchangjoon` | 2025-02 미사용 — 삭제 |

명령 예:
```sh
ROLE=aws-elasticbeanstalk-ec2-role
# Inline policy 모두 제거
for p in $(aws iam list-role-policies --role-name "$ROLE" --query 'PolicyNames[]' --output text); do
  aws iam delete-role-policy --role-name "$ROLE" --policy-name "$p"
done
# Managed policy detach
for p in $(aws iam list-attached-role-policies --role-name "$ROLE" --query 'AttachedPolicies[].PolicyArn' --output text); do
  aws iam detach-role-policy --role-name "$ROLE" --policy-arn "$p"
done
# Instance profile 있다면 제거 (EB EC2 role)
for ip in $(aws iam list-instance-profiles-for-role --role-name "$ROLE" --query 'InstanceProfiles[].InstanceProfileName' --output text); do
  aws iam remove-role-from-instance-profile --instance-profile-name "$ip" --role-name "$ROLE"
  aws iam delete-instance-profile --instance-profile-name "$ip"
done
aws iam delete-role --role-name "$ROLE"
```

### C.5 자동 생성 Lambda 정책 4건
- `AWSLambdaBasicExecutionRole-a52bd632-...` 외 3건은 콘솔이 자동 생성. 새 Lambda 롤이 대체하면 detach 후 삭제 가능. 권한 확인 후 결정.

### C.6 EC2 키페어
- `baek_aws_trial` (2021-04 생성, 인스턴스 0건). 삭제 명령:
```sh
aws ec2 delete-key-pair --key-name baek_aws_trial --region ap-northeast-2
```

## D. 실행 순서 (권장)

1. **백업**: 메일 데이터가 0건이므로 별도 백업 없음. Terraform 코드는 git에 보존.
2. **현 운영 중단**: SES Receipt Rule Set `Default` 비활성화 → 메일 수신 일시 중단.
3. **C.1 ~ C.3** 삭제 (메일 인프라).
4. Terraform `dev` 환경에 새 리소스 apply → DNS/SES 검증 완료까지 대기 (DKIM 검증은 보통 분 단위).
5. **C.4 ~ C.6** 삭제 (잔여 IAM/Key pair).
6. 정리 결과는 `docs/CHANGELOG.md`(추후)에 기록.

## 다운타임

- 약 5~15분(SES 도메인 ID 삭제→재생성→DKIM 검증).
- 학습 프로젝트라 실 사용자 영향 미미.

## 관련 문서
- [ANALYSIS.md](ANALYSIS.md), [DESIGN.md](DESIGN.md), [ROADMAP.md](ROADMAP.md)
