"""Local socket surface fitting and UV-space cleanup on the review copy only."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
import rig_reference_nebula as work


def terms(x,z):
    return np.array([np.ones_like(x),x,z,x*x,x*z,z*z]).T


def fade(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)


def refine():
    work.reset_pose();c=work.character();body=c.body
    source=next(n.image for n in body.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image)
    width,height=source.size
    pixels=np.array(source.pixels[:],dtype=np.float32).reshape(height,width,4)
    features=[{'x':p.x,'z':p.z,'rx':r.x,'rz':r.z,'back':p.y+.035} for p,r in c.eyes]
    for feature in features:
        samples=[];colors=[]
        for radius in [1.55,1.8]:
            for angle in np.linspace(0,2*math.pi,96,endpoint=False):
                x,z=radius*math.cos(angle),radius*math.sin(angle)
                point,uv=c.surface(feature['x']+x*feature['rx'],feature['z']+z*feature['rz'])
                samples.append((x,z))
                colors.append(pixels[int(uv.y*(height-1)),int(uv.x*(width-1)),:3])
        samples=np.array(samples);design=terms(samples[:,0],samples[:,1])
        feature['color']=np.linalg.lstsq(design,np.array(colors),rcond=None)[0]
    before=np.array([v.co[:] for v in body.data.vertices])
    after=before.copy()
    edge=np.array([e.vertices[:] for e in body.data.edges]);a,b=edge.T
    degree=np.bincount(edge.ravel(),minlength=len(before));relaxed=before[:,1].copy()
    for _ in range(18):
        total=np.zeros(len(before));np.add.at(total,a,relaxed[b]);np.add.at(total,b,relaxed[a])
        relaxed=.5*relaxed+.5*total/np.maximum(1,degree)
    for f in features:
        x=(before[:,0]-f['x'])/f['rx'];z=(before[:,2]-f['z'])/f['rz']
        radial=np.hypot(x,z);amount=(1-fade(1.05,1.55,radial))*(before[:,1]<-.55)
        target=relaxed.copy()
        inner=1-fade(.85,1.12,radial)
        target=target*(1-inner)+np.maximum(target,f['back'])*inner
        after[:,1]=after[:,1]*(1-amount)+target*amount
    delta=after-before
    for vertex in body.data.vertices:vertex.co=after[vertex.index]
    for key in body.data.shape_keys.key_blocks:
        for i in np.where(np.linalg.norm(delta,axis=1)>1e-10)[0]:key.data[int(i)].co+=Vector(delta[i])
    body.data.update()
    # Rasterize affected UV triangles; blend fitted neighboring skin at the boundary.
    uv=body.data.uv_layers.active.data
    cleanup=np.zeros((height,width),dtype=np.float32)
    for polygon in body.data.polygons:
        center=polygon.center
        if center.y>-.55:continue
        chosen=[f for f in features if math.hypot((center.x-f['x'])/f['rx'],(center.z-f['z'])/f['rz'])<1.8]
        if not chosen:continue
        triangle=np.array([uv[i].uv[:] for i in polygon.loop_indices[:3]])*[width-1,height-1]
        world=np.array([body.data.vertices[i].co[:] for i in polygon.vertices[:3]])
        lo=np.maximum(0,np.floor(triangle.min(axis=0)).astype(int));hi=np.minimum([width-1,height-1],np.ceil(triangle.max(axis=0)).astype(int))
        xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
        a,b,d=triangle;v0=b-a;v1=d-a;den=v0[0]*v1[1]-v1[0]*v0[1]
        if abs(den)<1e-8:continue
        px,py=xx-a[0],yy-a[1]
        s=(px*v1[1]-v1[0]*py)/den;t=(v0[0]*py-px*v0[1])/den
        inside=(s>=-.4)&(t>=-.4)&(s+t<=1.4)
        wx=world[0,0]+s*(world[1,0]-world[0,0])+t*(world[2,0]-world[0,0])
        wz=world[0,2]+s*(world[1,2]-world[0,2])+t*(world[2,2]-world[0,2])
        patch=pixels[lo[1]:hi[1]+1,lo[0]:hi[0]+1,:3]
        for f in chosen:
            x=(wx-f['x'])/f['rx'];z=(wz-f['z'])/f['rz']
            weight=(1-fade(1.12,1.60,np.hypot(x,z)))*inside
            target=np.clip((terms(x.ravel(),z.ravel())@f['color']).reshape(*x.shape,3),0,1)
            patch[:]=patch*(1-weight[:,:,None])+target*weight[:,:,None]
            region=cleanup[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            np.maximum(region,weight,out=region)
    mat=body.data.materials[0].copy();mat.name='Nebula refined skin'
    image=bpy.data.images.new('Nebula refined diffuse',width=width,height=height,alpha=True)
    image.pixels.foreach_set(pixels.ravel());image.update();image.pack()
    next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image).image=image
    for node in mat.node_tree.nodes:
        if node.type!='TEX_IMAGE' or node.image==image:continue
        original=node.image
        assert tuple(original.size)==(width,height),'Source material maps must share dimensions'
        data=np.array(original.pixels[:],dtype=np.float32).reshape(height,width,4)
        target=(.5,.5,1) if 'normal' in original.name.lower() else (1,.65,0)
        data[:,:,:3]=data[:,:,:3]*(1-cleanup[:,:,None])+np.array(target)*cleanup[:,:,None]
        result=bpy.data.images.new('Nebula refined '+original.name,width=width,height=height,alpha=True)
        result.colorspace_settings.name='Non-Color'
        result.pixels.foreach_set(data.ravel());result.update();result.pack();node.image=result
    body.data.materials[0]=mat
    body['socketRefinement']='Locally fitted socket depth and continuous UV-space skin reconstruction'
    work.view(distance=2.4,center=(0,-.2,2.52))
    return {'movedVertices':int(np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-10))}


def blend_pupil_edges():
    face=bpy.context.scene.objects['NebulaEyesAndMouth']
    color=work.CONFIG['eyeColor'].lstrip('#')
    white=np.array([int(color[i:i+2],16) for i in (0,2,4)],dtype=np.float32)/255
    sclera=bpy.data.materials['nebula sclera']
    linear=np.where(white<=.04045,white/12.92,((white+.055)/1.055)**2.4)
    sclera.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*linear,1)
    for mat in face.data.materials:
        if 'iris' not in mat.name:continue
        node=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE')
        image=node.image;w,h=image.size
        pixels=np.array(image.pixels[:],dtype=np.float32).reshape(h,w,4)
        weight=fade(.30,.65,pixels[:,:,:3].min(axis=2))
        pixels[:,:,:3]=pixels[:,:,:3]*(1-weight[:,:,None])+white*weight[:,:,None]
        image.pixels.foreach_set(pixels.ravel());image.update();image.pack()
        mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.30


def smooth_neck():
    body=bpy.context.scene.objects['NebulaSourceBody']
    assert not body.get('neckRelaxed'),'Neck smoothing already applied'
    keys=body.data.shape_keys.key_blocks
    source=np.array([v.co[:] for v in keys[0].data],dtype=np.float64)
    adjacency=[[] for _ in source]
    for edge in body.data.edges:
        a,b=edge.vertices;adjacency[a].append(b);adjacency[b].append(a)
    z=source[:,2]
    mask=fade(1.77,1.90,z)*(1-fade(2.12,2.25,z))*(1-fade(.17,.34,np.abs(source[:,0])))
    selected=np.flatnonzero(mask>0)
    result=source.copy()
    for _ in range(16):
        updated=result.copy()
        for i in selected:
            if adjacency[i]:updated[i]+=(result[adjacency[i]].mean(axis=0)-result[i])*.35*mask[i]
        result=updated
    delta=result-source
    for key in keys:
        for i in selected:key.data[i].co+=Vector(delta[i])
    for i in selected:body.data.vertices[i].co=keys[0].data[i].co
    reset_surface_normals(body)
    body.data.update();body['neckRelaxed']=True
    return {'vertices':len(selected),'maxDisplacement':float(np.linalg.norm(delta,axis=1).max())}


def reset_surface_normals(body):
    # Imported split normals and flat faces become invalid after local retopology.
    for name in ('custom_normal','sharp_edge'):
        attribute=body.data.attributes.get(name)
        if attribute:body.data.attributes.remove(attribute)
    for face in body.data.polygons:face.use_smooth=True


def retopologize_mouth():
    from build_avatar_fleet import material
    from mathutils.geometry import barycentric_transform
    from mathutils.bvhtree import BVHTree
    work.reset_pose();c=work.character();body=c.body
    original=bpy.data.objects['Nebula'];scale=3.2/1.6186459064483643
    source_tree=BVHTree.FromPolygons([v.co for v in original.data.vertices],[p.vertices[:] for p in original.data.polygons])
    def source_uv(x,z):
        point,_,index,_=source_tree.ray_cast(Vector((x/scale,-5,z/scale)),Vector((0,1,0)))
        assert point is not None,'Mouth patch must project onto the preserved source'
        loops=original.data.polygons[index].loop_indices[:3]
        positions=[original.data.vertices[original.data.loops[i].vertex_index].co for i in loops]
        coords=[Vector((*original.data.uv_layers.active.data[i].uv,0)) for i in loops]
        result=barycentric_transform(point,*positions,*coords)
        return Vector((result.x,result.y))
    bm=bmesh.new();bm.from_mesh(body.data)
    remove=[f for f in bm.faces if f.calc_center_median().y<-.55 and
            ((f.calc_center_median().x-c.mx)/.21)**2+((f.calc_center_median().z-c.mz)/.105)**2<1]
    bmesh.ops.delete(bm,geom=remove,context='FACES')
    boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.x-c.mx)<.25 and abs(v.co.z-c.mz)<.14 and v.co.y<-.55 for v in e.verts)]
    neighbors={}
    for edge in boundary:
        a,b=edge.verts;neighbors.setdefault(a,[]).append(b);neighbors.setdefault(b,[]).append(a)
    assert neighbors and all(len(v)==2 for v in neighbors.values()),'Expected a closed outer mouth patch'
    start=min(neighbors,key=lambda v:v.co.x);outer=[start];previous=None
    while True:
        current=outer[-1];nxt=next(v for v in neighbors[current] if v!=previous)
        if nxt==start:break
        outer.append(nxt);previous=current
        assert len(outer)<=len(neighbors)
    assert len(outer)==len(neighbors),'Unexpected extra patch boundary'
    theta=np.unwrap([math.atan2((v.co.z-c.mz)/.105,(v.co.x-c.mx)/.21) for v in outer])
    # Uniform inner spacing keeps narrow lip corners from inheriting tiny source triangles.
    direction=1 if theta[-1]>theta[0] else -1
    angles=theta[0]+direction*np.arange(len(outer))*2*math.pi/len(outer)
    uv=bm.loops.layers.uv.active;deform=bm.verts.layers.deform.active
    layers=list(bm.verts.layers.shape.items());head=body.vertex_groups['Head'].index
    source_image=next(n.image for n in body.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image)
    w,h=source_image.size;pixels=np.array(source_image.pixels[:]).reshape(h,w,4)
    outer_colors=[]
    for v in outer:
        coord=source_uv(v.co.x,v.co.z)
        outer_colors.append(pixels[int(coord.y*(h-1)),int(coord.x*(w-1)),:3])
    xy=np.array([((v.co.x-c.mx)/.21,(v.co.z-c.mz)/.105) for v in outer])
    fit=np.linalg.lstsq(terms(xy[:,0],xy[:,1]),outer_colors,rcond=None)[0]
    layer=bm.loops.layers.float_color.get('MouthColor') or bm.loops.layers.float_color.new('MouthColor')
    for face in bm.faces:
        for loop in face.loops:loop[layer]=(1,1,1,1)
    mat=material('Nebula continuous lip skin','#ffffff',.5)
    attr=mat.node_tree.nodes.new('ShaderNodeVertexColor');attr.layer_name='MouthColor'
    mat.node_tree.links.new(attr.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    mat_index=len(body.data.materials);body.data.materials.append(mat)
    colors={v:np.array(rgb) for v,rgb in zip(outer,outer_colors)}
    rings=[outer]
    for ring in range(1,7):
        t=ring/6;row=[]
        for vertex,angle in zip(outer,angles):
            x=c.mx+c.mw*math.cos(angle);z=c.mouth_z(x)+.006*math.sin(angle)
            y=float(np.interp((x-c.mx)/c.mw,np.linspace(-1,1,65),c.mouth_rim))-.003
            point=vertex.co.lerp(Vector((x,y,z)),t)
            new=bm.verts.new(point);new[deform][head]=1
            for name,layer in layers:new[layer]=point+(Vector((0,0,0)) if name=='Basis' else c.skin_delta(point,name))
            normalized=terms(np.array([(point.x-c.mx)/.21]),np.array([(point.z-c.mz)/.105]))
            fitted=np.clip((normalized@fit)[0],0,1)
            colors[new]=colors[vertex]*(1-t)+fitted*t
            row.append(new)
        rings.append(row)
    for outside,inside in zip(rings,rings[1:]):
        for i in range(len(outer)):
            j=(i+1)%len(outer);face=bm.faces.new((outside[i],outside[j],inside[j],inside[i]))
            face.normal_update()
            if face.normal.y>0:face.normal_flip()
            face.smooth=True
            face.material_index=mat_index
            for loop in face.loops:
                loop[uv].uv=(.5,.5)
                rgb=colors[loop.vert];linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
                loop[bm.loops.layers.float_color['MouthColor']]=(*linear,1)
    loose=[v for v in bm.verts if not v.link_faces]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(body.data);bm.free();body.data.update()
    reset_surface_normals(body)
    assert all(len(key.data)==len(body.data.vertices) for key in body.data.shape_keys.key_blocks)
    body['oralBoundaryRefinement']='Six connected quad rings replacing the jagged source mouth patch'
    return {'outerVertices':len(outer),'quadFaces':len(outer)*6,'bodyVertices':len(body.data.vertices)}
