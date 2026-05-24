from noval import NewId,GetApp,_
import os
import tkinter as tk
from tkinter import ttk
import noval.project.executor as executor
import noval.toolbar as toolbar
from noval.project.output import *
from noval.project.executor import *
import noval.core as core
from noval.util.appdirs import get_user_data_path



# -*- coding: utf-8 -*-
from noval import GetApp,_
import os
import tkinter as tk
from tkinter.messagebox import showerror
import noval.iface as iface
import noval.plugin as plugin
import noval.consts as consts
from tkinter import ttk
import sys
from noval.editor.code import CodeCtrl
import noval.syntax.lang as lang
import noval.syntax.syntax as syntax
import noval.util.strutils as strutils
import noval.util.utils as utils
import noval.python.pyutils as pyutils
import re
import noval.editor.text as texteditor
import tkinter.font as tk_font
import noval.python.plugins.pyshell.running_py as running
from noval.util.command import *
from noval.shell import *
import noval.roughparse as roughparse
import traceback
from noval.python.plugins.pyshell.pyshell import ShellText
from scientificshell.table import TableFrame
runner = None
def get_runner():
    return runner



def common_run_exception(func):
    '''
        调式运行公共异常处理函数,装饰调式运行函数,做同样的异常处理
    '''
    def _wrapper(*args, **kwargs): 
        try:
            func(*args, **kwargs)
        except executor.StartupPathNotExistError as e:
            e.ShowMessageBox()
        except Exception as e:
            if not isinstance(e,RuntimeError):
                utils.get_logger().exception("")
            messagebox.showerror(_("Run Error"),str(e),parent=GetApp().GetTopWindow())
    return _wrapper 

class CommonRunCommandUI(ttk.Frame):
    KILL_PROCESS_ID = NewId()
    CLOSE_TAB_ID = NewId()
    TERMINATE_ALL_PROCESS_ID = NewId()
    RESTART_PROCESS_ID = NewId()

    def __init__(self,parent, debugger,run_parameter,toolbar_orient=tk.HORIZONTAL):
        ttk.Frame.__init__(self, parent)
        self._debugger = debugger
        self._run_parameter = run_parameter
        self._restarted = False
        self._stopped = False
        # GUI Initialization follows
        self._tb = toolbar.ToolBar(self,orient=toolbar_orient)
        if toolbar_orient == tk.HORIZONTAL:
            self._tb.pack(fill="x",expand=0)
        else:
            self._tb.pack(side=tk.LEFT,fill="y",expand=0)
        self.CreateToolbarButtons()
        self.btn=ttk.Button(self,text='点我')
        self.btn.pack(side=tk.LEFT)
        
        self.EnableToolbar()
        
    def EnableToolbar(self):
        enable=True
        self._tb.EnableTool(self.KILL_PROCESS_ID,enable=enable)
        self._tb.EnableTool(self.TERMINATE_ALL_PROCESS_ID,enable=enable)
        self._tb.EnableTool(self.RESTART_PROCESS_ID,enable=enable)
            
    def CreateToolbarButtons(self):
        
        self.terminate_all_image = GetApp().GetImage("python/debugger/terminate_all.png")
        self.restart_image = GetApp().GetImage("python/debugger/restart.png")
        self.close_img = GetApp().GetImage("python/debugger/close.png")
        self.stop_img = GetApp().GetImage("python/debugger/stop.png")
        
        self._tb.AddButton(self.CLOSE_TAB_ID,self.close_img,_("Close Window"),lambda:self.OnToolClicked(self.CLOSE_TAB_ID))
        self._tb.AddButton(self.KILL_PROCESS_ID,self.stop_img,_("Stop the Run."),lambda:self.OnToolClicked(self.KILL_PROCESS_ID))
        
        self._tb.AddButton(self.TERMINATE_ALL_PROCESS_ID,self.terminate_all_image,_("Stop All the Run."),lambda:self.OnToolClicked(self.TERMINATE_ALL_PROCESS_ID))
        self._tb.AddButton(self.RESTART_PROCESS_ID,self.restart_image,_("Restart the Run."),lambda:self.OnToolClicked(self.RESTART_PROCESS_ID))


    def SetRunParameter(self,run_parameter):
        self._run_parameter = run_parameter

    def CreateExecutor(self,source=SOURCE_DEBUG,finish_stopped=True):
        '''
            finish_stopped表示该执行器支持完成后,是否表示整个运行完成,大部分情况下一个进程执行完成,就表示改运行完成
            考虑到一次完整的运行可能需要连续执行几个进程,第一个进程执行完后并不表示整个执行完成,要接着执行下一个,直到最后一个进程执行完成才表示运行完成
            source表示输出日志来源,比如有的是build输出,有的是debug输出,默认是debug输出
        '''
        self._executor = self.GetExecutorClass()(self._run_parameter, self, callbackOnExit=lambda:self.ExecutorFinished(finish_stopped),source=source)
        self.evt_stdtext_binding = GetApp().bind(executor.EVT_UPDATE_STDTEXT, self.AppendText,True)
        self.evt_stdterr_binding = GetApp().bind(executor.EVT_UPDATE_ERRTEXT, self.AppendErrorText,True)
        self._output.SetExecutor(self._executor)

    def GetExecutorClass(self):
        return Executor

    def destroy(self):
        # See comment on PythonDebuggerUI.StopExecution
        self._executor.DoStopExecution()
        ttk.Frame.destroy(self)
        
    def GetOutputview(self):
        return self._output

    def GetOutputviewClass(self):
        return CommononOutputview

    @common_run_exception
    def Execute(self):
        try:
            self._executor.Execute()
        except Exception as e:
            self.StopExecution()
            self.ExecutorFinished()
            raise e
    
    def IsProcessRunning(self):
        return not self.Stopped
    
    @property
    def Stopped(self):
        return self._stopped
        
    def UpdateTerminateAllUI(self):
        self._tb.EnableTool(self.TERMINATE_ALL_PROCESS_ID, self.IsProcessRunning())
        
    def UpdateAllRunnerTerminateAllUI(self):
        pass
        
    def ExecutorFinished(self,stopped=True):
        '''
            stopped表示该执行完成后是否表示整个运行完成了,stopped为True表示是,为False表示否,意外着还有下一个执行
        '''
        try:
            self._stopped = stopped
            self._tb.EnableTool(self.KILL_PROCESS_ID, False)
            self._textCtrl.set_read_only(True)
            self.UpdateAllRunnerTerminateAllUI()
        except tk.TclError:
            utils.get_logger().warn("RunCommandUI object has been deleted, attribute access no longer allowed when finish executor")
            return
        #如果是点了重新执行按钮,程序执行完成后,需要再运行一次
        if self._restarted:
            self.RestartRunProcess()
            self._restarted = False

    def StopExecution(self,unbind_evt=False):
        if not self._stopped:
            if unbind_evt:
                GetApp().unbind(executor.EVT_UPDATE_STDTEXT,self.evt_stdtext_binding)
                GetApp().unbind(executor.EVT_UPDATE_ERRTEXT,self.evt_stdterr_binding)
            self._executor.DoStopExecution()
            self._textCtrl.set_read_only(True)

    def AppendText(self, event):
        if event.get('interface') != self:
            utils.get_logger().debug('run view interface receive other stdout msg,ignore it')
            return
        #程序终止或完成时把输出框设置为只读
        self._textCtrl.AppendText(event.get('source'),event.get('value'),self._stopped)

    def AppendErrorText(self, event):
        if event.get('interface') != self:
            utils.get_logger().debug('run view interface receive other stderr msg,ignore it')
            return
        #程序终止或完成时把输出框设置为只读
        self._textCtrl.AppendErrorText(event.get('source'),event.get('value'),self._stopped)

    def StopAndRemoveUI(self):
        '''
            这里必须返回True,否则会导致程序不允许关闭
        '''
        #关闭窗口之前检查是否有进程在运行
        if not self._stopped :
            ret = messagebox.askyesno(_("Process Running.."),
                                      _("Process is still running,Do you want to kill the process and remove it?"),parent=self)
            if ret == False:
                return False
        #类似于右上角按钮关闭事件,会更新菜单是否选中
        self.master.close()
        return True

    def SaveProjectFiles(self):
        '''
            调式运行时保存文件策略,默认保存当前项目的修改文件
        '''
        self._debugger.GetCurrentProject().PromptToSaveFiles()
        
    def RestartProcess(self):
        currentProj = GetApp().MainFrame.GetProjectView(False).GetCurrentProject()
        self.SaveProjectFiles()
        if not self._stopped:
            self._restarted = True
            self.StopExecution()
        else:
            self.RestartRunProcess()
            
    def RestartRunProcess(self):
        self._textCtrl.ClearOutput()
        self._tb.EnableTool(self.KILL_PROCESS_ID, True)
        self._tb.EnableTool(self.TERMINATE_ALL_PROCESS_ID, True)
        self._stopped = False
        self.Execute()

    #------------------------------------------------------------------------------
    # Event handling
    #-----------------------------------------------------------------------------

    def OnToolClicked(self, id):
        if id == self.KILL_PROCESS_ID:
            print('lill process')
            #self.StopExecution()

        elif id == self.CLOSE_TAB_ID:
            self.StopAndRemoveUI()
            
        elif id == self.TERMINATE_ALL_PROCESS_ID:
##            self.ShutdownAllRunners()
            print('终止一切进程！')
            
        elif id == self.RESTART_PROCESS_ID:
    #        self.RestartProcess()   
            print('重启进程！')    

    def Close(self):
        self.StopAndRemoveUI()
        
    def GetOutputCtrl(self):
        return self._textCtrl

class MyShellText(ShellText):
    def __init__(self, master, cnf={}, **kw):
        super().__init__(master,cnf,**kw)
        self._master=master
    def _submit_input(self, text_to_be_submitted):
        utils.get_logger().debug(
            "SHELL: submitting %r in state %s", text_to_be_submitted, self.get_runner().get_state()
        )
        if self.get_runner().is_waiting_toplevel_command():
            # register in history and count
            if text_to_be_submitted in self._command_history:
                self._command_history.PopItem(text_to_be_submitted)
            self.addHistory(text_to_be_submitted)

            # meaning command selection is not in process
            self._command_history_current_index = None

            self.update_tty_mode()

            try:
                self.process_cmd_line(text_to_be_submitted)
                # remember the place where the output of this command started
                self.mark_set("command_io_start", "output_insert")
                self.mark_gravity("command_io_start", "left")
                # discard old io events
                self._applied_io_events = []
                self._queued_io_events = []
            except Exception:
                GetApp().report_exception()
                self._insert_prompt()

            GetApp().event_generate("ShellCommand", command_text=text_to_be_submitted)
        else:
            assert self.get_runner().is_running()
            self.get_runner().send_program_input(text_to_be_submitted)
            GetApp().event_generate("ShellInput", input_text=text_to_be_submitted)
            self._applied_io_events.append((text_to_be_submitted, "stdin"))
        print('保存变量！！！')
        self.after(200,self.saveVariables)

    def _submit_input2(self, text_to_be_submitted):
        utils.get_logger().debug(
            "SHELL: submitting %r in state %s", text_to_be_submitted, self.get_runner().get_state()
        )
        if self.get_runner().is_waiting_toplevel_command():
            # register in history and count
##            if text_to_be_submitted in self._command_history:
##                self._command_history.PopItem(text_to_be_submitted)
##            self.addHistory(text_to_be_submitted)

            # meaning command selection is not in process
            self._command_history_current_index = None

            self.update_tty_mode()

            try:
                self.process_cmd_line(text_to_be_submitted)
                # remember the place where the output of this command started
                self.mark_set("command_io_start", "output_insert")
                self.mark_gravity("command_io_start", "left")
                # discard old io events
                self._applied_io_events = []
                self._queued_io_events = []
            except Exception:
                GetApp().report_exception()
                self._insert_prompt()

            GetApp().event_generate("ShellCommand", command_text=text_to_be_submitted)
        else:
            assert self.get_runner().is_running()
            self.get_runner().send_program_input(text_to_be_submitted)
            GetApp().event_generate("ShellInput", input_text=text_to_be_submitted)
            self._applied_io_events.append((text_to_be_submitted, "stdin"))

    
    def _submit_programmed_input(self, text_to_be_submitted):
        utils.get_logger().debug(
            "SHELL——programmed input:::: submitting %r in state %s", text_to_be_submitted, self.get_runner().get_state()
        )
        if self.get_runner().is_waiting_toplevel_command():

            # meaning command selection is not in process
            self._command_history_current_index = None

            self.update_tty_mode()

            try:
                self.process_cmd_line(text_to_be_submitted)
                print('hhhhhh'*200)
                # remember the place where the output of this command started
                self.mark_set("command_io_start", "output_insert")
                self.mark_gravity("command_io_start", "left")
                # discard old io events
                self._applied_io_events = []
                self._queued_io_events = []
            except Exception:
                GetApp().report_exception()
                self._insert_prompt()

            GetApp().event_generate("ShellCommand", command_text=text_to_be_submitted)
        else:
            assert self.get_runner().is_running()
            self.get_runner().send_program_input(text_to_be_submitted)
            GetApp().event_generate("ShellInput", input_text=text_to_be_submitted)
            self._applied_io_events.append((text_to_be_submitted, "stdin"))  

    def saveVariables(self):
        cmd= """
import os
import pickle
moduleType=type(os)



__dic=locals()

for __k in list(__dic.keys()):
    
    if __k.startswith(\'__\'):
        continue
    
    __path=os.path.join(\'{0}\',\'pluginFiles/powercmd/%s.pkl\'%__k)
    try:
        
        #print(__path)
        with open(__path,\'wb\') as __f:
            
            
            pickle.dump(__dic[__k],__f)
              
        
    except Exception as __e:
        pass
        #print(__e)
    if os.path.getsize(__path)==0:
        os.remove(__path)
                
         """.format(get_user_data_path())
        print(cmd)
        self._submit_input2(cmd)
        self.after(1000,self._master.varShowTable.loadTable)
        #GetApp().event_generate("ShellCommand", command_text=cmd)
        #self.after(3000,self.saveVariables)
        return 


class MyPyShell(BaseShell):
    def __init__(self, mater):
        global runner
        default_editor_family = GetApp().GetDefaultEditorFamily()
        #pyshell不能和文本编辑器使用同一字体,以免放大字体时pyshell也会放大字体
        self.fonts = [
            tk_font.Font(
                name="PyShellEditorFont1", family=utils.profile_get(consts.EDITOR_FONT_FAMILY_KEY,default_editor_family)
            ),
            tk_font.Font(
                name="PyShellBoldEditorFont1",
                family=utils.profile_get(consts.EDITOR_FONT_FAMILY_KEY,default_editor_family),
                weight="bold",
            ),
        ]
        BaseShell.__init__(self,mater)
        self._add_main_backends()
        runner = self._runner
        self.varShowTable=TableFrame(self)
        self.varShowTable.grid()
        
        
    def sendCommand(self,cmd):
        
        self.saveVariables()

    def UpdateShell(self,event):
        current_interpreter = GetApp().GetCurrentInterpreter()
        backend = None
        if current_interpreter.IsBuiltIn:
            backend = "SameAsFrontend"
        else:
            backend = "CustomCPython"
        utils.profile_set("run.backend_name",backend)
        self._runner.restart_backend(clean=True,first=False)

    def _start_runner(self):
        try:
            GetApp().update_idletasks()  # allow UI to complete
            self._runner.start()
        except Exception:
            GetApp().report_exception("Error when initializing backend")
            
    
    def GetShelltextClass(self):
        return MyShellText

    def GetFontName(self):
        return 'PyShellEditorFont1'
    

    def GetRunner(self):
        return running.PythonRunner(self)
    
    def fixLineEndings(self, text):
        """Return text with line endings replaced by OS-specific endings."""
        lines = text.split('\r\n')
        for l in range(len(lines)):
            chunks = lines[l].split('\r')
            for c in range(len(chunks)):
                chunks[c] = os.linesep.join(chunks[c].split('\n'))
            lines[l] = os.linesep.join(chunks)
        text = os.linesep.join(lines)
        return text

    def _add_main_backends(self):
        #self.set_default("run.backend_name", "SameAsFrontend")
        #self.set_default("CustomInterpreter.used_paths", [])
        #self.set_default("CustomInterpreter.path", "")
        GetApp().add_backend(
            "SameAsFrontend",
            running.BuiltinCPythonProxy,
            _("The same interpreter which runs Thonny (default)"),
            "1",
        )
        GetApp().add_backend(
            "CustomCPython",
            running.CustomCPythonProxy,
            _("Alternative Python 3 interpreter or virtual environment"),
            "2",
        )
if __name__=='__main__':
    t=MyText()