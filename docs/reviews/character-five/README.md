# 캐릭터 5종 검토 패키지

현재 단계는 **24×24 기본 자세 승인·쿼카 물건 선택 대기**다. 사용자는 원작 색감·표정을 유지하는 실루엣 보강 방향과 원본 픽셀의 코드 수정을 승인했다. 시바 테니스공·오리 물방울·똥 휴지 뭉치·떡볶이 어묵꼬치를 선택했고 쿼카는 잎사귀·풀 뭉치 두 안을 예시 페이지에서 비교하도록 요청했다. 출시 대기 패키지 완성이나 최종 시각 승인을 뜻하지 않는다. 시바견·오리·똥·떡볶이·쿼카의 기존 ID를 유지하며, 전 단계 승인 뒤에만 후속 PR을 main에 병합한다.

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

`candidates/appearance-v1/concept-board.png`는 ImageGen으로 만든 **외형 방향 콘셉트**다. 이미지 안의 ORIGINAL 열까지 다시 그려진 그림이며 원본 PNG의 정확한 복사나 최종 24×24 프레임이 아니다. 정확한 원본은 페이지의 canvas와 `originals/`에서 확인한다. 이 보드를 규격 자산으로 축소해 자동 채택하지 않는다. 실제 원본 픽셀의 색감·표정을 보존한 기본 자세 비교안을 다시 검토한 후 전체 프레임에 적용한다.

`concepts/keepsakes-v1.png`는 아래 물건의 기획 후보이며 최종 16×16 그림이 아니다.

실제 기본 자세 후보는 `candidates/appearance-v1/pixel_*.png` 5개다. `python3 docs/reviews/character-five/build_appearance.py`로 원본 0번에서 재생성하며 새 색을 추가하지 않는다. 원본·변경 좌표·해시는 `appearance-changes.json`에 기록한다. 똥·떡볶이의 기본 0번은 그대로 보존했고, 결함이 있는 다른 프레임의 발 연결과 동작 수정은 기본 자세 승인 뒤 진행한다.

| 캐릭터 | A | B |
| --- | --- | --- |
| 시바견 | 뼈다귀 장난감 / 가벼운 장난감 톡 | 테니스공 / 탄성 있는 통 |
| 오리 | 물방울 / 짧은 물방울 팝 | 작은 물고기 / 물기 있는 찰박 |
| 똥 | 휴지 뭉치 / 가벼운 종이 퍽 | 미니 뚫어뻥 / 짧은 고무 뽁 |
| 떡볶이 | 떡 한 조각 / 말랑한 찹 | 어묵꼬치 / 가벼운 촵 |
| 쿼카 | 잎사귀 / 얇은 잎 파삭 | 풀 뭉치 / 부드러운 풀 퍽 |

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
