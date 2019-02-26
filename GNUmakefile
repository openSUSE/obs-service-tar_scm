# Ensure that we don't accidentally ignore failing commands just
# because they're in a pipeline.  This applies in particular to piping
# the test runs through tee(1).
# http://stackoverflow.com/a/31605520/179332
SHELL    = /bin/bash -o pipefail

DESTDIR ?=
PREFIX   = /usr
SYSCFG   = /etc

CLEAN_PYFILES = \
  ./tar_scm.py \
  ./TarSCM/scm/bzr.py \
  ./TarSCM/scm/svn.py \
  ./TarSCM/exceptions.py \

CLEAN_TEST_PYFILES = \
  ./tests/__init__.py \
  ./tests/utils.py \
  ./tests/tarfixtures.py \
  ./tests/unittestcases.py \
  ./tests/archiveobscpiotestcases.py \

PYLINT_READY_TEST_MODULES = \
  $(CLEAN_TEST_PYFILES) \
  ./tests/test.py \
  ./tests/scmlogs.py \
  ./tests/tartests.py \

PYLINT_READY_MODULES = \
  $(CLEAN_PYFILES) \
  ./TarSCM/__init__.py  \
  ./TarSCM/scm/git.py  \
  ./TarSCM/scm/hg.py  \
  ./TarSCM/scm/__init__.py  \
  ./TarSCM/cli.py  \
  ./TarSCM/tasks.py  \

define first_in_path
$(or \
    $(firstword $(wildcard \
        $(foreach p,$(1),$(addsuffix /$(p),$(subst :, ,$(PATH)))) \
    )), \
    $(error Need one of: $(1)) \
)
endef

define first_in_path_opt
$(or \
    $(firstword $(wildcard \
        $(foreach p,$(1),$(addsuffix /$(p),$(subst :, ,$(PATH)))) \
    )), \
)
endef

# On ArchLinux, /usr/bin/python is Python 3, and other distros
# will switch to the same at various points.  So until we support
# Python 3, we need to do our best to ensure we have Python 2.
PYTHON3 = python3 python3.6 python-3.6 python
PYTHON2 = python2 python2.7 python-2.7 python2.6 python-2.6 python
ALL_PYTHONS = $(PYTHON3) $(PYTHON2)
PYTHON_MAJOR := $(shell python -c "import sys; print sys.version[:1]" 2>/dev/null)
ifeq ($(PYTHON_MAJOR), 2)
PYTHON := $(shell which python2)
else
PYTHON = $(call first_in_path,$(ALL_PYTHONS))
endif

mylibdir = $(PREFIX)/lib/obs/service
mycfgdir = $(SYSCFG)/obs/services

LIST_PY_FILES=git ls-tree --name-only -r HEAD | grep '\.py$$'
PY_FILES=$(shell $(LIST_PY_FILES))

ALL_PYLINT2 = pylint-2.7 pylint2.7 pylint
ALL_PYLINT3 = pylint-3.4 pylint3.4 pylint-3.5 pylint3.5 pylint-3.6 pylint3.6 pylint-3.7 pylint3.7
ALL_FLAKE83 = flake8-3.6 flake8-36 flake8-37 flake8-3.7 flake8

PYLINT2 = $(call first_in_path_opt,$(ALL_PYLINT2))
PYLINT3 = $(call first_in_path_opt,$(ALL_PYLINT3))

FLAKE83 = $(call first_in_path_opt,$(ALL_FLAKE83))

default: check

.PHONY: check check_all
check: check2 check3

.PHONY: check2
check2: flake8 pylint test

.PHONY: check3
check3: flake83 pylint3 test3

.PHONY: list-py-files
list-py-files:
	@$(LIST_PY_FILES)

.PHONY: flake8
flake8:
	@if ! which flake8 >/dev/null 2>&1; then \
		echo "flake8 not installed!  Cannot check PEP8 compliance with flake8. Skipping tests." >&2; \
	else \
		echo "Running flake8";\
		flake8;\
		echo "Finished flake8";\
	fi

.PHONY: flake83
flake83:
	@if [ "x$(FLAKE83)" != "x" ]; then \
		echo "Running flake83";\
		$(FLAKE83);\
		echo "Finished flake83";\
	else \
		echo "flake8 for python3 not found";\
	fi


.PHONY: test
test:
	: Running the test suite.  Please be patient - this takes a few minutes ...
	LANG=en_US.UTF-8 LC_TYPE=en_US.UTF-8 TAR_SCM_TESTMODE=1 PYTHONPATH=. $(PYTHON) tests/test.py 2>&1 | tee ./test.log

test3:
	: Running the test suite.  Please be patient - this takes a few minutes ...
	LANG=en_US.UTF-8 LC_TYPE=en_US.UTF-8 TAR_SCM_TESTMODE=1 PYTHONPATH=. python3 tests/test.py 2>&1 | tee ./test3.log

.PHONY: pylint
pylint: pylint2 pylinttest2

.PHONY: pylint3
pylint3:
	@if [ "x$(PYLINT3)" != "x" ]; then \
		$(PYLINT3) --rcfile=./.pylintrc $(PYLINT_READY_MODULES); \
		PYTHONPATH=tests $(PYLINT3) --rcfile=./.pylinttestsrc $(PYLINT_READY_TEST_MODULES); \
	else \
		echo "PYLINT3 not set - Skipping tests"; \
	fi

.PHONY: pylint2
pylint2:
	@if [ "x$(PYLINT2)" != "x" ]; then \
		$(PYLINT2) --rcfile=./.pylintrc $(PYLINT_READY_MODULES); \
	else \
		echo "PYLINT2 not set - Skipping tests"; \
	fi

.PHONY: pylinttest2
pylinttest2:
	@if [ "x$(PYLINT2)" != "x" ]; then \
		PYTHONPATH=tests $(PYLINT2) --rcfile=./.pylinttestsrc $(PYLINT_READY_TEST_MODULES); \
	else \
		echo "PYLINT2 not set - Skipping tests"; \
	fi


cover:
	PYTHONPATH=. coverage2 run tests/test.py 2>&1 | tee ./cover.log
	coverage2 html --include=./TarSCM/*

tar_scm: tar_scm.py
	@echo "Creating $@ which uses $(PYTHON) ..."
	sed 's,^\#!/usr/bin/.*,#!$(PYTHON),' $< > $@

.PHONY: install

install: dirs tar_scm service
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
	find ./TarSCM/ -name '*.py*' -exec install -m 644 {} $(DESTDIR)$(mylibdir)/{} \;

.PHONY: dirs
dirs:
	mkdir -p $(DESTDIR)$(mylibdir)
	mkdir -p $(DESTDIR)$(mylibdir)/TarSCM
	mkdir -p $(DESTDIR)$(mylibdir)/TarSCM/scm
	mkdir -p $(DESTDIR)$(mycfgdir)

.PHONY: service
service: dirs
	install -m 0644 tar.service $(DESTDIR)$(mylibdir)/
	install -m 0644 snapcraft.service $(DESTDIR)$(mylibdir)/
	install -m 0644 appimage.service $(DESTDIR)$(mylibdir)/
	sed -e '/^===OBS_ONLY/,/^===/d' -e '/^===/d' tar_scm.service.in > $(DESTDIR)$(mylibdir)/tar_scm.service
	sed -e '/^===TAR_ONLY/,/^===/d' -e '/^===/d' tar_scm.service.in > $(DESTDIR)$(mylibdir)/obs_scm.service

show-python:
	@echo "$(PYTHON)"

.PHONY: clean
clean:
	find -name '*.pyc' -exec rm -f {} \;
	rm -rf ./tests/tmp/
	rm -f ./test.log
	rm -f ./test3.log
	rm -f ./cover.log

compile:
	find -name '*.py' -exec python -m py_compile {} \;
