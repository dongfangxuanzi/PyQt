from distutils.core import setup
from setuptools import find_packages

install_requires = ['pyyaml']
# todo:暂时注释,待以后实现
# TODO:this may cause problem ,should watch some time to check error or not
# XXX This is hacky.
# We cannot then use _fixupCommand because this will cause a
# shell to be openned as the command is launched. Therefore need
# to ensure be have the full path to the executable to launch.
setup(name='CodeCounter',
        version='1.1.0',
        description='''CoderCounter is a program can canculate code file line,such ass python,javasript,html,config etc which ignore code comments and blank code line.
             it support single code file or code dir''',
        author='wukan',
        author_email='kan.wu@gengtalks.com',
        url='https://gitlab.com/wekay102200/CodeCounter.git',
        license='Genetalks',
        packages=find_packages(),
        install_requires=install_requires,
        zip_safe=False,
        package_data={'CodeCounter':['./parser.yml']},
        classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
        ],
        entry_points="""
        [console_scripts]
        CodeCounter = CodeCounter.CodeCounter:main
        """
)
