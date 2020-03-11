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

PYTHON3 = python3.9 python-3.9 python3.8 python-3.8 python3.7 python-3.7 python3.6 python-3.6 python3.5 python-3.5 python3.4 python-3.4 python3.3 python-3.3 python3.2 python-3.2 python3

# Ensure that correct python version is used in travis
ALL_PYTHONS = $(PYTHON3)

PYTHON = $(call first_in_path,$(ALL_PYTHONS))

mylibdir = $(PREFIX)/lib/obs/service
mycfgdir = $(SYSCFG)/obs/services

LIST_PY_FILES=git ls-tree --name-only -r HEAD | grep '\.py$$'
PY_FILES=$(shell $(LIST_PY_FILES))

ALL_PYLINT = pylint-3.4 pylint3.4 pylint-3.5 pylint3.5 pylint-3.6 pylint3.6 pylint-3.7 pylint3.7 pylit-3.8 pylint3.8 pylint-3.9 pylint3.9 pylint
ALL_FLAKE8 = flake8-3.6 flake8-36 flake8-37 flake8-3.7 flake8-38 flake8-3.8 flake8-39 flake8-3.9 flake8

PYLINT = $(call first_in_path_opt,$(ALL_PYLINT))
FLAKE8 = $(call first_in_path_opt,$(ALL_FLAKE8))

default: check

.PHONY: check check_all
check: flake8 pylint test

.PHONY: list-py-files
list-py-files:
	@$(LIST_PY_FILES)

.PHONY: flake8
flake8:
	@if [ "x$(FLAKE8)" != "x" ]; then \
		echo "Running flake8";\
		$(FLAKE8);\
		echo "Finished flake8";\
	else \
		echo "flake8 for python3 not found";\
	fi


test:
	: Running the test suite.  Please be patient - this takes a few minutes ...
	TAR_SCM_TESTMODE=1 PYTHONPATH=. python3 tests/test.py 2>&1 | tee ./test3.log

.PHONY: pylint
pylint:
	@if [ "x$(PYLINT)" != "x" ]; then \
		$(PYLINT) --rcfile=./.pylintrc $(PYLINT_READY_MODULES); \
		PYTHONPATH=tests $(PYLINT) --rcfile=./.pylinttestsrc $(PYLINT_READY_TEST_MODULES); \
	else \
		echo "PYLINT not set - Skipping tests"; \
	fi

cover:
	PYTHONPATH=. coverage2 run tests/test.py 2>&1 | tee ./cover.log
	coverage2 html --include=./TarSCM/*

tar_scm: tar_scm.py
	@echo "Creating $@ which uses $(PYTHON) ..."
	sed 's,^\#!/usr/bin/.*,#!$(PYTHON),' $< > $@

.PHONY: install

install: dirs tar_scm service compile
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
	[ ! -L $(DESTDIR)$(mylibdir)/obs_gbp ] || rm $(DESTDIR)$(mylibdir)/obs_gbp
	ln -s tar_scm $(DESTDIR)$(mylibdir)/obs_gbp
	find ./TarSCM/ -name '*.py*' -exec install -D -m 644 {} $(DESTDIR)$(mylibdir)/{} \;

.PHONY: dirs
dirs:
	mkdir -p $(DESTDIR)$(mylibdir)
	mkdir -p $(DESTDIR)$(mylibdir)/TarSCM
	mkdir -p $(DESTDIR)$(mylibdir)/TarSCM/scm
	mkdir -p $(DESTDIR)$(mycfgdir)
	mkdir -p $(DESTDIR)$(mycfgdir)/tar_scm.d

.PHONY: service
service: dirs
	install -m 0644 tar.service $(DESTDIR)$(mylibdir)/
	install -m 0644 snapcraft.service $(DESTDIR)$(mylibdir)/
	install -m 0644 appimage.service $(DESTDIR)$(mylibdir)/
	sed -e '/^===OBS_ONLY/,/^===/d' -e '/^===GBP_ONLY/,/^===/d' -e '/^===/d' tar_scm.service.in > $(DESTDIR)$(mylibdir)/tar_scm.service
	sed -e '/^===TAR_ONLY/,/^===/d' -e '/^===GBP_ONLY/,/^===/d' -e '/^===/d' tar_scm.service.in > $(DESTDIR)$(mylibdir)/obs_scm.service
	sed -e '/^===OBS_ONLY/,/^===/d' -e '/^===TAR_ONLY/,/^===/d' -e '/^===/d' tar_scm.service.in > $(DESTDIR)$(mylibdir)/obs_gbp.service

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
	find -name '*.py' -exec $(PYTHON) -m py_compile {} \;
