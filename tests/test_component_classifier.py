"""Tests for component_classifier.py"""

from rsb.scaffold.component_classifier import ComponentType, classify_component


def test_classifies_client_component_with_hooks(cra_basic_path) -> None:
    home = cra_basic_path / "src" / "pages" / "Home.jsx"
    result = classify_component(home)
    assert result.component_type == ComponentType.CLIENT
    assert result.has_data_fetching is True


def test_classifies_product_as_client(cra_basic_path) -> None:
    product = cra_basic_path / "src" / "pages" / "Product.jsx"
    result = classify_component(product)
    assert result.component_type == ComponentType.CLIENT


def test_migration_notes_for_react_query(cra_basic_path) -> None:
    home = cra_basic_path / "src" / "pages" / "Home.jsx"
    result = classify_component(home)
    assert len(result.migration_notes) > 0
    combined = " ".join(result.migration_notes).lower()
    assert "server component" in combined or "async" in combined


def test_simple_component_is_server(tmp_path) -> None:
    component = tmp_path / "Static.jsx"
    component.write_text(
        """
import React from 'react';
export default function Static({ title }) {
  return <div><h1>{title}</h1></div>;
}
""",
        encoding="utf-8",
    )
    result = classify_component(component)
    assert result.component_type == ComponentType.SERVER
