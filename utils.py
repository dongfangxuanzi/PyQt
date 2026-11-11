# -*- coding: utf-8 -*-
from noval.util.logger import *
from noval.util.apputils import *
from noval.util.appdirs import *
from noval.util.urlutils import *
from noval.util.strutils import *
from noval import GetApp
import subprocess
    
def profile_get(key,default_value=""):
    if is_py2():
        basestring_ = basestring
    elif is_py3_plus():
        basestring_ = str
    if isinstance(default_value,basestring_):
        return GetApp().GetConfig().Read(key, default_value)
    else:
        try:
            return eval(GetApp().GetConfig().Read(key, ""))
        except:
            return default_value
    
def profile_get_int(key,default_value=-1):
    return GetApp().GetConfig().ReadInt(key, default_value)
    
def profile_set(key,value):
    if type(value) == int or type(value) == bool:
        GetApp().GetConfig().WriteInt(key,value)
    else:
        if isinstance(value, str) or (is_py2() and isinstance(value,unicode)):
            GetApp().GetConfig().Write(key,value)
        else:
            GetApp().GetConfig().Write(key,repr(value))

def update_statusbar(msg):
    try:
        GetApp().MainFrame.PushStatusText(msg)
    except:
        pass
    
def get_main_frame():
    return GetApp().MainFrame

def get_child_pids(ppid):
    child_ids = []
    for pid in psutil.pids():
        try:
            p = psutil.Process(pid)
            if p.ppid() == ppid:
                child_ids.append(p.pid)
        except:
            pass
    return child_ids
    
if is_windows():
    from noval.util.registry import *
elif is_linux():
    try:
        from ConfigParser import ConfigParser
    except:
        from configparser import ConfigParser
        
class Config(object):
    if is_windows():
        def __init__(self,app_name):
            self.app_name = app_name
            base_reg = Registry().Open('SOFTWARE')
            self.reg = self.EnsureOpenKey(base_reg,self.app_name)
                
        def EnsureOpenKey(self,parent_reg,key):
            #打开时必须设置注册表有写的权限,否则会提示权限不足
            reg = parent_reg.Open(key,access=KEY_ALL_ACCESS)
            if reg is None:
                reg = parent_reg.CreateKey(key)
            return reg
                
        def GetDestRegKey(self,key,ensure_open=True):
            '''
                按照/分割线分割多级key,如果是写入操作,则创建所有子健
                如果是读取操作,则不能创建子健,只能打开,如果打开失败,则返回None
                ensure_open:打开子健失败时是否创建子健
            '''
            if -1 == key.find("/"):
                return self.reg,key
            child_keys = key.split("/")
            last_key = child_keys.pop()
            loop_reg = self.reg
            for child in child_keys:
                if ensure_open:
                    child_reg = self.EnsureOpenKey(loop_reg,child)
                else:
                    child_reg = loop_reg.Open(child,access=KEY_ALL_ACCESS)
                    if child_reg is None:
                        return None,last_key
                loop_reg = child_reg
            return loop_reg,last_key
                
        def Read(self,key,default=""):
            dest_key_reg,last_key = self.GetDestRegKey(key,ensure_open=False)
            if dest_key_reg is None:
                return default
            try:
                return dest_key_reg.ReadEx(last_key)
            except:
                if is_py2():
                    assert(isinstance(default,basestring))
                elif is_py3_plus():
                    assert(isinstance(default,str))
                return default
            
        def ReadInt(self,key,default=-1):
            return int(self.Read(key,str(int(default))))
            
        def Write(self,key,value):
            try:
                dest_key_reg,last_key = self.GetDestRegKey(key)
                val_type = REG_SZ
                if is_py3_plus() and type(value) == bytes:
                    val_type = REG_BINARY
                dest_key_reg.WriteValueEx(last_key,value,val_type=val_type)
            except Exception as e:
                get_logger().exception("write reg key %s fail" % key)
                
        def WriteInt(self,key,value):
            try:
                dest_key_reg,last_key = self.GetDestRegKey(key)
                dest_key_reg.WriteValueEx(last_key,value,val_type=REG_DWORD)
            except:
                get_logger().exception("write reg key %s fail" % key)
                
        def Exist(self,key):
            try:
                self.reg.ReadEx(key)
                return True
            except:
                return False
                
        def DeleteEntry(self,key_val):
            dest_key_reg,value = self.GetDestRegKey(key_val,ensure_open=False)
            if dest_key_reg is None:
                return
            try:
                dest_key_reg.DeleteValue(value)
            except:
                get_logger().debug("delete key_val %s fail" % key_val)
                
        def GetGroups(self,key_path,names):
            if not self.reg.Exist(key_path):
                return
            dest_key_reg,value = self.GetDestRegKey(key_path)
            for name in dest_key_reg.EnumChildKeyNames():
                names.append(name)
            
        def DeleteGroup(self,key_path):
            self.reg.DeleteKeys(key_path)
            
    else:
        def __init__(self,app_name):
            self.app_name = app_name
            self.cfg = ConfigParser()
            self.config_path = os.path.join(os.path.expanduser("~"),"." + self.app_name)
            try:
                self.cfg.read(self.config_path)
            except Exception as e:
                get_logger().warn('load ide config file error %s,will reaload it',str(e))
                self.Reload()
            
        def GetDestSection(self,key,ensure_open=True):
            '''
                按照/分割线分割多级key,如果是写入操作,则创建所有子健
                如果是读取操作,则不能创建子健,只能打开,如果打开失败,则返回None
                ensure_open:打开子健失败时是否创建子健
            '''
            if -1 == key.find("/"):
                return 'DEFAULT',key
            sections = key.split("/")
            last_key = sections.pop()
            for i in range(len(sections)):
                section = ("/").join(sections[0:i+1])
                if ensure_open:
                    #禁止写入空字段[]
                    if section and not self.cfg.has_section(section):
                        self.cfg.add_section(section)
                else:
                    if section and not self.cfg.has_section(section):
                        return None,last_key
            return ("/").join(sections),last_key
                
        def Read(self,key,default=""):
            section,last_key = self.GetDestSection(key,ensure_open=False)
            try:
                return self.cfg.get(section,last_key)
            except:
                if is_py2():
                    assert(isinstance(default,basestring))
                elif is_py3_plus():
                    assert(isinstance(default,str))
                return default
            
        def ReadInt(self,key,default=-1):
            section,last_key = self.GetDestSection(key,ensure_open=False)
            try:
                return self.cfg.getint(section,last_key)
            except:
                assert(isinstance(default,int) or isinstance(default,bool))
                return default
            
        def Write(self,key,value):
            section,last_key = self.GetDestSection(key)
            if isinstance(value, str) or (is_py2() and isinstance(value,unicode)):
                if is_py2():
                    value = str(value)
                self.cfg.set(section,last_key,value)
            else:
                self.cfg.set(section,last_key,repr(value))
            
        def WriteInt(self,key,value):
            section,last_key = self.GetDestSection(key)
            #将bool值转换为int
            if type(value) == bool:
                value = int(value)
            assert(type(value) == int)
            #python3 configparser不支持写入整形变量,必须先转换为字符串
            if is_py3_plus():
                value = str(value)
            #必须将整形转换为字符串写入
            self.cfg.set(section,last_key,str(value))
            
        def Save(self):
            with open(self.config_path,"w") as f:
                self.cfg.write(f)
                
        def DeleteEntry(self,key):
            section,last_key = self.GetDestSection(key)
            self.cfg.remove_option(section,last_key)
            self.Save()

        def GetGroups(self,key_path,names):
            for section in self.cfg.sections():
                if section.find(key_path) != -1:
                    names.append(key_path)
            
        def DeleteGroup(self,key_path):
            for section in self.cfg.sections():
                if section.find(key_path) != -1:
                    self.cfg.remove_section(section)
            self.Save()
            
        def Reload(self):
            '''
                如果配置文件加载错误,重新加载时删除原配置文件
            '''
            if os.path.exists(self.config_path):
                os.remove(self.config_path)
            self.cfg.read(self.config_path)

def call_after(func):
    '''
        不带参数的装饰器
    '''
    def _wrapper(*args, **kwargs): 
        GetApp().after(100,func, *args, **kwargs) 
    return _wrapper 
    
def call_after_with_arg(*wrap_args,**wrap_kwargs):
    '''
        带参数的装饰器
    '''
    def call_after(func): 
        def _wrapper(*args, **kwargs): 
            GetApp().after(wrap_args[0],func, *args, **kwargs) 
        return _wrapper
    return call_after

def GetClassFromDynamicImportModule(full_class_path):
    '''
        从给定字符串中动态获取模块的类
    '''
    parts = full_class_path.split(".")
    full_module_path = ".".join(parts[0:-1])
    class_name = parts[-1]
    #必须先导入模块,再获取模块里面的方法,不要直接导入类
    #如果类名是类似xx.yy.zz这样的,必须设置fromlist不为空
    module_obj = __import__(full_module_path,globals(), globals(), fromlist=['__name__'])
    class_obj = getattr(module_obj,class_name)
    return class_obj


def compute_run_time(func):
    '''
        统计函数执行时间的装饰函数
    '''
    def wrapped_func(*args,**kwargs):
        start = time.perf_counter()
        ret = func(*args,**kwargs)
        end = time.perf_counter()
        elapse = end - start
        get_logger().info("%s elapse %.3f seconds" % (func.__name__,end-start))
        return ret
    return wrapped_func
    
def GetCommandOutput(command,read_error=False,cwd=None,encoding = get_default_encoding()):
    '''
        获取命令的输出信息,输出不能太长
    '''
    output = ''
    try:
        p = subprocess.Popen(command,shell=True,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if read_error:
            output = p.stderr.read()
        else:
            output = p.stdout.read()
        #PY3输出类型为bytes,需要转换为str类型
        if is_py3_plus():
            output = str(output,encoding = encoding)
    except Exception as e:
        get_logger().error("get command %s output error:%s",command,e)
        get_logger().exception("")
        return ''
    return output

def call_process(cmd,args):
    '''
        简单调用进程
    '''
    if is_windows():
        import win32api
        win32api.ShellExecute(0,"open",cmd," " + args + " " +extension.commandPostArgs , '', 1)
    else:
        subprocess.call(cmd + ' ' + args,shell=True)
        

def create_process(command,args,shell=True,env=None,universal_newlines=True,cwd=None):
    '''
        创建普通进程
    '''
    #如果shell为False,表示命令是列表,subprocess.Popen只接受数组变量作为命令
    if not shell:
        if isinstance(args,str):
            #将字符串参数按空格转换成参数列表,支持分割双引号参数
            args = parse_cmd_line(args)
        cmd = [command] + args
    #否则是shell命令字符串
    else:
        cmd = command + " " + args
    get_logger().info("run command is:%s",cmd)
    if is_windows():
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        #隐藏命令行黑框
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    else:
        startupinfo = None
        creationflags = 0
    p = subprocess.Popen(
        cmd,
        shell=shell,
        env=env,
        cwd=cwd,
        universal_newlines=universal_newlines,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    return p

def test_try_except_finnaly():
    try:
        a=1/0
    except ZeroDivisionError:
        print('++++++++')
        return 0
    finally:
        print('---------------')
        return 1
        
def test_try_except_else():
    try:
        a=1/0
    except ZeroDivisionError:
        print('++++++++')
        return 0
    else:
        print('---------------')
        return 1