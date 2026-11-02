# OpenF1 API — guia resumido

Resumo dos principais recursos da [documentação oficial da OpenF1](https://openf1.org/docs/#api-endpoints). Para parâmetros e atributos completos, consulte a documentação original.

## Visão geral

- API HTTP para dados de Fórmula 1: telemetria, tempos, pilotos, sessões, resultados e condições de pista.
- Base URL: `https://api.openf1.org/v1`
- Consultas por `GET`; a resposta padrão é JSON.
- Dados históricos a partir de 2023 são gratuitos e não exigem autenticação. O acesso em tempo real requer assinatura.
- Os registros incluem identificadores de sessão/etapa e, quando aplicável, data e hora em UTC.

## Principais endpoints

| Endpoint | Dados fornecidos |
| --- | --- |
| `/car_data` | Telemetria dos carros: velocidade, RPM, marcha, acelerador, freio e DRS. Amostragem aproximada de 3,7 Hz. |
| `/championship_drivers` | Classificação do campeonato de pilotos (beta; sessões de corrida). |
| `/championship_teams` | Classificação do campeonato de equipes (beta; sessões de corrida). |
| `/drivers` | Informações dos pilotos da sessão, como nome, número e equipe. |
| `/intervals` | Intervalos entre pilotos e diferença para o líder. |
| `/laps` | Voltas, tempos, setores e dados relacionados aos pneus. |
| `/location` | Localização dos carros ao longo da sessão. |
| `/meetings` | Etapas do calendário, circuitos, países e datas. |
| `/overtakes` | Ultrapassagens e posições dos pilotos envolvidos. |
| `/pit` | Paradas nos boxes e durações. |
| `/position` | Posições dos pilotos ao longo da sessão. |
| `/race_control` | Mensagens da direção de prova, bandeiras e incidentes. |
| `/sessions` | Sessões de cada etapa, com tipo, horários e identificadores. |
| `/session_result` | Resultado da sessão, posições e status dos pilotos. |
| `/starting_grid` | Posições de largada. |
| `/stints` | Stints, compostos de pneus e voltas realizadas. |
| `/team_radio` | Mensagens de rádio e links para áudio. |
| `/weather` | Temperatura, umidade, pressão, chuva e vento. |

## Identificadores e filtros

Os parâmetros são enviados na query string. As chaves mais usadas são:

- `meeting_key`: identifica uma etapa/evento.
- `session_key`: identifica uma sessão, como treino, classificação ou corrida.
- `driver_number`: número do piloto.
- `date`: data/hora do registro, geralmente em UTC no formato ISO 8601.

Use `latest` em `meeting_key` ou `session_key` para referenciar a etapa ou sessão mais recente/atual. Consulte primeiro `/meetings` e `/sessions` para descobrir os identificadores necessários às demais consultas.

É possível filtrar por atributos dos registros, exceto campos do tipo array. Comparações como `>=`, `<=`, `<` e `>` permitem restringir valores. Para períodos, use filtros como `date_start` e `date_end`; prefira datas ISO 8601 para evitar ambiguidades.

```text
https://api.openf1.org/v1/sessions?year=2023
https://api.openf1.org/v1/drivers?session_key=9158&driver_number=1
https://api.openf1.org/v1/car_data?session_key=9159&driver_number=55&speed>=315
https://api.openf1.org/v1/sessions?date_start>=2023-09-01&date_end<=2023-09-30
```

## Formatos de resposta

JSON é o formato padrão. Para receber CSV, acrescente `csv=true`:

```text
https://api.openf1.org/v1/sessions?year=2023&csv=true
```

## Exemplo com cURL

```bash
curl "https://api.openf1.org/v1/drivers?session_key=9158&driver_number=1"
```

## Recomendações de uso

- Restrinja as consultas por sessão, etapa, piloto ou período para evitar respostas desnecessariamente grandes.
- Trate a resposta como uma coleção de registros e valide campos que possam estar ausentes ou nulos.
- Dados em tempo real podem exigir assinatura; consulte a [documentação de autenticação e streaming](https://openf1.org/auth.html).
- Consulte a documentação oficial para os esquemas e atributos atualizados de cada endpoint.
