#!/bin/bash
# scripts/sync-issue-status.sh
# Git 브랜치 존재 여부로 BACKLOG.md의 ISSUE/RFC 상태 자동 동기화

set -e

BACKLOG_FILE="docs/BACKLOG.md"

echo "🔄 Syncing issue status with git branches..."

# 1. 현재 모든 브랜치 가져오기 (local + remote)
git fetch --all --quiet 2>/dev/null || true

# 2. ISSUE 상태 업데이트
for issue_num in {001..020}; do
  issue_id="ISSUE-${issue_num}"
  
  # 브랜치 패턴: feature/ISSUE-XXX-*, bug/ISSUE-XXX-*, refactor/ISSUE-XXX-*
  branch=$(git branch -a 2>/dev/null | grep -E "(feature|bug|refactor)/${issue_id}" | head -1 || echo "")
  
  if [ -n "$branch" ]; then
    # 브랜치 존재 → [/] In Progress로 변경
   # BACKLOG에서 해당 ISSUE 라인을 찾아 상태 업데이트
    if grep -q "\\*\\*${issue_id}\\*\\*" "$BACKLOG_FILE" 2>/dev/null; then
      # [ ] → [/]로 변경 (이미 [x]나 [/]가 아닌 경우만)
      sed -i.bak "s/^- \[ \] \*\*${issue_id}\*\*/- [\/] **${issue_id}**/" "$BACKLOG_FILE"
      
      # 브랜치 이름 추출 및 표시 (브랜치 정보가 없으면 추가)
      branch_name=$(echo "$branch" | sed 's/^[* ]*//' | sed 's|remotes/origin/||' | xargs)
      if ! grep -q "\`\[${branch_name}\]\`" "$BACKLOG_FILE"; then
        # 브랜치 정보 추가 (라인 끝에)
        sed -i.bak "s/\(\*\*${issue_id}\*\*.*\)$/\1 | \`[${branch_name}]\`/" "$BACKLOG_FILE"
      fi
      
      echo "  ✓ ${issue_id}: In Progress [${branch_name}]"
    fi
  else
    # 브랜치 없음 → [/] → [ ] 로 되돌리기 (완료된 것 제외)
    if grep -q "^- \[/\] \*\*${issue_id}\*\*" "$BACKLOG_FILE" 2>/dev/null; then
      sed -i.bak "s/^- \[\/\] \*\*${issue_id}\*\*/- [ ] **${issue_id}**/" "$BACKLOG_FILE"
      # 브랜치 정보 제거
      sed -i.bak "s/\(\*\*${issue_id}\*\*.*\) | \`\[.*\]\`/\1/" "$BACKLOG_FILE"
      echo "  ○ ${issue_id}: No branch (Open)"
    fi
  fi
done

# 3. RFC 상태 업데이트 (동일 로직)
for rfc_num in {001..020}; do
  rfc_id="RFC-$(printf '%03d' $rfc_num)"
  
  # RFC 브랜치 패턴: rfc/RFC-XXX-*
  branch=$(git branch -a 2>/dev/null | grep "rfc/${rfc_id}" | head -1 || echo "")
  
  if [ -n "$branch" ]; then
    if grep -q "\\*\\*${rfc_id}\\*\\*" "$BACKLOG_FILE" 2>/dev/null; then
      sed -i.bak "s/^- \[ \] \*\*${rfc_id}\*\*/- [\/] **${rfc_id}**/" "$BACKLOG_FILE"
      
      branch_name=$(echo "$branch" | sed 's/^[* ]*//' | sed 's|remotes/origin/||' | xargs)
      if ! grep -q "\`\[${branch_name}\]\`" "$BACKLOG_FILE"; then
        sed -i.bak "s/\(\*\*${rfc_id}\*\*.*\)$/\1 | \`[${branch_name}]\`/" "$BACKLOG_FILE"
      fi
      
      echo "  ✓ ${rfc_id}: In Progress [${branch_name}]"
    fi
  fi
done

# 4. 백업 파일 정리
rm -f "${BACKLOG_FILE}.bak"

echo "✅ Sync complete!"
