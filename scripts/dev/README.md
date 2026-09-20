# Development scripts

Ad-hoc helpers used while building and wiring up the Meta integration. They are
**not** part of the application, **not** run by CI, and several need real
credentials and a live WhatsApp number to do anything.

They previously lived in `src/`, where three of them were named `test_*.py`.
That shadowed the real test modules of the same name: `tests/run_tests.py` put
`src/` on `sys.path` and then discovered tests by bare module name, so
`test_whatsapp_integration` resolved to the script here rather than the suite —
and this one fails on import, which aborted the whole run. Moving them out is
what fixes that properly.

| Script | What it does | Needs |
|---|---|---|
| `verify_meta_setup.py` | Checks a Meta app's token, phone number ID and webhook config | Live credentials |
| `find_phone_number_id.py` | Looks up the phone number ID for a WhatsApp Business account | Live credentials |
| `deploy_whatsapp.py` | Deployment helper | Live credentials |
| `currency_demo.py` | Prints example conversions from `CurrencyConverter` | Network |
| `test_webhook.py` | Minimal Flask app for eyeballing raw webhook payloads | — |
| `test_memory.py` | Manual exercise of `ConversationMemory` | — |
| `test_whatsapp_integration.py` | **Broken.** Imports `twilio_whatsapp_integration`, which does not exist in this repository — presumably left over from a Twilio-based version | — |
| `start_whatsapp_bot.bat` | Windows launcher | — |

Run them from the repository root, e.g.:

```bash
python scripts/dev/currency_demo.py
```

The real test suite is in `tests/` and runs with `python -m pytest tests/`.
