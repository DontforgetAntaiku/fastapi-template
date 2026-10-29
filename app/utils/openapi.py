import copy
from typing import Any

QUERY_SUFFIX = "::QUERY"


def typescript_compatible(spec: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(spec)
    result["openapi"] = "3.1.0"
    paths: dict[str, Any] = {}
    for path, item in result["paths"].items():
        operation = item.pop("query", None)
        paths[path] = item
        if operation is not None:
            operation["x-http-method"] = "QUERY"
            twin: dict[str, Any] = {"post": operation}
            if "parameters" in item:
                twin["parameters"] = item["parameters"]
            paths[path + QUERY_SUFFIX] = twin
    result["paths"] = {p: i for p, i in paths.items() if i}
    return result
