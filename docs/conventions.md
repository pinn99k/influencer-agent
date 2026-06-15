# conventions.md
# 코딩 컨벤션 — 모든 세션에 적용. 변경 시 ADR 필요.

## 네이밍
- 변수 / 함수:  camelCase
- 클래스:       PascalCase
- 상수:         UPPER_SNAKE_CASE
- 파일:         {kebab-case | snake_case | PascalCase} ← 스택에 맞춰 선택

## 포맷
- 들여쓰기:     {공백 N칸 | 탭}
- 최대 줄 길이: {N}자
- 세미콜론:     {사용 | 미사용}
- 자동 포맷:    {prettier / gofmt / black 등 — 커맨드 명시}

## 레이어 책임
- {레이어명}: {책임 범위} / {금지 사항}
- 예) Controller: 요청·응답만 / 비즈니스 로직 금지

## 주석
- 함수 단위:  {JSDoc | KDoc | docstring | 없음}
- 인라인:     복잡한 로직만. 자명한 코드에 주석 금지.
- TODO:       TODO(이름): 내용 형식. 이슈 없는 TODO 방치 금지.

## 테스트
- 위치:       {src/__tests__/ | src/test/ | 같은 폴더}
- 네이밍:     {describe('대상') + it('동작')} 형식 권장
- 커버리지:   {N% 이상 유지 | 미설정}

## Git
- 커밋 메시지: {feat | fix | docs | refactor | test | chore}: 내용 (한글 가능)
- 브랜치:      main / feature/{이슈번호}-{설명}
- PR 조건:     {테스트 통과 필수 | 리뷰어 N명 이상}
- 머지 전략:   {squash merge | merge commit | rebase}

## 절대 금지
- {이 프로젝트에서 절대 하지 말 것 + 이유}
- 예) 비밀키 하드코딩 금지 (보안 취약점)
- 예) console.log 커밋 금지 (→ logger 사용)

## 이 파일 수정 시
→ ADR 작성 후 수정 (docs/adr/{NNN}-conventions-update.md)
→ 팀 합의 필수
