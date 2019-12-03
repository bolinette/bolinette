clean:
	rm -rf dist/*

install:
	pip install -r requirements.txt
	pip install -e .

package:
	python setup.py sdist
	python setup.py bdist_wheel

tests:
    pytest
