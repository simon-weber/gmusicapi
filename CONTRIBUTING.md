## Submitting an issue 
The more details you can give, the better. The tail of your `gmusicapi.log` often has useful information, too.

## Submitting code 
Generally, the `develop` branch is used for upstream integration; when in doubt, make pull requests against it.

One exception: the docs are built dynamically against the current state of `master`, so doc-only improvements can use `master` directly.

### Checking out a dev environment
You can do this however you like, but I'd recommend [virtualenv](http://www.virtualenv.org/en/latest/):
* `git clone https://github.com/simon-weber/Unofficial-Google-Music-API.git`
* `cd Unofficial-Google-Music-API/`
* `virtualenv --no-site-packages venv-gmapi`
* `source venv-gmapi/bin/activate`
* `pip install -e .` this installs the package as editable; changes to the source are reflected when running 
* `git checkout develop`
* hack away
* `python -m gmusicapi.test.integration_test_api`
* `deactivate` when you're finished
