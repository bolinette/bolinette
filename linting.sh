mypy --namespace-packages --explicit-package-bases bolinette \
    && mypy --namespace-packages --explicit-package-bases tests \
    && isort --skip __init__.py bolinette && isort --skip __init__.py tests \
    && autoflake -r --in-place --remove-unused-variables bolinette && autoflake -r --in-place --remove-unused-variables tests \
    && black bolinette && black tests