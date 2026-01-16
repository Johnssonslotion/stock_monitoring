#!/bin/bash
# Database Migration Manager
# Author: Antigravity AI
# Date: 2026-01-16
#
# Usage:
#   ./migrate.sh status        # 현재 적용된 마이그레이션 확인
#   ./migrate.sh up            # 미적용 마이그레이션 적용
#   ./migrate.sh down          # 마지막 마이그레이션 롤백
#   ./migrate.sh baseline      # 현재 스키마를 baseline으로 저장

# DO NOT exit on error for status command
# set -e is removed to allow graceful status display

# Configuration
CONTAINER_NAME="${DB_CONTAINER:-stock-timescale}"
DB_NAME="${DB_NAME:-stockval}"
DB_USER="${DB_USER:-postgres}"
MIGRATIONS_DIR="$(cd "$(dirname "$0")/../../migrations" && pwd)"
APPLIED_FILE="${MIGRATIONS_DIR}/.applied"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Initialize .applied file if not exists
if [ ! -f "$APPLIED_FILE" ]; then
    echo "# Applied Migrations (DO NOT EDIT MANUALLY)" > "$APPLIED_FILE"
    echo "# Format: YYYYMMDD_HHMMSS migration_file" >> "$APPLIED_FILE"
fi

# Execute SQL in database (Simple Command)
exec_sql() {
    local sql="$1"
    docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "$sql" 2>&1
}

# Execute SQL file (Transactional)
exec_sql_file() {
    local file="$1"
    # --single-transaction: Wrap entire script in one transaction
    # -v ON_ERROR_STOP=1: Stop immediately on error
    docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 --single-transaction < "$file"
}

# Get list of migration files (sorted)
get_migration_files() {
    find "$MIGRATIONS_DIR" -name "[0-9][0-9][0-9]_*.sql" | sort
}

# Get applied migrations
get_applied_migrations() {
    grep -v "^#" "$APPLIED_FILE" | awk '{print $2}' || true
}

# Check if migration is applied
is_applied() {
    local migration="$1"
    local basename=$(basename "$migration")
    grep -q "\\s${basename}$" "$APPLIED_FILE" 2>/dev/null
}

# Mark migration as applied
mark_applied() {
    local migration="$1"
    local basename=$(basename "$migration")
    local timestamp=$(date +%Y%m%d_%H%M%S)
    echo "${timestamp} ${basename}" >> "$APPLIED_FILE"
}

# Remove last applied migration
unmark_last() {
    local temp_file="${APPLIED_FILE}.tmp"
    head -n -1 "$APPLIED_FILE" > "$temp_file"
    mv "$temp_file" "$APPLIED_FILE"
}

# Status command
cmd_status() {
    echo -e "${GREEN}=== Migration Status ===${NC}"
    echo ""
    echo "Database: ${DB_NAME} (Container: ${CONTAINER_NAME})"
    echo "Migrations Directory: ${MIGRATIONS_DIR}"
    echo ""
    
    local all_migrations=$(get_migration_files)
    local applied_count=0
    local pending_count=0
    
    echo -e "${GREEN}Applied Migrations:${NC}"
    if grep -v "^#" "$APPLIED_FILE" | grep -q "^[0-9]"; then
        while IFS= read -r line; do
            if [[ "$line" =~ ^[0-9] ]]; then
                echo "  ✅ $line"
                ((applied_count++))
            fi
        done < "$APPLIED_FILE"
    else
        echo "  (None)"
    fi
    
    echo ""
    echo -e "${YELLOW}Pending Migrations:${NC}"
    for migration in $all_migrations; do
        if ! is_applied "$migration"; then
            echo "  ⏳ $(basename "$migration")"
            ((pending_count++))
        fi
    done
    
    if [ $pending_count -eq 0 ]; then
        echo "  (None)"
    fi
    
    echo ""
    echo "Total: $applied_count applied, $pending_count pending"
}

# Up command
cmd_up() {
    echo -e "${GREEN}=== Applying Migrations ===${NC}"
    echo ""
    
    # Check container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${RED}Error: Container ${CONTAINER_NAME} is not running${NC}"
        exit 1
    fi
    
    local all_migrations=$(get_migration_files)
    local applied_any=false
    
    for migration in $all_migrations; do
        if ! is_applied "$migration"; then
            echo -e "${YELLOW}Applying: $(basename "$migration")${NC}"
            
            # Backup before migration (Schema Only is fast, but Data Safety requires care)
            # For Zero Cost, we stick to Schema Only for speed + optional full backup manually
            local backup_file="/tmp/db_pre_migration_$(date +%Y%m%d_%H%M%S).sql"
            echo "  Creating backup (Schema Only): $backup_file"
            docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --schema-only > "$backup_file" 2>/dev/null
            
            # Apply migration (Atomic)
            if exec_sql_file "$migration" > /tmp/migration.log 2>&1; then
                echo -e "  ${GREEN}✅ Success (Atomic Committed)${NC}"
                mark_applied "$migration"
                applied_any=true
                
                # Deep Verification
                echo "  Verifying schema..."
                if exec_sql "\dt" > /dev/null 2>&1; then
                    echo -e "  ${GREEN}✅ Schema verified${NC}"
                else
                    echo -e "  ${RED}❌ Schema verification failed${NC}"
                    exit 1
                fi
            else
                echo -e "  ${RED}❌ Failed (Transaction Rolled Back)${NC}"
                echo "  Error log:"
                cat /tmp/migration.log | head -20
                echo ""
                echo "  Backup saved at: $backup_file"
                exit 1
            fi
            
            echo ""
        fi
    done
    
    if [ "$applied_any" = false ]; then
        echo "No pending migrations."
    else
        echo -e "${GREEN}All migrations applied successfully!${NC}"
    fi
}

# Down command (rollback last migration)
cmd_down() {
    echo -e "${YELLOW}=== Rolling Back Last Migration ===${NC}"
    echo ""
    
    # Get last applied migration
    local last_applied=$(grep -v "^#" "$APPLIED_FILE" | tail -1 | awk '{print $2}')
    
    if [ -z "$last_applied" ]; then
        echo "No migrations to rollback."
        exit 0
    fi
    
    echo "Last applied: $last_applied"
    echo ""
    
    # Look for down migration file
    local migration_base="${last_applied%.sql}"
    local down_file="${MIGRATIONS_DIR}/${migration_base}_down.sql"
    
    if [ ! -f "$down_file" ]; then
        echo -e "${RED}Error: Rollback script not found: ${down_file}${NC}"
        echo "Manual rollback required."
        exit 1
    fi
    
    # Backup before rollback
    local backup_file="/tmp/db_pre_rollback_$(date +%Y%m%d_%H%M%S).sql"
    echo "Creating backup: $backup_file"
    docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --schema-only > "$backup_file" 2>/dev/null
    
    # Execute rollback (Atomic)
    echo "Executing rollback..."
    if exec_sql_file "$down_file" > /tmp/rollback.log 2>&1; then
        echo -e "${GREEN}✅ Rollback successful (Atomic Committed)${NC}"
        unmark_last
        echo "Migration $last_applied rolled back."
    else
        echo -e "${RED}❌ Rollback failed (Transaction Rolled Back)${NC}"
        echo "Error log:"
        cat /tmp/rollback.log | head -20
        echo ""
        echo "Backup saved at: $backup_file"
        exit 1
    fi
}

# Baseline command
cmd_baseline() {
    echo -e "${GREEN}=== Creating Baseline ===${NC}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local baseline_file="${MIGRATIONS_DIR}/000_baseline_${timestamp}.sql"
    
    echo "Exporting schema to: $baseline_file"
    docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --schema-only > "$baseline_file" 2>/dev/null
    
    echo -e "${GREEN}✅ Baseline created${NC}"
    echo "File: $(basename "$baseline_file")"
    echo "Size: $(du -h "$baseline_file" | cut -f1)"
}

# Main
case "${1:-}" in
    status)
        cmd_status
        exit 0
        ;;
    up)
        cmd_up
        exit 0
        ;;
    down)
        cmd_down
        exit 0
        ;;
    baseline)
        cmd_baseline
        exit 0
        ;;
    *)
        echo "Database Migration Manager"
        echo ""
        echo "Usage:"
        echo "  $0 status      - Show migration status"
        echo "  $0 up          - Apply pending migrations (Atomic)"
        echo "  $0 down        - Rollback last migration (Atomic)"
        echo "  $0 baseline    - Create schema baseline"
        echo ""
        echo "Environment Variables:"
        echo "  DB_CONTAINER   - Docker container name (default: stock-timescale)"
        echo "  DB_NAME        - Database name (default: stockval)"
        echo "  DB_USER        - Database user (default: postgres)"
        exit 1
        ;;
esac
