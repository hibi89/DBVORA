# DBVORA 상업 배포 및 타사 라이선스 검토 — 2026-11-14 KST

**현재 결론: 판매 RELEASE HOLD, 법적 권리 검토 부분 완료.** 이 기록은 법률 자문이나 재배포 허락의 발급이 아니다. GitHub 원본 `hibi89/DBVORA`는 2026-11-14 조회 기준 **Public**; root LICENSE/NOTICE 및 고객 사용권 정책 미확정. 상품을 게시하기 전에 사용자 소유권·기여자/고객 약속·타사 의존성·판매 조건을 확인해야 한다. 기존 저장소 공개/비공개 정책은 무단 변경하지 않는다.

## 배포 형태별 A/B
| 형태 | 무상 배포 기술 | 장점/현금 비용 | 권리·품질 제약 | 현재 판단 |
| --- | --- | --- | --- | --- |
| A: Python 원본 ZIP (56+ files), 고객 PC가 Python3.11 설치 | 무료, stdlib 오프라인 SQLite HTML은 pip 의존 없음 | 즉시 QA 쉬움·작은 ZIP | 소스 노출, Python 필요, 서명/소유권·고객 재배포권 문서 미완 | **검수용 우선** |
| B: PyInstaller 단독 core EXE | 무료 공개 GitHub Windows runner; 실행파일에 Python runtime 포함 | Windows 사용성 향상·개별 Python 설치 불필요 | 서명/SmartScreen·훼손 방지·EXE 버전/AV·서드파티 고지 추가, 현재 *합성 데모만 가능* | **검증된 사용자용 데모만**, 판매금지 |

판매용은 별도 사용자 승인 후 선택하며, A/B 어느 쪽도 **지금 판매 가능함을 의미하지 않는다**.

## 확인된 1차 법적 출처/정확 적용 범위
| 구성 요소 | 공식 라이선스 확인 | 우리가 실행하는 방식/배포 여부 | 주의 |
| --- | --- | --- | --- |
| DBVORA 자체 소스 | 사용자 원본에 독립 LICENSE/NOTICE 부재 | 현재 Public 저장소, 개발자 소스 ZIP에도 DBVORA 자체 사용권 계약 없음 | Public 노출은 원본 저작권 양도·무제한 재사용 허락이 아님. 고객별 라이선스는 소유자 확인·승인 필요 |
| FastAPI (선택 UI) | MIT — https://github.com/fastapi/fastapi/blob/master/LICENSE | `pip install .[ui]` 외부 설치; core-only EXE에는 묶지 않음 | 상업 배포/재배포 시 정확한 MIT 저작권·허가 고지 필요 |
| Uvicorn (선택 UI) | BSD-3-Clause — https://pypi.org/project/uvicorn/ | 외부 설치; core-only EXE 제외 | BSD 저작권·면책 고지 확인 및 보존 |
| Psycopg 3 + psycopg-binary (선택 PG) | LGPL-3.0-only — https://pypi.org/project/psycopg/ 및 https://pypi.org/project/psycopg-binary/ | PG 옵션 실행 시 별도 pip 설치, 현재 core-only EXE 미포함 | LGPL 소스·재링크 조건 등 **실제 번들 형태별 의무 검토**. PG가 들어간 독립 EXE를 확인 없이 상용 배포하지 않음 |
| PyInstaller 빌드 도구 | GPL 2.0 + 상업 빌드 예외 — https://www.pyinstaller.org/en/stable/license.html | Windows runner에서 소유자 합성 데모 EXE 빌드 | 예외가 *다른 의존성* 권리까지 면제하지 않음. 현재 빌더 자체 변경 없음 |
| PostgreSQL 서버 | PostgreSQL License — https://www.postgresql.org/about/licence/ | **CI 임시 로컬 검증 Docker**에서만 실행, 고객 배포본에 DB 서버 미포함 | 판매 패키지에 서버 번들되지 않으며 실제 고객 서버 접근은 별도 승인 |
| Zstandard CLI | 별도 실행기 요구, 현 ZIP에 미포함 | core-only EXE에 미포함 | 향후 실행기 동봉 시 해당 배포판의 라이선스·출처·고지 별도 확인 |

**미조사**: optional UI/PG 전체 *전이 의존성*의 실제 잠금 버전/LICENSE 원본, 상업적 번들 저작권 고지, Windows Defender/SmartScreen 테스트, 코드서명, 고객지원·환불·업데이트 정책. README의 구 문구(private/old 테스트)는 최신 `STATUS.md`/GitHub 실행 결과를 우선한다.

## 권고 고객 사용권 초안의 결정 항목 (사용자 승인 전 변경 금지)
- 사용 허가의 당사자/사업자(실명·상호 표기), 소프트웨어 저작권 소유자/기여자 동의 및 고객의 유상 사용권 여부
- STANDARD/DELUXE/PREMIUM별 **제공물**, PC 수·사용 기간·업데이트 기간·지원 시간, 저장·복제·재판매·재배포 허용 범위
- 사용자 PC Windows 10/11 지원 조건, 초기 설치·서비스/교육 제공 여부, 장애 책임·데이터 복구 지원·고객 DB 연결 금지/허가 범위
- 환불/수정 및 납품 승인 기준은 당시 크몽 정책, 전자상거래·소프트웨어 라이선스 법규와 충돌하지 않도록 검토
- 라이선스 서면/README/NOTICE, 종속성 고지. 자체 root LICENSE 자동 생성/변경 금지(권한·계약 행위).
- 상품 등록/출시/가격 변경은 최종 사용자 승인 후만 수행하고 실제 링크·등록 증거 없이는 '등록완료' 금지

**판매 문구 제한**: '무손실 보장/전원 차단 보장', '스마트스크린 통과', '실 고객 PG 지원 보장', 'ZIP 대비 일률적 고압축', 'EXE 완성 제품' 등 실제 시험·권리 없는 절대 주장 금지. 합성 데모는 합성 데모로만 표기.

## 이번 사용자 PC 최소 실행 근거
- Synthetic ZIP: https://github.com/hibi89/DBVORA/actions/runs/43544666021
- 실제 PG16 localhost TLS verify-full 읽기전용, FK·HTML·거부 인증서 5/5: https://github.com/hibi89/DBVORA/actions/runs/43545900975
- 실제 Windows core-only unsigned EXE 생성·실행: https://github.com/hibi89/DBVORA/actions/runs/43546585469
- 사용자 실제 Windows 10/11 수용과 고객 배포·라이선스는 여전히 미확인. 2026-11-14 오후 1시(KST) 통합 사용자 요청 알림으로 모음.
