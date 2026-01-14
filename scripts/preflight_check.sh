#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TARGET_ENV="$1"

echo -e "${YELLOW}🔍 Pre-flight Check for: ${TARGET_ENV}${NC}"

if [ "$TARGET_ENV" == "local" ]; then
    echo -e "${GREEN}💻 Mac Local Mode Selected.${NC}"
    echo -e "   - Profile: local"
    echo -e "   - Hot-Reload: Enabled"
    exit 0
fi

if [ "$TARGET_ENV" == "production" ]; then
    # 1. Check Git Status
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${RED}❌ BLOCKING: You have uncommitted changes. Production deployment requires a clean git state.${NC}"
        git status
        exit 1
    fi
    echo -e "${GREEN}✅ Git State is Clean.${NC}"

    # 2. Confirmation
    echo -e "${RED}⚠️  WARNING: You are about to deploy to PRODUCTION.${NC}"
    
    # CI/CD Bypass
    if [ "$NON_INTERACTIVE" == "1" ]; then
        echo -e "${YELLOW}🤖 Non-Interactive Mode Detected. Proceeding automatically...${NC}"
    else
        read -p "Are you sure? (Type 'yes' to proceed): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "Aborted."
            exit 1
        fi
    fi
else
    # Dev Mode Checks
    echo -e "${GREEN}✅ Development Mode Selected.${NC}"
fi

exit 0
