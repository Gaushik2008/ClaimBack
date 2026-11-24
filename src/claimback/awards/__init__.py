"""Insurance Ombudsman award ingestion: PDF text -> structured cases."""

from .parser import Award, parse_award, split_awards

__all__ = ["Award", "parse_award", "split_awards"]
