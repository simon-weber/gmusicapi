## Submitting an issue 
The more details you can give, the better. The tail of your `gmusicapi.log` often has useful information, too.

## Building docs locally
[Sphinx](http://sphinx-doc.org/) is used to generate the docs, and they can be built locally if you'd like to view your edits.

First, get a dev environment set up (if you're unsure, there are steps below). Then, install Sphinx: `pip install sphinx`.

Building the docs requires make: `cd docs`, then `make html`.

If there weren't any problems, the docs are in `./build/html`. You can serve them up locally with `python -m SimpleHTTPServer`, then view them in your web browser at `http://127.0.0.1:8000/build/html/`.

## Submitting code 
Generally, the `develop` branch is used for upstream integration; when in doubt, make pull requests against it.

One exception: the docs are built dynamically against the current state of `master`, so doc-only improvements that still apply to the current release can use `master` directly. These kind of changes usually get merged into `develop` after a release.

### Checking out a dev environment
You can do this however you like, but generally you want to use [virtualenv](http://www.virtualenv.org/en/latest/):
* `$ git clone https://github.com/simon-weber/gmusicapi.git`
* `$ cd gmusicapi/`
* `$ virtualenv --no-site-packages venv-gmapi`
* `$ source venv-gmapi/bin/activate`
* `$ pip install -e .` # this installs the package as editable; changes to the source are reflected when running 
* `$ git checkout develop`
*  # hack away
* `$ python -m gmusicapi.test.run_tests` # (see the next section for more info)
* `$ deactivate` # when you're finished

### Running tests
###### See the beginning of test.run_tests for more information about environment variables to use
There are two main sets of tests: local tests and server tests. The tests are powered by [proboscis](https://pythonhosted.org/proboscis/) and are contained in the test module.

Running the local tests is easy. Inside a virtual environment:
* `$ python -m gmusicapi.test.run_tests --group=local`

The server tests are a bit more complicated, as they exercise the actual Google Music API. Before starting, you should be able to log in to each client (`Mobileclient`, `Webclient` and `Musicmanager`). In particular, the `Webclient` requires a Google account _without_ multi-factor authentication turned on (an app-specific password does not work!). The `Musicmanager` requires you to go through OAUTH:
* `from gmusicapi import Musicmanager`
* `Musicmanager.perform_oauth()`

The server tests also require a device ID. You can set the environment variable `GM_AA_D_ID` or enter your ID at the prompt. Setting either to 'mac' will use Mobileclient.FROM_MAC_ADDRESS. Some tests will fail if not using an Android device ID (use `Mobileclient.get_registered_devices()` to find the ID; strip out any leading `0x`).

Once you have all that set up, run the server tests:
* `$ python -m gmusicapi.test.run_tests --group=server`
or together with the local tests:
* `$ python -m gmusicapi.test.run_tests`

Many of the server tests require a subscription to Google Music All-Access. If you have a subscription, set the environment variable `GM_A` (to anything).


As there is experimental support for Python 3, it would be ideal to run the tests against all supported versions of Python. You can do this by using [tox](http://tox.testrun.org/):
* Install all supported versions of Python that you'd like to test (Python 2.7, 3.4 and 3.5 are currently tested with tox)
* **Outside** of a virtualenv, `$ pip install tox`
* Set the environment variables (as above)
* Run the tests: `$ tox` (this will create virtualenvs for you)
* If you don't want to test every single version in the compatibility matrix, you can run tox with `--skip-missing-interpreters`, which will test just the python versions that you have installed
