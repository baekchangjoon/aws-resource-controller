# Terraform — TempSES

## 디렉터리 구조

```
terraform/
├── envs/
│   ├── dev/           # dev stage entrypoint
│   └── prod/          # prod stage entrypoint
└── modules/
    ├── ses/                  # Domain identity, DKIM, MAIL FROM, Receipt Rule Set
    ├── ingest_pipeline/      # S3 mail bucket + Lambda + DLQ + IAM
    ├── ddb/                  # DynamoDB tables (addresses, messages) + TTL
    ├── api/                  # HTTP API + Lambda integrations + CORS
    ├── frontend/             # S3 web bucket + CloudFront + ACM + Route53 record
    └── route53_records/      # SES/MAIL FROM/MX/DMARC records into existing zone
```

## 상태 관리

S3 + DynamoDB lock 백엔드(권장) — `backend.tf` 참조.

## 보존 리소스 참조

기존에 존재하는 자원은 `data` 블록으로 참조한다. 자세한 내용은 [docs/TEARDOWN.md](../docs/TEARDOWN.md) 참고.

- Route53 호스티드존: `data "aws_route53_zone"`
- IAM 사용자 `dev-temp-mail-user`: 참조만, 권한 변경 없음

## 사용

```sh
cd envs/dev
terraform init
terraform plan
terraform apply
```

## 모듈 인터페이스 (계획)

각 모듈은 `variables.tf`, `outputs.tf`, `versions.tf`를 둔다. 상세는 모듈 구현 단계에서 작성.
