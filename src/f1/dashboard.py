"""Streamlit dashboard for the five fastest race laps at each circuit."""

import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from urllib.parse import urlencode

import streamlit as st

from f1 import OpenF1Client, OpenF1Error, OpenF1RequestError, OpenF1ResponseError

Record = dict[str, object]


@st.cache_data(ttl=3600)
def get_meetings(year: int) -> list[Record]:
    """Fetch and cache race meetings for a season."""
    with OpenF1Client() as client:
        return client.meetings(year=year)


@st.cache_data(ttl=3600)
def get_season_sessions(year: int) -> list[Record]:
    """Fetch and cache all sessions for a season."""
    with OpenF1Client() as client:
        return client.sessions(year=year)


@st.cache_data(ttl=3600)
def get_laps(session_key: int) -> list[Record]:
    """Fetch and cache lap records for a session."""
    with OpenF1Client() as client:
        return client.laps(session_key=session_key)


@st.cache_data(ttl=3600)
def sessions_for_type(
    sessions: Sequence[Record],
    session_type: str | None,
) -> list[Record]:
    """Select sessions matching a type, or all types when not specified."""
    return [
        session
        for session in sessions
        if (session_type is None or session.get("session_type") == session_type)
        and isinstance(session.get("session_key"), int)
        and isinstance(session.get("meeting_key"), int)
    ]


def filter_sessions(
    sessions: Sequence[Record],
    session_type: str | None,
    meeting_keys: set[int] | None,
) -> list[Record]:
    """Apply the selected session type and circuit filters."""
    return [
        session
        for session in sessions_for_type(sessions, session_type)
        if meeting_keys is None or session["meeting_key"] in meeting_keys
    ]


def format_lap_time(seconds: float) -> str:
    """Format a lap duration in seconds as minutes and milliseconds."""
    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{int(minutes)}:{remaining_seconds:06.3f}"


def fastest_laps(
    laps: Sequence[Record],
    drivers: Sequence[Record],
    limit: int = 5,
) -> list[Record]:
    """Return the fastest valid laps, enriched with driver names."""
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    driver_names = {
        str(driver["driver_number"]): _driver_name(driver)
        for driver in drivers
        if driver.get("driver_number") is not None
    }

    valid_laps = [lap for lap in laps if _is_valid_lap(lap)]
    valid_laps.sort(key=lambda lap: lap["lap_duration"])

    results: list[Record] = []
    for position, lap in enumerate(valid_laps[:limit], start=1):
        driver_number = lap.get("driver_number")
        duration = lap["lap_duration"]
        results.append(
            {
                "Posição": position,
                "Piloto": driver_names.get(
                    str(driver_number),
                    f"Piloto {driver_number}" if driver_number is not None else "N/D",
                ),
                "Número": driver_number if driver_number is not None else "N/D",
                "Volta": lap.get("lap_number", "N/D"),
                "Tempo": format_lap_time(float(duration)),
                "Etapa": lap.get("_meeting_name", "N/D"),
                "Sessão": lap.get("_session_name", "N/D"),
            }
        )

    return results


def fastest_lap_times_by_driver(
    laps_by_session: dict[int, Sequence[Record]],
) -> list[Record]:
    """Return each driver's fastest valid lap across the selected sessions."""
    fastest_by_driver: dict[str, float] = {}
    for laps in laps_by_session.values():
        for lap in laps:
            driver_number = lap.get("driver_number")
            if driver_number is None or not _is_valid_lap(lap):
                continue

            key = str(driver_number)
            duration = float(lap["lap_duration"])
            if key not in fastest_by_driver or duration < fastest_by_driver[key]:
                fastest_by_driver[key] = duration

    return [
        {"Piloto": f"Piloto {driver_number}", "Tempo (s)": duration}
        for driver_number, duration in sorted(
            fastest_by_driver.items(),
            key=lambda item: (item[1], item[0]),
        )
    ]


def fastest_laps_by_circuit(
    meetings: Sequence[Record],
    sessions: Sequence[Record],
    laps_by_session: dict[int, Sequence[Record]],
    drivers_by_session: dict[int, Sequence[Record]],
    session_type: str | None = None,
    limit: int = 5,
) -> list[Record]:
    """Build one top-lap ranking per circuit across the season's race sessions."""
    meeting_by_key = {
        meeting["meeting_key"]: meeting
        for meeting in meetings
        if isinstance(meeting.get("meeting_key"), int)
    }

    circuit_laps: dict[str, list[Record]] = defaultdict(list)
    circuit_drivers: dict[str, dict[str, Record]] = defaultdict(dict)
    circuit_names: dict[str, str] = {}
    seen_sessions: set[int] = set()
    seen_laps: set[tuple[int, str, str]] = set()
    for session in sessions_for_type(sessions, session_type):
        session_key = session["session_key"]
        if session_key in seen_sessions:
            continue
        seen_sessions.add(session_key)

        meeting = meeting_by_key.get(session["meeting_key"])
        if meeting is None:
            continue

        circuit = meeting.get("circuit_short_name")
        circuit_key = meeting.get("circuit_key")
        if circuit_key is not None:
            key = f"key:{circuit_key}"
        elif isinstance(circuit, str):
            key = f"name:{circuit.casefold()}"
        else:
            key = f"meeting:{session['meeting_key']}"
        circuit_names[key] = (
            str(circuit) if isinstance(circuit, str) else "Circuito desconhecido"
        )
        meeting_name = meeting.get("meeting_name", "Grande Prêmio")
        session_name = session.get("session_name", "Sessão")
        for lap in laps_by_session.get(session_key, []):
            if not _is_valid_lap(lap):
                continue
            driver_number = lap.get("driver_number")
            lap_number = lap.get("lap_number")
            if driver_number is not None and lap_number is not None:
                lap_identity = (session_key, str(driver_number), str(lap_number))
                if lap_identity in seen_laps:
                    continue
                seen_laps.add(lap_identity)
            circuit_laps[key].append(
                {
                    **lap,
                    "_meeting_name": meeting_name,
                    "_session_name": session_name,
                }
            )

        for driver in drivers_by_session.get(session_key, []):
            driver_number = driver.get("driver_number")
            if driver_number is not None:
                circuit_drivers[key][str(driver_number)] = driver

    rows = [
        {
            "Circuito": circuit_names[key],
            **lap,
        }
        for key, laps in circuit_laps.items()
        for lap in fastest_laps(
            laps,
            list(circuit_drivers[key].values()),
            limit=limit,
        )
    ]
    return sorted(rows, key=lambda row: (str(row["Circuito"]), int(row["Posição"])))


def describe_openf1_error(error: OpenF1Error) -> str:
    """Return an actionable message based on the observed API failure."""
    if isinstance(error, OpenF1ResponseError):
        if "invalid JSON" in str(error):
            return "A OpenF1 respondeu com JSON inválido."
        return "A resposta da OpenF1 veio em um formato inesperado."

    if not isinstance(error, OpenF1RequestError):
        return f"Não foi possível consultar a OpenF1: {error}"

    status = error.status_code
    detail = (error.api_detail or "").lower()
    if status == 400:
        return "A API recusou a consulta; verifique os parâmetros enviados."
    if status == 401 and "live f1 session in progress" in detail:
        return (
            "A OpenF1 informou que o acesso global, inclusive a sessões passadas, "
            "está restrito durante uma sessão ao vivo. O detalhe retornado pela "
            "API confirma essa condição; tente novamente após a sessão terminar."
        )
    if status in (401, 403):
        return (
            "A OpenF1 recusou esta solicitação (HTTP "
            f"{status}); consulte os detalhes técnicos da resposta."
        )
    if status == 404:
        return (
            "O endpoint ou os dados desta consulta não foram encontrados. "
            "Verifique a temporada e os identificadores da sessão."
        )
    if status == 429:
        if error.retry_after is not None:
            return (
                "A OpenF1 limitou temporariamente as requisições. Aguarde "
                f"{error.retry_after:g} segundos antes de tentar novamente."
            )
        return (
            "A OpenF1 limitou temporariamente as requisições. Aguarde antes "
            "de tentar novamente."
        )
    if status is not None and 500 <= status < 600:
        return (
            f"A OpenF1 está temporariamente indisponível (HTTP {status}). "
            "Tente novamente mais tarde."
        )
    if error.cause_type and error.cause_type.endswith("Timeout"):
        return "A consulta à OpenF1 excedeu o tempo limite após novas tentativas."
    if error.cause_type:
        return (
            "Não foi possível conectar à OpenF1 após novas tentativas "
            f"({error.cause_type}). Verifique a conexão."
        )
    return f"Falha ao consultar a OpenF1: {error}"


def should_continue_after_race_error(error: OpenF1Error) -> bool:
    """Continue past a missing or malformed race response, not global failures."""
    return isinstance(error, OpenF1ResponseError) or (
        isinstance(error, OpenF1RequestError) and error.status_code == 404
    )


def show_openf1_error(error: OpenF1Error) -> None:
    """Display a user-facing error and its request diagnostics."""
    st.error(describe_openf1_error(error))
    with st.expander("Detalhes técnicos"):
        st.code(str(error))
        if isinstance(error, OpenF1RequestError):
            st.write(f"Endpoint: `GET /{error.endpoint}`")
            if error.params:
                st.write(f"Parâmetros: `{urlencode(error.params)}`")
            if error.status_code is not None:
                st.write(f"HTTP: `{error.status_code}`")
            if error.api_detail:
                st.write(f"Detalhe da API: {error.api_detail}")
            if error.cause_type:
                st.write(f"Exceção: `{error.cause_type}`")


def _is_valid_lap(lap: Record) -> bool:
    duration = lap.get("lap_duration")
    return (
        isinstance(duration, (int, float))
        and not isinstance(duration, bool)
        and math.isfinite(duration)
        and duration > 0
        and lap.get("is_pit_out_lap") is not True
    )


def _driver_name(driver: Record) -> str:
    for field in ("full_name", "broadcast_name", "name_acronym"):
        name = driver.get(field)
        if isinstance(name, str) and name:
            return name
    return f"Piloto {driver['driver_number']}"


def _circuit_identity(meeting: Record) -> str:
    circuit_key = meeting.get("circuit_key")
    if circuit_key is not None:
        return f"key:{circuit_key}"
    circuit_name = meeting.get("circuit_short_name")
    if isinstance(circuit_name, str):
        return f"name:{circuit_name.casefold()}"
    return f"meeting:{meeting.get('meeting_key')}"


def _circuit_label(meeting: Record) -> str:
    circuit = meeting.get("circuit_short_name", "Circuito desconhecido")
    return str(circuit)


def main() -> None:
    st.set_page_config(
        page_title="F1 — Voltas mais rápidas por circuito", page_icon="🏎️"
    )
    st.title("🏎️ Cinco voltas mais rápidas por circuito")
    st.caption(
        "Veja, para cada circuito da temporada, as cinco voltas válidas mais "
        "rápidas do tipo de sessão selecionado."
    )

    year = st.selectbox(
        "Temporada",
        options=list(range(date.today().year, 2022, -1)),
    )

    try:
        meetings = get_meetings(year)
        sessions = get_season_sessions(year)
    except OpenF1Error as exc:
        show_openf1_error(exc)
        st.stop()

    if not meetings:
        st.info(f"Nenhuma etapa encontrada para a temporada {year}.")
        st.stop()

    available_types = sorted(
        {
            session_type
            for session in sessions
            if isinstance((session_type := session.get("session_type")), str)
        }
    )
    if not available_types:
        st.info(f"Nenhum tipo de sessão encontrado para {year}.")
        st.stop()

    session_type_options = ["Todos os tipos", *available_types]
    default_session_type = (
        session_type_options.index("Race") if "Race" in available_types else 0
    )
    selected_session_type = st.selectbox(
        "Tipo de sessão",
        options=session_type_options,
        index=default_session_type,
    )
    session_type_filter = (
        None if selected_session_type == "Todos os tipos" else selected_session_type
    )

    circuit_meetings: dict[str, list[Record]] = defaultdict(list)
    for meeting in meetings:
        circuit_meetings[_circuit_identity(meeting)].append(meeting)
    circuit_labels = {
        key: " / ".join(
            dict.fromkeys(_circuit_label(meeting) for meeting in matching_meetings)
        )
        for key, matching_meetings in circuit_meetings.items()
    }
    circuit_options = sorted(circuit_labels)
    if not circuit_options:
        st.info(f"Nenhum circuito encontrado para {year}.")
        st.stop()

    selected_circuit = st.selectbox(
        "Circuito",
        options=circuit_options,
        format_func=lambda value: circuit_labels[value],
    )
    selected_meeting_keys = {
        meeting["meeting_key"]
        for meeting in circuit_meetings[selected_circuit]
        if isinstance(meeting.get("meeting_key"), int)
    }
    selected_sessions = filter_sessions(
        sessions,
        session_type_filter,
        selected_meeting_keys,
    )
    if not selected_sessions:
        st.info("Nenhuma sessão corresponde aos filtros selecionados.")
        st.stop()

    laps_by_session: dict[int, Sequence[Record]] = {}
    meeting_labels = {
        meeting["meeting_key"]: _circuit_label(meeting)
        for meeting in meetings
        if isinstance(meeting.get("meeting_key"), int)
    }
    session_errors: list[str] = []
    progress = st.progress(0, text="Carregando voltas...")
    for index, session in enumerate(selected_sessions, start=1):
        session_key = session["session_key"]
        try:
            laps_by_session[session_key] = get_laps(session_key)
        except OpenF1Error as exc:
            meeting_label = meeting_labels.get(
                session["meeting_key"],
                "etapa desconhecida",
            )
            if should_continue_after_race_error(exc):
                session_errors.append(f"{meeting_label}: {describe_openf1_error(exc)}")
            else:
                show_openf1_error(exc)
                st.stop()
        progress.progress(
            index / len(selected_sessions),
            text=f"Carregando sessão {index} de {len(selected_sessions)}...",
        )
    progress.empty()
    for session_error in session_errors:
        st.warning(session_error)

    ranking = fastest_laps_by_circuit(
        meetings,
        selected_sessions,
        laps_by_session,
        {},
        session_type=session_type_filter,
    )
    if not ranking:
        st.info("Nenhuma volta encontrada para os filtros selecionados.")
        st.stop()

    st.subheader(f"Top 5 voltas mais rápidas por circuito — {year}")
    st.dataframe(ranking, hide_index=True, width="stretch")
    chart_data = fastest_lap_times_by_driver(laps_by_session)
    if chart_data:
        st.subheader("Melhor tempo por piloto")
        st.bar_chart(
            chart_data,
            x="Tempo (s)",
            y="Piloto",
            horizontal=True,
        )
    st.caption(
        "O ranking combina as sessões selecionadas do mesmo circuito. "
        "O gráfico compara o melhor tempo válido de cada piloto nas sessões "
        "selecionadas. Voltas sem tempo válido e voltas de saída dos boxes são "
        "desconsideradas. "
        "O limite é de 3 solicitações por segundo e 30 por minuto; a aplicação "
        "aguarda automaticamente para respeitar a cota."
    )


if __name__ == "__main__":
    main()
