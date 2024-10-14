===============
Getting started
===============

---------------------
Setup dev environment
---------------------

Instead of running the steps below manually, you can install `mchbuild` and then
install, test and run the application:

.. code-block:: console

    $ pipx install mchbuild
    $ cd flex-container-orchestrator
    $ mchbuild local.build local.test
    $ mchbuild local.run

Try it out at and stop it with Ctrl-C. More information can be found in :file:`.mch-ci.yml`.

------------------------------------------------
Install dependencies & start the project locally
------------------------------------------------

1. Enter the project folder:

.. code-block:: console

    $ cd flex-container-orchestrator

2. Install packages

.. code-block:: console

    $ poetry install

3. Run the flex-container-orchestrator

.. code-block:: console

    $ poetry run uvicorn --port 8080 --reload flex_container_orchestrator.main:app

-------------------------------
Run the tests and quality tools
-------------------------------

1. Run tests

.. code-block:: console

    $ poetry run pytest

2. Run pylint

.. code-block:: console

    $ poetry run pylint flex_container_orchestrator


3. Run mypy

.. code-block:: console

    $ poetry run mypy flex_container_orchestrator


----------------------
Generate documentation
----------------------

.. code-block:: console

    $ poetry run sphinx-build doc doc/_build

Then open the index.html file generated in *flex-container-orchestrator/build/sphinx/html*


.. HINT::
   All **poetry run** prefixes in the commands can be avoided if running them within the poetry shell
