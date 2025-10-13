VERSION?=1.0.0
BUILDROOT?=/etc/mock/default.cfg

.PHONY: build
build: build-py
	sed -i "s|Version:.*|Version:  $(VERSION)|" rhc-playbook-verifier.spec
	@echo "Built $(VERSION)"

.PHONY: build-py
build-py:
	@echo "Building Python package" && \
	cp data/public.gpg python/rhc_playbook_verifier/data/public.gpg
	cp data/revoked_playbooks.yml python/rhc_playbook_verifier/data/revoked_playbooks.yml
	sed -i "s|version = .*|version = $(VERSION)|" setup.cfg


.PHONY: test
test: test-py

.PHONY: test-py
test-py:
	PYTHONPATH=python/ pytest python/tests-unit/ -v


.PHONY: integration
integration: integration-py

.PHONY: integration-py
integration-py:
	PYTHONPATH=python/ pytest python/tests-integration/ -v


.PHONY: check
check: check-py
	gitleaks git --verbose

.PHONY: check-py
check-py:
	ruff check python/
	ruff format --diff python/
	mypy


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
rpm: build tarball srpm
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
