from fprime_mcp.tools.network_search import (
    NetworkSearchRequest,
    convert_results_to_csv,
    search_network_by_natural_language,
)


def test_request_requires_any_search_criteria() -> None:
    request = NetworkSearchRequest()
    assert request.has_search_criteria() is False


def test_convert_results_to_csv_includes_header_and_values() -> None:
    data = [
        {
            "person_name": "Jane Doe",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "function": ["engineering", "product"],
            "HaveContactedInLastYear": True,
        }
    ]
    csv_output = convert_results_to_csv(data)
    assert "person_name,linkedin_url,title,company_name" in csv_output
    assert "Jane Doe" in csv_output
    assert "engineering; product" in csv_output


def test_tool_rejects_empty_search_payload() -> None:
    result = search_network_by_natural_language()
    assert result["success"] is False
    assert "At least one" in result["error"]


def test_tool_rejects_invalid_response_format() -> None:
    result = search_network_by_natural_language(text_queries=["cto"], response_format="xml")
    assert result["success"] is False
    assert "Validation error" in result["error"]
