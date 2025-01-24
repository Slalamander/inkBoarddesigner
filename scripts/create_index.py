import json
from pathlib import Path

# import inkBoard
# from inkBoard import constants
# from inkBoard.types import manifestjson, platformjson

import inkBoarddesigner
# import PythonScreenStackManager


def gather_folders(base_folder) -> list[Path]:
    folders = []

    for p in Path(base_folder).iterdir():
        if p.is_dir(): folders.append(p)
    return folders

def create_integration_index():
    folder = constants.DESIGNER_FOLDER / "integrations"
    int_folders = gather_folders(folder)
    integration_index = {}
    for p in int_folders:
        manifest_file = p / "manifest.json"
        if not manifest_file.exists():
            continue

        with open(manifest_file) as file:
            d = manifestjson(**json.load(file))
            integration_index[p.name] = d["version"]
    return integration_index

def create_platform_index():
    folder = constants.DESIGNER_FOLDER / "platforms"
    int_folders = gather_folders(folder)
    platform_index = {}
    for p in int_folders:
        platform_file = p / "platform.json"
        if not platform_file.exists():
            continue

        with open(platform_file) as file:
            d = platformjson(**json.load(file))
            platform_index[p.name] = d["version"]
    return platform_index

if __name__ == "__main__":
    # folder = constants.DESIGNER_FOLDER / "integrations"

    index = {
        # "inkBoard": inkBoard.__version__,
        # "PythonScreenStackManager": PythonScreenStackManager.__version__,
        "inkBoarddesigner": inkBoarddesigner.__version__,
        "platforms": create_platform_index(),
        "integrations": create_integration_index()
        }

    print(index)
    with open(Path(__file__).parent.parent / "index.json", "w") as file:
        json.dump(index,file,indent=4)