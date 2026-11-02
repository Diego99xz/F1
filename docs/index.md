# F1

Cliente Python para consultar dados históricos da [API OpenF1](https://openf1.org/).
O pacote oferece consultas a etapas, sessões, pilotos, voltas, telemetria e clima.
Dados em tempo real não fazem parte do escopo atual.

## Configuração

O projeto requer Python 3.13 ou superior e usa pyenv para selecionar a versão
local e Poetry para dependências e ambiente virtual.

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

## Dashboard

Inicie a interface web local com:

```powershell
poetry run streamlit run src/f1/dashboard.py
```

O dashboard tem três filtros: ano, tipo de sessão e circuito. O tipo de sessão
começa em `Race`; é necessário selecionar um circuito. O ranking agrega as
sessões do tipo escolhido nesse circuito e mostra até cinco voltas, indicando a
etapa e a sessão de origem. O piloto é identificado pelo número fornecido em
`/laps`. Voltas de saída dos boxes e voltas sem `lap_duration` numérica, finita
e positiva são excluídas. Um gráfico de barras compara o melhor tempo válido de
cada piloto nas sessões selecionadas.

O plano comunitário fornece dados históricos desde 2023 sem autenticação, com
limite de três solicitações por segundo e 30 por minuto. O cliente aplica
limitação global de chamadas. A consulta do circuito selecionado pode demorar
conforme a quantidade de sessões e a cota disponível.

O dashboard diferencia erros HTTP, conexão, timeout e respostas inválidas.
Uma restrição de sessão ao vivo só é indicada quando a API retorna esse motivo.
Respostas 429 e erros 5xx ou de conexão têm até duas novas tentativas; no HTTP
429, respeita-se `Retry-After` sem esperar automaticamente mais de 30 segundos.
Uma resposta válida vazia indica apenas ausência de registros. Erros 401/403
exibem o detalhe da API sem presumir que seja necessário contratar um plano.

## Uso como biblioteca

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
            weather = client.weather(session_key=session_key)
```

O cliente também oferece `car_data()` para telemetria e `get()` para consultar
outros recursos com parâmetros aceitos pela API. Restrinja consultas volumosas
por sessão, piloto ou período.

Falhas de rede e respostas HTTP não exitosas levantam `OpenF1RequestError`;
JSON inválido ou com formato inesperado levanta `OpenF1ResponseError`. Ambas
herdam de `OpenF1Error`.

## Tarefas de desenvolvimento

Execute os atalhos definidos no `pyproject.toml` com Poetry:

```powershell
poetry run task test
poetry run task lint
poetry run task format
poetry run task docs
```

`test` executa pytest com cobertura mínima de 50%; `lint` executa Ruff;
`format` aplica a formatação Ruff; `docs` compila o site MkDocs em modo estrito.
