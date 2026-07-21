import re
from astroid import nodes
from ...pylint_fix import PylintFixer
from ...basefix import fix_code_file_msg
from ...codeutils import get_node_range
from novalapp.python.parser.node_scope import ScopeFinder
from novalapp.python.syspath import append_to_syspath, remove_syspath

class PylintW0221Fixer(PylintFixer):
    '''
    规则说明: 继承方法的参数个数改变了
    '''

    def __init__(self):
        super().__init__('W0221', False)

    @fix_code_file_msg
    def fix_message(self, doc, msg, **kwargs):
        textview = kwargs.get('textview')
        regstr = r"was (\d+) in '(.*)' and is now (\d+) in overriding '(.*)' method"
        res = re.search(regstr, msg.msg)
        parent_arg_num,parent_method,derived_arg_num,derived_method = res.groups()
        print(res,parent_arg_num,parent_method,derived_arg_num,derived_method)
        parent_class_name,parent_method_name = parent_method.split('.')
        derived_class_name,derived_method_name = derived_method.split('.')
        docpath = doc.GetPath()
        append_to_syspath(docpath)
        node = self.find_msg_node(textview,msg)
        pnode = node.parent
        print(node,pnode,pnode.parent,parent_class_name,parent_method_name,derived_class_name,derived_method_name,"--------------------------")
        if isinstance(node, nodes.Name) and node.name == derived_method_name and (
            isinstance(pnode, nodes.FunctionDef)
        ):
            if isinstance(pnode.parent, nodes.ClassDef) and pnode.parent.name==derived_class_name:
                class_node = pnode.parent
                mros = class_node.mro()
                mros.remove(class_node)
                for mro in mros:
                    print(mro,"+++++++++++++++++++++++")
                    if mro.name == parent_class_name:
                        base_node_method = ScopeFinder.get_class_method_node(mro,pnode.name)
                        print(base_node_method,"=====================")
                        if not base_node_method:
                            break
                        args = base_node_method.arguments.args
                        pnode.arguments.args = args
                        arg_node_range = get_node_range(pnode.arguments)
                        arg_node_range.replace_with_text(
                            textview,
                            pnode.arguments.as_string()
                        )
                        remove_syspath(docpath)
                        return True
        remove_syspath(docpath)
        return False
