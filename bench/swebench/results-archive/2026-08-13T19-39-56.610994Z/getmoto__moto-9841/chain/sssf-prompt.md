# getmoto__moto-9841

## Problem

Suport for cloudformation AWS::KMS::Alias resource does not support Full ARN as TargetKeyId
Hi Team, 

we've recently upgraded moto from 5.1.21 to 5.1.22 (renovate) and our testing framework broke with the following error:

```
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <moto.kms.models.KmsBackend object at 0x10b3b1fd0>
target_key_id = 'arn:aws:kms:ap-southeast-2:123456789012:key/26fe9350-25da-4bac-91f8-796abadaee5e'
alias_name = 'alias/test-alias'

    def update_alias(self, target_key_id: str, alias_name: str) -> Alias:
        for key in self.keys.values():
            if alias_name in key.aliases and target_key_id != key.id:
                # Updating the Key that this is an alias of
                alias = key.aliases.pop(alias_name)
                self.keys[target_key_id].aliases[alias_name] = alias
                return alias
        # TargetKeyId hasn't changed - nothing to update
>       return self.keys[target_key_id].aliases[alias_name]
               ^^^^^^^^^^^^^^^^^^^^^^^^
E       KeyError: 'arn:aws:kms:ap-southeast-2:123456789012:key/26fe9350-25da-4bac-91f8-796abadaee5e'

.venv/lib/python3.14/site-packages/moto/kms/models.py:521: KeyError
```

Upon investigation of the release notes and code, this seems related to:
- https://github.com/getmoto/moto/pull/9745
- https://github.com/getmoto/moto/issues/9724

where support for `AWS::KMS::Alias` was added to the cloudformation sub-module, which seem to only accept a KeyId and not the full ARN.

The full ARN is officially supported by AWS (https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-kms-alias.html), support should probably be added to moto as well. 

For now, I'll downgrade the moto version back to 5.1.21 to pass my unit / integration tests.

## Definition of done

Change the production code in this repository so the described behaviour is
correct.

Work exactly as you normally do: write tests that express the required
behaviour, then make them pass. A separate held-out test suite, written by the
project's maintainers and which you will never see, is the final judge.

## Where to put tests

Put new tests in the files or directories the test command below already
targets, so your own runs execute them.

Your test edits are removed from the diff before the held-out suite runs, so
they cannot affect the verdict either way — they are your feedback loop, not
the grade. Only your production-code changes are judged. This means a test
that merely asserts whatever your implementation happens to do buys nothing:
make the tests encode what the TASK requires.

## Running the tests

This checkout has NO dependencies installed, so a bare `pytest` fails with
`ModuleNotFoundError`. Run this exact command from the repo root — it executes
inside an image that has the dependencies, with your working tree mounted so it
tests YOUR edits:

```
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.getmoto_1776_moto-9841@sha256:25cb9ea1e18acfadbf1a8b4a5746153746cd994e138c01f295d83813ab63a171 -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''tests/test_kms/test_kms.py'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
