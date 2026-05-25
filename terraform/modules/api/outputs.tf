output "api_endpoint" {
  description = "Base URL of the HTTP API"
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "api_lambda_function_name" {
  value = aws_lambda_function.api.function_name
}

output "api_lambda_role_arn" {
  value = aws_iam_role.api_lambda.arn
}
