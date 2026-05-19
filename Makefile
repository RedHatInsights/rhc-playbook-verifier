PYTHON		?= python3
VERSION = $(shell $(PYTHON) setup.py --version | tr -d '\n')
SOURCES := $(shell find . -name '*.py' -o -name 'rhc-playbook-verifier.toml')

BUILDROOT?=/etc/mock/default.cfg

# setuptools < 69.3.0 creates archives with dashes, e.g. rhc-playbook-verifier-1.0.0.tar.gz
# setuptools >= 69.3.0 creates archives with underscores, e.g. rhc_playbook_verifier-1.0.0.tar.gz
# See: https://setuptools.pypa.io/en/latest/history.html#v69-3-0
SDIST_PREFIX := $(shell if [[ $$(echo -e "69.3.0\n$$(rpm -q python3-setuptools --qf='%{VERSION}')" | sort -V | head -n 1) == '69.3.0' ]]; then echo 'rhc_playbook_verifier'; else echo 'rhc-playbook-verifier'; fi)

rhc-playbook-verifier.spec: rhc-playbook-verifier.spec.in
	[[ -n "$(VERSION)" ]]
	[[ -n "$(SDIST_PREFIX)" ]]
	sed -e 's,[@]VERSION[@],$(VERSION),g' -e 's,[@]SDIST_PREFIX[@],$(SDIST_PREFIX),g' $< > $@

dist: $(SOURCES)
	cp data/public.gpg python/rhc_playbook_verifier/data/public.gpg
	cp data/revoked_playbooks.yml python/rhc_playbook_verifier/data/revoked_playbooks.yml
	$(PYTHON) setup.py sdist
	touch $@  # ensure target is newer than prerequisites

# --define values are listed in:
# https://docs.fedoraproject.org/en-US/packaging-guidelines/RPMMacros/#_macros_set_for_the_rpm_and_srpm_build_process
srpm: rhc-playbook-verifier.spec dist
	rpmbuild -bs \
		--define="_sourcedir $(abspath dist)" \
		--define="_srcrpmdir $(abspath srpm)" \
		rhc-playbook-verifier.spec
	touch $@  # ensure target is newer than prerequisites

rpm: rhc-playbook-verifier.spec dist
	rpmbuild -bb \
		--define="_sourcedir $(abspath dist)" \
		--define="_rpmdir $(abspath rpm)" \
		rhc-playbook-verifier.spec
	touch $@

mock: srpm
	mock \
		--root=$(BUILDROOT) \
		--rebuild \
		--resultdir="$(abspath mock)" \
		srpm/rhc-playbook-verifier-*.src.rpm
	touch $@  # ensure target is newer than prerequisites
