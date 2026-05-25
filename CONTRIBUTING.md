# Contributing — TempSES

## 작업 흐름

1. 이슈 또는 작업 항목 선정 ([docs/ROADMAP.md](docs/ROADMAP.md) 참고)
2. 기능 브랜치 생성 — `git checkout -b <type>/<short-name>` (예: `feat/ddb-tables`)
3. **TDD**: 실패 테스트 작성 → 구현 → 리팩토링
4. lint/test 통과 확인 (CI가 동일하게 검사)
5. PR 생성 → 리뷰 → main 머지
6. 직접 main push 금지

## 커밋 메시지 — Conventional Commits

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) 형식을 따른다.

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### type 종류
- `feat` — 신규 기능
- `fix` — 버그 수정
- `docs` — 문서만 변경
- `chore` — 빌드/툴/설정 변경 (런타임 영향 없음)
- `refactor` — 동작 변화 없는 코드 개선
- `test` — 테스트 추가/수정
- `ci` — CI/CD 관련
- `perf` — 성능 개선
- `style` — 포맷팅(공백/들여쓰기) 변경
- `build` — 빌드 시스템 변경
- `revert` — 이전 커밋 되돌리기

### 예시
```
feat(ingest): drop messages with spam verdict FAIL

When SES marks an inbound message with X-SES-Spam-Verdict: FAIL,
the ingest Lambda now skips parsing and logs drop_reason=spam.

Refs: docs/DESIGN.md §7.1
```

### Breaking change
`!` 접미사 또는 `BREAKING CHANGE:` 푸터.
```
feat(api)!: rename /addresses to /mailboxes
```

## 코드 스타일

- Python: [ruff](https://docs.astral.sh/ruff/) (formatter + linter) + [mypy](https://mypy.readthedocs.io/) — `pyproject.toml`에서 설정 관리
- TypeScript: ESLint + Prettier + `tsc --noEmit`
- Terraform: `terraform fmt` + [tflint](https://github.com/terraform-linters/tflint)

## 테스트

- **단위 테스트는 PR 머지 전 반드시 통과**.
- 새 기능을 추가하면 그 기능을 검증하는 테스트가 같은 PR에 포함되어야 함.
- E2E 테스트는 PR 라벨 `run-e2e` 또는 nightly cron으로 실행.

## PR 리뷰 체크리스트

- [ ] 변경 의도가 PR 설명에 명시되어 있는가
- [ ] 관련 문서(`docs/`)가 함께 갱신되었는가
- [ ] Terraform 변경이라면 `terraform plan` 결과가 PR에 첨부되었는가
- [ ] 보안 영향(권한, 시크릿, 외부 노출)이 검토되었는가
- [ ] 테스트가 추가/갱신되었는가
