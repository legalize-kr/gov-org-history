# Limitations

## 현재 한계

- `relgoagCode`는 기관 코드와 기관명 문자열이 섞여 내려올 수 있습니다. v1은 이 값을 그대로 보존하고, 확정된 전후 기관 ID 매핑은 하지 않습니다.
- 기관별기구도는 현재 목록 기준입니다. 과거 시점의 기관별 상세 설치근거는 정부기구도 스냅샷의 법령 필드와 별도로 crosswalk해야 합니다.
- 자료실과 행정기관별 조직변천의 첨부 파일 본문은 다운로드하지 않습니다. 현재는 파일 목록과 다운로드 URL만 보존합니다.
- 법령 근거는 `law.go.kr` URL 또는 법령명 수준입니다. `legalize-kr` 특정 revision과의 exact/date-scoped 연결은 후속 작업입니다.
- 조직의 분할/통합은 `reorganCode`와 `relgoagCode` evidence를 보존하는 수준입니다. 여러 선행 기관이 하나로 합쳐지는 복합 edge는 첨부 문서나 법령 개정 이력을 추가로 확인해야 합니다.

## 검증 기준

v1 데이터는 다음 조건을 만족해야 합니다.

- `python3 scripts/validate.py .` 통과.
- 스냅샷마다 `node_count`와 실제 `nodes` 길이가 일치.
- 각 노드의 `parent_id`가 같은 스냅샷 안에 존재하거나 비어 있음.
- 각 노드가 하나 이상의 `legal_basis`를 가짐.
- 현재 기관별기구도 항목이 `installation_basis`와 `related_laws`를 가짐.

