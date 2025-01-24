import os
import json
import logging
from pathlib import Path
import shutil
import tempfile
import zipfile

import inkBoard
from inkBoard import constants
from inkBoard.types import manifestjson, platformjson
from inkBoard.packaging import ZIP_COMPRESSION, ZIP_COMPRESSION_LEVEL, parse_version

import inkBoarddesigner
import PythonScreenStackManager

_LOGGER = inkBoard.getLogger("inkBoard-index")
_LOGGER.setLevel(logging.INFO)

INDEX_FOLDER = Path(__file__).parent
INDEX_FILE = INDEX_FOLDER / "index.json"
INTEGRATION_INDEX_FOLDER = INDEX_FOLDER / "integrations"
PLATFORM_INDEX_FOLDER = INDEX_FOLDER / "platforms"

if not INTEGRATION_INDEX_FOLDER.exists(): INTEGRATION_INDEX_FOLDER.mkdir()
if not PLATFORM_INDEX_FOLDER.exists(): PLATFORM_INDEX_FOLDER.mkdir()

if INDEX_FILE.exists():
    with open(INDEX_FILE, "r") as file:
        current_index = json.load(file)
else:
    current_index = {
        "inkBoard": inkBoard.__version__,
        "PythonScreenStackManager": PythonScreenStackManager.__version__,
        "inkBoarddesigner": inkBoarddesigner.__version__,
        "platforms": {},
        "integrations": {},
        }

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

        if (not (INTEGRATION_INDEX_FOLDER / f"{p.name}.zip").exists()
                or p.name not in current_index["integrations"]
                or parse_version(d["version"]) > parse_version(current_index["integrations"][p.name])):
            create_integration_zip(p)
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
        
        if (not (PLATFORM_INDEX_FOLDER / f"{p.name}.zip").exists()
                or p.name not in current_index["platforms"]
                or parse_version(d["version"]) > parse_version(current_index["platforms"][p.name])):
            create_platform_zip(p)
    return platform_index

##for the zips, would they only be for inkBoard, and not the designer?
##I.e. should the zips not hold any data that would be omitted when downloading
##I think, for now, yes. -> also base installer handles the installation anyways so only the downloading really matters

##If so, omit from integrations: designer.py/designer folder
##from platforms: any of the manual files.
##packge_files folder will be included, but should only be unpacked based on prompt input
##readme is omitted as it should be in the docs anyways
##always omit __pycache__

def ignore_files(src, names):
    """Returns a list with files to not copy for `shutil.copytree`

    Parameters
    ----------
    parentbase_folder : Path
        The base folder being copied from
    src : str
        source path, passed by `copytree`
    names : list[str]
        list with file and folder names, passed by `copytree`
    ignore_in_baseparent_folder : set, optional
        Set with filenames to ignore (i.e. not copy), _Only if_ the parent folder of `src` is `base_ignore_folder`, by default {}

    Returns
    -------
    _type_
        _description_
    """        

    # ignore_set = {"__pycache__"}
    # if Path(src).parent == parentbase_folder:
    #     ignore_set.update(ignore_in_baseparent_folder)

    return {"__pycache__"}

def create_integration_zip(integration_folder: Path):

    ##As per packaging: first create temp directory
    ##When that is done, put all files in there into the zipfile

    with tempfile.TemporaryDirectory(dir=str(INTEGRATION_INDEX_FOLDER)) as tempdir:
        name = integration_folder.name
        print(f"Gathering integration {name}")
        shutil.copytree(
            src = integration_folder,
            dst= Path(tempdir) / name,
            ignore=lambda *args: ("__pycache__","emulator.json", "designer", "designer.py")
        )

        print(f"Zipping up integration {name}")
        with zipfile.ZipFile(INTEGRATION_INDEX_FOLDER / f"{name}.zip", 'w', ZIP_COMPRESSION, compresslevel=ZIP_COMPRESSION_LEVEL) as zip_file:
            for foldername, subfolders, filenames in os.walk(tempdir):
                _LOGGER.verbose(f"Zipping contents of folder {foldername}")
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    zip_file.write(file_path, os.path.relpath(file_path, tempdir))
                for dir in subfolders:
                    dir_path = os.path.join(foldername, dir)
                    zip_file.write(dir_path, os.path.relpath(dir_path, tempdir))
        print(f"Succesfully packaged integration {name}")
    return

def create_platform_zip(platform_folder: Path):
    
    with tempfile.TemporaryDirectory(dir=str(INTEGRATION_INDEX_FOLDER)) as tempdir:
        name = platform_folder.name
        print(f"Gathering platform {name}")
        shutil.copytree(
            src = platform_folder,
            dst= Path(tempdir) / name,
            ignore=lambda *args: ("__pycache__","designer.py", "designer")
        )

        print(f"Zipping up platform {name}")
        with zipfile.ZipFile(PLATFORM_INDEX_FOLDER / f"{name}.zip", 'w', ZIP_COMPRESSION, compresslevel=ZIP_COMPRESSION_LEVEL) as zip_file:
            for foldername, subfolders, filenames in os.walk(tempdir):
                _LOGGER.verbose(f"Zipping contents of folder {foldername}")
                for filename in filenames:
                    file_path = os.path.join(foldername, filename)
                    zip_file.write(file_path, os.path.relpath(file_path, tempdir))
                for dir in subfolders:
                    dir_path = os.path.join(foldername, dir)
                    zip_file.write(dir_path, os.path.relpath(dir_path, tempdir))
        print(f"Succesfully packaged platform {name}")
    return

if __name__ == "__main__":
    index = {
        "inkBoard": inkBoard.__version__,
        "PythonScreenStackManager": PythonScreenStackManager.__version__,
        "inkBoarddesigner": inkBoarddesigner.__version__,
        "platforms": create_platform_index(),
        "integrations": create_integration_index()
        }

    ##May actually put this in a different repo;
    ##inkBoard-index or something
    ##Which would hold all the zip files too
    ##Would have to see if that is allowed per github rules but it seems so
    ##If so, generated zip files should be compressed.
    print(index)
    with open(Path(__file__).parent / "index.json", "w") as file:
        json.dump(index,file,indent=4)