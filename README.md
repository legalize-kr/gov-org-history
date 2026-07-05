# gov-org-history

정부조직관리정보시스템의 정부기구도와 기관별기구도를 시점별 JSON/Markdown 친화 데이터로 보존하는 Legalize-KR 결과 저장소입니다.

이 저장소의 목적은 법령, 행정규칙, 정부입법, 의안 데이터에서 등장하는 기관명을 시간축 위에서 해석할 수 있게 하는 것입니다. 예를 들어 어느 날짜의 `국가보훈부`가 어떤 상위기관 아래에 있었는지, 원천이 `승격`으로 표시한 경우 관련기관이 무엇이었는지, 해당 스냅샷의 법령 근거가 무엇인지 확인할 수 있어야 합니다.

## 주요 원천

- 현재/역대 정부기구도: `https://org.go.kr/oam/gvrnOrgChartView.ifrm?flag=gov`
- 정부기구도 JSON endpoint: `POST https://org.go.kr/oam/selectGvrnOrgViewList.do`
- 시행일 목록 endpoint: `POST https://org.go.kr/oam/selectEfYdList.do`
- 기관별기구도: `https://org.go.kr/cop/bbs/getInstiChartList.do`
- 자료실: `https://www.org.go.kr/cop/bbs/selectArticleList.do?bbsId=BBSMSTR_400000010000`
- 행정기관별 조직변천: `https://org.go.kr/orgnzt/chnge/viewAdmnstMach.do`

## 데이터 구조

```text
data/
  snapshots/
    index.json
    {YYYY-MM-DD}/snapshot.json
  institutions/
    current.json
  relations/
    reorganizations.json
  reference-files/
    library.json
    admin-machinery-changes.json
sources/
  org-go-kr/
    efyd-list.json
    gvrn-org/{YYYY-MM-DD}.json
    institution-list/page-*.html
    reference-library/page-*.html
    admin-machinery-changes/page.html
schemas/
  gvrn-snapshot.schema.json
  institutions.schema.json
  reorganizations.schema.json
  reference-files.schema.json
metadata.json
stats.json
```

## 생성 방법

```bash
python3 scripts/fetch_gvrn_org.py --out . --all
python3 scripts/fetch_institution_list.py --out . --write-html
python3 scripts/fetch_reference_lists.py --out . --write-html
python3 scripts/generate_metadata.py .
python3 scripts/validate.py .
```

## 자동 업데이트

`.github/workflows/update-recent.yml`은 매주 일요일 23:30 KST에 self-hosted runner에서 실행됩니다. workflow는 최근 31일 범위의 정부기구도 스냅샷, 최신 스냅샷, 현재 기관별기구도, 자료실 및 행정기관별 조직변천 파일 목록을 비교하고, 의미 있는 변경이 있을 때만 `data/`, `sources/`, `metadata.json`, `stats.json`을 갱신해 커밋합니다.

수동으로 같은 확인을 실행할 때는 다음 명령을 사용합니다.

```bash
python3 scripts/update_recent.py --out . --lookback-days 31
python3 scripts/validate.py .
```

특정 시행일만 다시 가져올 때는 다음처럼 실행합니다.

```bash
python3 scripts/fetch_gvrn_org.py --out . --date 20260102
python3 scripts/generate_metadata.py .
python3 scripts/validate.py .
```

## 연결 정책

조직 변천 관계는 `data/relations/reorganizations.json`에 edge로 기록합니다.

| 필드 | 의미 |
|---|---|
| `source_value` | 원천 `reorganCode` 값입니다. 예: `신설`, `승격`, `개편` |
| `source_ref` | 원천 `relgoagCode` 값입니다. 코드 또는 기관명 문자열일 수 있습니다. |
| `target_org_id` | 해당 시점 스냅샷에서 변천 표시가 붙은 기관의 `orgCode`입니다. |
| `evidence.snapshot` | edge를 산출한 스냅샷 파일입니다. |

`relgoagCode`가 `국가보훈처`처럼 기관명으로 내려오거나 `1550000`처럼 코드로 내려오는 경우가 있으므로, 별도 해소 단계 전에는 `source_ref`를 확정된 조직 ID로 취급하지 않습니다.

## 설치 근거와 관련 법령

- 스냅샷 노드의 `legal_basis`는 원천 JSON의 `lsId`, `lsNm`, `lsiEfYd`에서 가져옵니다.
- 현재 기관별기구도의 `installation_basis`와 `related_laws`는 목록 페이지의 `설치근거`, `관련법령` 링크에서 가져옵니다.
- `law_go_kr_url`은 원천 링크 또는 `law.go.kr` 법령명 URL을 보존합니다. Legalize-KR 내부 법령 revision과의 확정 연결은 후속 crosswalk 범위입니다.

## 상태

초기 구성은 정부조직관리정보시스템의 공개 JSON과 HTML 목록을 보존하는 v1입니다. 법령 revision crosswalk, 첨부 파일 본문 다운로드, Markdown 보고서 생성, `legalize-web`/CLI 연동은 후속 단계로 분리합니다.
