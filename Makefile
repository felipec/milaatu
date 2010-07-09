version := $(shell ./get-version)

D := $(DESTDIR)

install: datadir := $(D)/usr/share/milaatu
install:
	install -m 755 -D milaatu-runner $(D)/usr/bin/milaatu-runner
	install -m 755 -D runner $(datadir)/runner
	install -m 644 base/* $(datadir)/base
	install -m 644 tests/* $(datadir)/tests

dist: base := milaatu-$(version)
dist:
	git archive --format=tar --prefix=$(base)/ HEAD > /tmp/$(base).tar
	mkdir -p $(base)
	echo $(version) > $(base)/.version
	chmod 664 $(base)/.version
	tar --append -f /tmp/$(base).tar --owner root --group root $(base)/.version
	rm -r $(base)
	gzip /tmp/$(base).tar
