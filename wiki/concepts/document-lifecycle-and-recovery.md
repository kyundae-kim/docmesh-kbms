---
title: 문서 저장소 Lifecycle과 Recovery
created: 2026-09-05
updated: 2026-09-05
type: concept
tags: [ingestion, storage, quality, operations, provenance]
sources: [raw/articles/dms-core-api-reference-v0-11-0.md, raw/articles/dms-core-examples-v0-11-0.md]
confidence: high
---

# 문서 저장소 Lifecycle과 Recovery

## 저장·조회 흐름

업로드는 bytes, 파일 경로 또는 정확한 크기를 선언한 동기 binary stream을 받는다. stream 입력의 선언 크기와 실제 읽은 bytes가 다르면 object를 rollback한 뒤 `ValidationError`를 발생시킨다. caller가 제공한 stream과 sink는 SDK가 닫지 않으며, SDK가 연 file과 source content stream은 SDK가 관리한다.

일반 metadata는 `PublicDocumentMetadata`로 제공하고 `storage_key`를 숨긴다. 관리·복구 경계에서만 `get_internal_document_metadata()`로 내부 metadata를 요청한다. 본문은 eager `DocumentContent` 또는 context-managed stream으로 읽을 수 있다.

## 상태와 삭제

soft delete는 logical delete를 수행하고 문서 상태를 `DELETED`로 만든다. hard delete는 metadata까지 제거한다. 일반 목록과 public metadata 조회는 `DELETING`, `DELETED` 문서를 숨기며, 삭제된 본문 요청은 `DocumentDeletedError`, 숨겨진 metadata 요청은 `DocumentNotFoundError`가 된다.

## 일관성 검사와 복구

`inspect_document()`은 동일 partition에서 metadata와 object 존재를 비교한다. 주요 `RecoveryIssue`는 `NONE`, `METADATA_MISSING`, `OBJECT_MISSING`, `DELETION_INCOMPLETE`, `FAILED_STATUS`다. 복구 작업은 다음 action을 사용한다.

- `COMPLETE_DELETION_SOFT`
- `COMPLETE_DELETION_HARD`
- `MARK_FAILED`
- `PURGE_ORPHAN_OBJECT`

batch recovery는 bounded batch로 제한한다. `dry_run=True`인 경우에만 immutable `ReconciliationPlan`을 내보내며, 실행 시 항목을 다시 검사해 오래된 계획을 재검증한다. recovery audit callback은 best-effort라서 callback 실패가 실제 recovery 결과를 대체하지 않는다.

## reset과 실패 처리

reset은 metadata, `documents/` object prefix, upload operation 기록을 대상으로 하며, 가능한 저장소 작업을 계속 시도한다. 일부 저장소가 실패하면 부분 count와 `failed_stores`를 포함한 `DataResetError`가 발생하고 `ready_for_data_load`는 false다. 빈 범위에 대한 initialize는 멱등적이다.

이 lifecycle은 [[partitioned-document-management]]의 범위 격리와 [[sdk-public-contract]]의 오류·stream 계약을 함께 적용해야 안전하다.

## 관련 페이지

- [[dms-core]]
- [[partitioned-document-management]]
- [[sdk-public-contract]]

## 출처

- API Reference v0.11.0, upload·delete/reset·consistency inspection·recovery·error contract 절
- Examples v0.11.0, E-04·E-05·E-07·E-08·E-10
