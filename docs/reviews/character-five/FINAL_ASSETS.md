# 승인된 출시 대기 파일

캐릭터 5종·90프레임, 물건 5종·60프레임, 선택 충돌음 5개와 설명 10개를 아래 파일로 확정했다. 각 파일의 SHA-256과 승인 응답은 `package.json`·`approvals.json`에 고정한다. 승인 기본 자세 5개도 패키지에 보존한다.

후속 앱 연결 시 `python3 docs/reviews/character-five/verify_package.py --require-approved`를 먼저 실행한다. 아래 자산만 런타임 연결 대상으로 사용하며, 과거 후보·원본 녹음·생성기·미리보기 도구는 앱에 포함하지 않는다. 현재 앱·상품·버전·릴리스는 변경하지 않았다.

| 캐릭터 | 기본 / 동작 시트 | 물건 시트 | 선택 충돌음 | 이름·설명 |
| --- | --- | --- | --- | --- |
| 시바견 (`pixel_shiba`) | [기본](candidates/character-v2/pixel_shiba/base.png) / [동작](candidates/character-v2/pixel_shiba/throw_hit.png) | [물건](candidates/keepsakes-v2/tennis_ball/sprite.png) | [소리 1](candidates/audio-v2/tennis_ball/1.wav) | [설명](copy-v1/pixel_shiba.json) |
| 오리 (`pixel_duck`) | [기본](candidates/character-v2/pixel_duck/base.png) / [동작](candidates/character-v2/pixel_duck/throw_hit.png) | [물건](candidates/keepsakes-v2/rubber_duck/sprite.png) | [기존 소리](candidates/audio-v2/rubber_duck/original.wav) | [설명](copy-v1/pixel_duck.json) |
| 똥 (`pixel_poop`) | [기본](candidates/character-v2/pixel_poop/base.png) / [동작](candidates/character-v2/pixel_poop/throw_hit.png) | [물건](candidates/keepsakes-v2/tissue_ball/sprite.png) | [소리 2](candidates/audio-v3/tissue_ball/B.wav) | [설명](copy-v1/pixel_poop.json) |
| 떡볶이 (`pixel_tteokbokki`) | [기본](candidates/character-v2/pixel_tteokbokki/base.png) / [동작](candidates/character-v2/pixel_tteokbokki/throw_hit.png) | [물건](candidates/keepsakes-v2/fish_cake_skewer/sprite.png) | [소리 1](candidates/audio-v2/fish_cake_skewer/1.wav) | [설명](copy-v1/pixel_tteokbokki.json) |
| 쿼카 (`pixel_quokka`) | [기본](candidates/character-v3/pixel_quokka/base.png) / [동작](candidates/character-v3/pixel_quokka/throw_hit.png) | [물건](candidates/keepsakes-v2/leaf/sprite.png) | [소리 1](candidates/audio-v3/leaf/A.wav) | [설명](copy-v1/pixel_quokka.json) |

오리는 기존 `throwable_squeaky_duck` 상품의 시트와 승인 꽥 음원을 재사용한다. 신규 중복 상품을 만들지 않는다. idle은 기존 0.55/0.55초, walk는 0.16초/프레임·22pt/s, 재생은 30 FPS를 유지한다.

원작자 정지유 (@jungjiyu)의 원본 10개 이관 커밋: `a7e0af2406ce8b1ee0b2aeae653f66c4ed35087a`. 수정·도구 커밋과 분리해 원작 Author·AuthorDate·공동 작성자를 보존했다.
