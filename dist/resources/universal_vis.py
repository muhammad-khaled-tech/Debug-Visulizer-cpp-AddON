"""
Antigravity C++ Visualizer - Universal GDB Python Script
=========================================================

This script provides automatic visualization of C++ data structures
(Linked Lists, Trees, Graphs, Arrays) by introspecting objects via GDB's Python API.

Usage in GDB:
    (gdb) source universal_vis.py
    (gdb) vis head              # Visualize linked list starting at 'head'
    (gdb) vis root              # Visualize tree starting at 'root'
    (gdb) vis arr 10            # Visualize array of 10 elements
    (gdb) vis list.head slow fast  # Two-pointer visualization

The output is JSON matching the vscode-debug-visualizer's GraphVisualizationData schema.
"""

import gdb
import json

# Global state for graph construction
visited_nodes = set()
nodes = []
edges = []

def reset_state():
    """Reset global state before each visualization."""
    global visited_nodes, nodes, edges
    visited_nodes = set()
    nodes = []
    edges = []

def get_address(val):
    """Helper to get hex address from GDB value."""
    try:
        return str(val.address).split()[0]
    except:
        return str(val)

def get_pointer_address(ptr_val):
    """Get the address a pointer points to."""
    try:
        ptr_str = str(ptr_val)
        if ptr_str.startswith("0x"):
            return ptr_str.split()[0]
        return ptr_str
    except:
        return None

def find_data_field(val):
    """Try to find a meaningful data field in the struct."""
    data_field_names = ["data", "val", "value", "id", "key", "info", "elem", "item"]
    
    for field_name in data_field_names:
        try:
            field_val = val[field_name]
            return str(field_val)
        except:
            continue
    
    try:
        val_type = val.type
        if val_type.code == gdb.TYPE_CODE_STRUCT:
            for field in val_type.fields():
                try:
                    field_val = val[field.name]
                    if field_val.type.code != gdb.TYPE_CODE_PTR:
                        return f"{field.name}={field_val}"
                except:
                    continue
    except:
        pass
    
    return "Node"

def find_pointer_fields(val):
    """Find all pointer fields in a struct."""
    pointer_fields = []
    try:
        val_type = val.type
        if val_type.code == gdb.TYPE_CODE_STRUCT:
            for field in val_type.fields():
                try:
                    field_val = val[field.name]
                    if field_val.type.code == gdb.TYPE_CODE_PTR:
                        pointer_fields.append(field.name)
                except:
                    continue
    except:
        pass
    return pointer_fields

def traverse_doubly_linked_list(val, next_name="next", prev_name="previous", 
                                 highlight_addrs=None, highlight_labels=None,
                                 depth=0, max_depth=50):
    """
    Traverse a doubly linked list, showing BOTH next and previous pointers.
    
    Args:
        highlight_addrs: Set of addresses to highlight (for two-pointer viz)
        highlight_labels: Dict mapping address -> label (e.g., "slow", "fast")
    """
    global visited_nodes, nodes, edges
    
    if highlight_addrs is None:
        highlight_addrs = set()
    if highlight_labels is None:
        highlight_labels = {}
    
    if depth > max_depth:
        nodes.append({"id": "truncated", "label": "... (max depth)", "color": "#ff6b6b"})
        return
    
    try:
        addr = get_address(val)
        
        try:
            if int(val.address) == 0:
                return
        except:
            pass
            
        if addr in visited_nodes:
            return addr
            
        visited_nodes.add(addr)

        # Determine node appearance
        label = find_data_field(val)
        
        # Check if this node should be highlighted
        if addr in highlight_addrs:
            node_color = "#ff6b6b"  # Red for highlighted
            if addr in highlight_labels:
                label = f"{label}\n[{highlight_labels[addr]}]"
        elif depth == 0:
            node_color = "#69db7c"  # Green for head
        else:
            node_color = "#a5d8ff"  # Light blue
        
        nodes.append({
            "id": addr,
            "label": label,
            "color": node_color,
            "shape": "box"
        })

        # Follow 'next' pointer
        try:
            next_ptr = val[next_name]
            if int(next_ptr) != 0:
                next_addr = get_pointer_address(next_ptr)
                edges.append({
                    "from": addr,
                    "to": next_addr if next_addr in visited_nodes else get_address(next_ptr.dereference()),
                    "label": "next",
                    "color": "#228be6",  # Blue arrow pointing right
                    "arrows": "to"
                })
                traverse_doubly_linked_list(
                    next_ptr.dereference(), next_name, prev_name,
                    highlight_addrs, highlight_labels, depth + 1, max_depth
                )
        except gdb.error:
            pass
        except:
            pass
            
        # Show 'previous' pointer edge (but don't traverse it - we traverse forward)
        try:
            prev_ptr = val[prev_name]
            if int(prev_ptr) != 0:
                prev_addr = get_pointer_address(prev_ptr)
                # Add edge back to previous (it should already exist as a node)
                edges.append({
                    "from": addr,
                    "to": prev_addr,
                    "label": "prev",
                    "color": "#fab005",  # Orange/yellow arrow pointing left
                    "dashes": True,  # Dashed line to distinguish
                    "arrows": "to"
                })
        except gdb.error:
            pass
        except:
            pass

    except Exception as e:
        if len(nodes) == 0:
            nodes.append({"id": "error", "label": f"Error: {str(e)}", "color": "#ff6b6b"})

def traverse_linked_list(val, ptr_name="next", highlight_addrs=None, 
                         highlight_labels=None, depth=0, max_depth=50):
    """Recursive traversal for singly Linked List patterns."""
    global visited_nodes, nodes, edges
    
    if highlight_addrs is None:
        highlight_addrs = set()
    if highlight_labels is None:
        highlight_labels = {}
    
    if depth > max_depth:
        nodes.append({"id": "truncated", "label": "... (max depth)", "color": "#ff6b6b"})
        return
    
    try:
        addr = get_address(val)
        
        try:
            if int(val.address) == 0:
                return
        except:
            pass
            
        if addr in visited_nodes:
            return addr
            
        visited_nodes.add(addr)

        label = find_data_field(val)
        
        # Check highlighting
        if addr in highlight_addrs:
            node_color = "#ff6b6b"  # Red
            if addr in highlight_labels:
                label = f"{label}\n[{highlight_labels[addr]}]"
        elif depth == 0:
            node_color = "#69db7c"  # Green
        else:
            node_color = "#a5d8ff"  # Blue
        
        nodes.append({
            "id": addr,
            "label": label,
            "color": node_color,
            "shape": "box"
        })

        try:
            next_ptr = val[ptr_name]
            next_ptr_addr = get_pointer_address(next_ptr)
            
            if next_ptr_addr and int(next_ptr) != 0:
                edges.append({
                    "from": addr,
                    "to": next_ptr_addr if next_ptr_addr in visited_nodes else get_address(next_ptr.dereference()),
                    "label": ptr_name
                })
                traverse_linked_list(next_ptr.dereference(), ptr_name, 
                                     highlight_addrs, highlight_labels, depth + 1, max_depth)
        except gdb.error:
            pass
        except:
            pass

    except Exception as e:
        if len(nodes) == 0:
            nodes.append({"id": "error", "label": f"Error: {str(e)}", "color": "#ff6b6b"})

def traverse_binary_tree(val, left_name="left", right_name="right", 
                         highlight_addrs=None, highlight_labels=None,
                         depth=0, max_depth=30):
    """Recursive traversal for Binary Tree patterns."""
    global visited_nodes, nodes, edges
    
    if highlight_addrs is None:
        highlight_addrs = set()
    if highlight_labels is None:
        highlight_labels = {}
    
    if depth > max_depth:
        return None
    
    try:
        addr = get_address(val)
        
        try:
            if int(val.address) == 0:
                return None
        except:
            pass
            
        if addr in visited_nodes:
            return addr
            
        visited_nodes.add(addr)

        label = find_data_field(val)
        
        if addr in highlight_addrs:
            node_color = "#ff6b6b"
            if addr in highlight_labels:
                label = f"{label}\n[{highlight_labels[addr]}]"
        elif depth == 0:
            node_color = "#69db7c"
        else:
            node_color = "#a5d8ff"
        
        nodes.append({
            "id": addr,
            "label": label,
            "color": node_color,
            "shape": "ellipse"
        })

        # Follow left child
        try:
            left_ptr = val[left_name]
            if int(left_ptr) != 0:
                left_addr = traverse_binary_tree(
                    left_ptr.dereference(), left_name, right_name,
                    highlight_addrs, highlight_labels, depth + 1, max_depth
                )
                if left_addr:
                    edges.append({
                        "from": addr,
                        "to": left_addr if left_addr in visited_nodes else get_address(left_ptr.dereference()),
                        "label": "L",
                        "color": "#228be6"
                    })
        except:
            pass

        # Follow right child
        try:
            right_ptr = val[right_name]
            if int(right_ptr) != 0:
                right_addr = traverse_binary_tree(
                    right_ptr.dereference(), left_name, right_name,
                    highlight_addrs, highlight_labels, depth + 1, max_depth
                )
                if right_addr:
                    edges.append({
                        "from": addr,
                        "to": right_addr if right_addr in visited_nodes else get_address(right_ptr.dereference()),
                        "label": "R",
                        "color": "#fab005"
                    })
        except:
            pass

        return addr

    except Exception as e:
        if len(nodes) == 0:
            nodes.append({"id": "error", "label": f"Error: {str(e)}", "color": "#ff6b6b"})
        return None

def visualize_array(expr, size):
    """
    Visualize a C/C++ array as a graph.
    
    Args:
        expr: Array expression (name of array or pointer)
        size: Number of elements to visualize
    """
    reset_state()
    
    try:
        # Create HTML TABLE for robust contiguous visualization
        highlight_indices = set() # Initialize empty set to avoid NameError
        arr = gdb.parse_and_eval(expr)
        
        # Colors (light blue background for cells)
        bg_color = "#339af0"
        text_color = "white"
        
        # Build HTML
        html = f"""
        <div style="font-family: monospace; font-size: 14px;">
            <div style="margin-bottom: 5px;">Array: {expr}</div>
            <table style="border-collapse: collapse; border: 1px solid #555;">
                <tr>
        """
        
        # Header Row (Indices)
        for i in range(size):
            html += f'<td style="border: 1px solid #555; padding: 4px; text-align: center; color: #888; font-size: 10px;">{i}</td>'
        
        html += "</tr><tr>"
        
        # Value Row
        for i in range(size):
            try:
                elem = arr[i]
                elem_val = str(elem)
                if len(elem_val) > 10: elem_val = elem_val[:7] + "..."
            except:
                elem_val = "?"
            
            # Highlight style
            cell_bg = "#ff6b6b" if i in highlight_indices else "#228be6"
            
            html += f'<td style="border: 1px solid #555; background-color: {cell_bg}; color: white; padding: 8px; min-width: 30px; text-align: center;">{elem_val}</td>'
            
        html += """
                </tr>
            </table>
        </div>
        """

        return json.dumps({
            "kind": {"text": True},
            "text": html,
            "mimetype": "text/html" # Try to hint HTML, though 'text' kind usually handles md/html mix
        })
        
    except Exception as e:
        return json.dumps({
            "kind": {"text": True},
            "text": f"Error: {str(e)}"
        })

def detect_structure_type(val):
    """
    Detect structure type: linked_list, doubly_linked_list, binary_tree, or generic.
    """
    pointer_fields = find_pointer_fields(val)
    
    # Check for doubly linked list FIRST
    prev_names = ["previous", "prev", "_prev", "pPrev", "m_prev", "blink"]
    next_names = ["next", "_next", "pNext", "m_next", "link", "flink"]
    
    found_prev = None
    found_next = None
    
    for name in prev_names:
        if name in pointer_fields:
            found_prev = name
            break
    
    for name in next_names:
        if name in pointer_fields:
            found_next = name
            break
    
    if found_prev and found_next:
        return ("doubly_linked_list", (found_next, found_prev))
    
    # Singly linked list
    if found_next:
        return ("linked_list", found_next)
    
    # Binary tree patterns
    tree_patterns = [
        ("left", "right"),
        ("lchild", "rchild"),
        ("pLeft", "pRight"),
        ("m_left", "m_right"),
    ]
    for left, right in tree_patterns:
        if left in pointer_fields and right in pointer_fields:
            return ("binary_tree", (left, right))
            
    # Check for wrapper class (e.g. BST with root, LinkedList with head)
    # This detects objects that contain a pointer to the actual data structure
    wrapper_patterns = ["root", "_root", "m_root", "head", "_head", "m_head", "first", "top"]
    for name in wrapper_patterns:
        if name in pointer_fields:
            return ("wrapper", name)
    
    # Generic
    if pointer_fields:
        return ("generic", pointer_fields)
    
    return ("scalar", None)

def visualize(expr, *pointer_vars):
    """
    Main entry point for visualization.
    
    Args:
        expr: The main expression to visualize (e.g., "head", "list.head")
        pointer_vars: Optional variable names to highlight (e.g., "slow", "fast")
    """
    reset_state()
    
    # Collect highlight information
    highlight_addrs = set()
    highlight_labels = {}
    
    for pvar in pointer_vars:
        try:
            ptr = gdb.parse_and_eval(pvar)
            if ptr.type.code == gdb.TYPE_CODE_PTR and int(ptr) != 0:
                ptr_val = ptr.dereference()
                addr = get_address(ptr_val)
                highlight_addrs.add(addr)
                highlight_labels[addr] = pvar
        except:
            pass
    
    try:
        val = gdb.parse_and_eval(expr)
        type_name = str(val.type)
        type_code = val.type.code
        
        # =============================================
        # C-style Array Auto-Detection
        # =============================================
        if type_code == gdb.TYPE_CODE_ARRAY:
            # It's a C-style array
            array_size = val.type.range()[1] + 1  # range() returns (0, n-1)
            return visualize_array(expr, array_size)
        
        # =============================================
        # STL Container Auto-Detection
        # =============================================
        
        # Detect std::vector
        if "std::vector" in type_name or "std::__cxx11::vector" in type_name:
            return visualize_std_vector(expr)
        
        # Detect std::list
        if "std::list" in type_name or "std::__cxx11::list" in type_name:
            return visualize_std_list(expr)
        
        # Detect std::map
        if "std::map" in type_name:
            return visualize_std_map(expr)
        
        # Detect std::set (similar to map internally)
        if "std::set" in type_name:
            return visualize_std_map(expr)  # Same internal structure
        
        # =============================================
        # Custom Pointer-Based Structures
        # =============================================
        
        # Handle pointer types
        if val.type.code == gdb.TYPE_CODE_PTR:
            if int(val) == 0:
                return json.dumps({
                    "kind": {"text": True},
                    "text": f"NULL pointer: {expr}"
                })
            val = val.dereference()
        
        # Detect structure type
        struct_type, field_info = detect_structure_type(val)
        
        if struct_type == "doubly_linked_list":
            next_name, prev_name = field_info
            traverse_doubly_linked_list(val, next_name=next_name, prev_name=prev_name,
                                        highlight_addrs=highlight_addrs, 
                                        highlight_labels=highlight_labels)
        elif struct_type == "linked_list":
            traverse_linked_list(val, ptr_name=field_info,
                                highlight_addrs=highlight_addrs,
                                highlight_labels=highlight_labels)
        elif struct_type == "binary_tree":
            left_name, right_name = field_info
            traverse_binary_tree(val, left_name=left_name, right_name=right_name,
                                highlight_addrs=highlight_addrs,
                                highlight_labels=highlight_labels)
        elif struct_type == "wrapper":
            # Recurse on the member (e.g. "tree.root")
            # We strip the current expression to avoid infinite recursion if something goes wrong
            # but generally we want to append the field name
            member_name = field_info
            new_expr = f"({expr}).{member_name}"
            return visualize(new_expr, *pointer_vars)
            
        elif struct_type == "generic":
            addr = get_address(val)
            label = find_data_field(val)
            nodes.append({
                "id": addr,
                "label": label,
                "color": "#69db7c",
                "shape": "box"
            })
            for ptr_field in field_info:
                try:
                    ptr_val = val[ptr_field]
                    if int(ptr_val) != 0:
                        edges.append({
                            "from": addr,
                            "to": get_pointer_address(ptr_val),
                            "label": ptr_field
                        })
                except:
                    pass
        else:
            return json.dumps({
                "kind": {"text": True},
                "text": f"{expr} = {val}"
            })
        
        return json.dumps({
            "kind": {"graph": True},
            "nodes": nodes,
            "edges": edges
        })
        
    except gdb.error as e:
        return json.dumps({
            "kind": {"text": True},
            "text": f"GDB Error: {str(e)}"
        })
    except Exception as e:
        return json.dumps({
            "kind": {"text": True},
            "text": f"Error: {str(e)}"
        })

# =============================================================================
# STL Container Support
# =============================================================================

def visualize_std_vector(expr, highlight_indices=None):
    """
    Visualize std::vector<T> as a graph/table.
    
    Args:
        expr: Vector expression (e.g., "vec", "myVector")
        highlight_indices: List of indices to highlight (optional)
    
    GDB internals for libstdc++ std::vector:
        _M_impl._M_start  - pointer to first element
        _M_impl._M_finish - pointer to one past last element
        _M_impl._M_end_of_storage - end of allocated memory
    """
    reset_state()
    
    if highlight_indices is None:
        highlight_indices = set()
    else:
        highlight_indices = set(highlight_indices)
    
    try:
        vec = gdb.parse_and_eval(expr)
        
        # Get internal pointers
        start = vec["_M_impl"]["_M_start"]
        finish = vec["_M_impl"]["_M_finish"]
        
        # Calculate size accurately
        try:
            # Method 1: Get T from std::vector<T> using template argument
            # This is the most robust way
            elem_type = vec.type.template_argument(0)
            elem_size = elem_type.sizeof
        except:
            try:
                # Method 2: Dereference start pointer if vector is not empty
                if int(finish) > int(start):
                    elem_size = start.dereference().type.sizeof
                else:
                    # Method 3: Fallback to pointer target type (can be wrong for typedefs)
                    elem_size = start.type.target().sizeof
            except:
                 elem_size = 1 # Fallback to avoid division by zero

        if elem_size == 0:
            elem_size = 1
        
        size = int((int(finish) - int(start)) / elem_size)
        
        if size <= 0:
            return json.dumps({
                "kind": {"text": True},
                "text": f"{expr}: empty vector (size=0)"
            })
        
        # Create HTML TABLE
        import math
        
        # Colors (light blue background for cells)
        bg_color = "#339af0"
        
        # Build HTML
        html = f"""
        <div style="font-family: monospace; font-size: 14px;">
            <div style="margin-bottom: 5px;">Vector: {expr} (size: {size})</div>
            <table style="border-collapse: collapse; border: 1px solid #555;">
                <tr>
        """
        
        # Header Row (Indices)
        for i in range(size):
            html += f'<td style="border: 1px solid #555; padding: 4px; text-align: center; color: #888; font-size: 10px;">{i}</td>'
        
        html += "</tr><tr>"
        
        # Value Row
        for i in range(size):
            try:
                elem = start[i]
                elem_val = str(elem)
                if len(elem_val) > 10: elem_val = elem_val[:7] + "..."
            except:
                elem_val = "?"
            
            # Highlight style
            cell_bg = "#ff6b6b" if i in highlight_indices else "#228be6"
            
            html += f'<td style="border: 1px solid #555; background-color: {cell_bg}; color: white; padding: 8px; min-width: 30px; text-align: center;">{elem_val}</td>'
            
        html += """
                </tr>
            </table>
        </div>
        """

        return json.dumps({
            "kind": {"text": True},
            "text": html,
            "mimetype": "text/html"
        })
        
    except Exception as e:
        return json.dumps({
            "kind": {"text": True},
            "text": f"std::vector Error: {str(e)}\nMake sure this is a libstdc++ std::vector"
        })

def visualize_std_list(expr, highlight_addrs=None):
    """
    Visualize std::list<T> as a doubly linked list graph.
    
    GDB internals for libstdc++ std::list:
        _M_impl._M_node - sentinel node (header)
        _M_next / _M_prev - node pointers in base class
        Node is std::_List_node<T> which has _M_storage
    """
    reset_state()
    
    if highlight_addrs is None:
        highlight_addrs = set()
    
    try:
        lst = gdb.parse_and_eval(expr)
        
        # Get element type from list type (e.g., "std::list<int>" -> "int")
        list_type_str = str(lst.type)
        elem_type = None
        try:
            # Extract T from std::list<T, allocator<T>>
            start = list_type_str.find('<') + 1
            end = list_type_str.rfind(',')
            if end == -1:
                end = list_type_str.rfind('>')
            elem_type_str = list_type_str[start:end].strip()
            elem_type = gdb.lookup_type(elem_type_str)
        except:
            pass
        
        # Get the sentinel node address
        sentinel = lst["_M_impl"]["_M_node"]
        sentinel_addr = str(sentinel.address).split()[0]
        
        # Get first real node (next from sentinel)
        try:
            current_ptr = sentinel["_M_next"]
        except:
            try:
                current_ptr = sentinel["_M_data"]["_M_next"]
            except:
                return json.dumps({
                    "kind": {"text": True},
                    "text": f"Cannot access std::list structure"
                })
        
        node_count = 0
        max_nodes = 100
        prev_node_id = None
        
        while node_count < max_nodes:
            current_addr = str(current_ptr).split()[0]
            
            # Check if we're back at sentinel
            if current_addr == sentinel_addr:
                break
            
            if current_addr in visited_nodes:
                break  # Cycle detection
                
            visited_nodes.add(current_addr)
            
            # Try to get data value
            value = "?"
            try:
                # Cast to the actual node type: std::_List_node<T>
                if elem_type:
                    node_type_name = f"std::_List_node<{elem_type}>"
                    try:
                        node_type = gdb.lookup_type(node_type_name)
                        node = current_ptr.cast(node_type.pointer()).dereference()
                        # Access _M_storage which is __gnu_cxx::__aligned_membuf<T>
                        storage = node["_M_storage"]
                        # Get address of storage and cast to T*
                        storage_addr = storage.address
                        elem_ptr_type = elem_type.pointer()
                        value = storage_addr.cast(elem_ptr_type).dereference()
                    except Exception as inner_e:
                        # Fallback for older GCC/different structure
                        try:
                            node = current_ptr.dereference()
                            storage = node["_M_storage"]
                            storage_addr = storage.address
                            elem_ptr_type = elem_type.pointer()
                            value = storage_addr.cast(elem_ptr_type).dereference()
                        except:
                            value = "?"
                else:
                    # No type info available
                    value = "?"
            except:
                value = "?"
            
            node_id = current_addr
            
            color = "#ff6b6b" if current_addr in highlight_addrs else "#a5d8ff"
            if node_count == 0:
                color = "#69db7c"  # Green for first
            
            nodes.append({
                "id": node_id,
                "label": str(value)[:20],
                "color": color,
                "shape": "box"
            })
            
            # Add edge from previous
            if prev_node_id:
                edges.append({
                    "from": prev_node_id,
                    "to": node_id,
                    "label": "next",
                    "color": "#228be6"
                })
                # Add prev edge back
                edges.append({
                    "from": node_id,
                    "to": prev_node_id,
                    "label": "prev",
                    "color": "#fab005",
                    "dashes": True
                })
            
            prev_node_id = node_id
            
            # Move to next node
            try:
                current_ptr = current_ptr.dereference()["_M_next"]
            except:
                try:
                    current_ptr = current_ptr.dereference()["_M_data"]["_M_next"]
                except:
                    break
            
            node_count += 1
        
        if len(nodes) == 0:
            return json.dumps({
                "kind": {"text": True},
                "text": f"{expr}: empty std::list"
            })
        
        return json.dumps({
            "kind": {"graph": True},
            "nodes": nodes,
            "edges": edges
        })
        
    except Exception as e:
        return json.dumps({
            "kind": {"text": True},
            "text": f"std::list Error: {str(e)}"
        })

def visualize_std_map(expr, max_items=50):
    """
    Visualize std::map<K,V> as a tree structure.
    
    Note: std::map uses a red-black tree internally.
    """
    reset_state()
    
    try:
        m = gdb.parse_and_eval(expr)
        
        # Get size
        try:
            size = int(m["_M_t"]["_M_impl"]["_M_node_count"])
        except:
            size = 0
        
        if size == 0:
            return json.dumps({
                "kind": {"text": True},
                "text": f"{expr}: empty std::map (size=0)"
            })
        
        # For std::map, we'll show as a simple list of key-value pairs
        # Full tree visualization is complex
        
        items = []
        
        # This is a simplified visualization
        # For full RB-tree visualization, we'd need to traverse the tree
        
        nodes.append({
            "id": "map_root",
            "label": f"std::map\nsize={size}",
            "color": "#69db7c",
            "shape": "ellipse"
        })
        
        return json.dumps({
            "kind": {"graph": True},
            "nodes": nodes,
            "edges": edges
        })
        
    except Exception as e:
        return json.dumps({
            "kind": {"text": True},
            "text": f"std::map Error: {str(e)}"
        })

# =============================================================================
# Animation / History Support
# =============================================================================

# Global history for step-by-step visualization
visualization_history = []
current_step = 0

def record_step(expr, description=""):
    """
    Record current state for animation playback.
    
    Usage in code (via GDB breakpoints):
        (gdb) vis_record head "Initial state"
        (gdb) vis_record head "After insert"
    """
    global visualization_history, current_step
    
    try:
        # Get current visualization
        result_json = visualize(expr)
        result = json.loads(result_json)
        
        step_data = {
            "step": len(visualization_history),
            "description": description,
            "expression": expr,
            "data": result
        }
        
        visualization_history.append(step_data)
        current_step = len(visualization_history) - 1
        
        return json.dumps({
            "kind": {"text": True},
            "text": f"Step {current_step} recorded: {description}"
        })
        
    except Exception as e:
        return json.dumps({
            "kind": {"text": True},
            "text": f"Recording Error: {str(e)}"
        })

def show_step(step_num):
    """Show a specific step from history."""
    global visualization_history, current_step
    
    if step_num < 0 or step_num >= len(visualization_history):
        return json.dumps({
            "kind": {"text": True},
            "text": f"Invalid step. History has {len(visualization_history)} steps (0-{len(visualization_history)-1})"
        })
    
    current_step = step_num
    step_data = visualization_history[step_num]
    
    # Add step info to the visualization
    result = step_data["data"].copy()
    
    # Add a header node showing step info
    if "nodes" in result:
        step_info_node = {
            "id": "step_info",
            "label": f"Step {step_num}\n{step_data['description']}",
            "color": "#ffd43b",
            "shape": "box"
        }
        result["nodes"].insert(0, step_info_node)
    
    return json.dumps(result)

def show_all_steps():
    """Show overview of all recorded steps."""
    global visualization_history
    
    if len(visualization_history) == 0:
        return json.dumps({
            "kind": {"text": True},
            "text": "No steps recorded. Use 'vis_record <expr> <description>' to record."
        })
    
    steps_text = "Recorded Steps:\n"
    for step in visualization_history:
        steps_text += f"  [{step['step']}] {step['description']}\n"
    
    return json.dumps({
        "kind": {"text": True},
        "text": steps_text
    })

def clear_history():
    """Clear all recorded steps."""
    global visualization_history, current_step
    visualization_history = []
    current_step = 0
    return json.dumps({
        "kind": {"text": True},
        "text": "History cleared."
    })

def visualize_with_traversal(expr, traversal_type="bfs", current_idx=0):
    """
    Visualize a tree with traversal highlighting.
    
    Args:
        expr: Tree root expression
        traversal_type: "bfs", "dfs", "inorder", "preorder", "postorder"
        current_idx: Which node in traversal order to highlight
    """
    reset_state()
    
    try:
        val = gdb.parse_and_eval(expr)
        
        if val.type.code == gdb.TYPE_CODE_PTR:
            if int(val) == 0:
                return json.dumps({
                    "kind": {"text": True},
                    "text": "NULL tree"
                })
            val = val.dereference()
        
        # Collect all nodes first
        traversal_order = []
        
        def collect_bfs(root_val):
            from collections import deque
            queue = deque([root_val])
            while queue:
                node = queue.popleft()
                try:
                    if int(node.address) == 0:
                        continue
                except:
                    continue
                traversal_order.append(get_address(node))
                try:
                    left = node["left"]
                    if int(left) != 0:
                        queue.append(left.dereference())
                except:
                    pass
                try:
                    right = node["right"]
                    if int(right) != 0:
                        queue.append(right.dereference())
                except:
                    pass
        
        def collect_inorder(node):
            try:
                if int(node.address) == 0:
                    return
            except:
                return
            try:
                left = node["left"]
                if int(left) != 0:
                    collect_inorder(left.dereference())
            except:
                pass
            traversal_order.append(get_address(node))
            try:
                right = node["right"]
                if int(right) != 0:
                    collect_inorder(right.dereference())
            except:
                pass
        
        # Collect based on traversal type
        if traversal_type == "bfs":
            collect_bfs(val)
        elif traversal_type in ["inorder", "dfs"]:
            collect_inorder(val)
        else:
            collect_bfs(val)  # Default to BFS
        
        # Determine which nodes to highlight
        highlight_addrs = set()
        highlight_labels = {}
        
        if current_idx < len(traversal_order):
            # Highlight current and visited
            for i in range(current_idx + 1):
                if i == current_idx:
                    highlight_addrs.add(traversal_order[i])
                    highlight_labels[traversal_order[i]] = f"→ {i}"
        
        # Now visualize with highlighting
        struct_type, field_info = detect_structure_type(val)
        
        if struct_type == "binary_tree":
            left_name, right_name = field_info
            traverse_binary_tree(val, left_name, right_name,
                                highlight_addrs, highlight_labels)
        else:
            return json.dumps({
                "kind": {"text": True},
                "text": f"Not a binary tree structure"
            })
        
        # Add traversal info
        info_node = {
            "id": "traversal_info",
            "label": f"{traversal_type.upper()}\nStep {current_idx}/{len(traversal_order)-1}",
            "color": "#ffd43b",
            "shape": "box"
        }
        nodes.insert(0, info_node)
        
        return json.dumps({
            "kind": {"graph": True},
            "nodes": nodes,
            "edges": edges
        })
        
    except Exception as e:
        return json.dumps({
            "kind": {"text": True},
            "text": f"Traversal Error: {str(e)}"
        })

# =============================================================================
# GDB Command Registration
# =============================================================================


class VisualizeCommand(gdb.Command):
    """
    GDB Command: vis <expression> [pointer1] [pointer2] ...
    
    Visualizes a C++ data structure and outputs JSON.
    
    Examples:
        (gdb) vis head                    # Visualize linked list
        (gdb) vis root                    # Visualize binary tree
        (gdb) vis list.head slow fast     # Two-pointer highlighting
    """
    
    def __init__(self):
        super(VisualizeCommand, self).__init__("vis", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Usage: vis <expression> [pointer1] [pointer2] ...")
            print("Examples:")
            print("  vis head              - Visualize linked list")
            print("  vis root              - Visualize binary tree")
            print("  vis head slow fast    - Highlight slow & fast pointers")
            return
        
        parts = arg.strip().split()
        expr = parts[0]
        pointer_vars = parts[1:] if len(parts) > 1 else []
        
        result = visualize(expr, *pointer_vars)
        print(result)

class ArrayVisualizeCommand(gdb.Command):
    """
    GDB Command: vis_arr <array_expr> <size>
    
    Visualizes a C/C++ array.
    
    Examples:
        (gdb) vis_arr arr 10          # Visualize arr[0..9]
        (gdb) vis_arr vec._M_impl._M_start 5
    """
    
    def __init__(self):
        super(ArrayVisualizeCommand, self).__init__("vis_arr", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Usage: vis_arr <array_expr> <size>")
            print("Example: vis_arr arr 10")
            return
        
        parts = arg.strip().split()
        if len(parts) < 2:
            print("Error: Need array expression and size")
            return
            
        expr = parts[0]
        try:
            size = int(parts[1])
        except:
            print("Error: Size must be an integer")
            return
        
        result = visualize_array(expr, size)
        print(result)

# Register commands
VisualizeCommand()
ArrayVisualizeCommand()

class VectorVisualizeCommand(gdb.Command):
    """GDB Command: vis_vec <vector_expr> [idx1] [idx2] ..."""
    
    def __init__(self):
        super(VectorVisualizeCommand, self).__init__("vis_vec", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Usage: vis_vec <vector_expr> [highlight_index1] [highlight_index2] ...")
            print("Example: vis_vec myVector 0 5")
            return
        
        parts = arg.strip().split()
        expr = parts[0]
        highlight_indices = []
        for p in parts[1:]:
            try:
                highlight_indices.append(int(p))
            except:
                pass
        
        result = visualize_std_vector(expr, highlight_indices)
        print(result)

class ListVisualizeCommand(gdb.Command):
    """GDB Command: vis_list <list_expr>"""
    
    def __init__(self):
        super(ListVisualizeCommand, self).__init__("vis_list", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Usage: vis_list <std_list_expr>")
            print("Example: vis_list myList")
            return
        
        result = visualize_std_list(arg.strip())
        print(result)

class RecordStepCommand(gdb.Command):
    """GDB Command: vis_record <expr> <description>"""
    
    def __init__(self):
        super(RecordStepCommand, self).__init__("vis_record", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Usage: vis_record <expr> <description>")
            print("Example: vis_record head 'After inserting node'")
            return
        
        parts = arg.strip().split(maxsplit=1)
        expr = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        
        result = record_step(expr, description)
        print(result)

class ShowStepCommand(gdb.Command):
    """GDB Command: vis_step <step_number>"""
    
    def __init__(self):
        super(ShowStepCommand, self).__init__("vis_step", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            result = show_all_steps()
        else:
            try:
                step_num = int(arg.strip())
                result = show_step(step_num)
            except:
                result = show_all_steps()
        print(result)

class ClearHistoryCommand(gdb.Command):
    """GDB Command: vis_clear"""
    
    def __init__(self):
        super(ClearHistoryCommand, self).__init__("vis_clear", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        result = clear_history()
        print(result)

class TraversalCommand(gdb.Command):
    """GDB Command: vis_trav <tree_expr> <type> <step>"""
    
    def __init__(self):
        super(TraversalCommand, self).__init__("vis_trav", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not arg:
            print("Usage: vis_trav <tree_expr> [bfs|inorder] [step_number]")
            print("Example: vis_trav root bfs 3")
            return
        
        parts = arg.strip().split()
        expr = parts[0]
        trav_type = parts[1] if len(parts) > 1 else "bfs"
        step = int(parts[2]) if len(parts) > 2 else 0
        
        result = visualize_with_traversal(expr, trav_type, step)
        print(result)

# Register new commands
VectorVisualizeCommand()
ListVisualizeCommand()
RecordStepCommand()
ShowStepCommand()
ClearHistoryCommand()
TraversalCommand()

# Also provide a Python function that can be called directly
def gdb_visualize(expr, *pointer_vars):
    """Function callable from GDB's Python interface."""
    return visualize(expr, *pointer_vars)

print("=" * 65)
print("  Antigravity C++ Visualizer - GDB Script Loaded (v3.0)")
print("=" * 65)
print("  BASIC COMMANDS:")
print("    vis <expr>              - Visualize data structure")
print("    vis <expr> p1 p2        - With pointer highlighting")
print("    vis_arr <arr> <size>    - Visualize C array")
print("")
print("  STL CONTAINERS:")
print("    vis_vec <vector>        - Visualize std::vector")
print("    vis_list <list>         - Visualize std::list")
print("")
print("  ANIMATION / STEP-BY-STEP:")
print("    vis_record <expr> 'msg' - Record current state")
print("    vis_step [n]            - Show step n (or list all)")
print("    vis_clear               - Clear recorded history")
print("    vis_trav <tree> bfs 3   - Tree traversal at step 3")
print("=" * 65)
