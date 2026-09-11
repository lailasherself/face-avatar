"""Finish the user's fresh image-contour sources in live Blender, one at a time."""
import ast
import bpy
import bmesh
import hashlib
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.geometry import delaunay_2d_cdt
from complete_clay_likeness import smooth, plain_material, closed_rings, mesh, profile
from complete_cosmic_likeness import ellipsoid, inside, tube
from build_avatar_fleet import CHANNELS

ROOT=Path(__file__).resolve().parents[1]
LEVELS=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1]


def prefix():return bpy.context.scene['completionCharacter']
def obj(n):return bpy.context.scene.objects[prefix()+' '+n]
def qa():return ROOT/'.context/qa'/(prefix().lower()+'-complete')
def meshes():return [o for o in bpy.context.scene.objects if o.type=='MESH']


def prepare(character):
    p=character.title();s=bpy.context.scene
    lock=json.loads((ROOT/'scripts/reference-source-lock.json').read_text())[character]
    assert s['sourceReference']==str(ROOT/lock['image'])
    assert hashlib.sha256((ROOT/lock['image']).read_bytes()).hexdigest()==lock['sha256']
    assert not any(o.type=='ARMATURE' for o in s.objects),'Already rigged; do not rebuild'
    s['completionCharacter']=p;s['referenceSHA256']=lock['sha256'];qa().mkdir(parents=True,exist_ok=True)
    s['status']='Fresh supplied-image source: detailing and rigging in progress'
    s['completionMaterials']={n:plain_material(p+' '+n,c,r).name for n,c,r in [('Oral interior',(.008,.001,.003),.94),('Teeth',(.82,.73,.56),.32),('Tongue',(.50,.06,.10),.45)]}
    if p=='Orbit':
        import build_supplied_orbit as source
        arms={'R':[source.point(303,707,.035),source.point(238,720,.015),source.point(142,601,-.29),source.point(137,583,-.31)],'L':[source.point(600,711,.045),source.point(644,774,.015),source.point(770,675,-.29),source.point(786,659,-.31)]}
        pixels=ast.literal_eval(obj('Body')['referenceDigitPixels'])
        digits={side:{n:[source.point(x,z,-.32-.015*i) for i,(x,z) in enumerate(points)] for n,points in dd.items()} for side,dd in pixels.items()}
        hip,knee,ankle,neck,head=.67,.34,.13,1.65,2.65
    else:
        import build_supplied_coral as source
        arms={side:[source.point(x,z,.045) for x,z in ps] for side,ps in {'R':[(452,594),(424,655),(406,704),(403,741)],'L':[(570,590),(597,648),(619,703),(623,736)]}.items()}
        digits={'L':{},'R':{}};hip,knee,ankle,neck,head=.36,.18,.065,.96,1.9
    s['rigArms']={side:[list(v) for v in ps] for side,ps in arms.items()}
    s['rigDigits']={side:{n:[list(v) for v in ps] for n,ps in dd.items()} for side,dd in digits.items()}
    s['rigStations']=[hip,knee,ankle,neck,head]
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/likeness-trials'/(character+'-image-rig.blend')))


def paths():
    s=bpy.context.scene
    return ({side:[Vector(tuple(p)) for p in ps] for side,ps in s['rigArms'].items()},
            {side:{n:[Vector(tuple(p)) for p in ps] for n,ps in dd.items()} for side,dd in s['rigDigits'].items()})


def closest(p,path):
    result=(1e9,0)
    for i,(a,b) in enumerate(zip(path,path[1:])):
        d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));dist=(p-a-d*t).length
        if dist<result[0]:result=dist,i+t
    return result


def detail_orbit():
    import build_supplied_orbit as source
    arms,digits=paths();o=obj('Body');m=source.mat('Skin').copy();m.name='Orbit Sculpted Clay Body';o.data.materials.clear();o.data.materials.append(m)
    flow=o.data.attributes.new('sculpt_flow','FLOAT','POINT');belly=o.data.attributes.new('belly_mask','FLOAT','POINT')
    for v in o.data.vertices:
        x,y,z=v.co;side='L' if x>0 else 'R';value=z
        if abs(x)>.57 and z>1.2:
            _,u=closest(v.co,arms[side]);value=u*.28
            d,du,digit=min((*closest(v.co,ps),n) for n,ps in digits[side].items())
            if d<.09 and du>.2:value=du*.13
        flow.data[v.index].value=value
        r=math.sqrt(((x-.025)/.55)**2+((z-1.015)/.55)**2)
        belly.data[v.index].value=(1-smooth(.87,1.05,r))*smooth(-.04,-.19,y)
        v.select=False
    n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF']
    attr=n.new('ShaderNodeAttribute');attr.attribute_name='belly_mask'
    tint=n.new('ShaderNodeMixRGB');tint.inputs[1].default_value=(.40,.255,.52,1);tint.inputs[2].default_value=(.64,.285,.34,1);l.new(attr.outputs['Fac'],tint.inputs[0]);l.new(tint.outputs[0],p.inputs['Base Color'])
    a=n.new('ShaderNodeAttribute');a.attribute_name='sculpt_flow'
    mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=285;l.new(a.outputs['Fac'],mul.inputs[0])
    wave=n.new('ShaderNodeMath');wave.operation='SINE';l.new(mul.outputs[0],wave.inputs[0])
    previous=p.inputs['Normal'].links[0].from_socket
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.38;bump.inputs['Distance'].default_value=.012;l.new(wave.outputs[0],bump.inputs['Height']);l.new(previous,bump.inputs['Normal']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
    for side in ['L','R']:
        eye=obj('Eye '+side);pupil=source.point(390,524) if side=='R' else source.point(638,536);rx,rz=(.078,.089) if side=='R' else (.066,.083)
        m=source.mat('Gold').copy();m.name='Orbit Glass Iris '+side;eye.data.materials.clear();eye.data.materials.append(m)
        for f in eye.data.polygons:f.material_index=0
        n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];tex=n.new('ShaderNodeTexCoord')
        sub=n.new('ShaderNodeVectorMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=pupil;l.new(tex.outputs['Object'],sub.inputs[0])
        scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(1/rx,0,1/rz);l.new(sub.outputs[0],scale.inputs[0])
        length=n.new('ShaderNodeVectorMath');length.operation='LENGTH';l.new(scale.outputs[0],length.inputs[0])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.98;ramp.color_ramp.elements[0].color=(.0004,.001,.0005,1);ramp.color_ramp.elements[1].position=1.02;ramp.color_ramp.elements[1].color=(.96,.38,.002,1);l.new(length.outputs['Value'],ramp.inputs[0]);l.new(ramp.outputs['Color'],p.inputs['Base Color'])
        p.inputs['Roughness'].default_value=.11;p.inputs['Coat Weight'].default_value=1
        eye['eyeCenter']=[sum(v.co.x for v in eye.data.vertices)/len(eye.data.vertices),sum(v.co.z for v in eye.data.vertices)/len(eye.data.vertices)]
    for o in meshes():
        if 'Antenna' not in o.name:continue
        m=source.mat('Skin').copy();m.name=o.name+' Wrinkled Clay';o.data.materials[0]=m
        n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];previous=p.inputs['Normal'].links[0].from_socket
        a=o.data.attributes.new('sculpt_flow','FLOAT','POINT')
        for v in o.data.vertices:a.data[v.index].value=min(99,v.index//40)/99
        attr=n.new('ShaderNodeAttribute');attr.attribute_name='sculpt_flow';mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=240;l.new(attr.outputs['Fac'],mul.inputs[0]);wave=n.new('ShaderNodeMath');wave.operation='SINE';l.new(mul.outputs[0],wave.inputs[0]);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.35;b.inputs['Distance'].default_value=.013;l.new(wave.outputs[0],b.inputs['Height']);l.new(previous,b.inputs['Normal']);l.new(b.outputs['Normal'],p.inputs['Normal'])


def soften_orbit_detail():
    reset()
    for o in meshes():
        if o!=obj('Body') and 'Antenna' not in o.name:continue
        m=o.data.materials[0];n=m.node_tree.nodes;l=m.node_tree.links;wave=next(x for x in n if x.type=='MATH' and x.operation=='SINE');source=wave.inputs[0].links[0].from_socket
        tex=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=8;noise.inputs['Detail'].default_value=4;l.new(tex.outputs['Object'],noise.inputs['Vector'])
        mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=11;l.new(noise.outputs['Fac'],mul.inputs[0]);add=n.new('ShaderNodeMath');add.operation='ADD';l.new(source,add.inputs[0]);l.new(mul.outputs[0],add.inputs[1]);l.new(add.outputs[0],wave.inputs[0])
        last=n['Principled BSDF'].inputs['Normal'].links[0].from_node;last.inputs['Strength'].default_value=.19;last.inputs['Distance'].default_value=.005
    for side in ['L','R']:
        eye=obj('Eye '+side);n=78 if side=='R' else 72
        for key in eye.data.shape_keys.key_blocks:
            if key.name.startswith('eyeBlink'):continue
            for i,v in enumerate(key.data):
                r=1.015*(1-min(48,i//n)/49);v.co.y-=.045*max(0,1-r*r)
        eye.data.update()
    for v in obj('Upper Teeth').data.vertices:v.co.z+=.010
    for key in obj('Upper Teeth').data.shape_keys.key_blocks:
        for v in key.data:v.co.z+=.010
    bpy.context.view_layer.update()


def skeleton():
    arms,digits=paths();hip,knee,ankle,neck,head=bpy.context.scene['rigStations'];p=prefix();body=obj('Body')
    data=bpy.data.armatures.new(p+' Skeleton');rig=bpy.data.objects.new(p+' AvatarRig',data);bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    def bone(n,a,b,parent=None):
        e=data.edit_bones.new(n);e.head=a;e.tail=b
        if parent:e.parent=data.edit_bones[parent]
        return e
    chest=min(v[0].z for v in arms.values());cx=.025 if p=='Orbit' else .008
    bone('Root',(0,0,0),(0,0,.08));bone('Hips',(cx,0,hip),(cx,0,hip+.10),'Root');bone('Spine',(cx,0,hip+.10),(cx,0,chest-.10),'Hips');bone('Chest',(cx,0,chest-.10),(cx,0,chest),'Spine');bone('Neck',(cx,0,chest),(cx,0,neck),'Chest');bone('Head',(cx,0,neck),(cx,0,head),'Neck')
    for side,ps in arms.items():
        for i,n in enumerate(['UpperArm','Forearm','Hand']):bone(n+'.'+side,ps[i],ps[i+1],'Chest' if i==0 else ['UpperArm','Forearm'][i-1]+'.'+side)
        x=(-.407 if side=='R' else .433) if p=='Orbit' else (-.152 if side=='R' else .164)
        bone('Thigh.'+side,(x,0,hip),(x,0,knee),'Hips');bone('Shin.'+side,(x,0,knee),(x,-.04,ankle),'Thigh.'+side);bone('Foot.'+side,(x,-.04,ankle),(x,-.21,.045),'Shin.'+side)
        for digit,ps in digits[side].items():
            for i in range(3):e=bone(f'{digit}{i+1}.{side}',ps[i],ps[i+1],f'{digit}{i}.{side}' if i else 'Hand.'+side);e.align_roll(Vector((0,-1,0)))
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig['installationApproved']=False;rig['rigVersion']=p.lower()+'-supplied-image-1'
    for side in arms:
        data.bones['UpperArm.'+side]['armCollisionRestContact']=True
        for digit in digits[side]:
            for i,a in enumerate([.45,.55,.40]):data.bones[f'{digit}{i+1}.{side}']['fingerCurlRadians']=a
    groups={b.name:body.vertex_groups.new(name=b.name) for b in data.bones}
    regions={}
    if p=='Coral':
        adj=[[] for v in body.data.vertices]
        for e in body.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
        remaining={v.index for v in body.data.vertices if v.co.z<.72}
        while remaining:
            todo=[remaining.pop()];component=list(todo)
            while todo:
                for j in adj[todo.pop()]:
                    if j in remaining:remaining.remove(j);todo.append(j);component.append(j)
            mx=sum(body.data.vertices[i].co.x for i in component)/len(component)
            for i in component:regions[i]=1 if abs(mx)>.30 else 0
    for v in body.data.vertices:
        x,y,z=v.co;side='L' if x>cx else 'R';t=smooth(hip+.06,chest-.07,z);n=smooth(chest+.015,neck,z);w={'Hips':(1-t)*(1-n),'Chest':t*(1-n),'Neck':n}
        leg=1-smooth(hip-.12,hip+.09,z)
        if leg:
            k=1-smooth(knee-.1,knee+.1,z);f=1-smooth(ankle-.025,ankle+.09,z);lw={'Thigh.'+side:1-k,'Shin.'+side:k*(1-f),'Foot.'+side:k*f};w={n:a*(1-leg) for n,a in w.items()};w.update({n:a*leg for n,a in lw.items()})
        if p=='Orbit':arm=smooth(.32,.69,abs(x-cx))*smooth(1.10,1.30,z)
        else:arm=regions.get(v.index,smooth(.13,.33,abs(x-cx)))
        if arm:
            dist,u=closest(v.co,arms[side]);e=smooth(.60,1.40,u);hand=smooth(1.80,2.35,u);aw={'UpperArm.'+side:1-e,'Forearm.'+side:e*(1-hand),'Hand.'+side:e*hand}
            if digits[side] and u>1.65:
                d,du,digit=min((*closest(v.co,ps),n) for n,ps in digits[side].items());factor=smooth(.12,.92,du)*(1-smooth(.08,.14,d));q=max(0,min(2,du-.5));i=min(1,int(q));f=q-i;aw={n:a*(1-factor) for n,a in aw.items()};aw[f'{digit}{i+1}.{side}']=(1-f)*factor;aw[f'{digit}{i+2}.{side}']=f*factor
            w={n:a*(1-arm) for n,a in w.items()};w.update({n:a*arm for n,a in aw.items()})
        for n,a in w.items():
            if a>1e-8:groups[n].add([v.index],a,'REPLACE')
    for o in meshes():
        if o!=body:o.vertex_groups.new(name='Head').add(list(range(len(o.data.vertices))),1,'REPLACE')
        o.parent=rig;m=o.modifiers.new('Reference body deformation','ARMATURE');m.object=rig
    body['armCollisionSurface']=True;obj('Head')['armCollisionSurface']=True
    normalize()
    print({'bones':len(data.bones),'native_fingers':sum(len(d) for d in digits.values())})


def normalize():
    for o in meshes():
        rows=[]
        for v in o.data.vertices:
            pairs=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-7],key=lambda p:-p[1])[:4];total=sum(a for _,a in pairs);assert total>0
            rows.append([(i,a/total) for i,a in pairs])
        for g in o.vertex_groups:g.remove(list(range(len(rows))))
        for j,row in enumerate(rows):
            for i,a in row:o.vertex_groups[i].add([j],a,'REPLACE')


def relax_weights(iterations=650):
    o=obj('Body');count=len(o.data.vertices);groups=list(o.vertex_groups);arms,digits=paths();w=np.zeros((count,len(groups)))
    for v in o.data.vertices:
        for g in v.groups:w[v.index,g.group]=g.weight
    edges=np.array([e.vertices[:] for e in o.data.edges]);a=np.r_[edges[:,0],edges[:,1]];b=np.r_[edges[:,1],edges[:,0]]
    coords=np.array([v.co[:] for v in o.data.vertices]);conductance=1/np.maximum(np.sum((coords[a]-coords[b])**2,axis=1),1e-8);degree=np.maximum(np.bincount(a,weights=conductance,minlength=count),1)
    mask=[]
    for v in o.data.vertices:
        x,y,z=v.co;side='L' if x>0 else 'R';ps=arms[side]
        shoulder=(v.co-ps[0]).length;elbow=(v.co-ps[1]).length;wrist=(v.co-ps[2]).length
        amount=max(1-smooth(.30,.51,shoulder),1-smooth(.27,.46,elbow),1-smooth(.13,.25,wrist))
        mask.append(amount*smooth(.10,.24,abs(x))*.8)
    mask=np.array(mask)
    for _ in range(iterations):
        mean=np.stack([np.bincount(a,weights=w[b,i]*conductance,minlength=count)/degree for i in range(len(groups))],axis=1);w+=(mean-w)*mask[:,None]
    for g in groups:g.remove(list(range(count)))
    for j,row in enumerate(w):
        weights={groups[i].name:float(v) for i,v in enumerate(row) if v>1e-7};x=o.data.vertices[j].co.x;side='L' if x>0 else 'R'
        if any(weights.get(n+'.'+side,0)>1e-7 for n in ['UpperArm','Forearm','Hand']):
            trunk=sum(weights.pop(n,0) for n in ['Hips','Spine','Chest','Neck','Head']);weights['Chest']=trunk
        pairs=bounded_weights(weights);total=sum(v for _,v in pairs)
        for n,v in pairs:o.vertex_groups[n].add([j],v/total,'REPLACE')


def bounded_weights(weights):
    bones=obj('AvatarRig').data.bones;w={n:a for n,a in weights.items() if a>1e-7}
    def ancestor(a,b):
        p=bones[b].parent
        while p:
            if p.name==a:return True
            p=p.parent
        return False
    while len(w)>4:
        leaves=[n for n in w if not any(n!=m and ancestor(n,m) for m in w)]
        name=min(leaves,key=lambda n:w[n]);p=bones[name].parent
        while p and p.name not in w:p=p.parent
        if p:w[p.name]+=w.pop(name)
        else:
            amount=w.pop(name);target=max(w,key=w.get);w[target]+=amount
    return list(w.items())


def clean_finger_transitions():
    o=obj('Body');arms,digits=paths();rows=[]
    for v in o.data.vertices:
        w={o.vertex_groups[g.group].name:g.weight for g in v.groups};side='L' if v.co.x>0 else 'R'
        if prefix()=='Orbit' and v.co.z>1.12:
            transfer=smooth(.45,.76,abs(v.co.x))*smooth(1.12,1.40,v.co.z)
            for parent in ['Hips','Spine','Chest','Neck']:
                amount=w.get(parent,0)*transfer;w[parent]=w.get(parent,0)-amount;w['UpperArm.'+side]=w.get('UpperArm.'+side,0)+amount
            transfer=smooth(.66,.81,abs(v.co.x))*smooth(1.36,1.53,v.co.z)
            amount=w.get('UpperArm.'+side,0)*transfer;w['UpperArm.'+side]=w.get('UpperArm.'+side,0)-amount;w['Forearm.'+side]=w.get('Forearm.'+side,0)+amount
        if digits[side]:
            fd={d:sum(w.get(f'{d}{i}.{side}',0) for i in [1,2,3]) for d in digits[side]};digit=max(fd,key=fd.get);total=sum(fd.values())
            if total>0:
                dist,u=closest(v.co,digits[side][digit]);amount=1-smooth(.075,.14,dist);amount*=smooth(.02,.25,u)
                for d in fd:
                    for i in [1,2,3]:w.pop(f'{d}{i}.{side}',None)
                w['Hand.'+side]=w.get('Hand.'+side,0)+total*(1-amount);total*=amount
                if total>1e-7:
                    inherited=sum(w.pop(n,0) for n in ['Hips','Spine','Chest','Neck','Head','UpperArm.'+side]);w['Forearm.'+side]=w.get('Forearm.'+side,0)+inherited
                    q=max(0,min(2,u-.5));i=min(1,int(q));t=q-i;w[f'{digit}{i+1}.{side}']=total*(1-t);w[f'{digit}{i+2}.{side}']=total*t
        pairs=sorted([(n,a) for n,a in w.items() if a>1e-7],key=lambda p:-p[1])[:4];total=sum(a for _,a in pairs);rows.append([(n,a/total) for n,a in pairs])
    for g in o.vertex_groups:g.remove(list(range(len(rows))))
    for i,row in enumerate(rows):
        for n,a in row:o.vertex_groups[n].add([i],a,'REPLACE')


def standing_rest():
    reset();rig=obj('AvatarRig');body=obj('Body');assert not body.data.shape_keys
    assert not rig.get('standingRestApplied',False)
    bpy.ops.wm.save_as_mainfile(filepath=str(qa()/'reference-pose-rig.blend'),copy=True)
    for side in ['L','R']:
        sign=1 if side=='L' else -1
        for name,direction in [('UpperArm',(sign*.65,0,-1)),('Forearm',(sign*.25,-.12,-1)),('Hand',(sign*.25,-.12,-1))]:
            bone=rig.pose.bones[name+'.'+side];current=bone.matrix.to_quaternion();axis=current@Vector((0,1,0));target=axis.rotation_difference(Vector(direction).normalized())@current
            matrix=target.to_matrix().to_4x4();matrix.translation=bone.head;bone.matrix=matrix;bpy.context.view_layer.update()
    ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();coords=np.array([v.co[:] for v in m.vertices],dtype=np.float32);ev.to_mesh_clear()
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.armature_apply(selected=False);bpy.ops.object.mode_set(mode='OBJECT')
    body.data.vertices.foreach_set('co',coords.ravel());body.data.update();rig['standingRestApplied']=True
    bpy.context.scene['rigArms']={side:[list(rig.data.bones[n+'.'+side].head_local) for n in ['UpperArm','Forearm','Hand']]+[list(rig.data.bones['Hand.'+side].tail_local)] for side in ['L','R']}
    reset();save()


def relax_neutral_surface():
    reset();o=obj('Body');arms,_=paths();g=o.vertex_groups.new(name='NeutralSurfaceRelax')
    for v in o.data.vertices:
        side='L' if v.co.x>0 else 'R';d=min((v.co-p).length for p in arms[side][:2]);w=(1-smooth(.20,.48,d))*smooth(.20,.38,abs(v.co.x))
        if w>0:g.add([v.index],w,'REPLACE')
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Relax neutral shoulder compression','SMOOTH');mod.factor=.65;mod.iterations=45;mod.vertex_group=g.name
    while list(o.modifiers).index(mod)>0:bpy.ops.object.modifier_move_up(modifier=mod.name)
    group_name=g.name;bpy.ops.object.modifier_apply(modifier=mod.name);o.vertex_groups.remove(o.vertex_groups[group_name]);o.data.update();bpy.context.view_layer.update()


def reset():
    for o in bpy.context.scene.objects:
        if o.type=='ARMATURE':
            for b in o.pose.bones:b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion();b.location=(0,0,0);b.scale=(1,1,1)
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=0
    bpy.context.view_layer.update()


def rotate(name,axis,angle):
    b=obj('AvatarRig').pose.bones[name];b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion(Vector(axis),angle);bpy.context.view_layer.update()


def expression(values):
    for o in meshes():
        if o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=values.get(k.name,0)
    bpy.context.view_layer.update()


def render(label):
    s=bpy.context.scene;s.render.filepath=str(qa()/(label+'.png'));bpy.ops.render.render(write_still=True)


def save():bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/likeness-trials'/(prefix().lower()+'-image-rig.blend')))


def face_config():
    if prefix()=='Orbit':
        import build_supplied_orbit as source
        return source,120,LEVELS,.172,.087,.020
    import build_supplied_coral as source
    return source,160,[i/16 for i in range(1,17)],.365,.125,.025


def mouth_point(j):
    source,n,levels,width,opening,drop=face_config();p=obj('Head')['patches']['mouth'];i=p['start']+(len(levels)-1)*n+j
    h=obj('Head');data=h.data.shape_keys.key_blocks['Basis'].data if h.data.shape_keys else h.data.vertices
    return data[i].co.copy()


def mouth_motion(j,name):
    source,n,levels,width,opening,drop=face_config();center=source.MOUTH;phi=j*math.tau/n;q=math.cos(phi);sn=math.sin(phi);p=mouth_point(j);v=p.copy()
    side=1 if name.endswith('Left') else -1;mask=smooth(-.25,.55,q*side);top=max(0,sn);bottom=max(0,-sn);scale=1 if prefix()=='Orbit' else 1.4
    if name in {'jawOpen','mouthClose'}:
        target=Vector((center.x+(width+.008)*q,0,center.y-drop+opening*sn));target.y=source.depth((target.x,target.z))+(p.y-source.depth((p.x,p.z)))
        return (target-p)*(1 if name=='jawOpen' else -1)
    if name in {'jawLeft','jawRight','mouthLeft','mouthRight'}:v.x+=side*.014*scale
    elif name=='jawForward':v.y-=.014
    elif name.startswith('mouthSmile'):v.z+=.014*mask*abs(q)*scale;v.x+=side*.005*mask
    elif name.startswith('mouthFrown'):v.z-=.010*mask*abs(q)*scale
    elif name.startswith('mouthDimple'):v.x+=side*.006*mask;v.y+=.005*mask
    elif name.startswith('mouthStretch'):v.x+=side*.012*mask
    elif name in {'mouthPucker','mouthFunnel'}:v.x=center.x+(v.x-center.x)*(.88 if name=='mouthPucker' else .94);v.z+=.010*sn;v.y-=.014
    elif name=='mouthRollUpper':v.z-=.002*top;v.y+=.005*top
    elif name=='mouthRollLower':v.z+=.002*bottom;v.y+=.005*bottom
    elif name=='mouthShrugUpper':v.z+=.010*top
    elif name=='mouthShrugLower':v.z+=.006*bottom
    elif name.startswith('mouthPress'):v.z-=.0015*sn*mask
    elif name.startswith('mouthUpperUp'):v.z+=.013*top*mask
    elif name.startswith('mouthLowerDown'):v.z-=.014*bottom*mask
    return v-p


def facial_orbit():
    source,n,levels,width,opening,drop=face_config();h=obj('Head');base=h.shape_key_add(name='Basis',from_mix=False);patches=h['patches'];poly=source.outline()
    for name in CHANNELS:
        if name=='tongueOut':continue
        key=h.shape_key_add(name=name,from_mix=False)
        if name.startswith(('mouth','jaw')):
            deltas=[mouth_motion(j,name) for j in range(n)];start=patches['mouth']['start']
            for row,t in enumerate(levels):
                for j in range(n):
                    i=start+row*n+j;b=base.data[i].co;p=b+deltas[j]*t
                    p.y=source.depth((p.x,p.z),poly)+b.y-source.depth((b.x,b.z),poly)
                    if name not in {'jawOpen','mouthClose'}:p.y+=deltas[j].y*t
                    key.data[i].co=p
        elif name.startswith(('eyeBlink','eyeWide','eyeSquint')):
            side='L' if name.endswith('Left') else 'R';patch=patches[side];center=Vector(obj('Eye '+side)['eyeCenter']);factor=-.999 if 'Blink' in name else -.35 if 'Squint' in name else .13
            for row,t in enumerate(levels):
                for j in range(patch['size']):
                    i=patch['start']+row*patch['size']+j;p=base.data[i].co.copy();p.z+=(p.z-center.y)*factor*t;p.y=source.depth((p.x,p.z),poly)-.009*math.sin(t*math.pi);key.data[i].co=p
        else:
            side='L' if name.endswith('Left') else 'R';center=Vector(obj('Eye '+side)['eyeCenter'])
            for v,b in zip(key.data,base.data):
                x,y,z=b.co;front=smooth(0,-.3,y);near=math.exp(-((x-center.x)/.24)**4)
                if name.startswith('brow'):v.co.z+=(.022 if 'Up' in name else -.018)*front*near*math.exp(-((z-center.y-.14)/.14)**4)
                elif name.startswith('cheekSquint'):v.co.z+=.012*front*near*math.exp(-((z-center.y+.12)/.13)**4)
                elif name=='cheekPuff':v.co.y-=.020*front*math.exp(-((z-source.MOUTH.y)/.18)**4)
                elif name.startswith('noseSneer'):v.co.z+=.012*front*near*math.exp(-((z-source.MOUTH.y-.1)/.14)**4)
    for side,label in [('L','Left'),('R','Right')]:
        o=obj('Eye '+side);base=o.shape_key_add(name='Basis',from_mix=False);center=Vector(o['eyeCenter'])
        for kind,factor in [('eyeBlink',-.999),('eyeSquint',-.35),('eyeWide',.13)]:
            key=o.shape_key_add(name=kind+label,from_mix=False)
            for v,b in zip(key.data,base.data):
                p=b.co.copy();p.z+=(p.z-center.y)*factor;p.y=source.depth((p.x,p.z),poly)+.026 if kind=='eyeBlink' else b.co.y;v.co=p
        for kind,amount in [('In',-.01 if side=='L' else .01),('Out',.01 if side=='L' else -.01),('Up',.007),('Down',-.007)]:
            key=o.shape_key_add(name='eyeLook'+kind+label,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((amount,0,0) if kind in {'In','Out'} else (0,0,amount))
    bpy.data.objects.remove(obj('Mouth interior'),do_unlink=True)
    oral()


def bind_head(o):
    rig=obj('AvatarRig');o.vertex_groups.new(name='Head').add(list(range(len(o.data.vertices))),1,'REPLACE');o.parent=rig;m=o.modifiers.new('Head deformation','ARMATURE');m.object=rig


def oral():
    source,n,levels,width,opening,drop=face_config();center=source.MOUTH;face_y=source.depth(center);materials={n:bpy.data.materials[m] for n,m in bpy.context.scene['completionMaterials'].items()}
    rings=[]
    for row in range(13):
        t=row/12;ring=[]
        for j in range(n):
            p=mouth_point(j);phi=j*math.tau/n;rear=Vector((center.x+(width+.045)*math.cos(phi),face_y+.26,center.y-.03+(opening+.04)*math.sin(phi)));v=p.lerp(rear,t);v.y+=.004*(1-t);ring.append(v)
        rings.append(ring)
    cavity=closed_rings(prefix()+' Oral Cavity',rings,materials['Oral interior']);bm=bmesh.new();bm.from_mesh(cavity.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[13*n]],context='VERTS');bm.to_mesh(cavity.data);bm.free();bind_head(cavity);base=cavity.shape_key_add(name='Basis',from_mix=False)
    for name in CHANNELS:
        if not name.startswith(('jaw','mouth')):continue
        key=cavity.shape_key_add(name=name,from_mix=False);deltas=[mouth_motion(j,name) for j in range(n)]
        for i,(v,b) in enumerate(zip(key.data,base.data)):v.co=b.co+deltas[i%n]*(1-smooth(.1,.8,min(1,i//n/12)))
    count=6 if prefix()=='Orbit' else 8;spacing=width*1.55/count;radius=spacing*.43
    for row,zc in [('Upper',center.y+.035),('Lower',center.y-.022)]:
        material=materials['Teeth'].copy();material.name=prefix()+row+'Teeth'
        parts=[ellipsoid(prefix()+row+' Tooth '+str(i),(center.x+(i-(count-1)/2)*spacing,face_y+.065,zc),(radius,.03,.024),material,nr=10,nc=16) for i in range(count)]
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts:o.select_set(True)
        bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name=prefix()+' '+row+' Teeth';bind_head(o);base=o.shape_key_add(name='Basis',from_mix=False)
        for name,sign in [('jawOpen',1),('mouthClose',-1)]:
            key=o.shape_key_add(name=name,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((0,0,sign*(.008 if row=='Upper' else -(opening*.72))))
    nr,nc=49,24;rings=[]
    for i in range(nr):
        t=i/(nr-1);tip=math.sqrt(max(.02,1-t**8));rings.append([(center.x+min(.10,width*.40)*tip*math.cos(j*math.tau/nc),face_y+.19-.09*t,center.y-.025+.016*tip*math.sin(j*math.tau/nc)) for j in range(nc)])
    o=closed_rings(prefix()+' Long Tongue',rings,materials['Tongue']);bind_head(o);base=o.shape_key_add(name='Basis',from_mix=False)
    for name in ['tongueOut','jawOpen','mouthClose']:
        key=o.shape_key_add(name=name,from_mix=False)
        for i,(v,b) in enumerate(zip(key.data,base.data)):
            t=(i//nc)/(nr-1) if i<nr*nc else (0 if i==nr*nc else 1)
            if name=='tongueOut':v.co.y-=.98*t;v.co.z+=.09*math.sin(math.pi*t)-.30*t*t
            else:v.co.z-=(-1 if name=='mouthClose' else 1)*.025*smooth(0,.38,t)
    o['tongueRootAnchored']=True;o['additionalReach']=.98


def bake_materials():
    reset();s=bpy.context.scene;objects=meshes();materials={m.name:m for o in objects for m in o.data.materials};s.cycles.samples=8
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True);o.active_shape_key_index=0
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
    nodes={}
    for name,m in materials.items():
        m.use_fake_user=True;nodes[name]=m.node_tree.nodes.new('ShaderNodeTexImage');m.node_tree.nodes.active=nodes[name]
    images={};out=ROOT/'assets/likeness-trials';out.mkdir(parents=True,exist_ok=True)
    for label,size,kind in [('basecolor',2048,'DIFFUSE'),('normal',1024,'NORMAL')]:
        atlas=bpy.data.images.new(prefix()+' supplied '+label,width=size,height=size)
        if kind=='NORMAL':atlas.colorspace_settings.name='Non-Color'
        for node in nodes.values():node.image=atlas
        if kind=='NORMAL':bpy.ops.object.bake(type=kind,use_clear=False,margin=8,normal_space='TANGENT')
        else:bpy.ops.object.bake(type=kind,pass_filter={'COLOR'},use_clear=False,margin=8)
        atlas.filepath_raw=str(out/(prefix().lower()+'-image-'+label+'.png'));atlas.file_format='PNG';atlas.save();atlas.pack();images[label]=atlas
    replacements={}
    for name,original in materials.items():
        old=original.node_tree.nodes.get('Principled BSDF');m=plain_material(name+' - Baked PBR',(.5,.5,.5),old.inputs['Roughness'].default_value);n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF']
        for label in ['Metallic','Specular IOR Level','Coat Weight','Coat Roughness','IOR','Transmission Weight']:p.inputs[label].default_value=old.inputs[label].default_value
        color=n.new('ShaderNodeTexImage');color.image=images['basecolor'];l.new(color.outputs['Color'],p.inputs['Base Color']);tex=n.new('ShaderNodeTexImage');tex.image=images['normal'];normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal']);replacements[name]=m
    for o in objects:
        for i,m in enumerate(list(o.data.materials)):o.data.materials[i]=replacements[m.name]
    s['editableProceduralMaterials']=list(materials);s.cycles.samples=32;save()


def export_runtime():
    reset();rig=obj('AvatarRig');bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in {'MESH','ARMATURE'}:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    path=ROOT/'assets/likeness-trials'/(prefix().lower()+'-image-rig.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_morph=True,export_morph_normal=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    rig.hide_set(True);bpy.context.scene['status']='Body and facial review rig; physical ZED/Orin and user visual acceptance pending';save();print(str(path))


def neck_bridge():
    reset()
    for o in meshes():
        for i,m in enumerate(list(o.data.materials)):
            if m.name.endswith(' - Baked PBR'):o.data.materials[i]=bpy.data.materials[m.name[:-12]]
    m=obj('Head').data.materials[0]
    center=(.015,.015,1.63) if prefix()=='Orbit' else (.008,.015,.91)
    radii=(.235,.225,.18) if prefix()=='Orbit' else (.205,.19,.15)
    o=ellipsoid(prefix()+' Neck Bridge',center,radii,m,nr=28,nc=48);rig=obj('AvatarRig');o.parent=rig
    groups={n:o.vertex_groups.new(name=n) for n in ['Neck','Head']}
    for v in o.data.vertices:
        t=smooth(center[2]-.08,center[2]+.08,v.co.z)
        for n,a in [('Neck',1-t),('Head',t)]:
            if a>0:groups[n].add([v.index],a,'REPLACE')
    mod=o.modifiers.new('Neck deformation','ARMATURE');mod.object=rig


def retopologize_coral():
    import build_supplied_coral as source
    h=obj('Head');bpy.ops.object.select_all(action='DESELECT');h.select_set(True);bpy.context.view_layer.objects.active=h
    mod=h.modifiers.new('Retain sculpt silhouette at animation density','DECIMATE');mod.ratio=.16;bpy.ops.object.modifier_apply(modifier=mod.name)
    old=h.data;points=[v.co.copy() for v in old.vertices];center=source.MOUTH
    keep=[];materials=[]
    for f in old.polygons:
        near=any(points[i].y<-.04 and ((points[i].x-center.x)/.49)**2+((points[i].z-center.y)/.205)**2<1 for i in f.vertices)
        if not near:keep.append(tuple(f.vertices));materials.append(f.material_index)
    used=sorted({i for f in keep for i in f});mapping={j:i for i,j in enumerate(used)};vs=[points[j] for j in used];fs=[tuple(mapping[j] for j in f) for f in keep];edges={}
    for f in fs:
        for a,b in zip(f,f[1:]+f[:1]):e=tuple(sorted((a,b)));edges[e]=edges.get(e,0)+1
    neighbors={}
    for (a,b),count in edges.items():
        if count==1:neighbors.setdefault(a,[]).append(b);neighbors.setdefault(b,[]).append(a)
    assert neighbors and all(len(v)==2 for v in neighbors.values()),'Mouth cut must leave closed boundary loops'
    first=min(neighbors,key=lambda i:vs[i].x);ordered=[first,neighbors[first][0]]
    while len(ordered)<len(neighbors):
        nxt=next(i for i in neighbors[ordered[-1]] if i!=ordered[-2]);assert nxt!=first,'Unexpected disconnected mouth cut';ordered.append(nxt)
    if sum(vs[a].x*vs[b].z-vs[b].x*vs[a].z for a,b in zip(ordered,ordered[1:]+ordered[:1]))<0:ordered.reverse()
    n=160;outer=[Vector((vs[i].x,vs[i].z)) for i in ordered];ring=[center+Vector((.465*math.cos(j*math.tau/n),.19*math.sin(j*math.tau/n))) for j in range(n)]
    coords=outer+ring;nc=len(outer);constraints=[(j,(j+1)%nc) for j in range(nc)]+[(nc+j,nc+(j+1)%n) for j in range(n)]
    dv,de,df,ov,oe,of=delaunay_2d_cdt(coords,constraints,[],0,1e-7);orig={j:i for i,ids in enumerate(ov) for j in ids};new={orig[j]:ordered[j] for j in range(nc)}
    for i,p in enumerate(dv):
        if i not in new:new[i]=len(vs);vs.append(Vector((p.x,source.depth(p),p.y)))
    for f in df:
        c=sum((dv[i] for i in f),Vector((0,0)))/len(f)
        if inside(c,outer) and not inside(c,ring):fs.append(tuple(new[i] for i in f));materials.append(0)
    previous=[new[orig[nc+j]] for j in range(n)];start=len(vs)
    for row in range(1,17):
        t=row/16;current=[]
        for j,a in enumerate(ring):
            phi=j*math.tau/n;sn=math.sin(phi);inner=center+Vector((.365*math.cos(phi),.022*sn-.012*math.cos(phi*2)))
            p=a.lerp(inner,t);current.append(len(vs));vs.append(Vector((p.x,source.depth(p)-.038*math.sin(t*math.pi/1.35),p.y)))
        for j in range(n):fs.append((previous[j],previous[(j+1)%n],current[(j+1)%n],current[j]));materials.append(1 if t>.40 else 0)
        previous=current
    data=bpy.data.meshes.new('Coral animation mouth and reduced sculpt');data.from_pydata(vs,[],fs);data.update()
    for m in old.materials:data.materials.append(m)
    for f,mi in zip(data.polygons,materials):f.material_index=mi;f.use_smooth=True
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();h.data=data;h['patches']={'mouth':{'start':start,'size':n}}
    h['topologyStatus']='Sculpt silhouette preserved; 16 uniform 160-column mouth rings and constrained outer transition'
    print({'head_vertices':len(vs),'mouth_columns':n,'boundary_vertices':len(ordered)})


def lid_geometry(side,angle):
    import build_supplied_coral as source
    c=source.point(406 if side=='R' else 588,383,-.315);rx,ry,rz=.207,.235,.218;nr,nc=20,72;vs=[];fs=[]
    for sign in [1,-1]:
        offset=len(vs)
        for i in range(nr):
            theta=.005+(angle-.005)*i/(nr-1)
            for j in range(nc):
                phi=j*math.tau/nc;vs.append((c.x+rx*math.sin(theta)*math.cos(phi),c.y+ry*math.sin(theta)*math.sin(phi),c.z+sign*rz*math.cos(theta)))
        for i in range(nr-1):
            for j in range(nc):a=offset+i*nc+j;b=offset+i*nc+(j+1)%nc;fs.append((a,b,b+nc,a+nc))
        top=len(vs);vs.append((c.x,c.y,c.z+sign*rz));bottom=len(vs);vs.append((c.x,c.y,c.z+sign*rz*math.cos(angle)))
        for j in range(nc):fs.append((top,offset+(j+1)%nc,offset+j));fs.append((bottom,offset+(nr-1)*nc+j,offset+(nr-1)*nc+(j+1)%nc))
    return vs,fs


def facial_coral():
    source,n,levels,width,opening,drop=face_config();h=obj('Head');base=h.shape_key_add(name='Basis',from_mix=False);patch=h['patches']['mouth'];poly=source.contour()
    for name in CHANNELS:
        if name=='tongueOut':continue
        key=h.shape_key_add(name=name,from_mix=False)
        if name.startswith(('jaw','mouth')):
            deltas=[mouth_motion(j,name) for j in range(n)]
            for row,t in enumerate(levels):
                for j in range(n):
                    i=patch['start']+row*n+j;b=base.data[i].co;p=b+deltas[j]*t;p.y=source.depth((p.x,p.z),poly)+b.y-source.depth((b.x,b.z),poly)
                    if name not in {'jawOpen','mouthClose'}:p.y+=deltas[j].y*t
                    key.data[i].co=p
        else:
            c=source.point(588 if name.endswith('Left') else 406,383,-.315)
            for v,b in zip(key.data,base.data):
                x,y,z=b.co;front=smooth(.01,-.25,y);near=math.exp(-((x-c.x)/.23)**4)
                if name.startswith('brow'):v.co.z+=(.020 if 'Up' in name else -.015)*front*near*math.exp(-((z-c.z-.24)/.13)**4)
                elif name.startswith('cheekSquint'):v.co.z+=.014*front*near*math.exp(-((z-c.z+.22)/.14)**4)
                elif name=='cheekPuff':v.co.y-=.023*front*math.exp(-((z-source.MOUTH.y-.21)/.19)**4)
                elif name.startswith('noseSneer'):v.co.z+=.013*front*near*math.exp(-((z-source.MOUTH.y-.31)/.14)**4)
    for side,label in [('L','Left'),('R','Right')]:
        vs,fs=lid_geometry(side,.57);o=mesh('Coral Eyelids '+side,vs,fs,source.mat('Skin'));bind_head(o);o.shape_key_add(name='Basis',from_mix=False)
        for name,angle in [('eyeBlink',math.pi/2+.002),('eyeSquint',.91),('eyeWide',.40)]:
            key=o.shape_key_add(name=name+label,from_mix=False);coords,_=lid_geometry(side,angle)
            for v,p in zip(key.data,coords):v.co=p
        eye=obj('Eye '+side);eye.shape_key_add(name='Basis',from_mix=False);pupil=obj('Pupil '+side);base=pupil.shape_key_add(name='Basis',from_mix=False)
        c=source.point(406 if side=='R' else 588,383,-.315)
        for kind,amount in [('In',-.040 if side=='L' else .040),('Out',.040 if side=='L' else -.040),('Up',.035),('Down',-.035)]:
            key=pupil.shape_key_add(name='eyeLook'+kind+label,from_mix=False)
            for v,b in zip(key.data,base.data):
                p=b.co+Vector((amount,0,0) if kind in {'In','Out'} else (0,0,amount));p.y=c.y-.207*math.sqrt(max(.03,1-((p.x-c.x)/.20)**2-((p.z-c.z)/.211)**2))-.005;v.co=p
    oral()
    reset()


def refine_coral_body():
    import build_supplied_coral as source
    reset();bpy.ops.wm.save_as_mainfile(filepath=str(qa()/'before-flipper-refinement.blend'),copy=True)
    oldrig=obj('AvatarRig')
    for o in meshes():
        o.parent=None;o.vertex_groups.clear()
        for m in list(o.modifiers):
            if m.type=='ARMATURE':o.modifiers.remove(m)
    bpy.data.objects.remove(oldrig,do_unlink=True);bpy.data.objects.remove(obj('Body'),do_unlink=True)
    rings=[]
    for i in range(64):
        py=590+160*i/63;p=source.point(514,py,.035);rx=profile([(590,.20),(620,.23),(680,.265),(735,.285),(750,.275)],py)
        rings.append([(p.x+rx*math.cos(j*math.tau/64),p.y+.20*math.sin(j*math.tau/64),p.z) for j in range(64)])
    parts=[closed_rings('Coral Torso revised',rings,source.mat('Body'))];arms={}
    for side,pixels in [('R',[(452,594),(424,655),(406,704),(403,741)]),('L',[(570,590),(597,648),(619,703),(623,736)])]:
        ps=[source.point(x,z,y) for (x,z),y in zip(pixels,[.045,-.10,-.13,-.13])];arms[side]=[list(v) for v in ps];m=source.mat('Body') if side=='R' else source.mat('Skin')
        parts.append(tube('Coral Flipper revised '+side,ps,[.105,.098,.089,.073],m,rings=72,sides=40));parts.append(ellipsoid('Coral Flipper end revised '+side,ps[-1],(.074,.073,.104),m))
    for side,x in [('R',474),('L',553)]:
        rings=[]
        for i in range(40):
            t=i/39;p=source.point(x,723+90*t,.035);rx=.112 if t<.95 else .108;rings.append([(p.x+rx*math.cos(j*math.tau/48),p.y+.145*math.sin(j*math.tau/48),p.z) for j in range(48)])
        parts.append(closed_rings('Coral Leg revised '+side,rings,source.mat('Body')))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='Coral Body'
    mod=o.modifiers.new('Shoulder-only flipper attachments','REMESH');mod.mode='VOXEL';mod.voxel_size=.008;mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=o.modifiers.new('Blend flipper roots','SMOOTH');mod.factor=.6;mod.iterations=4;bpy.ops.object.modifier_apply(modifier=mod.name)
    skin=next(i for i,m in enumerate(o.data.materials) if m==source.mat('Skin'))
    for p in o.data.polygons:
        if p.center.x>.30:p.material_index=skin
    bpy.context.scene['rigArms']=arms;skeleton()
    bridge=obj('Neck Bridge');bridge.vertex_groups.clear();groups={n:bridge.vertex_groups.new(name=n) for n in ['Neck','Head']}
    for v in bridge.data.vertices:
        t=smooth(.83,.99,v.co.z)
        for n,a in [('Neck',1-t),('Head',t)]:
            if a>0:groups[n].add([v.index],a,'REPLACE')
    for side,label in [('L','Left'),('R','Right')]:
        eye=obj('Eyelids '+side)
        for name,angle in [('Basis',.57),('eyeBlink'+label,math.pi/2+.002),('eyeSquint'+label,.91),('eyeWide'+label,.40)]:
            coords,_=lid_geometry(side,angle)
            for v,p in zip(eye.data.shape_keys.key_blocks[name].data,coords):v.co=p
    for row,delta in [('Upper',.031),('Lower',-.030)]:
        for key in obj(row+' Teeth').data.shape_keys.key_blocks:
            for v in key.data:v.co.z+=delta
    reset();save()


def polish_coral():
    import build_supplied_coral as source
    reset()
    for row in ['Upper','Lower']:
        for key in obj(row+' Teeth').data.shape_keys.key_blocks:
            for v in key.data:v.co.y+=.085;v.co.z+=.012 if row=='Lower' else 0
    m=source.mat('Skin');n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];previous=p.inputs['Normal'].links[0].from_socket
    tex=n.new('ShaderNodeTexCoord');wave=n.new('ShaderNodeTexWave');wave.bands_direction='Z';wave.inputs['Scale'].default_value=6.5;wave.inputs['Distortion'].default_value=5;wave.inputs['Detail'].default_value=3;l.new(tex.outputs['Object'],wave.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.012;l.new(wave.outputs['Color'],bump.inputs['Height']);l.new(previous,bump.inputs['Normal']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
    p.inputs['Roughness'].default_value=.46;p.inputs['Specular IOR Level'].default_value=.3;p.inputs['Coat Weight'].default_value=.17
    p=source.mat('Eye').node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.90,.75,.48,1);p.inputs['Roughness'].default_value=.19;p.inputs['Coat Weight'].default_value=.6;p.inputs['Coat Roughness'].default_value=.065
    save()
