.PHONY: install
install:
	mkdir -p $(DESTDIR)/usr/lib/obs/service
	mkdir -p $(DESTDIR)/etc/obs/services
	install -m 0755 tar_scm $(DESTDIR)/usr/lib/obs/service
	install -m 0644 tar_scm.service $(DESTDIR)/usr/lib/obs/service
	install -m 0644 tar_scm.rc $(DESTDIR)/etc/obs/services/tar_scm
