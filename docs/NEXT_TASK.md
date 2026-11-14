> **[2026-11-14 KST · P3 multi-process CAS exact source verified, next independent work]** Code/test [`c1f41fdb32fd`](https://github.com/hibi89/DBVORA/commit/c1f41fdb32fde48e316b1f4b98336734e903e4a5); [full gate](https://github.com/hibi89/DBVORA/actions/runs/43576862756) Windows/Linux 2/2 SUCCESS, 712 tests discovered / Ubuntu712PASS/Windows711PASS+1 named POSIX SKIP / mandatory12/12 each; [blueprint evidence](https://github.com/hibi89/DBVORA/actions/runs/43576863080) SUCCESS. New true spawn-worker same new chunk no-replace publication contest and same manifest concurrent restore, old generation sha preserved, both created outputs independent, zero orphan stage after clean termination. Operational CAS unchanged and no customer data. **Next `ㄱ`:** P3 simulated abrupt process exit during partial chunk/manifest staging then old generation restore + orphan read-only audit/manual HOLD; no physical power outage certification, no automatic cleanup. Compare subprocess crash test vs new global OS locking; prefer synthetic crash test if current logic safely fail-closes. Other alternative: P0 actual browser network timeout/abort (beyond HTTP503) and long-term memory observation. Official UNASSESSED/[작업중]/RELEASE HOLD/registrations0 retained.
>
> **[2026-11-14 KST · Next after P0 refresh/recovery PASS]** Exact test source `d5780ceece92`; [Ubuntu/Win real Chromium 17/17×2](https://github.com/hibi89/DBVORA/actions/runs/43576063961); [full gate 710 discovered (Linux710PASS, Win709PASS+1POSIX SKIP) / 12 mandatory each](https://github.com/hibi89/DBVORA/actions/runs/43576063937). 새 3건: 실제 SQLite1000/997 FK 6회 refresh와 observer/resize 등록 소유권, API HTTP503 상태유지→정상 복구, 390px 모바일 폭. 운영 변경0, 임시 합성 DB SHA/mtime 불변. **다음 모바일 `ㄱ`: P3 별도 프로세스 동일 청크 게시/세대복원 경쟁 테스트**; (A) 대규모 운영 락 도입은 플랫폼별 위험이 크고 (B) 기존 atomic no-replace 구조에 멀티프로세스 임시 합성 회귀 추가를 우선 비교·채택. 성공 시 Windows/Linux exact SHA와 고객 데이터/정전 제외 경계 문서화. 이후 P0 지연/연결단절·장기 메모리 스트레스. 공식 최종설계 UNASSESSED/과거 기술95, [작업중]/RELEASE HOLD/크몽 등록0 유지.
>
> **[2026-11-14 KST · P0 real 1,000-table SQLite end-to-end completed]** source `a0d710127cbc` [full #43573784544](https://github.com/hibi89/DBVORA/actions/runs/43573784544) Win+Ubuntu 2/2 SUCCESS (Python710 발견/Ubuntu710PASS/Win709PASS+1POSIX SKIP, mandatory12/12×2), [actual Chromium #43573784521](https://github.com/hibi89/DBVORA/actions/runs/43573784521) 각14/14. 임시 합성 실제 DB의 스키마 1000/997FK → API634619 bytes → Chrome 표시·검색·키보드·복구, 1001은 HTTP422/CATALOG_LIMIT로 명확히 거부하고 하나 제거 뒤 회복. 고객 하드웨어 속도 주장 금지. **다음 `ㄱ`**: P0 여러 번 refresh/error recovery/오버스펙 대형 catalog 표시 안정성·접근성, P3 다중 프로세스 경합 여부를 비용·위험 비교하고 필요한 최소 회귀. 출시·라이선스/구매자 실기기·실고객DB·물리 정전은 미검증. Official UNASSESSED/과거 내부95, [작업중]/RELEASE HOLD/등록0 유지.
>
> **[2026-11-14 KST · P0 1,000-table synthetic frontend verification completed]** source `8b2a23f1c7c8`, [Win/Linux full #43571467225](https://github.com/hibi89/DBVORA/actions/runs/43571467225) 2/2 SUCCESS (Ubuntu709PASS/Win708PASS+1POSIX SKIP, mandatory12/12×2), [real Chromium #43571467265](https://github.com/hibi89/DBVORA/actions/runs/43571467265) 각10/10. 1000 client-only tables+999 links render/selection/local filter/empty/reset preserved; selection no graph re-render; one run metrics render57–60ms; customer HW perf not certified. **다음 `ㄱ` 독립 작업:** read-only synthetic SQLite **실제 1,000 tables**를 생성·API inventory에 연결하여 full server→browser 종단 검증하고, 1,001개는 안전 LIMIT로 거부되는지 검증. 브라우저 인메모리 1000 테이블 결과를 이를 대신한 것처럼 주장 금지. 기존 real customer/Windows10/라이선스/실판매/정전 승인 요청 금지. 공식 UNASSESSED/[작업중]/RELEASE HOLD/등록0 유지.
>
> **[2026-11-14 KST · P3 synthetic concurrent CAS gate PASS]** Code `60e99bb40d55` [full #43569112618](https://github.com/hibi89/DBVORA/actions/runs/43569112618) Windows/Linux 2/2 SUCCESS, discovered709/Linux709PASS/Win708PASS+1 POSIX SKIP, mandatory12/12 each. 새 2-thread 동일 새 청크 게시 경합·동시 복원·중복키 오염 거부 3회귀; 처음 Windows 테스트 경로조건 불일치 #43568460809, 진단 #43568761086에서 발견→새 first-staging barrier로 수정 검증. **다음 독립 작업:** P0 클라이언트 로컬 테이블 1,000개 상한에서 DOM/검색·FK graph 갱신 비용과 0건/접근성 회귀 검증. 실제 고객/다중 프로세스/물리정전·상업 출시 제외. 공식 UNASSESSED/`[작업중]`/RELEASE HOLD/크몽 등록0 유지.
>
> **[2026-11-14 KST · P3 short-write fail-closed source `0abe50bbd219` 검증 완료]** [GitHub OS gate #43567268531](https://github.com/hibi89/DBVORA/actions/runs/43567268531) Win+Ubuntu 2/2 SUCCESS, Python706 discovered, Linux706PASS/Win705PASS+1 POSIX-SKIP, mandatory12/12. 초기 Windows 실패 #43566541865 및 진단 #43566989375는 테스트 injection 선택기 문제이며 최종 수정 SHA 확인; 불필요한 과거 SHA 재실행 금지. **다음 우선순위:** 동시 chunk publish 경합 및 이전 정상 세대 불변의 합성 재현, UI 1000테이블 제한 안의 레이아웃/필터 성능 회귀. 실제 고객 DB/정전·상업 승인/크몽 등록 제외. 최종 P100 UNASSESSED, `[작업중]`, RELEASE HOLD/등록0 유지.
>
> **[2026-11-14 KST · P3 다세대 회귀 완료 이후]** source `7e3ba31590d9`, [Windows/Linux full #43565286637](https://github.com/hibi89/DBVORA/actions/runs/43565286637) 2/2 SUCCESS, 총703 발견/Win702PASS+1POSIX SKIP/Ubuntu703PASS, mandatory12/12 each. 새 4건 실제 합성 악성 시나리오(4세대 복원/최신청크 손상/새 manifest 게시실패/감사 manifest 교체) 검증. **재검증 반복 대신 다음 독립 작업:** P3 여러 백업 세대에 대한 부분 파일 쓰기/경합 경계와 미검증 리소스·UI 크기 검증 또는 상품 최종설계 요구 항목/권리 목록 검토. 실제 고객 PC/데이터/전원차단/판매 작업 제외. Official P100 UNASSESSED, `[작업중]`, RELEASE HOLD, 등록0 유지.
>
> **[2026-11-14 KST · P3 manifest identity race guard 완료]** source `0caf6080eceb` [full #43562802300](https://github.com/hibi89/DBVORA/actions/runs/43562802300) Ubuntu699PASS, Windows698PASS+POSIX전용1SKIP, 12/12 ×2. 동일 크기·mtime을 가진 manifest로 교체되는 합성 TOCTOU는 FD+inode/ctime 교차검증으로 HOLD. **다음 우선순위:** 합성 CAS v2 여러 세대의 장기 생성·복원·읽기전용 감사와 손상·동시 실행 시 이전 정상 세대 보존을 회귀로 강화. 크몽 실제 등록·실 고객데이터·PC 사용자 지시 없음. 공식 P100 UNASSESSED, `[작업중]`, RELEASE HOLD 유지.
>
> **[2026-11-14 KST · frontend filter exact SHA 검증 후 독립 작업]** [`d52b75d90f16`](https://github.com/hibi89/DBVORA/commit/d52b75d90f1674e2357458c7bfbc22c4f2edb569)의 테이블 필터, 검색 0건, 관계선 감춤/복구, 검색어 재조회 유지, XSS 비실행 DOM 회귀가 Ubuntu/Windows 전체 698 discovered·12/12 mandatory 및 Chromium 각 9/9로 PASS([full](https://github.com/hibi89/DBVORA/actions/runs/43562375829), [browser](https://github.com/hibi89/DBVORA/actions/runs/43562375838)). **다음 AI 작업은 P3 합성 데이터 장기 복구체인·관측 안전성** 검토 후 실제 미검증 지점을 최소 구현 및 검증. 신규 PC 작업 요청 금지. 공식 P100 UNASSESSED/[작업중]/RELEASE HOLD/등록0 보존.
>
> **[2026-11-14 KST · R02 동일 프로세스 자원 변화량 신규 구현/검증 완료]** 기능+테스트 SHA [`6b9d7700b529`](https://github.com/hibi89/DBVORA/commit/6b9d7700b529f7cf00e38f6410d94d412a04f9da), [Windows2025·Ubuntu24.04 전체 릴리스 #43561622382](https://github.com/hibi89/DBVORA/actions/runs/43561622382) **2/2 SUCCESS**, Python **698개 발견**, Ubuntu **698 PASS/0FAIL/0SKIP**, Windows **697 PASS/0FAIL/1 POSIX 전용SKIP**, 필수 게이트 **12/12 × OS**. `dbvora.process_resources`의 `observe()`에 일시적 프로세스 식별과 PID 추가, `compare_local_samples()`는 같은 프로세스의 실제 CPU 누적시간/상주 RAM **두 시점 차이만** 제공. 별도 프로세스·잘못된 식별/시간·비교불가 RAM은 `unavailable`; DB 서버 CPU/RAM·호스트 CPU 사용률 및 예측 **계산하지 않음**. 로컬 CLI `--sample-interval-ms 100..5000`으로 동일 실행 내 관측. 외부 호출/파일쓰기/자동 스케줄러/고객자료0. **Windows 최초 #43560870440 실패**, [진단 #43561330045](https://github.com/hibi89/DBVORA/actions/runs/43561330045)로 실측 두 호출이 같은 단조시계 tick인 것을 확정, 테스트에서 실제 시계간격을 주도록 고쳐 제품 HOLD 규칙 유지, 최종 PASS. [설계·범위](docs/R02_SAME_PROCESS_RESOURCE_TREND_20261114.md). 사용자 이전 Windows 실제 합성 ZIP/Chrome 검수 근거는 유지되며 **새 CLI의 사용자 PC 직접 실행은 별도 미검증**. 공식 최종설계 **UNASSESSED**(내부 과거95는 이력), `[작업중]`·RELEASE HOLD·실 크몽 등록0·Production 미적용. 사용자 외출 후 폰 `ㄱ`으로 다음 개발 재개; 추가 PC 지시 없음.
>
## 2026-11-14 R02 검증 후 독립 개발 우선순위
- **재실행 금지:** local same-process CPU/RAM 2-sample exact SHA `6b9d7700b529` Windows/Linux 698 tests discovered, 12/12 stages each PASS. Initial Windows equal-clock-tick diagnostic cause isolated/fixed in tests; production HOLD unchanged.
- **다음 AI 직접 작업:** P3 고객자료 없이 합성 아카이브/복원 장기 안전성, 타임아웃/관측범위·용량 변화와 현재 사용자 실제 UI 검수 반영 대조. 필요한 실제 코드/테스트/브라우저 증거만 인정.
- **사용자에게 PC 추가 요청 없음:** 신규 CLI owner Win10 사용 자체는 아직 미실행이므로 NOT VERIFIED. 사용자가 외출 중이라면 폰 `ㄱ`만으로 개발 재개. 크몽 실제 등록 제외.
- **최종 상태:** official UNASSESSED/과거 내부95 이력, `[작업중]`, RELEASE HOLD, 등록0, Vercel/Production 미적용.

> **[DBVORA 최신 기능·검증 2026-11-14 KST]** source SHA `fdbf9ed34b932d220220fd1b13abb616389a37ea` [Windows2025·Ubuntu24.04 full gate #43555133875](https://github.com/hibi89/DBVORA/actions/runs/43555133875) **2/2 SUCCESS**, Python **688 discovered**, Linux **688PASS/0FAIL/0SKIP**, Windows **687PASS/0FAIL/1 POSIX 전용SKIP**, 각 OS mandatory **12/12 PASS**. **합성 compressed CAS v2 read-only 감사**: 명시한 기존 폴더만 조사, 각 zlib 청크·두세대 명세 전체 SHA256 확인, 누락/파손/미사용·임시파일을 별도 HOLD, **자동 삭제·복구·예약·고객 데이터 접근 없음**. 최초 Windows CI는 `DirEntry.stat`의 Windows 불완전한 하드링크 수로 7개 실패했고 `os.lstat`으로 고친 뒤 정확 소스 재실행 PASS. Windows 10/11 사용자 실기기와 물리 정전·고객 DB·상업 라이선스/NOTICE·가격/지원/환불/구매자 수용은 **미검증**. [unsigned synthetic-only 개발 ZIP 63파일 #43555133878](https://github.com/hibi89/DBVORA/actions/runs/43555133878), 안쪽 `dbvora-dev-preview-0.2.0.zip` SHA-256 `3edcfa008318454fffc5775731599250520142b6e636b0b7e00d15d2b732ed74`, 소스 SHA 일치(7일 보존). **공식 P100 UNASSESSED, 내부 과거95% 별도 기록, [작업중]/RELEASE HOLD/크몽 등록0/Production 미적용**. 오늘 13:00 FFAX·ASTRA·DATA2WEB·DBVORA 통합 사용자 요청 자동화 실제 **completed**, 동일 요청 재발송 금지.

## [2026-11-14 최신 후속 우선순위]
- **완료/재실행 불필요:** source `fdbf9ed34b932d220220fd1b13abb616389a37ea` 원본 전체 검증(688 discovered, Linux688PASS/Win687PASS+1named SKIP, 12/12 per OS); synthetic read-only CAS audit (missing/corrupt/orphan/staging) + cross-OS filesystem fix; 실제 로컬 PG16 TLS5/5, Chromium8/8×2 이전 별도 정확 SHA, 단일 ZIP vs zlib CAS 공간·속도 모두 기록.
- **AI가 다음에 할 일:** 배포 대상 사용성·읽기전용 검사 표기 및 구매자 QA 가이드 정비, 회귀 테스트 범위와 최종설계 수용요건 대조. 물리전원·실고객·판매용 EXE/라이선스 무검증 결과는 HOLD로 유지.
- **사용자 전용:** 13:00 KST 통합 4제품 알림은 실제 완료(휴대폰 승인/귀가 PC). 같은 작업 중복 요청 금지, 소유자 안전한 Win10 검수 및 판매/권리/요구 가중치 승인 전까지 100% 주장 금지.

> **[정본 우선: 2026-11-14 KST / 소스 SHA `2011d5fda1bd3d91b0010b5901fdf6149e0a31cc`]** [Windows2025·Ubuntu24.04 전체 릴리스 #43553401567](https://github.com/hibi89/DBVORA/actions/runs/43553401567) **양OS 2/2 SUCCESS**: Python **677개 테스트 발견**, Ubuntu **677 PASS/0 FAIL/0 SKIP**, Windows **676 PASS/0 FAIL/1 POSIX-only SKIP**, 필수 릴리스 단계 **12/12 PASS ×2**. 신규 R02 `dbvora.process_resources`가 명시한 로컬 볼륨 디스크 total/free, **DBVORA Python 프로세스 누적 CPU 시간과 현재 프로세스 resident RAM**을 실제 OS 관측값+출처/범위와 함께 제공하며 원격 DB/PG 서버 CPU·RAM은 **null/미지원**으로 두어 추정치 오인 방지. 원본 ZIP/ZSTD, 증분 raw v1/zlib v2, ENOSPC·서브프로세스 중단 테스트, 실제 임시 PG16 verify-full TLS5/5, Windows/Linux Chromium8/8 이력 보존. 동일 합성 2세대 벤치에서 Linux ZIP vs zlib 저장15.261/19.920ms·복원7.168/8.137ms, Windows 저장86.893/245.156ms·복원47.808/66.871ms 단일 샘플; zlib은 공간 절감하나 속도 느린 결과, 일반화 금지. [최신 synthetic-only 미서명 포터블 **62파일** GitHub ZIP #43553401541](https://github.com/hibi89/DBVORA/actions/runs/43553401541) 내부 ZIP SHA256 `1c1b4a395a7ee21fbd2cd8127aea479c55be0755284988f36d70fd998e5b8e38`(기능 소스 SHA 일치). 공식 사용자 최종설계 **P100 UNASSESSED**, 과거 내부 기술범위95 역사, **[작업중]/RELEASE HOLD/실 크몽 등록0**, Vercel/Production **미적용**. 사용자 Windows10/11 실기기·물리 전원차단·고객 DB/실서비스 PG·LICENSE/NOTICE/지원/환불/가격/실상품 등록 미승인. 사용자 요청은 **오늘 13:00 KST FFAX·ASTRA·DATA2WEB·DBVORA 통합 알림 1회**에서 폰/PC 분리. 데이터·비밀 외부반출0, 유료결제0.

## 2026-11-14 신규 R02 처리 및 다음 실행 순서
- **검증완료**: local Python process CPU-cumulative/resident RAM (Linux /proc/self/statm, Windows PSAPI) + selected local volume total/free 실제 관측. DB 서버 지표는 명시적으로 null. Windows+Linux 677 test discovery / 12 mandatory stages SUCCESS at SHA `2011d5fda1bd3d91b0010b5901fdf6149e0a31cc`. 최신 owner preview 62파일 [Actions](https://github.com/hibi89/DBVORA/actions/runs/43553401541) / inner sha `1c1b4a395a7ee21fbd2cd8127aea479c55be0755284988f36d70fd998e5b8e38`.
- **AI 독립 후속**: 2시점 로컬 process CPU 사용시간 증가와 source별 trend 미확정 표시, 실제 Win10/11 판매 데모/지원 문서 검수, 드라이브 통계가 SQLite 파일의 사용량이 아님을 GUI에도 계속 명시, 암호화/서명/물리정전은 무단 구현/인증 주장 불가.
- **13:00 KST 사용자 통합 (PC/폰 분리)**: owner Win10 QA 및 라이선스/제품 품질·가중100 승인·크몽 등록 조건만 묶어 1회 요청. 지금 고객 DB·token·유료결제·실물 정전시험 요구 없음.
- **상태**: official P100 UNASSESSED, historical internal95, [작업중]·RELEASE HOLD 유지.

> **[2026-11-14 KST 최신 기능/CI | 판매 승인 전]** source `ff20658b2d9db099eea6386d354e90f5c0dc5264`; [Windows2025+Ubuntu24.04 전체 CI #43552745227](https://github.com/hibi89/DBVORA/actions/runs/43552745227) 양쪽 **SUCCESS**, Python **671개 발견** / Linux **671 PASS, 0 FAIL, 0 SKIP** / Windows **670 PASS, 0 FAIL, 1 POSIX전용 SKIP**, 필수 **12/12 PASS ×2**. 같은 합성 SQLite 2세대에서 ZIP/rawCAS/zlibCAS 저장·복원 6개 실행 경로의 **실제 단일 wall-clock 시간 측정(평균/성능보증 아님)**과 저장 바이트 검증 PASS. Linux ZIP 저장 15.261ms, zlib v2 저장 19.920ms; ZIP 복원 7.168ms, zlib v2 복원 8.137ms. Windows ZIP 저장 86.893ms, zlib v2 저장 245.156ms; ZIP 복원 47.808ms, zlib v2 복원 66.871ms. Linux ZIP2 31,216B vs compressed CAS24,637B; Windows ZIP2 31,550B vs compressed CAS25,046B (**특정 합성 예시**). 단일 측정에서 zlib이 더 느렸으며 속도/효율 우월 일반화 금지. 기존 PG16 verify-full TLS·Chromium·실 자식 프로세스 중단·ENOSPC·주간 UTC 합성 reservation PASS 근거 유지. **공식 최종설계 P100 UNASSESSED**, 역사 내부95 별도, `[작업중]`·RELEASE HOLD·크몽 등록0·Production 미적용. 소유자 실제 Windows10/11 / 물리적 전원단절 / 고객DB 및 라이선스·NOTICE·지원/환불·가격·판매 사용승인 **미검증**. 0원·고객정보 외부전송0. 사용자 할 일은 기등록 **2026-11-14 13:00 KST 통합 알림**에서 한 번에 폰/PC 분리해 안내.

## 2026-11-14 최신 작업 우선순위 (source `ff20658b2d9db099eea6386d354e90f5c0dc5264`)
- **이미 검증된 재반복 금지**: Windows/Linux 각각671개 발견 테스트(Win670PASS+1 named skip)/12단계, 실 PG16 localhost verify-full TLS read-only5/5, 실제 Chromium8/8×2, 합성2세대 실제 ZIP/raw/zlib 저장/복원 및 6개 wall-clock timing single-sample. 무조건 속도절감 주장 금지.
- **AI 독립 작업 가능**: 장기 관측/메모리·CPU 출처 표준 표시, 경로·파일크기 실패안전 회귀, 별도 사용자용 synthetic-only 워크플로 문서 보강.
- **소유자만 가능한 13:00 일괄 요청**: 집 Windows10/11 새 ZIP 해시·오프라인 HTML 실기기 검수, 실제 물리 전원손실 테스트는 복구 계획 승인 뒤, 고객 라이선스/권리·제품 옵션·가격·지원·환불·최종 요구사항 가중치·실 크몽 등록. 외출중 PC 요청·고객 DB 업로드·유료 지출 금지.
- **공식 완성률 UNASSESSED**, P100 목표 유지; [작업중]/RELEASE HOLD/실 등록0.

> **[DBVORA 최신 정본 · 2026-11-14 KST · 사용자 P100 목표 진행 중]** 전체 기능/CI source `c9823a3d48c4c8507c8c4c61ca3328d92674b3d4`, [GitHub Windows2025·Ubuntu24.04 #43551764326](https://github.com/hibi89/DBVORA/actions/runs/43551764326) **2/2 SUCCESS**; Python **669개 발견**(Linux **669 PASS/0FAIL/0SKIP**, Windows **668 PASS/0FAIL/1 POSIX전용SKIP**), 최소 강제 커버리지 **668개**, 매 OS 필수 게이트 **12/12 PASS**. 추가된 기술: 합성 v2 CAS 중간 ENOSPC·게시 실패 **8개**, 실제 자식 프로세스 `os._exit` 중단 후 기존 복구 보존 **2개**, UTC ISO week별 별도 예약·주/일 ledger 안전재사용·인수 CLI 인자 경로 비노출 **7개 + 기준 강화 검증 1개**; 고객 실제 물리 전원차단 재현 아님. 기존 raw CAS v1·압축 v2·ZIP/ZSTD·PG16 localhost verify-full TLS/Chromium 합성 검증 이력 보존. [최신 사용자 검수용 unsigned 61파일 source ZIP #43551568838](https://github.com/hibi89/DBVORA/actions/runs/43551568838) code `7b9ee1e2ccb05fad64bd171cf858ce401c9da0fe` 안쪽 ZIP SHA-256 `8b53688aa371fb75b12130f9c323f035294735157555a0001789ac25be167ae1` (7일 보존); 이후 `c9823a3d48c4`의 변경은 검증기/단위시험 커버리지이며 위 61개 포터블 소스 구조는 이전 SHA에서 테스트됨. **공식 P100 UNASSESSED**(과거 내부 기술범위95 별도), **[작업중]/RELEASE HOLD/실 크몽 등록0**, Production/Vercel 미적용; Windows10/11 소유자 실기기·물리정전·고객DB·판매권/NOTICE/지원/가격/최종 사용자 수용 미검증. 0원/실고객 데이터 외부전송0. 오늘 **13:00 KST 기존 1회 통합 알림**에서만 사용자 할 일을 요청한다.

## 2026-11-14 최우선 다음 과제 (CI source `c9823a3d48c4c8507c8c4c61ca3328d92674b3d4`)
- **다시 하지 말 것**: 669 발견/양OS CI 12/12 PASS, local PG16 verify-full 5/5, chromium Windows/Linux 8/8, ZIP/CAS 원본 복원 및 합성2세대 용량측정, v2 ENOSPC 8개·실 자식-process exit 2개, daily/weekly ISO-week 원장, CLI 옵션 비노출, 최신 unsigned source ZIP 준비.
- **독립 개발 가능한 후속**: 읽기 전용 메트릭의 실제 관측 범위(지원 CPU/RAM vs unavailable) 재정리, 증분 저장-복원 시간 및 IO·메모리 A/B 정량화(합성 전용), 가독성·실제 사용자 워크플로 실기기 검증 준비. 보안/고객 데이터 제한 완화 금지.
- **13시 소유자 통합 요청**: 휴대폰으로 라이선스/상업조건·100점 요구 수용 결정, PC 귀가 후 안전한 unsigned ZIP SHA 검증과 합성 HTML 화면 1회 확인, 물리 정전/OS 복구는 별도 승인된 계획 후만. 신용카드·고객 DB·유료 기능·외부 업로드 없음.
- **판정**: 공식 UNASSESSED(과거 내부95), [작업중], RELEASE HOLD, 크몽 등록0, Production 미적용. 신규 소스 SHA의 GitHub 합성 PASS를 고객/전원손실 PASS로 승격하지 않음.

> **[최신 정본 2026-11-14 KST | 100% 목표 계속 · 판매 보류]** 기능·정식 합성 검증 SHA `9d24a58a045fd89a11d46c685ee59adec3ed63e8`. [Windows2025+Ubuntu24.04 전체 release #43549905413](https://github.com/hibi89/DBVORA/actions/runs/43549905413) **2/2 SUCCESS**: Ubuntu Python3.11 **651 PASS/0FAIL/0SKIP**, Windows2025 **650 PASS/0FAIL/1 POSIX-only SKIP**, **12/12 필수 단계/OS**, 실제 raw CAS v1+압축 CAS v2 CLI 독립 복원·중복 재사용·변조/형식오인 차단 12/12, 같은 합성 SQLite 2세대 ZIP/raw/zlib 크기·복원 실측 11/11. Linux ZIP 31,216B vs raw CAS 1,177,960B vs zlib CAS **24,637B**(-6,579B, -21.1% *해당 합성 데이터에 한정*); Windows ZIP31,550B, raw CAS1,177,960B, zlib CAS **25,046B**(-6,504B). PostgreSQL16 로컬 실제 verify-full TLS/read-only/FK/통계/HTML·불량 CA 거부 [5/5 #43545900975](https://github.com/hibi89/DBVORA/actions/runs/43545900975). 실제 Windows/Linux Chromium localhost 8/8×2 [#43544065399](https://github.com/hibi89/DBVORA/actions/runs/43544065399). Windows2025 PyInstaller *합성-only·미서명* EXE 실제 실행 [#43546585469](https://github.com/hibi89/DBVORA/actions/runs/43546585469). [최신 소스 ZIP #43549905406](https://github.com/hibi89/DBVORA/actions/runs/43549905406) **61파일/내부 ZIP SHA `b86b65c666af8d5bd0262bbec37bf8cf465391d8f22b518f976efc3d28bc7183`**, 7일 보존. **공식 전체 P100 UNASSESSED**, 과거 내부95는 기록만, **[작업중]/RELEASE HOLD/크몽 실등록0**, Production/Vercel **미적용**. 구매자 Windows10/11 실기기·물리 전원중단·고객 DB/PG 연결 환경·저작권/LICENSE/NOTICE/지원·환불/가격·가중치 수용승인 미검증. 유료지출0, 비밀·실고객 원본 업로드0. 사용자에게 필요한 일은 **13:00 KST 기존 통합 1회 알림**에만 전달.

## 2026-11-14 KST — 다음 작업 우선순위 (최신 SHA `9d24a58a045fd89a11d46c685ee59adec3ed63e8`)
- **완료, 반복 금지:** 로컬 임시 PG16 verify-full/least-privilege 실제 연결 5/5, 무료 Windows+Linux 651회 테스트/12단계, 실제 localhost Chromium 8/8×2, unsigned 합성 데모 Windows 실행, raw/zlib CAS CLI 12체크·3형태 2세대 복원·실측 11체크. 소스 변경 시 해당 SHA의 필수 CI 결과 재확인.
- **AI 독립 작업 우선:** 저장공간 부족/시간제한·후처리 실패시 *이전 정상 세대 보존*하는 합성 회귀 보강, 별도 압축/복원 속도 측정(성능과 용량 tradeoff), P100 요구 추적/상품 초안/권리 고지 최신화. 신규 기능을 고객상용 완성으로 승격 금지.
- **사용자 전용 13:00 통합 알림:** Win10/11 실제 1회 합성 전용 화면/안전 다운로드/SmartScreen 우회 없는 승인, 실제 사용권·저작권/제3자 종속성·가격·지원·환불·크몽 상품 게시, 100점 사용자 수용 가중치, 라이브 고객자료 없이 재현 가능한 합성/독립 QA. 불필요한 외출 중 PC 조작/유료결제/데이터 전송 요구 금지.
- **검증 한계:** v2 압축 CAS는 특정 합성 세대에서 Linux ZIP31,216B vs zlib CAS24,637B, Windows ZIP31,550B vs zlib CAS25,046B. 무조건적 절감·정전보장·실고객 DB 적합성 주장 금지. 공식 P100 UNASSESSED, [작업중]과 RELEASE HOLD 유지.

> **2026-11-14 KST — unsigned owner preview build exact SHA verified:** `3835a53de75f5de4e1d2ddd3c895377b83d45112`, [Actions](https://github.com/hibi89/DBVORA/actions/runs/43544666021), 56파일 개발자 preview ZIP 자체 SHA-256 `e7a6d46099c170cc8e0f70b098dd6a86d47c5678b0ff51bc3cfa7225fa0426f1`, 합성-only 패키징/검증 PASS. 매니페스트 미서명/고객 readiness false, 실제 사용자 Win10에서 압축해제·검증 스크립트/오프라인 HTML 눈검수 전까지 판매 승인 금지. [최소 1회 QA 문서](docs/OWNER_WINDOWS_QUICK_QA_20261114.md), 기존 full source clone 심층 QA는 선택 사항. 크몽 상품 설명은 실검증범위만; 13시 사용자 작업 통합 알림 설정 완료. P100 [작업중]/UNASSESSED/RELEASE HOLD, 등록0, 운영 서비스/Vercel 미적용. 기존 10항 인수인계 보존.

> **[2026-11-14 KST — Chromium 실제 localhost Windows+Ubuntu 8/8 통과]** 추가 클라우드 Windows·Linux 실제 Chromium HTTP 8/8×2 SUCCESS, `a982508160a3085e12e3663f1df9979dac4e9cae`, [Actions](https://github.com/hibi89/DBVORA/actions/runs/43544065399). 다음 GPT 작업은 상업 종속성/권리/지원 안내 및 최종설계 추적표 갱신, 일반 소비자 실제 Windows 실기기는 **2026-11-14 13:00 KST 통합 사용자 알림**까지 사용자 요청 보류. 실 PG TLS, 물리 전원중단, 사용자 Win10, 고객 인수·상업권리/가격·등록은 미검증. P100 [작업중]/RELEASE HOLD, 공식 UNASSESSED.

## 2026-11-14 KST — 최신 병렬 브라우저 양OS 2/2 PASS
- 코드 SHA eab26716e25e8c55b120d295110be2f754b6aa5e, docs full-gate c730c6912dc3635a8f8a56504116b9cbed5039a3 [2/2 PASS](https://github.com/hibi89/DBVORA/actions/runs/43543990300), 브라우저 workflow SHA a982508160a3085e12e3663f1df9979dac4e9cae [Win/Linux 2/2, 각 8/8 PASS](https://github.com/hibi89/DBVORA/actions/runs/43544065399), 합성 화면 PNG 4장 (7일 아티팩트).
- **NEXT 미완료:** 소유자 Windows10 실사용 1회 [QA](OWNER_WINDOWS_QUICK_QA_20261114.md), PG TLS 합성 실제 서버 승인, 배포·라이선스/가격/지원/고객 승인, 공식 최종설계 가중치 수용. [작업중]·공식 UNASSESSED·RELEASE HOLD 유지.
## 2026-11-14 KST — P100 최초 미완료 작업(합성 전체 CI + 실 Chromium 완료)
- 검증된 기능 소스 SHA eab26716e25e8c55b120d295110be2f754b6aa5e: Windows2025 **616 PASS/0 FAIL/1 POSIX 0600 SKIP, 10/10 gate PASS**, Ubuntu24.04 **617 PASS/0 FAIL/0 SKIP, 10/10 gate PASS** [full](https://github.com/hibi89/DBVORA/actions/runs/43543367368); 실제 Chromium localhost **8/8 PASS**, 합성 desktop/mobile PNG 2개 GitHub Actions 7일 보존 [browser](https://github.com/hibi89/DBVORA/actions/runs/43543367417).
- **NEXT 1:** 소유자 Windows10에서 합성-only full gate·오프라인 HTML 클릭 검수 1회. 외출 중 PC 조작 필요 없음. [실행 가이드](OWNER_WINDOWS_QUICK_QA_20261114.md).
- **NEXT 2:** 승인된 격리 synthetic PG 실서버에서 verify-full TLS/read-only 연결(비밀·실고객 공유 금지). 그 전 PG 판매 보장 금지.
- **NEXT 3:** 상업 LICENSE/NOTICE·고객 배포 형태(개발 ZIP != 설치 EXE)·지원/환불 및 가격 확정, 크몽 단일 상품 초안 최종 확인. 등록실적 0, 출시 HOLD.
- **NEXT 4:** 사용자 확정 최종설계 전체 요구/가중치 100점 수용표 검증 후 공식 점수 계산(현행 UNASSESSED, 과거 내부95 별도). [작업중] 지우지 말 것.

## 2026-11-14 KST — 사용자 최종설계 P100 지시(기존 P95 완료와 별개)
- 최초 미완료 단위: **원격 정본 전체 소스 자동 검증**. `.github/workflows/dbvora-release-gate.yml` 신설, GitHub-hosted Ubuntu 24.04 / Windows 2025 Python3.11 + Node22의 `python -m scripts.verify_release_gate` 실제 결과/커밋 확인.
- 이후 Windows 사용자 실기기→합성 PostgreSQL TLS read-only(별도 승인·무비밀 공유)→법적 라이선스/고객 인수/판매 GO. 이전 P95는 내부범위 기록, **공식 최종 100점 UNASSESSED**, 판매 HOLD.
- 검증 근거/실행 지시와 A/B 비용 선택은 `docs/DBVORA_P100_ACCEPTANCE_20261114.md`. 이 문서/CI만으로 점수 또는 100%를 올리지 않는다.

## 2026-11-13 KST — DBVORA P95 내부 범위 달성 / 판매 P100 게이트 진행 대기
- GitHub 원본 11개 소스/테스트/pyproject Git Blob SHA **모두 일치**하는 최소 실제 원본 세트 Linux Python3.13.5로 실행. `python -m scripts.pg_synthetic_acceptance` **6/6 PASS(exit0)**, `python -W error::ResourceWarning -m unittest -v tests.test_pg_synthetic_acceptance tests.test_pg_html_script` **11 PASS/0 FAIL/0 SKIP** + quiet repeat PASS. 진짜 PG reader/statistics/FK/manual hints/offline HTML/원본 safe_zip new-only file publish 포함; 데이터는 합성 전용, external network/real PG/customer 없음. [P1-11 원본11 SHA·완료 증거](P1_11_P95_EXACT_SOURCE_ACCEPTANCE_20261113.md).
- 내부 가중 P0 **25/25**+P1 **13/15**+P2 **20/20**+P3 **19/20**+P4 **18/20**=**95/100 내부 설계 대비 기능 목표** 달성. 중앙 DBVORA `[작업중]` 목표 달성 후 해제. **판매 RELEASE HOLD, P100 아님**.
- **다음(사용자 별도 목표 P100/출시)**: 전체 인증된 private repo checkout에서 모든 Python>=553/Node/실 ZIP `python -m scripts.verify_release_gate` 수행, 안전한 synthetic PG read-only TLS 실제 서버 + Win3.11 NTFS/브라우저/전원 재시작 QA + 법적 권리/서명/고객 인수. 개인 인증·유료CI·원본/Production 수정은 사전 승인.
- Linux source-specific actual E2E PASS와 **full checkout 전체 회귀 미검증**을 혼동 금지. 무단 출시/고객 연결 금지.

## 2026-11-13 KST — P1-10 오프라인 PG 통합 검증 게이트 신규 / 94% 잠정·P95 미달
- Actual code: `scripts.pg_synthetic_acceptance` 6 check PG catalog→stats→FK→DBA hints→CSP HTML→temp file SHA; mandatory release `synthetic_pg_to_offline_html`. Fail-close release tests; `tests/test_pg_synthetic_acceptance.py`, `tests/test_pg_html_script.py`, optional PG extra + guide. No external DB or API used.
- Verified exact-source output: GitHub HTML `multi_engine_report.py` JS 3074 char FNV `88ecd396` parity, Node22 syntax+interaction/search/hints PASS; `pyproject.toml` SHA `080af800601fff0177eedbfbf58aeb3b2664c36a` parity Python3.13.5 TOML PASS. **New complete PG E2E itself and full original suite UNRUN**. Weighted internal P0 25 P1 12 P2 20 P3 19 P4 18 = **94/100 provisional**, P95 unmet, Release HOLD, central [작업중] keep.
- **NEXT blocking objective:** complete authenticated source checkout on allowed runtime → `python -m scripts.pg_synthetic_acceptance` actual 6/6 + `python -m unittest discover -s tests -v` + `python -m scripts.verify_release_gate` including ZIP/Node, correct any failures → reassess P95 only with proof; authorized synthetic PG read-only TLS and Windows NTFS later. [P1-10](P1_10_PG_OFFLINE_E2E_20261113.md).

## 2026-11-13 KST — P1-09 핵심 PG 가시화·수동 최적화, P92 잠정 / 목표 P95 진행 중
- PostgreSQL `pg_stat_user_tables` 추정 live/dead 행과 실측 heap/index 바이트는 기본 OFF, 사용자가 `--include-postgres-statistics` + PG network 동의한 경우에만 고정 SELECT로 수집. view/partition parent는 물리 사용량/통계 미측정 표시. 오프라인 HTML에 지표·조건별 **수동 검토**만, 자동 최적화/SQL 실행/DB 수정 없음.
- GitHub 최신 feature branch에 `postgres_statistics.py`, `optimization_review.py` 신규 + `postgres_reader.py`, `mixed_cli.py`, `multi_engine_report.py` 및 새/기존 회귀 테스트 반영. 정확 PG stats module **격리 17 PASS**, optimization exact GitHub test **8 PASS**, full reader/PG stats/HTML+CLI integration/원본 전체 >=553 Python+Node/실PG TLS·Windows **NOT RUN**.
- 내부 P0 24 + P1 12 + P2 20 + P3 19 + P4 17 = **92/100 잠정 기능범위**, 95 미달, 판매 RELEASE HOLD, 해총 DBVORA **[작업중] 유지**. 검증 92%라는 뜻 아님.
- **Next:** full authorized private checkout → `python -m unittest discover -s tests -v` / `python -m scripts.verify_release_gate` + Node + real package ZIP + UI; 신규 `tests/test_postgres_statistics.py`, `tests/test_postgres_reader.py`, `tests/test_mixed_cli.py` 오류 수정; 별도 승인의 synthetic PG read-only verify-full + Windows3.11 NTFS 확인. [상세 P1-09](P1_09_PG_STATS_OPTIMIZATION_20261113.md).

> **P4-05 보강 검증:** 정확 Git Blob `81694c7b623edbf94894a195a11f924c0a5a41f9`의 신설 원본 ZIP-gate 테스트 7/7 PASS(단 모의 build/trusted child), 신설 모듈 `7e08838eae1d9d40937a34b5d7ebe41e291f6dca` 정확 일치. **전체 553+ Python·Node/실 패키지 테스트는 미실행**, 85% 잠정·P95 미달/[작업중] 유지. 다음 검증은 전체 정본 `python -m scripts.verify_release_gate`.

## 2026-11-12 KST — P4-05 현재: 진짜 ZIP 통합 검증을 필수 게이트에 연결, P95 미달/85 유지
- `scripts.portable_acceptance_gate`: full source developer ZIP→`verify_zip`→fresh extract→별도 trusted checkout `verify_trusted_extraction` pre-import→실제 패키지 synth archive selftest→temporary ZIP-file tamper fail-closed 검증 **코드 구현**. `verify_release_gate` 새 필수 `trusted_portable_zip_e2e` PASS 전에는 전체 PASS 불가.
- Linux Python3.13.5 로컬 동일 신규 모듈/임시 실제 단일 파일 ZIP + 모의 원본 builder/trusted subprocess **5/5 scoped PASS**. 원본 전체 Python>=553+Node/실 `build_portable`/Windows3.11 NTFS·PG TLS·고객 검증 **NOT RUN**. 85% 잠정 불변, P95 미달, SALE RELEASE HOLD, [작업중] 유지.
- **Next:** full authenticated checkout, execute `python -m scripts.verify_release_gate` and record all PASS/FAIL/SKIP, including trusted ZIP gate SHA. No Windows/manual owner action until necessary. Then Windows3.11 Native/NTFS/Edge file://, separately approved sandbox PG TLS and rights. [P4-05 report](P4_05_TRUSTED_ZIP_RELEASE_GATE_20261112.md).

## 2026-11-12 KST — P4-04 최신: 정확 원본 unit27 PASS, 목표 P95 미달/85 잠정
- Python `-S -B`는 기존 `.pyc`를 읽으므로 추출 코드 내부 실행 전 검증만으로는 안전성 입증 불가. 모든 bytecode 캐시 거부, 별도 신뢰된 원본 checkout의 `scripts/verify_trusted_extraction.py`로 **먼저** extracted ZIP을 파일만 검사하는 안전경로 신규 구현. 합성 로컬 Python3.13.5 GitHub exact source/test **27 PASS**, 추가 독립7 PASS(원본 full suite 아님), Git Blob 4개 일치.
- 비공개 원본 전체 Python >=553+Node·신 ZIP 실제 빌드 및 원본 통합 테스트·Windows3.11/NTFS Edge/file://·실 PostgreSQL read-only TLS/고객 권리 검수 **미실행**. 현재 85% 잠정 고정, P95 목표 미달, RELEASE HOLD, 해총 DBVORA [작업중] 유지.
- **Next mandatory:** private full original source environment→`python -m scripts.verify_release_gate`→real `scripts.build_portable` ZIP→새 경로 추출→별도 trusted script `python -I -S -B /trusted/DBVORA/scripts/verify_trusted_extraction.py --extracted /fresh/absolute/folder`→Windows native 소유자 QA→승인된 PG TLS. 원본 SHA 및 PASS/FAIL/SKIP·ZIP SHA 기록, 실패시 STOP/PIVOT. [상세 P4-04](P4_04_TRUSTED_PREIMPORT_AUDIT_20261112.md).

## 2026-11-12 KST — P4-03 최신: P95 미달, 85% 잠정 / 작업중 표식 유지
- GitHub 정본의 추출 ZIP 검증은 모든 미등록 일반 파일(확장자 없는 파일 포함) 거부, 매니페스트에 등록된 소스의 CPython 생성 캐시만 허용, 외부 하드링크 캐시 거부로 강화. 테스트 파일에도 캐시/변조/추출 ZIP subprocess 회귀를 추가했으나 아직 정본 실행 **미검증**.
- Python3.13.5 임시 폴더 재구성 규칙 **19 PASS/0 FAIL**, 전체 정본 >=553 Python + Node·실 제품 ZIP·Windows/PG는 **NOT RUN**. 현재 **85% 잠정**, P95 NOT MET, RELEASE HOLD. 중앙 [작업중] 제거 금지.
- **바로 다음:** 승인된 전체 private checkout에서 `python -m scripts.verify_release_gate`, 전체 유닛/Node + `scripts.build_portable` 신 ZIP 무결성+독립 프로세스 회귀→Windows3.11 NTFS/실 Chromium file URL→별도 승인된 비운영 PG TLS. [P4-03 근거](P4_03_STRICT_EXTRACTED_MANIFEST_20261112.md).

## 2026-11-12 KST — P4-02 최신, 목표 P95 미달 (잠정 P85 / [작업중] 유지)
- 추출된 개발자 ZIP의 미등록 `.pyc/.pth/.cmd/.bat/.ps1/.sh/.exe/.dll/.pyd/.so/.com/.vbs` 및 기존 소스 확장자는 무결성 검증 거부, 정상 생성 `__pycache__/*.pyc` 예외 유지. 소스 확인 런처 Python `-S -B`. 7개 단위 음성례 + 정본 ZIP 추출 subprocess 통합 회귀 2개 **커밋**, 전체 원본 미실행.
- Linux 격리 재구성 로직 8/8 PASS는 원본 full suite PASS가 아님. 제품 85% 잠정 불변, RELEASE HOLD.
- **Next:** exact remote HEAD→private complete checkout→`python -m scripts.verify_release_gate` (>=553 Python + Node)→`python -m scripts.build_portable` actual ZIP extract/real tests→native Windows3.11/NTFS/Edge file:// QA→owner-approved PG TLS. 실제 테스트 없으면 P95를 보고하지 말고 중앙 [작업중]을 그대로 둔다. 상세 [P4-02](P4_02_UNSIGNED_SIDECAR_GUARD_20261112.md).

## 2026-11-12 KST — P4-01 latest: 85 provisional engineering milestone, RELEASE HOLD
- New owner-usable no-input local `python -m dbvora.archive.review_selftest` (actual ZIP/ZSTD restore/recovery ledger/HTML/replay/corruption **22 checks PASS**) and `python -B -m dbvora.archive.portable_verify` (unsigned extracted source SHA, path symlink checks). Developer ZIP build now includes Win/Unix check+verify launchers; avoids real customer DB paths, API and auto-actions.
- Exact GitHub source/test blob parity, isolated Linux Python3.13.5 **87 PASS/0 FAIL/0 SKIP**, compileall PASS. 27-file *synthetic mini ZIP* from subset (not official builder) extracted: source SHA verification27 PASS, selftest ZIP/ZSTD22 PASS, tamper rejected. Chromium actual renderer static document 12/12 PASS, native file URL not verified.
- **Do not treat 85 as commercial readiness:** weighted P0 22 P1 8 P2 20 P3 19 P4 16, user requested internal engineering milestone. Full original Python≥553+Node and `scripts.build_portable` complete source ZIP/Windows3.11/NTFS, PostgreSQL read-only TLS, install/customer/physical shutdown are **NOT RUN**. No GitHub Actions invoked.
- **Next**: original private complete checkout > `python -m scripts.verify_release_gate` ≥553+Node > fix failures > real ZIP build/extract/run > actual Windows NTFS/UI file:// > owner-approved PG TLS; then signed installer/customer consent. RELEASE HOLD. See docs/P4_01_PORTABLE_SELFTEST_AND_INTEGRITY_20261112.md.

## 2026-11-12 KST — P3-08 most recent: real ZIP/ZSTD synthetic chain PASS, 77 provisional, target85
- Actual GitHub source bytes reconstituted for SQLite reader, safe_zip, zstd_archive, recovery_catalog, request_service, request_ledger, request_audit, review_html, fixture, plus new P3-08 gate and 15 tests. Verified exact Git Blob SHA. Linux Python3.13.5 + local zstd: **actual P3-08 16 checks PASS**, ZIP/ZSTD independent restore and corruption/replay HOLD; isolated unit 58 PASS, compileall PASS. No customer source.
- Fixed create=False record-only ledger recreation on disappeared path; two added regression tests and local equivalent race/concurrency cases PASS.
- Whole private original checkout **not available** due Git DNS; `python -m scripts.verify_release_gate` floor **518** plus Node never run. No paid CI triggered. Native Windows/NTFS+browser and approved real PG/TLS unverified. RELEASE HOLD and no automatic retry/retention/sale.
- **Next**: full 518+ Python/Node original-run; Windows3.11 NTFS, owner-approved read-only nonproduction PostgreSQL, portable installer. 77 is provisional engineering 22+8+19+17+11, 85 still 8p away. See docs/P3_08_REAL_CHAIN_AND_LEDGER_RACE_20261112.md.

## 2026-11-12 KST — P3-07 current resume: DBVORA 72 provisional / 85 goal
- New synthetic-only explicit CLI python -m dbvora.archive.review_html with separate existing ledger/archive/output dirs and --accept-plaintext-summary; automatic replay/authorization prohibited.
- Local isolated 39 PASS/0 FAIL/0 SKIP and HTML Chromium synthetic 5 rows/0 JS/0 outbound; exact new Git Blob parity. Full original-source Python minimum 499 plus Node, real archive ZIP/ZSTD roundtrip NOT RUN.
- **Next MUST**: authorized complete original checkout, python -m scripts.verify_release_gate and original archive request service roundtrip; then Windows3.11/NTFS browser file://, approved real PG read-only TLS. No source overwrite, customer credentials, auto retry, paid CI or deployment.
- Score 70→72 provisional via P3 owner review+P4 static HTML; 85 NOT MET. RELEASE HOLD, no customer acceptance. See docs/P3_07_OFFLINE_RECOVERY_REVIEW_20261112.md.

## 2026-11-12 KST — P3-06 latest, target 85%; full integration verification first
- Added synthetic-only read-only audit CLI `python -m dbvora.archive.request_audit --ledger-dir ... --archive-dir ... --synthetic-only`; isolated Linux reconstructed test 17 PASS, **whole repository NOT RUN**.
- **Highest priority:** complete original checkout, `python -m scripts.verify_release_gate` (Python minimum 477 + Node), archive request replay and recovery tests with original source; no test count reduction or release-acceptance shortcut.
- Then native Windows Python3.11 NTFS and `file://` browser; approved read-only PostgreSQL TLS role only if separately authorized. All customer source and output remain protected.
- Product readiness remains **70% provisional / 85% NOT MET / RELEASE HOLD**. See `docs/P3_06_REQUEST_LEDGER_AUDIT_20261112.md`.

## 2026-11-11 KST — P1-PG02 provisional 70% milestone, 30% unverified product scope
- New `dbvora/multi_engine_report.py` and `dbvora/mixed_cli.py` with 31 regression tests source-exact; current targeted 178/178 Linux PASS; Chromium set_content 9 conditions PASS, direct file:// blocked by environment. RELEASE HOLD.
- **Next P0:** whole repo `python -m scripts.verify_release_gate` Python >=460 + Node DOM, ensure old features work after mix report.
- **Next P1:** authorized nonproduction PostgreSQL actual psycopg3 metadata/TLS/DB ACL test; no credentials in args or source, no auto connection.
- **Next P4:** native Windows3.11/NTFS SQLite/ZSTD, HTML file:// click/console, package/restore/backward compatibility, power loss tests. Only after verified customer approvals plan release.
- Engineering 70% is a weighted estimate, not a complete product or commercial release. No automation or pruning enabled.

## 2026-11-11 KST — P1-PG01 immediate unfinished
1. Full checkout `python -m scripts.verify_release_gate` with Python >=429, Node/browser and ZIP/ZSTD + P3 request-service tests.
2. Safely validate PostgreSQL SQL against **owner-approved read-only sandbox** only, optional installed psycopg3 and TLS verify-full; no credential logging/remote telemetry. This connector is not currently exposed by workspace/UI.
3. Verify Windows3.11/NTFS synthetic artifact publication + package installer, P3 ledger crash recovery. Read-only PG, P3 automatic schedule and final Windows customer acceptance remain before 70%.
4. Provisional 55% unchanged pending acceptance, RELEASE HOLD, no external DB connection used in this turn.

## 2026-11-11 KST — P3-05 highest priority
- Confirm new exact `feature/p0-db-map` commit, two new source Git blobs and docs parity. Full Python `unittest discover` floor is now **414**, not yet executed.
- From complete source checkout run `python -m scripts.verify_release_gate`, then browser smoke/Node, then a native Python3.11 Windows/NTFS synthetic ZIP/ZSTD backup+restore+replay fault gate. Use authorized test directories only; no real customer data until explicitly approved.
- `dbvora.archive.request_service.archive_once` is currently **synthetic-only Python API** and does not replace the user CLI/scheduler. Verify request-ID ledger integrity/power-loss edge cases before expanding that boundary. No exactly-once guarantee.
- Assess PostgreSQL read-only connector, workspace integrations, product packaging, documentation and P4 criteria; score stays **55% provisional** versus target 70%, RELEASE HOLD until evidence improves.

## 2026-11-11 — P3-03 first unfinished verified release gate
- Commit adds `python -m scripts.request_archive_gate` real-source acceptance and 17 fault tests. Prior 17/17 local tests were with CLI/ledger stand-ins; no integrated production code verification.
- On **complete private checkout**, run `python -W error::ResourceWarning -m unittest -v tests.test_request_archive_gate`, `python -m scripts.request_archive_gate` and `python -m scripts.verify_release_gate`. Floor >=397 Python + Node TAP + existing ZIP/ZSTD + new 9-check request replay gate.
- Next native Windows Python3.11/NTFS crash/restore tests and user-facing source-only consent before raising completion. No paid CI/real customer DB/force push/public mirror. Provisional 55% until proven.

## 2026-11-11 KST — P3-02 next priority (supersedes old milestones)
1. This branch has **synthetic gate-only** request reservation integrated with genuine archive CLI calls. Run `python -m scripts.synthetic_cli_gate` from a **complete authorized checkout**, then `python -m scripts.verify_release_gate` (Python >=378, Node TAP 1, ZIP/ZSTD and filesystem). The new two P3-02 tests have not been run on current commit.
2. Require exact source blob SHA verification and actual Linux/Windows results, do not re-use prior 30-case evidence as new integrated proof.
3. Then test Windows3.11/NTFS with original `py -3.11 -B -m scripts.windows_ntfs_gate` and a safe copied fixture. Do not modify user-facing archive_cli or enable scheduling until request ledger and post-crash recovery are proven.
4. Commercial completeness remains **55% provisional**, 70 target pending; release HOLD. No customer files, paid CI, real backup overwrites, changed permissions or production.

# NEXT_TASK — authentic frontend assets and full 199-case integration gate

> **Latest active work is the final section of this document.** Older first-unfinished headings below are preserved as historical checkpoints and must not be repeated.

Trigger: ㄱ / [디비보라 깃헙보고 작업해]. Read feature/p0-db-map latest remote SHA, HANDOFF, STATUS, AGENTS, REQUIREMENTS and docs/P1_C5_CLI.md before acting. Do not repeat P0/C0/C1/C2/C3/C4.

## Implemented this turn
- New dbvora/archive_cli.py subcommands: snapshot/ZIP or ZSTD archive/independent new-path restore/unsigned receipt/read-only receipt audit. Explicit --synthetic-only and --accept-plaintext / --accept-unsigned; no default customer access, overwrites, server write API, deletion, schedule or uploads.
- New tests/test_archive_cli.py 9 synthetic integration tests. Local code compile PASS, independent mock CLI checks 11 PASS, but actual existing archive modules and 125 regression tests NOT RUN in this current container (no private GitHub checkout/network).
- docs/P1_C5_CLI.md records end-user commands, limitations and lack of true idempotency.

## First unfinished gate (mandatory)
1. Obtain full current feature branch checkout in an environment with private repo access, run \`python -W error::ResourceWarning -m unittest discover -s tests -q\` (expected >=134 cases if all tests discovered), \`python -m compileall -q dbvora tests scripts\`, \`node --test tests/test_ui_dom.cjs\`, \`python -m scripts.preflight_archiving\`; record exact pass/fail/skip and fix any integration errors. Do not infer PASS from mock smoke.
2. Test actual synthetic ZIP/receipt/audit roundtrip; ZSTD optional only when locally present. Confirm source bytes/mtime unchanged, fail-closed on corrupt/nonexistent args, no source paths in CLI output; verify no unintended files outside designated demo directories.
3. Review Windows/Python 3.11 and NTFS support; existing safe publish currently fail-closed if dir fsync unsupported. Use ZIP-only fallback if optional zstd missing, never quietly claim success. No unmanaged browser policy bypass.
4. Add retry request-ID ledger or explicit deduplication with concurrency/power-loss tests BEFORE calling any automated operation idempotent. CLI retries currently create distinct new artifacts, never overwrite existing; classify as not idempotent.
5. Update STATUS/HANDOFF/next task with real test evidence + SHA and assess product roadmap priorities: PostgreSQL read-only, multi-DB map, metrics, packaging vs compression refinements.

## Prohibited without approval
Real customer DB access, deletion/retention/overwrite, network/third-party uploads, external paid service, public distribution, installed local credentials or Windows installer release. Signed provenance and physical power-loss guarantee are NOT provided.

## P1-C5 synthetic gate added (2026-10-26 KST)
- `python -m scripts.synthetic_cli_gate` on a **complete local checkout** is now the short one-shot offline acceptance smoke: it exercises *real* CLI snapshot, ZIP, unsigned receipt, restore, audit and source immutability using ONLY an OS-temp generated SQLite fixture. ZSTD is optional; output is JSON, always `ready_for_customer_data=false`.
- **NOT yet executed end-to-end in this environment**: the container can only access separate CLI files and mocks; private GitHub clone cannot resolve, and paid/private Actions have not been authorized or run. New script py_compile PASS, CLI 11 mocks PASS, gate error handling 3 isolated local mocks PASS. The standalone gate mock test file could not be uploaded due to two security validation blocks; do not assume it is in GitHub.
- Mandatory gate: real `python -m scripts.synthetic_cli_gate`, full `unittest` >=134, Node DOM, compileall, preflight. Inspect failures; preserve previous code/data and fix minimal problems. On any failure keep P1-C5 as PARTIAL and no customer release. Windows 3.11 filesystem semantics remain NOT_TESTED.

## 2026-10-26 KST next mandatory gate (no additional feature creep)
- Execute `python -m scripts.verify_release_gate` from a **complete** feature/p0-db-map checkout. It fails unless >=141 tests discovered, actual synthetic CLI ZIP+receipt+restore+audits PASS, conditional ZSTD PASS or explicit absent skip, JS DOM/compileall/preflight PASS. Reports `ready_for_customer_data=false` even if all synthetic checks pass.
- Executed only 7/7 mocked runner logic unit tests (PASS), new Python compile PASS, and negative incomplete checkout test (FAIL_CLOSED, expected). **Full 141-test suite has not run** and must not be reported as success. The incomplete source is a tool environment constraint rather than an observed product failure.
- If full checkout available, collect JSON gate result and test summary with exact failures, fix first failing code, then update STATUS/HANDOFF with SHA. No actual customer DB, public release, or paid CI without approval.

## First unfinished task after latest 2026-10-26 gate hardening
- Run `python -m scripts.verify_release_gate` from a complete authorized `feature/p0-db-map` checkout. It now requires >=145 Python cases, 0 skips when ZSTD is present (otherwise <=1 optional skip), Node TAP exactly 1 PASS, real synthetic SQLite ZIP/ZSTD restore, compileall and temporary filesystem preflight. Gate still never authorizes customer data.
- Latest executed evidence: 11 focused mocked decision tests PASS, Python syntax PASS, exact blob SHA matched committed code. Full suite and real archive end-to-end have not run due unavailable complete checkout. A partial checkout correctly returns FAIL_CLOSED; do not mislabel as functional breakage.
- Next once checkout works: capture full pass/fail/skip and failing names; repair root causes, run Windows Python3.11/NTFS synthetic trial, reassess remaining product roadmap. Do not promote, deploy, or invoke paid CI without approval.

## First unfinished gate after 2026-10-26 P1-C5 evidence hardening
- **Required**: from complete private feature checkout run `python -m scripts.verify_release_gate`. It now requires **>=156** Python tests; when optional ZSTD is absent, only the explicitly named CLI ZSTD roundtrip skip with the documented reason is allowed. It also independently hashes generated ZIP/ZSTD archive and restored files in the synthetic gate, checks Node TAP, compileall and temp filesystem preflight.
- **Current evidence only**: Linux Python3.13.5, 14 release-gate mocked process tests PASS + 8 real temporary-file helper/mocked-CLI tests PASS = 22; exact 4 source Git blobs matched local tested SHA. Actual full unittest >=156, real ZIP/ZSTD end-to-end, Windows/NTFS remain NOT RUN due incomplete private checkout. Existing prior 125 tests belong to earlier git revisions.
- Next: obtain complete authorized checkout/runner, run the 156+ gate and fix real failures. Do not run customer DB operations, paid CI, public source mirroring, or Production without explicit approval. Preserve main/develop and existing data.

## NEW EVIDENCE 2026-10-26: real ZIP/ZSTD engine executed
- Actual GitHub SHA-matched local modules directly executed: ZIP synthetic smoke **17/17 PASS**; ZSTD levels 1,3,9 actual independent restore **all PASS**. Detailed reproducible source provenance, environment, cases, sample sizes in `docs/P1_C5_REAL_ENGINE_SMOKE_20261026.md`.
- **First remaining task changes**: acquire `recovery_catalog.py`, `receipts.py`, checked-in `archive_cli.py`, and `test_archive_cli.py` in the same isolated workspace; validate exact Git SHA; run the 9 real CLI tests (ZSTD binary available). Next verify read-only catalog and receipt SHA lineage, then assemble/run complete 156 tests. Do not mark any unexecuted case PASS.
- Still require Windows Python3.11, real browser and power-loss/prod security gates; no customer DB or paid CI without approval.

## 2026-10-26 KST — P1-C5 real CLI+Receipt Linux gate completed
- Exact original modules: `tests.test_archive_cli` **9/9 PASS** with real Receipt and catalog, no stubs. `scripts.synthetic_cli_gate` **8 checks PASS** with ZSTD. `tests.test_synthetic_cli_gate` + `tests.test_verify_release_gate`: **22/22 PASS**. Extra actual Receipt/lineage/corrupt-audit synthetic checks **12/12 PASS**, not committed as tests. Details/source Git blobs in `docs/P1_C5_REAL_CLI_RECEIPTS_20261026.md`.
- 31 of 156 checked-in Python tests exercised, full 156 not run. Next: acquire remaining 125 checked-in test code and P0/API dependencies, complete unified `python -m scripts.verify_release_gate` and Node DOM and preflight, then Windows3.11/NTFS. No commercial release or customer DB operations, no unapproved paid Actions or public source mirror.

## 2026-10-26 — COMPLETED Linux synthetic 156-case release gate; NEW next step
- Supersedes all above old 31/156 and missing-source notices: Git-SHA-matched source workspace 36/36, actual checked-in Python regression 156/156 PASS (0 FAIL, 0 SKIP), unified six-step synthetic gate PASS, CLI ZIP/ZSTD+receipt/audit 8 checks, Node DOM 1/1, compileall and filesystem preflight.
- New first blocker: Windows Python3.11/NTFS fail-closed durability/hardlink/restore compatibility on an authorized actual Windows host, plus real-browser GUI, packaging and hardware power-loss evidence. No client files or paid Actions without approval.
- Full evidence at docs/P1_C5_FULL_SYNTHETIC_GATE_20261026.md. Linux synthetic PASS is not customer data readiness. Main/develop not promoted.

## First unfinished task after 2026-10-26 Windows diagnostic implementation
- Linux **167/167** Python suite PASS and full six-step synthetic gate PASS; 11 Windows preflight decision tests PASS (mocked OS facts). Windows diagnostic code complete but **not executed on native Windows**; Linux run correctly refused.
- On authorized private Windows Python3.11 NTFS machine: run `py -3.11 -B -m scripts.windows_ntfs_gate`. On `DURABILITY_NOT_PROVEN_FAIL_CLOSED`, preserve strict failure, investigate native Windows file+directory persistence and rollback, only then adapt writer with Windows-proven tests. See `docs/WINDOWS_NTFS_VALIDATION_20261026.md`.
- Next after Windows: actual GUI browser and packaging. No customer data, Public mirror, paid Actions, destructive cleanup or Production without approval.

## 2026-10-26 — developer preview + Chromium DOM completed
- **180/180** Python full source regression PASS (0 fail/skip), 6/6 synthetic Linux release gate PASS, optional real Chromium injected synthetic browser DOM 5/5 PASS; tested original source version alignment and deterministic 23-file unsigned portable developer ZIP. See `docs/PORTABLE_BROWSER_PREVIEW_20261026.md`.
- **First unresolved**: genuine Windows Python3.11/NTFS synthetic durability and independent restore (`py -3.11 -B -m scripts.windows_ntfs_gate`); current archive fsync may fail closed as designed. Then Windows actual localhost HTTP browser and standalone installer/offline UI dependency packaging.
- Browser local URL navigation blocked by current sandbox. Do not confuse Chromium `set_content` + fetch stub with HTTP browser E2E, though actual render and user interaction verified. No customer data, paid CI, main/develop promotion or public release.

## 2026-10-26 — offline HTML preview implementation complete
- New local one-file read-only schema HTML without FastAPI/Uvicorn/HTTP, now bundled in developer source ZIP with Windows & Unix map exporters. Full **194/194** Python Linux suite PASS, all six offline synthetic release stages PASS. Optional real Chromium generated HTML **7/7 PASS**: correct FK & table cards, text-safe hostile names, no external network requests, no mobile overflow.
- Full steps, asset safety, explicit SHA, privacy limits: `docs/OFFLINE_HTML_PREVIEW_20261026.md`. Single-file HTML contains schema identifiers so user must authorize sharing; no rows, DB paths or customer data tested.
- Remaining actual Windows3.11/NTFS archive durability and portable Windows launcher/browser open, native installer, browser HTTP E2E unverified. No production or customer data authorization.

## Current next work — after CSP fail-closed hardening (2026-10-26 KST)
- The new HTML template marker security guard is committed on feature/p0-db-map, with one new checked-in Python test and revised **195-case minimum**. Prior **194/194** remains valid only for the preceding commit; current-HEAD full regression is **NOT RUN**.
- First reproducible gate on an authorized complete branch checkout: `python -W error::ResourceWarning -m unittest discover -s tests -v` (expect >=195, zero failures), `python -m scripts.verify_release_gate`, and `python -m scripts.offline_html_browser_probe` when an allowed Chromium environment is available. Verify HTML CSP actually exists, network stays disabled, source hash/mtime unchanged.
- Highest OS blocker still native Windows Python3.11/NTFS `py -3.11 -B -m scripts.windows_ntfs_gate` and real Windows offline HTML launcher/`file://` browser. Do not bypass directory sync, use customer DB, release a Windows installer, pay for CI, or promote main/develop without approval and supporting evidence.

## Latest first unfinished unit — 2026-10-26 KST synthetic owner self-check
- New code `dbvora/offline_selftest.py` and four test cases committed; source ZIP bundles checker, docs `OFFLINE_SELFTEST_20261026.md`. The new code was syntax-checked and 4/4 tests passed with a **stub export boundary only**; Git blob provenance verified. Current full suite minimum **199**, not yet executed at current HEAD.
- First action when full private checkout execution possible: run real `python -m dbvora.offline_selftest` (no test-double); then `python -m scripts.verify_release_gate` with >=199 tests and `python -m scripts.offline_html_browser_probe` if actual Chromium allowed. Fail-closed if incorrect.
- Native Windows separate gate: on authorized owner PC `py -3.11 -m dbvora.offline_selftest` from developer preview and `py -3.11 -B -m scripts.windows_ntfs_gate` from complete checkout. A browser file navigation and Windows NTFS publication proof are still **NOT VERIFIED**; self-check success cannot substitute.
- Do not ask user to operate local PC until this exact native-only blocker matters; do not use customer files, paid CI, public source, installer release, or disable durability fsync.

## Active next gate after real offline Python focus (2026-10-26 KST)
- The real GitHub `export_html.py`, `inventory.py`, `sqlite_reader.py`, `metrics.py`, `offline_selftest.py`, actual HTML skeleton and checked-in tests pass focused **17/17** with synthetic data; mock CSS/JS kept explicit. Old Python ResourceWarning from `tests/test_export_html.py` patched and revalidated. Full evidence: `docs/OFFLINE_SELFTEST_REAL_CORE_20261026.md`.
- Next safely available tasks: recover exact production `dbvora/web/style.css` and `app.js` into authenticated verification environment, then Chromium generated HTML and offline navigation checks; assemble complete authenticated repo and run `python -m scripts.verify_release_gate` (>=199) without paid CI. Do not report the 17 focused tests as full 199 success.
- Native Windows Python3.11 NTFS directory-fsync and Windows `file://` remain user-machine-only validation; run `py -3.11 -m dbvora.offline_selftest` from private preview and `py -3.11 -B -m scripts.windows_ntfs_gate` from complete checkout if/when owner at Windows PC. No customer DB access, source-publication, paid Actions, installer or forced promotion without prior approval.

## 2026-10-26 KST — next after authentic frontend Chromium validation
- Latest verified targeted code: real GitHub JS/CSS blobs, `node --check` PASS; 17/17 focused Python PASS (without placeholder frontend assets); owner synthetic selfcheck 9/9 PASS; expanded real Chromium `page.set_content` **13/13 PASS** at repo probe blob `1bc43ccad0b371c2412af5d90e749be3c2d617dd`. Report in `docs/FRONTEND_REAL_ASSETS_CHROMIUM_20261026.md`.
- A real `file://` navigation attempt returned Chromium `ERR_BLOCKED_BY_ADMINISTRATOR`, **not** product failure and **not** product validation. Leave `browser_file_navigation=false`. No policy bypass.
- **First unfinished**: authorized complete GitHub private checkout, then full `python -m scripts.verify_release_gate` (>=199 Python cases + local ZIP/ZSTD/fs preflight/Node); check in-memory Chromium 13 tests. No paid Actions or source publicization.
- **Next native-only**: Windows 3.11 NTFS durability `py -3.11 -B -m scripts.windows_ntfs_gate` (complete checkout) and `py -3.11 -m dbvora.offline_selftest` (private preview); native `file://` viewer launch. Do not treat Linux proof as Windows. Owner task only once ready at PC; no customer DB, installer, automated deletion, Production without approval.

## 2026-10-26 KST — next after 201-case portable selfcheck addition
- New 0-argument Windows+Unix selfcheck launchers committed to unsigned source ZIP with both paths in `_REQUIRED`; two new packaged selfcheck tests and 201 Python test minimum added. 14 GitHub Python test files verified by SHA with **201 definitions**. See `docs/PORTABLE_SYNTHETIC_LAUNCHERS_20261026.md`.
- **First unfinished gate:** source-complete private checkout; run `python -m scripts.verify_release_gate` (>=201 cases; all six steps), including actual ZIP extraction and `dbvora.offline_selftest` subprocess test. Verify source ZIP SHA, no network/customer data; do not use mocked local directory as full checkout. If environment still cannot access complete private checkout, record this explicit blocker instead of claiming 201 PASS.
- **OS-only:** Windows Python3.11 `check_dbvora_windows.cmd` from private ZIP and native NTFS `py -3.11 -B -m scripts.windows_ntfs_gate` from complete repo, plus actual local browser `file://` opening. Linux simulated/Chromium `set_content` does not substitute for these. No customer DB, paid CI, public installer or permission changes without approval.

## 2026-10-27 KST — next after read-only C2 prototype
- GitHub branch implements `dbvora/archive/dedup_plan.py` only as **candidate byte reuse analysis**, plus 9/9 isolated synthetic tests. No chunk store/write path, refcount/GC, restore or deletion. All 15 test source files authenticated via Git blobs; **210 test definitions**, **not** 210 executed tests. See `docs/C2_DEDUP_PLAN_20261027.md`.
- Priority A: obtain authorized full private checkout and run `python -m scripts.verify_release_gate` (>=210 full Python cases, Node DOM, real ZIP/ZSTD synthetic CLI/restore and filesystem preflight), and `python -m scripts.offline_html_browser_probe` if installed Chromium works. The existing external QA kit v2 pins the **old** 201-case baseline and will intentionally reject the new branch; regenerate its SHA pins before using it. Do not disable pinning.
- Priority B: expand C2 to safe on-disk chunk manifests and independent restore only *after* complete regression, preserving original and previous verified backups. Physical dedup savings, customer restore and crash durability require independent measurement/gates; no auto-delete.
- Priority C: address `dbvora/web/app.js` resize-listener accumulation with an approved ordinary GitHub update (prior blocked), verify exact remote SHA and Chromium browser regression. No bypass of safety controls.
- Native-only Windows Python3.11 NTFS and `file://` remain a separate release blocker. No customer DB/paid CI/public installer/release without owner approval.

## 2026-10-27 KST — after UI resize handler patch (latest)
- DONE on `feature/p0-db-map`: source `dbvora/web/app.js` now installs window resize listener once outside `render()`, and `tests/test_ui_dom.cjs` guards repeated refresh registration. Commit chain `4c9f8b39dbd4` → `bf92b7d26e15`. Original 4 resize subscriptions after initial+three refreshes, revised 1; exact committed code + test executed in V8 with Node built-ins simulated and existing schema/XSS assertions PASS.
- **First uncompleted integrated gate:** authenticated full private checkout → `node --test tests/test_ui_dom.cjs` (real Node) → `python -m scripts.verify_release_gate` (>=210 Python discovered + ZIP/ZSTD synthetic roundtrip, Node DOM and temp FS) → generated HTML Chromium check if available. The V8 simulation is not a substitute for actual Node, complete regression, browser navigation or Windows testing.
- C2 `dedup_plan.py` remains read-only estimate only; no chunk persistence or real dedup restore. Native Windows3.11/NTFS, offline `file://` and power-cut remain blocking customer release. Do not promote main/develop, trigger paid CI, use customer DB, expose source/public site or relax fsync before approval and evidence.

## 2026-10-27 KST — Node runtime regression now verified; full Python gate pending
1. **DONE:** exact GitHub current `app.js` and `tests/test_ui_dom.cjs` Git blob hashes verified 2/2. Node v22.16.0 actual `node --check` PASS and `node --test tests/test_ui_dom.cjs` TAP **1 passed / 0 failed**, refresh resize listener remains one. Unlike earlier simulated Node shim, this pass used the genuine Node executable with checked-in source bytes.
2. **BLOCKED BY SOURCE AVAILABILITY (not product failure):** current **>=210** Python unittest + `python -m scripts.verify_release_gate` was not executed. The available old `dbvora-dev-preview-0.2.0.zip` lacks newer offline selftest and has older exporter; QA kit v3 pins source HEAD `31b8257` before live head; never weaken source SHA safeguards. Need full authorized current private source checkout for real suite, ZIP/ZSTD and package checks. Avoid rerunning the same unauthenticated GitHub clone known to fail.
3. **NEXT after complete checkout:** run current-source file hashes, `python -W error::ResourceWarning -m unittest discover -s tests -v` (>=210), `python -m scripts.verify_release_gate` (six stages), independently inspect failure/output. Then native Windows3.11/NTFS and `file://` tests, no customer data. Preserve main/develop, privacy, existing backups and source.

## 2026-10-27 — latest next gate after strict audit
- Done: opt-in `archive_cli audit --require-all-verified` and 3 genuine synthetic CLI tests PASS. Normal `audit` remains a read-only report even if a receipt fails; its exit code alone does not certify content.
- `scripts.verify_release_gate` minimum now **213 Python tests**, with `tests/test_audit_strict.py` required. This full gate was NOT executed; earlier QA kit pins old Git SHA and cannot be treated as current.
- Next: acquire authorized full source at live feature SHA, independently verify all Git blob IDs, run `python -W error::ResourceWarning -m unittest discover -s tests -v` and `python -m scripts.verify_release_gate`, then actual browser and native Windows Python3.11/NTFS validation. Do not disable SHA pinning or infer customer readiness.
- No customer files, paid CI, archive deletion, main/develop promotion or public deployment without required approvals and test evidence. See `docs/P1_C6_STRICT_AUDIT_20261027.md`.

## 2026-10-27 KST — active next checkpoint after P1-C7
- DONE: additional orphan-receipt fail-closed safety guard in opt-in `archive_cli audit --require-all-verified`; default audit backwards-compatible. Real disposable SQLite + archived receipt Python tests **4/4 PASS**; combined exact-current-code focused 18/18 PASS. Current Python test *definitions* **214**, not 214 executed.
- BLOCKER: complete authenticated private checkout missing. `python -m scripts.verify_release_gate` on partial source deliberately emits `FAIL_CLOSED / INCOMPLETE_SOURCE_CHECKOUT, missing_count=10`; do not count as product bug or bypass. Prior QA kit SHA pins old feature head.
- NEXT A: secure full authorized current `feature/p0-db-map` files and prove Git blob integrity; then run Python >=214, real Node DOM, ZIP/ZSTD synthetic roundtrip and temp-FS preflight using `python -m scripts.verify_release_gate`. Then native Windows3.11 NTFS/file navigation/durable restore. No paid CI or Public source clone.
- NEXT B after real full gate: only then evaluate C2 content-addressed manifest and independent restore implementation. Do not write customer data or enable auto cleanup.

## 2026-10-27 KST — current after QA v4 (first unfinished task unchanged)
1. **Completed fallback:** SHA-pinned offline source QA kit v4 produced as local conversation artifact. 50 exact source Git blobs recorded in `docs/QA_V4_MANIFEST_20261027.md`; harness **16/16 PASS**, stale or nonexistent source ZIP **FAIL_CLOSED**, no private customer/source data in kit. Obsolete JS resize patch is retired.
2. **Unfinished:** full private feature checkout/source ZIP has NOT been made available to the runtime, so **214 real Python tests and six-stage unified acceptance NOT RUN**. Manifest hashes/QA harness checks are not proof of product acceptance.
3. **Action path:** owner-authorized private source ZIP (source baseline `318a49e3031b9d0aa052221e35ebdebbec70dedd`) checked against pins; run `run_dbvora_qa.py --zip <private-zip> --report <new-report.json>` in a fully available local Python3.11+/Node environment or separately approved CI. For a newer code blob, review changes and generate updated pinned kit, never bypass pinning.
4. **Next gates:** independently inspect results and fix failing code; real ZIP/ZSTD/Node/preflight + Windows Python3.11 NTFS durability and file:// GUI; then C2 actual chunk persistence only after base safety. No paid CI, customer data, force push, public repository or unapproved external upload.

## 2026-10-27 KST — latest continuation after QA v5
- DONE: local QA v5 now hashes each pinned source member again while extracting, closing ZIP-replacement-before-execution gap. v5 selftests 19/19 PASS, previously built strict audit/gate focus 18/18 PASS. No DBVORA product/source logic changed. Evidence `docs/QA_V5_POSTVERIFY_EXTRACTION_20261027.md`.
- BLOCKED: full GitHub private source checkout unavailable to this runtime; entire **214-test** suite and full six-stage release gate remain **NOT RUN**. Existing GitHub manifest pins **50** reviewed sources at source commit `318a49e3031b9d0aa052221e35ebdebbec70dedd`; docs-only head can advance.
- NEXT: with authorized private source archive run the pinned QA v5 runner (zero-cost local), then investigate actual failed cases, verify Windows Python3.11 NTFS durability and native file browser. No automatic deletion, real customer data, Public repository changes, CI costs, or feature-to-main merge without necessary approvals.

## 2026-10-27 KST — current next checkpoint after P1-C8/QA v6
1. DONE: current Git-blob-matched export path 13/13 Python PASS, real Chromium `page.set_content` offline UI 14/14 PASS; negative control original JS 13/14 FAIL_CLOSED. Repeat-refresh listener protection committed to `scripts/offline_html_browser_probe.py`. Evidence P1-C8 doc.
2. DONE: offline QA kit **v6** rebased source SHA pins to `cafbd87e61f20cffe778692f8a29db541588eeaf`, SHA-256 `c80228f0...`, 19/19 harness selftests PASS, missing/outdated source ZIP FAIL_CLOSED. Earlier QA v4/v5 intentionally stale for current code.
3. UNFINISHED/BLOCKED: full authenticated private source checkout → all **214 Python tests** plus six-stage `python -m scripts.verify_release_gate` → independent failures/fixes. No full-release claim based on focused tests or QA selftests. Authorize complete source ZIP locally or separately approved CI; no paid CI automatically.
4. IMPORTANT ENVIRONMENT LIMIT: genuine `file://` opening produced Chromium `ERR_BLOCKED_BY_ADMINISTRATOR` in this runtime; do not circumvent policy and do not claim actual file navigation PASS. Test later in permitted native Windows3.11/NTFS + browser (no customer data), also verify crash durability and power interruption before release.
5. C2 actual dedup persistence/GC remains deferred until core integrated release gate; never auto-delete verified originals, weaken source checks or promote to main/develop prematurely.

## 2026-10-27 KST — current owner-local QA bridge first priority
- DONE: GitHub-exact source inventory 27/50 files restored from past trusted snapshots, remaining 23 missing in execution environment. No false full-suite claim.
- DONE: owner-local private source verification bootstrap v1 as temporary conversation ZIP, integrates QA v6 and Git clone (local credential manager)/existing clone, 50 Git blob pin verification and Git archive. Actual synthetic unit tests **5/5 PASS**; v6 harness **19/19 PASS** fresh extraction. No real customer data, source upload, paid CI, repository writes or source exposure. See `docs/OWNER_LOCAL_QA_BRIDGE_20261027.md`.
- BLOCKED: without an owner-authenticated private source checkout, the product's **214 Python tests, six-stage unified gate** and Windows NTFS durability remain NOT RUN. On owner-authorized Windows Python3.11/Node environment run the bootstrap once, review sanitized QA JSON and fix actual failures; do not infer PASS from harness tests.
- AFTER full verified checkout: Chromium browser file:// on permitted host; independent crash/NTFS recovery, then C2 actual dedup store design. No Git main/develop merge, paid GitHub Actions, public source or customer DB until appropriate authorization and evidence.

## 2026-10-27 KST — current first gate after owner Windows v1 ZIP mismatch
- Owner authenticated private Git clone and 50 current Git blob hashes **PASS**, but v1 `git archive` ZIP QA **FAIL_CLOSED SOURCE_BLOB_MISMATCH before execution**. Preserve its output and don't repeat v1 unchanged or waive SHA checks.
- New standalone owner-local QA **v2** (raw Git-object content instead of `git archive`): synthetic Linux **6/6** plus unchanged QA v6 **19/19** after extraction; no live Windows v2 test. See `docs/OWNER_LOCAL_QA_BRIDGE_V2_20261027.md`.
- NEXT on authenticated owner's Windows machine: unzip v2 package to clean local directory and execute `py -3.11 verify_private_source_v2.py --clone --qa-kit qa_v6 --output .`; inspect sanitized `DBVORA_QA_v2_<sha12>.json`. A host synthetic PASS is NOT customer-ready. After full Python 214 tests and gate, validate native Windows Python3.11/NTFS + file:// + restoration and power-interruption separately.

## 2026-10-27 KST — immediate task: owner direct-Git Windows UTF-8 gate rerun
- The owner **successfully cloned** `feature/p0-db-map` directly via Git. Stop requiring v1/v2 zipped QA bridges: they are unnecessary and source pins are obsolete after the code/test update.
- Windows Python3.11 gate crashed due to CP949 decoding Node's UTF-8 test output and downstream `None + str`. The feature branch fixes strict stream handling and requires >=**218** Python tests. Isolated revised routine 6/6 and real Unicode Node TAP 1/1 PASS on Linux; **full Windows gate still NOT RUN**.
- Next owner PowerShell (existing checkout): `cd E:\DBVORA_GIT`; `git status --short`; `git pull --ff-only`; only after success, `py -3.11 -B -m scripts.verify_release_gate`. Receive JSON and fix only identified failures. No new clone/ZIP/payment/customer DB; keep main/develop untouched.
- After 218-case six-step synthetic PASS: separate Windows native NTFS/power recovery and file:// browser tests; no sales or public release before evidence. Incident doc: `docs/WINDOWS_CP949_RELEASE_GATE_20261027.md`.

## 2026-10-27 KST — next exact gate after owner Windows FAIL_CLOSED
- Owner's Windows Python3.11 218-case run at `a867f744...`: checkout & compileall PASS; Python unit/CLI/Node/preflight all FAIL. It returned no failure IDs/codes; do not infer all independent product faults. The `safe_zip._sync_directory` POSIX directory fsync path is a plausible shared native-Windows blocker, but **not proven on owner host**.
- Added fail-closed path-free JSON diagnostics: min **223** Python tests (23 in gate unit module), returns failure test IDs, CLI safe error code, Node TAP counts, filesystem publish code, stage exit codes. Original guards unchanged. See `docs/WINDOWS_RELEASE_GATE_DIAGNOSTICS_20261027.md`.
- NEXT (owner existing Git checkout; no ZIP): `cd E:\DBVORA_GIT`, `git status --short`, `git pull --ff-only`, `py -3.11 -B -m scripts.verify_release_gate` only if pull succeeded. Review sanitized JSON and fix specifically reported failures. No direct customer database, path export, public mirror, paid CI, main/develop merge, weakened fsync, or destructive archive change. Native Windows/NTFS recovery/Power-cut/file:// still separate.

## 2026-10-27 KST — current after Windows 223-case fail-closed
- Owner direct-Git real Windows Python3.11 gate: **223 discovered, 9 skipped, Python EXIT1**, `CLI_PUBLISH_FAILED`, filesystem `PUBLISH_FAILED`, Node EXIT0 `TAP_SUMMARY_MISSING`; checkout and compileall pass. Old 218 result superseded. No 223 PASS claim.
- Feature code now explicitly forces Node TAP `--test-reporter=tap` and reports bounded skipped test IDs; **225 discovery** (25 gate regression tests). New full Windows 225 suite remains NOT RUN. Synthetic Node v22 explicit TAP 1/1 PASS; Git-authenticated old `safe_zip` blob injected unsupported directory-open yields fail-closed `PUBLISH_FAILED`.
- First safety-critical next work: select between Windows archive fail-closed (no writes) vs separately gated native create-only publication design. Proposed B, but **require owner's explicit approval** before changing durable-archive write behavior. See `docs/WINDOWS_NTFS_PUBLICATION_OPTIONS_20261027.md`. Do NOT bypass `_sync_directory`, lower skip policy, or enable customer use merely to pass tests.
- After design approval and local synthetic implementation validation, owner uses existing `E:\DBVORA_GIT`, `git pull --ff-only`, and one `py -3.11 -B -m scripts.verify_release_gate` for refreshed failure IDs & Node TAP result. No ZIP, new clone, paid CI, public repo, main/develop promotion, deletion or real customer data.

## 2026-10-27 KST — approved Windows option B, next first native check
- **DONE**: isolated NTFS create-only Win32 proof-of-concept in `dbvora/archive/windows_ntfs_publish.py`, `scripts/windows_ntfs_publish_probe.py`, `tests/test_windows_ntfs_publish.py`. No production backup code integration, no fsync bypass. Local Linux3.13.5 synthetic **12/12 PASS**, Git blob SHA 3/3 verified, compileall PASS, standalone non-Windows fail-closed. Gate now expects **237** Python cases; real integrated 237 NOT RUN.
- **IMMEDIATE NEXT**: owner authenticated existing `E:\DBVORA_GIT` only: `git status --short` → `git pull --ff-only` → `py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish` → `py -3.11 -B -m scripts.windows_ntfs_publish_probe --synthetic-only`. Requires no ZIP, new clone, secrets, paid CI, or real/customer DB. Report full sanitized probe JSON, do not treat PASS_SYNTHETIC_ONLY as power-cut/customer proof.
- Afterwards assess real NTFS API behavior, create-only failure handling, concurrent publication and crash integrity, then integrate only if metadata/backup durability can be honestly supported; retain old Windows `PUBLISH_FAILED` otherwise. Separate earlier Node TAP and OS-dependent 9 skips from archive issues. No main/develop merge or commercial release pending validation. See `docs/WINDOWS_NTFS_NATIVE_PROTOTYPE_20261027.md`.

## 2026-10-27 KST — Windows native 12/12 + 6/6 PASS, now 15-case concurrent/exit gate
- **DONE owner actual Windows**: 12/12 `tests.test_windows_ntfs_publish` PASS 0.111s, `scripts.windows_ntfs_publish_probe --synthetic-only` PASS_WINDOWS_NTFS_SYNTHETIC_ONLY with six PASS steps. Actual Python3.11 + OS temp NTFS native tested; no source ZIP. Both crash power-loss and metadata durability remain unverified, customer_ready=false.
- **DONE code**: Added three isolated create-only checks: concurrent competing publication, child exit before publish, child exit after native move. Total isolated NTFS **15 tests**; full discovery minimum now **240**. Local Linux stand-in of new three test scenarios 3/3 PASS, but newly checked-in complete 15 and native 15 NOT yet executed.
- **IMMEDIATE next owner-native check**: in existing Git checkout, ensure clean `git status --short`, `git pull --ff-only`; then `py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish`; share result. No need rerun original 6-step probe. See `docs/WINDOWS_NTFS_NATIVE_OWNER_EVIDENCE_20261027.md`.
- **AFTER native 15 check**: plan independent Windows NTFS safe archive adapter with atomic create-once, metadata persistence limitations, SHA restore, process failure/restart/concurrency tests, opt-in only. Do **not** remove `safe_zip._sync_directory`, enable real DB, claim backup durability, promote main/develop, incur paid CI or publicize.

## 2026-10-27 KST — next W0/W2 Windows NTFS research gates (design checkpoint)
- Reviewed all current Win32 and legacy archive publication/receipt boundaries at Git SHA `9112244781e91f155d0be0e7c706e532be9c72fe`. Detailed A/B cost-maintenance-risk comparison and W0-W5 acceptance: `docs/WINDOWS_NTFS_ARCHIVE_ADAPTER_PLAN_20261027.md`.
- W0 first unfinished: owner Windows Python3.11 existing `E:\DBVORA_GIT`, clean `git status --short`, `git pull --ff-only`, then `py -3.11 -B -m unittest -q tests.test_windows_ntfs_publish` **only**. Native 15 results PENDING; original 12+6 PASS is not a substitute. Do not repeat six-step probe without new failure.
- W2 after W0: synthetic OS-temp-only shadow adapter with SQLite backup + archive + byte-exact independent restore, no production `safe_zip` rewrite, no customer DB, no overwrite, and no durability success claim from API flags. Production connection needs separate approval.
- Status of this checkpoint: design documentation committed, no new execution or product-code modifications. Full >=240 suite, original Windows archival failures, physical power durability, file:// and customer use remain BLOCKED/UNVERIFIED.

## 2026-10-27 KST — current next step W2 native and W3 synthetic recovery research
- **W0 PASS**: owner Windows isolated native 15/15 twice; second run after updated feature checkout `5ef6187`. No repeat needed.
- **W2 code + simulated verification PASS**: synthetic temporary SQLite online snapshot + ZIP, independent exact restore, original source unchanged. Eight Linux3.13 local tests PASS. Exact-source hashes recorded in `docs/WINDOWS_NTFS_SHADOW_EVIDENCE_20261027.md`. The new CLI accepts only `--synthetic-only` and no file paths; not integrated with production.
- Next native-only evidence when a Windows runner is available: `py -3.11 -B -m scripts.windows_ntfs_archive_shadow --synthetic-only` and `py -3.11 -B -m unittest -q tests.test_windows_ntfs_archive_shadow`. Do not require the owner to repeat the old 15 or six-step native probe. This native W2 gate is pending, **not** required for us to continue designing and testing W3 synthetic restart/receipt-gap logic offline.
- In parallel GPT-6 can independently review and construct W3 process-exit/restart/orphan receipt negative tests on a synthetic filesystem; production activation and real/customer data require distinct approval.
- Release minimum now >=248; the **full** native Windows CLI/test/browser gate is still fail-closed/unverified. No paid CI or privilege/production changes without owner approval.

## 2026-10-27 KST — MVP-first next unit
- Current feature includes new synthetic-only `dbvora.demo_preview`, six regression tests, and `docs/MVP_GAP_MATRIX_20261027.md`. Full gate minimum **254**, but complete source test not executed. One-command preview requires Python3.11+ and an existing absolute output folder; generates no customer DB copy.
- NEXT: read full product at latest SHA, verify real `tests.test_demo_preview` + `tests.test_export_html` + `tests.test_offline_selftest` and browser if environment allows; then implement missing multi-DB topology with explicit connectors/evidence. Avoid repeatedly asking owner to run unit tests where local/CI synthetic runners are available.
- Keep archive Windows fail-closed; only revisit NTFS zip restore after P0 visual MVP is demonstrably stable. No production/customer DB, installer, paid CI, automatic archive delete or public release without approval. User can issue `ㄱ` to continue.

## 2026-10-27 KST — accelerated P0-03 multi-DB registry integrated (workspace HTML pending GitHub integration)
- DONE in current feature: `dbvora/workspace.py` merges 2–8 explicitly selected read-only SQLite inventories into path-free schema/fk/size workspace; source SHA `643d2741f0b3e1dd8edb5ae23c794ee45ce5128d`.
- DONE tests: `tests/test_workspace_registry.py` seven real synthetic cases, source SHA `0a52ae3cd66027b92f96703de85c6b419055167a`; Linux Python3.13.5 local total **22/22** over registry seven + prototype 15 (full current GitHub checkout and production NOT RUN). Release required minimum >=261.
- SEPARATE LOCAL PROTOTYPE: `dbvora/workspace_html.py` offline multi-DB viewer with actual Chromium set_content DB/table clicking **12 checks PASS, 0 pageerrors**, plus 15 source integration tests. Source/test **NOT YET IN GITHUB**, preserved in conversation developer ZIP `DBVORA_P0_multidb_source_20261027.zip` and working container path. See `docs/P0_03_WORKSPACE_EVIDENCE_20261027.md`.
- NEXT highest priority: upload tested HTML viewer/test source into feature with exact hashes, real full-source integration, then native `file://` as supported. Do not mark multi-DB UI shipped before that. Original archive Windows durability/production release remains fail-closed and unverified.

## 2026-10-27 KST — next after P0-03 interactive offline MVP
- New GitHub source: `dbvora/workspace_html.py`, `tests/test_workspace.py`; **P0-03 multi-DB map MVP coded**, 22/22 local real SQLite targeted tests + 12 Chromium `set_content` interactions PASS. Previously separate developer zip is now superseded by exact committed trimmed source.
- NEXT 1: reconstruct/checkout full feature to run **>=276** complete Python release tests + Node DOM + offline self-test, and evaluate genuine file:// navigation in a permitted browser. Do not repeat known blocked managed Chromium URL navigation.
- NEXT 2: original design gap comparison: implement user-defined cross-database links with explicit evidence only, or measured storage trends, keeping MVP stable. Avoid PostgreSQL/real DB credentials and public deploy until approved.
- NEXT 3: safe Windows archive durability proof remains separate. Never change existing `safe_zip._sync_directory` fail-closed to force full Windows CLI green. Customer file/paid CI, backup deletion or permission change require owner approval.

## 2026-10-27 KST — next after P0-04
- DONE: cross-DB explicit declaration validation + click-through into target database/table; synthetic example is `products.id -> invoices.product_id`. A user declaration is **unverified** metadata only; no actual cross-DB SQL join or referential guarantee. Tests 36/36 Python + 9/9 Chromium set_content PASS; actual file:// blocked by managed browser policy.
- NEXT: full checkout `>=290` Python and Node/CLI synthetic release checks; if blocked, independently implement next original-design high-impact feature: measured per-table disk usage using SQLite `dbstat` only where supported (otherwise report unavailable), with WAL scope and multi-observation growth provenance explicit. Prefer local synthetic fixtures and no owner PC repeated tasks.
- Production Windows archiver remains deliberately fail-closed, physical power-loss durability, customer database approval, installer and native HTML `file://` unverified. No main/develop promotion, paid CI, public change or archive source modification.


## 2026-10-27 KST — after P0-05 storage and growth
- DONE new bounded SQLite dbstat table/index page allocation and 2-snapshot metadata-only main-file and btree delta, explicit local `--save-observation` / `--baseline-file`. Previous 36 tests + new 14 **50/50 Linux synthetic real SQLite PASS**; Chromium set_content sizing/trend click-through PASS. See `docs/P0_05_STORAGE_EVIDENCE_20261027.md`.
- NEXT: full private source checkout **>=304** Python release gate, Node, CLI and package tests; real file:// browser and Windows Python3.11 P0-05 native constraints remain unverified, avoid reattempting managed Chromium blocked navigation.
- Continue original design gap closing: measured resource observations only with accurate provenance; consider safe manual repeat snapshot UI before any unattended schedules, and keep Windows archive release blocked until proven durable. **No** customer DB use, paid CI, main promotion, deletion, force pushes or source backup changes.

## 2026-10-27 KST — after P0-06 integrated synthetic P0
- **DONE:** 13-check real product P0 integrated synthetic command `python -m scripts.mvp_offline_gate` returns 0 and stable JSON; eight dedicated fail-closed tests, **58/58 P0 targeted Linux3.13.5 PASS** (50 prior + 8). Exact source and test Git blob SHA verified, documentation evidence recorded.
- **NEXT high priority:** run full private checkout `python -m scripts.verify_release_gate` (>=312 tests, Node DOM, CLI, preflight) on *authorized* complete-source execution environment; current isolated Linux container couldn't clone private repo because github.com DNS unavailable. Maintain NOT_RUN for full gate; do not claim release-ready. A synthetic-only read-only scanner may advance offline while waiting for complete checkout, but no Windows customer archive activation.
- **NEXT design/security:** review standalone workspace HTML against malicious names and huge inventories, metadata-only snapshot authenticity/permission and source mutation races. Add bounded negative cases before manual observation UX polish. Genuine file:// and Windows Python3.11 P0-05/06 remain unverified. No owner manual action needed merely for local Python unit tests.
- **BLOCKERS:** native Windows archive `PUBLISH_FAILED` (fail closed), power-cut metadata durability, optional ZSTD tool, browser navigation managed-policy. No paid CI, public/promote/delete customer backups/credentials without owner consent.

## 2026-10-27 KST — P0-07 next action
- **DONE:** Shared bounded, strict JSON parser for user-selected manifest/baseline; replaced vulnerable path.stat -> separate read_text sequences with open descriptor identity, size cap and fail-closed duplicate-key/nonstandard-float parser. **12 new security tests**, local actual P0 subset **70/70 PASS**, P0 integration **13/13 PASS**.
- **NEXT:** `export_workspace` produces optional HTML plus observation JSON in sequence; if latter write fails, orphan HTML may remain. Use safe staged/published output semantics and preserve prior user files; test injected failure and no replacement. Do not delete/alter real customer DB.
- **NEXT:** bigger malicious schema identifier and report cap tests. Full private >=324 Python, Node TAP, CLI + FS preflight must be executed in complete checkout; this sandbox clone cannot resolve github.com DNS. Windows Python3.11 and actual file:// browser are independent pending gates.
- Archive NTFS production remains fail-closed; no paid CI, main/dev promotions or customer data without consent.


## 2026-11-11 KST — current next task after P0-08 (replaces historical first-pending text)
1. Verify new P0-08 report/observation failure cleanup with source-backed SQLite tests on a **complete authorized checkout**; run `python -B -m unittest -v tests.test_publication_cleanup tests.test_workspace_publication tests.test_workspace_storage` and `python -m scripts.verify_release_gate` (>=336 discovered Python tests).
2. Keep 55% product completion until evidence supports advancement; full Windows browser/NTFS and power-loss remain separate unverified gates. Failure cleanup is best-effort, not cross-file atomic publish guarantee.
3. For the 70% roadmap, prefer demonstrable read-only observability and opt-in PostgreSQL connector contract vs. unsafe production archive changes. No customer DB, paid CI, automatic deletion, overwrite, permission change, main/develop merge or deployment without approval.
4. Source P0-08 commits `0518269d8b1686f4dae686ebaec358eca41a4a7d` and `9d1d4b0898c5293f34f01feff4894c5ed97aabb1`; see `docs/P0_08_PUBLICATION_RECOVERY_20261111.md`.

## 2026-11-11 KST — next after P0-09 (latest)
- **DONE, isolated:** schema advisory pure Python module, SQLite in-memory catalog tests 9 PASS, previous P0-08 cleanup 7 PASS; exact source/test Git hashes and new UI snippet JS syntax checked.
- **FIRST GATE:** from a complete authorized private feature checkout run `python -B -m unittest -v tests.test_schema_review tests.test_schema_review_ui tests.test_publication_cleanup tests.test_workspace_publication`; then `python -m scripts.verify_release_gate` (>=347 discovered), collect exact Python/Node/ZIP/Windows outcomes. New full-source UI cases not yet executed.
- **THEN:** source-backed Windows3.11 synthetic offline HTML test; prioritize read-only utility rather than unapproved real DB access. Existing original archive customer/NTFS durability fail-closed unchanged, no paid CI/customer files/external data/overwrite/new project/production.
- **Completion:** DBVORA remains 55% until full relevant evidence; next 70% steps require substantive working delivered capabilities. `docs/P0_09_SCHEMA_REVIEW_20261111.md` is P0-09 evidence.

## 2026-11-11 KST — NEXT after P0-10
- Completed code in a8169a969db919f336a2fc68343a63f291513960: SQLite ASCII FK target casing, preserve Unicode distinctness. Local isolated SQLite/P0-08/P0-09 suite 22/22 PASS with exact SHA.
- First unresolved: complete private checkout -> run python -B -m unittest -v tests.test_sqlite_identifiers tests.test_workspace_registry tests.test_schema_review tests.test_schema_review_ui tests.test_publication_cleanup tests.test_workspace_publication, then python -m scripts.verify_release_gate (>=355).
- Follow with Windows Python3.11 native offline HTML visual interaction and safe archive verification; no real customer DB or paid CI without approval.
- Product 55% (unchanged), 70% target remains. docs/P0_10_SQLITE_IDENTIFIER_CASE_20261111.md is evidence. Unverified gate is not failure nor PASS.

## 2026-11-11 KST — latest after P0-11
- P0-11 code 47e9b7c840bcd9fd6613b69d58f3736cd43161c7 fixes offline SVG FK edge when SQLite ASCII table case differs; new DOM VM test appended to existing Node TAP gate. No customer/Production change, no increase beyond 55% commercial completion.
- First: complete private checkout => `node --test tests/test_ui_dom.cjs` + `python -B -m unittest -v tests.test_workspace_registry tests.test_schema_review_ui tests.test_workspace_publication`; then `python -m scripts.verify_release_gate` (>=355 Python expected). Inspect source-backed failures before more features.
- If full checkout remains unavailable due DNS, pivot to another product/authorized checkout rather than invent a PASS or repeat failed clone. Windows file:// browser and archive power loss remain separate needed acceptance. Source detail docs/P0_11_FK_GRAPH_ASCII_20261111.md.

## 2026-11-11 KST — first next action after P0-12
- Confirmed Node22 exact-source TAP 1/1 PASS, Chromium 3/3 synthetic document-only PASS; file:// blocked by runner policy, real local HTML still **NOT VERIFIED**. Optional browser script added 55749bfc (runs without customer DB; Playwright Python optional, no release gate widening).
- First complete authorized feature checkout: node --test tests/test_ui_dom.cjs; python -B -m unittest -v tests.test_workspace_registry tests.test_schema_review_ui tests.test_workspace_publication; python -m scripts.verify_release_gate (>=355). Do not count only isolated previous Python 22 as complete checkout proof.
- Then optional python -m scripts.browser_workspace_smoke --chromium PATH (real file://) in unrestricted authorized Windows browser; only --document-only is safe partial rendering proof. Validate actual original full HTML template (not synthetic shell), archive restore/NTFS and customer release later.
- DBVORA 55% unchanged / 70% goal; no paid CI/customer files/permission/Production changes. Details docs/P0_12_BROWSER_SMOKE_20261111.md.
