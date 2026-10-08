from starlette.requests import Request

from src.utils.cache import request_key_builder


def _request(query: bytes) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/comforts",
            "query_string": query,
            "headers": [],
        }
    )


async def endpoint(): ...


def test_key_ignores_endpoint_kwargs_and_query_order():
    key_1 = request_key_builder(
        endpoint, "ns", request=_request(b"a=1&b=2"), args=(), kwargs={"db": object()}
    )
    key_2 = request_key_builder(
        endpoint, "ns", request=_request(b"b=2&a=1"), args=(), kwargs={"db": object()}
    )
    assert key_1 == key_2 == "ns:/api/v1/comforts?a=1&b=2"


def test_key_depends_on_query():
    key_1 = request_key_builder(endpoint, "ns", request=_request(b"a=1"), args=(), kwargs={})
    key_2 = request_key_builder(endpoint, "ns", request=_request(b"a=2"), args=(), kwargs={})
    assert key_1 != key_2
