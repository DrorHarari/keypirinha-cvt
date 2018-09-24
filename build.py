import zipfile
zf = zipfile.ZipFile('Cvt.keypirinha-package','w',zipfile.ZIP_DEFLATED)
zf.write('lib/safeeval.py')
zf.write('data/cvtdefs.json')
zf.write('cvt.py')
zf.write('cvt.ini')
zf.write('cvt.ico')
zf.write('LICENSE')
zf.close()