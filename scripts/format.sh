isort bolinette tests example \
    && autoflake -r --in-place --remove-unused-variables bolinette tests example \
    && black bolinette tests example