import os
from pathlib import Path


class ImageGroupResolver(object):
    """
    Fully qualifies an image group
    """

    def __init__(self, container: str, image_classifier: str):
        self._container = container
        self._image_classifier = image_classifier

    def ig_path(self, workRid: str, image_group_name: str) -> Path:
        """
        Fully qualifies a RID and a Path
        :param workRid:
        :param image_group_name:
        :return: fully qualified path to image group
        """
        pre_path = Path(self._container, workRid, self._image_classifier)
        v1path = Path(pre_path,  f"{workRid}-{image_group_name}")
        if not os.path.exists(v1path):
            v1path = Path(pre_path, image_group_name)
        return v1path
