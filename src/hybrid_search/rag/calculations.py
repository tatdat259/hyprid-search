"""Deterministic calculations over explicitly sourced financial table values."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, Optional

from hybrid_search.models.search import SearchResult


@dataclass(frozen=True)
class RevenueFact:
    year: str
    amount: Decimal
    unit: str
    chunk_id: str
    ticker: str


@dataclass(frozen=True)
class CalculationResult:
    answer: str
    chunk_ids: list[str]


class RevenueGrowthCalculator:
    _year_pattern = re.compile(r"\b(?:fy\s*)?(20\d{2})\b", re.IGNORECASE)
    _number_pattern = re.compile(r"\(?\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\)?")
    _unit_pattern = re.compile(r"\b(?:in\s+)?(thousands|millions|billions)\b", re.IGNORECASE)
    _company_aliases = {
        "apple": "AAPL", "aapl": "AAPL",
        "microsoft": "MSFT", "msft": "MSFT",
        "nvidia": "NVDA", "nvda": "NVDA",
        "alphabet": "GOOGL", "google": "GOOGL", "googl": "GOOGL",
        "amazon": "AMZN", "amzn": "AMZN",
        "meta": "META", "facebook": "META",
        "tesla": "TSLA", "tsla": "TSLA",
    }

    @classmethod
    def requested_years(cls, query: str) -> Optional[tuple[str, str]]:
        lower = query.lower()
        if not ("revenue" in lower or "net sales" in lower):
            return None
        if not any(term in lower for term in ("growth", "growth rate", "percentage change", "percent change", "tăng trưởng")):
            return None
        years = list(dict.fromkeys(cls._year_pattern.findall(query)))
        if len(years) != 2:
            return None
        return years[0], years[1]

    @classmethod
    def combined_requested(cls, query: str) -> bool:
        lower = query.lower()
        return (
            ("revenue" in lower or "net sales" in lower)
            and any(term in lower for term in ("combined", "total", "sum", "tổng", "cộng"))
            and len(cls._mentioned_companies(query)) >= 2
        )

    @classmethod
    def calculation_requested(cls, query: str) -> bool:
        return cls.requested_years(query) is not None or cls.combined_requested(query)

    @classmethod
    def _mentioned_companies(cls, query: str) -> list[str]:
        lower = query.lower()
        return list(dict.fromkeys(
            ticker for name, ticker in cls._company_aliases.items()
            if re.search(r"\b" + re.escape(name) + r"\b", lower)
        ))

    @classmethod
    def calculate(cls, query: str, results: Iterable[SearchResult], language: str) -> Optional[CalculationResult]:
        years = cls.requested_years(query)
        if not years:
            return None
        requested_companies = cls._mentioned_companies(query)
        start = end = None
        for result in results:
            if requested_companies and result.ticker.upper() not in requested_companies:
                continue
            row_facts = {fact.year: fact for fact in cls._table_facts(result)}
            if set(years).issubset(row_facts):
                start, end = row_facts[years[0]], row_facts[years[1]]
                break
        if start is None or end is None:
            return None
        if start.unit != end.unit or start.amount == 0:
            return None
        growth = ((end.amount - start.amount) / start.amount * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        source_ids = list(dict.fromkeys([start.chunk_id, end.chunk_id]))
        if language == "vi":
            answer = (
                f"Tăng trưởng doanh thu từ FY{start.year} đến FY{end.year} là {growth}% "
                f"= ({cls._format(end.amount)} - {cls._format(start.amount)}) / {cls._format(start.amount)} x 100."
            )
        else:
            answer = (
                f"Revenue growth from FY{start.year} to FY{end.year} was {growth}% "
                f"= ({cls._format(end.amount)} - {cls._format(start.amount)}) / {cls._format(start.amount)} x 100."
            )
        return CalculationResult(answer=answer, chunk_ids=source_ids)

    @classmethod
    def calculate_combined(cls, query: str, results: Iterable[SearchResult], language: str) -> Optional[CalculationResult]:
        if not cls.combined_requested(query):
            return None
        requested = cls._mentioned_companies(query)
        years = list(dict.fromkeys(cls._year_pattern.findall(query)))
        if len(years) != 1:
            return None
        year = years[0]
        facts: dict[str, RevenueFact] = {}
        for result in results:
            for fact in cls._table_facts(result):
                if fact.ticker in requested and fact.year == year and fact.ticker not in facts:
                    facts[fact.ticker] = fact
        if set(facts) != set(requested) or len({fact.unit for fact in facts.values()}) != 1:
            return None
        total = sum((fact.amount for fact in facts.values()), Decimal("0"))
        source_ids = list(dict.fromkeys(facts[ticker].chunk_id for ticker in requested))
        details = " + ".join(cls._format(facts[ticker].amount) for ticker in requested)
        companies = (" và " if language == "vi" else " and ").join(requested)
        if language == "vi":
            answer = f"Tổng doanh thu của {companies} trong FY{year} là {cls._format(total)} {facts[requested[0]].unit} = {details}."
        else:
            answer = f"Combined revenue of {companies} in FY{year} was {cls._format(total)} {facts[requested[0]].unit} = {details}."
        return CalculationResult(answer=answer, chunk_ids=source_ids)

    @classmethod
    def _table_facts(cls, result: SearchResult) -> list[RevenueFact]:
        cells = [cell.strip() for cell in result.text.split("|")]
        facts: list[RevenueFact] = []
        for index, cell in enumerate(cells):
            label = re.sub(r"\s+", " ", cell.strip().lower()).rstrip(":")
            if label not in {"total revenue", "total net sales", "total"}:
                continue
            if label == "total":
                normalized = [
                    re.sub(r"\s+", " ", value.strip().lower()).rstrip(":")
                    for value in cells[:index]
                ]
                section_headers = {
                    "revenue", "operating income", "cost of revenue", "net income",
                    "assets", "liabilities", "equity", "cash flows",
                }
                nearest_header = next((value for value in reversed(normalized) if value in section_headers), None)
                if nearest_header != "revenue":
                    continue

            values: list[str] = []
            for value_cell in cells[index + 1:]:
                value_cell = value_cell.strip()
                if not value_cell or value_cell in {"$", "(", ")"}:
                    continue
                match = re.fullmatch(r"\(?\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\)?", value_cell)
                if not match:
                    break
                values.append(match.group(1))
            if not values:
                continue

            header_years: list[str] = []
            for prior_cell in cells[:index]:
                prior_cell = prior_cell.strip()
                year_match = re.fullmatch(r"(?:FY\s*)?(20\d{2})", prior_cell, re.IGNORECASE)
                if not year_match:
                    year_match = re.search(
                        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(20\d{2})\b",
                        prior_cell, re.IGNORECASE,
                    )
                if year_match and year_match.group(1) not in header_years:
                    header_years.append(year_match.group(1))
            header_years = header_years[-len(values):]
            if len(header_years) != len(values):
                period_match = re.search(r"\bFY\s*(20\d{2})\b", result.fiscal_period, re.IGNORECASE)
                if len(values) == 1 and period_match:
                    header_years = [period_match.group(1)]
                else:
                    continue

            unit = cls._unit(result.text)
            if not unit:
                continue
            for year, raw in zip(header_years, values):
                try:
                    facts.append(RevenueFact(
                        year, Decimal(raw.replace(",", "")), unit,
                        result.chunk_id, result.ticker.upper(),
                    ))
                except InvalidOperation:
                    continue
        return facts
    @classmethod
    def _unit(cls, text: str) -> Optional[str]:
        match = cls._unit_pattern.search(text)
        return match.group(1).lower() if match else None

    @staticmethod
    def _format(amount: Decimal) -> str:
        return f"{amount:,.0f}"