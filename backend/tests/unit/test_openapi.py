import json

from app.cli import FRONTEND_OPENAPI, openapi_json
from app.main import app


def _upload_files_schema() -> dict:
    schema = app.openapi()
    body = schema["paths"]["/donations/{donation_id}/images"]["post"]["requestBody"]
    ref = body["content"]["multipart/form-data"]["schema"]["$ref"].split("/")[-1]
    return schema["components"]["schemas"][ref]["properties"]["files"]


def test_image_upload_shows_a_file_picker_in_docs():
    files = _upload_files_schema()
    assert files["type"] == "array"
    assert files["items"]["format"] == "binary"


def test_patch_is_stable_across_calls():
    assert app.openapi() is app.openapi()
    assert _upload_files_schema()["items"]["format"] == "binary"


def test_frontend_schema_is_current():
    """The frontend generates its API types from a committed copy of the schema. If this
    fails, run `python -m app.cli export-openapi`, then `npm run gen:api` in frontend/."""
    assert FRONTEND_OPENAPI.exists(), "frontend/src/api/openapi.json is missing"
    committed = json.loads(FRONTEND_OPENAPI.read_text(encoding="utf-8"))
    assert committed == json.loads(openapi_json()), (
        "frontend/src/api/openapi.json is out of date: run `python -m app.cli export-openapi` "
        "and `npm run gen:api`."
    )
