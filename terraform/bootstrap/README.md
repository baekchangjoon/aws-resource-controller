# Terraform Bootstrap

Terraform 본 모듈이 사용할 **state 백엔드 자원**을 만든다.

## 무엇을 만드는가
- S3 버킷 `tempses-tfstate-<account-id>` — Terraform state 저장 (versioning + SSE-S3 + public access block)
- DynamoDB 테이블 `tempses-tflock` — Terraform state lock

## 닭과 달걀 회피
이 모듈은 **로컬 state**를 사용한다 (`backend.tf` 없음). 한 번 apply 한 후 state 파일은 `.gitignore`로 제외하고, 본 모듈은 이후 변경할 일이 거의 없다.

## 사용

```sh
cd terraform/bootstrap
terraform init
terraform apply
```

apply 후 출력값(`state_bucket_name`, `lock_table_name`)을 `terraform/envs/{dev,prod}/backend.tf`에 반영한다 (이미 본 저장소에서는 하드코딩됨).

## 참고
- [Terraform S3 backend docs](https://developer.hashicorp.com/terraform/language/settings/backends/s3)
- [Bootstrapping Terraform state with Terraform itself](https://medium.com/@malparty/bootstrapping-terraform-state-with-terraform-itself-c8c4eaeb0d97)
