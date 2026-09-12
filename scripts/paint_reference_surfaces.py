"""Reference-sampled texture painting and broad sculpt corrections via Blender MCP.

The PNG supplies visible pigment and small-scale relief cues, not hidden geometry.
Unseen surfaces use cloned skin patches. Single-view lighting removal is approximate.
Run explicit stages on backed-up candidates, one character at a time.
"""
import json
import math
import shutil
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
import complete_supplied_characters as rig
import refine_supplied_likeness as export
import polish_supplied_characters as surfaces

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'.context/qa/reference-painted-v4'


def blur(a,sigma):
    # Reflection padding avoids FFT wraparound across the source photograph.
    pad=max(2,int(sigma*3));axes=((pad,pad),(pad,pad))+((0,0),)*(a.ndim-2)
    p=np.pad(a,axes,mode='reflect');h,w=p.shape[:2]
    f=np.exp(-2*math.pi**2*sigma**2*(np.fft.fftfreq(h)[:,None]**2+np.fft.rfftfreq(w)[None,:]**2))
    if a.ndim==3:f=f[:,:,None]
    return np.fft.irfft2(np.fft.rfft2(p,axes=(0,1))*f,s=(h,w),axes=(0,1)).real[pad:-pad,pad:-pad].astype(np.float32)


def sample(a,uv):
    h,w=a.shape[:2];x=np.clip(uv[:,0],0,w-1.001);y=np.clip(uv[:,1],0,h-1.001)
    ix=x.astype(int);iy=y.astype(int);fx=x-ix;fy=y-iy
    if a.ndim==3:fx=fx[:,None];fy=fy[:,None]
    return (a[iy,ix]*(1-fx)+a[iy,ix+1]*fx)*(1-fy)+(a[iy+1,ix]*(1-fx)+a[iy+1,ix+1]*fx)*fy


def image(label,pixels,color=True):
    if pixels.ndim==2:pixels=np.repeat(pixels[:,:,None],3,axis=2)
    h,w=pixels.shape[:2];im=bpy.data.images.new(rig.prefix()+' Painted '+label,width=w,height=h)
    im.colorspace_settings.name='sRGB' if color else 'Non-Color'
    rgba=np.concatenate([pixels,np.ones((h,w,1),dtype=np.float32)],axis=2)
    im.pixels.foreach_set(np.flipud(rgba).astype(np.float32).ravel());im.update()
    im.filepath_raw=str(QA/(rig.prefix().lower()+'-paint-'+label+'.png'));im.file_format='PNG';im.save();im.pack()
    return im


def source_pixels():
    im=bpy.data.images.load(str(ROOT/'assets/references'/(rig.prefix().lower()+'-supplied.png')),check_existing=True)
    w,h=im.size;a=np.empty(w*h*4,dtype=np.float32);im.pixels.foreach_get(a)
    return np.flipud(a.reshape(h,w,4))[:,:,:3].copy()


def pixels_from_points(points):
    scale,cx,z0=(300,464,1150) if rig.prefix()=='Orbit' else (250,512,819)
    return np.stack([points[:,0]*scale+cx,z0-points[:,2]*scale],axis=1)


def clone_patch(patch,color):
    if color:
        median=np.median(patch,axis=(0,1))
        patch=median*np.clip(patch/np.maximum(blur(patch,8),.04),.86,1.14)
    else:patch=.5+(patch-.5)*.45
    patch=np.concatenate([patch,patch[:,::-1]],axis=1)
    return np.concatenate([patch,patch[::-1]],axis=0)


def prepare_paint():
    QA.mkdir(parents=True,exist_ok=True)
    rgb=source_pixels();gray=np.mean(rgb,axis=2);low=blur(gray,24)
    # Retain local pigment variation while attenuating broad photographic lighting.
    target=.51
    if rig.prefix()=='Coral':
        y=np.arange(rgb.shape[0])[:,None];t=np.clip((y-565)/85,0,1)
        target=.36-.16*t*t*(3-2*t)
    flat=np.clip(rgb*(target/np.maximum(low,.12))[:,:,None]**.68,0,1)
    flat=np.clip(flat*(np.maximum(blur(gray,5),.04)/np.maximum(gray,.04))[:,:,None]**.65,0,1)
    fine=gray-blur(gray,5)
    relief=np.clip(.5+fine*2.8,.08,.92)
    r,g,b=rgb.transpose(2,0,1)
    if rig.prefix()=='Orbit':valid=(b>g*1.05)&(r>g*1.04)&(b>r*.77)
    else:valid=(r>g*1.12)&(b>g*1.10)
    mask=blur(valid.astype(np.float32),1.3)
    rough=np.clip((.55 if rig.prefix()=='Orbit' else .43)-fine*.7,.28,.72)
    maps={n:image(n,a,c) for n,a,c in [('pigment',flat,True),('relief',relief,False),('mask',mask,False),('roughness',rough,False)]}
    crop=(350,350,570,465) if rig.prefix()=='Orbit' else (430,273,565,316)
    x0,y0,x1,y1=crop
    for label,a,c in [('clone-pigment',flat,True),('clone-relief',relief,False)]:
        patch=clone_patch(a[y0:y1,x0:x1],c)
        maps[label]=image(label,patch,c)
    bpy.context.scene['referencePaintMaps']={n:im.name for n,im in maps.items()}
    print('Reference pigment, relief, variable roughness and cloned side patches prepared')


def body_clones():
    maps=bpy.context.scene['referencePaintMaps']
    x0,y0,x1,y1=(370,756,570,885) if rig.prefix()=='Orbit' else (480,638,550,705)
    for source,label,color in [('pigment','body-clone-pigment',True),('relief','body-clone-relief',False)]:
        im=bpy.data.images[maps[source]];w,h=im.size;a=np.empty(w*h*4,dtype=np.float32);im.pixels.foreach_get(a)
        patch=np.flipud(a.reshape(h,w,4))[y0:y1,x0:x1,:3]
        if rig.prefix()=='Orbit' and color:
            lum=np.mean(patch,axis=2);variation=np.clip(lum/np.median(lum),.7,1.3)
            patch=variation[:,:,None]*np.array([.56,.39,.67],dtype=np.float32)
        patch=clone_patch(patch,color)
        maps[label]=image(label,patch,color).name


def refresh_clones():
    maps=bpy.context.scene['referencePaintMaps']
    x0,y0,x1,y1=(350,350,570,465) if rig.prefix()=='Orbit' else (430,273,565,316)
    for source,label,color in [('pigment','clone-pigment',True),('relief','clone-relief',False)]:
        im=bpy.data.images[maps[source]];w,h=im.size;a=np.empty(w*h*4,dtype=np.float32);im.pixels.foreach_get(a)
        patch=np.flipud(a.reshape(h,w,4))[y0:y1,x0:x1,:3]
        maps[label]=image(label,clone_patch(patch,color),color).name
    body_clones()


def reference_body_points():
    path=ROOT/'.context/qa'/(rig.prefix().lower()+'-complete')/'reference-pose-rig.blend'
    if rig.prefix()=='Coral' and not path.exists():
        # Coral was authored arms-down and never underwent Orbit's rest-pose bake.
        return np.array([v.co[:] for v in rig.obj('Body').data.vertices])
    name=rig.prefix()+' Body'
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=[name]
    o=dst.objects[0]
    try:
        points=np.array([v.co[:] for v in o.data.vertices])
        assert len(points)==len(rig.obj('Body').data.vertices)
        return points
    finally:bpy.data.objects.remove(o,do_unlink=True)


def coordinates():
    body_reference=reference_body_points()
    for o in rig.meshes():
        if not any(s in o.name for s in ['Head','Body','Neck Bridge','Eyelids','Antenna','Collar']):continue
        p=body_reference if o==rig.obj('Body') else np.array([v.co[:] for v in o.data.vertices])
        uv=pixels_from_points(p);h,w=source_pixels().shape[:2]
        layer=o.data.uv_layers.get('ReferencePaint') or o.data.uv_layers.new(name='ReferencePaint')
        loop_vertices=np.array([loop.vertex_index for loop in o.data.loops])
        layer.data.foreach_set('uv',np.stack([uv[:,0]/w,1-uv[:,1]/h],axis=1)[loop_vertices].astype(np.float32).ravel())
        o.data.uv_layers.active_index=0
        normals=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('normal',normals)
        a=np.clip((-normals.reshape(-1,3)[:,1]-.05)/.65,0,1)
        if o==rig.obj('Head') and rig.prefix()=='Orbit':
            for x,y in [(392,305),(620,316)]:
                a*=1-np.exp(-((uv[:,0]-x)/43)**4-((uv[:,1]-y)/31)**4)
        if o==rig.obj('Body') and rig.prefix()=='Orbit':
            # The reference head occludes this shoulder/neck area in its raised-arm pose.
            t=np.clip((uv[:,1]-687)/35,0,1);a*=t*t*(3-2*t)
        front=o.data.attributes.get('reference_front') or o.data.attributes.new('reference_front','FLOAT','POINT')
        front.data.foreach_set('value',(a*a*(3-2*a)).astype(np.float32))
        o['referencePaintUV']='reference pose coordinates, transferred by vertex identity'
    print('Reference-pose painting coordinates attached without changing weights')


def restore_unpainted():
    """Pin retained baked materials to their old UVs before repacking the new atlas."""
    names=[o.name for o in rig.meshes()]
    with bpy.data.libraries.load(str(QA/('before-'+rig.prefix().lower()+'.blend')),link=False) as (src,dst):dst.objects=list(names)
    old=dict(zip(names,dst.objects))
    try:
        for o in rig.meshes():
            previous=old[o.name]
            layer=o.data.uv_layers.get('PreviousAtlas') or o.data.uv_layers.new(name='PreviousAtlas')
            data=np.empty(len(previous.data.loops)*2,dtype=np.float32)
            previous.data.uv_layers[0].data.foreach_get('uv',data);layer.data.foreach_set('uv',data)
            o.data.uv_layers.active_index=0
            for i,m in enumerate(list(o.data.materials)):
                if 'Reference painted' in m.name:continue
                material=previous.data.materials[i].copy();o.data.materials[i]=material
                uv=material.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='PreviousAtlas'
                for n in material.node_tree.nodes:
                    if n.type=='TEX_IMAGE':material.node_tree.links.new(uv.outputs['UV'],n.inputs['Vector'])
                    elif n.type=='NORMAL_MAP':n.uv_map='PreviousAtlas'
        print('Retained eye, bulb, tooth and tongue maps pinned to their original atlas coordinates')
    finally:
        for o in old.values():bpy.data.objects.remove(o,do_unlink=True)


def preserve_finished_details():
    names=[o.name for o in rig.meshes() if not any(s in o.name for s in ['Head','Body','Neck Bridge','Eyelids','Antenna'])]
    with bpy.data.libraries.load(str(QA/('before-'+rig.prefix().lower()+'.blend')),link=False) as (src,dst):dst.objects=list(names)
    old=dict(zip(names,dst.objects))
    try:
        retained=set()
        for name,previous in old.items():
            o=bpy.context.scene.objects[name]
            data=np.empty(len(previous.data.loops)*2,dtype=np.float32)
            previous.data.uv_layers[0].data.foreach_get('uv',data);o.data.uv_layers[0].data.foreach_set('uv',data)
            o.data.uv_layers.active_index=0;o.data.uv_layers[0].active_render=True
            for i,m in enumerate(previous.data.materials):
                o.data.materials[i]=m
                retained.update(n.image for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image)
        for im in retained:
            path=QA/(rig.prefix().lower()+'-retained-'+Path(im.filepath).name)
            im.filepath_raw=str(path)
            if not path.exists():im.save()
            im.pack()
        print('Preserved original UVs/materials on eyes, bulbs, collars and oral details')
    finally:
        for o in old.values():bpy.data.objects.remove(o,do_unlink=True)


def protect_orbit_apertures():
    if rig.prefix()!='Orbit':return
    head=rig.obj('Head')
    if head.get('aperturesProtectedV4'):return
    with bpy.data.libraries.load(str(QA/'before-orbit.blend'),link=False) as (src,dst):dst.objects=['Orbit Head']
    old=dst.objects[0]
    try:
        keys=head.data.shape_keys.key_blocks;basis=keys['Basis'];delta=np.zeros((len(basis.data),3))
        for side in ['L','R']:
            patch=head['patches'][side];n=patch['size'];start=patch['start']
            for row,t in enumerate(rig.LEVELS):
                for j in range(n):
                    i=start+row*n+j
                    delta[i]=(np.array(old.data.shape_keys.key_blocks['Basis'].data[i].co)-np.array(basis.data[i].co))*export.smooth(0,.6,t)
        for k in keys:
            points=np.array([v.co[:] for v in k.data])+delta;k.data.foreach_set('co',points.astype(np.float32).ravel())
        for v,b in zip(head.data.vertices,basis.data):v.co=b.co
        head.data.update();head['aperturesProtectedV4']=True
    finally:bpy.data.objects.remove(old,do_unlink=True)


def sculpt():
    rig.reset();head=rig.obj('Head');assert not head.get('referenceSculptV4')
    rgb=source_pixels();gray=np.mean(rgb,axis=2);detail=blur(gray,1.5)-blur(gray,9)
    body_reference=reference_body_points()
    changes={}
    for o in [head,rig.obj('Body')]:
        p=np.array([v.co[:] for v in o.data.vertices]);delta=np.zeros_like(p)
        original=body_reference if o==rig.obj('Body') else p
        uv=pixels_from_points(original);signal=np.clip(sample(detail,uv)*5,-1,1)
        for i,v in enumerate(o.data.vertices):
            x,y,z=p[i];front=export.smooth(.05,.65,-v.normal.y)
            if o==head:
                if rig.prefix()=='Orbit':
                    brow=math.exp(-((z-2.17)/.12)**2)*math.exp(-((x-.08)/.57)**4)
                    cheeks=sum(math.exp(-((x-c)/.24)**2-((z-1.97)/.18)**2) for c in [-.38,.49])
                    delta[i,1]=-(.028*brow+.016*cheeks)*front
                else:
                    cheeks=sum(math.exp(-((x-c)/.18)**2-((z-1.30)/.28)**2) for c in [-.40,.34])
                    delta[i,1]=-.018*cheeks*front
                # Fine grain remains a normal map; only broad facial volume is sculpted.
            else:
                # Exclude fingertips and feet from the stronger torso/forearm relief.
                strength=.010 if rig.prefix()=='Orbit' else .0025
                strength*=export.smooth(.22,.50,z)
                displacement=signal[i]*strength*front
                delta[i]=np.array(v.normal[:])*displacement
        if o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:
                a=np.array([v.co[:] for v in k.data])+delta;k.data.foreach_set('co',a.astype(np.float32).ravel())
        o.data.vertices.foreach_set('co',(p+delta).astype(np.float32).ravel());o.data.update()
        changes[o.name]={'verticesMoved':int(np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-6)),'maximumDisplacement':float(np.max(np.linalg.norm(delta,axis=1)))}
    head['referenceSculptV4']=True
    attach_cavity()
    (QA/(rig.prefix().lower()+'-sculpt.json')).write_text(json.dumps(changes,indent=2));print(changes)


def attach_cavity():
    head=rig.obj('Head');cavity=rig.obj('Oral Cavity');_,n,levels,*_=rig.face_config()
    start=head['patches']['mouth']['start']+(len(levels)-1)*n
    for key in cavity.data.shape_keys.key_blocks:
        target=head.data.shape_keys.key_blocks.get(key.name,head.data.shape_keys.key_blocks['Basis'])
        changes=[target.data[start+j].co+Vector((0,.001,0))-key.data[j].co for j in range(n)]
        for i,v in enumerate(key.data):
            row,j=divmod(i,n)
            if row<9:v.co+=changes[j]*(1-export.smooth(.1,.8,row/12))
    for v,b in zip(cavity.data.vertices,cavity.data.shape_keys.key_blocks['Basis'].data):v.co=b.co
    cavity.data.update()


def painted_materials(only=None):
    maps={n:bpy.data.images[name] for n,name in bpy.context.scene['referencePaintMaps'].items()}
    for o in rig.meshes():
        if only and o not in [obj for label in only for obj in export.groups()[label][0]]:continue
        if not o.data.uv_layers.get('ReferencePaint'):continue
        for i,old in enumerate(list(o.data.materials)):
            rear=o==rig.obj('Head') and ('Mouth' in old.name or 'rear seal' in old.name)
            if not rear and ('Mouth' in old.name or 'Oral' in old.name):continue
            lip='lips' in old.name.lower()
            neck='Neck Bridge' in o.name
            s=surfaces.Surface('Reference painted '+o.name+(' rear seal' if rear else ' lips' if lip else ' skin'),(.3,.2,.35),.53)
            uv=s.node('ShaderNodeUVMap');uv.uv_map='ReferencePaint'
            def tex(label,projected=True):
                t=s.node('ShaderNodeTexImage');t.image=maps[label]
                if projected:s.wire(uv.outputs['UV'],t.inputs['Vector'])
                else:
                    t.projection='BOX';t.projection_blend=.35
                    s.wire(s.coord,t.inputs['Vector'])
                return t.outputs['Color']
            weight=0 if rear or neck else 1 if lip else s.math('MULTIPLY',s.attribute('reference_front'),tex('mask'))
            clone='body-clone-' if (o==rig.obj('Body') or neck) and 'body-clone-pigment' in maps else 'clone-'
            color=s.mix(weight,tex(clone+'pigment',False),tex('pigment'))
            s.wire(color,s.p.inputs['Base Color'])
            height=s.mix(weight,tex(clone+'relief',False),tex('relief'))
            s.bump(height,.024 if rig.prefix()=='Orbit' else .012,.65)
            s.wire(tex('roughness'),s.p.inputs['Roughness'])
            s.p.inputs['Coat Weight'].default_value=.06 if rig.prefix()=='Orbit' else .12
            o.data.materials[i]=s.mat
    bpy.context.scene['surfaceRevision']='reference-painted-sculpt-4'
    print('Reference-sampled pigment/relief and variable roughness assigned; no silhouette billboard')


def save():
    rig.reset();bpy.ops.wm.save_as_mainfile(filepath=str(QA/(rig.prefix().lower()+'-candidate.blend')))


def bake(label):
    old=export.QA
    try:export.QA=QA;export.bake_group(label,roughness=True)
    finally:export.QA=old
    save()


def export_candidate():
    preserve_finished_details();protect_orbit_apertures()
    # Reference relief should read as small tool marks under runtime lighting.
    for o in rig.meshes():
        for m in o.data.materials:
            if 'Reference painted' not in m.name:continue
            for node in m.node_tree.nodes:
                if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.60 if rig.prefix()=='Orbit' else .40
    save()
    old=export.QA
    try:export.QA=QA;export.export_candidate()
    finally:export.QA=old


def audit():
    old=export.QA
    try:
        export.QA=QA
        export.audit(before_path=QA/('before-'+rig.prefix().lower()+'.blend'))
    finally:export.QA=old
    names=[rig.prefix()+' Head',rig.prefix()+' Body']
    with bpy.data.libraries.load(str(QA/('before-'+rig.prefix().lower()+'.blend')),link=False) as (src,dst):dst.objects=list(names)
    previous=dict(zip(names,dst.objects));report={}
    try:
        for name,old in previous.items():
            o=bpy.context.scene.objects[name];old.data.calc_loop_triangles()
            triangles=np.array([t.vertices[:] for t in old.data.loop_triangles])
            a=np.array([v.co[:] for v in old.data.vertices])[triangles]
            b=np.array([v.co[:] for v in o.data.vertices])[triangles]
            n=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);q=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0])
            flips=int(np.count_nonzero(np.sum(n*q,axis=1)<-1e-12))
            report[name]={'newReversedTriangles':flips,'triangles':len(triangles)}
            assert flips==0,(name,flips)
        (QA/(rig.prefix().lower()+'-sculpt-topology.json')).write_text(json.dumps(report,indent=2));print(report)
    finally:
        for o in previous.values():bpy.data.objects.remove(o,do_unlink=True)


def limit_sculpt_folds():
    names=[rig.prefix()+' Head',rig.prefix()+' Body']
    with bpy.data.libraries.load(str(QA/('before-'+rig.prefix().lower()+'.blend')),link=False) as (src,dst):dst.objects=list(names)
    previous=dict(zip(names,dst.objects));report={}
    try:
        for name,old in previous.items():
            o=bpy.context.scene.objects[name];old.data.calc_loop_triangles()
            triangles=np.array([t.vertices[:] for t in old.data.loop_triangles]);base=np.array([v.co[:] for v in old.data.vertices])
            start=np.array([v.co[:] for v in o.data.vertices]);delta=start-base
            a=base[triangles];normal=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);first=0
            for step in range(60):
                b=(base+delta)[triangles];q=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0]);bad=np.sum(normal*q,axis=1)<-1e-12
                if step==0:first=int(np.count_nonzero(bad))
                if not np.any(bad):break
                selected=np.zeros(len(base),dtype=bool);selected[triangles[bad].ravel()]=True
                neighbors=np.unique(triangles[np.any(selected[triangles],axis=1)])
                delta[neighbors]*=.5
            else:raise AssertionError('Sculpt fold limiter did not converge: '+name)
            correction=base+delta-start
            if o.data.shape_keys:
                for k in o.data.shape_keys.key_blocks:
                    points=np.array([v.co[:] for v in k.data])+correction;k.data.foreach_set('co',points.astype(np.float32).ravel())
            o.data.vertices.foreach_set('co',(base+delta).astype(np.float32).ravel());o.data.update()
            report[name]={'initialFoldedTriangles':first,'remaining':0,'localReductionSteps':step}
        attach_cavity()
        (QA/(rig.prefix().lower()+'-sculpt-limits.json')).write_text(json.dumps(report,indent=2));print(report)
    finally:
        for o in previous.values():bpy.data.objects.remove(o,do_unlink=True)


def promote():
    audit();name=rig.prefix().lower()
    assert bpy.context.scene['surfaceRevision']=='reference-painted-sculpt-4'
    paths=list(QA.glob(name+'-paint-*.png'))+list(QA.glob(name+'-retained-*.png'))
    paths += [QA/(name+'-'+label+'-'+channel+'.png') for label in export.groups() for channel in ['basecolor','normal','roughness']]
    for path in paths:
        destination=ROOT/'assets/likeness-trials'/path.name;shutil.copy2(path,destination)
        for im in bpy.data.images:
            if im.filepath and Path(im.filepath).name==path.name:im.filepath=str(destination);im.pack()
    save();export_candidate()
    shutil.copy2(QA/(name+'-candidate.glb'),ROOT/'assets/likeness-trials'/(name+'-image-rig.glb'))
    filenames={p.name for p in paths}
    for im in bpy.data.images:
        if im.filepath and Path(im.filepath).name in filenames:
            im.filepath=str(ROOT/'assets/likeness-trials'/Path(im.filepath).name);im.pack()
    # Preserve tracked automatic backups; this revision has explicit before-state files.
    versions=bpy.context.preferences.filepaths.save_version;bpy.context.preferences.filepaths.save_version=0
    try:bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/likeness-trials'/(name+'-image-rig.blend')))
    finally:bpy.context.preferences.filepaths.save_version=versions
