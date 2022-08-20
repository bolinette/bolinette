isort --skip __init__.py bolinette tests \
    && autoflake -r --in-place --remove-unused-variables bolinette tests \
    && black bolinette tests