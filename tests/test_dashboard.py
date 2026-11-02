import pytest

from f1 import OpenF1RequestError, OpenF1ResponseError
from f1.dashboard import (
    describe_openf1_error,
    fastest_lap_times_by_driver,
    fastest_laps,
    fastest_laps_by_circuit,
    filter_sessions,
    format_lap_time,
    sessions_for_type,
    should_continue_after_race_error,
)


def test_fastest_laps_returns_top_five_with_driver_names() -> None:
    laps = [
        {
            "driver_number": number,
            "lap_number": number,
            "lap_duration": duration,
        }
        for number, duration in [
            (1, 90.5),
            (2, 88.25),
            (3, 92.1),
            (4, 87.8),
            (5, 89.0),
            (6, 91),
        ]
    ]
    drivers = [
        {"driver_number": number, "full_name": f"Driver {number}"}
        for number in range(1, 7)
    ]

    result = fastest_laps(laps, drivers)

    assert [row["Número"] for row in result] == [4, 2, 5, 1, 6]
    assert [row["Posição"] for row in result] == [1, 2, 3, 4, 5]
    assert result[0]["Piloto"] == "Driver 4"
    assert result[0]["Tempo"] == "1:27.800"


def test_fastest_laps_ignores_invalid_and_pit_exit_laps() -> None:
    laps = [
        {"driver_number": 1, "lap_number": 1, "lap_duration": None},
        {"driver_number": 2, "lap_number": 2, "lap_duration": 0},
        {"driver_number": 3, "lap_number": 3, "lap_duration": float("inf")},
        {
            "driver_number": 4,
            "lap_number": 4,
            "lap_duration": 80.0,
            "is_pit_out_lap": True,
        },
        {"driver_number": 5, "lap_number": 5, "lap_duration": 81.25},
    ]

    result = fastest_laps(laps, [])

    assert len(result) == 1
    assert result[0]["Piloto"] == "Piloto 5"
    assert result[0]["Tempo"] == "1:21.250"


def test_fastest_laps_uses_name_fallbacks_and_custom_limit() -> None:
    laps = [
        {"driver_number": 44, "lap_number": 10, "lap_duration": 65.0},
        {"driver_number": 16, "lap_number": 11, "lap_duration": 66.0},
    ]
    drivers = [
        {"driver_number": 44, "broadcast_name": "LEWIS HAMILTON"},
        {"driver_number": 16, "name_acronym": "LEC"},
    ]

    result = fastest_laps(laps, drivers, limit=1)

    assert len(result) == 1
    assert result[0]["Piloto"] == "LEWIS HAMILTON"


def test_fastest_lap_times_by_driver_returns_fastest_valid_time() -> None:
    laps_by_session = {
        101: [
            {"driver_number": 44, "lap_duration": 91.0},
            {"driver_number": 16, "lap_duration": 90.0},
            {"driver_number": 44, "lap_duration": 89.5},
            {"driver_number": 1, "lap_duration": None},
        ],
        102: [
            {"driver_number": 44, "lap_duration": 90.0},
            {"driver_number": 16, "lap_duration": 88.0, "is_pit_out_lap": True},
            {"driver_number": 16, "lap_duration": 90.0},
            {"lap_duration": 80.0},
        ],
    }

    assert fastest_lap_times_by_driver(laps_by_session) == [
        {"Piloto": "Piloto 44", "Tempo (s)": 89.5},
        {"Piloto": "Piloto 16", "Tempo (s)": 90.0},
    ]


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0.0, "0:00.000"), (83.456, "1:23.456"), (3600.0, "60:00.000")],
)
def test_format_lap_time(seconds: float, expected: str) -> None:
    assert format_lap_time(seconds) == expected


def test_fastest_laps_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        fastest_laps([], [], limit=0)


def test_session_type_filter_selects_requested_type_and_valid_keys() -> None:
    sessions = [
        {
            "session_name": "Race",
            "session_type": "Race",
            "session_key": 10,
            "meeting_key": 1,
        },
        {
            "session_name": "Sprint",
            "session_type": "Sprint",
            "session_key": 11,
            "meeting_key": 1,
        },
        {
            "session_name": "Race",
            "session_type": "Race",
            "session_key": "12",
            "meeting_key": 2,
        },
    ]

    assert sessions_for_type(sessions, "Race") == [sessions[0]]
    assert sessions_for_type(sessions, None) == sessions[:2]


def test_filters_can_limit_session_type_and_circuit() -> None:
    sessions = [
        {
            "session_type": "Race",
            "session_key": 10,
            "meeting_key": 1,
        },
        {
            "session_type": "Race",
            "session_key": 20,
            "meeting_key": 2,
        },
        {
            "session_type": "Practice",
            "session_key": 11,
            "meeting_key": 1,
        },
    ]

    assert filter_sessions(sessions, "Race", {2}) == [sessions[1]]
    assert filter_sessions(sessions, None, None) == sessions


def test_fastest_laps_by_circuit_ranks_each_circuit() -> None:
    meetings = [
        {
            "meeting_key": 1,
            "meeting_name": "Grand Prix Alpha",
            "circuit_short_name": "Alpha",
        },
        {
            "meeting_key": 2,
            "meeting_name": "Grand Prix Beta",
            "circuit_short_name": "Beta",
        },
    ]
    sessions = [
        {
            "session_name": "Race",
            "session_type": "Race",
            "session_key": 101,
            "meeting_key": 1,
        },
        {
            "session_name": "Sprint",
            "session_type": "Sprint",
            "session_key": 102,
            "meeting_key": 1,
        },
        {
            "session_name": "Race",
            "session_type": "Race",
            "session_key": 201,
            "meeting_key": 2,
        },
    ]
    laps_by_session = {
        101: [
            {"driver_number": 1, "lap_number": lap, "lap_duration": duration}
            for lap, duration in [(1, 91.0), (2, 89.0), (3, 90.0)]
        ],
        201: [
            {"driver_number": 2, "lap_number": lap, "lap_duration": duration}
            for lap, duration in [(1, 88.0), (2, 87.0)]
        ],
    }

    ranking = fastest_laps_by_circuit(
        meetings,
        sessions,
        laps_by_session,
        {},
        session_type="Race",
        limit=2,
    )

    assert [(row["Circuito"], row["Posição"]) for row in ranking] == [
        ("Alpha", 1),
        ("Alpha", 2),
        ("Beta", 1),
        ("Beta", 2),
    ]
    assert [row["Tempo"] for row in ranking] == [
        "1:29.000",
        "1:30.000",
        "1:27.000",
        "1:28.000",
    ]


def test_same_circuit_aggregates_races_and_returns_at_most_five() -> None:
    meetings = [
        {
            "meeting_key": 1,
            "meeting_name": "Grand Prix Alpha",
            "circuit_key": 10,
            "circuit_short_name": "Alpha",
        },
        {
            "meeting_key": 2,
            "meeting_name": "Grand Prix Beta",
            "circuit_key": 10,
            "circuit_short_name": "Alpha",
        },
    ]
    sessions = [
        {
            "session_name": "Race",
            "session_type": "Race",
            "session_key": 101,
            "meeting_key": 1,
        },
        {
            "session_name": "Race",
            "session_type": "Race",
            "session_key": 201,
            "meeting_key": 2,
        },
    ]
    laps_by_session = {
        101: [
            {"driver_number": 1, "lap_number": lap, "lap_duration": 90 + lap}
            for lap in range(1, 5)
        ]
        + [
            {"driver_number": 1, "lap_number": 1, "lap_duration": 91},
            {
                "driver_number": 3,
                "lap_number": 9,
                "lap_duration": 60,
                "is_pit_out_lap": True,
            },
        ],
        201: [
            {"driver_number": 2, "lap_number": lap, "lap_duration": 80 + lap}
            for lap in range(1, 5)
        ],
    }

    ranking = fastest_laps_by_circuit(
        meetings,
        sessions,
        laps_by_session,
        {},
        session_type="Race",
    )

    assert len(ranking) == 5
    assert {row["Circuito"] for row in ranking} == {"Alpha"}
    assert [row["Tempo"] for row in ranking] == [
        "1:21.000",
        "1:22.000",
        "1:23.000",
        "1:24.000",
        "1:31.000",
    ]


def test_circuit_with_empty_lap_records_does_not_create_rank_rows() -> None:
    meetings = [
        {
            "meeting_key": 1,
            "meeting_name": "Grand Prix Alpha",
            "circuit_short_name": "Alpha",
        }
    ]
    sessions = [{"session_name": "Race", "session_key": 101, "meeting_key": 1}]

    assert (
        fastest_laps_by_circuit(
            meetings,
            sessions,
            {101: []},
            {},
            session_type="Race",
        )
        == []
    )


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (400, "verifique os parâmetros"),
        (401, "recusou esta solicitação"),
        (403, "recusou esta solicitação"),
        (404, "não foram encontrados"),
        (500, "temporariamente indisponível"),
        (503, "temporariamente indisponível"),
    ],
)
def test_http_errors_have_status_specific_messages(
    status_code: int,
    expected: str,
) -> None:
    error = OpenF1RequestError(
        f"HTTP {status_code}",
        endpoint="meetings",
        params={"year": 2023},
        status_code=status_code,
    )

    assert expected in describe_openf1_error(error)


def test_live_session_message_depends_on_actual_api_detail() -> None:
    error = OpenF1RequestError(
        "HTTP 401",
        endpoint="meetings",
        params={"year": 2023},
        status_code=401,
        api_detail="Live F1 session in progress",
    )

    assert "informou que o acesso global" in describe_openf1_error(error)


def test_unknown_unauthorized_error_does_not_claim_live_session_or_payment() -> None:
    error = OpenF1RequestError(
        "HTTP 401",
        endpoint="meetings",
        params={"year": 2023},
        status_code=401,
        api_detail="Unauthorized",
    )

    message = describe_openf1_error(error)
    assert "recusou esta solicitação" in message
    assert "ao vivo" not in message
    assert "pagar" not in message


def test_retry_after_message_includes_wait_time() -> None:
    error = OpenF1RequestError(
        "HTTP 429",
        endpoint="meetings",
        params={},
        status_code=429,
        retry_after=12,
    )

    assert "12 segundos" in describe_openf1_error(error)


def test_only_session_specific_not_found_or_bad_response_is_skipped() -> None:
    missing_session = OpenF1RequestError(
        "HTTP 404",
        endpoint="laps",
        params={"session_key": 1},
        status_code=404,
    )
    invalid_payload = OpenF1ResponseError("invalid JSON")
    rate_limited = OpenF1RequestError(
        "HTTP 429",
        endpoint="laps",
        params={"session_key": 1},
        status_code=429,
    )

    assert should_continue_after_race_error(missing_session)
    assert should_continue_after_race_error(invalid_payload)
    assert not should_continue_after_race_error(rate_limited)
