# DBVORA P0 — 실제 Chromium 1,000테이블 24회 반복 사용 및 GC 후 힙 관측

- 기준: 2026-11-14 KST
- 제품 저장소: `hibi89/DBVORA@feature/p0-db-map`
- 정확한 테스트 소스: `10b4c46769199a1153088b138dd404f307b0b651`
- 코드 변경: `scripts/browser_http_e2e.py`의 합성 브라우저 종단 검증에 **2개 체크 추가**. 운영 UI/API/백업 원본 코드는 변경하지 않음.

## 방법 비교

| 방법 | 비용·실행 | 안전성과 검증 범위 |
| --- | --- | --- |
| A. 운영 UI에 새 메모리 추적 모듈을 포함해 장기 실사용 데이터를 수집 | 개인정보·보안/성능 부담 및 배포 검증 확대 | 제품 행동에 영향, 고객 데이터/기기 필요 가능 |
| **B. 기존 실제 Chromium 종단 테스트에서 CDP로 GC/JS 힙 계측** | 기존 GitHub 무료 CI, browser-side only, 추가 서비스/계정 없음 | 1회 headless synthetic 환경 수치만 얻음; 장기 누수 부재의 인증은 아님 |

**B 선택.** 실제 localhost 합성 SQLite 1,000테이블·997 FK → HTTP Inventory → 실제 Chromium DOM/선택/그래프 흐름을 그대로 재사용함.

## 회귀 조건

1. Chromium 1440×900, 실제 합성 SQLite 한 파일. 24회 반복해서 각기 다른 생성 테이블을 검색하고, 키보드 Enter로 선택한 다음 서버에 실제 GET `/api/inventory` refresh. 응답 완료 뒤 검색어와 aria pressed·인스펙터 연동 확인, 필터 해제 후 SVG 997개 복구.
2. 6번째 주기마다 Playwright 브라우저 요청에만 `route.abort('failed')` 주입해 합계 **4회 네트워크 중단**. 정상 UI 보존과 200 응답 재조회/오류 해제 필수. 실 서버와 합성 DB 자체에 장애를 주입하거나 파일을 수정하지 않음.
3. **매 주기 확인:** DOM button=1,000, SVG path=997, aria-pressed=1, `ResizeObserver` 활성=1/최대=1, resize listener=1, observer created=disconnected+1. 전체 DOM 노드 수는 초기 개수에서 ±30개 이내; 원본 SQLite SHA256+mtime 불변.
4. `Chrome DevTools Protocol` `HeapProfiler.collectGarbage` → `Performance.getMetrics` `JSHeapUsedSize`를 시작/8/16/24회 종료 시 측정. 1회 실행 내 순증가 24 MiB 초과만 gross-growth HOLD. 이 상한값은 수용 실험용 광범위 이상징후 가드이지 **장기 성능 SLA나 메모리 누수 없음의 증명이 아님**.
5. 기존 실제 브라우저 회귀(HTML, 키보드, XSS, HTTP503, HTTP422, 15초 timeout/abort, 모바일 390px, 원본변경0)도 전체 완료해야 PASS.

## 실제 GitHub Actions 결과

- [실 Chromium #43586399733](https://github.com/hibi89/DBVORA/actions/runs/43586399733): Ubuntu24.04, Windows2025 각 **22/22 PASS**. 정확한 source SHA 동일.
- [전체 릴리스 #43586399633](https://github.com/hibi89/DBVORA/actions/runs/43586399633): 양 OS **2/2 SUCCESS**, Python714 발견 / Ubuntu714 PASS, 0FAIL·0SKIP / Windows713 PASS, 0FAIL, 1 POSIX-only SKIP `test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`, 양 OS mandatory12/12.
- [최종설계 증거 게이트 #43586399936](https://github.com/hibi89/DBVORA/actions/runs/43586399936): SUCCESS (공식 최종설계 100점이나 구매자 수용은 아님).

| 1회 실행의 CDP GC 후 JS 힙 실측 | Ubuntu | Windows |
| --- | ---: | ---: |
| 시작 | 3,200,520 B | 3,231,760 B |
| 8회 | 3,277,784 B | 3,285,276 B |
| 16회 | 3,299,004 B | 3,300,028 B |
| 24회 | 3,288,340 B | 3,301,908 B |
| 24회 순증가 | **87,820 B** | **70,148 B** |
| 시작 DOM 노드 | 7,123 | 7,123 |
| 중간 가상 연결중단 | 4회 | 4회 |

**해석:** 이 두 GitHub 표준 러너의 짧은 Headless Chromium 24회 시험에서는 큰 잔류 힙 증가, 리스너·관찰자 누적, DOM/그래프 누적이 재현되지 않았다. 반복 사용 데이터에 관한 추가 증거일 뿐, 실제 사용자 PC 성능·장기간 반복·특정 메모리 leak 부재·실DB와 물리 정전 안전성은 별도 미검증.

## 상태와 다음 작업

- 공식 사용자 최종설계 완성률: `UNASSESSED` (과거 내부 기술 범위 95는 이력값).
- 중앙 원장: `[작업중]` / `RELEASE HOLD` / 실제 크몽 등록 0.
- Production/Vercel: 설치형 로컬 제품으로 `미적용`.
- 이번 작업 중 고객 DB, 실제 백업 원본, 권한·토큰·env, 외부 업로드, 유료 서비스·상업 판매와 배포를 변경하지 않았음.
- 다음 `ㄱ` 우선순위는 최종 확정 `REQUIREMENTS.md` 대비 미검증 항목과 P100 수용 근거 정리 후, 독립적으로 검증 가능한 고위험 구현 잔여 작업을 우선순위화. 사용자의 PC나 고객 실데이터 필요 작업은 별도 보류.
