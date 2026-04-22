from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_notebook_path():
    return FIXTURES / "sample_notebook.ipynb"
