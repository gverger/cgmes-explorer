import base64
from pathlib import Path
import yaml


def datauri(filepath: str):
    with open(filepath, "rb") as fc:
        base64_utf8_str = base64.b64encode(fc.read()).decode("utf-8")

        ext = filepath.split(".")[-1]
        return f"data:image/{ext};base64,{base64_utf8_str}"


Images = dict()
with open("visu/assets/icons.yml", "r") as f:
    content = yaml.safe_load(f)
    for k, v in content["types"].items():
        Images[k] = v


def images(el_type: str):
    if el_type in Images:
        return datauri((Path("visu/assets") / Images[el_type]).as_posix())
    return Images.get(el_type, None)
