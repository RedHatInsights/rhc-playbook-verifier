PYTHON		?= python3
VERSION = $(shell $(PYTHON) setup.py --version | tr -d '\n')

BUILDROOT?=/etc/mock/default.cfg

rhc-playbook-verifier.spec: rhc-playbook-verifier.spec.in
	[[ -n "$(VERSION)" ]]
	sed -e 's,[@]VERSION[@],$(VERSION),g' $< > $@

.PHONY: build-py
build-py:
	@echo "Building Python package" && \
	cp data/public.gpg python/rhc_playbook_verifier/data/public.gpg
	cp data/revoked_playbooks.yml python/rhc_playbook_verifier/data/revoked_playbooks.yml

.PHONY: tarball
tarball:
	mkdir -p "rpm/"
	rm -rf rpm/rhc-playbook-verifier-$(VERSION).tar.gz
	git ls-files -z | xargs -0 tar \
		--create --gzip \
		--transform "s|^|/rhc-playbook-verifier-$(VERSION)/|" \
		--file rpm/rhc-playbook-verifier-$(VERSION).tar.gz

.PHONY: srpm
srpm:
	rpmbuild -bs \
		--define "_sourcedir `pwd`/rpm" \
		--define "_srcrpmdir `pwd`/rpm" \
		rhc-playbook-verifier.spec

.PHONY: rpm
rpm: rhc-playbook-verifier.spec tarball srpm
	mock \
		--root $(BUILDROOT) \
		--rebuild \
		--resultdir "rpm/" \
		rpm/rhc-playbook-verifier-*.src.rpm


.PHONY: clean
clean: clean-rpm

.PHONY: clean-rpm
clean-rpm:
	rm -f rpm/*
