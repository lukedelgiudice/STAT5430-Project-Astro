import bpy
import csv
import math

CSV_PATH = r"C:\Users\luked\FALL 2025\STAT 5430\results\spatial\study5_clusters_Outpost.csv"

UNIT_SCALE = 0.01 

 # Minimum size of a cluster
BASE_RADIUS = 0.5

# How fast size grows with deaths
SCALE_MULTIPLIER = 0.5

def import_death_clusters():
    print("="*40)
    print(f"loading clusters: {CSV_PATH}")
    
    coords = []
    counts = []
    
    try:
        with open(CSV_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                x = float(row['x']) * UNIT_SCALE
                y = float(row['y']) * UNIT_SCALE
                z = float(row['z']) * UNIT_SCALE
                c = int(row['count'])
                
                coords.append((x, y, z))
                counts.append(c)
    except FileNotFoundError:
        print("error: CSV file not found")
        return

    if not coords:
        print("no data found in CSV")
        return

    print(f"found {len(coords)} clusters")

    mesh_name = "DeathClusters_Data"
    if mesh_name in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes[mesh_name])
    mesh = bpy.data.meshes.new(mesh_name)
    mesh.from_pydata(coords, [], [])
    mesh.update()
    
    obj_name = "Death_Cluster_Visualizer"
    if obj_name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)
    obj = bpy.data.objects.new(obj_name, mesh)
    bpy.context.collection.objects.link(obj)
    
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    attr = mesh.attributes.new(name="death_count", type='INT', domain='POINT')
    attr.data.foreach_set('value', counts)

    modifier = obj.modifiers.new(name="ClusterGeoNodes", type='NODES')
    
    tree_name = "DeathCluster_NodeTree"
    if tree_name in bpy.data.node_groups:
        node_group = bpy.data.node_groups[tree_name]
        node_group.nodes.clear()
    else:
        node_group = bpy.data.node_groups.new(tree_name, 'GeometryNodeTree')

    if hasattr(node_group, "interface"):
        node_group.interface.clear()
        node_group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        node_group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        node_group.inputs.new('NodeSocketGeometry', 'Geometry')
        node_group.outputs.new('NodeSocketGeometry', 'Geometry')

    in_node = node_group.nodes.new('NodeGroupInput')
    in_node.location = (-400, 0)
    out_node = node_group.nodes.new('NodeGroupOutput')
    out_node.location = (600, 0)
    
    inst_node = node_group.nodes.new('GeometryNodeInstanceOnPoints')
    inst_node.location = (200, 0)
    
    sphere_node = node_group.nodes.new('GeometryNodeMeshIcoSphere')
    sphere_node.location = (0, -150)
    sphere_node.inputs['Radius'].default_value = BASE_RADIUS
    sphere_node.inputs['Subdivisions'].default_value = 3
    
    attr_node = node_group.nodes.new('GeometryNodeInputNamedAttribute')
    attr_node.location = (-300, 150)
    attr_node.data_type = 'INT'
    attr_node.inputs['Name'].default_value = "death_count"
    
    math_log = node_group.nodes.new('ShaderNodeMath')
    math_log.operation = 'LOGARITHM'
    math_log.location = (-100, 150)
    
    math_mul = node_group.nodes.new('ShaderNodeMath')
    math_mul.operation = 'MULTIPLY'
    math_mul.inputs[1].default_value = SCALE_MULTIPLIER
    math_mul.location = (50, 150)
    
    math_add = node_group.nodes.new('ShaderNodeMath')
    math_add.operation = 'ADD'
    math_add.inputs[1].default_value = 1.0
    math_add.location = (200, 150)
    
    store_attr = node_group.nodes.new('GeometryNodeStoreNamedAttribute')
    store_attr.location = (400, 0)
    store_attr.data_type = 'INT'
    store_attr.inputs['Name'].default_value = "heat_count"

    node_group.links.new(in_node.outputs[0], inst_node.inputs['Points'])
    node_group.links.new(sphere_node.outputs['Mesh'], inst_node.inputs['Instance'])
    
    node_group.links.new(attr_node.outputs[0], math_log.inputs[0])
    node_group.links.new(math_log.outputs[0], math_mul.inputs[0])
    node_group.links.new(math_mul.outputs[0], math_add.inputs[0])
    node_group.links.new(math_add.outputs[0], inst_node.inputs['Scale'])
    
    node_group.links.new(inst_node.outputs[0], store_attr.inputs['Geometry'])
    node_group.links.new(attr_node.outputs[0], store_attr.inputs['Value'])
    
    node_group.links.new(store_attr.outputs[0], out_node.inputs[0])
    
    modifier.node_group = node_group

    mat_name = "Cluster_Heatmap_Mat"
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(mat_name)
        
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    out_shader = nodes.new('ShaderNodeOutputMaterial')
    principled = nodes.new('ShaderNodeBsdfPrincipled')
    
    attr_in = nodes.new('ShaderNodeAttribute')
    attr_in.attribute_name = "heat_count"
    
    map_range = nodes.new('ShaderNodeMapRange')
    map_range.inputs['From Min'].default_value = 1.0
    map_range.inputs['From Max'].default_value = 20.0
    map_range.inputs['To Min'].default_value = 0.0
    map_range.inputs['To Max'].default_value = 1.0
    
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0, 0, 1, 1)
    ramp.color_ramp.elements[1].color = (1, 0, 0, 1)
    
    principled.inputs['Emission Strength'].default_value = 2.0
    
    mat.node_tree.links.new(attr_in.outputs['Fac'], map_range.inputs['Value'])
    mat.node_tree.links.new(map_range.outputs['Result'], ramp.inputs['Fac'])
    mat.node_tree.links.new(ramp.outputs['Color'], principled.inputs['Base Color'])
    mat.node_tree.links.new(ramp.outputs['Color'], principled.inputs['Emission Color'])
    mat.node_tree.links.new(principled.outputs['BSDF'], out_shader.inputs['Surface'])
    
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
        
    print(f"object '{obj_name}' created")

import_death_clusters()