from tools.build_colab import build_raw_url, build_colab_open_url


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
