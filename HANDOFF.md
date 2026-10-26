# DBVORA HANDOFF — 새 채팅 필수 10항

> **재개 문장**: [디비보라 깃헙보고 작업해]. 시작 즉시 CHAT_BOOTSTRAP.md를 읽고 실제 GitHub 최신 상태 검증 후 docs/NEXT_TASK.md의 첫 미완료 단위를 실행한다. 단순 'ㄱ' 역시 계속 진행 신호.

1. **목표·용도·확정 요구·기술**: 독립 로컬 설치형 DB 가시화/구조 관제/초고효율 압축·무손실 복원. 클릭형 DB/컬럼/용량 구조도, 주기적 저장 최적화. 설계 채택안은 Python 3.11+ 로컬 FastAPI·SQLite 관리 메타데이터·가벼운 SVG/웹 UI; 압축은 우선 ZSTD 등 검증된 기술 활용, 중복/증분/정책은 자체 오케스트레이션으로 확장. 실제 구현 전이다.
2. **완료·변경·선정 근거**: GitHub Private 빈 저장소에서 README 재개 진입점을 생성한 뒤 요구/운영/설계 인수인계 초기 문서 및 브랜치를 만드는 작업. 두 설계안·결정 근거는 docs/ARCHITECTURE.md, docs/DECISIONS.md. 제품 코드는 미구현.
3. **테스트·성공·실패·미검증**: 초기 설정은 원격 문서의 실제 fetch, 브랜치 검색, 최신 commit 조회로 검증한다. 현재 단위/통합/브라우저/Windows 테스트는 **0 실행 / 0 성공 / 0 실패**, 제품 미검증. 향후 명령과 성공 기준은 docs/NEXT_TASK.md.
4. **완료/진행/대기/차단·중단 지점**: README 커밋됨. 설계/문서/브랜치 최종 게시·검증 진행 중(최종 사용자 보고 확인). 다음 구현은 feature/p0-db-map의 합성 SQLite read-only 스키마 인벤토리. PostgreSQL/압축/스케줄러/상용화는 후속.
5. **오류·원인·재시도 금지·대안**: 처음 빈 저장소에서는 README 404 'This repository is empty'가 정상 관측, 코드 장애 아님. 인증 실패/파일 부재와 제품 오류 혼동 금지. GitHub 쓸 수 없을 때 실패 이유와 작업 미반영 표시 후 파일 산출물로 전환. 수집 중 live SQLite 파일 단순 복사·압축 금지. 똑같은 실패 방식 2회 반복 금지.
6. **저장소·브랜치·SHA·경로**: https://github.com/hibi89/DBVORA / Private / main(안정) / develop(통합) / feature/p0-db-map(첫 기능 예정). README 초기 커밋 9e90d4364357a39d40fc3a34237c7d5d78729c73. 이후 **HEAD는 최종 검증한 최신 SHA로 반드시 대체 확인**. 필수 경로 CHAT_BOOTSTRAP.md, AGENTS.md, REQUIREMENTS.md, STATUS.md, HANDOFF.md, docs/.
7. **운영 URL·Vercel·실행 환경**: Vercel/Production 미적용; 공식 URL 없음. 로컬 실행 목표 http://127.0.0.1:8765 (예정·미구현), Python 3.11+, Windows/Linux. 개발 의존성은 처음엔 최소화하고 유료 외부 서비스 없음.
8. **원본·백업·인증·수정 금지**: 생성 시 사용자 원본 DB/테스트 데이터 없음. Git 커밋과 브랜치로 문서 복구. 고객 파일/DB는 읽기 권한을 명시적으로 확인 후 로컬에만 유지. 비밀키·.env·실고객 기록 GitHub 금지. SQLite 백업/압축 시 원본/마지막 정상 스냅샷 절대 훼손 금지.
9. **다음 작업·순서·완료 기준·승인**: branch+remote 확인 → 합성 SQLite fixture 생성 → schema/keys/file-size 읽기 전용 수집 → 예상/미지원 지표 구분 → 결정론적 JSON output+unit tests → 최소 UI·브라우저 확인 → CI·SHA·인수인계 갱신. 실제 DB 연결, 삭제·원본 변형, 외부 비용·데이터 전송·공개는 사전 승인.
10. **갱신 시각(KST)·확인 시점·범위·문서 기준 커밋**: 2026-10-26 KST 초기 부트스트랩. 마지막 GitHub 검증·커밋 SHA는 아래 또는 종료 보고에서 최신값 확인. 문서 작성 자체는 제품 완성 아님. 차기 채팅에서 최신 원격 SHA와 테스트 실행 결과를 추가 기록한다.

## 복원 우선순위
현재 이 채팅의 최종 사용자 보고에서 확인된 SHA/브랜치를 기준으로 삼되 새 채팅은 원격을 다시 검증. 장기 비전보다 docs/NEXT_TASK.md의 최소 실제 코드 구현·테스트를 우선. 사용자를 로컬 반복노동에 동원하지 않는다.
