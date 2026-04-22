from unittest.mock import patch, Mock

import nbformat
from pathlib import Path
from tools.test_colab import extract_urls, check_url_reachable


def test_extract_urls_from_code_cell(tmp_path):
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell(
        'pd.read_csv("https://raw.githubusercontent.com/ixnix/GE5280Py'
        'thonGeosciences/main/module_7/data/earthquake.txt")'
    ))
    path = tmp_path / "n.ipynb"
    nbformat.write(nb, path)
    urls = extract_urls(path)
    assert any("raw.githubusercontent.com" in u for u in urls)


def test_extract_urls_from_markdown(tmp_path):
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_markdown_cell(
        "![badge](https://colab.research.google.com/assets/colab-badge.svg)\n"
        "[Open in Colab](https://colab.research.google.com/github/foo/bar/blob/main/x.ipynb)"
    ))
    path = tmp_path / "n.ipynb"
    nbformat.write(nb, path)
    urls = extract_urls(path)
    assert any("colab-badge.svg" in u for u in urls)
    assert any("colab.research.google.com/github/foo" in u for u in urls)


def test_extract_urls_deduplicates(tmp_path):
    nb = nbformat.v4.new_notebook()
    url = "https://raw.githubusercontent.com/a/b/main/c.csv"
    nb.cells.append(nbformat.v4.new_code_cell(f'x = "{url}"\ny = "{url}"'))
    path = tmp_path / "n.ipynb"
    nbformat.write(nb, path)
    urls = extract_urls(path)
    assert urls.count(url) == 1


def test_check_url_ok_head():
    resp = Mock(status_code=200)
    with patch("tools.test_colab.requests.head", return_value=resp) as mhead:
        assert check_url_reachable("https://x/y.csv") is True
        mhead.assert_called_once()


def test_check_url_falls_back_to_get_on_405():
    head_resp = Mock(status_code=405)
    get_resp = Mock(status_code=200)
    with patch("tools.test_colab.requests.head", return_value=head_resp), \
         patch("tools.test_colab.requests.get", return_value=get_resp) as mget:
        assert check_url_reachable("https://x/y.csv") is True
        mget.assert_called_once()


def test_check_url_404_is_false():
    resp = Mock(status_code=404)
    with patch("tools.test_colab.requests.head", return_value=resp):
        assert check_url_reachable("https://x/y.csv") is False


def test_check_url_retries_once_on_exception():
    import requests as _requests
    side_effects = [_requests.ConnectionError("flake"), Mock(status_code=200)]
    with patch("tools.test_colab.requests.head", side_effect=side_effects) as mhead:
        assert check_url_reachable("https://x/y.csv") is True
        assert mhead.call_count == 2
