import os, sys
def resource_path(*parts):

    here = os.path.dirname(__file__)
    # Последний шанс: вернуть путь рядом с модулем (и пусть ошибка будет говорящей)
    return os.path.join(here, *parts)