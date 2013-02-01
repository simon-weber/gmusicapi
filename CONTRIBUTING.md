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
* `git clone https://github.com/simon-weber/Unofficial-Google-Music-API.git`
* `cd Unofficial-Google-Music-API/`
* `virtualenv --no-site-packages venv-gmapi`
* `source venv-gmapi/bin/activate`
* `pip install -e .` this installs the package as editable; changes to the source are reflected when running 
* `git checkout develop`
* hack away
* `python -m gmusicapi.test.integration_test_api`
* `deactivate` when you're finished
