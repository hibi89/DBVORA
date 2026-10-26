# DBVORA Chat Bootstrap — 최우선 재개 지침

## 정확한 호출 문구
[디비보라 깃헙보고 작업해]

동일 의미의 [DBVORA 깃헙 레포지토리 보고 작업이어가셈]도 허용. 사용자 'ㄱ'은 다음 미완료 작업 진행 신호.

## 새 채팅 실행 순서 (질문 없이 진행 가능한 범위)
1. GitHub 연결 저장소 hibi89/DBVORA 및 Private 여부, 권한, 기본/개발/작업 브랜치와 최신 HEAD SHA를 실제 조회한다. 과거 요약을 최신으로 추정하지 않는다.
2. main의 이 파일 → 해당 개발 브랜치의 HANDOFF.md → STATUS.md → AGENTS.md → REQUIREMENTS.md → docs/DECISIONS.md → docs/ARCHITECTURE.md → docs/COMPRESSION_PLAN.md → docs/NEXT_TASK.md → 실제 소스/테스트를 순서대로 연다. 초기에는 모든 문서가 같은 내용으로 분기되어 있을 수 있다.
3. 앞선 단위 완료 여부(코드, CI, 테스트, 실제 동작)를 증거로 재검증하고 중복 개발을 하지 않는다. 문서와 코드가 다르면 실검증 결과를 우선한다.
4. 첫 미완료 SAFE 단위는 docs/NEXT_TASK.md에 있다. 현재 작업 브랜치는 feature/p0-db-map이며, 다음 변경 역시 검증 가능한 작은 단위로 최소 변경·합성 데이터 테스트를 직접 구현한다. 가능한 도구로 실행해 통과/실패/미검증을 명확히 기록한다.
5. 필요한 경우 PR로 develop에 검증 후 반영한다. main은 검증된 안정 기준으로 두고, 승인 없는 강제 병합·force push·권한/공개 변경은 하지 않는다.
6. 주요 구현 및 새 채팅 이관 전에 STATUS.md·HANDOFF.md·NEXT_TASK.md를 GitHub에 갱신하고 새 커밋 SHA와 확인 시점(KST)을 보고한다. 최신 문서 기준 브랜치를 명시한다.

## 작동 원칙
- ChatGPT 총괄이 직접 설계/코드/테스트/검수한다. 사용자에게 대신 복붙/로컬 실행을 시키지 않는다. 사용자 기기·인증에만 가능한 단계는 BLOCKED로 남긴다.
- 유료 사용, 원본 변형·삭제, 실사용 DB 접근, 고객 데이터 외부 전송, 배포, 브랜드·라이선스/권한 변경은 명시적인 사전 승인 필요.
- 저장소 코드는 실고객 비밀·DB 원본·벤치마크 대용량 원본을 포함하지 않는다.
- GitHub 변경과 로컬/브라우저/Production 검증을 구분한다. 현재 Vercel은 미적용.
- REA_APP은 앱 기술 역설계 도구이며 DBVORA 오케스트레이터가 아니다.

## 확인 시점에 따른 상태

- feature/p0-db-map: P0-01 SQLite read-only 인벤토리 및 P0-02 FastAPI localhost 웹 UI 파일·테스트 구현. Python unittest 28/28, Node DOM 시뮬레이션 1/1, 실제 localhost HTTP 200/403, wheel 정적 파일 포함 확인.
- Chromium 탐색은 현 작업환경 managed policy URLBlocklist '*'로 차단돼 실브라우저 E2E 미검증. Chrome 제한을 우회하지 말고 Windows/승인된 브라우저 환경에서 추후 검증.
- Python 3.11, Windows, 실고객 DB, live WAL 및 복원/압축 미검증. 외부 배포·Vercel 미적용.
- 코드/UI 사용 안내는 docs/P0_02_USAGE.md. 다음 안전한 개발은 docs/NEXT_TASK.md의 합성 SQLite C0 스냅샷 실험; 브라우저 검증은 별도 BLOCKED 기록을 유지. 이미 완료한 P0-01/02를 재구현하지 말 것.
