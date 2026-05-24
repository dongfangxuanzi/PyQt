r"""
    Python interface for process control.

    This module defines three Process classes for spawning,
    communicating and control processes. They are: Process, ProcessOpen,
    ProcessProxy. All of the classes allow one to specify the command (cmd),
    starting working directory (cwd), and environment to create for the
    new process (env) and to "wait" for termination of the child and
    "kill" the child.

    Process:
        Use this class to simply launch a process (either a GUI app or a
        console app in a new console) with which you do not intend to
        communicate via it std handles.

    ProcessOpen:
        Think of this as a super version of Python's os.popen3() method.
        This spawns the given command and sets up pipes for
        stdin/stdout/stderr which can then be used to communicate with
        the child.

    ProcessProxy:
        This is a heavy-weight class that, similar to ProcessOpen,
        spawns the given commands and sets up pipes to the child's
        stdin/stdout/stderr. However, it also starts three threads to
        proxy communication between each of the child's and parent's std
        handles. At the parent end of this communication are, by
        default, IOBuffer objects. You may specify your own objects here
        (usually sub-classing from IOBuffer, which handles some
        synchronization issues for you). The result is that it is
        possible to have your own IOBuffer instance that gets, say, a
        .write() "event" for every write that the child does on its
        stdout.

        Understanding ProcessProxy is pretty complex. Some examples
        below attempt to help show some uses. Here is a diagram of the
        comminucation:

                            <parent process>
               ,---->->->------'   ^   `------>->->----,
               |                   |                   v
           IOBuffer             IOBuffer            IOBuffer
           (p.stdout)           (p.stderr)          (p.stdin)
               |                   |                   |
           _OutFileProxy        _OutFileProxy       _InFileProxy
           thread               thread              thread
               |                   ^                   |
               `----<-<-<------,   |   ,------<-<-<----'
                            <child process>

    Usage:
        import process
        p = process.<Process class>(cmd='echo hi', ...)
        #... use the various methods and attributes

    Examples:
      A simple 'hello world':
        >>> import process
        >>> p = process.ProcessOpen(['echo', 'hello'])
        >>> p.stdout.read()
        'hello\r\n'
        >>> p.wait()   # .wait() returns the child's exit status
        0

      Redirecting the stdout handler:
        >>> import sys
        >>> p = process.ProcessProxy(['echo', 'hello'], stdout=sys.stdout)
        hello

      Using stdin (need to use ProcessProxy here because it defaults to
      text-mode translation on Windows, ProcessOpen does not support
      this):
        >>> p = process.ProcessProxy(['sort'])
        >>> p.stdin.write('5\n')
        >>> p.stdin.write('2\n')
        >>> p.stdin.write('7\n')
        >>> p.stdin.close()
        >>> p.stdout.read()
        '2\n5\n7\n'

      Specifying environment variables:
        >>> p = process.ProcessOpen(['perl', '-e', 'print $ENV{FOO}'])
        >>> p.stdout.read()
        ''
        >>> p = process.ProcessOpen(['perl', '-e', 'print $ENV{FOO}'],
        ...                         env={'FOO':'bar'})
        >>> p.stdout.read()
        'bar'

      Killing a long running process (On Linux, to poll you must use
      p.wait(os.WNOHANG)):
        >>> p = ProcessOpen(['perl', '-e', 'while (1) {}'])
        >>> try:
        ...     p.wait(os.WNOHANG)  # poll to see if is process still running
        ... except ProcessError, ex:
        ...     if ex.errno == ProcessProxy.WAIT_TIMEOUT:
        ...             print "process is still running"
        ...
        process is still running
        >>> p.kill(42)
        >>> p.wait()
        42

      Providing objects for stdin/stdout/stderr:
        XXX write this, mention IOBuffer subclassing.
"""
class User(object):
  def __init__(self, name):
    self.name = name
    
class Teacher(User):
      def __init__(self, name, age):
          self._age = age
	
if True:
     print('Hi there')


# The space after open is unnecessary
with open( 'file.dat') as f:
    contents = f.read()
	
if age>15:
    print('Can drive')
	
	
age=67

# There are two spaces before the multiplication operator
num = 10
doubled = num  * 2

## Prints hello
print('hello')

#This comment needs a space
def print_name(self):
    print(self.name)
	
def print_name(self):
    print(self.name)  #This comment needs a space

age = 10+15
remainder = 10%2
my_tuple = 1,  2

def  func():
    pass
	
from collections import(namedtuple, defaultdict)
class MyClass(object):
    def func1():
        pass
    def func2():
        pass
		
def func1():
    pass
def func2():
    pass
	
import collections, os, sys


list1=[11111,333,344555,66666,2333333,9999,'aaaaaa','bbbbbbbb',"gggggggggggggggggggg","x","y","zzzzz"]


list2=[11111,333,344555,66666,2333333,9999,'aaaaaa','bbbbbbbb',"gggggggggggggggggggg","x","y","zzzzz",
    # hahhahah
    "a","b","ccccc","ddddddddd"]
class User(object):
    pass
user = User()

def f(): pass

def test_func():
    lines = [1, 2, 3, 4]
    plist = []
    for i, line in enumerate(lines):
        new_line = line.strip()
        plist.append(new_line)
        
    j=3
    x, y = 1, 2
    
str1='a,2,3'
dst=str1.split(',')[0]
print(dst)
root_dir_path=''
parent_path=''
relative_path = str(root_dir_path).replace(
    str(parent_path) + os.sep, '').split('.')[0]
    
i=1
if i==1 or i ==2:
    print(str1)
    
if i!=1 and i !=2:
    print(str1)
    
lst1 = [1,2,3]
if 0==len(lst1):
    print(lst1)
    
if len(lst1)==0:
    print(lst1)
if 0!=len(lst1):
    print(str1)
if len(lst1)!=0:
    print(str1)
    
if len(lst1):
    print(lst1)
    
if not len(lst1):
    print(str1)
    
a1=True if len(lst1)==0 else False

newname=''
a2=False if len(lst1)!=0 else True
ok = True if len(newname) > 0 else False
ok2 = True if newname else False
ok3 = True if not newname else False
ok4 = False if newname else True
ok5 = False if not newname else True
ok6 = not (not newname)
ok7 = not (not a1)
x=1
y=2
x1=-(-1)
x2=-(x-y)
start=-1
if start < 0:
    start = 0
if start <= 0:
    start = 0
if start >100:
    start = 100
    
if start >=100:
    start = 100

start_test_str = 'this is a test string'
if start_test_str.startswith('th') or start_test_str.startswith('this'):
    print('hi')