# keras-team__keras-22316

## Problem

`Function.operations` include operations used to compute inputs
`Function` objects created with inputs that are the result of other operations include these operations in `Function.operations` even though these operations are not a part of the `Function`s computation graph.

Example

```python
import keras
from keras import Function

x = keras.Input(batch_shape=(), name="x")
y = x**2
z = y + 1
func = Function(y, z)
print(func.operations)
# [<InputLayer name=x, built=True>, <Operation name=power>, <Operation name=add>]
```

I don't believe there's any significant performance penalty in running the computation graph, but it can lead to confusing situations when crawling a `Model`s computation graph via `clone_model`. A work-around is to clone the model with fresh inputs first.

```python
from keras.models import clone_model

model = keras.Model(y, z)
print(model.operations) # same as above
model = clone_model(model, keras.Input(batch_shape=y.shape, dtype=y.dtype), lambda op: op)
print(model.operations) # [<InputLayer name=input_layer, built=True>, <Operation name=add>]
```

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
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.keras-team_1776_keras-22316@sha256:2a85415e1bcc6b0e03d08d36e0d922d9428d4b4fc0b6299dadf4c36d9f6a6520 -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''keras/src/ops/function_test.py'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
