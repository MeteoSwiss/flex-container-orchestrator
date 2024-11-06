flex-container-orchestrator
===========================

The flex-container-orchestrator manages the event driven workflow Flexpart IFS workflow, based on events from Aviso. The repo coordinates both flexprep (pre-processing of raw IFS data) and flexpart-ifs containers, ensuring all required lead time data is processed before launching Flexpart.

===============
Getting started
===============

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

    $ poetry run python3 flex_container_orchestrator/main.py  --date {date} --time {time} --step {step} --location {location}    

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

---------------------------------------------------
Setup dev environment - Meteoswiss environment only
---------------------------------------------------

Instead of running the steps below manually, you can install `mchbuild` and then
install, test and run the application:

.. code-block:: console

    $ pipx install mchbuild
    $ cd flex-container-orchestrator
    $ mchbuild local.build local.test
    $ mchbuild local.run

Try it out at and stop it with Ctrl-C. More information can be found in :file:`.mch-ci.yml`.

----------------------
Generate documentation
----------------------

.. code-block:: console

    $ poetry run sphinx-build doc doc/_build

Then open the index.html file generated in *flex-container-orchestrator/build/sphinx/html*


.. HINT::
   All **poetry run** prefixes in the commands can be avoided if running them within the poetry shell
