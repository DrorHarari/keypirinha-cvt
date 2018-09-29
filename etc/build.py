# The build.py script is assumed to be located in the package's etc folder
from pathlib import Path
import os
import zipfile

PACKAGE_NAME="Cvt"

ETC_FOLDER=Path(__file__).parent
PACKAGE_FOLDER=ETC_FOLDER.parent
PACKAGE_FILE=Path.joinpath(PACKAGE_FOLDER, f"{PACKAGE_NAME}.keypirinha-package")

zf = zipfile.ZipFile(PACKAGE_FILE,'w',zipfile.ZIP_DEFLATED)

# File to include in the package
os.chdir(PACKAGE_FOLDER)
zf.write('cvt.py')
zf.write('lib/safeeval.py')
zf.write('data/cvtdefs.json')
zf.write('cvt.py')
zf.write('cvt.ini')
zf.write('cvt.ico')
zf.write('LICENSE')
zf.close()
