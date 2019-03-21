from manifestforwork import expandImageList


def test_expand():
    imageListString = "I2PD44320001.tif:2|I2PD44320003.jpg|I2PD44320305.jpg:3"
    expected = ["I2PD44320001.tif", "I2PD44320002.tif", "I2PD44320003.jpg",
              "I2PD44320305.jpg", "I2PD44320306.jpg", "I2PD44320307.jpg"]

    expanded = expandImageList(imageListString)
    assert expanded == expected
