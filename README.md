# docmesh-kbms

문서 원본과 메타데이터는 `dms-core`가 관리하고, 이 프로젝트는 문서 내용을
추출·chunking·embedding하여 Milvus에 저장하는 지식 저장 관리 시스템이다.

외부 공개 진입점은 `kbms.KnowledgeManagement` 하나다.

## 계층

- Domain: Python
- Document management: dms-core
- ORM/RDB: SQLAlchemy with SQLite or PostgreSQL
- Vector store: Milvus
- Embedding provider: Ollama

`KnowledgeManagement.upload_document()`은 dms-core 업로드 후 SQLAlchemy projection을
저장하고, 텍스트 문서만 Ollama/Milvus로 지식화한다. SQLAlchemy `Session`과
dms-core, Ollama, Milvus client의 생성·종료 및 commit/rollback은 host가 맡는다.
host 권한 정책은 생성자에 `access_policy`로 주입하고, 각 문서 작업에는 dms-core의
`AccessContext`를 전달해 사용자·그룹 권한을 적용한다.

## 검증

```bash
uv run pytest -q
uv run ruff check kbms test_kbms
```

SQLite memory/disk와 Milvus local 검사는 항상 실행된다. PostgreSQL, Milvus server,
Ollama 연결 검사는
다음 환경변수가 설정된 경우 실행된다.

```bash
export KBMS_POSTGRES_URL='postgresql+psycopg://docmesh:postgres@postgres:5432/kbms'
export KBMS_MILVUS_URI='http://milvus:19530'
export KBMS_OLLAMA_HOST='http://192.168.219.106:11434'
export KBMS_OLLAMA_EMBEDDING_MODEL='bge-m3'
export KBMS_OLLAMA_GENERATION_MODEL='llama3.2'
uv run pytest -q -m integration
```

실환경 전체 흐름(DMS + MinIO + PostgreSQL + Ollama + Milvus)은 다음 테스트가
검증한다. MinIO 설정을 생략하면 devcontainer 기본값을 사용한다.

```bash
export KBMS_MINIO_ENDPOINT='milvus-minio:9000'
export KBMS_MINIO_ACCESS_KEY='minioadmin'
export KBMS_MINIO_SECRET_KEY='minioadmin'
export KBMS_MINIO_BUCKET='kbms-e2e'
uv run pytest -q -m real_integration test_kbms/test_real_integration.py
```
