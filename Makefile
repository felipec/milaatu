D := $(DESTDIR)

install: datadir := $(D)/usr/share/milaatu
install:
	install -m 755 -D milaatu-runner $(D)/usr/bin/milaatu-runner
	install -m 755 -D runner $(datadir)/runner
	install -m 644 base/* $(datadir)/base
	install -m 644 tests/* $(datadir)/tests
