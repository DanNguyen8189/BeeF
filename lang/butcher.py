#!/usr/bin/env python2.7
from __future__ import print_function

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
TYPE_TAG = '_TYPE_'

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

FINALIZE_TAG = '_FINALIZE_'

ALL_TAGS = {
    NAME_TAG,PATH_TAG,TEXT_TAG, CAPTURE_TAG,BINDS_TAG,TYPE_TAG,
    IMPORTS_TAG,MODULE_TAG,LEAF_TAG,TREE_TAG,BUILDER_TAG,
    CALLS_TAG,ADD_CALL_TAG,EXPORTS_TAG,ADD_EXPORT_TAG,
    FINALIZE_TAG
}

#keywords
PREAMBLE_KEYWORD    = 'preamble'
POSTAMBLE_KEYWORD   = 'postamble'
BINDINGS_KEYWORD    = 'bindings'
DEPENDS_KEYWORD     = 'depends'
NAMESPACE_KEYWORD   = 'namespace'

CALLING_KEYWORD     = 'call'
IF_KEYWORD          = 'if'
ELSE_KEYWORD        = 'else'

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

#TODO: use disjoint sets for dependency handling
# function calls create a directional dependency from the caller to the callee
# each namespace maintains a dictionary of accessible named closures
# each function maintains a set of names it is dependant upon
# calls to other functions in the same scope will merge callee set into caller set
# nested dependencies should be resolved recursively
# end goal: each namespace layer should be represented as a single subset of 
#   named closures in the namespace
#   

# Resolving Dependencies:
#   1. Generate inter-namespace function dependency tree

# module[EXPORTS_TAG] = {
#   FUNCTION_EXPORT: {
#       NAME_TAG:namespace
#       function_1: {<dependencies>}
#       function_2: {<dependencies>}
#       nested_namespace: {
#           NAME_TAG: nested_namespace
#       }
#   }
#   BINDING_EXPORT:  {
# 
#   }
# }

class Namespace():
    def __init__(self,namespace,closure_type=NAMESPACE_TYPE):
        # pass in the root module
        self.name = namespace[NAME_TAG]
        self.nodes = {}     # functions in this namespace
        self.sinks = {}     # nested namespaces visible in this scope
        self.imports = []   # imported namespaces
        self.binds = []     # imported bindings
        if closure_type == NAMESPACE_TYPE:
            self.ingest_namespace(namespace)
        else:
            self.ingest_module(namespace)

    def ingest_module(self,module):
        for closure in module:
            if closure == BINDINGS_KEYWORD: # extract from imported modules
                self.binds = [module[closure][binding] for binding in module[closure] if binding not in ALL_TAGS]
            elif closure in ALL_TAGS: # skip any other tags
                continue
            elif closure == NAMESPACE_KEYWORD:
                self.ingest_namespace(module[closure])
                return

    def ingest_namespace(self,namespace):
        for closure in namespace:
            if closure == IMPORTS_TAG: # extract from imported modules
                self.imports = namespace[closure]
                continue
            elif closure == BINDS_TAG: # extract from imported modules
                self.binds   = namespace[closure]
                continue
            elif closure in ALL_TAGS: # skip any other tags
                continue
            closure_name = namespace[closure][NAME_TAG]
            closure_type = namespace[closure][TYPE_TAG]
            if closure_type == FUNCTION_TYPE:
                self.nodes[closure_name] = DependencyNode(namespace[closure],self)
            elif closure_type == NAMESPACE_TYPE:
                self.sinks[closure_name] = Namespace(namespace[closure])

    # carry out the actual namespace importing    
    def resolve_imports(self,module_imports):
        for sink in self.sinks:
            self.sinks[sink].resolve_imports(module_imports)
        for module in self.imports:
            if module not in self.sinks:
                if module not in module_imports:
                    compiler_error("Could not find module",[module])
                self.sinks[module] = module_imports[module]

    def link_dependencies(self):
        self.link_internal()
        self.link_nested()

    # resolve internal dependencies    
    def link_internal(self):
        for sink in self.sinks:
            self.sinks[sink].link_internal()
        for node in self.nodes:
            self.nodes[node].reset_net_dependents()
            self.nodes[node].initial_dep_recurse()
        for node in self.nodes:
            self.nodes[node].deep_dep_recurse(self.nodes)

    # link with nested namespaces
    def link_nested(self):
        for sink in self.sinks:
            self.sinks[sink].link_nested()
        for node in self.nodes:
            self.nodes[node].initial_nested_recurse()
    
class DependencyLayer():
    def __init__(self,namespace):
        self.name      = namespace.name
        self.namespace = namespace
        self.sublayers = {}
        self.resolved  = False
        self.linked    = False
        self.compiled  = False

        self.id = -1

        # link the namespace dependencies
        self.namespace.link_dependencies()
        pass

    # given a resolved Namespace and a set of tokens required, compile a
    # dependency layer
    def resolve(self,entry_points):
        if not entry_points: # we dont need this layer
            return
        # merge internal token sets of entry points
        internal_token_layer = set()
        for dependency in entry_points:
            if len(dependency) != 1: # only base namespace is visible, no nesting
                compiler_error("Invalid entry point function call",dependency)
            dependency = dependency[0]
            if dependency not in self.namespace.nodes:
                compiler_error("Unable to find entry point",[dependency])
            internal_token_layer.add(dependency)
            internal_token_layer.update(self.namespace.nodes[dependency].dependencies)

        # for each imported namespace, merge dependency token sets of 
        # tokens in merged internal token set
        self.layer_deps = {}
        print("{} token layer: {}".format(self.name,internal_token_layer))
        for sink in self.namespace.sinks:
            self.sublayers[sink] = DependencyLayer(self.namespace.sinks[sink])
            sink_deps = set()
            for token in internal_token_layer:
                # print("{} nested deps: {}".format(token,self.namespace.nodes[token].nested_dependencies))
                if sink in self.namespace.nodes[token].nested_dependencies:
                    sink_deps.update(self.namespace.nodes[token].nested_dependencies[sink])
            self.layer_deps[sink] = sink_deps
            # print("Compiling dependencies on {}: {}".format(sink,sink_deps))
            
        # pp.pprint(self.layer_deps)

        # for each imported namespace, use its finalized dependency token set
        # to compile it into a dependency layer, add it as a child of this layer
        removal_candidates = []
        for layer in self.sublayers:
            if not self.layer_deps[layer]:
                removal_candidates.append(layer)
                continue
            layer_entry_points = [[token] for token in self.layer_deps[layer]]
            print("Entry points to {} -> {}".format(layer,layer_entry_points))
            self.sublayers[layer].resolve(layer_entry_points)

        # clean up unused sublayers
        for layer in removal_candidates:
            del self.sublayers[layer]
        
        self.resolved = True

        self.resolved_token_layer = list(internal_token_layer)
        
        return
    
    def link(self):
        if not self.resolved:
            compiler_error("Attempted to link unresolved layer",[self.name])

        # organize this dependency layer into an ordered list, using some
        # deterministic optimization critereon -> net incoming/outgoing dpes
            # imported code at the bottom, since it has no dependencies on 
            # importing code
            # nested namespaces at the bottom too, for the same reason
        resolved_node_layer = [self.namespace.nodes[node] for node in self.resolved_token_layer]
        resolved_node_layer.sort(DependencyNode.sort)
        fid = 1
        for node in resolved_node_layer:
            # compute function call IDs from list order
            node.fid = fid
            fid = fid + 1
            print("{} ID: {}".format(node.name,node.fid))

        # link local namespace function calls
        for node in resolved_node_layer:
            node.link_local(self)

        # use dependency tokens to grab refs to DependencyNode objects
        # recursively link() all sublayers
        layer_list = []
        layer_id = fid
        for layer in self.sublayers:
            self.sublayers[layer].link()
            self.sublayers[layer].id = layer_id # set after linking, so that local-scope is always -1
            for node in resolved_node_layer:
                node.link(self.sublayers[layer])
            layer_list.append(self.sublayers[layer])
            layer_id = layer_id + 1

        self.resolved_namespace_layer = resolved_node_layer + layer_list

        for node in resolved_node_layer:
            print("{} links: {}".format(node.name,node.links))

        self.linked = True
        pass

    def build(self):
        if not self.linked:
            compiler_error("Cannot build unlinked layer",[self.name])
        
        # recursively build subunits
        for node in self.resolved_namespace_layer:
            node.build()

        # expand function text bindings into assembly

        # insert virtual machine flags?

        # wrap function text in functional counting blocks

        # concatenate functional blocks and sublayers into namespace ID table

        # wrap namespace ID table in execution loop header and footer
        pass


class DependencyNode():
    def __init__(self,function,container):
        # extract core information from function closure
        self.name  = function[NAME_TAG]
        self.text  = function[TEXT_TAG][:]
        self.calls = function[CALLS_TAG][:]
        self.net_dependent = 0
        self.fid = -1
        self.container = container
        self.links = [(-1,-1)]*len(self.calls)

    def reset_net_dependents(self):
        self.net_dependent = 0

    def add_dependent(self):
        self.net_dependent = self.net_dependent + 1

    def remove_dependent(self):
        self.net_dependent = self.net_dependent - 1

    def initial_dep_recurse(self):
        self.dependencies = set()
        for i in range(len(self.calls)-1,-1,-1):
            if len(self.calls[i]) == 1: # in-scope function call
                target = self.calls[i][0]
                self.remove_dependent()
                self.dependencies.add(target)

    def deep_dep_recurse(self,nodes):
        old_size = 0
        new_size = len(self.dependencies)
        while old_size < new_size:
            self.do_dep_recurse(nodes)
            old_size = new_size
            new_size = len(self.dependencies)
        # pp.pprint(self.dependencies)


    def do_dep_recurse(self,nodes):
        for node in self.dependencies.copy():
            new_deps =  nodes[node].dependencies - self.dependencies
            self.dependencies.update(new_deps)
            for dep in new_deps:
                nodes[dep].add_dependent()

    def initial_nested_recurse(self):
        self.nested_dependencies = {}
        # print("{} nested dependencies: ".format(self.name))
        for i in range(len(self.calls)-1,-1,-1):
            if len(self.calls[i]) == 2: # nested-scope function call
                # print(self.calls[i])
                target = self.calls[i]
                if not target[0] in self.nested_dependencies:
                    self.nested_dependencies[target[0]] = set()
                self.nested_dependencies[target[0]].add(target[1])
        # pp.pprint(self.nested_dependencies)
        return 

    # grab refs to nodes in this layer
    def link(self,layer):
        if layer.name == self.container.name:
            self.link_local(layer)
            return

        for i in range(0,len(self.calls)):
            call = self.calls[i]
            if call[0] == layer.name:
                self.links[i] = (layer.id,layer.namespace.nodes[call[1]].fid)
        return

    def link_local(self,layer):
        for i in range(0,len(self.calls)):
            if len(self.calls[i]) == 1:
                call = self.calls[i][0]
                self.links[i] = (layer.id,layer.namespace.nodes[call].fid)
        return
    
    def sort(self,other):
        if self.net_dependent > other.net_dependent:
            return 1
        elif other.net_dependent > self.net_dependent:
            return -1
        return 0

    def build(self):
        # keep things divided by tokens, for now
        self.raw_text = ["<_>"] # pop the null cid from the stack
        call_counter = 0
        old_cid = 0
        for token in self.text:
            call_counter,old_cid = self.recursive_build(self.raw_text,token,call_counter,old_cid)
        print(self.name+": "+str.join("",self.raw_text))
        return

    def recursive_build(self,build_list,token,call_counter,old_cid):
        if type(token) is str:
            self.raw_text.append(token) 
        else: # inline keyword
            if token[NAME_TAG] == CALLING_KEYWORD:
                link = self.links[call_counter]
                link_text,old_cid = self.expand_link(link,old_cid)
                build_list.append(link_text)
                call_counter = call_counter + 1
            else:
                for tk in token[TEXT_TAG]:
                    call_counter,old_cid = self.recursive_build(build_list,tk,call_counter,old_cid)

        return call_counter,old_cid

    def expand_link(self,link,old_cid):
        # assume we are adjacent to control cell
        function_call = ["<"] # move into control cell
        if link[0] == -1: # local scope
            cid = link[1] # get the function call id directly
            function_call.append(adjust_cell_value(old_cid,cid))
            function_call.append("^")
        else:             # nested scope
            cid = link[0] # get the scope call id
            fid = link[1]
            # push a value to index into the nested scope
            function_call.append(adjust_cell_value(old_cid,fid))
            function_call.append("^")

            # push a value to index into the function
            # id_diff = fid - cid
            # adjc = "+" if id_diff < 0 else "-"
            # function_call.append((adjc*abs(id_diff)) + "^")
            function_call.append(adjust_cell_value(cid,fid))
            function_call.append("^")

            cid = fid # so we can return the value we just pushed

        function_call.append(">") # move back to starting cell
        return  str.join("",function_call),cid

def adjust_cell_value(curr_value,target_value):
    return "x"


def indented_print(name,indent):
    print("{}{}".format(
        str.join('',['  ' for i in range(0,indent)]),
        name
    ))

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
    compiler_error("Unrecognized module member",[name])

def resolve_binding_child(name,parent):
    return BOUND_TYPE

def resolve_namespace_child(name,parent):
    return FUNCTION_TYPE

def resolve_function_child(name,parent):
    if name in TEXT_KEYWORDS:
        return TEXT_KEYWORD_TYPE
    elif not parent[TEXT_TAG]:
        upgrade_function_to_namespace(parent)
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

def upgrade_function_to_namespace(closure):
    closure[TYPE_TAG] = NAMESPACE_TYPE
    # closure[TREE_TAG] = closure[TREE_TAG].upgrade_to_layer()

def strip_module_name(name):
    return name.split('/')[-1].split(".")[0]

def process_token(name,closure):
    name = str.join("",name).strip()
    if closure[TYPE_TAG] == IMPORT_TYPE:
        exported_namespace = parse_file(name)[EXPORTS_TAG]
        external_module_name = strip_module_name(name)
        module_imports = closure[IMPORTS_TAG]
        # print(closure[PATH_TAG])
        # print(module_imports)
        module_imports[external_module_name] = exported_namespace
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
                upgrade_function_to_namespace(closure)
        elif capture_mode in closure:
            closure[capture_mode].insert(0,token) # prefer modules imported "later"
            # if capture_mode == IMPORTS_TAG:
            #     closure[TREE_TAG].add_future_contents(token)
        else:
            compiler_error(
                "Erroneous text in function signature",
                closure[PATH_TAG])
    while text: #clear the list
        text.pop()

# def link_parent_closure(parent,child):
#     parent[TREE_TAG].link(child[TEXT_TAG])

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
    closure[FINALIZE_TAG] = (lambda: 0) # do nothing
    
    # type-specific tags
    if closure[TYPE_TAG] == BOUND_TYPE or closure[TYPE_TAG] == FUNCTION_TYPE or closure[TYPE_TAG] == PREAMBLE_TYPE:
        closure[CALLS_TAG] = []
    elif closure[TYPE_TAG] == IMPORT_TYPE:
        closure[IMPORTS_TAG] = {}
    elif closure[TYPE_TAG] == MODULE_TYPE:
        closure[EXPORTS_TAG] = None


    # text keyword closures remain in the text section
    if name in TEXT_KEYWORDS:
        parent[TEXT_TAG].append(closure)
        closure[CALLS_TAG] = parent[CALLS_TAG]
        if name == CALLING_KEYWORD:
            parent[CALLS_TAG].append(closure[TEXT_TAG])
            # closure[FINALIZE_TAG] = (lambda: print(parent[CALLS_TAG]))
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
                    curr[FINALIZE_TAG]()
                    curr = stack.pop()
                    if not stack:
                        break
                elif char == COMMENT_DELIM:
                    source.readline() # skip the rest of the line
                continue
            name += char
    
    return root

# def import_namespace(tree,name):

def parse_file(file):
    # parse the file into nexted closure format
    with open(file) as source:
        module = parse_closures(source)[MODULE_TAG]

    base_namespace = Namespace(module,closure_type=MODULE_TYPE)
    if DEPENDS_KEYWORD in module:
        base_namespace.resolve_imports(module[DEPENDS_KEYWORD][IMPORTS_TAG])
    module[EXPORTS_TAG] = base_namespace

    return module

def main():
    # parse the base module
    base_module = parse_file(sys.argv[1])
    # base_module[EXPORTS_TAG][FUNCTION_EXPORT].print_contents()
    pp.pprint(base_module)
    base_layer = DependencyLayer(base_module[EXPORTS_TAG])

    base_layer.resolve(base_module[PREAMBLE_KEYWORD][CALLS_TAG])
    base_layer.link()
    base_layer.build()


    # collect dependencies from dependency tree

    # traverse the tree and link it to the function objects

    # resolve namespace names into IDs -- do some tree reduction magic?

    # resolve text tokens into code blobs
        # resolve all bound tokens in namespace
        # resolve bound function calls into absolute
        # resolve inline closures into control structures

    # resolve function calls into stack operations

    # assemble function call table

    # resolve function closures into countdown blocks

    # resolve *amble closures into code blobs  

if __name__ == '__main__':
    main()