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
PYTHON = $(call first_in_path,$(PYTHONS))

mylibdir = $(PREFIX)/lib/obs/service
mycfgdir = $(SYSCFG)/obs/services

default: check

.PHONY: check
check: pep8 test

.PHONY: pep8
pep8: tar_scm.py
	@if ! which pep8 >/dev/null 2>&1; then \
		echo "pep8 not installed!  Cannot check PEP8 compliance; aborting." >&2; \
		exit 1; \
	fi
	find -name \*.py | xargs pep8 --ignore=E221,E272,E241,E731 $<

.PHONY: test
test:
	: Running the test suite.  Please be patient - this takes a few minutes ...
	PYTHONPATH=. $(PYTHON) tests/test.py

tar_scm: tar_scm.py
	@echo "Creating $@ which uses $(PYTHON) ..."
	sed 's,^\#!/usr/bin/.*,#!$(PYTHON),' $< > $@

.PHONY: install
install: tar_scm
	mkdir -p $(DESTDIR)$(mylibdir)
	mkdir -p $(DESTDIR)$(mycfgdir)
	install -m 0755 tar_scm $(DESTDIR)$(mylibdir)/tar_scm
	install -m 0644 tar_scm.service $(DESTDIR)$(mylibdir)
	install -m 0644 tar_scm.rc $(DESTDIR)$(mycfgdir)/tar_scm

show-python:
	@echo "$(PYTHON)"
