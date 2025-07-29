#!/bin/sh
set -e

rm -rf sdks/typescript
npx --yes @openapitools/openapi-generator-cli generate \
  -i openapi.json \
  -g typescript-fetch \
  -o sdks/typescript \
  --additional-properties supportsES6=true,npmName=origin-sdk
npm --prefix sdks/typescript install --silent
npm --prefix sdks/typescript run build --silent
