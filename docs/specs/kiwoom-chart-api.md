# Kiwoom Tick Chart REST API Specification

**API Name**: 주식틱차트조회 (Stock Tick Chart Query)
**API ID**: `ka10079`
**Endpoint**: `/api/dostk/chart` (Full: `https://api.kiwoom.com/api/dostk/chart`)
**Method**: POST
**Format**: JSON
**Content-Type**: application/json;charset=UTF-8

---

## 2. Request Specification

### Headers
| Header | Value | Required | Description |
|--------|-------|----------|-------------|
| `authorization` | `Bearer {token}` | Y | OAuth2 Access Token |
| `api-id` | `ka10079` | Y | **Critical**: Must match API ID |
| `User-Agent` | Mozilla/5.0... | Y | **Critical**: Required to bypass WAF |
| `cont-yn` | `N` (First) / `Y` (Next) | N | Continuity flag |
| `next-key` | String | N | Generic Key for pagination (from Response Header) |

### Body
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stk_cd` | String(20) | Y | Stock Code (e.g. "005930") |
| `tic_scope` | String(2) | Y | Tick Scope: "1"=1tick, "3"=3ticks... |
| `upd_stkpc_tp` | String(1) | Y | Adjusted Price: "0" or "1" |

---

## 3. Response Specification

**Fields**:
- `stk_tic_chart_qry` (List):
    - `cntr_tm`: Execution Time (HHMMSS)
    - `cur_prc`: Current Price
    - `trde_qty`: Volume (Transaction Qty)
    - `open_pric`, `high_pric`, `low_pric`
    - `pred_pre`: Price Change

---

## 4. Verification Strategy
1. Request `tic_scope="1"` (1 Tick Chart).
2. Count the number of items in `stk_tic_chart_qty` list for the target time window (e.g. 09:00:00 ~ 09:05:00).
3. Compare this count with DB row count.
