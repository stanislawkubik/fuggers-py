.PHONY: docs docs-clean

docs:
	python -m sphinx -W --keep-going -b html docs docs/_build/html

docs-clean:
	rm -rf docs/_build
