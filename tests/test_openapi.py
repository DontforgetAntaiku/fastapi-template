def test_spec_is_3_2_and_documents_query_with_body():
    from main import app

    spec = app.openapi()
    assert spec["openapi"] == "3.2.0"
    operation = spec["paths"]["/api/v1/users"]["query"]
    body = operation["requestBody"]["content"]["application/json"]["schema"]
    assert body["$ref"].endswith("/UserFilter")
    assert operation["operationId"] == "users_search_users"


def test_private_fields_are_in_no_schema():
    from main import app

    assert "password_hash" not in str(app.openapi())


def test_typescript_spec_turns_query_into_a_post_twin():
    from app.utils.openapi import typescript_compatible
    from main import app

    spec = typescript_compatible(app.openapi())
    assert spec["openapi"] == "3.1.0"
    assert "query" not in spec["paths"]["/api/v1/users"]
    twin = spec["paths"]["/api/v1/users::QUERY"]["post"]
    assert twin["operationId"] == "users_search_users"
    assert twin["x-http-method"] == "QUERY"
    assert "requestBody" in twin
    assert spec["paths"]["/api/v1/users"]["post"]["operationId"] == "users_create_user"
    assert not any("query" in item for item in spec["paths"].values())


def test_app_spec_is_not_modified_by_the_conversion():
    from app.utils.openapi import typescript_compatible
    from main import app

    typescript_compatible(app.openapi())
    assert "query" in app.openapi()["paths"]["/api/v1/users"]
