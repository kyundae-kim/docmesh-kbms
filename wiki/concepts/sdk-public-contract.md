---
title: DMS SDK 공개 계약
created: 2026-09-05
updated: 2026-09-05
type: concept
tags: [api, security, quality, testing, decision]
sources: [raw/articles/dms-core-api-reference-v0-11-0.md, raw/articles/dms-core-examples-v0-11-0.md]
confidence: high
---

# DMS SDK 공개 계약

## Import와 조립

소비자는 안정적인 경계인 `from dms import ...`에서 공개 이름을 가져온다. factory는 host가 만든 SQLAlchemy engine과 MinIO client를 조립하며, async 경로는 native async storage component 또는 sync SDK compatibility 경로를 선택할 수 있다. 주입된 자원의 lifecycle은 host 소유다.

기능별 capability protocol을 이용하면 host가 필요한 계약만 type-check하거나 주입할 수 있다. `DocumentManagementClient`는 writer, reader, lister, deleter, resetter 계약을 합성한다.

## 입력과 출력

- 일반 document method: `partition=` keyword 필수
- upload: bytes, file, known-size sync stream
- list: opaque cursor 기반 `DocumentPage`; offset 목록은 제공하지 않음
- metadata: public projection과 명시적 internal metadata 경계
- DTO: `to_dict()`와 JSON Schema 제공
- stream: sync는 `with`/`close()`, async는 `async with`/`aclose()` 사용

public serialization에서는 `storage_key`가 노출되지 않는다. `PublicDocumentMetadata.to_dict()`의 호환 필드명과 `to_public_dict()`의 외부 표현 차이도 계약으로 취급한다.

## 오류와 관찰성

모든 public `DmsError` subclass는 안정적인 `code`, `category`, `retryable` class attribute를 갖는다. 외부 응답에는 infrastructure exception 원문이나 storage locator를 노출하지 않는다. `OperationObserver`는 성공·실패 event를 받지만 observer 오류가 원래 작업 결과를 바꾸지 않는다.

## 검증 포인트

1. package root export와 capability protocol을 contract test로 확인한다.
2. partition 누락·cursor 오용·stream 크기 불일치를 `ValidationError`로 검증한다.
3. public DTO serialization과 JSON Schema에서 `storage_key` 비노출을 검증한다.
4. 오류 metadata를 기준으로 retry 여부를 결정한다.
5. async stream과 주입 자원의 종료 책임이 host/SDK 사이에서 섞이지 않는지 확인한다.

이 계약은 [[dms-core]]의 공개 표면을 구체화하고 [[document-lifecycle-and-recovery]]의 저장·복구 동작, [[partitioned-document-management]]의 범위 규칙을 검증 가능한 형태로 연결한다.

## 관련 페이지

- [[dms-core]]
- [[partitioned-document-management]]
- [[document-lifecycle-and-recovery]]

## 출처

- API Reference v0.11.0, 공개 import·facade·error·trace ID·version caution 절
- Examples v0.11.0, E-01·E-02·E-04·E-05·E-06·E-09·E-10·E-11
