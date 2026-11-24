from sec_rag_analyst.judge import build_judge_prompt, parse_judgement


def test_parse_good_reply():
    r = parse_judgement('{"verdict": "correct", "supported": true, "reason": "matches"}')
    assert r["verdict"] == "correct" and r["supported"] is True and r["reason"] == "matches"


def test_parse_accepts_yes_string_for_supported():
    assert parse_judgement('{"verdict": "incorrect", "supported": "yes", "reason": ""}')["supported"] is True


def test_parse_bad_verdict_becomes_error():
    assert parse_judgement('{"verdict": "maybe", "supported": true}')["verdict"] == "error"


def test_parse_not_json_becomes_error():
    assert parse_judgement("I think it is correct")["verdict"] == "error"


def test_prompt_contains_all_parts():
    p = build_judge_prompt("Q?", "gold", "model", [{"page_number": 7, "text": "some   text"}])
    assert "Q?" in p and "Gold answer: gold" in p and "Model answer: model" in p and "[page 7]\nsome text" in p


def test_is_not_found():
    from sec_rag_analyst.judge import is_not_found

    assert is_not_found("not found (page 84, page 99)")
    assert is_not_found("The excerpts do not contain the answer. not found (page 82)")
    assert not is_not_found("Revenue was $5 million. " * 20 + "The risk was not found to be material.")
    assert not is_not_found("Yes, American Express retained card members.")
