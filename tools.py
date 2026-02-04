#coding=gbk
# 哈哈啥开发阶段
import os

def mkdir(dirname):
    dirname=dirname.replace("/","\\")
    if dirname.find("\\") == -1:
        os.mkdir(dirname)
        return
    lst=dirname.split("\\")
    destDir=""
    if lst[0].endswith("\\"):
        destDir = lst[0] + lst[1]
    else:
        destDir = lst[0] + "\\" + lst[1]
    
    if not os.path.exists(destDir):
        os.mkdir(destDir)
    for n in lst[2:]:
        destDir=os.path.join(destDir,n)
        if not os.path.exists(destDir):
            os.mkdir(destDir)
    
    
