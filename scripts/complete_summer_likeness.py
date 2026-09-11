"""Summer's own reference-contour build, staged in the live Blender MCP scene."""
import bpy
import bmesh
import math
import json
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.geometry import delaunay_2d_cdt
from complete_cosmic_likeness import tube,ellipsoid,loop,inside
from complete_clay_likeness import mesh,closed_rings,plain_material,profile,smooth
from build_avatar_fleet import CHANNELS

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'.context/attachments/tHW4Gg/lailasherself_cosmic_alien_creature_themed_on_Southern_summer_8abcf53c-0a7f-4167-805e-c3baa8dbb743_2.png'
QA=ROOT/'.context/qa/summer-complete'
OUT=ROOT/'blender/likeness-trials/summer-body-rig.blend'
GLB=ROOT/'assets/likeness-trials/summer-body-rig.glb'
OUTLINE=[(320,465),(370,457),(442,455),(511,461),(560,477),(615,506),(657,547),(681,603),(696,655),(698,701),(684,747),(652,780),(603,800),(545,814),(476,821),(407,820),(340,811),(282,791),(237,766),(210,732),(195,685),(195,630),(209,577),(239,532),(278,494)]
EYES={'R':[(398,651),(410,650),(427,657),(450,674),(462,690),(451,704),(429,715),(407,721),(390,718),(377,708),(374,690),(380,669)],
      'L':[(674,642),(680,649),(685,668),(686,686),(680,704),(671,711),(659,707),(650,698),(648,684),(657,662)]}
MOUTH=Vector(((552-440)/280,(1212-741)/280))
ARMS={'R':[(-.35,.02,1.225),(-.625,0,.886),(-.710,-.03,.679),(-.710,-.055,.607)],
      'L':[(.30,.025,1.20),(.475,.01,.918),(.579,-.03,.700),(.570,-.055,.630)]}


def obj(name):return bpy.context.scene.objects[name]
def mat(name):return bpy.data.materials[bpy.context.scene['material_names'][name]]
def point(px,py,y=0):return Vector(((px-440)/280,y,(1212-py)/280))
def contour():return [Vector((p.x,p.z)) for p in [point(*v) for v in loop(OUTLINE)]]


def depth(p,outline=None):
    outline=outline or contour();cx,cz=0,2.04;dx,dz=p[0]-cx,p[1]-cz;hits=[]
    if abs(dx)+abs(dz)<1e-8:return -.48
    for a,b in zip(outline,outline[1:]+outline[:1]):
        ex,ez=b.x-a.x,b.y-a.y;det=dx*ez-dz*ex
        if abs(det)<1e-10:continue
        ax,az=a.x-cx,a.y-cz;t=(ax*ez-az*ex)/det;u=(ax*dz-az*dx)/det
        if t>0 and -1e-6<=u<=1.000001:hits.append(t)
    r=1/min(hits) if hits else 1
    return -.48*math.sqrt(max(0,1-r*r))


def scene():
    QA.mkdir(parents=True,exist_ok=True);s=bpy.data.scenes.new('Summer - Reference Contour Character');bpy.context.window.scene=s
    s['status']='Isolated reference build in progress, not installation approved.';s['source_reference']=str(REF)
    materials={name:plain_material('Summer '+name,color,rough) for name,color,rough in [('Skin',(.004,.006,.018),.52),('Eye',(.014,.009,.030),.31),('Glow',(1,.42,.065),.35),('Oral interior',(.001,.0003,.001),.95),('Teeth',(.70,.62,.44),.35),('Tongue',(.42,.06,.065),.46)]}
    s['material_names']={n:m.name for n,m in materials.items()}
    p=mat('Glow').node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(1,.40,.12,1);p.inputs['Emission Color'].default_value=(1,.40,.05,1);p.inputs['Emission Strength'].default_value=.25
    p=mat('Eye').node_tree.nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.65;p.inputs['Specular IOR Level'].default_value=.1
    ref=bpy.data.objects.new('Summer reference - comparison only',None);s.collection.objects.link(ref);ref.empty_display_type='IMAGE';ref.data=bpy.data.images.load(str(REF),check_existing=True);ref.data.pack();ref.empty_display_size=1344/280;ref.location=(-2.8,.8,(1212-672)/280);ref.rotation_euler=(math.pi/2,0,0);ref.hide_render=True
    world=bpy.data.worlds.new('Summer review world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.16,.16,1);world.node_tree.nodes['Background'].inputs[1].default_value=.40;s.world=world
    for name,loc,power,size in [('Key',(-3,-4,6),420,4),('Fill',(3,-3,3),170,3),('Rim',(1,3,5),260,3)]:
        d=bpy.data.lights.new('Summer '+name,'AREA');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.7))-o.location).to_track_quat('-Z','Y').to_euler();d.energy=power;d.size=size
    d=bpy.data.cameras.new('Summer Camera');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);s.camera=o;d.type='ORTHO';d.ortho_scale=3.65
    s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1100;s.render.resolution_y=1400;s.render.resolution_percentage=100;s.view_settings.view_transform='Standard';view()


def head():
    outline=contour();count=len(outline);front=[Vector((p.x*.975,2.04+(p.y-2.04)*.975)) for p in outline]
    apertures={side:[Vector((p.x,p.z)) for p in [point(*v) for v in loop(points,6)]] for side,points in EYES.items()}
    centers={side:sum(points,Vector((0,0)))/len(points) for side,points in apertures.items()}
    holes={side:[centers[side]+(p-centers[side])*1.22 for p in points] for side,points in apertures.items()}
    holes['mouth']=[MOUTH+Vector((.30*math.cos(j*math.tau/120),.185*math.sin(j*math.tau/120))) for j in range(120)]
    coords=list(front);constraints=[(i,(i+1)%count) for i in range(count)];indexes={}
    for name,points in holes.items():
        start=len(coords);coords+=points;indexes[name]=list(range(start,len(coords)));constraints.extend((start+j,start+(j+1)%len(points)) for j in range(len(points)))
    for r in [.95,.91,.85,.78,.69,.60,.50,.39,.28,.17,.07]:
        for p in outline:
            q=Vector((p.x*r,2.04+(p.y-2.04)*r))
            if not any(inside(q,h) for h in holes.values()):coords.append(q)
    dv,de,df,ov,oe,of=delaunay_2d_cdt(coords,constraints,[],0,1e-7);mapping={j:i for i,ids in enumerate(ov) for j in ids}
    vs=[Vector((p.x,depth(p,outline),p.y)) for p in dv];fs=[]
    for f in df:
        center=sum((dv[i] for i in f),Vector((0,0)))/len(f)
        if inside(center,front) and not any(inside(center,h) for h in holes.values()):fs.append(tuple(f))
    previous=[mapping[i] for i in range(count)]
    for r,back in [(r,False) for r in [.986,.996,1]]+[(r,True) for r in [.996,.986,.965,.93,.88,.80,.71,.60,.48,.35,.21,.08]]:
        current=[]
        for p in outline:
            q=Vector((p.x*r,2.04+(p.y-2.04)*r));current.append(len(vs));vs.append(Vector((q.x,.38*math.sqrt(1-r*r) if back else depth(q,outline),q.y)))
        for j in range(count):fs.append((previous[j],previous[(j+1)%count],current[(j+1)%count],current[j]))
        previous=current
    ci=len(vs);vs.append(Vector((0,.38,2.04)));fs.extend((previous[j],previous[(j+1)%count],ci) for j in range(count))
    patches={};levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1]
    for name,outer in holes.items():
        n=len(outer);previous=[mapping[i] for i in indexes[name]];start=len(vs)
        for t in levels:
            current=[]
            for j,a in enumerate(outer):
                if name=='mouth':
                    phi=j*math.tau/n;sn=math.sin(phi);inner=MOUTH+Vector((.17*math.cos(phi),.025*sn*sn+(.006 if sn>=0 else .005)*sn))
                else:inner=apertures[name][j]
                p=a.lerp(inner,t);current.append(len(vs));vs.append(Vector((p.x,depth(p,outline)+(.008*t*t if name!='mouth' else 0),p.y)))
            for j in range(n):fs.append((previous[j],previous[(j+1)%n],current[(j+1)%n],current[j]))
            previous=current
        patches[name]={'start':start,'size':n}
    h=mesh('Summer Head',vs,fs,mat('Skin'));h['patches']=patches;h['armCollisionSurface']=True
    for side,points in apertures.items():
        center=centers[side];rings=[];n=len(points)
        for i in range(17):
            r=1.01*(1-i/17)
            rings.append([(p.x,depth(p,outline)+.014-.029*(1-r*r),p.y) for p in [center+(v-center)*r for v in points]])
        eye=closed_rings('Summer Eye '+side,rings,mat('Eye'))
        bm=bmesh.new();bm.from_mesh(eye.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[17*n]],context='VERTS');bm.to_mesh(eye.data);bm.free()
        eye['eyeCenter']=list(center);eye.data.materials.append(mat('Glow'))
        cut=(418-440)/280 if side=='R' else (670-440)/280
        bm=bmesh.new();bm.from_mesh(eye.data)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(cut,0,0),plane_no=(1,0,0),clear_inner=False,clear_outer=False)
        bm.to_mesh(eye.data);bm.free()
        for poly in eye.data.polygons:
            x=sum(eye.data.vertices[i].co.x for i in poly.vertices)/len(poly.vertices)
            if (side=='R' and x<(418-440)/280) or (side=='L' and x>(670-440)/280):poly.material_index=1
    print({'head_vertices':len(vs),'eye_apertures':len(apertures),'uniform_mouth_columns':120})


def projections():
    specs=[('Upper R',[(302,492),(284,447),(263,402),(251,375)],[.135,.145,.205,.17],(.23,.19,.25)),
           ('Upper L',[(562,498),(587,449),(612,404),(625,379)],[.14,.15,.20,.16],(.225,.18,.25)),
           ('Middle R',[(239,587),(203,578),(169,556),(151,548)],[.13,.15,.16,.10],(.205,.16,.18)),
           ('Middle L',[(643,579),(681,569),(711,545),(718,530)],[.13,.14,.15,.10],(.17,.16,.18)),
           ('Lower R',[(224,703),(192,703),(168,697)],[.13,.13,.095],(.15,.13,.145)),
           ('Lower L',[(670,703),(702,697),(717,685)],[.12,.13,.085],(.145,.13,.135))]
    for name,pixels,radii,size in specs:
        points=[point(x,z,.035) for x,z in pixels];a=tube('Summer '+name+' Stem',points,radii,mat('Skin'),rings=40,sides=32);b=ellipsoid('Summer '+name+' Tip',points[-1],size,mat('Skin'),nr=24,nc=40)
        bpy.ops.object.select_all(action='DESELECT');a.select_set(True);b.select_set(True);bpy.context.view_layer.objects.active=a;bpy.ops.object.join()
        mod=a.modifiers.new('Continuous rounded projection','REMESH');mod.mode='VOXEL';mod.voxel_size=.011;mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=a.modifiers.new('Soft projection transition','SMOOTH');mod.factor=1;mod.iterations=4;bpy.ops.object.modifier_apply(modifier=mod.name)


def body():
    rings=[]
    for i in range(64):
        z=.30+1.17*i/63;r=profile([(.30,.32),(.43,.39),(.64,.35),(.85,.295),(1.10,.25),(1.32,.255),(1.47,.24)],z)
        rings.append([(-.04+r*math.cos(j*math.tau/64),.02+r*.77*math.sin(j*math.tau/64),z) for j in range(64)])
    closed_rings('Summer Torso',rings,mat('Skin'))
    digit_paths={}
    for side,p in ARMS.items():
        tube('Summer Arm '+side,[(p[0][0]*.35,.02,p[0][2]+.10),*p],[.10,.12,.112,.090,.090],mat('Skin'))
        ellipsoid('Summer Palm '+side,p[-1],(.10,.08,.09),mat('Skin'))
        if side=='R':digits={'Thumb':[(-.62,-.05,.65),(-.555,-.06,.61),(-.515,-.08,.59),(-.52,-.10,.565)],'Index':[(-.745,-.05,.60),(-.770,-.07,.535),(-.750,-.09,.475),(-.700,-.10,.46)]}
        else:digits={'Thumb':[(.535,-.05,.665),(.490,-.06,.61),(.475,-.08,.565),(.49,-.10,.55)],'Index':[(.625,-.05,.64),(.665,-.07,.585),(.66,-.09,.53),(.63,-.10,.52)]}
        for digit,points in digits.items():
            tube(f'Summer {digit} {side}',points,[.055,.05,.044,.012],mat('Skin'),rings=32,sides=24);digit_paths[f'{digit}.{side}']=points
        rings=[]
        for i in range(40):
            z=.015+.64*i/39;r=profile([(.015,.23),(.045,.29),(.13,.28),(.30,.215),(.50,.18),(.655,.10)],z);x=(-.37 if side=='R' else .28)+(.15 if side=='R' else -.12)*smooth(.10,.65,z)
            rings.append([(x+r*math.cos(j*math.tau/48),-.015+r*.92*math.sin(j*math.tau/48),z) for j in range(48)])
        closed_rings('Summer Leg '+side,rings,mat('Skin'))
    names=['Summer Torso']+[f'Summer {part} {side}' for side in ['L','R'] for part in ['Arm','Palm','Thumb','Index','Leg']]
    bpy.ops.object.select_all(action='DESELECT')
    for name in names:obj(name).select_set(True)
    bpy.context.view_layer.objects.active=obj('Summer Torso');bpy.ops.object.join();o=bpy.context.object;o.name='Summer Body';o['digitPaths']=digit_paths;o['armCollisionSurface']=True
    mod=o.modifiers.new('Continuous body skin','REMESH');mod.mode='VOXEL';mod.voxel_size=.012;mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=o.modifiers.new('Soft shoulder and hip transitions','SMOOTH');mod.factor=1;mod.iterations=5;bpy.ops.object.modifier_apply(modifier=mod.name)


def skin():
    m=mat('Skin');n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];p.inputs['Specular IOR Level'].default_value=.12;p.inputs['Roughness'].default_value=.72
    tex=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=5;noise.inputs['Detail'].default_value=3;l.new(tex.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.20;ramp.color_ramp.elements[0].color=(.0003,.001,.004,1);ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.007,.006,.026,1);l.new(noise.outputs['Fac'],ramp.inputs[0]);color=ramp.outputs[0]
    for scale,edge,tint in [(100,.17,(1,.68,.32,1))]:
        vor=n.new('ShaderNodeTexVoronoi');vor.inputs['Scale'].default_value=scale;l.new(tex.outputs['Object'],vor.inputs['Vector'])
        r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.012;r.color_ramp.elements[0].color=tint;r.color_ramp.elements[1].position=edge;r.color_ramp.elements[1].color=(0,0,0,1);l.new(vor.outputs['Distance'],r.inputs[0])
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='ADD';mix.inputs[0].default_value=1;l.new(color,mix.inputs[1]);l.new(r.outputs[0],mix.inputs[2]);color=mix.outputs[0]
    # Prominent warm spots are fitted as volumetric fields, not projected pixels.
    spots=[(220,368,-.16,.105),(291,442,-.13,.10),(590,374,-.16,.11),(598,439,-.14,.075),(170,576,-.13,.095),(725,520,-.12,.10),(456,510,None,.09),(264,612,None,.095),(317,623,None,.07),(516,602,None,.07),(426,754,None,.075),(482,938,-.17,.065),(277,998,-.11,.10),(408,1016,-.235,.15),(518,1051,-.17,.09),(360,1158,-.22,.14),(575,1158,-.12,.13),(167,688,-.12,.105)]
    emission=None
    for px,py,y,radius in spots:
        q=point(px,py);q.y=depth((q.x,q.z)) if y is None else y
        distance=n.new('ShaderNodeVectorMath');distance.operation='DISTANCE';l.new(tex.outputs['Object'],distance.inputs[0]);distance.inputs[1].default_value=q
        falloff=n.new('ShaderNodeMapRange');falloff.clamp=True;falloff.interpolation_type='SMOOTHERSTEP';falloff.inputs['From Min'].default_value=0;falloff.inputs['From Max'].default_value=radius;falloff.inputs['To Min'].default_value=1;falloff.inputs['To Max'].default_value=0;l.new(distance.outputs['Value'],falloff.inputs['Value'])
        tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[1].default_value=(1,.45,.12,1);l.new(falloff.outputs[0],tint.inputs[2])
        add=n.new('ShaderNodeMixRGB');add.blend_type='ADD';add.inputs[0].default_value=1;l.new(color,add.inputs[1]);l.new(tint.outputs[0],add.inputs[2]);color=add.outputs[0]
        if emission is None:emission=tint.outputs[0]
        else:
            add=n.new('ShaderNodeMixRGB');add.blend_type='ADD';add.inputs[0].default_value=1;l.new(emission,add.inputs[1]);l.new(tint.outputs[0],add.inputs[2]);emission=add.outputs[0]
    l.new(emission,p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=.45
    l.new(color,p.inputs['Base Color']);m['source']='New dark star-field with warm flecks and soft luminous spots, not a projection of the source PNG.'


def skeleton():
    data=bpy.data.armatures.new('Summer Skeleton');rig=bpy.data.objects.new('Summer AvatarRig',data);bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,a,b,parent=None):
        e=data.edit_bones.new(name);e.head=a;e.tail=b
        if parent:e.parent=data.edit_bones[parent]
        return e
    bone('Root',(0,0,0),(0,0,.15));bone('Hips',(-.04,.02,.36),(-.04,.02,.60),'Root');bone('Spine',(-.04,.02,.60),(-.04,.02,.90),'Hips');bone('Chest',(-.04,.02,.90),(-.04,.02,1.20),'Spine');bone('Neck',(-.04,.02,1.20),(0,.02,1.50),'Chest');bone('Head',(0,.02,1.50),(0,.02,2.5),'Neck')
    paths={n:[[float(x) for x in p] for p in value] for n,value in obj('Summer Body')['digitPaths'].items()}
    for side,p in ARMS.items():
        bone('UpperArm.'+side,p[0],p[1],'Chest');bone('Forearm.'+side,p[1],p[2],'UpperArm.'+side);bone('Hand.'+side,p[2],p[3],'Forearm.'+side)
        x=-.29 if side=='R' else .22
        bone('Thigh.'+side,(x,.02,.49),(x,-.01,.28),'Hips');bone('Shin.'+side,(x,-.01,.28),(x,-.04,.09),'Thigh.'+side);bone('Foot.'+side,(x,-.04,.09),(x,-.20,.04),'Shin.'+side)
        for digit in ['Thumb','Index']:
            points=paths[digit+'.'+side]
            for i in range(3):e=bone(f'{digit}{i+1}.{side}',points[i],points[i+1],f'{digit}{i}.{side}' if i else 'Hand.'+side);e.align_roll(Vector((0,-1,0)))
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig['installationApproved']=False;rig['rigVersion']='summer-reference-contour-1'
    for side in ARMS:
        data.bones['UpperArm.'+side]['armCollisionRestContact']=True
        for digit in ['Thumb','Index']:
            for i,a in enumerate([.45,.55,.40]):data.bones[f'{digit}{i+1}.{side}']['fingerCurlRadians']=a
    body=obj('Summer Body');adj=[[] for _ in body.data.vertices]
    for e in body.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
    remaining={v.index for v in body.data.vertices if v.co.z<1.0};regions={}
    while remaining:
        todo=[remaining.pop()];component=list(todo)
        while todo:
            for j in adj[todo.pop()]:
                if j in remaining:remaining.remove(j);todo.append(j);component.append(j)
        mx=sum(body.data.vertices[i].co.x for i in component)/len(component)
        for i in component:regions[i]=1 if abs(mx)>.42 else 0
    def closest(p,path):
        result=(1e9,0)
        for i,(a,b) in enumerate(zip(path,path[1:])):
            a,b=Vector(a),Vector(b);d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));distance=(p-a-d*t).length
            if distance<result[0]:result=(distance,i+t)
        return result
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH':continue
        groups={b.name:o.vertex_groups.new(name=b.name) for b in data.bones}
        for v in o.data.vertices:
            x,y,z=v.co;side='L' if x>-.04 else 'R';w={'Head':1}
            if o==body:
                if z<.9:t=smooth(.45,.85,z);w={'Hips':1-t,'Spine':t}
                else:t=smooth(.90,1.16,z);n=smooth(1.23,1.44,z);w={'Spine':(1-t)*(1-n),'Chest':t*(1-n),'Neck':n}
                leg=1-smooth(.38,.57,z)
                if leg:
                    knee=1-smooth(.20,.36,z);foot=1-smooth(.06,.17,z);lw={'Thigh.'+side:1-knee,'Shin.'+side:knee*(1-foot),'Foot.'+side:knee*foot};w={n:a*(1-leg) for n,a in w.items()};w.update({n:a*leg for n,a in lw.items()})
                arm=regions[v.index] if v.index in regions else smooth(.18,.43 if side=='L' else .50,abs(x))
                if arm:
                    p=ARMS[side];e=1-smooth(p[1][2]-.14,p[1][2]+.14,z);hand=1-smooth(p[2][2]-.06,p[2][2]+.06,z);aw={'UpperArm.'+side:1-e,'Forearm.'+side:e*(1-hand),'Hand.'+side:e*hand}
                    if abs(x)>.40 and z<.77:
                        dist,u,digit=min((*closest(v.co,paths[digit+'.'+side]),digit) for digit in ['Thumb','Index'])
                        factor=smooth(.15,.95,u)*(1-smooth(.65,.77,z));q=max(0,min(2,u-.5));i=min(1,int(q));f=q-i;aw={n:a*(1-factor) for n,a in aw.items()};aw[f'{digit}{i+1}.{side}']=(1-f)*factor;aw[f'{digit}{i+2}.{side}']=f*factor
                    w={n:a*(1-arm) for n,a in w.items()};w.update({n:a*arm for n,a in aw.items()})
            for n,a in w.items():
                if a>1e-8:groups[n].add([v.index],a,'REPLACE')
        o.parent=rig;m=o.modifiers.new('Body deformation','ARMATURE');m.object=rig
    print({'bones':len(data.bones),'reference_digits':2})


def smooth_weights(iterations=650):
    import numpy as np
    o=obj('Summer Body');count=len(o.data.vertices);groups=list(o.vertex_groups);w=np.zeros((count,len(groups)))
    for v in o.data.vertices:
        for g in v.groups:w[v.index,g.group]=g.weight
    edges=np.array([e.vertices[:] for e in o.data.edges]);a=np.r_[edges[:,0],edges[:,1]];b=np.r_[edges[:,1],edges[:,0]];degree=np.bincount(a,minlength=count)
    mask=np.array([smooth(.10,.22,abs(v.co.x+.04))*(1-smooth(.58,.70,abs(v.co.x)))*smooth(.81,.95,v.co.z)*(1-smooth(1.34,1.46,v.co.z)) for v in o.data.vertices])*.7
    for _ in range(iterations):
        mean=np.stack([np.bincount(a,weights=w[b,i],minlength=count)/np.maximum(degree,1) for i in range(len(groups))],axis=1);w+=(mean-w)*mask[:,None]
    rows=[]
    for v,row in zip(o.data.vertices,w):
        weights={groups[i].name:float(x) for i,x in enumerate(row) if x>1e-8};side='L' if v.co.x>-.04 else 'R'
        if any(weights.get(n+'.'+side,0)>1e-8 for n in ['UpperArm','Forearm','Hand']):
            torso=sum(weights.pop(n,0) for n in ['Hips','Spine','Chest','Neck','Head'])
            if torso:weights['Chest']=torso
        if v.co.z<.77 and any(weights.get(f'{digit}{i}.{side}',0)>1e-8 for digit in ['Thumb','Index'] for i in [1,2,3]):weights['Forearm.'+side]=weights.get('Forearm.'+side,0)+weights.pop('UpperArm.'+side,0)
        pairs=sorted(weights.items(),key=lambda p:-p[1])[:4];total=sum(x for _,x in pairs);rows.append([(n,x/total) for n,x in pairs])
    for g in groups:g.remove(list(range(count)))
    for i,row in enumerate(rows):
        for n,value in row:o.vertex_groups[n].add([i],value,'REPLACE')


def mouth_point(j):
    phi=j*math.tau/120;sn=math.sin(phi);p=MOUTH+Vector((.17*math.cos(phi),.025*sn*sn+(.006 if sn>=0 else .005)*sn));return Vector((p.x,depth(p),p.y))


def mouth_motion(j,name):
    phi=j*math.tau/120;q=math.cos(phi);sn=math.sin(phi);p=mouth_point(j);v=p.copy();side=1 if name.endswith('Left') else -1;mask=smooth(-.25,.55,q*side);top=max(0,sn);bottom=max(0,-sn)
    if name in {'jawOpen','mouthClose'}:
        target=Vector((MOUTH.x+.18*q,0,MOUTH.y-.032+.077*sn));target.y=depth((target.x,target.z));return (target-p)*(1 if name=='jawOpen' else -1)
    if name in {'jawLeft','jawRight','mouthLeft','mouthRight'}:v.x+=side*.016
    elif name=='jawForward':v.y-=.012
    elif name.startswith('mouthSmile'):v.z+=.018*mask*abs(q);v.x+=side*.006*mask
    elif name.startswith('mouthFrown'):v.z-=.012*mask*abs(q)
    elif name.startswith('mouthDimple'):v.x+=side*.008*mask;v.y+=.006*mask
    elif name.startswith('mouthStretch'):v.x+=side*.015*mask
    elif name in {'mouthPucker','mouthFunnel'}:v.x=MOUTH.x+(v.x-MOUTH.x)*(.83 if name=='mouthPucker' else .9);v.z+=.018*sn;v.y-=.015
    elif name=='mouthRollUpper':v.z-=.002*top;v.y+=.006*top
    elif name=='mouthRollLower':v.z+=.002*bottom;v.y+=.006*bottom
    elif name=='mouthShrugUpper':v.z+=.018*top
    elif name=='mouthShrugLower':v.z+=.009*bottom
    elif name.startswith('mouthPress'):v.z-=.0015*sn*mask
    elif name.startswith('mouthUpperUp'):v.z+=.018*top*mask
    elif name.startswith('mouthLowerDown'):v.z-=.020*bottom*mask
    return v-p


def facial():
    h=obj('Summer Head');base=h.shape_key_add(name='Basis');patches=h['patches'];levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1];outline=contour()
    for name in CHANNELS:
        if name=='tongueOut':continue
        key=h.shape_key_add(name=name,from_mix=False)
        for v,b in zip(key.data,base.data):v.co=b.co
        if name.startswith(('mouth','jaw')):
            deltas=[mouth_motion(j,name) for j in range(120)];start=patches['mouth']['start']
            for row,t in enumerate(levels):
                for j in range(120):
                    i=start+row*120+j;p=base.data[i].co+deltas[j]*t;p.y=depth((p.x,p.z),outline)+(0 if name in {'jawOpen','mouthClose'} else deltas[j].y)*t;key.data[i].co=p
        elif name.startswith(('eyeBlink','eyeWide','eyeSquint')):
            side='L' if name.endswith('Left') else 'R';patch=patches[side];center=Vector(obj('Summer Eye '+side)['eyeCenter']);factor=-.999 if 'Blink' in name else -.38 if 'Squint' in name else .12
            for row,t in enumerate(levels):
                for j in range(patch['size']):
                    i=patch['start']+row*patch['size']+j;p=base.data[i].co.copy();p.z+=(p.z-center.y)*factor*t;p.y=depth((p.x,p.z),outline)+.008*t*t;key.data[i].co=p
        else:
            side='L' if name.endswith('Left') else 'R';center=Vector(obj('Summer Eye '+side)['eyeCenter'])
            for v,b in zip(key.data,base.data):
                x,y,z=b.co;front=smooth(0,-.3,y);near=math.exp(-((x-center.x)/.20)**4)
                if name.startswith('brow'):v.co.z+=(.02 if 'Up' in name else -.016)*front*near*math.exp(-((z-center.y-.18)/.14)**4)
                elif name.startswith('cheekSquint'):v.co.z+=.01*front*near*math.exp(-((z-center.y+.16)/.13)**4)
                elif name=='cheekPuff':v.co.y-=.018*front*math.exp(-((z-1.66)/.15)**4)
                elif name.startswith('noseSneer'):v.co.z+=.01*front*near*math.exp(-((z-1.86)/.14)**4)
    for side,label in [('L','Left'),('R','Right')]:
        o=obj('Summer Eye '+side);base=o.shape_key_add(name='Basis');center=Vector(o['eyeCenter'])
        for kind,factor in [('eyeBlink',-.999),('eyeSquint',-.38),('eyeWide',.12)]:
            key=o.shape_key_add(name=kind+label,from_mix=False)
            for v,b in zip(key.data,base.data):
                p=b.co.copy();p.z+=(p.z-center.y)*factor;p.y=depth((p.x,p.z),outline)+.020 if kind=='eyeBlink' else b.co.y;v.co=p
        for kind,amount in [('In',-.006 if side=='L' else .006),('Out',.006 if side=='L' else -.006),('Up',.005),('Down',-.005)]:
            key=o.shape_key_add(name='eyeLook'+kind+label,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((amount,0,0) if kind in {'In','Out'} else (0,0,amount))
    oral()


def bind_head(o):
    rig=obj('Summer AvatarRig');g=o.vertex_groups.new(name='Head');g.add(list(range(len(o.data.vertices))),1,'REPLACE');o.parent=rig;m=o.modifiers.new('Head deformation','ARMATURE');m.object=rig


def oral():
    n=120;inner=[mouth_point(j) for j in range(n)];rings=[]
    for row in range(13):
        t=row/12;ring=[]
        for j,p in enumerate(inner):
            phi=j*math.tau/n;rear=Vector((MOUTH.x+.23*math.cos(phi),p.y+.244,MOUTH.y-.04+.14*math.sin(phi)));v=p.lerp(rear,t);v.y+=.004*(1-t);ring.append(v)
        rings.append(ring)
    cavity=closed_rings('Summer Oral Cavity',rings,mat('Oral interior'));bm=bmesh.new();bm.from_mesh(cavity.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[13*n]],context='VERTS');bm.to_mesh(cavity.data);bm.free();bind_head(cavity);base=cavity.shape_key_add(name='Basis')
    for name in CHANNELS:
        if not name.startswith(('jaw','mouth')):continue
        key=cavity.shape_key_add(name=name,from_mix=False);deltas=[mouth_motion(j,name) for j in range(n)]
        for i,(v,b) in enumerate(zip(key.data,base.data)):v.co=b.co+deltas[i%n]*(1-smooth(.1,.8,min(1,i//n/12)))
    for row,zc in [('Upper',MOUTH.y+.057),('Lower',MOUTH.y-.030)]:
        parts=[ellipsoid(f'Summer {row} Tooth {i}',(MOUTH.x+(i-2.5)*.040,-.19,zc),(.018,.025,.024),mat('Teeth'),nr=8,nc=16) for i in range(6)]
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts:o.select_set(True)
        bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='Summer '+row+' Teeth';bind_head(o);base=o.shape_key_add(name='Basis')
        for name,sign in [('jawOpen',1),('mouthClose',-1)]:
            key=o.shape_key_add(name=name,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((0,0,sign*(-.003 if row=='Upper' else -.055)))
    nr,nc=49,24;rings=[]
    for i in range(nr):
        t=i/(nr-1);tip=math.sqrt(max(.02,1-t**8));rings.append([(MOUTH.x+.065*tip*math.cos(j*math.tau/nc),-.12-.09*t,MOUTH.y-.028+.016*tip*math.sin(j*math.tau/nc)) for j in range(nc)])
    o=closed_rings('Summer Long Tongue',rings,mat('Tongue'));bind_head(o);base=o.shape_key_add(name='Basis')
    for name in ['tongueOut','jawOpen','mouthClose']:
        key=o.shape_key_add(name=name,from_mix=False)
        for i,(v,b) in enumerate(zip(key.data,base.data)):
            t=(i//nc)/(nr-1) if i<nr*nc else (0 if i==nr*nc else 1);v.co=b.co
            if name=='tongueOut':v.co.y-=.90*t;v.co.z+=.10*math.sin(math.pi*t)-.34*t*t
            else:v.co.z-=(-1 if name=='mouthClose' else 1)*.028*smooth(0,.38,t)
    o['tongueRootAnchored']=True;o['additionalReach']=.90


def reset():
    for o in bpy.context.scene.objects:
        if o.type=='ARMATURE':
            for p in o.pose.bones:p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion();p.location=(0,0,0);p.scale=(1,1,1)
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=0
    bpy.context.view_layer.update()


def expression(values):
    for o in bpy.context.scene.objects:
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=values.get(k.name,0)
    bpy.context.view_layer.update()


def rotate(name,axis,angle):
    p=obj('Summer AvatarRig').pose.bones[name];p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion(Vector(axis),angle);bpy.context.view_layer.update()


def bake_material():
    reset();s=bpy.context.scene;s.cycles.samples=8;skin=mat('Skin');skin.use_fake_user=True
    objects=[o for o in s.objects if o.type=='MESH' and skin in list(o.data.materials)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
    node=skin.node_tree.nodes.new('ShaderNodeTexImage');skin.node_tree.nodes.active=node;images={}
    for name,size,kind in [('basecolor',2048,'DIFFUSE'),('normal',1024,'NORMAL'),('emission',1024,'EMIT')]:
        atlas=bpy.data.images.new('Summer starfield '+name,width=size,height=size);node.image=atlas
        if kind=='NORMAL':atlas.colorspace_settings.name='Non-Color';bpy.ops.object.bake(type=kind,use_clear=False,margin=8,normal_space='TANGENT')
        elif kind=='DIFFUSE':bpy.ops.object.bake(type=kind,pass_filter={'COLOR'},use_clear=False,margin=8)
        else:bpy.ops.object.bake(type=kind,use_clear=False,margin=8)
        atlas.filepath_raw=str(GLB.parent/f'summer-starfield-{name}.png');atlas.file_format='PNG';atlas.save();atlas.pack();images[name]=atlas
    baked=plain_material('Summer Starfield - Runtime PBR',(.004,.006,.018),.72);n=baked.node_tree.nodes;l=baked.node_tree.links;p=n['Principled BSDF'];p.inputs['Specular IOR Level'].default_value=.12
    for name,target in [('basecolor','Base Color'),('emission','Emission Color')]:
        tex=n.new('ShaderNodeTexImage');tex.image=images[name];l.new(tex.outputs['Color'],p.inputs[target])
    p.inputs['Emission Strength'].default_value=1
    tex=n.new('ShaderNodeTexImage');tex.image=images['normal'];normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
    for o in objects:o.data.materials[0]=baked
    s.cycles.samples=32;print('Color, tangent normal and warm emission atlases baked; editable 3D material retained.')


def validate():
    from reference_rig_checks import validate as check
    return check('Summer','Summer AvatarRig',QA,obj('Summer Head')['patches']['mouth']['start'],reset,rotate,expression)


def export_runtime():
    reset();rig=obj('Summer AvatarRig');bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in {'MESH','ARMATURE'}:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_morph=True,export_morph_normal=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    rig.hide_set(True);bpy.context.scene['status']='Isolated review rig; visual acceptance and physical ZED/Orin checks still required.';bpy.ops.wm.save_as_mainfile(filepath=str(OUT))


def view(angle=False):
    s=bpy.context.scene;s.camera.location=(4,-8,3) if angle else (0,-8,1.59);s.camera.rotation_euler=(Vector((0,0,1.59))-s.camera.location).to_track_quat('-Z','Y').to_euler()
    for o in s.objects:
        if o.type in {'CAMERA','LIGHT','ARMATURE'}:o.hide_set(True)
    for a in bpy.context.screen.areas:
        if a.type=='VIEW_3D':
            sp=a.spaces.active;sp.shading.type='MATERIAL';sp.overlay.show_cursor=False;sp.overlay.show_floor=False;sp.overlay.show_axis_x=False;sp.overlay.show_axis_y=False;sp.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2);sp.region_3d.view_location=(-1.4,0,1.6);sp.region_3d.view_distance=5.5;sp.region_3d.view_perspective='ORTHO'


def render(name):bpy.context.scene.render.filepath=str(QA/(name+'.png'));bpy.ops.render.render(write_still=True)
