"""Tests for nl_cli.py — fallback parser and response formatter."""

from src.biliwatchlater.nl_cli import ParsedIntent, SessionContext, _parse_fallback, _resolve_bvids


class TestFallbackParser:
    def test_search_keyword(self):
        intent = _parse_fallback("帮我找AI有关的视频")
        assert intent.action == "search"
        assert "AI" in intent.params.get("query", "")

    def test_search_query_direct(self):
        intent = _parse_fallback("搜索Python")
        assert intent.action == "search"
        assert "Python" in intent.params.get("query", "")

    def test_stats_overview(self):
        intent = _parse_fallback("统计一下")
        assert intent.action == "stats"
        assert intent.params.get("type") == "overview"
        intent = _parse_fallback("看下整体")
        assert intent.action == "stats"

    def test_stats_duration(self):
        intent = _parse_fallback("时长分布")
        assert intent.action == "stats"
        assert intent.params.get("type") == "duration"

    def test_sync(self):
        intent = _parse_fallback("同步一下")
        assert intent.action == "sync"

    def test_help(self):
        intent = _parse_fallback("帮助")
        assert intent.action == "help"
        intent = _parse_fallback("怎么用")
        assert intent.action == "help"

    def test_default_fallback_to_search(self):
        intent = _parse_fallback("今天有什么好看的")
        assert intent.action == "search"
        assert intent.params.get("query", "") == "今天有什么好看的"


class TestBvidResolution:
    def test_direct_bvid(self):
        ctx = SessionContext(last_results=[
            {"bvid": "BV1ResultAA", "title": "Video A"},
        ])
        result = _resolve_bvids({"bvid": "BV1ResultAA"}, ctx)
        assert result["bvid"] == "BV1ResultAA"

    def test_ordinal_reference(self):
        ctx = SessionContext(last_results=[
            {"bvid": "BV1First", "title": "First"},
            {"bvid": "BV1Second", "title": "Second"},
        ])
        result = _resolve_bvids({"bvid": "result_1"}, ctx)
        assert result["bvid"] == "BV1First"
        result = _resolve_bvids({"bvid": "result_2"}, ctx)
        assert result["bvid"] == "BV1Second"

    def test_ordinal_out_of_range(self):
        ctx = SessionContext(last_results=[{"bvid": "BV1Only"}])
        result = _resolve_bvids({"bvid": "result_99"}, ctx)
        assert result["bvid"] == "result_99"  # unchanged

    def test_no_bvid_param_unchanged(self):
        ctx = SessionContext()
        result = _resolve_bvids({"name": "test"}, ctx)
        assert result == {"name": "test"}

    def test_empty_results_ordinal(self):
        ctx = SessionContext()
        result = _resolve_bvids({"bvid": "result_1"}, ctx)
        assert result["bvid"] == "result_1"


class TestParsedIntentDataclass:
    def test_defaults(self):
        intent = ParsedIntent(action="help")
        assert intent.action == "help"
        assert intent.params == {}
        assert intent.raw == ""

    def test_with_params(self):
        intent = ParsedIntent(action="search", params={"query": "AI"}, raw="帮我找AI")
        assert intent.action == "search"
        assert intent.params["query"] == "AI"
        assert intent.raw == "帮我找AI"
