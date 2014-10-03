# `tar_scm` testing

## Unit tests

Run the unit test suite via:

    python tests/test.py

The output may become easier to understand if you uncomment the
'failfast' option in `test.py`.  This requires Python 2.7, however.
You may also find that the buffered `STDOUT` from test failures gets
displayed to the screen twice - once before the test failure (and
corresponding stacktrace), and once after; in which case just grep for
`/^FAIL: /` in the output and start reading from there.

If you want to narrow the tests being run, to speed up testing during
development, you can provide command-line arguments:

    # only run the 'plain' and 'subdir' git tests
    python tests/test.py test_plain test_subdir

    # run all git tests matching the regexp /subdir/
    python tests/test.py /subdir/

Currently this filtering only applies to the git tests, but you can
easily tweak `test.py` to change that.

Note that for each test, a fresh `svn`/`git`/`hg`/`bzr` repository is
created, and `tar_scm` is invoked one *or more* times in a faked-up
OBS source service environment.  Whenever `tar_scm` invokes the VCS
for which its functionality is being tested, through modification of
`$PATH` it actually invokes `scm-wrapper`, which logs the VCS
invocation before continuing.

## PEP8 checking

There's also a `pep8` rule for checking
[PEP8](http://legacy.python.org/dev/peps/pep-0008/) compliance:

    make pep8

## Running all tests.

You can run both sets of tests together via:

    make check
