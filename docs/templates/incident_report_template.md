### [ERR-XXXX] [Short Error Title]

- **Last Updated**: YYYY-MM-DD
- **Severity**: [Critical / High / Medium / Low]
- **Components**: [e.g., Collector, Redis, DB]

#### 1. 증상 (Symptoms)
- **Log Pattern**:
  ```text
  [ERROR] Connection refused...
  ```
- **User Impact**: [e.g., Real-time map stopped updating]

#### 2. 원인 (Root Cause)
- [Brief explanation of why this happened]

#### 3. 해결 절차 (Resolution) &mdash; *Copy & Paste Ready*
**Step 1: 빠른 복구 (Mitigation)**
```bash
# 명령어 1
docker restart [container_name]
```

**Step 2: 심층 분석 (Investigation)**
```bash
# 명령어 2
docker logs --tail 100 [container_name]
```

**Step 3: 영구 해결 (Fix)**
- Patch: [Link to Commit/PR]
- Config: 변경된 설정 값 (`ENV_VAR=VALUE`)

#### 4. 재발 방지 (Prevention)
- [ ] Add monitoring alert (Sentinel)
- [ ] Add regression test
