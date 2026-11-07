from hybrid_search.models.search import SearchResult
from hybrid_search.rag.calculations import RevenueGrowthCalculator


def search_result(text: str) -> SearchResult:
    return SearchResult(
        chunk_id="apple-revenue-table", document_id="apple-2024", score=1, rank=1,
        text=text, company="Apple Inc.", ticker="AAPL", document_type="10-K",
        filing_date="2024-11-01", fiscal_period="FY2024", section="Item 8",
        source_url="https://sec.gov/apple", retrieval_method="rerank",
    )


def test_revenue_growth_uses_sourced_table_values():
    result = RevenueGrowthCalculator.calculate(
        "What is Apple's revenue growth rate from FY2023 to FY2024?",
        [search_result("Amounts in millions\n| Total net sales | 2024 | 2023 |\n| Total net sales | 391,035 | 383,285 |")],
        "en",
    )
    assert result is not None
    assert "2.02%" in result.answer
    assert result.chunk_ids == ["apple-revenue-table"]


def test_revenue_growth_requires_a_unit_and_two_years():
    result = RevenueGrowthCalculator.calculate(
        "What is Apple's revenue growth rate from FY2023 to FY2024?",
        [search_result("| Total net sales | 2024 | 2023 |\n| Total net sales | 391,035 | 383,285 |")],
        "en",
    )
    assert result is None


def test_combined_revenue_sums_requested_company_facts():
    apple = search_result("Amounts in millions | 2024 | Total net sales | 391,035 |")
    microsoft = SearchResult(
        chunk_id="microsoft-revenue-table", document_id="microsoft-2024", score=0.9, rank=8,
        text="Amounts in millions | Year Ended June 30, | 2024 | 2023 | Revenue: | Product | 64,773 | 64,699 | Service and other | 180,349 | 147,216 | Total | 245,122 | 211,915 |",
        company="Microsoft Corporation", ticker="MSFT", document_type="10-K",
        filing_date="2024-07-30", fiscal_period="FY2024", section="Financial Statements",
        source_url="https://sec.gov/microsoft", retrieval_method="rerank",
    )
    result = RevenueGrowthCalculator.calculate_combined(
        "Calculate the combined revenue of Apple and Microsoft in FY2024.",
        [apple, microsoft], "en",
    )
    assert result is not None
    assert "636,157" in result.answer
    assert result.chunk_ids == ["apple-revenue-table", "microsoft-revenue-table"]

def test_revenue_parser_does_not_use_cash_or_assets_from_mixed_chunk():
    mixed = search_result(
        "FY2024 | Cash and cash equivalents | 29,943 | Total assets | 364,980 | "
        "Deferred revenue | 8,249 | text mentions revenue but has no total net sales row"
    )
    result = RevenueGrowthCalculator.calculate_combined(
        "Calculate the combined revenue of Apple and Microsoft in FY2024.", [mixed], "en"
    )
    assert result is None


def test_growth_does_not_mix_revenue_years_from_different_chunks():
    fy2024 = search_result("Amounts in millions | 2024 | Total net sales | 391,035 |")
    fy2023 = search_result("Amounts in millions | 2023 | Total net sales | 383,285 |")
    fy2023.chunk_id = "apple-2023"
    result = RevenueGrowthCalculator.calculate(
        "What is Apple's revenue growth rate from FY2023 to FY2024?", [fy2024, fy2023], "en"
    )
    assert result is None

def test_revenue_total_row_under_revenue_header_and_cash_rows_are_distinguished():
    microsoft = SearchResult(
        chunk_id="microsoft-income", document_id="microsoft-2024", score=0.9, rank=1,
        text=("Amounts in millions | Year Ended June 30, | 2024 | 2023 | 2022 | Revenue: | "
              "Product | $ | 64,773 | $ | 64,699 | $ | 72,732 | "
              "Service and other | 180,349 | 147,216 | 125,538 | "
              "Total | $ | 245,122 | $ | 211,915 | $ | 198,270 |"),
        company="Microsoft Corporation", ticker="MSFT", document_type="10-K",
        filing_date="2024-07-30", fiscal_period="FY2024", section="Financial Statements",
        source_url="https://sec.gov/microsoft", retrieval_method="rerank",
    )
    growth = RevenueGrowthCalculator.calculate(
        "What is Microsoft's revenue growth rate from FY2023 to FY2024?", [microsoft], "en"
    )
    assert growth is not None and "15.67%" in growth.answer

    balance_sheet = search_result(
        "Amounts in millions | September 28, 2024 | September 30, 2023 | "
        "ASSETS: | Cash and cash equivalents | $ | 29,943 | $ | 29,965 | "
        "Total current assets | 152,987 | 143,566 | Total assets | $ | 364,980 | $ | 352,583 | "
        "LIABILITIES: | Deferred revenue | 8,249 | 8,061 | Total liabilities | 308,030 | 290,437 |"
    )
    assert RevenueGrowthCalculator.calculate_combined(
        "Calculate the combined revenue of Apple and Microsoft in FY2024.", [balance_sheet], "en"
    ) is None