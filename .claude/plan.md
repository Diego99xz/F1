# Plano de criação do projeto F1

## 1. Objetivo

Criar um projeto Python organizado e testável para consultar e trabalhar com dados históricos da API OpenF1. O projeto deve começar com uma integração pequena e confiável, permitindo ampliar os endpoints e os casos de uso conforme os requisitos da aplicação forem definidos.

Este plano combina os recursos descritos em [doc_api.md](./.claude/doc_api.md) com os padrões obrigatórios de [SKILL.md](./.claude/SKILL.md).

## 2. Escopo inicial e premissas

### Incluído no MVP

- Consumir a API REST `https://api.openf1.org/v1`.
- Consultar etapas (`meetings`) e sessões (`sessions`) como ponto de entrada para obter `meeting_key` e `session_key`.
- Consultar dados relacionados a uma sessão, começando por pilotos (`drivers`), voltas (`laps`), telemetria (`car_data`) e clima (`weather`).
- Permitir filtros por identificadores e parâmetros suportados pela API.
- Tratar respostas, erros de rede, timeouts e dados ausentes de forma explícita.
- Usar dados históricos, disponíveis sem autenticação segundo a documentação resumida.

### Fora do escopo inicial

- Acesso a dados em tempo real, que pode exigir assinatura.
- Interface web, dashboard ou aplicativo visual.
- Banco de dados, persistência permanente e agendamento de pipelines.
- Cobrir imediatamente todos os endpoints ou todos os atributos da API.

Esses itens devem ser adicionados somente após definição de requisitos e decisão técnica. O MVP não deve presumir qual visualização, armazenamento ou produto final será necessário.

## 3. Arquitetura proposta

Manter o layout `src/` e adaptar os módulos à necessidade real, sem criar camadas vazias:

```text
src/f1/
├── __init__.py
├── client.py          # chamadas HTTP e parâmetros da API
├── config.py          # configuração externa, somente se necessária
└── ...                # modelos ou serviços apenas quando agregarem valor
tests/
├── unit/
└── integration/       # opcional; usar apenas quando houver integração apropriada
```

Separar responsabilidades conforme o crescimento:

1. **Cliente OpenF1:** construir consultas e encapsular transporte HTTP.
2. **Validação/representação:** validar ou tipar dados somente onde isso agregar clareza; considerar campos opcionais e mudanças no esquema remoto.
3. **Lógica de domínio:** transformações e casos de uso independentes do transporte, se forem definidos.
4. **Execução:** oferecer uma forma clara de usar o pacote; definir CLI ou entry point apenas quando houver necessidade concreta.

Não acoplar regras de negócio a detalhes de HTTP. Não introduzir banco, framework, ORM ou biblioteca de dados antes de um requisito que justifique essa escolha.

## 4. Fases de implementação

### Fase 1 — Preparar a base

- Confirmar objetivo funcional do produto e casos de uso prioritários antes de ampliar o escopo.
- Revisar `pyproject.toml`, que já declara o pacote `f1` em `src/` e Python `>=3.13`.
- Confirmar versão compatível do Python, Poetry e o ambiente virtual utilizado.
- Definir dependências mínimas de runtime e desenvolvimento; adicionar somente pelo Poetry.
- Configurar Ruff, pytest e pytest-cov em `pyproject.toml`, preservando os metadados existentes.
- Criar/atualizar `poetry.lock` e `.python-version` quando apropriado ao ambiente e à estratégia do projeto.
- Configurar `.gitignore` para ambientes, caches e artefatos locais.

**Critério de saída:** projeto instalável pelo Poetry, pacote `f1` importável no ambiente do projeto e ferramentas configuradas sem dependências desnecessárias.

### Fase 2 — Implementar o cliente OpenF1

- Criar interface simples para consultas `GET` à base URL da API.
- Aceitar endpoint e parâmetros de consulta sem montar URLs manualmente em cada chamada.
- Codificar parâmetros corretamente, inclusive comparadores como `>=` e filtros de data.
- Definir timeout explícito e propagar erros de HTTP/rede com contexto útil; não retornar sucesso vazio quando ocorrer falha.
- Tratar JSON como formato padrão e deixar CSV fora da interface inicial, salvo necessidade confirmada.
- Não incluir autenticação no MVP histórico. Manter a configuração extensível sem armazenar credenciais no código.

**Critério de saída:** cliente pode consultar um endpoint com filtros e diferencia resposta válida de falhas de transporte ou resposta inválida.

### Fase 3 — Adicionar consultas prioritárias

Implementar funções pequenas e consistentes para:

1. Listar etapas usando `/meetings`.
2. Listar sessões por etapa/ano usando `/sessions`.
3. Consultar pilotos por sessão usando `/drivers`.
4. Consultar voltas da sessão ou de um piloto usando `/laps`.
5. Consultar telemetria de um piloto usando `/car_data`, com filtros de sessão e tempo quando necessários para limitar volume.
6. Consultar condições meteorológicas usando `/weather`.

Usar `/position`, `/race_control`, `/pit`, `/stints`, `/intervals` e demais endpoints apenas quando os casos de uso definidos justificarem sua inclusão. Para ranking ou resultado, considerar `/session_result` e os endpoints beta de campeonato de acordo com sua disponibilidade e limitações.

**Critério de saída:** chamadas prioritárias usam filtros por `session_key`, `meeting_key` ou `driver_number` adequados e retornam dados da OpenF1 sem embutir identificadores de exemplo como valores fixos de produção.

### Fase 4 — Testes e confiabilidade

- Criar testes unitários para construção de parâmetros, validação, transformações e tratamento de erros.
- Mockar chamadas HTTP em testes unitários; não depender da disponibilidade da API externa.
- Adicionar testes de integração separados e opcionais somente se houver estratégia estável, sem credenciais e com volume limitado.
- Cobrir respostas vazias, campos ausentes/nulos, JSON inválido, timeout, erro HTTP e parâmetros com caracteres especiais.
- Configurar `pytest-cov` para medir exclusivamente `src/f1/` e falhar abaixo de 50% de cobertura.
- Executar Ruff para lint, organização de imports e formatação.

**Critério de saída:** testes determinísticos passam; cobertura de produção é igual ou superior a 50%; Ruff não reporta problemas pendentes.

### Fase 5 — Uso e documentação

- Documentar instalação, configuração, consultas suportadas e exemplos de uso no README e na documentação técnica quando ela for criada.
- Manter [doc_api.md](./.claude/doc_api.md) como resumo da API de referência; não duplicar nele a documentação interna do cliente.
- Criar documentação MkDocs Material quando a documentação do projeto justificar o site, com página inicial e navegação simples.
- Explicar limitações do acesso histórico/tempo real, uso de identificadores e recomendação de restringir consultas para evitar respostas grandes.
- Validar a compilação com `poetry run mkdocs build --strict` quando MkDocs estiver configurado ou for parte da entrega.

**Critério de saída:** instruções reproduzíveis e exemplos compatíveis com o comportamento implementado; build de documentação passa quando aplicável.

### Fase 6 — Revisão e expansão

- Revisar diff, dependências, artefatos gerados, segredos e compatibilidade com Python declarado.
- Avaliar, com requisitos definidos, a necessidade de persistência, transformações, agregações, CLI, dashboard, cache, retries limitados ou acesso ao vivo.
- Adicionar endpoints gradualmente, com testes e documentação correspondentes.

**Critério de saída:** alterações são necessárias ao escopo acordado, sem regressões conhecidas e com validações relatadas com resultados reais.

## 5. Qualidade e segurança

- Priorizar funções simples, type hints em interfaces públicas e erros explícitos.
- Validar configurações necessárias antes de executar consultas.
- Não registrar tokens, credenciais, dados pessoais ou conteúdo sensível.
- Não armazenar segredos em código ou versionar arquivos `.env` com valores reais.
- Não carregar grandes volumes de telemetria sem necessidade; restringir consultas e avaliar processamento incremental somente quando o volume justificar.
- Projetar retries com limites e backoff apenas para falhas transitórias; definir idempotência antes de adicionar escrita ou persistência.
- Não afirmar que uma validação passou sem executar o comando correspondente.

## 6. Comandos de validação previstos

Executar no ambiente do Poetry, após confirmar que as ferramentas estão configuradas:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run pytest
poetry run pytest --cov=f1 --cov-report=term-missing --cov-fail-under=50
poetry run mkdocs build --strict
```

Executar a validação do MkDocs apenas depois de sua configuração estar presente. Se qualquer ferramenta ainda não estiver configurada, primeiro inspecionar o manifesto e adicioná-la via Poetry somente quando necessário.

## 7. Decisões pendentes antes de ampliar o MVP

- Qual é o resultado esperado para o usuário: biblioteca de consultas, pipeline de dados, dashboard ou outro produto?
- Quais dados são prioritários e quais filtros devem ser expostos?
- O projeto precisa persistir dados? Se sim, em qual formato e destino?
- É necessário processar dados em tempo real ou apenas históricos?
- Qual interface de execução é desejada: API Python, CLI, job agendado ou interface visual?
- Existem requisitos de atualização, volume, latência ou retenção?

As respostas podem alterar a arquitetura e o escopo das fases posteriores; não implementar essas decisões por suposição.
