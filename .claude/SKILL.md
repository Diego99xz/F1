# Skill: Padronização de projetos Python

## Objetivo

Orientar uma IA de programação na criação, manutenção e evolução de projetos Python com ambientes reprodutíveis, código consistente, testes automatizados e documentação técnica verificável.

## Escopo

Aplicar esta skill ao iniciar um projeto Python ou ao implementar funcionalidades, corrigir defeitos, refatorar código, alterar dependências, testes ou documentação em um projeto Python existente.

Esta skill define requisitos obrigatórios e recomendações. **Obrigatório** indica uma regra que deve ser seguida. **Recomendado** indica uma prática a adotar quando fizer sentido para o projeto. Não altere arquivos ou configurações existentes automaticamente apenas para alinhá-los a um exemplo: primeiro inspecione-os, preserve o que for válido e explique incompatibilidades.

## Contexto do projeto atual

Ao criar esta skill, o projeto contém:

- Pacote de produção em `src/f1/` e testes em `tests/`.
- `pyproject.toml` com Poetry, pacote `f1` e requisito `requires-python = ">=3.13"`.
- Nenhum `poetry.lock`, `.python-version`, `.gitignore`, `mkdocs.yml` ou dependência de desenvolvimento identificada.

Esses fatos descrevem o estado observado, não afirmam que as ferramentas já estejam configuradas ou validadas. Ao trabalhar neste projeto, respeite a estrutura e a compatibilidade Python declarada. Proponha alterações de configuração ou dependências somente quando necessárias à tarefa e faça-as de forma explícita.

## 1. Ambiente e dependências

### Requisitos obrigatórios

1. Use **pyenv** para instalar e selecionar localmente a versão de Python do projeto. No Windows, use uma distribuição compatível, como **pyenv-win**; os comandos e a configuração do shell podem diferir do pyenv para Unix.
2. Registre a seleção local em `.python-version`. A versão deve ser compatível com as dependências e com o requisito declarado no `pyproject.toml`.
3. Use **Poetry** para dependências do projeto, ambiente virtual, instalação e execução. O Poetry deve usar o interpretador selecionado pelo pyenv.
4. Declare em `pyproject.toml` o intervalo de versões Python suportado e mantenha-o coerente com `.python-version` e com as dependências.
5. Centralize metadados, dependências e configurações de ferramentas em `pyproject.toml` sempre que a ferramenta permitir.
6. Versione `poetry.lock` para aplicações e projetos que dependem de instalações reproduzíveis. Atualize-o com comandos do Poetry quando as dependências mudarem.
7. Instale dependências de produção e desenvolvimento no ambiente do projeto. Não instale dependências do projeto globalmente e não use `pip` para gerenciá-las diretamente.
8. Antes de instalar ou alterar dependências, inspecione `pyproject.toml`, `poetry.lock`, o ambiente ativo e as ferramentas já disponíveis. Instale somente o necessário.
9. Execute Python, testes e ferramentas usando `poetry run` ou comandos equivalentes do Poetry.
10. Documente os comandos de configuração para uma máquina nova e as diferenças relevantes entre Windows/PowerShell e Unix.

### Configuração inicial

Escolha uma versão compatível com o intervalo suportado pelo projeto. Confirme a versão antes de fixá-la. Os exemplos abaixo usam `3.13.x` apenas como ilustração; adapte o patch à versão disponível e às necessidades do projeto.

**Unix (bash/zsh, pyenv):**

```bash
pyenv install 3.13.x
pyenv local 3.13.x
python --version
poetry env use "$(pyenv which python)"
poetry install
poetry env info
```

**Windows (PowerShell, pyenv-win):**

```powershell
pyenv install 3.13.x
pyenv local 3.13.x
python --version
poetry env use (pyenv which python)
poetry install
poetry env info
```

Instale e configure pyenv/pyenv-win e Poetry conforme a documentação oficial de cada ferramenta e os requisitos do sistema operacional. Não suponha que comandos de instalação de Unix funcionem no Windows. Se `pyenv which python` não estiver disponível na instalação usada, consulte os executáveis reconhecidos por `pyenv` e `poetry env use`; não selecione um interpretador global por conveniência.

O comando `pyenv local` cria ou atualiza `.python-version`. Após selecionar o interpretador correto, crie/atualize o ambiente virtual com `poetry env use` e instale as dependências com `poetry install`. Verifique o caminho e a versão do ambiente antes de executar tarefas.

### Dependências

- Adicione dependências de produção com `poetry add nome-do-pacote`.
- Adicione ferramentas de desenvolvimento com `poetry add --group dev nome-do-pacote`.
- Remova dependências com o comando apropriado do Poetry e atualize o lockfile com o Poetry.
- Não adicione uma ferramenta ou biblioteca se a funcionalidade existente já resolver a necessidade. Justifique novas dependências na alteração.
- Use `poetry run python -m pacote` para executar o pacote e `poetry run python caminho/do/script.py` para scripts avulsos.

## 2. Estrutura do projeto

Adote `src/` para separar código de produção de testes. Adapte nomes e diretórios ao projeto; não crie módulos, diretórios ou arquivos sem necessidade.

```text
projeto/
├── src/
│   └── pacote/
│       ├── __init__.py
│       └── ...
├── tests/
│   └── ...
├── docs/
│   ├── index.md
│   └── ...
├── .python-version
├── .gitignore
├── mkdocs.yml
├── pyproject.toml
├── poetry.lock
├── README.md
└── SKILL.md
```

- Todo código de produção fica no pacote sob `src/`; testes automatizados ficam em `tests/`.
- Mantenha documentação técnica em `docs/` quando o projeto usar MkDocs.
- Preserve arquivos e convenções existentes que já atendam ao projeto.
- Configure `.gitignore` para ignorar `.venv/`, caches, arquivos temporários, artefatos de teste/compilação e arquivos com segredos. Não ignore `poetry.lock` quando a reprodutibilidade do projeto depender dele.

## 3. Ruff — análise e formatação

**Obrigatório:** use [Ruff](https://docs.astral.sh/ruff/) para lint e formatação; instale-o como dependência de desenvolvimento via Poetry. Configure as regras no `pyproject.toml` e execute-o no ambiente do projeto.

Exemplo de configuração a adaptar ao projeto:

```toml
[tool.ruff]
line-length = 88
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.ruff.format]
quote-style = "double"
```

Escolha `target-version` conforme a versão mínima real suportada. Ajuste a lista de regras aos padrões adotados, sem desabilitar regras globalmente ou ignorar alertas sem justificativa técnica.

```bash
poetry run ruff check .
poetry run ruff check . --fix
poetry run ruff format .
poetry run ruff format --check .
```

Corrija os problemas encontrados antes de concluir. Não use formatadores concorrentes como Black quando Ruff estiver configurado para formatar o projeto.

## 4. Pytest — testes e cobertura

**Obrigatório:** use [pytest](https://docs.pytest.org/) e `pytest-cov` como dependências de desenvolvimento instaladas via Poetry. Os testes devem verificar comportamento real, ser independentes e reproduzíveis.

A cobertura mínima é **50% do código de produção** em `src/<pacote>/`. A configuração deve medir explicitamente esse código, não os testes, e falhar abaixo do limite. Adapte `<pacote>` ao nome real; por exemplo, neste repositório, o pacote é `f1`.

Configuração ilustrativa em `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "--cov=src/<pacote>",
    "--cov-report=term-missing",
    "--cov-fail-under=50",
]

[tool.coverage.run]
source = ["src/<pacote>"]
branch = true
```

Substitua literalmente `<pacote>` pelo diretório real do pacote antes de usar a configuração. Evite definir a mesma opção em vários arquivos.

```bash
poetry run pytest
poetry run pytest --cov-report=html
```

O primeiro comando deve mostrar cobertura no terminal e retornar falha se ficar abaixo de 50%. O segundo também gera `htmlcov/index.html`; abra esse arquivo localmente para consultar o relatório HTML.

Os testes devem cobrir casos de sucesso, entradas inválidas, exceções, limites e comportamentos relevantes. Use mocks para isolar serviços externos quando apropriado. Não crie testes artificiais, não exclua código da medição para alcançar a meta e não reduza o limite para ocultar cobertura insuficiente.

## 5. MkDocs Material — documentação

Quando o projeto mantiver documentação técnica em site, use **MkDocs Material** como dependência de desenvolvimento instalada via Poetry. Mantenha as páginas em Markdown em `docs/`, configure o site em `mkdocs.yml` e inclua `docs/index.md`.

A documentação deve explicar, conforme aplicável:

- Objetivo, arquitetura e estrutura do projeto.
- Requisitos e configuração do ambiente.
- Instalação, execução, testes e comandos disponíveis.
- Módulos e APIs públicas, parâmetros, retornos, exceções e exemplos de uso.

Mantenha o conteúdo coerente com a implementação: não documente funcionalidades inexistentes. Atualize páginas afetadas quando o código ou o fluxo de uso mudar.

Exemplo básico de `mkdocs.yml`, ajustável à estrutura efetiva:

```yaml
site_name: Documentação do projeto
docs_dir: docs
theme:
  name: material
nav:
  - Início: index.md
```

Instale a ferramenta somente se a documentação do projeto exigir MkDocs e após verificar o manifesto:

```bash
poetry add --group dev mkdocs-material
poetry run mkdocs serve
poetry run mkdocs build --strict
```

`mkdocs serve` inicia o servidor local e informa o endereço para abrir no navegador. `mkdocs build --strict` compila a versão estática e trata avisos como erros. Não execute o comando de instalação se a dependência já estiver configurada.

## 6. Configuração centralizada e compatibilidade

- Mantenha no `pyproject.toml` os metadados, dependências e configurações de Poetry, Ruff, pytest e cobertura quando suportado.
- Mantenha `mkdocs.yml` como configuração do site MkDocs e `.python-version` como seleção local do pyenv.
- Antes de copiar exemplos desta skill, confira a versão do Poetry, o formato existente do `pyproject.toml`, a versão mínima de Python e as opções aceitas pelas ferramentas.
- Exemplos são referências, não autorização para sobrescrever configurações válidas. Integre as opções necessárias sem apagar metadados, dependências ou configuração existentes.
- Os comandos apresentados devem refletir as dependências configuradas. Não declare que uma ferramenta está instalada ou validada sem verificar.

## 7. Fluxo obrigatório de desenvolvimento

Ao implementar uma funcionalidade, corrigir um defeito ou refatorar:

1. Inspecione a estrutura, o estado do repositório, `pyproject.toml`, lockfile, instruções e testes existentes.
2. Identifique requisitos, comportamento esperado, superfícies afetadas e critérios de aceitação.
3. Verifique a versão Python selecionada pelo pyenv e sua compatibilidade com o projeto.
4. Confirme que Poetry aponta para o ambiente virtual correto.
5. Instale ou altere somente dependências necessárias, pelo Poetry, e atualize o lockfile.
6. Implemente a solução no pacote de produção existente sob `src/`.
7. Crie ou atualize testes relacionados em `tests/`.
8. Execute Ruff para lint e formatação; revise as alterações de formatação.
9. Execute pytest; confira resultado e cobertura do código de produção contra o limite de 50%.
10. Atualize a documentação somente quando a alteração afetar o comportamento, a instalação, a configuração ou o uso documentado.
11. Quando MkDocs estiver configurado ou for alterado, compile a documentação em modo estrito.
12. Revise o diff: remova alterações desnecessárias, dependências não utilizadas e arquivos acidentais; preserve alterações preexistentes de outras pessoas.
13. Informe o resumo da implementação e os resultados reais das validações, inclusive falhas não resolvidas.

Não afirme que lint, testes, cobertura ou documentação foram validados sem executar os respectivos comandos e conferir o resultado. Se uma validação falhar, investigue, corrija a causa quando estiver no escopo e execute novamente; caso contrário, relate claramente a falha e sua causa conhecida.

## 8. Boas práticas e restrições

- Priorize soluções simples, legíveis, modulares e fáceis de manter; siga PEP 8 e use type hints quando apropriado.
- Aplique SOLID quando ajudar a resolver o problema, sem criar abstrações desnecessárias.
- Evite duplicação, dependências sem justificativa, código sem uso e mudanças de comportamento não solicitadas.
- Nunca inclua segredos, tokens, senhas ou credenciais no código, nos testes ou na documentação.
- Não sobrescreva configurações ou arquivos sem inspecioná-los; não altere funcionalidades existentes sem necessidade.
- Não ignore falhas de testes, não reduza o limite de cobertura e não use instalação global como substituta das dependências do projeto.
- Use comandos reproduzíveis no ambiente do Poetry e considere diferenças entre PowerShell e shells Unix.

## 9. Checklist de conclusão

Antes de concluir uma tarefa, confirme os itens aplicáveis:

- [ ] Estrutura, configurações e alterações preexistentes foram inspecionadas e preservadas.
- [ ] A solução está no pacote correto sob `src/`, com testes em `tests/`.
- [ ] Python e ambiente virtual correspondem à configuração local do projeto.
- [ ] Dependências necessárias estão declaradas no Poetry e o lockfile foi atualizado quando necessário.
- [ ] `poetry run ruff check .` e `poetry run ruff format --check .` passaram.
- [ ] `poetry run pytest` passou e a cobertura de produção é de pelo menos 50%.
- [ ] Documentação afetada foi atualizada; se MkDocs se aplica, `poetry run mkdocs build --strict` passou.
- [ ] O diff não contém arquivos ou alterações desnecessários.
- [ ] A resposta final informa o que foi alterado e os resultados efetivamente verificados.

## Critérios objetivos de conclusão

Uma implementação está concluída quando atende aos critérios de aceitação, não introduz regressões conhecidas, possui testes pertinentes, passa pelas validações aplicáveis e mantém cobertura mínima de 50% do código de produção. A documentação deve refletir o comportamento atual e compilar sem erros quando MkDocs estiver configurado. Qualquer validação não executada ou falha restante deve ser explicitamente informada, nunca apresentada como sucesso.
