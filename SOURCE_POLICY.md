# Source Policy

`gov-org-history`는 공식 공개 원천을 기준으로 생성합니다.

## 보존 원칙

- `orgCode`, `orgNm`, `upOrgCode`, `rootOrgCode`, `efYd`, `edYd`, `reorganCode`, `relgoagCode`를 핵심 원천 필드로 보존합니다.
- 원천 JSON의 법령 필드(`lsId`, `lsNm`, `lsiEfYd`, `lsiSeq`)는 스냅샷별 설치 근거 후보로 보존합니다.
- 기관별기구도 목록의 `설치근거`와 `관련법령` 링크는 현재 기관 단위 근거로 보존합니다.
- 자료실과 행정기관별 조직변천 파일은 제목, 게시글 ID, 첨부 ID, 다운로드 URL만 보존합니다.

## 재배포와 첨부 파일

정부조직관리정보시스템 HTML/JSON에서 제공되는 구조화 메타데이터는 출처와 fetch 시각을 함께 기록합니다. HWP/PDF/XLSX 등 첨부 파일 본문은 초기 v1에서 자동 다운로드하지 않습니다. 파일 본문을 저장소에 포함하려면 각 파일의 이용 조건, 형식, 크기, 저작권 표시를 별도로 확인하고 결과를 문서화해야 합니다.

## 원천 URL

| 데이터 | 원천 |
|---|---|
| 시행일 목록 | `POST https://org.go.kr/oam/selectEfYdList.do` |
| 정부기구도 노드 | `POST https://org.go.kr/oam/selectGvrnOrgViewList.do` |
| 기관별기구도와 근거 링크 | `https://org.go.kr/cop/bbs/getInstiChartList.do` |
| 자료실 파일 목록 | `https://www.org.go.kr/cop/bbs/selectArticleList.do?bbsId=BBSMSTR_400000010000` |
| 행정기관별 조직변천 파일 목록 | `https://org.go.kr/orgnzt/chnge/viewAdmnstMach.do` |

