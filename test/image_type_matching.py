import unittest

from v_m_b.image.generateManifest import is_BUDA_Matching_file_ext

tests:[] = [
    ['asdfgdfg.notther', 'NOT', False],
    ['asdfgdfg.jpg', 'NOT', False],
    ['asdfgdfg.TIF', 'not', False],
    ['asdfgdfg.jpG', 'TIF', False],
    ['asdfgdfg.JpG', 'tiff', False],
    ['asdfgdfg.TIF', 'TIFF', True],
    ['asdfgdfg.TiFF', 'TIFF', True],
    ['asdfgdfg.Tif', 'JPEG', False],
    ['asdfgdfg.JPEG', 'JPEG', True],
    ['asdfgdfg.jpeG', 'JPEG', True],
    ['asdfgdfg.jpG', 'JPEG', True],
    ['asdfgdfg.JPG', 'JPEG', True],
    ['', None, False],
    [None, '', False],
    [None, None, False]
]


class MyTestCase(unittest.TestCase):
    def test_BUDA_Image_matching(self):
        [self.assertEqual(is_BUDA_Matching_file_ext(x[0], x[1]), x[2], f"{x[0]} {x[1]}") for x in tests]  # add assertion here


if __name__ == '__main__':
    unittest.main()
