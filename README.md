# Ansible playbook verifier

When some Red Hat Insights service instructs a RHEL system to take some action (disable password-based SSH access to root account, update all packages containing CVEs, convert from CentOS to RHEL), it does so by sending an Ansible playbook to the host system.

Before the host executes the playbook, it verifies the embedded GPG signature to ensure the playbook can be trusted. That is what the Ansible playbook verifier does.

Historically, the Verifier has been a Python application shipped via Insights Client through its Core. This repository replaces it.

**References:**

- [Red Hat Insights](https://consoledot.redhat.com/insights): Red Hat cloud services
- [yggdrasil](https://github.com/RedHatInsights/yggdrasil): MQTT broker that delivers playbooks from Insights to the host
- [rhc-worker-playbook](https://github.com/RedHatInsights/rhc-worker-playbook): Yggdrasil worker executing signed Ansible playbooks
- [rhc-worker-script](https://github.com/oamg/rhc-worker-script): Yggdrasil worker executing Python or Bash scripts from signed YAML files
- [insights-client](https://github.com/RedHatInsights/insights-client): The wrapper around Insights Core
- [insights-core](https://github.com/RedHatInsights/insights-core): The old Playbook verifier location (see `insights/client/apps/ansible/`)

## Development

Install and use:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
rhc-playbook-verifier --stdin < data/playbooks/bugs.yml
```

Lint:

```bash
dnf install pre-commit
pre-commit run -a
```

Test:

```bash
pip install -e .
python -m unittest discover python/tests/

pip install coverage
python -m coverage run -m unittest discover python/tests/
python -m coverage report
python -m coverage html
```

Test with [tmt](https://tmt.readthedocs.io/en/stable/index.html):

```bash
# test with fedora container
tmt run --all provision --how=container report --how=html

# test with fedora container, with dependencies preinstalled
podman image build -t verifier-fedora -f Containerfile-fedora
tmt run --all provision --how=container --image=localhost/verifier-fedora report --how=html

# test with ubi9 container, with dependencies preinstalled
dnf -y install subscription-manager
subscription-manager register
podman image build -t verifier-ubi9 -f Containerfile-ubi9
tmt run --all provision --how=container --image=localhost/verifier-ubi9 report --how=html
```

## Building

The Python verifier can be built as an RPM package.

```shell
# non-isolated build
dnf -y install rpmdevtools
make rpm

# isolated build
dnf -y install mock
gpasswd --add "$(whoami)" mock
newgrp mock  # or, log out and back in
make mock
```

## Contributing

This project is developed under the [MIT license](LICENSE).

See [CONTRIBUTING.md](CONTRIBUTING.md) to learn more about the contribution process, Conventional Commits and Developer Certificate of Origin.
