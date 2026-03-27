import zipfile
zf = zipfile.ZipFile('dist/guild_packs-2.0.0-py3-none-any.whl')
test_files = [n for n in zf.namelist() if 'test_e2e' in n.lower()]
print("test_e2e files in wheel:", test_files)
convert_files = [n for n in zf.namelist() if 'test_convert' in n.lower()]
print("test_convert files in wheel:", convert_files)
all_test = [n for n in zf.namelist() if '/tests/' in n]
print("All test dir files in wheel:", all_test)
