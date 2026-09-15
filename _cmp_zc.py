'''Checks if the .zip is correct basically just a sanity check tool
prints out ok,diff or only in zip check so confirms if its correct for the lambda'''


import os
print('=== zip_check/rankerbot .py files vs source ===')
import difflib
norm = lambda s: s.replace('\r\n','\n').replace('\r','\n')
for root, dirs, files in os.walk('zip_check/rankerbot'):
    for f in files:
        if f.endswith('.py') and '__pycache__' not in root:
            zpath = os.path.join(root, f)
            spath = zpath.replace('zip_check/', '', 1)
            if os.path.exists(spath):
                zdata = open(zpath, encoding='utf-8').read()
                sdata = open(spath, encoding='utf-8').read()
                if norm(zdata) != norm(sdata):
                    print(f'DIFF {spath}')
                else:
                    print(f'OK   {spath}')
            else:
                print(f'ONLY_IN_ZIP_CHECK {zpath}')
