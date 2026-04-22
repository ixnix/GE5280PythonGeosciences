from tools.build_colab import (
    build_raw_url,
    build_colab_open_url,
    rewrite_code_string_paths,
    rewrite_markdown_paths,
)


def test_build_raw_url_data_file():
    assert build_raw_url(7, "data/earthquake.txt") == (
        "https://raw.githubusercontent.com/ixnix/GE5280PythonGeosciences/"
        "main/module_7/data/earthquake.txt"
    )


def test_build_raw_url_img_file():
    assert build_raw_url(1, "img/filesystem.png") == (
        "https://raw.githubusercontent.com/ixnix/GE5280PythonGeosciences/"
        "main/module_1/img/filesystem.png"
    )


def test_build_colab_open_url():
    assert build_colab_open_url(13, "13_Cartopy.ipynb") == (
        "https://colab.research.google.com/github/ixnix/"
        "GE5280PythonGeosciences/blob/main/colab/module_13/13_Cartopy.ipynb"
    )


def test_rewrite_double_quoted_data_path():
    src = 'df = pd.read_csv("data/earthquake.txt")'
    out = rewrite_code_string_paths(src, module=6)
    assert out == (
        'df = pd.read_csv("https://raw.githubusercontent.com/ixnix/'
        'GE5280PythonGeosciences/main/module_6/data/earthquake.txt")'
    )


def test_rewrite_single_quoted_img_path():
    src = "Image(filename='img/foo.png')"
    out = rewrite_code_string_paths(src, module=1)
    assert "module_1/img/foo.png" in out
    assert "'https://raw" in out


def test_rewrite_leaves_unrelated_strings_alone():
    src = "x = 'hello world'\nfn = 'output.csv'"
    out = rewrite_code_string_paths(src, module=7)
    assert out == src


def test_rewrite_leaves_writes_and_non_data_paths_alone():
    src = 'with open("output.csv", "w") as f: pass'
    out = rewrite_code_string_paths(src, module=7)
    assert out == src


def test_rewrite_handles_nested_subdirs():
    src = "x = 'data/sub/nested.csv'"
    out = rewrite_code_string_paths(src, module=8)
    assert "module_8/data/sub/nested.csv" in out


def test_rewrite_multiple_occurrences():
    src = 'a = "data/one.csv"; b = "img/two.png"'
    out = rewrite_code_string_paths(src, module=9)
    assert "module_9/data/one.csv" in out
    assert "module_9/img/two.png" in out


def test_rewrite_markdown_image():
    src = "Here's a picture:\n\n![diagram](img/foo.png)\n"
    out = rewrite_markdown_paths(src, module=7)
    assert "module_7/img/foo.png" in out
    assert "![diagram](https://raw" in out


def test_rewrite_markdown_data_link():
    src = "See [data](data/things.csv) for details."
    out = rewrite_markdown_paths(src, module=8)
    assert "module_8/data/things.csv" in out


def test_rewrite_html_img_tag_double_quoted():
    src = '<img src="img/bar.jpg" width="300">'
    out = rewrite_markdown_paths(src, module=1)
    assert 'src="https://raw' in out
    assert "module_1/img/bar.jpg" in out


def test_rewrite_html_img_tag_single_quoted():
    src = "<img src='img/bar.jpg'>"
    out = rewrite_markdown_paths(src, module=1)
    assert "src='https://raw" in out


def test_rewrite_markdown_leaves_prose_alone():
    src = "The data/ folder contains CSV files."
    out = rewrite_markdown_paths(src, module=7)
    assert out == src
