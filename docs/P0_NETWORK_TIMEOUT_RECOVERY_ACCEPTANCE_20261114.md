# DBVORA P0 — 네트워크 단절·지연·15초 타임아웃 복구 수용증거

- 기준일: 2026-11-14 KST
- 정본: `hibi89/DBVORA@feature/p0-db-map`
- **기능 소스 SHA**: `38798bf0819c329c3f92defa8cfe9c9885d73022`
- 범위: 127.0.0.1 실제 HTTP 서버 + 실제 임시 합성 SQLite(1,000테이블, 997개 FK) + Chromium. 고객 DB/장치 접근 없음.
- 운영 변경은 `dbvora/web/app.js`의 **refresh** 경로로 제한. 기존 읽기 전용 inventory/REST API·백업/CAS·레이아웃/카드/관계도는 불변.

## 원인과 대안 비교

기존 `refresh()`는 `await fetch('/api/inventory')`에 시간 제한이 없어 응답이 무기한 멈추면 새로고침 버튼이 계속 비활성화될 수 있었다.

| 후보 | 비용·성능 | 안전성·유지보수 |
| --- | --- | --- |
| A. 서버/API에 강제 전체 요청 타임아웃, 전체 페이지 자동 재로딩 | 서버 변경 필요·동시 사용자/대용량 작업 동작 영향, 재조회/추가 DB 읽기 | 검색·인스펙터·마지막 정상 구조도 리셋 위험, 전체 API 회귀 필요 |
| **B. 클라이언트 요청별 15초 AbortController와 중복요청 방지** | 외부 서비스·유료 과금 0, 현행 조회 비용 그대로 | 오류 시 직전 정상 구조·검색·선택 보존, 재시도 버튼 복귀, 서버/DB 코드 미수정 |

**B 채택.** 15초가 지나면 브라우저의 단일 해당 요청을 Abort하고, 친숙한 오류 메시지를 제공한 뒤 `Refresh`를 재활성화한다. 네트워크 TypeError/AbortError도 경로 노출 대신 중단 안내. 타임아웃 timer는 완료 시 항상 해제. 동시에 또 refresh 함수를 호출하더라도 기존 작업 완료 전 새 요청·오래된 응답이 발생하지 않도록 guard 사용.

## 정확한 검증

- `scripts/browser_http_e2e.py`에 실제 Chromium 3종 추가. 실제 localhost 서버/합성 SQLite를 쓰되 **Playwright의 지정된 라우트 하나에만 장애 주입**:
  1. `route.abort('failed')`로 연결 단절 → 오류 배너·버튼 활성·기존 1,000테이블/검색/선택/observer 유지 → 라우트 해제 후 실제 200 API 복구
  2. `route.continue_()` 전 0.6초 인위적 지연 → 실제 HTTP200, 상태 불변·가짜 타임아웃 없음
  3. 요청 라우트를 미응답 상태로 유지 → 브라우저 자체 **15초 AbortController** 타임아웃, 오류 표시/버튼 재활성화 → 라우트 해제 후 정상 HTTP200·관계선 997개 복구
- 각 시나리오에서 테스트 DB 원본 SHA256 및 mtime 무변경, 필터 하나만 노출, aria-pressed 한 개, 오류 후 재시도, 활성 observer 1·resize listener 1을 확인. DOM/JS 오류 부재 및 기존 HTTP503/HTTP422 거부 시나리오도 통과해야 최종 PASS.
- `tests/test_ui_dom.cjs` 실제 네트워크 예외 시 오류/최종 구조/필터 유지와 복구 확인, `tests/test_ui_large_dom.cjs`에 타이머/AbortController 노드 테스트 환경만 지원. HTML/브라우저 자산에 새 종속성 없음.

## 원격 검증 증거 (정확 기능 SHA)

- [실제 Chromium Windows2025+Ubuntu24.04 #43584055932](https://github.com/hibi89/DBVORA/actions/runs/43584055932): **양 OS 20/20 PASS**, `PASS_SYNTHETIC_HTTP_BROWSER_ONLY`; +3 시나리오 포함.
- [전체 릴리스 #43584055935](https://github.com/hibi89/DBVORA/actions/runs/43584055935): Ubuntu24.04 **714/714 PASS / 0FAIL / 0SKIP**, 필수12/12 PASS. Windows2025: **최종 결과 확인 대기**.
- [최종설계 증거정책 #43584056105](https://github.com/hibi89/DBVORA/actions/runs/43584056105): SUCCESS (공식 사용자 최종설계 점수 산정/구매자 수용 승인 아님).
- Git commit 작성자/커미터: 연결된 `hibi89`; 확인 메일은 비밀이 아니지만 재공개하지 않음.
- 브라우저 20회 체크는 네트워크 장애 시의 짧은 기능 회귀이며 **장기 heap·실 고객 환경/물리적인 라우터 단절·실 사용자 Windows10 성능을 보증하지 않음**.

## 출시·데이터 안전 경계

- 원본 고객 DB, 고객 백업, 토큰, .env, Vercel, 라이선스, 권한, 가격, 도메인, main/develop 변경0.
- 공식 최종설계 `UNASSESSED` (과거 내부 기술95 기록), `[작업중]`, `RELEASE HOLD`, 크몽 실등록0, Vercel/Production 미적용.
- 다음 `ㄱ` 후보: 1,000테이블 실제 Chromium 장시간 반복 렌더/heap 관측·장애 후 이벤트/observer 누적, 또는 사용자 최종설계별 수용 잔여 항목 정리. 프로그램 완성/상업 출시 무검증을 GO로 표기 금지.
