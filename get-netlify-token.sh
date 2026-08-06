#!/usr/bin/env bash
set -euo pipefail

echo "=== Netlify deploy credentials (for GitHub Actions) ==="
echo
echo "1) Personal access token"
echo "   https://app.netlify.com/user/applications#personal-access-tokens"
echo "   ? Create token ? save as NETLIFY_AUTH_TOKEN"
echo
echo "2) Site ID"
echo "   Netlify dashboard ? your site ? Site configuration ? General ? Site ID"
echo "   ? save as NETLIFY_SITE_ID"
echo
echo "3) GitHub repository secrets (Settings ? Secrets and variables ? Actions)"
echo "   NETLIFY_AUTH_TOKEN"
echo "   NETLIFY_SITE_ID"
echo
echo "4) Push to main � GitHub Actions deploys automatically."
echo "   Manual deploy: NETLIFY_AUTH_TOKEN=... NETLIFY_SITE_ID=... ./deploy.sh"
