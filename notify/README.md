# Optional workload notifications

Notifications are disabled unless `NOTIFY_PROVIDER_CONFIG` explicitly names a readable regular file. The tracked `provider-config.yaml` is a retired, empty configuration and is not included in Docker builds. Do not restore historical webhook credentials or commit replacement credentials.

The wrappers retain the existing provider id `dalfox`, including `sqlmap-notify.sh`. They pass their arguments as one input line to ProjectDiscovery Notify using an explicit `-provider-config` path. They do not read Notify's default provider configuration. An unset/empty variable skips notifications successfully; a missing or unreadable configured file fails with exit code 2. Notify's exit status is propagated. Automatic Notify update checks are disabled.

## Local runtime configuration

Keep a replacement provider configuration outside the repository and restrict access to the file. Its provider entries must use the existing `dalfox` id. Follow the [Notify provider configuration documentation](https://github.com/projectdiscovery/notify#provider-config) for its format. No replacement endpoint or credential is supplied here.

For a locally built image, explicitly mount the file read-only and pass its container path:

```bash
docker run --rm \
  --mount type=bind,src=/absolute/path/to/provider-config.local.yaml,dst=/run/notify/provider-config.yaml,readonly \
  --env NOTIFY_PROVIDER_CONFIG=/run/notify/provider-config.yaml \
  xhunt-tools:latest \
  ./notify/dalfox-notify.sh 'an authorized workload result'
```

This is an opt-in example that sends a real notification if run with valid credentials. Do not use real credentials for automated tests.

**AWS Batch status:** Current job definitions do not mount or materialize this provider file or set `NOTIFY_PROVIDER_CONFIG`. Batch notifications therefore remain disabled with these wrappers. A secure runtime delivery mechanism would need a separate design and explicit infrastructure changes; it is not implemented by this change.

The ignore files exclude local provider-config files, environment files and Git history from normal builds/commits. Ignore patterns are a safeguard, not a secret scanner. Existing images, old commits and other copied artifacts may still contain historical values. Rebuilding an image does not remove older image layers or published tags.

## Offline checks

From the repository root:

```bash
python -m unittest discover -s tests -p 'test_notifications.py' -v
```

The tests require Python 3 and Bash. On Windows, set `XHUNT_TEST_BASH` to the Git for Windows Bash executable if Bash is not on PATH. They prepend a fake `notify` executable to PATH and use inert local files; no scanner, real Notify binary, network request, Docker build, or notification is run.
