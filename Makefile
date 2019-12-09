clean:
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .

package:
	python setup.py sdist
	python setup.py bdist_wheel
