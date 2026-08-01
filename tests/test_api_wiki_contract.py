import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

from pydantic import BaseModel

from app.api.auth import CurrentUserResponse, TokenResponse
from app.api.router import PingResponse
from app.main import app


WIKI_ROOT = Path(__file__).parents[1] / "wikis"
HTTP_METHODS = {
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "HEAD",
    "TRACE",
}
REQUIRED_OPERATION_SECTIONS = {
    "Purpose",
    "Authentication and Headers",
    "Path and Query Parameters",
    "Request",
    "Successful Response",
    "Stable Business Errors",
    "State Side Effects",
}
H2_PATTERN = re.compile(r"^## (?!#)(?P<title>.+)$", re.MULTILINE)
CODE_FENCE_PATTERN = re.compile(
    r"^```(?P<language>[A-Za-z0-9_-]+)\s*\n(?P<content>.*?)^```$",
    re.MULTILINE | re.DOTALL,
)
URL_PATTERN = re.compile(r"^- URL: +`(?P<path>/[^`]+)`$")
METHOD_PATTERN = re.compile(r"^- Method: +`(?P<method>[A-Z]+)`$")
METADATA_PATTERN = re.compile(r"^- (?:URL|Method):")
LEGACY_TITLE_PATTERN = re.compile(
    r"^(?:GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD|TRACE) /"
)
USERNAME_PATTERN = re.compile(r"[a-z0-9._-]+\.example")
SENSITIVE_VALUES = {
    "password": {"<password>", "<new-password>"},
    "new_password": {"<new-password>"},
    "token": {"<opaque-token>"},
    "access_token": {"<opaque-token>"},
}


@dataclass(frozen=True)
class WikiOperation:
    source: str
    title: str
    method: str
    path: str
    markdown: str


OperationKey = tuple[str, str]
RESPONSE_MODELS: dict[OperationKey, type[BaseModel]] = {
    ("POST", "/api/auth/token"): TokenResponse,
    ("GET", "/api/auth/me"): CurrentUserResponse,
    ("GET", "/ping"): PingResponse,
}


def parse_wiki_operations(markdown: str, *, source: str) -> list[WikiOperation]:
    headings = list(H2_PATTERN.finditer(markdown))
    operations: list[WikiOperation] = []

    for index, heading in enumerate(headings):
        title = heading.group("title")
        assert not LEGACY_TITLE_PATTERN.match(title), (
            f'{source} section "{title}" must use a business-action title'
        )
        section_end = (
            headings[index + 1].start()
            if index + 1 < len(headings)
            else len(markdown)
        )
        section = markdown[heading.end() : section_end]
        prologue = re.split(r"^### ", section, maxsplit=1, flags=re.MULTILINE)[0]
        lines = [line.strip() for line in prologue.splitlines() if line.strip()]
        metadata = [line for line in lines if METADATA_PATTERN.match(line)]
        if not metadata:
            continue

        assert len(lines) >= 2 and metadata == lines[:2], (
            f'{source} section "{title}" must declare URL and Method first'
        )
        assert len(metadata) == 2, (
            f'{source} section "{title}" must declare exactly one URL and Method'
        )
        url_match = URL_PATTERN.fullmatch(metadata[0])
        method_match = METHOD_PATTERN.fullmatch(metadata[1])
        assert url_match is not None and method_match is not None, (
            f'{source} section "{title}" metadata does not match API_TEMPLATE.md'
        )
        method = method_match.group("method")
        assert method in HTTP_METHODS, (
            f'{source} section "{title}" uses an unsupported method'
        )
        operations.append(
            WikiOperation(
                source=source,
                title=title,
                method=method,
                path=url_match.group("path"),
                markdown=section,
            )
        )

    title_counts = Counter(operation.title for operation in operations)
    duplicate_titles = sorted(
        title for title, count in title_counts.items() if count > 1
    )
    assert not duplicate_titles, (
        f"{source} has duplicate operation titles: {', '.join(duplicate_titles)}"
    )
    return operations


def load_wiki_operations() -> dict[OperationKey, WikiOperation]:
    collected: dict[OperationKey, WikiOperation] = {}
    for path in WIKI_ROOT.glob("*.md"):
        if path.name == "API_TEMPLATE.md":
            continue
        for operation in parse_wiki_operations(
            path.read_text(),
            source=path.name,
        ):
            key = (operation.method, operation.path)
            assert key not in collected, (
                f"Duplicate Wiki operation: {operation.method} {operation.path}"
            )
            collected[key] = operation
    return collected


def code_blocks_after_marker(
    markdown: str,
    marker: str,
) -> list[tuple[str, str]]:
    marker_match = re.search(
        rf"^#### {re.escape(marker)}\s*$",
        markdown,
        flags=re.MULTILINE,
    )
    if marker_match is None:
        return []
    remaining = markdown[marker_match.end() :]
    next_heading = re.search(r"^#{1,4} ", remaining, flags=re.MULTILINE)
    marker_section = (
        remaining[: next_heading.start()]
        if next_heading is not None
        else remaining
    )
    return [
        (match.group("language").lower(), match.group("content").strip())
        for match in CODE_FENCE_PATTERN.finditer(marker_section)
    ]


def validate_sensitive_field(key: str, value: Any, *, location: str) -> None:
    if key == "username":
        assert isinstance(value, str) and USERNAME_PATTERN.fullmatch(value), (
            f"{location} username must use a .example sample value"
        )
    if key in SENSITIVE_VALUES:
        assert value in SENSITIVE_VALUES[key], (
            f"{location} {key} must use an allowed placeholder"
        )


def validate_json_value(value: Any, *, location: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            validate_sensitive_field(key, child, location=location)
            validate_json_value(child, location=location)
    elif isinstance(value, list):
        for child in value:
            validate_json_value(child, location=location)


def validate_operation_examples(
    key: OperationKey,
    operation: WikiOperation,
    openapi_operation: dict[str, Any],
) -> None:
    location = f'{operation.source} section "{operation.title}"'
    missing_sections = {
        section
        for section in REQUIRED_OPERATION_SECTIONS
        if f"### {section}" not in operation.markdown
    }
    assert not missing_sections, (
        f"{location} is missing contract sections: "
        f"{', '.join(sorted(missing_sections))}"
    )

    request_body = openapi_operation.get("requestBody")
    if request_body is None:
        assert "**Request body: none.**" in operation.markdown, (
            f'{location} is missing the "Request body: none" marker'
        )
    else:
        request_blocks = code_blocks_after_marker(
            operation.markdown,
            "Request Body Example",
        )
        request_languages = {language for language, _ in request_blocks}
        content_types = set(request_body.get("content", {}))
        if "application/json" in content_types:
            assert "json" in request_languages, (
                f"{location} is missing a JSON request body example"
            )
        if "application/x-www-form-urlencoded" in content_types:
            assert "text" in request_languages, (
                f"{location} is missing a form request body example"
            )

    success_responses = [
        response
        for status, response in openapi_operation.get("responses", {}).items()
        if str(status).startswith("2")
    ]
    success_content_types = {
        content_type
        for response in success_responses
        for content_type in response.get("content", {})
    }
    response_blocks = code_blocks_after_marker(
        operation.markdown,
        "Successful Response Example",
    )
    if "application/json" in success_content_types:
        json_examples = [
            content for language, content in response_blocks if language == "json"
        ]
        assert len(json_examples) == 1, (
            f"{location} must have exactly one successful JSON response example"
        )
        example = json.loads(json_examples[0])
        model = RESPONSE_MODELS.get(key)
        assert model is not None, (
            f"{location} is missing a response-example model mapping"
        )
        assert set(example) == set(model.model_fields), (
            f"{location} response fields do not match {model.__name__}"
        )
        model.model_validate(example)
    else:
        assert "**Response body: none.**" in operation.markdown, (
            f'{location} is missing the "Response body: none" marker'
        )

    for language, content in CODE_FENCE_PATTERN.findall(operation.markdown):
        if language.lower() == "json":
            value = json.loads(content)
            validate_json_value(value, location=location)
        elif language.lower() == "text" and "=" in content:
            for field, value in parse_qsl(content.strip(), keep_blank_values=True):
                validate_sensitive_field(field, value, location=location)


def test_wiki_operations_match_openapi() -> None:
    wiki_operations = load_wiki_operations()
    openapi = app.openapi()
    openapi_operations = {
        (method.upper(), path)
        for path, path_item in openapi["paths"].items()
        for method in path_item
        if method.upper() in HTTP_METHODS
    }

    assert set(wiki_operations) == openapi_operations


def test_wiki_examples_match_openapi_and_response_models() -> None:
    wiki_operations = load_wiki_operations()
    openapi = app.openapi()

    for key, operation in wiki_operations.items():
        method, path = key
        validate_operation_examples(
            key,
            operation,
            openapi["paths"][path][method.lower()],
        )
