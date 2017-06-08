# Ensure that we don't accidentally ignore failing commands just
# because they're in a pipeline.  This applies in particular to piping
# the test runs through tee(1).
# http://stackoverflow.com/a/31605520/179332
SHELL    = /bin/bash -o pipefail

DESTDIR ?=
PREFIX   = /usr/local
SYSCFG   = /etc

define first_in_path
$(or \
    $(firstword $(wildcard \
        $(foreach p,$(1),$(addsuffix /$(p),$(subst :, ,$(PATH)))) \
    )), \
    $(error Need one of: $(1)) \
)
endef

# On ArchLinux, /usr/bin/python is Python 3, and other distros
# will switch to the same at various points.  So until we support
# Python 3, we need to do our best to ensure we have Python 2.
PYTHONS = python2.7 python-2.7 python2.6 python-2.6 python
PYTHON_MAJOR := $(shell python -c "import sys; print sys.version[:1]" 2>/dev/null)
ifeq ($(PYTHON_MAJOR), 2)
PYTHON := $(shell which python)
else
PYTHON = $(call first_in_path,$(PYTHONS))
endif

mylibdir = $(PREFIX)/lib/obs/service
mycfgdir = $(SYSCFG)/obs/services

LIST_PY_FILES=git ls-tree --name-only -r HEAD | grep '\.py$$'
PY_FILES=$(shell $(LIST_PY_FILES))

default: check

.PHONY: check
check: lint test

.PHONY: lint
lint: pep8 flake8

.PHONY: list-py-files
list-py-files:
	@$(LIST_PY_FILES)

.PHONY: pep8
pep8: $(PY_FILES)
	@if ! which pep8 >/dev/null 2>&1; then \
		echo "pep8 not installed!  Cannot check PEP8 compliance; aborting." >&2; \
		exit 1; \
	fi
	$(LIST_PY_FILES) | xargs pep8 --ignore=E221,E241,E251,E272,E731

.PHONY: flake8
flake8: $(PY_FILES)
	@if ! which flake8 >/dev/null 2>&1; then \
		echo "flake8 not installed!  Aborting." >&2; \
		exit 1; \
	fi
	$(LIST_PY_FILES) | xargs flake8 --ignore=E221,E241,E251,E272,E731

.PHONY: pylint
pylint: $(PY_FILES)
	@if ! which pylint >/dev/null 2>&1; then \
		echo "pylint not installed!  Aborting." >&2; \
		exit 1; \
	fi
	$(LIST_PY_FILES) | xargs pylint

.PHONY: test
test:
	: Running the test suite.  Please be patient - this takes a few minutes ...
	PYTHONPATH=. $(PYTHON) tests/test.py 2>&1 | tee ./test.log

test3:
	: Running the test suite.  Please be patient - this takes a few minutes ...
	PYTHONPATH=. python3 tests/test.py 2>&1 | tee ./test3.log

cover:
	PYTHONPATH=. coverage2 run tests/test.py 2>&1 | tee ./cover.log
	coverage2 html --include=./TarSCM/*

tar_scm: tar_scm.py
	@echo "Creating $@ which uses $(PYTHON) ..."
	sed 's,^\#!/usr/bin/.*,#!$(PYTHON),' $< > $@

.PHONY: install
install: tar_scm compile
	mkdir -p $(DESTDIR)$(mylibdir)
	mkdir -p $(DESTDIR)$(mylibdir)/TarSCM
	mkdir -p $(DESTDIR)$(mylibdir)/TarSCM/scm
	mkdir -p $(DESTDIR)$(mycfgdir)
	install -m 0755 tar_scm $(DESTDIR)$(mylibdir)/tar_scm
	install -m 0644 tar_scm.rc $(DESTDIR)$(mycfgdir)/tar_scm
	# Recreate links, otherwise reinstalling would fail
	[ ! -L $(DESTDIR)$(mylibdir)/obs_scm ] || rm $(DESTDIR)$(mylibdir)/obs_scm
	ln -s tar_scm $(DESTDIR)$(mylibdir)/obs_scm
	[ ! -L $(DESTDIR)$(mylibdir)/tar ] || rm $(DESTDIR)$(mylibdir)/tar
	ln -s tar_scm $(DESTDIR)$(mylibdir)/tar
	[ ! -L $(DESTDIR)$(mylibdir)/appimage ] || rm $(DESTDIR)$(mylibdir)/appimage
	ln -s tar_scm $(DESTDIR)$(mylibdir)/appimage
	[ ! -L $(DESTDIR)$(mylibdir)/snapcraft ] || rm $(DESTDIR)$(mylibdir)/snapcraft
	ln -s tar_scm $(DESTDIR)$(mylibdir)/snapcraft
	install -m 0644 tar.service $(DESTDIR)$(mylibdir)/
	install -m 0644 snapcraft.service $(DESTDIR)$(mylibdir)/
	install -m 0644 appimage.service $(DESTDIR)$(mylibdir)/
	sed -e '/^===OBS_ONLY/,/^===/d' -e '/^===/d' tar_scm.service.in > $(DESTDIR)$(mylibdir)/tar_scm.service
	sed -e '/^===TAR_ONLY/,/^===/d' -e '/^===/d' tar_scm.service.in > $(DESTDIR)$(mylibdir)/obs_scm.service
	find ./TarSCM/ -name '*.py*' -exec install -m 644 {} $(DESTDIR)$(mylibdir)/{} \;
show-python:
	@echo "$(PYTHON)"

clean:
	find -name '*.pyc' -exec rm -f {} \;
	rm -rf ./tests/tmp/
	rm -f ./test.log
	rm -f ./test3.log
	rm -f ./cover.log
compile:
	find -name '*.py' -exec python -m py_compile {} \;

