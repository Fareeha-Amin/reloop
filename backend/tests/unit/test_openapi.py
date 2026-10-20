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
