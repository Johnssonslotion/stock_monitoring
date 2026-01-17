# [Module/Feature Name] Specification

**Version**: 1.0  
**Date**: YYYY-MM-DD  
**Author**: [Persona]

---

## 1. Overview (개요)
이 모듈/기능의 목적과 범위를 설명합니다.

**Purpose**: [왜 이 모듈이 필요한가?]  
**Scope**: [어디까지 커버하는가?]

---

## 2. Interface (인터페이스)

### 2.1 Public API / Functions

#### Function: `function_name()`
```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    간단한 설명
    
    Args:
        param1 (Type1): 파라미터 설명
        param2 (Type2): 파라미터 설명
    
    Returns:
        ReturnType: 반환값 설명
    
    Raises:
        ExceptionType: 예외 발생 조건
    """
```

**Behavior**: [함수의 동작 설명]

### 2.2 REST API Endpoints (해당 시)
```yaml
GET /api/v1/resource
```
- **Request**: [요청 형식]
- **Response**: [응답 형식]
- **Auth**: [인증 필요 여부]

---

## 3. Data Structures (데이터 구조)

### 3.1 Input Schema
```json
{
  "field1": "string",
  "field2": 123,
  "field3": ["array"]
}
```

**Swagger/OpenAPI** (선택):
```yaml
components:
  schemas:
    ResourceSchema:
      type: object
      properties:
        field1:
          type: string
```

### 3.2 Output Schema
[출력 데이터 형식 정의]

### 3.3 Database Schema (해당 시)
```sql
CREATE TABLE table_name (
  id SERIAL PRIMARY KEY,
  column1 VARCHAR(255),
  column2 TIMESTAMPTZ
);
```

---

## 4. Edge Cases (예외 상황 처리)

| Scenario | Expected Behavior |
|:---|:---|
| Null/None 입력 | [처리 방법] |
| 빈 배열/리스트 | [처리 방법] |
| 타임아웃 | [처리 방법] |
| 네트워크 장애 | [처리 방법] |
| 잘못된 데이터 타입 | [처리 방법] |

---

## 5. Dependencies (의존성)

### External Libraries
- `library_name==1.0.0`: [용도]

### Internal Modules
- `src/module/component.py`: [용도]

### External Services
- Redis: [용도]
- TimescaleDB: [용도]

---

## 6. Constraints (제약사항)

- **Performance**: [성능 요구사항]
- **Resource**: [리소스 제한]
- **Security**: [보안 고려사항]

---

## 7. Examples (사용 예시)

### Example 1: Basic Usage
```python
result = function_name(param1="value", param2=123)
```

### Example 2: Error Handling
```python
try:
    result = function_name(...)
except SpecificException as e:
    # Handle error
```

---

## 8. References
- Related RFC: [링크]
- Related Specs: [링크]
- External Docs: [링크]
