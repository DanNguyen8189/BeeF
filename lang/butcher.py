#!/usr/bin/env python2.7
"""
Alexander Haggart, 4/14/18

Assembler for COW assembly files
    - Assembles .beef machine code from .cow assembly files

syntax:
module_name{
    preamble{

    }
    depends{

    }
    namespace{
        function_name binds other_module{
            bindings_and_raw_assembly
            if{
                
            }
            else{
            
            }
            call{
                path to function
            }
        }
        nested_namespace_name imports other_module_1 binds other_module_2{
            inner_function_name{

            }
        }
    }
    bindings{
        bound_token binds other_module{

        }
    }
    postamble{

    }
}

parse:
{
    NAME_TAG:name
    TYPE_TAG:module
}
"""
import sys
import traceback
import pprint as pp

def print_usage():
    print("usage: butcher path/to/cow/file")

# common tags
NAME_TAG        = '_NAME_'
PATH_TAG        = '_PATH_'
TEXT_TAG        = '_TEXT_'

# namespace and binding tags
CAPTURE_TAG     = '_CAPTURE_'
BINDS_TAG       = '_BINDS_'

# namespace-only tags
IMPORTS_TAG     = '_IMPORTS_'

# special tags
MODULE_TAG      = '_MODULE_'
TREE_TAG        = '_TREE_'
LEAF_TAG        = '_LEAF_'
BUILDER_TAG     = '_BUILDER_'

CALLS_TAG       = '_CALLS_'
ADD_CALL_TAG    = '_ADD_CALL_'

EXPORTS_TAG     = '_EXPORTS_'
ADD_EXPORT_TAG  = '_ADD_EXPORT_'
FUNCTION_EXPORT = '_FUNCTION_'
BINDING_EXPORT  = '_BINDING_'

ALL_TAGS = {
    NAME_TAG,PATH_TAG,TEXT_TAG, CAPTURE_TAG,BINDS_TAG,
    IMPORTS_TAG,MODULE_TAG,LEAF_TAG,TREE_TAG,BUILDER_TAG,
    CALLS_TAG,ADD_CALL_TAG
}

#keywords
PREAMBLE_KEYWORD = 'preamble'
POSTAMBLE_KEYWORD = 'postamble'
BINDINGS_KEYWORD = 'bindings'
DEPENDS_KEYWORD = 'depends'
NAMESPACE_KEYWORD = 'namespace'

CALLING_KEYWORD = 'call'
IF_KEYWORD = 'if'
ELSE_KEYWORD = 'else'

TEXT_KEYWORDS = {
    IF_KEYWORD,
    ELSE_KEYWORD,
    CALLING_KEYWORD,
}

POST_BINDING_KEYWORDS = {}

IMPORT_CAPTURE = 'imports'
BINDING_CAPTURE = 'binds'
PRE_BINDING_KEYWORDS = {
    # CALLING_CAPTURE:CALLS_TAG,
    IMPORT_CAPTURE:IMPORTS_TAG,
    BINDING_CAPTURE:BINDS_TAG
}

TYPE_TAG = '_TYPE_'

# closure types -- specify closure purpose, stored as a TYPE_TAG
ROOT_TYPE           = 'root'
MODULE_TYPE         = 'module'
NAMESPACE_TYPE      = 'namespace'
PREAMBLE_TYPE       = 'preamble'
POSTAMBLE_TYPE      = 'postamble'
FUNCTION_TYPE       = 'function'
IMPORT_TYPE         = 'import'
TEXT_KEYWORD_TYPE   = 'text_keyword'
BINDING_TYPE        = 'binding'
BOUND_TYPE          = 'bound'

COMMENT_DELIM = '#'

class Tree(): # for organizing dependencies
    def __init__(self,name,data):
        self.name = name
        self.data = data
        self.children = {}
    def graft(self,branch):
        # prevent cyclic grafts
        branch = branch.prune(self.name)
        self.children[branch.name] = branch
    def prune(self,name):
        deep_copy = Tree(self.name,self.data)
        for child in self.children:
            if self.children[child].name != name:
                deep_copy.graft(self.children[child].prune(name))
        return deep_copy
    def display(self,indent=0):
        print("{}{}".format(
            str.join('',['  ' for i in range(0,indent)]),
            self.name
        ))
        for child in self.children:
            self.children[child].display(indent+1)

class Stack(list): # for being pedantic
    def push(self,x): #ocd
        self.append(x)
    def path(self):
        return [layer[NAME_TAG] for layer in self]

def compiler_error(msg,path):
    print("Error: " + msg + ": {}".format(str.join("/",path)))
    traceback.print_stack()
    exit(1)

def insert_function_call(root,leaf):
    unique = False
    path = leaf[PATH_TAG]
    for node in path:
        if node not in root: # insert the rest of the path
            root[node] = {}
            unique = True
        root = root[node]
    if not unique:
        compiler_error("Namespace collision",path)
    root[LEAF_TAG] = leaf[TEXT_TAG]

FUNCTION_FINDER = {
    BUILDER_TAG:lambda path:insert_function_call(FUNCTION_FINDER,path),
}

# type resolver helper functions
def resolve_root_child(name,parent):
    return MODULE_TYPE

def resolve_module_child(name,parent):
    if name == PREAMBLE_KEYWORD:
        return PREAMBLE_TYPE
    elif name == POSTAMBLE_KEYWORD:
        return POSTAMBLE_TYPE
    elif name == DEPENDS_KEYWORD:
        return IMPORT_TYPE
    elif name == BINDINGS_KEYWORD:
        return BINDING_TYPE
    elif name == NAMESPACE_KEYWORD:
        return NAMESPACE_TYPE
    compiler_error("Unrecognized module child",[name])

def resolve_binding_child(name,parent):
    return BOUND_TYPE

def resolve_namespace_child(name,parent):
    return FUNCTION_TYPE

def resolve_function_child(name,parent):
    if name in TEXT_KEYWORDS:
        return TEXT_KEYWORD_TYPE
    elif not parent[TEXT_TAG]:
        parent[TYPE_TAG] = NAMESPACE_TYPE
        return FUNCTION_TYPE
    print(parent[TEXT_TAG])
    compiler_error("Closure in text-only closure",parent[PATH_TAG]+[name])

def resolve_text_only_child(name,parent):
    if name in TEXT_KEYWORDS:
        return TEXT_KEYWORD_TYPE
    else: # should we just error out?
        compiler_error("Closure in text-only closure",parent[PATH_TAG]+[name])

SORTING_HAT = {
    ROOT_TYPE:resolve_root_child,
    MODULE_TYPE:resolve_module_child,
    BINDING_TYPE:resolve_binding_child,
    NAMESPACE_TYPE:resolve_namespace_child,

    # text-only closures
    PREAMBLE_TYPE:resolve_text_only_child,
    POSTAMBLE_TYPE:resolve_text_only_child,
    FUNCTION_TYPE:resolve_function_child,
    TEXT_KEYWORD_TYPE:resolve_text_only_child,
    BOUND_TYPE:resolve_text_only_child,
    IMPORT_TYPE:resolve_text_only_child,
}

def strip_module_name(name):
    return name.split('/')[-1].split(".")[0]

def process_token(name,closure):
    name = str.join("",name).strip()
    if closure[TYPE_TAG] == IMPORT_TYPE:
        closure[IMPORTS_TAG][strip_module_name(name)] = parse_file(name)
        return
    closure[TEXT_TAG].append(name)

def get_closure_type(closure,parent):
    if TYPE_TAG not in closure:
        return SORTING_HAT[parent[TYPE_TAG]](closure[NAME_TAG],parent)
    return closure[TYPE_TAG]

def consume_modifiers(closure,text):
    capture_mode = 'none'
    for token in text:
        if token in PRE_BINDING_KEYWORDS:
            capture_mode = PRE_BINDING_KEYWORDS[token]
            closure[capture_mode] = []
            if token == IMPORT_CAPTURE:
                closure[TYPE_TAG] = NAMESPACE_TYPE
        elif capture_mode in closure:
            closure[capture_mode].insert(0,token) # prefer modules imported "later"
        else:
            compiler_error(
                "Erroneous text in function signature",
                closure[PATH_TAG])
    while text: #clear the list
        text.pop()

def module_add_export(module,export,export_type):
    name = export[NAME_TAG]
    subtree = Tree(name,export)
    if name in  module[EXPORTS_TAG][export_type]:
        compiler_error("Duplicate binding",export[PATH_TAG])
    module[EXPORTS_TAG][export_type][name] = subtree

def export_token(parent,export,export_type):
    parent[ADD_EXPORT_TAG][export_type](export)

def make_binding_exporter(parent):
    return (lambda binding: export_token(parent,binding,BINDING_EXPORT))

def make_function_exporter(parent):
    return (lambda function: export_token(parent,function,FUNCTION_EXPORT))

def make_closure(parent):
    closure = {}
    if parent[TYPE_TAG] == ROOT_TYPE:
        parent[MODULE_TAG] = closure
    if parent[TYPE_TAG] == NAMESPACE_TYPE:
        name = parent[TEXT_TAG].pop(0)
        closure[PATH_TAG] = parent[PATH_TAG] + [name]
        consume_modifiers(closure,parent[TEXT_TAG])
    else: # other types do not have modifiers
        name = parent[TEXT_TAG].pop()
        closure[PATH_TAG] = parent[PATH_TAG] + [name]
        
    closure[NAME_TAG] = name
    closure[TEXT_TAG] = []
    closure[TYPE_TAG] = get_closure_type(closure,parent)
    
    # rooted export structuring
    if closure[TYPE_TAG] == TEXT_KEYWORD_TYPE:
        closure[PATH_TAG].pop()
    elif closure[TYPE_TAG] == IMPORT_TYPE:
        closure[IMPORTS_TAG] = {}
    elif closure[TYPE_TAG] == BINDING_TYPE:
        closure[ADD_EXPORT_TAG] = {}
        closure[ADD_EXPORT_TAG][BINDING_EXPORT] = make_binding_exporter(parent)
    elif closure[TYPE_TAG] == NAMESPACE_TYPE:
        # only expose top-level functions
        closure[ADD_EXPORT_TAG] = {}
        if parent[TYPE_TAG] == MODULE_TYPE:
            closure[ADD_EXPORT_TAG][FUNCTION_EXPORT] = make_function_exporter(parent)
        else:
            closure[ADD_EXPORT_TAG][FUNCTION_EXPORT] = (lambda function: 0)
    elif closure[TYPE_TAG] == FUNCTION_TYPE:
        # these can transform into namespaces if they have nested functions
        closure[ADD_EXPORT_TAG] = {
            FUNCTION_EXPORT: (lambda function: 0),
        }
        parent[ADD_EXPORT_TAG][FUNCTION_EXPORT](closure)
    elif closure[TYPE_TAG] == BOUND_TYPE:
        parent[ADD_EXPORT_TAG][BINDING_EXPORT](closure)
    elif closure[TYPE_TAG] == MODULE_TYPE:
        closure[EXPORTS_TAG] = {
            BINDING_EXPORT:{},
            FUNCTION_EXPORT:{},
        }
        closure[ADD_EXPORT_TAG] = {
            BINDING_EXPORT:lambda b:module_add_export(closure,b,BINDING_EXPORT),
            FUNCTION_EXPORT:lambda f:module_add_export(closure,f,FUNCTION_EXPORT),
        }

    # rooted function call structuring
    if closure[TYPE_TAG] == BOUND_TYPE or closure[TYPE_TAG] == FUNCTION_TYPE:
        closure[CALLS_TAG] = []

    # text keyword closures remain in the text section
    if name in TEXT_KEYWORDS:
        parent[TEXT_TAG].append(closure)
        if name == CALLING_KEYWORD:
            parent[CALLS_TAG].append(closure)
    elif name in parent:
        compiler_error("Namespace collision",parent[PATH_TAG])
    else:
        parent[name] = closure            
    return closure

def parse_closures(source):
    name = []
    root = { # set up a root "closure" to build from
        PATH_TAG: [],
        NAME_TAG: "root",
        TEXT_TAG: [],
        TYPE_TAG: ROOT_TYPE,
    }
    curr = root
    stack = Stack()
    # TODO: better parsing
    while True:
        char = source.read(1)
        if not char:
            break
        if char == '{':
            if name:
                process_token(name,curr)
            tmp = make_closure(curr)
            stack.push(curr)
            curr = tmp
            name = []
        else:
            if char.isspace() or char == '}' or char == COMMENT_DELIM:
                if name:
                    process_token(name,curr)
                    name = []
                if char == '}':
                    curr = stack.pop()
                    if not stack:
                        break
                elif char == COMMENT_DELIM:
                    source.readline() # skip the rest of the line
                continue
            name += char
    
    return root

def parse_file(file):
    # parse the file into nexted closure format
    with open(file) as source:
        module = parse_closures(source)[MODULE_TAG]

    # resolve bindings
        # resolve function calls within bindings
    for binding in module[EXPORTS_TAG][BINDING_EXPORT]:
        graft_caller_dependencies(module,module[EXPORTS_TAG][BINDING_EXPORT][binding])
        module[EXPORTS_TAG][BINDING_EXPORT][binding].display()
    # resolve imported function paths
        # graft function tree branches onto root tree
    graft_imported_modules(module)
    expand_function_paths(module)

    # resolve function calls and nesting
        # use PATH_TAG to find target table addresses

    return module

def main():
    # parse the base module
    base_module = parse_file(sys.argv[1])
    pp.pprint(base_module)
    # pp.pprint(FUNCTION_CALLS)

    # resolve namespace names into IDs -- do some tree reduction magic?

    # resolve text tokens into code blobs
        # resolve all bound tokens in namespace
        # resolve bound function calls into absolute
        # resolve inline closures into control structures

    # resolve function calls into stack operations

    # assemble function call table

    # resolve function closures into countdown blocks

    # resolve *amble closures into code blobs

def module_find_function(module,path):
    curr = module
    unfinished = []
    for node in path:
        if not unfinished:
            if node == module[NAME_TAG]:
                continue
            if node in curr:
                curr = curr[node]
            else:
                unfinished.append(node)
        else:
            unfinished.append(node)
    if unfinished: # start looking in imported modules
        # unfinished calls are due to namespace imports
        if curr[TYPE_TAG] != NAMESPACE_TYPE: 
            compiler_error("Malformed function call",path)
        if IMPORTS_TAG not in curr:
            return False,False
        for external in curr[IMPORTS_TAG]: # imports are in precedence order
            module_imports = module[DEPENDS_KEYWORD][IMPORTS_TAG]
            if not external in module_imports:
                compiler_error("Imported module not listed as dependency",curr[PATH_TAG])

            # search in the imported module
            imported_function,containing_module = module_find_function(
                module_imports[external],
                [external] + [NAMESPACE_KEYWORD] + unfinished)
            if imported_function: # found it
                return imported_function,containing_module
        compiler_error("Unable to find function for call",path)
    return curr,module

def graft_caller_dependencies(module,root,ignore=set()):
    closure = root.data
    for call in closure[CALLS_TAG]:
        full_path = build_function_call_path(call,closure[TYPE_TAG])
        full_path_str = str.join("/",full_path)
        if full_path_str in ignore:
            return
        ignore.add(full_path_str)
        # print(call)
        target_function,containing_module = module_find_function(module,full_path)
        if not target_function:
            compiler_error("Unable to find function for call",full_path)
        dependency = Tree(target_function[NAME_TAG],target_function)
        graft_caller_dependencies(containing_module,dependency,ignore)
        root.graft(dependency)

def graft_imported_modules(module):
    # for call in module[CALLS_TAG]:
    #     path = graft_path(call)
    #     deepest,remaining = attempt_path_traverse(module,path)
    #     if not remaining: # successfully found target function
    #         # do some linking stuff
    #         return 
    #     # look in the import section of the deepest context we reached
    #     if deepest[TYPE_TAG] != NAMESPACE_TYPE:
    #         compiler_error("Malformed function call path",path)
    #     if IMPORTS_TAG not in deepest:
    #         err_no_target_for_path(path)
    #     # start looking in imported modules
    #     for external in deepest[IMPORTS_TAG]:
    #         if external not in module[DEPENDS_KEYWORD][IMPORTS_TAG]:
    #             err_no_target_for_path(path)
    #         # TODO: processed modules should expose functions with EXPORTS_TAG
    #         # new_namespace = module[DEPENDS_KEYWORD][IMPORTS_TAG][external][EXPORTS_TAG]
    pass

def err_no_target_for_path(path):
    compiler_error("Unable to locate target for call",path)

def build_function_call_path(call_closure,calling_type):
    prefix = call_closure[PATH_TAG][0:-1]
    # print("before: {}".format(prefix))
    if calling_type == BOUND_TYPE:
        prefix = [prefix[0]] + [NAMESPACE_KEYWORD]
    path = prefix + call_closure[TEXT_TAG]
    # print("after: {}".format(path))
    return path

def attempt_path_traverse(module,path):
    curr = module
    unfinished = []
    for node in path:
        if not unfinished:
            if node == module[NAME_TAG]:
                continue
            if node in curr:
                curr = curr[node]
            else:
                unfinished.append(node)
        else:
            unfinished.append(node)

    return curr,unfinished


def expand_dependencies():
    pass

# traverse module structure and expand call closure text into relative function
# paths
def expand_function_paths(module):
    pass
     


if __name__ == '__main__':
    main()