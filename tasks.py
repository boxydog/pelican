import os
import sys
from pathlib import Path
from shutil import which

from invoke import task

PKG_NAME = "pelican"
PKG_PATH = Path(PKG_NAME)
DOCS_PORT = os.environ.get("DOCS_PORT", 8000)
BIN_DIR = "bin" if os.name != "nt" else "Scripts"
PTY = os.name != "nt"
ACTIVE_VENV = os.environ.get("VIRTUAL_ENV", None)
VENV_HOME = Path(os.environ.get("WORKON_HOME", "~/virtualenvs"))
VENV_PATH = Path(ACTIVE_VENV) if ACTIVE_VENV else (VENV_HOME / PKG_NAME)
VENV = str(VENV_PATH.expanduser())
VENV_BIN = Path(VENV) / Path(BIN_DIR)

PYTHON = which("python")

TOOLS = ["pdm", "pre-commit", "psutil"]


def _get_pdm_path():
    return which("pdm") or VENV_BIN / "pdm"


def _get_precommit_path():
    return which("pre-commit") or VENV_BIN / "pre-commit"


def _get_coverage_path():
    return which("coverage")


@task
def docbuild(c):
    """Build documentation"""
    c.run(f"{VENV_BIN}/sphinx-build -W docs docs/_build", pty=PTY)


@task(docbuild)
def docserve(c):
    """Serve docs at http://localhost:$DOCS_PORT/ (default port is 8000)"""
    from livereload import Server

    server = Server()
    server.watch("docs/conf.py", lambda: docbuild(c))
    server.watch("CONTRIBUTING.rst", lambda: docbuild(c))
    server.watch("docs/*.rst", lambda: docbuild(c))
    server.serve(port=DOCS_PORT, root="docs/_build")


@task
def tests(c):
    """Run the test suite"""
    c.run(f"{PYTHON} -m pytest", pty=PTY)


@task
def coverage(c):
    """Generate code coverage of running the test suite."""
    c.run(f"{PYTHON} -m pytest --cov=pelican", pty=PTY)
    c.run(f"{PYTHON} -m coverage html", pty=PTY)


@task
def format(c, check=False, diff=False):
    """Run Ruff's auto-formatter, optionally with --check or --diff"""
    check_flag, diff_flag = "", ""
    if check:
        check_flag = "--check"
    if diff:
        diff_flag = "--diff"
    c.run(
        f"{VENV_BIN}/ruff format {check_flag} {diff_flag} {PKG_PATH} tasks.py", pty=PTY
    )


@task
def ruff(c, fix=False, diff=False):
    """Run Ruff to ensure code meets project standards."""
    diff_flag, fix_flag = "", ""
    if fix:
        fix_flag = "--fix"
    if diff:
        diff_flag = "--diff"
    c.run(f"{VENV_BIN}/ruff check {diff_flag} {fix_flag} .", pty=PTY)


@task
def lint(c, fix=False, diff=False):
    """Check code style via linting tools."""
    ruff(c, fix=fix, diff=diff)
    format(c, check=not fix, diff=diff)


@task
def tools(c):
    """Install tools in the virtual environment if not already on PATH"""
    for tool in TOOLS:
        if not which(tool):
            c.run(f"{PYTHON} -m pip install {tool}", pty=PTY)


@task
def precommit(c):
    """Install pre-commit hooks to .git/hooks/pre-commit"""
    precommt = _get_precommit_path()
    c.run(f"{precommt} install", pty=PTY)


@task
def setup(c):
    c.run(f"{PYTHON} -m pip install -U pip", pty=PTY)
    tools(c)
    pdm = _get_pdm_path()
    print(f"***** running {pdm} install", file=sys.stderr)  # noqa: T201
    c.run(f"{pdm} install -v", pty=PTY, echo=True)
    precommit(c)


@task
def update_functional_tests(c):
    """Update the generated functional test output"""
    c.run(
        f"bash -c 'LC_ALL=en_US.utf8 pelican -o {PKG_PATH}/tests/output/custom/ \
            -s samples/pelican.conf.py samples/content/'",
        pty=PTY,
    )
    c.run(
        f"bash -c 'LC_ALL=fr_FR.utf8 pelican -o {PKG_PATH}/tests/output/custom_locale/ \
            -s samples/pelican.conf_FR.py samples/content/'",
        pty=PTY,
    )
    c.run(
        f"bash -c 'LC_ALL=en_US.utf8 pelican -o \
            {PKG_PATH}/tests/output/basic/ samples/content/'",
        pty=PTY,
    )
