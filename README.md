# F1

Cliente Python para consultar dados históricos da [API OpenF1](https://openf1.org/).
O pacote oferece consultas a etapas, sessões, pilotos, voltas, telemetria e clima.
O acesso a dados em tempo real não faz parte deste MVP.

## Requisitos

- Python 3.13 ou superior
- [pyenv](https://github.com/pyenv/pyenv) (pyenv-win no Windows)
- [Poetry](https://python-poetry.org/)

## Configuração

O projeto fixa Python 3.13.7 em `.python-version`. Em uma máquina nova, instale
essa versão pelo pyenv e selecione o interpretador no ambiente Poetry.

### Windows (PowerShell)

```powershell
pyenv install 3.13.7
pyenv local 3.13.7
poetry env use (pyenv which python)
poetry install
```

### Unix (bash/zsh)

```bash
pyenv install 3.13.7
pyenv local 3.13.7
poetry env use "$(pyenv which python)"
poetry install
```

## Uso

### Dashboard

Para pesquisar as cinco voltas mais rápidas de cada circuito na temporada:

```powershell
poetry run streamlit run src/f1/dashboard.py
```

O dashboard oferece três filtros: **ano**, **tipo de sessão** e **circuito**.
O tipo de sessão começa em `Race`; é necessário selecionar um circuito. O ranking
agrega as sessões do tipo escolhido nesse circuito, exibe até cinco voltas e
indica etapa e sessão de origem. O piloto é identificado pelo número retornado
em `/laps`. Voltas sem `lap_duration` numérica, finita e positiva ou marcadas
`is_pit_out_lap` são excluídas. Um gráfico de barras compara o melhor tempo
válido de cada piloto nas sessões selecionadas. As consultas usam `/meetings`,
`/sessions` e `/laps`.

O plano comunitário disponibiliza dados históricos desde 2023 sem autenticação,
com limite de até três solicitações por segundo e 30 por minuto. O cliente
respeita esses limites. Selecionar um único circuito reduz o número de chamadas;
o progresso pode demorar conforme a quantidade de sessões e a cota disponível.
Respostas 429 e erros 5xx, timeout e conexão têm novas tentativas limitadas;
para 429, o cliente respeita `Retry-After` e
não espera automaticamente mais de 30 segundos. Respostas válidas sem registros
são tratadas como ausência de dados. HTTP 401/403 mostra o motivo técnico
retornado pela API, sem presumir que seja necessário contratar um plano.

### Biblioteca Python

```python
from f1 import OpenF1Client

with OpenF1Client() as client:
    meetings = client.meetings(year=2023)
    if meetings:
        meeting_key = meetings[0]["meeting_key"]
        sessions = client.sessions(meeting_key=meeting_key)
        if sessions:
            session_key = sessions[0]["session_key"]
            drivers = client.drivers(session_key=session_key)
            laps = client.laps(session_key=session_key, driver_number=1)
            telemetry = client.car_data(
                session_key=session_key,
                driver_number=1,
                date_start="2023-09-03T13:00:00+00:00",
                date_end="2023-09-03T13:10:00+00:00",
            )
            weather = client.weather(session_key=session_key)
```

Os métodos retornam uma lista de registros JSON (dicionários). `get()` também
permite consultar um recurso diretamente e passar filtros aceitos pela API:

```python
telemetry = client.get(
    "car_data",
    params={"session_key": session_key, "driver_number": 1, "speed>=": 300},
)
```

Identificadores como `meeting_key` e `session_key` podem ser obtidos pelas
consultas `meetings()` e `sessions()`. Restrinja telemetria e outros endpoints
volumosos por sessão, piloto ou período. O timeout padrão é de 10 segundos e
pode ser alterado ao criar o cliente, por exemplo `OpenF1Client(timeout=20)`.

Falhas de rede e respostas HTTP não exitosas levantam `OpenF1RequestError`;
JSON inválido ou com formato inesperado levanta `OpenF1ResponseError`. Ambas
herdam de `OpenF1Error`. O cliente pode ser fechado explicitamente com
`close()` ou usado como context manager, como nos exemplos.

## Desenvolvimento

```powershell
poetry run task test
poetry run task lint
poetry run task format
poetry run task docs
```

`test` mede a cobertura de `f1` e falha se ficar abaixo de 50%; os testes usam
transporte HTTP simulado e não dependem da API. `lint` executa Ruff,
`format` aplica sua formatação e `docs` valida o site MkDocs em modo estrito.

### Pre-commit

Instale o [pre-commit](https://pre-commit.com/) e habilite os hooks locais:

```powershell
pipx install pre-commit
pre-commit install
```

Os hooks executam Ruff para corrigir problemas de lint e formatar arquivos Python
antes de cada commit. Para executá-los manualmente em todos os arquivos:

```powershell
pre-commit run --all-files
```

## Integração contínua

O GitHub Actions executa testes, lint e build estrito da documentação em pushes,
pull requests e também pode ser acionado manualmente. A pipeline usa Python
3.13.7 e instala as dependências do grupo `dev` com Poetry.
