DESTDIR ?=
PREFIX   = /usr/local
SYSCFG   = /etc

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
	find -name \*.py | xargs pep8 --ignore=E221,E272,E241 $<

.PHONY: test
test:
	: Running the test suite.  Please be patient - this takes a few minutes ...
	python tests/test.py

.PHONY: install
install:
	mkdir -p $(DESTDIR)$(mylibdir)
	mkdir -p $(DESTDIR)$(mycfgdir)
	install -m 0755 tar_scm.py $(DESTDIR)$(mylibdir)/tar_scm
	install -m 0644 tar_scm.service $(DESTDIR)$(mylibdir)
	install -m 0644 tar_scm.rc $(DESTDIR)$(mycfgdir)/tar_scm
