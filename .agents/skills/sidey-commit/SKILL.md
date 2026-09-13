---
name: sidey-commit
description: Write and review SIDEY commit messages with conventional types, explicit distribution scopes, and Korean descriptions. Use before creating commits, supplying workflow finish messages, or writing PR titles that become commit subjects.
---

# SIDEY 커밋 컨벤션

직접 작성하는 커밋 제목은 반드시 `type(scope): 한국어 설명` 형식을 따른다. `scripts/workflow.py finish --message`와 커밋 제목으로 사용될 PR 제목에도 적용한다.

## Type과 scope

- Type은 실제 변경에 맞게 `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, `chore`, `revert` 중에서 고른다. 모든 변경을 `feat`로 쓰지 않는다.
- Scope는 대소문자를 포함해 아래 표기를 그대로 사용한다. 브랜치 이름만 보고 판단하지 말고 실제 diff와 영향을 받는 빌드 타깃을 확인한다.

| Scope | 적용 대상 |
| --- | --- |
| `macOS-Direct` | macOS 직배포판 전용 변경 |
| `AppStore` | macOS App Store판 전용 변경 |
| `macOS-Direct / AppStore` | 두 macOS 배포판에 함께 적용되는 변경 |
| `Windows` | Windows 구현·빌드·설치·전용 문서 변경 |
| `Shared` | 공용 문서·스킬·백엔드·웹·프로토콜·저장소 공통 작업 |

공유 변경이 여러 플랫폼에 영향을 주더라도 `Shared`를 사용한다. Scope 표기는 기존 플랫폼 브랜치 및 커밋 격리 규칙을 완화하지 않는다.

## 한국어 설명

- 콜론 뒤 제목 설명과 선택적인 커밋 본문은 반드시 한국어로 작성한다. Type과 scope는 위 표기를 유지한다.
- 코드 식별자, 파일명, API·제품명 등 고유 표기는 원문을 유지해도 되지만 설명 문장은 한국어로 쓴다.
- 제목은 실제 바뀐 동작이나 목적을 간결하게 설명한다. `수정`, `업데이트`처럼 대상과 내용이 없는 설명은 피한다.
- 본문이 필요하면 변경 이유, 주요 영향, 검증 결과를 한국어로 적는다. 기계가 해석하는 footer 키와 값은 필요한 원래 형식을 유지한다.

```text
feat(macOS-Direct): 업데이트 다운로드 진행률 표시
fix(AppStore): 상품 가격 재조회 오류 수정
refactor(macOS-Direct / AppStore): 방 세션 종료 책임 분리
fix(Windows): 오버레이 입력 모드 전환 오류 수정
chore(Shared): 한국어 커밋 컨벤션 스킬 추가
```

## 커밋 직전 확인

커밋에 포함할 전체 diff와 경로를 검토한 뒤 type, scope, 한국어 설명이 실제 변경과 일치하는지 확인한다. 기존 영어 커밋 이력은 이 규칙 도입만을 이유로 재작성하지 않는다. Git·GitHub가 자동 생성하는 merge 제목은 그대로 둘 수 있으며, 직접 제목을 지정하는 경우에는 이 규칙을 적용한다.

이 스킬은 커밋 메시지 규칙을 정의한다. 작업 시작·검증·통합은 [sidey-workflow](../sidey-workflow/SKILL.md)를 따른다. 스킬 사용 자체가 별도의 푸시·릴리스·배포를 승인하지는 않는다.

## Codex 공동 작성자

Codex가 실제 수정한 새 커밋에는 아래 trailer를 한 번 넣는다. 사람의 Git 작성자 이름·이메일은 유지한다.

```text
Co-authored-by: codex <codex@openai.com>
```

새 clone에서 `python3 scripts/setup_codex_attribution.py`를 한 번 실행한다. 설치된 훅은 같은 clone의 모든 worktree에 적용되며 `CODEX_THREAD_ID`가 있는 Codex 세션에서 동작한다. 일반 터미널 커밋에는 자동 귀속하지 않는다. 기존 hooksPath·다른 prepare-commit-msg 훅이 있으면 덮어쓰지 않으므로 설치 결과를 확인하고 기존 훅 관리 방식에 맞게 연결한다. 추적된 훅이 변경되면 설치 명령을 다시 실행한다.

Codex 실행 환경 변수가 전달되지 않는 경로에서는 실제 Codex 작업에 한해 `SIDEY_CODEX_COAUTHOR=1`로 실행하거나 trailer를 직접 넣는다. 기존 공동 작성자는 연속된 trailer 블록에 보존하고 같은 Codex 이메일을 중복 추가하지 않는다. 빈 메시지에는 자동 추가하지 않으므로 대화형 편집기로만 메시지를 작성할 때는 trailer를 직접 넣는다. 커밋 후 `git show -s --format=%B HEAD`로 확인한다.

다른 작성자의 원본을 그대로 이관하는 커밋은 `SIDEY_CODEX_COAUTHOR=0`으로 실행한다. 훅은 작성자·커미터 이메일이 다른 경우, merge·squash·기존 메시지 재사용/ amend·cherry-pick·rebase에서는 자동 추가하지 않는다. 이런 경로에서도 Codex가 실제 새 수정을 했다면 필요한 trailer를 직접 명시한다. 이력 보존 커밋에 작업하지 않은 AI를 추가하거나 기존 main을 재작성하지 않는다.

참고: [사용자 제공 가이드](https://swhan0329.github.io/codex-co-author-guide/ko/). 예제의 설정 덮어쓰기 방식은 적용하지 않고 SIDEY에 필요한 훅만 독립 구현한다. 계정 연결은 GitHub의 커밋 공동 작성자 목록에서 `codex@openai.com` → `@codex`로 확인한다.
