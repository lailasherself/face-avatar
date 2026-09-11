"""Blender post-armature corrections and portable export preparation."""
import bpy
import numpy as np


def surface_normals(body,points):
    mesh=body.data.copy();mesh.vertices.foreach_set('co',points.astype(np.float32).ravel());mesh.update()
    normals=np.array([v.normal[:] for v in mesh.vertices]);bpy.data.meshes.remove(mesh)
    return normals


def install_post_skin_modifier(body,samples):
    rest=np.array([v.co[:] for v in body.data.vertices])
    group=bpy.data.node_groups.new(body.name+' post-skin corrections','GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    sockets=[group.interface.new_socket(name=s['key'],in_out='INPUT',socket_type='NodeSocketFloat') for s in samples]
    nodes=group.nodes;links=group.links;inputs=nodes.new('NodeGroupInput');output=nodes.new('NodeGroupOutput')
    move=nodes.new('GeometryNodeSetPosition');links.new(inputs.outputs['Geometry'],move.inputs['Geometry'])
    links.new(move.outputs['Geometry'],output.inputs['Geometry']);last=None
    for i,(sample,socket) in enumerate(zip(samples,sockets)):
        key=body.data.shape_keys.key_blocks[sample['key']]
        delta=np.array([v.co[:] for v in key.data])-rest
        attr=body.data.attributes.new(name=f'_PSD_P_{i}',type='FLOAT_VECTOR',domain='POINT')
        attr.data.foreach_set('vector',delta.astype(np.float32).ravel())
        key.data.foreach_set('co',rest.astype(np.float32).ravel())
        read=nodes.new('GeometryNodeInputNamedAttribute');read.data_type='FLOAT_VECTOR';read.inputs['Name'].default_value=attr.name
        scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
        links.new(read.outputs['Attribute'],scale.inputs[0]);links.new(inputs.outputs[socket.name],scale.inputs['Scale'])
        if last:
            add=nodes.new('ShaderNodeVectorMath');add.operation='ADD';links.new(last,add.inputs[0]);links.new(scale.outputs['Vector'],add.inputs[1]);last=add.outputs['Vector']
        else:last=scale.outputs['Vector']
    links.new(last,move.inputs['Offset'])
    modifier=body.modifiers.new('Post-skin pose corrections','NODES');modifier.node_group=group
    for sample,socket in zip(samples,sockets):
        modifier[socket.identifier]=0.
        driver=modifier.driver_add(f'["{socket.identifier}"]').driver
        var=driver.variables.new();var.name='weight';var.type='SINGLE_PROP'
        var.targets[0].id_type='KEY';var.targets[0].id=body.data.shape_keys
        var.targets[0].data_path=f'key_blocks["{sample["key"]}"].value';driver.expression='weight'
    body['correctiveSpace']='postSkin'
    bpy.context.view_layer.update()


def export_space(body,samples,enabled):
    rest=np.array([v.co[:] for v in body.data.vertices])
    modifier=body.modifiers['Post-skin pose corrections']
    modifier.show_viewport=not enabled;modifier.show_render=not enabled
    for i,sample in enumerate(samples):
        values=rest.copy()
        if enabled:values+=np.array([v.vector[:] for v in body.data.attributes[f'_PSD_P_{i}'].data])
        body.data.shape_keys.key_blocks[sample['key']].data.foreach_set('co',values.astype(np.float32).ravel())
    bpy.context.view_layer.update()
