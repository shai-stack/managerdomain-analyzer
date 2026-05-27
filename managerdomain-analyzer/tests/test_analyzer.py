from analyzer import parse_managerdomain


def test_parse_single():
    assert parse_managerdomain("MANAGERDOMAIN=openx.com") == ["openx.com"]


def test_parse_multiple():
    text = "MANAGERDOMAIN=openx.com\nMANAGERDOMAIN=pubmatic.com"
    assert parse_managerdomain(text) == ["openx.com", "pubmatic.com"]


def test_parse_case_insensitive():
    assert parse_managerdomain("managerdomain=openx.com") == ["openx.com"]


def test_parse_mixed_case():
    assert parse_managerdomain("ManagerDomain=openx.com") == ["openx.com"]


def test_parse_ignores_comment_lines():
    text = "# managerdomain=openx.com\nMANAGERDOMAIN=pubmatic.com"
    assert parse_managerdomain(text) == ["pubmatic.com"]


def test_parse_no_match():
    assert parse_managerdomain("google.com, pub-123, DIRECT, abc123") == []


def test_parse_empty_string():
    assert parse_managerdomain("") == []


def test_parse_trims_value_whitespace():
    assert parse_managerdomain("MANAGERDOMAIN= openx.com ") == ["openx.com"]


def test_parse_skips_blank_value():
    assert parse_managerdomain("MANAGERDOMAIN=") == []
