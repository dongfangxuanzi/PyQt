import logging

class A:
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
        
def test():
    print(a)
    endstr = '....'
    logging.error("this a logger test:" + str(a))
    logging.warning("this a logger test:" + str(a) +",end str:" + endstr)
    logging.info('hello, world:%s'%str(a))
    logging.info('hello, world:%s:%s'%(str(a), endstr))
    b = B()
if __name__ == "__main__":
    a=1
    b=4
    c=5
    test()