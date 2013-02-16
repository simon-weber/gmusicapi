.. _contributing:

Contributing to gmusicapi
=========================

Contributions of all sizes are appreciated!
The `issues list <https://github.com/simon-weber/Unofficial-Google-Music-API/issues>`__
on GitHub always has things to be done.

Development
-----------

Please make pull requests to the ``develop`` branch.
``master`` is currently used to hold the code of the most recent release.

Building the docs locally is straightforward.
First, make sure Sphinx is installed: ``pip install sphinx``.

Next, simply do ``cd gmusicapi/docs`` followed by ``make html``.

If there weren't any problems, the docs are now in ``build/html``.
You can serve them up locally with ``python -m SimpleHTTPServer``,
then view them in your web browser at ``http://127.0.0.1:8000/build/html/``.
