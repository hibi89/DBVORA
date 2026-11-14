"""Mock AX consumers validate versioned, read-only DBVORA contracts."""
from datetime import datetime
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from dbvora.api import create_app
from dbvora.connectors.postgres_reader import inspect_catalog
from dbvora.inventory import inspect_sqlite
from dbvora.multi_engine_report import assemble_workspace
from dbvora.observation_ledger import append_observation
from tests.fixtures.make_sqlite import create_fixture


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "p0-01.v1": "p0-01.v1.schema.json",
    "p0-03.workspace.v1": "p0-03.workspace.v1.schema.json",
}
FORBIDDEN_KEYS = {"rows", "row_data", "dsn", "password", "token",
                  "credential", "credentials"}
FORBIDDEN_VALUES = (
    "NOT_FOR_SCHEMA_OUTPUT",
    "SYNTHETIC_ROW_MUST_NEVER_BE_EXPORTED",
    "example@invalid.test",
    "postgresql://",
    "DSN=",
)


class MockConsumerError(ValueError):
    pass


def _read_schema(name):
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def _is_type(instance, kind):
    if kind == "object":
        return type(instance) is dict
    if kind == "array":
        return type(instance) is list
    if kind == "string":
        return type(instance) is str
    if kind == "integer":
        return type(instance) is int
    if kind == "boolean":
        return type(instance) is bool
    if kind == "null":
        return instance is None
    return False


def _assert_schema_shape(instance, schema):
    """Validate every JSON Schema keyword used by the published schemas."""
    if "const" in schema and instance != schema["const"]:
        raise MockConsumerError("SCHEMA_CONST_MISMATCH")
    if "enum" in schema and instance not in schema["enum"]:
        raise MockConsumerError("SCHEMA_ENUM_MISMATCH")
    kind = schema.get("type")
    if kind is not None:
        accepted = kind if isinstance(kind, list) else [kind]
        if not any(_is_type(instance, candidate) for candidate in accepted):
            raise MockConsumerError("SCHEMA_TYPE_MISMATCH")
        kind = next(candidate for candidate in accepted
                    if _is_type(instance, candidate))
    if kind == "object":
        if any(key not in instance for key in schema.get("required", [])):
            raise MockConsumerError("SCHEMA_REQUIRED_FIELD_MISSING")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(instance) - set(properties):
            raise MockConsumerError("SCHEMA_ADDITIONAL_FIELD")
        for key, child_schema in properties.items():
            if key in instance:
                _assert_schema_shape(instance[key], child_schema)
    elif kind == "array":
        if len(instance) < schema.get("minItems", 0):
            raise MockConsumerError("SCHEMA_ARRAY_TOO_SHORT")
        if len(instance) > schema.get("maxItems", float("inf")):
            raise MockConsumerError("SCHEMA_ARRAY_TOO_LONG")
        for item in instance:
            _assert_schema_shape(item, schema.get("items", {}))
    elif kind == "string":
        if len(instance) < schema.get("minLength", 0):
            raise MockConsumerError("SCHEMA_STRING_TOO_SHORT")
        if len(instance) > schema.get("maxLength", float("inf")):
            raise MockConsumerError("SCHEMA_STRING_TOO_LONG")
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, instance) is None:
            raise MockConsumerError("SCHEMA_PATTERN_MISMATCH")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(instance.replace("Z", "+00:00"))
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise ValueError
            except (TypeError, ValueError):
                raise MockConsumerError("SCHEMA_DATETIME_MISMATCH") from None
    elif kind == "integer":
        if instance < schema.get("minimum", instance) or instance > schema.get("maximum", instance):
            raise MockConsumerError("SCHEMA_RANGE_MISMATCH")


def _reject_sensitive_fields(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise MockConsumerError("FORBIDDEN_FIELD")
            _reject_sensitive_fields(item)
    elif isinstance(value, list):
        for item in value:
            _reject_sensitive_fields(item)


def _assert_no_synthetic_rows_or_secrets(payload):
    _reject_sensitive_fields(payload)
    encoded = json.dumps(payload, ensure_ascii=False)
    if any(marker in encoded for marker in FORBIDDEN_VALUES):
        raise MockConsumerError("FORBIDDEN_VALUE")


def _accept_error(payload):
    _assert_schema_shape(payload, _read_schema("dbvora-error-v1.schema.json"))
    error = payload["error"]
    if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", error["code"]) is None:
        raise MockConsumerError("INVALID_ERROR_CONTRACT")
    return {"status": "unavailable", "error_code": error["code"]}


class MockHAEConsumer:
    @staticmethod
    def consume(payload):
        if type(payload) is not dict:
            raise MockConsumerError("INVALID_PAYLOAD")
        _assert_no_synthetic_rows_or_secrets(payload)
        if "error" in payload:
            return _accept_error(payload)
        version = payload.get("contract_version")
        schema_file = SCHEMAS.get(version)
        if schema_file is None:
            raise MockConsumerError("UNSUPPORTED_CONTRACT_VERSION")
        _assert_schema_shape(payload, _read_schema(schema_file))
        if version == "p0-01.v1":
            databases = [{"tables": payload["tables"]}]
            relationships = payload["relationships"]
            provenance = payload["provenance"]
        else:
            databases = payload["databases"]
            relationships = payload["relationships"]
            provenance = {"cpu_usage": payload["cpu_usage"],
                          "ram_usage": payload["ram_usage"]}
        return {
            "contract_version": "mock-hae.dbvora.v1",
            "source_contract_version": version,
            "database_count": len(databases),
            "table_count": sum(len(db["tables"]) for db in databases),
            "declared_relationship_count": sum(
                edge.get("evidence") == "declared_foreign_key"
                for edge in relationships
            ),
            "cpu_usage": provenance.get("cpu_usage", "unavailable"),
            "ram_usage": provenance.get("ram_usage", "unavailable"),
        }


class MockLAConsumer:
    @staticmethod
    def consume(payload):
        if type(payload) is not dict:
            raise MockConsumerError("INVALID_PAYLOAD")
        _assert_no_synthetic_rows_or_secrets(payload)
        if "error" in payload:
            return _accept_error(payload)
        version = payload.get("contract_version")
        schema_file = SCHEMAS.get(version)
        if schema_file is None:
            raise MockConsumerError("UNSUPPORTED_CONTRACT_VERSION")
        _assert_schema_shape(payload, _read_schema(schema_file))
        if version == "p0-01.v1":
            size_bytes = payload["size_bytes"]
            size_scope = payload["size_scope"]
            provenance = payload["provenance"]
        else:
            size_bytes = payload["total_main_db_size_bytes"]
            size_scope = payload["size_scope"]
            provenance = {"cpu_usage": payload["cpu_usage"],
                          "ram_usage": payload["ram_usage"]}
        return {
            "contract_version": "mock-la.dbvora.v1",
            "source_contract_version": version,
            "size_bytes": size_bytes,
            "size_scope": size_scope,
            "provenance": provenance,
        }


def _synthetic_pg_catalog(include_statistics=False):
    table = {
        "schema": "public",
        "name": "users",
        "relation_kind": "r",
        "size_bytes": 8192,
        "size_provenance": "pg_total_relation_size",
        "columns": [
            {"name": "id", "type": "bigint",
             "nullable_declared": False, "attnum": 1},
            {"name": "email", "type": "text",
             "nullable_declared": True, "attnum": 2},
        ],
        "primary_key_columns": ["id"],
        "indexes": [{
            "name": "users_pkey", "unique": True, "primary": True,
            "partial": False, "key_columns": ["id"],
        }],
        "foreign_keys": [],
    }
    if include_statistics:
        table["statistics"] = {
            "status": "observed",
            "estimated_live_rows": 1,
            "estimated_dead_rows": 0,
            "heap_bytes": 8192,
            "index_bytes": 4096,
            "row_count_provenance": "pg_stat_user_tables_estimate_not_exact",
            "storage_provenance": "pg_relation_size_and_pg_indexes_size",
        }
    return {
        "contract_version": "dbvora.pg_catalog.v1",
        "engine": "postgresql",
        "inspection_mode": "read_only_metadata_only",
        "observed_at": "2026-11-15T00:00:00+00:00",
        "database_count": 1,
        "table_count": 1,
        "tables": [table],
        "relationships": [],
        "cpu_usage": "unavailable",
        "ram_usage": "unavailable",
        "ready_for_customer_data": False,
    }


class AxMetadataContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.first = create_fixture(self.root / "first.sqlite")
        self.second = create_fixture(self.root / "second.sqlite")

    def test_published_schemas_match_synthetic_api_and_offline_outputs(self):
        single = inspect_sqlite(self.first)
        with TestClient(create_app(self.first, port=8765),
                        base_url="http://127.0.0.1:8765") as client:
            response = client.get("/api/inventory")
            self.assertEqual(response.status_code, 200)
            _assert_schema_shape(response.json(), _read_schema(SCHEMAS["p0-01.v1"]))
            self.assertNotIn("NOT_FOR_SCHEMA_OUTPUT", response.text)
            self.assertNotIn("example@invalid.test", response.text)

            workspace_response = client.get("/api/inventory")
            self.assertEqual(workspace_response.status_code, 200)
            single_payload = workspace_response.json()
            for consumer in (MockHAEConsumer.consume, MockLAConsumer.consume):
                consumer(single_payload)

            table_response = client.get("/api/table-storage?table=customers")
            self.assertEqual(table_response.status_code, 200)
            _assert_schema_shape(
                table_response.json(),
                _read_schema("dbvora.local-table-storage.v1.schema.json"),
            )

        multi_app = create_app([self.first, self.second], port=8765)
        with TestClient(multi_app, base_url="http://127.0.0.1:8765") as client:
            response = client.get("/api/inventory")
        self.assertEqual(response.status_code, 200)
        workspace_payload = response.json()
        _assert_schema_shape(workspace_payload,
                             _read_schema(SCHEMAS["p0-03.workspace.v1"]))
        for consumer in (MockHAEConsumer.consume, MockLAConsumer.consume):
            consumer(workspace_payload)

        ledger = self.root / "observations.sqlite"
        append_observation(
            ledger, db_id=single["db_id"], observed_at="2026-11-15T00:00:00Z",
            size_bytes=single["size_bytes"],
            scope="sqlite_main_file_excluding_wal_shm", consent=True,
        )
        app = create_app(self.first, port=8765, observation_ledger_path=ledger)
        with TestClient(app, base_url="http://127.0.0.1:8765") as client:
            response = client.get(
                "/api/observations",
                params={"database": single["db_id"]},
            )
        self.assertEqual(response.status_code, 200)
        _assert_schema_shape(
            response.json(),
            _read_schema("dbvora.local-observation.v1.schema.json"),
        )

        pg = _synthetic_pg_catalog(include_statistics=True)
        pg_schema = _read_schema("dbvora.pg_catalog.v1.schema.json")
        stats_schema = _read_schema("dbvora.pg_statistics.v1.schema.json")
        pg_app = create_app(self.first, port=8765, postgres_dsn="host=synthetic.invalid")
        with patch("dbvora.api.inspect_postgres", return_value=pg):
            with TestClient(pg_app, base_url="http://127.0.0.1:8765") as client:
                catalog_response = client.get("/api/postgres")
                stats_response = client.get("/api/postgres/statistics")
        self.assertEqual(catalog_response.status_code, 200)
        _assert_schema_shape(catalog_response.json(), pg_schema)
        self.assertEqual(stats_response.status_code, 200)
        _assert_schema_shape(stats_response.json(), stats_schema)

        mixed = assemble_workspace([single, pg])
        _assert_schema_shape(
            mixed,
            _read_schema("dbvora.multi_engine_offline.v1.schema.json"),
        )
        _assert_no_synthetic_rows_or_secrets(mixed)

    def test_mock_consumers_reject_unknown_versions_and_isolate_errors(self):
        app = create_app(self.first, port=8765)
        with patch("dbvora.api.inspect_postgres") as connector:
            with TestClient(app, base_url="http://127.0.0.1:8765") as client:
                disabled = client.get("/api/postgres")
        self.assertEqual(disabled.status_code, 404)
        connector.assert_not_called()
        _assert_schema_shape(
            disabled.json(), _read_schema("dbvora-error-v1.schema.json")
        )
        for consumer in (MockHAEConsumer.consume, MockLAConsumer.consume):
            self.assertEqual(
                consumer(disabled.json()),
                {"status": "unavailable", "error_code": "POSTGRES_DISABLED"},
            )
            with self.subTest(consumer=consumer.__qualname__):
                with self.assertRaisesRegex(
                    MockConsumerError, "UNSUPPORTED_CONTRACT_VERSION"
                ):
                    consumer({"contract_version": "p0-03.workspace.v999"})

        missing = create_fixture(self.root / "missing.sqlite")
        broken = create_app(missing, port=8765)
        missing.unlink()
        with TestClient(broken, base_url="http://127.0.0.1:8765") as client:
            response = client.get("/api/inventory")
        self.assertEqual(response.status_code, 422)
        _assert_schema_shape(
            response.json(), _read_schema("dbvora-error-v1.schema.json")
        )
        self.assertNotIn(str(missing), response.text)


if __name__ == "__main__":
    unittest.main()
