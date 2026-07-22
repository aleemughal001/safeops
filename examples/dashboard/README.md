# SafeOps Dashboard Examples

This directory contains sample dashboard artifacts for the SafeOps demo.

- `sample-incident-cockpit.html` — static example of the redesigned Tabler-based Incident Cockpit.

The real generated cockpit is created locally during the demo at:

```text
/tmp/safeops-demo/incident-cockpit.html
```

The investor package copy is created at:

```text
/tmp/safeops-demo/investor-demo-package/incident-cockpit.html
```

Use this command after running the investor demo:

```bash
python3 -m http.server 8088 --directory /tmp/safeops-demo/investor-demo-package
```

Then open:

```text
http://127.0.0.1:8088/incident-cockpit.html
```
