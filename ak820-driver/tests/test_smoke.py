import ak820


def test_package_imports():
    assert ak820.__version__


def test_device_id_is_the_wired_board():
    assert ak820.DEVICE_ID == "ak820_wired"
