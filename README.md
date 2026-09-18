# Bolinette

This is the Bolinette monorepo, a uv workspace.
Each directory under `packages/` is a separately published distribution sharing the `bolinette` namespace package:
`bolinette` (the core), `bolinette-data`, `bolinette-web` and `bolinette-api`.

```shell
uv sync --all-groups           # install every package editable, with dev and test tools
uv run python -m pytest        # run the tests
uv build --all-packages        # build one wheel and sdist per package into dist/
```
