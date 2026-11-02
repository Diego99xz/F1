from collections.abc import Callable

import httpx
import pytest

import f1.client as client_module
from f1 import OpenF1Client, OpenF1Error, OpenF1RequestError, OpenF1ResponseError


@pytest.fixture(autouse=True)
def disable_process_rate_limiter_for_mocked_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(client_module._REQUEST_RATE_LIMITER, "acquire", lambda: None)


def make_client(handler: httpx.MockTransport | None = None) -> OpenF1Client:
    transport = handler or httpx.MockTransport(
        lambda request: httpx.Response(200, json=[{"session_key": 1}])
    )
    return OpenF1Client(transport=transport)


def test_get_returns_records_and_encodes_query_parameters() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[{"speed": 320}])

    with make_client(httpx.MockTransport(handler)) as client:
        result = client.get(
            "/car_data",
            params={"session_key": 9158, "speed>=": 315},
        )

    assert result == [{"speed": 320}]
    assert requests[0].url.path == "/v1/car_data"
    assert requests[0].url.params["session_key"] == "9158"
    assert requests[0].url.params["speed>="] == "315"


@pytest.mark.parametrize(
    ("call", "endpoint", "expected_params"),
    [
        (lambda client: client.meetings(year=2023), "meetings", {"year": "2023"}),
        (
            lambda client: client.sessions(meeting_key=123, year=2023),
            "sessions",
            {"meeting_key": "123", "year": "2023"},
        ),
        (
            lambda client: client.drivers(9158, driver_number=1),
            "drivers",
            {"session_key": "9158", "driver_number": "1"},
        ),
        (
            lambda client: client.laps(
                9158,
                driver_number=1,
                date_start="start",
                date_end="end",
            ),
            "laps",
            {
                "session_key": "9158",
                "driver_number": "1",
                "date_start": "start",
                "date_end": "end",
            },
        ),
        (
            lambda client: client.car_data(9158, driver_number=1),
            "car_data",
            {"session_key": "9158", "driver_number": "1"},
        ),
        (
            lambda client: client.weather(9158, date_start="start", date_end="end"),
            "weather",
            {"session_key": "9158", "date_start": "start", "date_end": "end"},
        ),
    ],
)
def test_endpoint_helpers_send_supported_filters(
    call: Callable[[OpenF1Client], object],
    endpoint: str,
    expected_params: dict[str, str],
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    with make_client(httpx.MockTransport(handler)) as client:
        call(client)

    assert requests[0].url.path == f"/v1/{endpoint}"
    assert dict(requests[0].url.params) == expected_params


def test_optional_filters_are_omitted() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    with make_client(httpx.MockTransport(handler)) as client:
        result = client.meetings()

    assert dict(requests[0].url.params) == {}
    assert result == []


def test_historical_query_sends_the_selected_year() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[{"meeting_key": 123}])

    with make_client(httpx.MockTransport(handler)) as client:
        result = client.meetings(year=2023)

    assert result == [{"meeting_key": 123}]
    assert requests[0].url.params["year"] == "2023"


def test_http_error_is_wrapped_with_request_context() -> None:
    with make_client(
        httpx.MockTransport(lambda request: httpx.Response(503))
    ) as client:
        with pytest.raises(
            OpenF1RequestError,
            match=r"GET /sessions returned HTTP 503",
        ) as error:
            client.get("sessions")

    assert isinstance(error.value.__cause__, httpx.HTTPStatusError)
    assert error.value.status_code == 503
    assert error.value.endpoint == "sessions"
    assert error.value.params == {}


def test_http_error_includes_api_detail() -> None:
    with make_client(
        httpx.MockTransport(
            lambda request: httpx.Response(
                401,
                json={"detail": "Historical access is temporarily restricted"},
            )
        )
    ) as client:
        with pytest.raises(
            OpenF1RequestError,
            match="Historical access is temporarily restricted",
        ) as error:
            client.get("meetings")

    assert error.value.status_code == 401


@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
def test_non_retryable_http_errors_are_attempted_once(status_code: int) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, json={"detail": "request failed"})

    with make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(OpenF1RequestError) as error:
            client.meetings(year=2023)

    assert len(requests) == 1
    assert error.value.status_code == status_code
    assert error.value.endpoint == "meetings"
    assert error.value.params == {"year": 2023}
    assert "year=2023" in str(error.value)


def test_rate_limit_retries_after_retry_after_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(200, json=[]),
        ]
    )
    delays: list[float] = []
    monkeypatch.setattr(client_module.time, "sleep", delays.append)

    with make_client(httpx.MockTransport(lambda request: next(responses))) as client:
        assert client.get("meetings") == []

    assert delays == [2.0]


def test_rate_limit_does_not_retry_before_long_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(429, headers={"Retry-After": "120"})

    monkeypatch.setattr(client_module.time, "sleep", delays.append)
    with make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(OpenF1RequestError) as error:
            client.get("meetings")

    assert len(requests) == 1
    assert delays == []
    assert error.value.retry_after == 120


def test_server_error_retries_a_bounded_number_of_times(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503)

    monkeypatch.setattr(client_module.time, "sleep", delays.append)
    monkeypatch.setattr(client_module.random, "uniform", lambda start, end: 0)
    with make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(OpenF1RequestError) as error:
            client.get("sessions")

    assert len(requests) == 3
    assert delays == [0.5, 1.0]
    assert error.value.status_code == 503


def test_timeout_retries_and_can_recover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            raise httpx.ReadTimeout("request timed out", request=request)
        return httpx.Response(200, json=[])

    monkeypatch.setattr(client_module.time, "sleep", lambda delay: None)
    with make_client(httpx.MockTransport(handler)) as client:
        assert client.get("sessions") == []

    assert len(requests) == 2


def test_connection_error_stops_after_retry_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(client_module.time, "sleep", lambda delay: None)
    with make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(OpenF1RequestError) as error:
            client.get("sessions")

    assert len(requests) == 3
    assert error.value.cause_type == "ConnectError"
    assert "after 3 attempts" in str(error.value)


def test_network_error_is_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(client_module.time, "sleep", lambda delay: None)
    with make_client(httpx.MockTransport(handler)) as client:
        with pytest.raises(OpenF1RequestError, match="connection refused"):
            client.get("meetings")


def test_invalid_json_raises_response_error() -> None:
    with make_client(
        httpx.MockTransport(lambda request: httpx.Response(200, content=b"{"))
    ) as client:
        with pytest.raises(OpenF1ResponseError, match="invalid JSON"):
            client.get("sessions")


@pytest.mark.parametrize("payload", [{"session_key": 1}, [1, {"ok": True}]])
def test_non_collection_response_raises_response_error(payload: object) -> None:
    with make_client(
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(OpenF1ResponseError, match="JSON array of objects"):
            client.get("sessions")


@pytest.mark.parametrize("endpoint", ["", "/", "sessions/laps", "sessions?year=2023"])
def test_invalid_endpoint_is_rejected(endpoint: str) -> None:
    with make_client() as client:
        with pytest.raises(ValueError, match="single OpenF1 resource"):
            client.get(endpoint)


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        OpenF1Client(timeout=0)


def test_request_rate_limiter_enforces_three_requests_per_second() -> None:
    current_time = 0.0
    delays: list[float] = []

    def clock() -> float:
        return current_time

    def sleep(seconds: float) -> None:
        nonlocal current_time
        delays.append(seconds)
        current_time += seconds

    limiter = client_module._RequestRateLimiter(
        max_per_second=3,
        max_per_minute=30,
        clock=clock,
        sleep=sleep,
    )
    for _ in range(4):
        limiter.acquire()

    assert delays == [1.0]
    assert list(limiter._requests) == [0.0, 0.0, 0.0, 1.0]


def test_request_rate_limiter_enforces_thirty_requests_per_minute() -> None:
    current_time = 0.0
    delays: list[float] = []

    def clock() -> float:
        return current_time

    def sleep(seconds: float) -> None:
        nonlocal current_time
        delays.append(seconds)
        current_time += seconds

    limiter = client_module._RequestRateLimiter(
        max_per_second=100,
        max_per_minute=2,
        clock=clock,
        sleep=sleep,
    )
    for _ in range(3):
        limiter.acquire()

    assert delays == [60.0]
    assert list(limiter._requests) == [60.0]


def test_client_can_be_used_after_context_manager_exit() -> None:
    client = make_client()
    with client:
        assert not client._client.is_closed

    assert client._client.is_closed


def test_client_errors_share_a_base_exception() -> None:
    assert issubclass(OpenF1RequestError, OpenF1Error)
    assert issubclass(OpenF1ResponseError, OpenF1Error)
