#!/usr/bin/env bash
set -euo pipefail

echo "=== Surge deploy credentials (for GitHub Actions / Editor) ==="
echo
echo "1) Login"
echo "   surge login"
echo
echo "2) Fetch deploy token"
echo "   surge token"
echo
echo "3) GitHub repository secrets (Settings ? Secrets and variables ? Actions)"
echo "   SURGE_LOGIN    (your Surge email)"
echo "   SURGE_TOKEN    (token from step 2)"
echo
echo "4) Push to main � GitHub Actions deploys the editor to Surge."
echo "   Manual deploy: ./deploy-surge.sh"
