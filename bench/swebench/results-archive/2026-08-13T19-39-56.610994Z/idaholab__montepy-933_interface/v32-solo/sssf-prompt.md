# idaholab__montepy-933_interface

## Problem

Cannot nullify Cell.universe
## Bug Description

A cell's universe attribute cannot be set to `None` or deleted, essentially forcing `Cell.universe` to always be set to something once it has been set.

A new `Cell` is instantiated with a null universe attribute.


## To Reproduce

<!-- A short code snippet of what you have ran. Please change or remove any specific values or anything that can't be public. For example: --> 

``` python
>>> import montepy
>>> c = montepy.Cell("1 0 +1 imp:p=0")
>>> c.universe is None
True
>>> c.universe = None
TypeError
>>> del c.universe
AttributeError
```

## Error Message 

First error:

<details closed> 

``` python
>>> c.universe = None
Traceback (most recent call last):
  File "<python-input-2>", line 1, in <module>
    c.universe = None
    ^^^^^^^^^^
  File "./montepy/mcnp_object.py", line 49, in wrapped
    add_line_number_to_exception(e, self)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "./montepy/exceptions.py", line 235, in add_line_number_to_exception
    raise error
  File "./montepy/mcnp_object.py", line 41, in wrapped
    return func(*args, **kwargs)
  File "./montepy/mcnp_object.py", line 150, in __setattr__
    descriptor.__set__(self, value)
    ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "./montepy/mcnp_object.py", line 49, in wrapped
    add_line_number_to_exception(e, self)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
  File "./montepy/exceptions.py", line 259, in add_line_number_to_exception
    raise error.with_traceback(trace)
  File "./montepy/mcnp_object.py", line 41, in wrapped
    return func(*args, **kwargs)
  File "./montepy/cell.py", line 258, in universe
    raise TypeError("universe must be set to a Universe")
TypeError: universe must be set to a Universe

Error came from CELL: 1, mat: 0, DENS: None from an unknown file.
```
</details>

Second error:

<details closed>

``` python
>>> del c.universe
Traceback (most recent call last):
  File "<python-input-5>", line 1, in <module>
    del c.universe
        ^^^^^^^^^^
AttributeError: property 'universe' of 'Cell' object has no deleter
```
</details>

## Version

 - Version 1.3.0

## Interface

Type: Function
Name: universe
Path: montepy/cell.py
Input: self
Output: Universe or None
Description: Returns the current universe assigned to this cell. Use this to access or reset a cell's universe; setting it to None or deleting it resets the assignment to the default (universe 0) if the cell is within a problem, or clears it entirely if not.

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
docker run --rm -v "$PWD":/testbed -w /testbed --user "$(id -u):$(id -g)" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 --entrypoint bash swerebench/sweb.eval.x86_64.idaholab_1776_montepy-933_interface@sha256:d79f83f33b0f25749596dd0038adecb80e9b443300200890dca0f6d23488567c -lc 'source /opt/conda/bin/activate testbed && python -m pytest -p no:cacheprovider '\''tests/test_universe.py'\'' '\''tests/test_universe_integration.py'\'''
```

Read this before you trust a green run: the tests that command selects ALREADY
PASS in this checkout, unchanged, and they do NOT cover the task above. A
"passed" line from them is the state of the tree you were handed, not evidence
of anything you did. They are a regression check only. The behaviour the hidden
suite judges is not asserted anywhere in this tree yet — the test that proves
it is a test YOU write.
