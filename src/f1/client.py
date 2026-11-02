"""HTTP client for the historical OpenF1 REST API."""

import json
import math
import random
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from threading import Lock
from typing import Self
from urllib.parse import urlencode

import httpx

API_BASE_URL = "https://api.openf1.org/v1"
QueryValue = str | int | float | bool
MAX_RETRIES = 2
MAX_AUTOMATIC_RETRY_AFTER = 30.0
RETRY_BASE_SECONDS = 0.5
MAX_REQUESTS_PER_SECOND = 3
MAX_REQUESTS_PER_MINUTE = 30


class _RequestRateLimiter:
    """Keep process-wide request volume within the public API quota."""

    def __init__(
        self,
        max_per_second: int,
        max_per_minute: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._max_per_second = max_per_second
        self._max_per_minute = max_per_minute
        self._clock = clock
        self._sleep = sleep
        self._requests: deque[float] = deque()
        self._lock = Lock()

    def acquire(self) -> None:
        while True:
            now = self._clock()
            with self._lock:
                while self._requests and now - self._requests[0] >= 60:
                    self._requests.popleft()

                recent_second = [
                    sent_at for sent_at in self._requests if now - sent_at < 1
                ]
                wait_seconds = 0.0
                if len(recent_second) >= self._max_per_second:
                    wait_seconds = max(
                        wait_seconds,
                        recent_second[0] + 1 - now,
                    )
                if len(self._requests) >= self._max_per_minute:
                    wait_seconds = max(
                        wait_seconds,
                        self._requests[0] + 60 - now,
                    )

                if wait_seconds <= 0:
                    self._requests.append(now)
                    return

            self._sleep(wait_seconds)


_REQUEST_RATE_LIMITER = _RequestRateLimiter(
    MAX_REQUESTS_PER_SECOND,
    MAX_REQUESTS_PER_MINUTE,
)


class OpenF1Error(Exception):
    """Base exception for OpenF1 client errors."""


class OpenF1RequestError(OpenF1Error):
    """Raised when an OpenF1 request fails."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str,
        params: dict[str, QueryValue],
        status_code: int | None = None,
        api_detail: str | None = None,
        retry_after: float | None = None,
        cause_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.params = params
        self.status_code = status_code
        self.api_detail = api_detail
        self.retry_after = retry_after
        self.cause_type = cause_type


class OpenF1ResponseError(OpenF1Error):
    """Raised when an OpenF1 response is not a JSON collection of records."""


class OpenF1Client:
    """Query historical data from the OpenF1 API."""

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self._client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/",
            timeout=timeout,
            transport=transport,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def get(
        self,
        endpoint: str,
        params: dict[str, QueryValue] | None = None,
    ) -> list[dict[str, object]]:
        """Fetch a collection of records from one OpenF1 endpoint."""
        resource = endpoint.strip("/")
        if not resource or "/" in resource or "?" in resource:
            raise ValueError("endpoint must be a single OpenF1 resource name")

        request_params = dict(params) if params else {}
        request_context = self._request_context(resource, request_params)
        for attempt in range(MAX_RETRIES + 1):
            _REQUEST_RATE_LIMITER.acquire()
            try:
                response = self._client.get(resource, params=request_params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                api_detail = self._response_detail(exc.response)
                retry_after = self._retry_after_seconds(
                    exc.response.headers.get("Retry-After")
                )
                if self._should_retry_status(status_code) and attempt < MAX_RETRIES:
                    if (
                        status_code == 429
                        and retry_after is not None
                        and retry_after > MAX_AUTOMATIC_RETRY_AFTER
                    ):
                        raise self._request_error(
                            request_context,
                            endpoint=resource,
                            params=request_params,
                            status_code=status_code,
                            api_detail=api_detail,
                            retry_after=retry_after,
                        ) from exc
                    time.sleep(
                        retry_after
                        if status_code == 429 and retry_after is not None
                        else self._backoff(attempt)
                    )
                    continue
                raise self._request_error(
                    request_context,
                    endpoint=resource,
                    params=request_params,
                    status_code=status_code,
                    api_detail=api_detail,
                    retry_after=retry_after,
                ) from exc
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < MAX_RETRIES:
                    time.sleep(self._backoff(attempt))
                    continue
                raise self._request_error(
                    request_context,
                    endpoint=resource,
                    params=request_params,
                    cause_type=type(exc).__name__,
                    cause_message=str(exc),
                ) from exc
            except httpx.RequestError as exc:
                raise self._request_error(
                    request_context,
                    endpoint=resource,
                    params=request_params,
                    cause_type=type(exc).__name__,
                    cause_message=str(exc),
                ) from exc

            try:
                payload = response.json()
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise OpenF1ResponseError(
                    f"OpenF1 returned invalid JSON for {request_context}"
                ) from exc

            if not isinstance(payload, list) or not all(
                isinstance(record, dict) for record in payload
            ):
                raise OpenF1ResponseError(
                    f"OpenF1 response for {request_context} "
                    "must be a JSON array of objects"
                )

            return payload

        raise AssertionError("request retry loop ended unexpectedly")

    @staticmethod
    def _request_context(
        endpoint: str,
        params: dict[str, QueryValue],
    ) -> str:
        query = urlencode(params)
        return f"GET /{endpoint}{f'?{query}' if query else ''}"

    @staticmethod
    def _request_error(
        request_context: str,
        *,
        endpoint: str,
        params: dict[str, QueryValue],
        status_code: int | None = None,
        api_detail: str | None = None,
        retry_after: float | None = None,
        cause_type: str | None = None,
        cause_message: str | None = None,
    ) -> OpenF1RequestError:
        if status_code is not None:
            message = f"OpenF1 {request_context} returned HTTP {status_code}"
            if api_detail:
                message += f": {api_detail}"
        else:
            message = f"OpenF1 {request_context} failed"
            if cause_type:
                message += f" with {cause_type}"
            if cause_message:
                message += f": {cause_message}"
            message += f" after {MAX_RETRIES + 1} attempts"

        if retry_after is not None:
            message += f" (Retry-After: {retry_after:g} seconds)"

        return OpenF1RequestError(
            message,
            endpoint=endpoint,
            params=params,
            status_code=status_code,
            api_detail=api_detail,
            retry_after=retry_after,
            cause_type=cause_type,
        )

    @staticmethod
    def _should_retry_status(status_code: int) -> bool:
        return status_code == 429 or 500 <= status_code < 600

    @staticmethod
    def _backoff(attempt: int) -> float:
        return RETRY_BASE_SECONDS * (2**attempt) + random.uniform(0, 0.25)

    @staticmethod
    def _retry_after_seconds(value: str | None) -> float | None:
        if value is None:
            return None

        try:
            seconds = float(value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
            except (TypeError, ValueError, OverflowError):
                return None
        else:
            return max(0.0, seconds) if math.isfinite(seconds) else None

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())

    @staticmethod
    def _response_detail(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, str):
                return detail
        return None

    def meetings(
        self,
        *,
        year: int | None = None,
        meeting_key: int | str | None = None,
    ) -> list[dict[str, object]]:
        """List race meetings, optionally filtered by year or meeting key."""
        return self.get(
            "meetings",
            self._present(year=year, meeting_key=meeting_key),
        )

    def sessions(
        self,
        *,
        meeting_key: int | str | None = None,
        year: int | None = None,
    ) -> list[dict[str, object]]:
        """List sessions, optionally filtered by meeting or year."""
        return self.get(
            "sessions",
            self._present(meeting_key=meeting_key, year=year),
        )

    def drivers(
        self,
        session_key: int | str,
        *,
        driver_number: int | None = None,
    ) -> list[dict[str, object]]:
        """List drivers in a session, optionally filtered by driver number."""
        return self.get(
            "drivers",
            self._present(session_key=session_key, driver_number=driver_number),
        )

    def laps(
        self,
        session_key: int | str,
        *,
        driver_number: int | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> list[dict[str, object]]:
        """List session laps, optionally limited by driver or time range."""
        return self.get(
            "laps",
            self._present(
                session_key=session_key,
                driver_number=driver_number,
                date_start=date_start,
                date_end=date_end,
            ),
        )

    def car_data(
        self,
        session_key: int | str,
        *,
        driver_number: int | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> list[dict[str, object]]:
        """List car telemetry, optionally limited by driver or time range."""
        return self.get(
            "car_data",
            self._present(
                session_key=session_key,
                driver_number=driver_number,
                date_start=date_start,
                date_end=date_end,
            ),
        )

    def weather(
        self,
        session_key: int | str,
        *,
        date_start: str | None = None,
        date_end: str | None = None,
    ) -> list[dict[str, object]]:
        """List session weather records, optionally limited by time range."""
        return self.get(
            "weather",
            self._present(
                session_key=session_key,
                date_start=date_start,
                date_end=date_end,
            ),
        )

    @staticmethod
    def _present(**values: QueryValue | None) -> dict[str, QueryValue]:
        return {key: value for key, value in values.items() if value is not None}
