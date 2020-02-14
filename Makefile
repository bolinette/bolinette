clean:
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist

install-blnt:
	pip install --upgrade pip
	pip install -r requirements.bolinette.txt

package-blnt:
	python setup.bolinette.py sdist
	python setup.bolinette.py bdist_wheel

install-cli:
	pip install --upgrade pip
	pip install -r requirements.bolinette_cli.txt

package-cli:
	python setup.bolinette_cli.py sdist
	python setup.bolinette_cli.py bdist_wheel
