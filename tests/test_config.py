import pytest

from prowlarr2tx.config import ConfigError, parse_transmission


@pytest.mark.parametrize(
    "tx, expected",
    [
        ({"host": "h"}, ("h", 9091, "http", "/transmission/rpc")),
        ({"host": "h", "port": 1234}, ("h", 1234, "http", "/transmission/rpc")),
        ({"host": "https://x.org", "port": 443}, ("x.org", 443, "https", "/transmission/rpc")),
        ({"host": "https://x.org"}, ("x.org", 443, "https", "/transmission/rpc")),
        ({"host": "http://x.org:8080/tx/rpc"}, ("x.org", 8080, "http", "/tx/rpc")),
        ({"host": "x.org", "protocol": "https", "port": 443}, ("x.org", 443, "https", "/transmission/rpc")),
    ],
)
def test_parse_transmission(tx, expected):
    assert parse_transmission(tx, "t") == expected


def test_bad_protocol():
    with pytest.raises(ConfigError):
        parse_transmission({"host": "ftp://x"}, "t")
