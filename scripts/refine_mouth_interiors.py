"""Source-preserving oral revisions, run in small stages through Blender MCP."""
from pathlib import Path
import json
import math
import shutil
import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'.context/qa/mouth-interiors'
FILES={
    'clay':('blender/likeness-trials/clay-body-rig.blend','assets/likeness-trials/clay-body-rig.glb'),
    'nebula':('blender/reference-characters/nebula-review.blend','assets/reference-characters/nebula-review.glb'),
    'glass':('blender/likeness-trials/glass-body-rig.blend','assets/likeness-trials/glass-body-rig.glb'),
}

def reset():
    for o in bpy.context.scene.objects:
        if o.type=='ARMATURE':
            for b in o.pose.bones:b.matrix_basis.identity()
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=0
    bpy.context.view_layer.update()

def material(name,color,roughness=.6):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness;p.inputs['Coat Weight'].default_value=.08
    return m

def mesh_object(name,vertices,faces,mat,rig):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    o=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(o);o.parent=rig
    o.data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    o.vertex_groups.new(name='Head').add(list(range(len(vertices))),1,'REPLACE')
    mod=o.modifiers.new('Head skin','ARMATURE');mod.object=rig
    return o

def cavity(name,head,indices,rig,depth=.30,height=.40):
    old=bpy.context.scene.objects.get(name)
    if old:bpy.data.objects.remove(old,do_unlink=True)
    keys=head.data.shape_keys.key_blocks
    rim=np.array([keys['Basis'].data[i].co[:] for i in indices]);n=len(indices)
    center=np.mean(rim,axis=0);width=(rim[:,0].max()-rim[:,0].min())*.5
    opened=np.array([keys['jawOpen'].data[i].co[:] for i in indices]);middle=np.mean(opened,axis=0)
    angle=np.arctan2((opened[:,2]-middle[2])/max(np.ptp(opened[:,2])*.5,.001),(opened[:,0]-middle[0])/max(np.ptp(opened[:,0])*.5,.001))
    # Expand just behind the lip, then round the roof, floor and closed back wall.
    stages=[(0,0),(.025,.2),(.055,.55),(.10,1),(.18,1),(.30,1),(.45,1),(.62,1),(.78,.94),(.90,.73),(.97,.40)]
    rings=[]
    for t,size in stages:
        blend=min(1,t/.60);ellipse=np.stack([center[0]+width*1.05*np.cos(angle),np.full(n,center[1]+depth*t),center[2]+width*height*np.sin(angle)],axis=1)
        ring=rim*(1-blend)+ellipse*blend
        ring[:,1]=rim[:,1]+depth*t+.001
        if t>=.78:
            ring[:,0]=center[0]+(ring[:,0]-center[0])*size
            ring[:,2]=center[2]+(ring[:,2]-center[2])*size
        rings.append(ring)
    vertices=np.concatenate(rings).tolist()+[[center[0],center[1]+depth,center[2]]]
    faces=[(r*n+j,r*n+(j+1)%n,(r+1)*n+(j+1)%n,(r+1)*n+j) for r in range(len(rings)-1) for j in range(n)]
    faces += [((len(rings)-1)*n+j,(len(rings)-1)*n+(j+1)%n,len(vertices)-1) for j in range(n)]
    mat=material(name+' lining',(.025,.004,.007),.92)
    mat.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.12
    mat.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=0
    o=mesh_object(name,vertices,faces,mat,rig);o['oralRevision']='rounded-mouthbag-1';o['lipVertexIndices']=list(indices)
    colors=o.data.color_attributes.new(name='CavityTint',type='FLOAT_COLOR',domain='POINT')
    for i,c in enumerate(colors.data):
        t=stages[min(len(stages)-1,i//n)][0];a=(1-t)**2
        c.color=(.003+.055*a,.0006+.009*a,.001+.015*a,1)
    node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='CavityTint'
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    base=o.shape_key_add(name='Basis')
    for key in keys:
        if not key.name.startswith(('jaw','mouth')):continue
        target=o.shape_key_add(name=key.name);delta=np.array([key.data[i].co[:] for i in indices])-rim
        for r,(t,_) in enumerate(stages):
            for j in range(n):target.data[r*n+j].co=base.data[r*n+j].co+Vector(delta[j])*(1-min(1,t/.60))
    return o

def components(o):
    adjacency=[[] for _ in o.data.vertices]
    for e in o.data.edges:
        a,b=e.vertices;adjacency[a].append(b);adjacency[b].append(a)
    pending=set(range(len(adjacency)));result=[]
    while pending:
        queue=[pending.pop()];group=[]
        while queue:
            i=queue.pop();group.append(i)
            for j in adjacency[i]:
                if j in pending:pending.remove(j);queue.append(j)
        result.append(group)
    return sorted(result,key=lambda ids:sum(o.data.vertices[i].co.x for i in ids)/len(ids))

def clay_teeth():
    rig=bpy.context.scene.objects['AvatarRig']
    for row in ['Upper','Lower']:
        o=bpy.context.scene.objects['Clay '+row+' Teeth'];assert not o.get('dentalArchRevision')
        keys=o.data.shape_keys.key_blocks;base=keys['Basis'];groups=components(o);centers=[]
        for j,ids in enumerate(groups):
            points=np.array([base.data[i].co[:] for i in ids]);center=points.mean(axis=0);t=(j-(len(groups)-1)/2)/((len(groups)-1)/2)
            local=points-center;local[:,0]*=.90;local[:,1]*=.85;local[:,2]*=.82 if row=='Upper' else .72
            for axis in [0,2]:
                radius=max(abs(local[:,axis]));local[:,axis]=np.sign(local[:,axis])*radius*(abs(local[:,axis])/radius)**.65
            angle=t*.20;x=local[:,0].copy();y=local[:,1].copy();local[:,0]=x*math.cos(angle)-y*math.sin(angle);local[:,1]=x*math.sin(angle)+y*math.cos(angle)
            newcenter=center+np.array([0,.014*t*t,.003*t*t]);delta=local+newcenter-points
            for key in keys:
                for i,d in zip(ids,delta):key.data[i].co+=Vector(d)
            centers.append(newcenter)
        for v,b in zip(o.data.vertices,base.data):v.co=b.co
        o.data.update();o['dentalArchRevision']=1
        o.data.materials[0]=material('Clay individual teeth enamel',(.61,.51,.37),.39)
        # A recessed gum arch supports the roots without a flat plate behind crowns.
        centers=np.array(centers);vertices=[];faces=[];nr=25;nc=12
        for j in range(nr):
            t=j/(nr-1)*(len(centers)-1);k=min(len(centers)-2,int(t));c=centers[k]*(1-(t-k))+centers[k+1]*(t-k)
            c=c+np.array([0,.017,.014 if row=='Upper' else -.011])
            for a in np.arange(nc)*math.tau/nc:vertices.append((c[0],c[1]+.006*math.cos(a),c[2]+.004*math.sin(a)))
        for j in range(nr-1):
            for k in range(nc):faces.append((j*nc+k,j*nc+(k+1)%nc,(j+1)*nc+(k+1)%nc,(j+1)*nc+k))
        faces += [tuple(reversed(range(nc))),tuple((nr-1)*nc+k for k in range(nc))]
        gum=mesh_object('Clay '+row+' Gums',vertices,faces,material('Clay '+row+' gingiva',(.09,.017,.022),.55),rig)
        gb=gum.shape_key_add(name='Basis')
        for name in ['jawOpen','mouthClose']:
            gk=gum.shape_key_add(name=name);delta=keys[name].data[0].co-base.data[0].co
            for v,b in zip(gk.data,gb.data):v.co=b.co+delta

def clay():
    assert not bpy.context.scene.get('oralRevision'),'Open the pre-revision source before rebuilding'
    reset();h=bpy.context.scene.objects['Clay Skin'];n=h['mouthPatchRingSize'];start=h['mouthPatchStart']+(h['mouthPatchRings']-1)*n
    clay_teeth();cavity('Clay Oral Cavity',h,range(start,start+n),bpy.context.scene.objects['AvatarRig'],.34)
    retract_tongue(bpy.context.scene.objects['Clay Long Tongue'],.065)
    bpy.context.scene['oralRevision']='rounded-mouthbag-1'

def retract_tongue(o,distance,indices=None):
    keys=o.data.shape_keys.key_blocks;base=keys['Basis'];indices=list(range(len(base.data))) if indices is None else list(indices)
    back=max(base.data[i].co.y for i in indices);front=min(base.data[i].co.y for i in indices)
    for i in indices:
        t=min(1,max(0,(back-base.data[i].co.y)/max(.001,back-front)))
        for key in keys:
            if key.name!='tongueOut':key.data[i].co.y+=distance*t
    for v,b in zip(o.data.vertices,base.data):v.co=b.co
    o.data.update()

def nebula():
    reset();h=bpy.context.scene.objects['NebulaSourceBody'];assert not h.get('roundedOralLoops')
    assert len(h.data.vertices)==11272,'Unexpected Nebula source topology'
    bm=bmesh.new();bm.from_mesh(h.data)
    patch=[f for f in bm.faces if f.material_index==1]
    # Keep the shared outer boundary and all existing skin weights intact.
    layers=list(bm.verts.layers.shape.values())
    basis=bm.verts.layers.shape.get('Basis')
    # Resample only the two innermost rings. Explicit key interpolation avoids the
    # generic subdivider changing shared skin vertices or their facial targets.
    bm.verts.ensure_lookup_table()
    patch_vertices={v for f in patch for v in f.verts}
    color_layers=list(bm.loops.layers.float_color.values())+list(bm.loops.layers.color.values())
    colors={layer:{v:sum((loop[layer] for loop in v.link_loops if loop.face.material_index==1),Vector((0,0,0,0)))/sum(loop.face.material_index==1 for loop in v.link_loops) for v in patch_vertices} for layer in color_layers}
    outward=[[bm.verts[11247+j] for j in range(25)]];seen=set(outward[0])
    for _ in range(6):
        row=[next(e.other_vert(v) for e in v.link_edges if e.other_vert(v) in patch_vertices and e.other_vert(v) not in seen) for v in outward[-1]]
        assert len(set(row))==25;outward.append(row);seen.update(row)
    outer=outward[2];original=list(reversed(outward[:2]))
    replace={v for row in original for v in row}
    patch=[f for f in patch if any(v in replace for v in f.verts)]
    for layer in layers:
        for row in original:
            values=[v[layer]*.8+(row[(j-1)%25][layer]+row[(j+1)%25][layer])*.1 for j,v in enumerate(row)]
            for v,p in zip(row,values):v[layer]=p
    deform=bm.verts.layers.deform.verify();head_group=h.vertex_groups['Head'].index
    rings=[]
    for row in original:
        ring=[]
        for j in range(100):
            k,t=divmod(j,4);t/=4
            v=bm.verts.new()
            for layer in layers:
                p0,p1,p2,p3=[row[(k+d)%25][layer] for d in [-1,0,1,2]]
                v[layer]=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
            for layer in color_layers:colors[layer][v]=colors[layer][row[k]]*(1-t)+colors[layer][row[(k+1)%25]]*t
            v.co=v[basis];v[deform][head_group]=1;ring.append(v)
        rings.append(ring)
    bmesh.ops.delete(bm,geom=patch,context='FACES_ONLY')
    def face(vs):
        f=bm.faces.new(vs);f.material_index=1;f.smooth=True
        for loop in f.loops:
            for layer in color_layers:loop[layer]=colors[layer][loop.vert]
    for j in range(25):
        a,b=outer[j],outer[(j+1)%25];inner=rings[0];k=j*4
        for d in range(3):face([a,inner[(k+d+1)%100],inner[k+d]])
        face([a,b,inner[(k+4)%100],inner[k+3]])
    for a,b in zip(rings,rings[1:]):
        for j in range(100):face([a[j],a[(j+1)%100],b[(j+1)%100],b[j]])
    bm.normal_update()
    boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.x)<.25 and abs(v.co.z-2.305)<.15 for v in e.verts)]
    first=min((v for e in boundary for v in e.verts),key=lambda v:v.co.x);loop=[first];previous=None;current=first
    while True:
        choices=[e.other_vert(current) for e in current.link_edges if e in boundary and e.other_vert(current)!=previous]
        nxt=choices[0]
        if nxt==first:break
        loop.append(nxt);previous,current=current,nxt
        assert len(loop)<1000
    bm.verts.index_update();indices=[v.index for v in loop];bm.to_mesh(h.data);bm.free();h.data.update()
    assert len(h.data.shape_keys.key_blocks['Basis'].data)==len(h.data.vertices)
    h['roundedOralLoops']=True;h['mouthbagBoundary']=indices
    f=bpy.context.scene.objects['NebulaEyesAndMouth'];bm=bmesh.new();bm.from_mesh(f.data)
    old=[p for p in bm.faces if 'oral interior' in f.data.materials[p.material_index].name]
    bmesh.ops.delete(bm,geom=old,context='FACES_ONLY');bm.to_mesh(f.data);bm.free();f.data.update()
    tongue={i for p in f.data.polygons if 'tongue' in f.data.materials[p.material_index].name for i in p.vertices}
    retract_tongue(f,.045,tongue)
    cavity('Nebula Oral Cavity',h,indices,bpy.context.scene.objects['AvatarRig'],.25,.52)
    for name in ['UpperTeeth','LowerTeeth']:
        o=bpy.context.scene.objects[name]
        if not o.data.shape_keys:o.shape_key_add(name='Basis')
        keys=o.data.shape_keys.key_blocks;base=keys['Basis'];groups=components(o)
        for j,ids in enumerate(groups):
            p=np.array([base.data[i].co[:] for i in ids]);c=p.mean(axis=0);t=(j-(len(groups)-1)/2)/((len(groups)-1)/2)
            local=p-c;local[:,0]*=.93;local[:,2]*=.90
            delta=local+c+np.array([0,.009*t*t,.003*t*t])-p
            for key in keys:
                for i,d in zip(ids,delta):key.data[i].co+=Vector(d)
        for v,b in zip(o.data.vertices,base.data):v.co=b.co
        o.data.update()
    bpy.context.scene['oralRevision']='rounded-mouthbag-1'

def export_candidate(name):
    reset();rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o==rig or (o.type=='MESH' and o.parent==rig):o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(QA/(name+'-candidate.glb')),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_morph=True,export_morph_normal=True,export_extras=True,export_attributes=True,export_yup=True,export_cameras=False,export_lights=False)
    versions=bpy.context.preferences.filepaths.save_version;bpy.context.preferences.filepaths.save_version=0
    try:bpy.ops.wm.save_as_mainfile(filepath=str(QA/(name+'-candidate.blend')))
    finally:bpy.context.preferences.filepaths.save_version=versions

def glass():
    assert not bpy.context.scene.get('oralRevision'),'Open the pre-revision source before rebuilding'
    reset();h=bpy.context.scene.objects['Glass Head'];patch=h['patches']['mouth']
    start=patch['start']+11*patch['size'];rig=bpy.context.scene.objects['Glass AvatarRig']
    cavity('Glass Oral Cavity',h,range(start,start+patch['size']),rig,.25,.35)
    retract_tongue(bpy.context.scene.objects['Glass Long Tongue'],.035)
    # A subdued optical lip, limited to the existing innermost oral loops.
    lip=material('Glass optical lip',(.006,.021,.027),.30)
    p=lip.node_tree.nodes['Principled BSDF'];p.inputs['Metallic'].default_value=.12;p.inputs['Coat Weight'].default_value=.6
    h.data.materials.append(lip)
    for f in h.data.polygons:
        if min(f.vertices)>=patch['start']+9*patch['size']:f.material_index=len(h.data.materials)-1
    bpy.context.scene['oralRevision']='rounded-mouthbag-1'

def promote(name):
    audit(name)
    export_candidate(name)
    for suffix,path in zip(['.blend','.glb'],FILES[name]):shutil.copy2(QA/(name+'-candidate'+suffix),ROOT/path)

def audit(name):
    current={o.name:o for o in bpy.context.scene.objects}
    with bpy.data.libraries.load(str(QA/('before-'+name+'.blend')),link=False) as (src,dst):
        names=[n for n in src.objects if n in current];dst.objects=names.copy()
    def coords(data):return np.array([v.co[:] for v in data])
    def weights(o):return [[(o.vertex_groups[g.group].name,round(g.weight,6)) for g in v.groups] for v in o.data.vertices]
    checked=[]
    try:
        for n,old in zip(names,dst.objects):
            new=current[n]
            if old.type=='ARMATURE':
                assert list(old.data.bones.keys())==list(new.data.bones.keys())
                for b in old.data.bones:assert np.allclose(np.array(b.matrix_local),np.array(new.data.bones[b.name].matrix_local))
            if old.type!='MESH' or 'Oral Cavity' in n:continue
            assert weights(old)==weights(new)[:len(old.data.vertices)],n+' skin weights'
            a=old.data.shape_keys;b=new.data.shape_keys
            excluded=set()
            if n=='NebulaSourceBody':excluded={i for f in old.data.polygons if f.material_index==1 for i in f.vertices}
            if n=='NebulaEyesAndMouth':excluded={i for f in old.data.polygons if 'tongue' in old.data.materials[f.material_index].name for i in f.vertices}
            if 'Teeth' in n or 'Tongue' in n:excluded=set(range(len(old.data.vertices)))
            indices=[i for i in range(len(old.data.vertices)) if i not in excluded]
            if a:
                for key in a.key_blocks:
                    assert key.name in b.key_blocks,n+' missing '+key.name
                    original=coords(key.data);revised=coords(b.key_blocks[key.name].data)
                    assert np.isfinite(revised).all(),n+' invalid coordinates'
                    if indices:assert np.allclose(original[indices],revised[indices],atol=1e-7),n+' changed '+key.name
                    if key.name=='tongueOut':assert np.allclose(original,revised[:len(original)],atol=1e-7),n+' tongue endpoint'
            elif indices:assert np.allclose(coords(old.data.vertices)[indices],coords(new.data.vertices)[indices]),n+' base changed'
            checked.append(n)
        c=current[name.title()+' Oral Cavity'];bm=bmesh.new();bm.from_mesh(c.data)
        boundary=[e for e in bm.edges if e.is_boundary]
        assert len(boundary)==len(c['lipVertexIndices'])
        assert all(e.is_manifold or e.is_boundary for e in bm.edges)
        assert len(components(c))==1
        for v in c.data.vertices:assert abs(sum(g.weight for g in v.groups)-1)<1e-6
        for key in c.data.shape_keys.key_blocks:assert np.isfinite(coords(key.data)).all()
        bm.free()
        report={'id':name,'preservedMeshes':checked,'boneRestsPreserved':True,'weightsPreserved':True,'tongueEndpointPreserved':True,'mouthbagOpenBoundaryEdges':len(boundary),'closedBackWall':True}
        (QA/(name+'-geometry.json')).write_text(json.dumps(report,indent=2));print(report)
        return report
    finally:
        for o in dst.objects:bpy.data.objects.remove(o,do_unlink=True)
