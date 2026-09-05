# Wiki Schema

## Domain
지식 저장소 관리 시스템(Knowledge Repository Management System)의 개발 지식, 설계 결정, 요구사항, 기술 조사, 운영 절차를 축적하고 연결한다.

## Conventions
- 파일 이름: 소문자, 하이픈 사용, 공백 금지 (예: `document-ingestion.md`)
- 모든 위키 페이지는 아래 YAML frontmatter로 시작한다.
- 페이지 간 연결에는 `[[wikilinks]]`를 사용하며, 새 페이지는 최소 2개의 outbound 링크를 가진다.
- 페이지를 수정할 때마다 `updated` 날짜를 갱신한다.
- 새 페이지는 올바른 유형의 섹션에 `index.md`에 추가한다.
- 모든 작업은 `log.md`에 append-only 형식으로 기록한다.
- 3개 이상 소스를 종합한 페이지는 출처별 주장 문단 끝에 `^[raw/articles/source-file.md]` 형식의 provenance marker를 붙인다.
- 원본 자료는 `raw/`에 보존하며 수정하지 않는다. 정정과 해석은 Layer 2 페이지에 기록한다.

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [taxonomy-tag]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
contested: true
contradictions: [other-page-slug]
---
```
`confidence`, `contested`, `contradictions`는 해당되는 경우에만 사용한다.

## Raw Source Frontmatter
```yaml
---
source_url: https://example.com/source
ingested: YYYY-MM-DD
sha256: <sha256 of body below frontmatter>
---
```
해시 계산 대상은 frontmatter를 제외한 본문이다. 동일 URL 재수집 시 해시가 같으면 처리를 건너뛰고, 다르면 drift로 표시한다.

## Tag Taxonomy
- `requirements`: 요구사항과 사용자 시나리오
- `architecture`: 시스템 구조와 경계
- `data-model`: 데이터 모델과 스키마
- `ingestion`: 수집·파싱·정규화
- `retrieval`: 검색·질의·랭킹
- `storage`: 저장소와 파일 관리
- `metadata`: 메타데이터와 분류
- `provenance`: 출처·감사 추적
- `quality`: 품질 검증과 평가
- `security`: 인증·권한·보안
- `operations`: 배포·모니터링·운영
- `api`: API와 통합
- `frontend`: 사용자 인터페이스
- `testing`: 테스트 전략과 검증
- `decision`: 설계 결정과 트레이드오프
- `tooling`: 개발 도구와 워크플로

## Page Thresholds
- 한 소스의 중심 주제이거나 2개 이상의 소스에 등장하는 엔티티·개념만 페이지로 만든다.
- 기존 페이지에 이미 다뤄진 주제는 새 페이지 대신 기존 페이지를 갱신한다.
- 200줄을 넘는 페이지는 하위 주제로 분리하고 상호 링크한다.
- 완전히 대체된 페이지는 `_archive/`로 이동하고 index에서 제거한다.

## Update Policy
- 충돌 시 날짜와 출처를 먼저 비교한다.
- 최신 자료가 일반적으로 우선하지만, 실제로 모순되면 양쪽 주장을 날짜·출처와 함께 남긴다.
- 해결되지 않은 충돌은 frontmatter에 `contested: true`와 `contradictions`를 표시한다.
