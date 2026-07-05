# gov-org-history 작업 규칙

이 저장소는 정부조직관리정보시스템의 정부기구도, 기관별기구도, 역대정부기구도, 자료실 파일 목록, 행정기관별 조직변천 파일 목록을 보존하는 Legalize-KR 결과 저장소입니다.

## 원칙

- 공식 원천 URL, 원천 필드명, 원문 식별자를 가능한 한 보존합니다.
- `selectGvrnOrgViewList.do`의 `reorganCode`와 `relgoagCode`는 변천 관계의 evidence입니다. `relgoagCode`는 코드 또는 기관명 문자열로 내려올 수 있으므로, 별도 해소 전에는 확정된 org id로 과장하지 않습니다.
- 설치근거와 관련법령은 기관별기구도 목록의 `설치근거`, `관련법령` 링크를 우선 보존하고, 스냅샷 노드의 `lsId`, `lsNm`, `lsiEfYd`는 해당 스냅샷의 법령 근거로 보존합니다.
- 첨부 파일은 URL과 원천 첨부 ID만 먼저 기록합니다. 파일 본문을 저장소에 넣기 전에는 재배포 가능 여부와 파일 형식을 별도로 확인합니다.
- 생성 스크립트를 바꿨다면 `python3 scripts/validate.py .`를 실행합니다.

## 데이터 변경 범위

- 구조화 데이터는 `data/` 아래에 둡니다.
- 원천 응답과 HTML 보존본은 `sources/org-go-kr/` 아래에 둡니다.
- 수작업 보정이 필요하면 원천 필드와 보정 사유를 함께 남깁니다.

## 조회 방법

- 특정 시점의 정부기구도는 `data/snapshots/index.json`에서 `effective_date`를 찾고, `data/snapshots/{YYYY-MM-DD}/snapshot.json`의 `nodes`를 조회합니다.
- 조직 변천은 `data/relations/reorganizations.json`을 조회합니다. `source_value`는 원천 `reorganCode`, `source_ref`는 원천 `relgoagCode`, `target_org_id`와 `target_name`은 변천 표시가 붙은 대상 조직입니다.
- `relgoagCode`는 코드 또는 기관명 문자열일 수 있으므로, 별도 해소 전에는 `source_ref`를 확정된 조직 ID로 단정하지 않습니다.
- 현재 기관별 설치근거와 관련 법령은 `data/institutions/current.json`의 `installation_basis`와 `related_laws`를 확인합니다.
- 자료실 첨부 목록은 `data/reference-files/library.json`, 행정기관별 조직변천 파일 목록은 `data/reference-files/admin-machinery-changes.json`을 확인합니다.
- 단순 조회는 기존 `data/`를 우선 사용합니다. 최신 원천 반영이 필요한 경우에만 수집 스크립트를 실행하고, 마지막에 `python3 scripts/generate_metadata.py .`와 `python3 scripts/validate.py .`를 실행합니다.

## 주기 업데이트

- `.github/workflows/update-recent.yml`은 매주 일요일 23:30 KST에 self-hosted runner에서 실행됩니다.
- workflow는 `python3 scripts/update_recent.py --out . --lookback-days 31`로 최근 31일 범위의 스냅샷, 최신 스냅샷, 기관별기구도, 자료실, 행정기관별 조직변천 목록을 비교합니다.
- 의미 있는 변경이 있을 때만 `data/`, `sources/`, `metadata.json`, `stats.json`을 갱신하고 `data: 정부조직 이력 주간 업데이트` 커밋을 생성합니다.
