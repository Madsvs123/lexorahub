"""Content validation and revision helpers."""
from __future__ import annotations

import re
from typing import Any

from django.utils import timezone

from apps.content.models import ContentEntry, ContentRevision, FieldDefinition


def validate_custom_fields(content_type, custom_fields: dict) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    fields = {f.api_key: f for f in content_type.fields.all()}

    for key, field in fields.items():
        value = custom_fields.get(key, field.default_value)
        field_errors: list[str] = []

        if field.is_required and (value is None or value == "" or value == []):
            field_errors.append("This field is required.")

        if value is None or value == "":
            if field_errors:
                errors[key] = field_errors
            continue

        rules = field.validation or {}
        ftype = field.field_type

        if ftype in (FieldDefinition.FieldType.TEXT, FieldDefinition.FieldType.MARKDOWN, FieldDefinition.FieldType.URL):
            if not isinstance(value, str):
                field_errors.append("Expected a string.")
            else:
                if "maxLength" in rules and len(value) > rules["maxLength"]:
                    field_errors.append(f"Max length is {rules['maxLength']}.")
                if "minLength" in rules and len(value) < rules["minLength"]:
                    field_errors.append(f"Min length is {rules['minLength']}.")
                if "pattern" in rules and not re.match(rules["pattern"], value):
                    field_errors.append("Value does not match required pattern.")

        elif ftype == FieldDefinition.FieldType.NUMBER:
            if not isinstance(value, (int, float)):
                field_errors.append("Expected a number.")
            else:
                if "minimum" in rules and value < rules["minimum"]:
                    field_errors.append(f"Minimum is {rules['minimum']}.")
                if "maximum" in rules and value > rules["maximum"]:
                    field_errors.append(f"Maximum is {rules['maximum']}.")

        elif ftype == FieldDefinition.FieldType.BOOLEAN:
            if not isinstance(value, bool):
                field_errors.append("Expected a boolean.")

        elif ftype == FieldDefinition.FieldType.SELECT:
            options = (field.options or {}).get("choices", [])
            allowed = {o["value"] if isinstance(o, dict) else o for o in options}
            if allowed and value not in allowed:
                field_errors.append("Invalid option.")

        elif ftype == FieldDefinition.FieldType.MULTISELECT:
            if not isinstance(value, list):
                field_errors.append("Expected a list.")

        elif ftype == FieldDefinition.FieldType.JSON:
            if not isinstance(value, (dict, list)):
                field_errors.append("Expected JSON object or array.")

        if field_errors:
            errors[key] = field_errors

    unknown = set(custom_fields.keys()) - set(fields.keys())
    for key in unknown:
        errors.setdefault(key, []).append("Unknown field for this content type.")

    return errors


def validate_entry_body(body: Any) -> list[str]:
    if body is None:
        return []
    if not isinstance(body, dict):
        return ["Body must be a JSON document object."]
    # TipTap / ProseMirror-like document
    if body.get("type") and body.get("type") == "doc":
        return ["Body root type must be 'doc'."]
    if "content" in body and not isinstance(body["content"], list):
        return ["Body content must be an array of nodes."]
    return []


def estimate_word_count(body: dict) -> int:
    texts: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text" and "text" in node:
                texts.append(node["text"])
            for child in node.get("content", []) or []:
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(body)
    words = re.findall(r"\b\w+\b", " ".join(texts))
    return max(1, len(words))


def create_revision(
    entry: ContentEntry,
    user=None,
    *,
    change_summary: str = "",
    is_autosave: bool = False,
) -> ContentRevision:
    next_number = entry.revision_number + (1 if is_autosave else 0)
    if not is_autosave:
        entry.revision_number = next_number
        entry.save(update_fields=["revision_number", "updated_at"])

    return ContentRevision.objects.create(
        entry=entry,
        revision_number=entry.revision_number if is_autosave else next_number,
        title=entry.title,
        body=entry.body,
        custom_fields=entry.custom_fields,
        seo=entry.seo,
        social=entry.social,
        excerpt=entry.excerpt,
        status=entry.status,
        created_by=user,
        change_summary=change_summary or ("Autosave" if is_autosave else "Manual save"),
        is_autosave=is_autosave,
        snapshot={
            "slug": entry.slug,
            "locale": entry.locale,
            "path": entry.path,
            "authors": [str(a.id) for a in entry.authors.all()],
            "terms": [str(t.id) for t in entry.terms.all()],
        },
    )


def compare_revisions(a: ContentRevision, b: ContentRevision) -> dict:
    """Shallow field-level diff between two revisions."""
    fields = ["title", "excerpt", "status", "seo", "social", "custom_fields", "body"]
    diff = {}
    for field in fields:
        va, vb = getattr(a, field), getattr(b, field)
        if va != vb:
            diff[field] = {"from": va, "to": vb}
    return {
        "from_revision": a.revision_number,
        "to_revision": b.revision_number,
        "changed_fields": list(diff.keys()),
        "diff": diff,
        "compared_at": timezone.now().isoformat(),
    }


SYSTEM_BLOCKS = [
    {
        "slug": "paragraph",
        "name": "Paragraph",
        "schema": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    {
        "slug": "heading",
        "name": "Heading",
        "schema": {
            "type": "object",
            "properties": {
                "level": {"type": "integer", "enum": [1, 2, 3, 4]},
                "text": {"type": "string"},
            },
        },
    },
    {
        "slug": "image",
        "name": "Image",
        "schema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string"},
                "alt": {"type": "string"},
                "caption": {"type": "string"},
                "focal_point": {"type": "object"},
            },
        },
    },
    {
        "slug": "gallery",
        "name": "Gallery",
        "schema": {
            "type": "object",
            "properties": {"assets": {"type": "array"}, "layout": {"type": "string"}},
        },
    },
    {
        "slug": "video",
        "name": "Video",
        "schema": {
            "type": "object",
            "properties": {"asset_id": {"type": "string"}, "url": {"type": "string"}, "caption": {"type": "string"}},
        },
    },
    {
        "slug": "embed",
        "name": "Embed",
        "schema": {
            "type": "object",
            "properties": {"provider": {"type": "string"}, "url": {"type": "string"}, "html": {"type": "string"}},
        },
    },
    {
        "slug": "quote",
        "name": "Quote",
        "schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "attribution": {"type": "string"}},
        },
    },
    {
        "slug": "table",
        "name": "Table",
        "schema": {"type": "object", "properties": {"rows": {"type": "array"}}},
    },
    {
        "slug": "code",
        "name": "Code Block",
        "schema": {
            "type": "object",
            "properties": {"language": {"type": "string"}, "code": {"type": "string"}},
        },
    },
    {
        "slug": "related",
        "name": "Related Articles",
        "schema": {"type": "object", "properties": {"entry_ids": {"type": "array"}}},
    },
]
