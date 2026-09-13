# 승인 후 앱 연결 명세

캐릭터 5종과 물건 5종의 외형·동작, 설명 10개는 승인되었다. 테니스공·어묵꼬치는 audio-v2 소리 1, 오리는 기존 그림·승인 꽥 음원 재사용으로 확정했다. 휴지는 audio-v3 B(소리2), 잎사귀는 audio-v3 A(소리1)와 해당 합성까지 승인되었다. [최종 파일 목록](FINAL_ASSETS.md)을 따른다. 이 문서만으로 앱 연결이나 출시를 실행하지 않는다.

캐릭터 ID는 `pixel_shiba`, `pixel_duck`, `pixel_poop`, `pixel_tteokbokki`, `pixel_quokka`를 유지한다. 기본 240×24 시트는 idle 0–1, walk 2–5, doze 6–7, offline 8–9이며 동작 192×24 시트는 throw 0–3, hit 4–7이다. 24×24 셀, RGBA 8-bit·sRGB·hard alpha·정수 nearest-neighbor와 y=20 발끝 기준선을 유지한다. 실시간 그림자는 추가하지 않는다.

idle은 미리보기 기본값인 기존 main의 0.55/0.55초를 유지한다. “나머지 다 ok” 응답을 해당 기본값 유지 승인으로 `approvals.json`에 기록했다. PR의 2.4/0.3초 제안은 채택하지 않았다. walk는 프레임당 0.16초, 일반 최대 속도 22pt/s, 30 FPS다. doze는 0.8초, offline은 1.2초/프레임, throw는 총 0.4초, hit는 총 0.44초, release 지연은 0.2초다. 실제 앱 가속·휴식·겹침 회피는 기존 구현을 따른다.

애착 물건은 캐릭터와 별도 상품이다. 현재 기획 후보 이름이나 ID를 상품 카탈로그에 자동 등록하지 않는다. 최종 선택마다 회전 8장과 충돌 4장을 16×16 셀의 192×16 RGBA·sRGB·hard alpha 시트로 준비한다. 회전 중심 흔들림, 의도하지 않은 중복, 잔상·잘림은 프레임 검사와 실제 재생으로 확인한다.

효과음은 물건별 충돌음만 사용한다. 물건별 후보를 WAV 48 kHz·16-bit PCM·mono로 제작하고 출처·이용 조건·길이·peak/RMS 레벨·SHA-256을 기록한다. 기존 승인 충돌음과 비교한 청감·레벨 기록을 남기고 물건별 소리 번호 버튼으로 단일 청취와 애니메이션 합성을 제공한다. 충돌 한 번에 소리 한 번이다. 사용자의 재생 조작 전에는 소리를 내지 않고 비교 종료·페이지 숨김 때 예약과 현재 재생을 모두 중지한다. 발사·비행음은 만들지 않는다.

전체 사용자 승인·독립 diff 검토·필수 CI 뒤 패키지만 main에 병합한다. 이후 사용자의 macOS 업데이트 지시 시점에 최신 배포 이력을 확인하고 신규 콘텐츠 추가의 MINOR 기준으로 버전·build를 결정한다. 앱 연결은 `macos/*`, 필요한 상품·서버 변경은 별도 `shared/*`로 분리한다. Windows 후속은 별도 작업이며 이번 승인이나 macOS 구현으로 자동 적용하지 않는다.

## 후속 배포 작업에서 가져갈 파일

현재 요청은 파일 저장·문서화·PR 검토까지다. 검토 페이지는 동작 카드와 물건별 직접 소리 재생 버튼으로 단순화한다. 아래 후보와 승인 기록이 모두 확정된 뒤 배포 작업에서 가져다 쓴다. 미리보기용 JavaScript/Python 도구는 앱에 포함하지 않는다.

| 캐릭터 ID | 물건 검토 ID | 이름·설명 파일 | 기존 상품 재사용 |
| --- | --- | --- | --- |
| pixel_shiba | tennis_ball | copy-v1/pixel_shiba.json | 없음, 후속 상품 작업에서 ID·가격 결정 |
| pixel_duck | rubber_duck | copy-v1/pixel_duck.json | throwable_squeaky_duck 기존 그림·승인 꽥 소리 재사용 확정, 중복 상품 생성 금지 |
| pixel_poop | tissue_ball | copy-v1/pixel_poop.json | 없음, 후속 상품 작업에서 ID·가격 결정 |
| pixel_tteokbokki | fish_cake_skewer | copy-v1/pixel_tteokbokki.json | 없음, 후속 상품 작업에서 ID·가격 결정 |
| pixel_quokka | leaf | copy-v1/pixel_quokka.json | 없음, 후속 상품 작업에서 ID·가격 결정 |

캐릭터 시트는 시바·오리·똥·떡볶이가 `candidates/character-v2/<캐릭터 ID>/{base,throw_hit}.png`, 쿼카가 `candidates/character-v3/pixel_quokka/{base,throw_hit}.png`이며, 물건 시트는 `candidates/keepsakes-v2/<물건 검토 ID>/sprite.png`다. 각각 기본 10장·동작 8장·물건 12장이다. `appearance.png`는 승인 비교용 기본 자세이며 앱 런타임에는 시트를 사용한다.

음원은 테니스공·어묵꼬치가 `candidates/audio-v2/<물건 검토 ID>/{1,2,3}.wav`, 오리가 `candidates/audio-v2/rubber_duck/original.wav`, 휴지·잎사귀가 `candidates/audio-v3/<물건 검토 ID>/{A,B}.wav`다. 휴지·잎사귀 A/B는 화면 소리 1/2에 대응한다. 최종 선택은 오직 `approvals.json`의 캐릭터별 `audio.selection`을 `package.json`의 `candidate_id`에 연결해 찾는다. 테니스공·어묵꼬치는 각각 1, 오리는 기존 소리로 선택됐고 휴지는 B(소리2), 잎사귀는 A(소리1)로 최종 확정했다. 단순히 눌러 본 소리나 카드의 기본 합성 소리를 출시 선택으로 간주하지 않는다. `references/impact-baseball.wav`는 청취 기준이고 새 상품에 포함하지 않는다.

이름·고유 설명은 해당 `copy-v1/<캐릭터 ID>.json`의 `character`와 `keepsake`에 있다. 캐릭터·물건 설명을 묶은 파일별 `descriptions` 승인 5개가 기록되어 있다. 설명 파일 안의 status는 제작 당시 상태이며 최종 승인 상태는 해시에 연결된 `approvals.json`을 기준으로 한다. 승인 후 상태 문구만 바꾸기 위해 원본 파일을 재작성하지 않는다. 가격·스토어 상품 ID·상품 노출 상태는 이 파일에 없으며 별도 상품 작업에서 정한다.

원본 `originals/`, 이전 후보·콘셉트, `history/`, 생성기, 감사 기록은 출처·승인 이력으로 보존한다. 출시 패키지에 과거 후보나 모든 A/B 음원을 일괄 복사하지 않는다. 실제 런타임 연결 대상은 최종 승인된 시트·선택 WAV·설명뿐이다.

후속 담당자는 먼저 `verify_package.py --require-approved`를 실행해 최종 승인과 SHA-256을 확인한다. 그 뒤 최신 플랫폼 배포 이력·카탈로그를 읽는다. 공통 manifest·캐릭터↔물건↔선택 충돌음 매핑·상품·서버 권한은 별도 `shared/*`에서 연결하고, 앱 구현과 플랫폼 배포 사본은 각각 `macos/*`·`windows/*`에서 적용한다. 이번 PR은 이 연결이나 버전 변경을 실행하지 않는다.
