---
title: dms-core DMS SDK
created: 2026-09-05
updated: 2026-09-05
type: entity
tags: [architecture, api, storage, operations]
sources: [raw/articles/dms-core-api-reference-v0-11-0.md, raw/articles/dms-core-examples-v0-11-0.md]
confidence: high
---

# dms-core DMS SDK

## 개요

`dms-core` v0.11.0은 문서 메타데이터와 object storage를 함께 관리하는 Python SDK다. 독립 실행형 API 서버가 아니라 host 애플리케이션에 주입되어 사용되며, 권장 소비 경계는 `from dms import ...` package root다.

SDK는 SQLAlchemy engine, MinIO client 또는 storage component를 스스로 생성·종료하지 않는다. host가 의존성 생성, readiness, 종료 순서를 책임진다. 이 소유권 경계는 [[sdk-public-contract]]와 [[document-lifecycle-and-recovery]] 설계에 직접 영향을 준다.

## 공개 구성

- 동기 facade: `DocumentManagementSDKFactory`, `DefaultDocumentManagementSDK`
- 비동기 facade: `AsyncDocumentManagementSDKFactory`, `AsyncDocumentManagementSDK`
- 기능별 protocol: `DocumentWriter`, `DocumentReader`, `DocumentLister`, `DocumentDeleter`, `DataResetter`
- 주요 값 객체: `DocumentPartition`, `DocumentMetadata`, `PublicDocumentMetadata`, `DocumentPage`
- 구조화된 오류: `DmsError` 및 configuration, validation, authorization, storage, consistency 계열

총 56개 이름이 package root에서 공개되며 `dms.sdk`는 SDK export를 재-export한다. 내부 adapter, persistence model, storage port 및 환경변수 조립 helper는 안정적인 소비자 계약이 아니다.

## 버전 기준

이 페이지는 API Reference와 Examples가 명시한 v0.11.0 기준 commit `1f3325ed914fc970e4e040e161e6de117ede5aeb`을 기록한다. 이후 버전이 추가되면 기존 사실을 덮어쓰지 말고 버전별 페이지 또는 변경 기록으로 분리한다.

## 관련 페이지

- [[sdk-public-contract]]
- [[partitioned-document-management]]
- [[document-lifecycle-and-recovery]]

## 출처

- [API Reference v0.11.0](https://github.com/kyundae-kim/dms-core/wiki/API-Reference-v0.11.0)
- [Examples v0.11.0](https://github.com/kyundae-kim/dms-core/wiki/Examples-v0.11.0)
