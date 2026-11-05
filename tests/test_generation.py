from sec_rag_analyst.generation import build_prompt


def test_prompt_labels_each_excerpt_with_its_page_and_ends_with_the_question():
    hits = [
        {"page_number": 60, "text": "Purchases of property,\n\n plant and equipment (1,577)"},
        {"page_number": 58, "text": "Total assets 36,500"},
    ]
    prompt = build_prompt("What was capex?", hits)

    assert "[page 60]\nPurchases of property, plant and equipment (1,577)" in prompt
    assert "[page 58]\nTotal assets 36,500" in prompt
    assert prompt.endswith("Question: What was capex?")
    assert "not found" in prompt
