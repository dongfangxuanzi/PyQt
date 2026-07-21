# -*- coding: utf-8 -*-
'''
-------------------------------------------------------------------------------
Name:        fileutils.py
Purpose:     文件和目录相关操作处理的模块
Author:      wukan
Created:     2019-01-22
Copyright:   (c) wukan 2019
Licence:     GPL-3.0
-------------------------------------------------------------------------------
'''
import logging
import os
import shutil
import zipfile
import subprocess
import stat
import getpass
from typing import Optional, Union
import chardet
from ..common import filecheck
from .. import _
from ..common.encodings import UTF8_FILE_ENCODING, BINARY, ASCII_FILE_ENCODING, ANSI_FILE_ENCODING
from . import apputils, strutils
fileutils_logger = logging.getLogger(__name__)
_Checker = filecheck.FileTypeChecker()


def addRef(varname):
    return "${%s}" % varname


AG_SYSTEM_VAR_NAMES = []  # all AG System vars, with ${} syntax

AG_SYSTEM_VAR = "AG_SYSTEM"
AG_SYSTEM_VAR_REF = addRef(AG_SYSTEM_VAR)
AG_SYSTEM_VAR_NAMES.append(AG_SYSTEM_VAR_REF)

AG_SYSTEM_STATIC_VAR = "AG_SYSTEM_STATIC"
AG_SYSTEM_STATIC_VAR_REF = addRef(AG_SYSTEM_STATIC_VAR)
AG_SYSTEM_VAR_NAMES.append(AG_SYSTEM_STATIC_VAR_REF)

AG_APP_VAR = "AG_APP"
AG_APP_STATIC_VAR = "AG_APP_STATIC"

# _initAGSystemVars needs to be called to initialize the following two
# containers:
EXPANDED_AG_SYSTEM_VARS = {}  # ${varname} -> value (path)
# ${varname}, ordered from longest to shortest path value
AG_SYSTEM_VARS_LENGTH_ORDER = []


def _initAGSystemVars():
    if len(EXPANDED_AG_SYSTEM_VARS) > 0:
        return
    for v in AG_SYSTEM_VAR_NAMES:
        EXPANDED_AG_SYSTEM_VARS[v] = os.path.abspath(expandVars(v))
        AG_SYSTEM_VARS_LENGTH_ORDER.append(v)
    AG_SYSTEM_VARS_LENGTH_ORDER.sort(_sortByValLength)


def parameterizePathWithAGSystemVar(inpath):
    """
    Returns parameterized path if path starts with a known AG directory. Otherwise returns path
    as it was passed in.
    """
    _initAGSystemVars()
    path = inpath
    if not sysutils.isWindows():
        # ensure we have forward slashes
        path = path.replace("\\", "/")
    path = os.path.abspath(path)
    for varname in AG_SYSTEM_VARS_LENGTH_ORDER:
        varval = EXPANDED_AG_SYSTEM_VARS[varname]
        if path.startswith(varval):
            return path.replace(varval, varname)

    return inpath


def startsWithAgSystemVar(path):
    """Returns True if path starts with a known AG system env var, False otherwise."""
    for varname in AG_SYSTEM_VAR_NAMES:
        if path.startswith(varname):
            return True
    return False


def _sortByValLength(v1, v2):
    return len(EXPANDED_AG_SYSTEM_VARS[v2]) - len(EXPANDED_AG_SYSTEM_VARS[v1])


def make_dirs_for_file(filename):
    d = os.path.dirname(filename)
    if not os.path.exists(d):
        os.makedirs(d)


def create_empty_file(filename, ensure_dir_exist=False):
    f = None
    if ensure_dir_exist and not os.path.exists(filename):
        make_dirs_for_file(filename)
    with open(filename, "w") as f:
        f.write('')


def compareFiles(file1, file2, ignore=None):
    file1.seek(0)
    file2.seek(0)
    while True:
        line1 = file1.readline()
        line2 = file2.readline()
        if not line1:
            if not line2:
                return 0
            return -1
        if not line2:
            return -1
        if line1 != line2:
            if ignore is not None:
                if (line1.startswith(ignore) or line2.startswith(ignore)):
                    continue
            line1 = line1.replace(" ", "")
            line2 = line2.replace(" ", "")
            if line1 != line2:
                len1 = len(line1)
                len2 = len(line2)
                if ((abs(len1 - len2) == 1) and (len1 > 0) and (len2 > 0)
                        and (line1[-1] == "\n") and (line2[-1] == "\n")):
                    if len1 > len2:
                        longer = line1
                        shorter = line2
                    else:
                        shorter = line1
                        longer = line2
                    if ((longer[-2] == "\r") and (longer[:-2] == shorter[:-1])):
                        continue
                    if ((longer[-2:] == shorter[-2:]) and (longer[-3] == "\r") and (longer[:-3] == shorter[:-2])):
                        continue
                return -1


def expandKnownAGVars(value):
    return expandVars(value, includeEnv=False)


def expandVars(value, include_env=True):
    """Syntax: ${myvar,default="default value"}"""
    from activegrid import runtime
    sx = value.find("${")
    if sx >= 0:
        result = asString(value[:sx])
        endx = value.find("}")
        if endx > 1:
            default_value = None
            defsx = value.find(",default=\"")
            if sx < defsx < endx:
                varname = value[sx + 2:defsx]
                if value[endx - 1] == '"':
                    default_value = value[defsx + 10:endx - 1]
            if default_value is None:
                varname = value[sx + 2:endx]
            if varname == AG_SYSTEM_VAR:
                varval = runtime.appInfo.getSystemDir()
            elif varname == AG_SYSTEM_STATIC_VAR:
                varval = runtime.appInfo.getSystemStaticDir()
            elif varname == AG_APP_VAR:
                varval = runtime.appInfo.getAppDir()
            elif varname == AG_APP_STATIC_VAR:
                varval = runtime.appInfo.getAppStaticDir()
            else:
                if include_env:
                    varval = os.getenv(varname)
                else:
                    varval = None
            if ((varval is None) and (default_value is not None)):
                varval = default_value
            if varval is None:
                result += value[sx:endx + 1]
            else:
                result += varval
            return result + expandVars(value[endx + 1:])
    return value


def convertSourcePath(path, to, otherdir=None):
    fromname = "python"
    if to == 'python':
        fromname = "php"
    pythonnode = os.sep + fromname + os.sep
    ix = path.find(pythonnode)
    if ix < 0:
        ix = path.find(fromname) - 1
        if ((ix < 0) or (len(path) <= ix + 7)
                or (path[ix] not in ("\\", "/")) or (path[ix + 7] not in ("\\", "/"))):
            raise Exception(
                "Not in a %s source tree.  Cannot create file name for %s." % (fromname, path))
        if otherdir is None:
            return path[:ix + 1] + to + path[ix + 7:]
        return otherdir + path[ix + 7:]
    if otherdir is None:
        return path.replace(pythonnode, os.sep + to + os.sep)
    return otherdir + path[ix + 7:]


def visit(directory, files, extension, maxlevel=None, level=1):
    testdirs = os.listdir(directory)
    for thing in testdirs:
        fullpath = os.path.join(directory, thing)
        if (os.path.isdir(fullpath) and (maxlevel is None or level < maxlevel)):
            visit(fullpath, files, extension, maxlevel, level + 1)
        elif thing.endswith(extension):
            fullname = os.path.normpath(os.path.join(directory, thing))
            if fullname not in files:
                files.append(fullname)


def listFilesByExtensionInPath(path: Optional[list]=None, extension='.lyt', maxlevel=None):
    path = path or []
    retval = []
    for directory in path:
        visit(directory, retval, extension, maxlevel)
    return retval


def getFileLastModificationTime(filename):
    return os.path.getmtime(filename)


def findFileLocation(location, filename):
    i = filename.rfind(os.sep)
    if i > 0:
        filename = filename[:i]
    while location[0:2] == '..' and location[2:3] == os.sep:
        location = location[3:]
        i = filename.rfind(os.sep)
        filename = filename[:i]
    abspath = filename + os.sep + location
    return abspath


def getAllExistingFiles(files, basepath=None, forceForwardSlashes=False):
    """
    For each file in files, if it exists, adds its absolute path to the rtn list. If file is a
    dir, calls this function recursively on all child files in the dir.
    If basepath is set, and if the file being processed is relative to basedir, adds that
    relative path to rtn list instead of the abs path.
    Is this is Windows, and forceForwardSlashes is True, make sure returned paths only have
    forward slashes.
    """
    if isinstance(files, str):
        files = [files]
    rtn = []
    for file in files:
        if os.path.exists(file):
            if os.path.isfile(file):
                if basepath and hasAncestorDir(file, basepath):
                    rtn.append(getRelativePath(file, basepath))
                else:
                    rtn.append(os.path.abspath(str(file)))
            elif os.path.isdir(file):
                dircontent = [os.path.join(file, f) for f in os.listdir(file)]
                rtn.extend(getAllExistingFiles(dircontent, basepath))
    if forceForwardSlashes and sysutils.isWindows():
        new_rtn = []
        for f in rtn:
            new_rtn.append(f.replace("\\", "/"))
        rtn = new_rtn
    return rtn


def hasAncestorDir(file, parent):
    """Returns true if file has the dir 'parent' as some parent in its path."""
    return getRelativePath(file, parent) is not None


def getRelativePath(file, basedir):
    """
    Returns relative path from 'basedir' to 'file', assuming 'file' lives beneath 'basedir'. If
    it doesn't, returns None.
    """
    file = os.path.abspath(file)
    parent = os.path.abspath(basedir)
    if file == parent:
        return None
    if file.startswith(parent):
        return file[len(parent) + 1:]
    return None


def is_empty_dir(dir_path):
    if not os.path.isdir(dir_path):
        return False
    return not os.listdir(dir_path)


def zip_to(zipfilepath, basedir=None, files=None):
    """
    Zip all files in files and save zip as zipfilepath. If files is None, zip all files in
    basedir. For all files to be zipped, if they are relative to basedir, include the relative
    path in the archive.
    """
    if files is None and basedir is None:
        raise AssertionError("Either 'basedir' or 'files' must be set")
    if files is None:
        fileutils_logger.debug('Looking for files to zip in %s', basedir)
        files = getAllExistingFiles(basedir)
    else:
        # removes files that don't exist and gets abs for each
        files = getAllExistingFiles(files)
    if not files:
        fileutils_logger.debug("No files to zip, nothing to do")
        raise ValueError(_("No files to zip, nothing to do!"))
    with zipfile.ZipFile(zipfilepath, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        try:
            for file in files:
                arcname = None
                if basedir:
                    arcname = getRelativePath(file, basedir)
                if not arcname:
                    arcname = file
                    fileutils_logger.debug(
                        '%s: adding %s with arcname %s', zipfilepath, file, arcname)
                z.write(file, arcname)
        except Exception as ex:
            fileutils_logger.error('write arcname %s error:%s', zipfilepath, str(ex))


def unzip(zipfilepath, extractdir):
    """Unzip zipfilepath into extractdir."""
    z = zipfile.ZipFile(zipfilepath, mode="r")
    for info in z.infolist():
        filename = os.path.join(extractdir, info.filename)
        try:
            dir_ = os.path.dirname(filename)
            fileutils_logger.debug('Creating dir %s', dir_)
            os.makedirs(dir_)  # do we have to worry about permissions?
        except:
            pass
        if os.path.isdir(filename):
            continue
        fileutils_logger.debug(
            ('Writing arcfile %s to %s', info.filename, filename))
        with open(filename, "wb") as f:
            f.write(z.read(info.filename))


def copyFile(src, dest):
    """Copies file src to dest. Creates directories in 'dest' path if necessary."""
    destdir = os.path.dirname(dest)
    if not os.path.exists(destdir):
        os.makedirs(destdir)
    shutil.copy(src, dest)


def copyDir(src, dest):
    """Copies dir 'src' into dir 'dest'. Creates 'dest' if it does not exist."""
    shutil.copytree(src, dest)


def safe_remove(file):
    if not os.path.exists(file):
        return
    try:
        # 删除只读文件之前需要设置文件可写
        os.chmod(file, stat.S_IWRITE)
    except:
        pass
    if os.path.isfile(file):
        try:
            os.remove(file)
            fileutils_logger.debug('delete file %s success', file)
        except:
            pass
    elif os.path.isdir(file):
        try:
            shutil.rmtree(file)
        except:
            pass


def replaceToken(
    infilepath,
    tokens: Optional[dict] = None,
    outfilepath=None,
    delim='@@',
    use_env=False
):
    """
    @accepts str, dict, str, str, boolean
    Replaces tokens of form 'delim'<tokenname>'delim' in file at 'infilepath', using values in
    dict 'tokens'. If 'outfilepath' is set, writes output to 'outfilepath', if not set,
    overwrites original file. If 'useEnv' is True, adds os.environ to 'tokens'. This makes it
    possible to define an env var FOO=BLAH, and have @@FOO@@ be replaced with BLAH, without
    explicitly passing FOO=BLAH in 'tokens'. Note that entries in 'tokens' take precedence over
    entries in os.environ.
    """
    tokens = tokens or {}
    if use_env:
        for key, val in os.environ.items():
            # passed in tokens take precedence
            if not tokens.has_key(key):
                tokens[key] = val
    f = open(infilepath, "r")
    try:
        content = f.read()
    finally:
        if f:
            f.close()
    for token, value in tokens.items():
        content = content.replace("%s%s%s" % (delim, token, delim), str(value))
    if not outfilepath:
        outfilepath = infilepath
    f = open(outfilepath, "w")
    try:
        f.write(content)
    finally:
        if f:
            f.close()


def open_file_directory(file_path):
    """
    Opens the parent directory of a file, selecting the file if possible.
    """
    ret = 0
    err_msg = ''
    if apputils.is_windows():
        # Normally we can just run `explorer /select, filename`, but Python 2
        # always calls CreateProcessA, which doesn't support Unicode. We could
        # call CreateProcessW with ctypes, but the following is more robust.
        import ctypes
        import win32api

        ctypes.windll.ole32.CoInitialize(None)
        # Not sure why this is always UTF-8.
        pidl = ctypes.windll.shell32.ILCreateFromPathW(file_path)
        if 0 == pidl:
            pidl = ctypes.windll.shell32.ILCreateFromPathA(file_path)
        if 0 == pidl:
            ret = ctypes.windll.kernel32.GetLastError()
            err_msg = win32api.FormatMessage(ret)
        try:
            ctypes.windll.shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
            ctypes.windll.shell32.ILFree(pidl)
            ctypes.windll.ole32.CoUninitialize()
        except:
            fileutils_logger.exception(
                'open file/dir %s in explorer error:', file_path)
            # 选中指定对象.如果使用"/select",则父目录被打开,并选中指定对象,请注意命令中"/select"参数后面的逗号
            subprocess.Popen(["explorer", "/select,", file_path])
    else:
        # dde-file-manager是深度系统的文件管理器
        dde_file_manager = "dde-file-manager"
        managers = ["nautilus", dde_file_manager, "xdg-open"]
        for manager in managers:
            try:
                if manager == dde_file_manager:
                    subprocess.Popen([manager, os.path.dirname(file_path)])
                else:
                    subprocess.Popen([manager, file_path])
                ret = 0
                break
            except Exception as e:
                ret = -1
                err_msg = str(e)

    if ret != 0:
        raise RuntimeError(err_msg)


def open_path_in_terminator(file_path):
    ret = 0
    err_msg = ''
    sys_encoding = apputils.get_default_locale_encoding()
    if apputils.is_windows():
        import ctypes
        import win32api
        try:
            subprocess.Popen('start cmd.exe', shell=True, cwd=file_path)
        except:
            ret = ctypes.windll.kernel32.GetLastError()
            err_msg = win32api.FormatMessage(ret)
    else:
        try:
            subprocess.Popen('gnome-terminal', shell=True,
                             cwd=file_path.encode(sys_encoding))
        except Exception as e:
            ret = -1
            err_msg = str(e)
    if ret != 0:
        raise RuntimeError(err_msg)


def startfile(file_path):
    if apputils.is_windows():
        try:
            os.startfile(file_path)
        except:
            pass
    else:
        subprocess.call(["xdg-open", file_path])


def is_path_hidden(path):
    def is_windows_file_hidden(path):
        import win32con
        import win32file
        file_flag = win32file.GetFileAttributesW(path)
        hidden_flag = file_flag & win32con.FILE_ATTRIBUTE_HIDDEN
        is_hidden = hidden_flag == win32con.FILE_ATTRIBUTE_HIDDEN
        return is_hidden
    if os.path.basename(path).startswith("."):
        return True
    if apputils.is_windows():
        return is_windows_file_hidden(path)


def is_file_path_hidden(path):
    '''
    检查文件或目录是否隐藏,只要全路径中的某一段路径具有隐藏属性,则该全路径是隐藏的
    '''
    if apputils.is_windows():
        is_hidden = False
        if os.path.isfile(path):
            is_hidden = is_path_hidden(path)
        # files or dirs in hidden dir is not hidden,so
        # we shoud rotate to hidden dir
        else:
            while True:
                if os.path.dirname(path) == path:
                    break
                is_hidden = is_path_hidden(path)
                if is_hidden:
                    break
                path = os.path.dirname(path)
        return is_hidden
    is_hidden = False
    if os.path.isfile(path):
        is_hidden = is_path_hidden(path)
    else:
        while True:
            dirname = os.path.basename(path)
            if dirname in ('', '/'):
                break
            is_hidden = is_path_hidden(path)
            if is_hidden:
                break
            path = os.path.dirname(path)
    return is_hidden


def get_dir_files(
    path,
    file_list: list,
    filters: Optional[list] = None,
    rejects: Optional[list] = None
):
    '''
    获取路径下的子文件列表,非递归目录
    :param path: 根目录路径
    :type path: str
    :param file_list: 子文件列表
    :type file_list: list
    :param filters: 包含文件后缀列表
    :type filters: list
    :param rejects: 排除文件后缀列表
    :type rejects: list
    '''
    rejects = rejects or []
    filters = filters or []
    if not os.path.exists(path):
        return
    for f in os.listdir(path):
        file_path = os.path.join(path, f)
        if os.path.isfile(file_path):
            ext = strutils.get_file_extension(file_path)
            if ext in rejects:
                continue
            if filters == []:
                file_list.append(file_path)
            else:
                if ext in filters:
                    file_list.append(file_path)


def detect_file_encoding(filepath):
    try:
        with open(filepath, encoding=UTF8_FILE_ENCODING) as f:
            f.read()
            return UTF8_FILE_ENCODING
    except UnicodeDecodeError as ex:
        fileutils_logger.debug(
            "use encoding `%s` decode file %s error:%s, detect file encoding",
            UTF8_FILE_ENCODING,
            filepath,
            str(ex)
        )
    except Exception as ex:
        fileutils_logger.error(
            "open file %s with encoding %s error:%s",
            filepath,
            UTF8_FILE_ENCODING,
            str(ex)
        )
    with open(filepath, "rb") as f:
        chunk = f.read()
        if b'\0' in chunk:
            return BINARY
        result = detect(chunk)
        guess_encoding = result['encoding']
        fileutils_logger.debug('guess file %s encoding is %s', filepath, guess_encoding)
        if guess_encoding is not None and guess_encoding.lower() in [
            ASCII_FILE_ENCODING,
            ANSI_FILE_ENCODING,
            "gb2312",
            "gb18030",
            "gbk",
            "iso-8859-1"
        ]:
            return guess_encoding
        pre_read = 4096
        byte_str = bytearray(chunk)
        if not _Checker.IsUnicode(byte_str[0:pre_read]) and _Checker.IsBinaryBytes(byte_str[0:pre_read]):
            return BINARY
        return guess_encoding


def detect(byte_str):
    """
    Detect the encoding of the given byte string.
    :param byte_str:     The byte sequence to examine.
    :type byte_str:      ``bytes`` or ``bytearray``
    """
    if not isinstance(byte_str, bytearray):
        if not isinstance(byte_str, bytes):
            raise TypeError('Expected object of type bytes or bytearray, got: '
                            '{0}'.format(type(byte_str)))
        byte_str = bytearray(byte_str)
    # 如果文本为空,强制返回ascii编码,否则下面执行会返回cp936编码
    if not byte_str:
        return {'encoding': 'ascii'}
    detector = chardet.UniversalDetector(chardet.enums.LanguageFilter.CHINESE)
    detector.feed(byte_str)
    return detector.close()


def remove_dir(dir_path):
    files = os.listdir(dir_path)
    for f in files:
        file_path = os.path.join(dir_path, f)
        if os.path.isdir(file_path):
            remove_dir(file_path)
        else:
            os.remove(file_path)
    os.rmdir(dir_path)


if apputils.is_windows():
    def is_writable(path, user=None):
        return True
else:
    import pwd

    def is_writable(path, user=None):
        if not user:
            user = getpass.getuser()
        user_info = pwd.getpwnam(user)
        uid = user_info.pw_uid
        gid = user_info.pw_gid
        s = os.stat(path)
        mode = s[stat.ST_MODE]
        return (
            ((s[stat.ST_UID] == uid) and (mode & stat.S_IWUSR > 0)) or
            ((s[stat.ST_GID] == gid) and (mode & stat.S_IWGRP > 0)) or
            (mode & stat.S_IWOTH > 0)
        )


def normpath(path):
    return os.path.normpath(path)


def opj(path):
    """Convert paths to the platform-specific separator"""
    split_paths = path.split('/')
    # 修复os.path.join bug,在windows下硬盘符号后面必须添加路径分隔符
    if split_paths[0].endswith(":") and not path.startswith('/'):
        split_paths[0] += os.sep
    paths = tuple(split_paths)
    st = os.path.join(*paths)
    # HACK: on Linux, a leading / gets lost...
    if path.startswith('/'):
        st = '/' + st
    return normpath(st)


def get_filename_from_path(path):
    """
    Returns the filename for a full path.
    """
    return os.path.split(path)[1]


def get_filepath_from_path(path):
    """
    Returns the filename for a full path.
    """
    return os.path.split(path)[0]


def ComparePath(path1, path2):
    if os.name == 'nt':
        path1 = path1.replace("/", os.sep).rstrip(os.sep)
        path2 = path2.replace("/", os.sep).rstrip(os.sep)
        return normpath(path1.lower()) == normpath(path2.lower())
    return normpath(path1.rstrip(os.sep)) == normpath(path2.rstrip(os.sep))


def paths_contain_path(path_list, path):
    '''
    检测路径是否在路径列表中
    '''
    if os.name == 'nt':
        for p in path_list:
            if ComparePath(p, path):
                return True
        return False
    return path in path_list


def makedirs(dirname):
    dirname = os.path.abspath(dirname)
    dirname = dirname.replace("\\", "/")
    dirnames = dirname.split("/")
    destdir = ""
    destdir = os.path.join(dirnames[0] + "/", dirnames[1])

    if not os.path.exists(destdir):
        os.mkdir(destdir)

    for name in dirnames[2:]:
        destdir = os.path.join(destdir, name)
        if not os.path.exists(destdir):
            os.mkdir(destdir)


def compactPath(path, width, measure=len):
    """
    Provides a compacted path fitting inside the given width.
    measure - ref to a function used to get the length of the string
    """
    if measure(path) <= width:
        return path
    dots = '...'
    head, tail = os.path.split(path)
    mid = len(head) // 2
    head1 = head[:mid]
    head2 = head[mid:]

    while head1:
        path = os.path.join("%s%s%s" % (head1, dots, head2), tail)
        if measure(path) <= width:
            return path
        head1 = head1[:-1]
        head2 = head2[1:]

    path = os.path.join(dots, tail)
    if measure(path) <= width:
        return path

    while tail:
        path = "%s%s" % (dots, tail)
        if measure(path) <= width:
            return path
        tail = tail[1:]
    return ''


def get_file_content(
    filename,
    allow_exception=True,
    enc=UTF8_FILE_ENCODING,
    retlist=False
) -> Union[str, list]:
    """Provides the file content"""
    try:
        with open(filename, 'r', encoding=enc) as diskfile:
            if retlist:
                content = diskfile.readlines()
            else:
                content = diskfile.read()
        return content
    except Exception as exc:
        fileutils_logger.error(
            'Error reading from file %s: %s', filename, str(exc))
        if allow_exception:
            raise
        return None
