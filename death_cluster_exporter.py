import bpy
import os
import numpy as np

EXPORT_PATH = r"C:\Users\luked\FALL 2025\STAT 5430\results\spatial\DeathClusters_Outpost.fbx"
OBJECT_NAME = "Death_Cluster_Visualizer"

def export_clusters_to_unreal():
    print("="*40)
    print(f"Preparing {OBJECT_NAME} for Unreal Engine...")

    if OBJECT_NAME not in bpy.data.objects:
        print(f"Error: Object '{OBJECT_NAME}' not found. Run import script first.")
        return
    
    original_obj = bpy.data.objects[OBJECT_NAME]
    
    mesh_data = original_obj.data
    min_heat = 1.0
    max_heat = 10.0 
    
    if "death_count" in mesh_data.attributes:
        count = len(mesh_data.vertices)
        vals = np.zeros(count, dtype=np.int32)
        mesh_data.attributes["death_count"].data.foreach_get("value", vals)
        
        if len(vals) > 0:
            min_heat = float(np.min(vals))
            max_heat = float(np.max(vals))
            print(f"Dynamic Heat Range Detected: Min={min_heat}, Max={max_heat}")
    else:
        print("Warning: 'death_count' attribute not found on source mesh. Colors may be inaccurate.")

    if max_heat <= min_heat:
        max_heat = min_heat + 0.001

    bpy.ops.object.select_all(action='DESELECT')
    original_obj.select_set(True)
    bpy.context.view_layer.objects.active = original_obj

    bpy.ops.object.duplicate()
    export_obj = bpy.context.active_object
    export_obj.name = "Export_Mesh_Temp"

    modifier = export_obj.modifiers.get("ClusterGeoNodes")
    if modifier:
        tree = modifier.node_group
        nodes = tree.nodes
        links = tree.links
        
        out_node = next(n for n in nodes if n.type == 'GROUP_OUTPUT')
        
        realize_node = nodes.new('GeometryNodeRealizeInstances')
        realize_node.location = (200, 100)
        
        read_heat = nodes.new('GeometryNodeInputNamedAttribute')
        read_heat.data_type = 'INT'
        read_heat.inputs['Name'].default_value = "death_count"
        read_heat.location = (0, 300)
        
        map_range = nodes.new('ShaderNodeMapRange')
        map_range.location = (200, 300)
        map_range.inputs['From Min'].default_value = min_heat
        map_range.inputs['From Max'].default_value = max_heat
        map_range.inputs['To Min'].default_value = 0.0    # Factor for Blue
        map_range.inputs['To Max'].default_value = 1.0    # Factor for Red
        
        mix_col = nodes.new('ShaderNodeMix')
        mix_col.data_type = 'RGBA' 
        mix_col.clamp_factor = True
        mix_col.location = (400, 300)
        
        mix_col.inputs[6].default_value = (0.0, 0.0, 1.0, 1.0) # A: Blue
        mix_col.inputs[7].default_value = (1.0, 0.0, 0.0, 1.0) # B: Red
        
        store_col = nodes.new('GeometryNodeStoreNamedAttribute')
        store_col.location = (600, 100)
        store_col.data_type = 'BYTE_COLOR' 
        store_col.domain = 'CORNER'        
        store_col.inputs['Name'].default_value = "Col" 
        
        if out_node.inputs[0].links:
            prev_link = out_node.inputs[0].links[0]
            links.new(prev_link.from_socket, realize_node.inputs['Geometry'])
            
        links.new(realize_node.outputs['Geometry'], store_col.inputs['Geometry'])
        links.new(store_col.outputs['Geometry'], out_node.inputs[0])
        
        links.new(read_heat.outputs[0], map_range.inputs['Value'])
        links.new(map_range.outputs['Result'], mix_col.inputs[0]) # Factor
        
        links.new(mix_col.outputs[2], store_col.inputs['Value']) 
        
    print("Baking instances to mesh with dynamic gradient colors...")
    bpy.ops.object.convert(target='MESH')

    if len(export_obj.data.polygons) == 0:
        print("ERROR: Mesh has 0 polygons. Export aborted.")
        bpy.ops.object.delete()
        return

    os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)
    print(f"Exporting to: {EXPORT_PATH}")
    
    bpy.ops.export_scene.fbx(
        filepath=EXPORT_PATH,
        check_existing=False,
        use_selection=True,
        object_types={'MESH'},
        apply_scale_options='FBX_SCALE_ALL', 
        axis_forward='-Z', 
        axis_up='Y',
        bake_space_transform=True,
        use_mesh_modifiers=True,
        colors_type='SRGB',
    )

    bpy.ops.object.delete() 
    print("Done.")

export_clusters_to_unreal()