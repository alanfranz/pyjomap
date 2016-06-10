.PHONY: test clean distclean

# override VIRTUALENV or PYTHON as needed. If you override VIRTUALENV
# PYTHON may not be interpreted, depending on what you set.
PYTHON ?= $(shell which python2.7)
VIRTUALENV ?= $(shell which virtualenv) -p $(PYTHON)
SHELL := /bin/bash

devenv: setup.py Makefile
	test -r devenv || $(VIRTUALENV) devenv
	source devenv/bin/activate ; python devenv/bin/pip install --editable . --upgrade ; python devenv/bin/pip install bpython
	touch devenv

test: devenv
	devenv/bin/unit discover -v

clean:
	rm -rf tmp build dist

distclean: clean
	rm -rf devenv *.egg-info
