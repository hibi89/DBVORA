# DBVORA P0 — 반복 새로고침·API 오류 복구·Observer 수명 실브라우저 수용 증거

- 기준일: 2026-11-14 KST
- 정본: `hibi89/DBVORA@feature/p0-db-map`
- 정확한 **테스트 소스 SHA**: `d5780ceece92f28508712aa2cdd2a6228c7e137c`
- 변경: `scripts/browser_http_e2e.py`에 실제 임시 SQLite→localhost API→Chromium 검증 3건 추가. **운영 코드 변경 없음**.
- 공식 최종설계: `UNASSESSED`; `[작업중]`, `RELEASE HOLD`, 실제 크몽 등록 0을 그대로 유지.

## 설계 비교와 선택

| 비교 | A. 화면 전체 재로드·프런트 리팩터링 | B. 현재 상태 유지·실브라우저 결함 재현 |
|---|---|---|
| 사용자 상태 | 전체 리셋·검색/선택 손실 위험 | 기존 선택·필터·인스펙터 지속 검증 |
| 성능 | 화면과 API 전부 다시 시작 | 기존 증분 새로고침 경로 그대로 사용 |
| 현금 비용 | 새 서비스는 불필요하나 재작성/검증 시간 큼 | GitHub Actions/Playwright 기존 무료 스택 |
| 보안/원본 | 기존 UX·읽기 전용 계약 변경 가능 | 임시 합성 SQLite·localhost만 접근 |
| 유지보수 | 광범위 회귀 필요 | 기존 테스트 하네스에 한정 |

**B 선택**. 실제 결함이 재현되기 전 운영 UI 동작을 불필요하게 고치지 않는다.

## 검증 내용

1. **반복 6회:** 1,000개 테이블·997개 FK를 실제 SQLite 파일에서 읽은 뒤 Refresh 6회. 각 회마다 버튼 1,000개, SVG path 997개, 선택된 버튼 1개, 인스펙터·검색어, 오류상태 확인.
2. **누적 탐지:** 페이지 초기화 전에 native `ResizeObserver`·window resize 이벤트 등록만 계측. 생성된 observer = disconnect + 1, 활성 관찰 1, 동시에 활성화된 최대치 1, resize listener 1을 6회 모두 요구. **장기 힙 사용량 또는 운영 중 메모리 누수가 전혀 없다는 보증은 아님**.
3. **장애 주입:** 실제 로컬 서버나 DB 수정 없이 Playwright HTTP route에만 JSON HTTP503 응답을 임시 삽입. 마지막 정상 구조도·선택·검색을 보존하고, route 제거 후 HTTP200 수신/오류 배너 해제/관계선 997개 복구를 확인.
4. **모바일 회귀:** 실제 API 1,000테이블 표시 직후 390×844 화면에서 가로 넘침 없음, 버튼1,000·SVG997·새로고침 활성 확인.
5. **원본 보존:** 모든 반복·503 주입 전후 합성 SQLite의 SHA256+mtime 동일. 1001테이블은 기존대로 HTTP422 `CATALOG_LIMIT`; 테스트 생성 마지막 테이블만 DROP한 뒤 복구 확인.

## 정확한 원격 실행 증거

| 게이트 | Ubuntu 24.04 | Windows 2025 |
|---|---|---|
| [실제 Chromium #43576063961](https://github.com/hibi89/DBVORA/actions/runs/43576063961) | 17/17 PASS | 17/17 PASS |
| [전체 릴리스 #43576063937](https://github.com/hibi89/DBVORA/actions/runs/43576063937) | Python710 PASS·FAIL0·SKIP0·필수12/12 PASS | **현재 결과 확인 대기** |
| [설계 증거 #43576064144](https://github.com/hibi89/DBVORA/actions/runs/43576064144) | SUCCESS | workflow 단위 SUCCESS |

Chromium 양 OS 모두 `PASS_SYNTHETIC_HTTP_BROWSER_ONLY`. 성공한 단일 호출 샘플: Linux API72.292ms/browser ready203.113ms; Windows API94ms/browser ready187ms. 일반 고객 PC의 성능·연속 24시간 메모리 안전성 보증 아님.

## 잔여 작업 및 HOLD

- Windows 전체 릴리스 결과·정확 SHA 확인 후 STATUS/HANDOFF/NEXT_TASK 및 해총 중앙 원장에 확정 증거 반영.
- 별도 브라우저 프로세스 장기 스트레스·실 고객 Win10/11 PC 검증, API 연결 손실/지연(503 외), P3 **별도 프로세스** CAS 경합, 물리 정전 복원은 미검증.
- 고객 실DB·백업·고객 로컬경로·환경변수·토큰·상업 배포·main/develop 변경 없음.
- 실서비스/유료/사용자 기기/사용권·최종 100점 수용에는 추가 승인 필요. 크몽 상품 등록은 현재 범위 밖.
