---
title: Partition 기반 문서 관리
created: 2026-09-05
updated: 2026-09-05
type: concept
tags: [data-model, security, storage, api]
sources: [raw/articles/dms-core-api-reference-v0-11-0.md, raw/articles/dms-core-examples-v0-11-0.md]
confidence: high
---

# Partition 기반 문서 관리

## 정의

v0.11.0의 일반 문서 작업은 `DocumentPartition`을 keyword로 반드시 받아야 한다. partition은 personal 또는 group 범위를 표현하며, 같은 식별자라도 kind가 다르면 별개의 namespace다.

partition은 metadata 조회·목록·업로드·삭제·본문 읽기·recovery candidate 조회에 적용된다. cursor에는 partition, status filter, page size 조건이 결합되고, storage namespace와 idempotency namespace에도 partition kind가 반영된다. 따라서 다른 partition에서 cursor를 재사용하거나 `partition=None`으로 범위를 넓히는 우회는 허용되지 않는다.

## 접근 제어

DMS 자체는 인증이나 group membership을 결정하지 않는다. host가 확인한 사용자·역할·그룹을 `AccessContext`로 전달하고, `DocumentAccessPolicy`가 작업별 허용 여부를 판단한다. 정책 callback에는 public metadata만 전달되어 storage locator가 외부 경계로 새지 않는다.

이 모델은 [[dms-core]]의 주입형 SDK 경계와 [[sdk-public-contract]]의 명시적 public/internal metadata 분리를 전제로 한다.

## 전역 작업과의 구분

- `clear_partition_data(partition=...)`, `initialize_partition_for_data_load(partition=...)`: 지정 partition만 대상
- `clear_all_data()`, `initialize_for_data_load()`: 명시적인 전역 관리 작업
- 일반 API에 `partition=None`을 전달해 전역 작업으로 바꾸는 방식은 지원하지 않음

## 설계 시사점

1. 모든 애플리케이션 호출 계층에서 partition을 필수 값으로 보존한다.
2. cursor와 idempotency key를 partition과 함께 캐시·전달한다.
3. host 권한 정책과 DMS 데이터 경계를 분리한다.
4. public metadata와 내부 storage locator의 노출 경계를 테스트한다.

## 관련 페이지

- [[dms-core]]
- [[sdk-public-contract]]
- [[document-lifecycle-and-recovery]]

## 출처

- API Reference v0.11.0, 공개 import 경계·partition·access control·pagination·reset 절
- Examples v0.11.0, E-03·E-06·E-07·E-11
