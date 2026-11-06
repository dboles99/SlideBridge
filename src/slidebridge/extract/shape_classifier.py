"""Classify a python-pptx shape into a semantic role string."""

from __future__ import annotations

from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

_PLACEHOLDER_TITLE_TYPES = {
    PP_PLACEHOLDER.TITLE,
    PP_PLACEHOLDER.CENTER_TITLE,
    PP_PLACEHOLDER.VERTICAL_TITLE,
}

_PLACEHOLDER_BODY_TYPES = {
    PP_PLACEHOLDER.BODY,
    PP_PLACEHOLDER.OBJECT,
    PP_PLACEHOLDER.SUBTITLE,
    PP_PLACEHOLDER.VERTICAL_BODY,
    PP_PLACEHOLDER.VERTICAL_OBJECT,
}

_PLACEHOLDER_FOOTER_TYPES = {
    PP_PLACEHOLDER.DATE,
    PP_PLACEHOLDER.FOOTER,
    PP_PLACEHOLDER.SLIDE_NUMBER,
}


def classify_shape(shape) -> str:  # type: ignore[no-untyped-def]
    """Return a semantic role string for the given shape.

    Returns one of: title | body | footer | table | picture | group | other
    """
    # Table shapes
    if shape.shape_type == MSO_SHAPE_TYPE.TABLE:
        return "table"

    # Group shapes (contents may contain text but structure is opaque)
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        return "group"

    # Picture / embedded chart
    if shape.shape_type in (MSO_SHAPE_TYPE.PICTURE, MSO_SHAPE_TYPE.LINKED_PICTURE):
        return "picture"

    # Placeholder-based classification
    if shape.is_placeholder:
        ph_type = shape.placeholder_format.type
        if ph_type in _PLACEHOLDER_TITLE_TYPES:
            return "title"
        if ph_type in _PLACEHOLDER_FOOTER_TYPES:
            return "footer"
        if ph_type in _PLACEHOLDER_BODY_TYPES:
            return "body"
        return "body"  # catch-all for unknown placeholder types

    # Free text boxes
    if shape.has_text_frame:
        return "body"

    return "other"
