#coding:gbk
import tools,common
import re
import os
from xml.dom import minidom
from xml.dom import Node
from PIL import Image, ImageFile
import shutil
#AXMLJAR="AXMLPrinter2.jar"
def Readunzip(filename,dest,destPath):
    d={}
    cmd="java -jar exec\\AXMLPrinter2.jar %s"%(dest+"/AndroidManifest.xml")
    f=os.popen(cmd)
    filelist=[]
    imglist={}
    imgsizes=[]
    content=""
    for line in f.readlines():
        content+=line
    #print content
    doc=minidom.parseString(content)
    #print root.attributes
    root=doc.documentElement
    #print root.attributes['xmlns:android'].value
    #print root.attributes['android:versionCode'].value
    pkg=root.attributes['package'].value
    d["PkgVersion"]=root.attributes['android:versionName'].value
    f.close()
    for root,dirs,files in os.walk(dest):
        for file in files:
            path=root+"\\"+file
            path=path.split(dest+"\\")[1]
            filelist.append(path)
    metafile=os.path.join(dest,"META-INF\MANIFEST.MF")
    f=open(metafile)
    if destPath!=".":
        if not os.path.exists(destPath):#如果不存在目的路径，则创建一个
            tools.mkdir(destPath)
    destFullPath=os.path.join(destPath,os.path.basename(filename))
    for line in f:
        if line.__contains__("Name:"):
            value=line.split("Name:")[1]
            value=value.strip()
            try:
                img=Image.open(os.path.join(dest,value))
                imgsizes.append(img.size)
                imglist[value]=img.size
                del img
            except:
                pass
    f.close()
    d["PkgFileList"]=' '.join(filelist)
    d["PkgKeyInfo"]=pkg.decode("utf-8","replace").encode("gbk","replace")+d["PkgVersion"]
    size = tools.calc_screen_size(imgsizes)
    d["PkgHintResolution"]=""
    if size:
        d['PkgResolution'] = '%s*%s' % size
        d["PkgHintResolution"]=d['PkgResolution']
    for item in imglist.items():
        if item[1]==size:
            icon_src_path = dest + os.path.splitext(filename)[1]
            icon_full_path = destFullPath + 'hint.'+item[0].split(".")[-1]
            shutil.copyfile(dest+"/"+item[0],icon_full_path)
            d["PkgHintPath"]=icon_full_path
            d["PkgHintSize"] = common.GetPKg_size(icon_full_path)
            d["PkgHintInfo"] = str(d["PkgHintPath"])+","+str(d["PkgHintResolution"])+","+str(d["PkgHintSize"])
    return d
def analyse(filename,destPath):
    d={}
    dirname=os.path.dirname(filename)
    filelist=[]
    name=common.GetPkg_NameWithNoExt(filename)
    dest=dirname+"/"+name
    tools.unzip_7z(filename,dest)
    d=Readunzip(filename,dest,destPath)
    try:
        d['PkgInstallOK']=1
        d['FileSize']=common.GetPKg_size(filename)
        d['PkgCatalog']="游戏|软件" 
        d['PkgKeyTime']=common.GetPKg_Keytime(filename)
        d['PkgFileType']=common.GetPkg_FileType(filename)
        d['PkgFileName']=common.GetPkg_FileName(filename)
        d['PkgHashCode']=common.GetPKg_Hash(filename)
        d["PkgKeyInfo"]+=d['FileSize']
    except:
        d['PkgInstallOK']=0
    tools.deltree(dirname+"/"+name)
    return d
         
def _test():
    import sys
    destPath=""
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "测试数据/apk/1B09E4E7909EEC6219510290C21CACFB_c01c2f2612b999b9ca1a3f67a1f75ce2.apk"
        destPath=os.path.join(common.OutDir,os.path.dirname(filename .replace(":","")))
    d = analyse(filename,destPath)
    for k, v in d.items():
        print (k, ":", v)

if __name__ == "__main__":
    _test()
