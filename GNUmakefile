DESTDIR ?=
PREFIX   = /usr/local
SYSCFG   = /etc

mylibdir = $(PREFIX)/lib/obs/service
mycfgdir = $(SYSCFG)/obs/services

.PHONY: check
check:
	: Running the test suite.  Please be patient - this takes a few minutes ...
	python tests/test.py

.PHONY: install
install:
	mkdir -p $(DESTDIR)$(mylibdir)
	mkdir -p $(DESTDIR)$(mycfgdir)
	install -m 0755 tar_scm $(DESTDIR)$(mylibdir)
	install -m 0644 tar_scm.service $(DESTDIR)$(mylibdir)
	install -m 0644 tar_scm.rc $(DESTDIR)$(mycfgdir)/tar_scm
