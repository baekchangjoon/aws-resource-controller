#!/usr/bin/env bash
# Build the SPA and publish it to the dev environment.
#
# Reads bucket name + distribution id + API endpoint from Terraform
# outputs so the script stays in sync with the infrastructure.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TF_DIR="$HERE/../terraform/envs/dev"

API_BASE="$(terraform -chdir="$TF_DIR" output -raw api_endpoint)"
WEB_BUCKET="$(terraform -chdir="$TF_DIR" output -raw web_bucket_name)"
CF_ID="$(terraform -chdir="$TF_DIR" output -raw cloudfront_distribution_id)"

echo "API:        $API_BASE"
echo "S3 bucket:  $WEB_BUCKET"
echo "CloudFront: $CF_ID"

echo "[1/4] npm install"
( cd "$HERE" && npm install --no-fund --no-audit --silent )

echo "[2/4] vite build"
( cd "$HERE" && VITE_API_BASE="$API_BASE" npm run build )

echo "[3/4] sync to S3"
aws s3 sync "$HERE/dist/" "s3://$WEB_BUCKET/" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html"
aws s3 cp "$HERE/dist/index.html" "s3://$WEB_BUCKET/index.html" \
  --cache-control "public, max-age=0, must-revalidate" \
  --content-type "text/html; charset=utf-8"

echo "[4/4] CloudFront invalidation"
aws cloudfront create-invalidation --distribution-id "$CF_ID" --paths "/*" \
  --query 'Invalidation.{Id:Id,Status:Status}' --output json
