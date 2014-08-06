DESTDIR ?=
PREFIX   = /usr/local
SYSCFG   = /etc

mylibdir = $(PREFIX)/lib/obs/service
mycfgdir = $(SYSCFG)/obs/services

.PHONY: install
install:
	mkdir -p $(DESTDIR)$(mylibdir)
	mkdir -p $(DESTDIR)$(mycfgdir)
	install -m 0755 tar_scm $(DESTDIR)$(mylibdir)
	install -m 0644 tar_scm.service $(DESTDIR)$(mylibdir)
	install -m 0644 tar_scm.rc $(DESTDIR)$(mycfgdir)/tar_scm
