import nbformat
from pathlib import Path
from tools.test_colab import extract_urls


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
