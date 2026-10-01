import pytest

import praxis
from praxis.cli import main


def test_package_has_version():
    assert isinstance(praxis.__version__, str)


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"praxis {praxis.__version__}"


def test_cli_no_args_prints_help(capsys):
    assert main([]) == 0
    assert "usage: praxis" in capsys.readouterr().out
