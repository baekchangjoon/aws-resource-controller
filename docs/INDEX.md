---
title: 문서 인덱스
created: 2026-05-25
updated: 2026-05-25
phase: meta
status: living
reading_order: -1
---

# docs/ 인덱스

본 디렉터리는 두 가지로 나뉩니다.

- **루트의 `*.md`** — 살아있는(living) 참조 문서. 이름은 의미 기반이고 파일은 갱신될 수 있음.
- **`sessions/`** — 특정 시점의 진행 보고서(snapshot). 파일명에 날짜를 박아 시간순 정렬.

각 문서 첫 줄의 YAML frontmatter에 `created` / `updated` / `phase` / `status` / `reading_order`가 있어 기계가 읽을 수 있습니다. 실제 시간 정답은 `git log --follow <file>`.

## 읽는 순서 (reading_order)

처음 보시는 분은 이 순서로 읽으면 흐름이 이어집니다.

| 순서 | 문서 | 책임 | 상태 |
|------|------|------|------|
| 0 | [`../inventory/INVENTORY.md`](../inventory/INVENTORY.md) | 초기 AWS 인벤토리 스냅샷 | snapshot |
| 1 | [`ANALYSIS.md`](ANALYSIS.md) | 현재 인프라 + HTML 기획서 평가 + 격차 | living |
| 2 | [`DESIGN.md`](DESIGN.md) | 아키텍처, DB 스키마, API, 보안 모델 | living |
| 3 | [`ROADMAP.md`](ROADMAP.md) | Phase별 TDD/E2E/CI 전략 | living |
| 4 | [`DECISIONS.md`](DECISIONS.md) | D1~D18 사용자 결정 + 파생 결정 | living |
| 5 | [`TEARDOWN.md`](TEARDOWN.md) | 보존/삭제/인수 명세 | living |
| 6 | [`VERIFICATION.md`](VERIFICATION.md) | Phase별 검증 audit | living |
| 7 | [`sessions/2026-05-25.md`](sessions/2026-05-25.md) | 첫 세션 진행 종합 | snapshot |

## 생성 타임라인 (git log 기준)

| 시각 (KST) | 문서 | 비고 |
|-----------|------|------|
| 2026-05-25 11:35 | INVENTORY, ANALYSIS, DESIGN, ROADMAP, DECISIONS, TEARDOWN | 분석/설계 일괄 작성 |
| 2026-05-25 11:55 | VERIFICATION | Phase 0 검증 시점 |
| 2026-05-25 12:11 | DESIGN, DECISIONS (갱신) | D17, D18 추가 + 버킷 명명 패턴 동기화 |
| 2026-05-25 12:32 | VERIFICATION (갱신) | Phase 1.1 결과 추가 |
| 2026-05-25 13:20 | sessions/2026-05-25.md | 세션 종합 보고 |

> 위 표는 `git log --diff-filter=A --follow --format='%aI' -- <file>`로 산출된 첫 commit 시각을 기준으로 합니다. 갱신 이력 전체는 `git log -- docs/<file>` 또는 `CHANGELOG.md`.

## frontmatter 필드 정의

```yaml
---
title: <사람이 읽는 제목>
created: YYYY-MM-DD     # 첫 commit 날짜 (불변)
updated: YYYY-MM-DD     # 마지막 의미 있는 갱신 날짜
phase: <0|1|2|3|all>    # 어느 Phase의 산출물인지
status: <living|snapshot|superseded>
reading_order: <int>    # 신규 독자가 읽어야 하는 순서
session: YYYY-MM-DD     # sessions/ 디렉터리 문서만 사용
---
```

### status 값
- `living` — 계속 갱신되는 참조 문서. 파일명 그대로 유지.
- `snapshot` — 특정 시점 기록. 일반적으로 갱신하지 않음 (오자/링크 보정 정도만).
- `superseded` — 더 이상 유효하지 않음. 본문 상단에 후속 문서로의 링크를 둘 것.

### phase 값
- `meta` — 본 INDEX처럼 다른 문서를 안내하는 메타 문서
- `0`~`3` — 해당 Phase 산출물
- `all` — 여러 Phase에 걸쳐 갱신되는 종합 문서 (예: VERIFICATION, 세션 보고서)

## 자동 검증

[`scripts/lint_docs.py`](../scripts/lint_docs.py)가 CI에서 매 PR/push마다 모든 `docs/*.md`와 `inventory/*.md`의:
1. frontmatter 필수 필드 (`title`, `created`, `updated`, `status`)
2. `status: living`인 경우 추가 필드 (`phase`, `reading_order`)
3. `created`/`updated`가 `YYYY-MM-DD` 포맷
4. 상대 링크 중 깨진 것

을 점검하고 위반 시 CI 실패시킵니다.

## 새 세션 추가 방법

다음 세션의 작업을 기록하려면:

1. `cp docs/sessions/2026-05-25.md docs/sessions/YYYY-MM-DD.md`
2. frontmatter의 `session` / `created` / `updated`를 새 날짜로
3. 본 INDEX.md의 "읽는 순서"와 "생성 타임라인" 표를 갱신
4. (선택) 직전 세션 문서의 frontmatter `status`는 `snapshot` 유지

## 새 결정 / 새 검증 추가 방법

- 새 결정: `DECISIONS.md`에 D19~ 항목 append → INDEX 갱신 불필요
- 새 검증: `VERIFICATION.md`에 Phase 섹션 append → INDEX 갱신 불필요
- 새 설계 변경: 기존 `DESIGN.md` 갱신 + `updated`를 오늘 날짜로
