import json
from pathlib import Path

from jsonschema import validate
from jsonschema.exceptions import ValidationError


SCHEMA_DIR = Path("schemas")


def load_schema(schema_name: str) -> dict:
    schema_path = SCHEMA_DIR / schema_name

    with open(schema_path, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_data(data: dict, schema_name: str) -> bool:
    schema = load_schema(schema_name)

    try:
        validate(instance=data, schema=schema)

        print(f"[VALIDATION PASSED] {schema_name}")
        return True

    except ValidationError as error:
        print(f"[VALIDATION FAILED] {schema_name}")
        print(error.message)

        raise