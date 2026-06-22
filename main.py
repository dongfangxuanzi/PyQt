import logging


num_str = some_num.__str__() # [unnecessary-dunder-call]
num_repr = some_num.__add__(2) # [unnecessary-dunder-call]
my_repr = my_module.my_object.__repr__() # [unnecessary-dunder-call]

MY_CONTAINS_BAD = {1, 2, 3}.__contains__(1) # [unnecessary-dunder-call]
MY_CONTAINS_GOOD = 1 in {1, 2, 3}

def foo1(x, y, z):
    MY_CONTAINS_BAD=False
    for i in x:
        if i > y:  # [no-else-break]
            break
        else:
            a = z

def test_W0120_for():
    for i in range(10):
        if i>9:
            return i
    else:
        return -1
        
def test_W0120_while():
    while i:
        if i>9:
            return i
        i +=1
    else:
        return -1

class A:
    # pylint: disable = ggggg
    # pylint: disable=kkkk
    def __init__(self):
        self.name = 'a'
        self.out()

    def out(self):
        print(self.name)


class B(A):
    def __init__(self):
        self.name = 'b'
        self.age = 11
        self.out()
        
    def out(self):
        print(self.age)
        
    def set_age(self, age):
        if self.age <=0:
            self.age =0
        self.age = age
        if self.age >=100:
            self.age =100
        self.addr = 'hubei'

class C(A):
    def __init__(self, a, b): ...
    
    def __setitem__(self, key, item): setattr(self.obj, key, item)
    def __delitem__(self, key): delattr(self.obj, key)
    
    
    def OnResourceViewToolClicked(self, event):
        id = event.GetId()
        if id in (ResourceView.REFRESH_PATH_ID, ResourceView.ADD_FOLDER_ID):
            return self.dir_ctrl.ProcessEvent(event)
    def OnToolClicked(self, id):
        super().OnToolClicked(id)
        if id == self.TERMINATE_ALL_PROCESS_ID:
            self.ShutdownAllRunners()
            
def test():
    print(a)
    '''todo
    this is pointless string statement
    '''
    endstr = '....'
    logging.error("this a logger test:" + str(a))
    logging.warning("this a logger test:" + str(a) +",end str:" + endstr)
    logging.info('hello, world:%s'%str(a))
    logging.info('hello, world:%s:%s'%(str(a), endstr))
    b = B()
    '''this is another pointless string statement'''
    if 1:
        logging.debug('1')
    else:
        '''else pointless string statement'''
        
    try:
        return Tracer._execute_prepared_user_code(self, statements, expression, global_vars)
    finally:
        """
        from thonny.misc_utils import _win_get_used_memory
        print("Memory:", _win_get_used_memory() / 1024 / 1024)
        print("States:", len(self._saved_states))
        print(self._fulltags.most_common())
        """
    

if __name__ == "__main__":
    a=1
    b=4
    c=5
    test()