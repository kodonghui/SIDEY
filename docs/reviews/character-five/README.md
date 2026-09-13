# 캐릭터 5종 검토 패키지

현재 단계는 **새 쿼카 외형·4종의 보정 동작·물건 회전/충돌 승인 대기**다. 시바·오리·똥·떡볶이는 원작 외형 유지가 승인됐으며 발목 단절과 잘못된 동작은 수정한다. 쿼카는 동물 정체성만 유지해 새로 해석한다. 선택 물건은 테니스공·목욕탕 고무 오리·휴지 뭉치·어묵꼬치·잎사귀다. 물방울과 풀 뭉치는 채택하지 않는다. 현재 작업은 [초안 PR #93](https://github.com/sidey-app/SIDEY/pull/93)에 보존하며 전체 승인 전에는 main에 병합하지 않는다.

## 로컬 검토

저장소 루트에서 실행한다. 웹 배포나 앱 실행은 하지 않는다.

```sh
python3 docs/reviews/character-five/verify_package.py
python3 docs/reviews/character-five/audit_frames.py --self-test
python3 docs/reviews/character-five/test_verify_package.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory docs/reviews/character-five
```

브라우저에서 <http://127.0.0.1:8765/>를 연다. 실제 원본 90프레임, 기본 자세·실루엣, 프레임 선택·재생·배경·반전·네 가장자리와 두 idle 타이밍을 비교한다. 검토 도구의 22pt/s 정속 이동은 앱의 일반 최대 산책 속도 비교용이다. 앱의 가속·휴식·겹침 회피까지 재현하는 검증은 아니다.

브라우저 회귀 검사는 설치된 Playwright 환경에서 `node docs/reviews/character-five/verify_browser.cjs`로 실행한다. 필요하면 `NODE_PATH`로 Playwright 모듈 위치, `SIDEY_REVIEW_CHROMIUM`으로 Chromium 실행 파일, `SIDEY_REVIEW_URL`로 다른 로컬 포트를 지정한다. 화면·결과 JSON은 `SIDEY_REVIEW_OUTPUT`(기본 `/private/tmp/character-five-browser-evidence`)에 기록한다. 숨김 처리는 합성 `document.hidden` 이벤트로 검사하며 OS 창 최소화 검증과 구분한다.

현재 캐릭터 후보는 `candidates/character-v2/`에 둔다. 시바·오리·똥·떡볶이의 `appearance.png`는 원본 base 0번과 RGBA가 동일하며, 기본·동작 시트는 총 72프레임의 발 연결과 던지기 중복을 보정했다. `python3 docs/reviews/character-five/build_character_repairs.py`는 원본·수정 시트·픽셀 변경 기록을 읽기 전용으로 대조한다(`--write`는 명시적 재생성). 원본 90프레임은 `originals/`에 변경 없이 보존한다.

쿼카는 `build_quokka.py`의 새로운 24×24 픽셀 맵이며, 목도리 없는 갈색 털·둥근 귀·웃는 주둥이·작은 앞발을 사용한다. `concepts/quokka-v2.png`는 ImageGen 방향 참고이고 실제 승인은 `candidates/character-v2/pixel_quokka/appearance.png`를 기준으로 한다. 쿼카 전체 동작은 기본 자세 승인 후 제작한다.

선택 물건 5종의 16×16 후보는 `candidates/keepsakes-v2/<id>/sprite.png`에 둔다. 회전 8장·충돌 4장과 소멸을 검토한다. 목욕탕 고무 오리는 기존 `throwable_squeaky_duck` 시트를 그대로 재사용한다. 나머지는 승인된 콘셉트를 명시적 픽셀 맵과 결정적 애니메이션으로 구성한 새 규격 후보이며, 콘셉트 승인만으로 새 프레임 승인을 채우지 않는다. `build_keepsakes.py`와 `keepsake-changes.json`에 생성 규칙·출처·해시·회전 중심 검사를 기록한다.

| 캐릭터 | 선택 물건 | 현재 상태 |
| --- | --- | --- |
| 시바견 | 테니스공 | 콘셉트 승인, 규격 프레임 검토 |
| 오리 | 목욕탕 고무 오리 | 사용자 요청으로 물방울 대체, 기존 삑삑 오리 시트 재사용 검토 |
| 똥 | 휴지 뭉치 | 콘셉트 승인, 규격 프레임 검토 |
| 떡볶이 | 어묵꼬치 | 콘셉트 승인, 규격 프레임 검토 |
| 쿼카 | 잎사귀 | 사용자 최종 선택, 규격 프레임 검토 |

`appearance-v1/`과 `concepts/keepsakes-v1.png`는 과거 비교 자료다. 생성 보드의 ORIGINAL 열도 재생성된 그림이며 정확한 원본이 아니다. 예전 선택 기록은 `history/approvals-v1.json`에 보존하고 현재 승인은 `approvals.json`에서만 판정한다.

## 원본·기여 기록

- 원작 기여: **정지유 (@jungjiyu)**, Git Author `jiyu.jung <libraryofjiyu@gmail.com>`.
- 원본 [PR #27](https://github.com/sidey-app/SIDEY/pull/27), 고정 HEAD `ec8dc51cbc0c3eb665c0bca76e2dd7d8ec42fb27`.
- 실제 자산 작성 커밋: `f5f5e63cff7b348ab86433af9b4d72c26f05513f`, AuthorDate `2026-09-03T17:23:45Z`.
- 원본 공동 작성자: `Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- 이관 커밋은 원작자의 PNG 10개만 포함하며 위 작성자·작성일·공동 작성자를 보존한다. 도구·생성 콘셉트·후속 픽셀 수정은 이관 커밋과 분리한다.
- 원본 파일과 SHA-256은 `package.json`; 개별 90프레임 RGBA 해시와 결함은 `source-audit.json`에서 확인한다. 원본 PNG는 PR HEAD 및 최초 자산 커밋 양쪽과 byte 단위로 일치한다.
- 서면 계약: **완료 — 사용자 제공 계획의 확인에 근거함**. 계약 원문·정산 정보는 저장하지 않는다.
- 자산 이용 조건은 [패키지 라이선스 적용 범위](LICENSE.md)와 [SIDEY Paid Asset License 1.0](../../../assets/PAID_ASSET_LICENSE.md)을 따른다. 공개 열람이 다른 제품의 사용·수정·판매 허가를 뜻하지 않는다.

원본 PR의 다른 25종, 하트 쿠션·아메리카노, 앱·상품·마이그레이션·배포 사본은 이관하지 않는다. 기존 main의 활성 자산과 상품은 유지한다. `docs/` 경로는 현재 Pages push 경로 필터에 해당하지 않는다.

## 확인한 결함

- 90프레임 모두 24×24, RGBA·sRGB·hard alpha, 최하단 불투명 행 y=20(하단 3px 여백).
- 5종의 기본 시트 1·3·5 및 동작 시트 6: y=19 전체가 비어 발 6px가 분리됨. 총 20프레임.
- 시바 throw 2=3, 떡볶이 throw 0=1 중복. 상태 간 정상 자세 재사용은 자동 제거하지 않는다.
- 셀 경계 접촉 22프레임. 실제 잘림 여부는 시각 검토가 필요하다.

## 승인·병합 순서

1. 외형 방향과 실제 기본 자세·실루엣 승인 → 전체 기본 10·동작 8, 총 90프레임 수정 → 전체 동작 승인 → 움직임·idle 타이밍 승인.
2. 물건 기획 선택 → 선택된 5종의 회전 8·충돌 4, 총 60프레임 제작·시각 승인 → 물건당 A/B 충돌음 제작·승인 → 합성 장면 최종 승인.
3. `approvals.json`에 후보 ID·대상 경로·SHA-256·실제 사용자 선택과 근거를 기록한다. 미응답은 pending이다. 파일이 바뀌면 이전 승인은 유효하지 않다. 생성 콘셉트 승인만으로 최종 프레임 승인을 채우지 않는다.
4. `python3 docs/reviews/character-five/verify_package.py --require-approved`가 모든 최종 산출물·승인·해시를 확인해야 병합할 수 있다. 현재는 의도적으로 실패해야 한다.
5. 독립 최종 diff 검토와 정확한 head의 필수 CI 이후 `scripts/workflow.py check/finish`로 후속 PR을 merge commit으로 병합하고 기본 main 작업 폴더를 갱신한다.
6. 병합 뒤 #27에 5종 채택 결과와 후속 PR 링크를 댓글로 남겨 종료한다. 원본 브랜치 force push·삭제는 하지 않는다.
7. main에 비어 있지 않은 원작자 이관 커밋이 포함되는지, GitHub commit author가 `jungjiyu`인지 확인한다. [GitHub 기여자 안내](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors)에 따라 계정 이메일 연결과 기본 브랜치 반영을 확인하고 집계 화면 갱신은 별도로 기록한다.

앱·상점·서버 연결, 플랫폼 배포 사본, 버전 변경·태그·릴리스·스토어 업로드는 이후 **macOS 심사 완료 및 업데이트 작업 지시**가 있을 때 진행한다. 후속 구현 계약은 [HANDOFF.md](HANDOFF.md)에 둔다.
