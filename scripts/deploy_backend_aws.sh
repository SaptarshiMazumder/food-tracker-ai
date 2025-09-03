#!/usr/bin/env bash

set -euo pipefail

# Simple deploy script to build the Lambda image (multi-stage target in app/Dockerfile),
# push to ECR, create/update the Lambda function, set env vars, and output Function URL.

# -------- Config (overridable via env or flags) --------
REGION="${REGION:-ap-northeast-1}"
ECR_REPO="${ECR_REPO:-food-analyzer-backend-lambda}"
IMAGE_TAG="${IMAGE_TAG:-v1}"
FUNCTION_NAME="${FUNCTION_NAME:-FoodAnalyzerBackend}"
ROLE_NAME="${ROLE_NAME:-food-analyzer-lambda-role}"
BUILD_IMAGE="true"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [options]
  -r <region>            AWS region (default: ${REGION})
  -t <tag>               Image tag (default: ${IMAGE_TAG})
  -f <function-name>     Lambda function name (default: ${FUNCTION_NAME})
  -n <repo-name>         ECR repository name (default: ${ECR_REPO})
  -s                     Skip docker build (use existing local image)
  -h                     Help

Environment variables respected: REGION, ECR_REPO, IMAGE_TAG, FUNCTION_NAME, ROLE_NAME
Reads .env from repo root if present to populate API keys for Lambda env.
USAGE
}

while getopts ":r:t:f:n:sh" opt; do
  case $opt in
    r) REGION="$OPTARG" ;;
    t) IMAGE_TAG="$OPTARG" ;;
    f) FUNCTION_NAME="$OPTARG" ;;
    n) ECR_REPO="$OPTARG" ;;
    s) BUILD_IMAGE="false" ;;
    h) usage; exit 0 ;;
    :) echo "Option -$OPTARG requires an argument" >&2; usage; exit 2 ;;
    \?) echo "Unknown option -$OPTARG" >&2; usage; exit 2 ;;
  esac
done

# -------- Pre-flight checks --------
command -v aws >/dev/null 2>&1 || { echo "ERROR: aws CLI is required" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required" >&2; exit 1; }

# Load .env if present (best-effort)
if [[ -f ./.env ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' ./.env | xargs -r) || true
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"
LOCAL_IMAGE="food-analyzer-backend-lambda:${IMAGE_TAG}"
REMOTE_TAG="${ECR_URI}:${IMAGE_TAG}"

echo "\n=== Configuration ==="
echo "Account ID:    ${ACCOUNT_ID}"
echo "Region:        ${REGION}"
echo "ECR Repo:      ${ECR_REPO}"
echo "Image Tag:     ${IMAGE_TAG}"
echo "Function Name: ${FUNCTION_NAME}"
echo "Role Name:     ${ROLE_NAME}"
echo "ECR URI:       ${ECR_URI}"
echo

# -------- Build Lambda image (aws_dev_service target) --------
if [[ "${BUILD_IMAGE}" == "true" ]]; then
  echo "Building image ${LOCAL_IMAGE} from app/Dockerfile (target aws_dev_service) ..."
  docker build -f app/Dockerfile --target aws_dev_service -t "${LOCAL_IMAGE}" .
else
  echo "Skipping build, using existing local image: ${LOCAL_IMAGE}"
fi

# -------- Ensure ECR repo and push image --------
aws ecr describe-repositories --repository-names "${ECR_REPO}" --region "${REGION}" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${ECR_REPO}" --region "${REGION}" >/dev/null

aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${ECR_URI}"

echo "Tagging and pushing ${LOCAL_IMAGE} -> ${REMOTE_TAG} ..."
docker tag "${LOCAL_IMAGE}" "${REMOTE_TAG}"
docker push "${REMOTE_TAG}"

# -------- Create Lambda execution role if missing --------
ROLE_ARN=$(aws iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text 2>/dev/null || true)
if [[ -z "${ROLE_ARN}" || "${ROLE_ARN}" == "None" ]]; then
  echo "Creating IAM role ${ROLE_NAME} ..."
  TMP_TRUST=$(mktemp)
  cat >"${TMP_TRUST}" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Principal": { "Service": "lambda.amazonaws.com" }, "Action": "sts:AssumeRole" }
  ]
}
JSON
  ROLE_ARN=$(aws iam create-role \
    --role-name "${ROLE_NAME}" \
    --assume-role-policy-document file://"${TMP_TRUST}" \
    --query 'Role.Arn' --output text)
  aws iam attach-role-policy --role-name "${ROLE_NAME}" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >/dev/null
  rm -f "${TMP_TRUST}"
  # Small wait to allow role propagation
  sleep 8
fi
echo "Role ARN: ${ROLE_ARN}"

# -------- Create or Update Lambda function from ECR image --------
if aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${REGION}" >/dev/null 2>&1; then
  echo "Updating Lambda code for ${FUNCTION_NAME} ..."
  aws lambda update-function-code --function-name "${FUNCTION_NAME}" \
    --image-uri "${REMOTE_TAG}" --region "${REGION}" >/dev/null
else
  echo "Creating Lambda function ${FUNCTION_NAME} ..."
  aws lambda create-function --function-name "${FUNCTION_NAME}" \
    --package-type Image --code ImageUri="${REMOTE_TAG}" \
    --role "${ROLE_ARN}" --timeout 900 --memory-size 1024 \
    --region "${REGION}" >/dev/null
fi

# -------- Wait for function to finish updating before next operations --------
echo "Waiting for Lambda to finish updating ..."
aws lambda wait function-updated --function-name "${FUNCTION_NAME}" --region "${REGION}" || true

# -------- Update environment variables --------
# Pull secrets from environment if set, otherwise leave blank or sensible defaults
SECRET_KEY_VAL="${SECRET_KEY:-replace-me}"
GOOGLE_API_KEY_VAL="${GOOGLE_API_KEY:-}"
GOOGLE_CLOUD_PROJECT_VAL="${GOOGLE_CLOUD_PROJECT:-}"
GOOGLE_CLOUD_LOCATION_VAL="${GOOGLE_CLOUD_LOCATION:-ap-northeast-1}"
GOOGLE_CSE_ID_VAL="${GOOGLE_CSE_ID:-}"
OPENAI_API_KEY_VAL="${OPENAI_API_KEY:-}"
ING_PROVIDER_VAL="${INGREDIENTS_PROVIDER:-gemini}"
DEFAULT_MODEL_VAL="${DEFAULT_MODEL:-gemini-2.5-pro}"
DEFAULT_OAI_MODEL_VAL="${DEFAULT_OPENAI_MODEL:-gpt-4o}"
RAG_DIR_VAL="${RAG_ARTIFACTS_DIR:-/var/task/mmfood-rag/artifacts}"
UPLOAD_DIR_VAL="${UPLOAD_DIR:-/tmp/uploads}"

echo "Updating Lambda environment variables ..."
set +e
for attempt in $(seq 1 12); do
  aws lambda update-function-configuration --function-name "${FUNCTION_NAME}" --region "${REGION}" \
    --environment "Variables={FLASK_ENV=production,SECRET_KEY=${SECRET_KEY_VAL},GOOGLE_API_KEY=${GOOGLE_API_KEY_VAL},GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT_VAL},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION_VAL},GOOGLE_CSE_ID=${GOOGLE_CSE_ID_VAL},OPENAI_API_KEY=${OPENAI_API_KEY_VAL},INGREDIENTS_PROVIDER=${ING_PROVIDER_VAL},DEFAULT_MODEL=${DEFAULT_MODEL_VAL},DEFAULT_OPENAI_MODEL=${DEFAULT_OAI_MODEL_VAL},RAG_ARTIFACTS_DIR=${RAG_DIR_VAL},UPLOAD_DIR=${UPLOAD_DIR_VAL}}" >/dev/null
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "Environment update succeeded."
    break
  fi
  echo "Lambda is still updating (attempt ${attempt}/12). Retrying in 5s ..."
  sleep 5
done
set -e

# Ensure config update is fully applied
aws lambda wait function-updated --function-name "${FUNCTION_NAME}" --region "${REGION}" || true

# -------- Ensure Function URL exists and is public --------
if ! aws lambda get-function-url-config --function-name "${FUNCTION_NAME}" --region "${REGION}" >/dev/null 2>&1; then
  aws lambda create-function-url-config --function-name "${FUNCTION_NAME}" --auth-type NONE --region "${REGION}" >/dev/null
  # permission may already exist; ignore errors
  aws lambda add-permission --function-name "${FUNCTION_NAME}" --region "${REGION}" \
    --action lambda:InvokeFunctionUrl --principal "*" \
    --function-url-auth-type "NONE" --statement-id public-url-access >/dev/null 2>&1 || true
fi

FN_URL=$(aws lambda get-function-url-config --function-name "${FUNCTION_NAME}" --region "${REGION}" --query FunctionUrl --output text)
echo "\nDeployed. Function URL: ${FN_URL}"
echo "Try: curl \"${FN_URL}/health\""


