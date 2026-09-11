"""Reference-contour Cosmic build, executed in stages through live Blender MCP.

Uses the approved Clay workflow's mesh utilities, not the rejected generic face.
Original assets and the installation roster are never replaced here.
"""
import bpy
import bmesh
import math
import json
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.geometry import delaunay_2d_cdt
from complete_clay_likeness import mesh, closed_rings, plain_material, smooth, profile
from build_avatar_fleet import CHANNELS

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'.context/attachments/kioMh1/lailasherself_cosmic_alien_creature_made_of_a_swirling_star-f_80d4b03e-6e0a-42a9-9dff-fa782902333e_3.png'
OUT=ROOT/'blender/likeness-trials/cosmic-body-rig.blend'
GLB=ROOT/'assets/likeness-trials/cosmic-body-rig.glb'
QA=ROOT/'.context/qa/cosmic-complete'
SCALE=280
OUTLINE=[(276,354),(313,355),(350,360),(387,350),(430,346),(471,346),(520,352),(548,358),(579,342),(613,361),(627,395),(644,431),(655,481),(655,541),(647,584),(639,621),(650,660),(652,686),(637,708),(605,721),(535,730),(450,734),(370,729),(306,722),(272,712),(250,696),(242,673),(246,648),(256,620),(253,583),(245,554),(239,516),(237,477),(244,432),(257,394)]
MOUTH=(0,1.882)
ARMS={'L':[(.38,.015,1.34),(.63,-.015,1.12),(.728,-.065,.96),(.775,-.09,.87)],
      'R':[(-.38,.015,1.34),(-.63,-.015,1.10),(-.716,-.065,.92),(-.773,-.09,.82)]}


def obj(name):return bpy.context.scene.objects[name]
def point(x,z,y=0):return Vector(((x-448)/SCALE,y,(1178-z)/SCALE))


def loop(points,steps=5):
    out=[]
    for i in range(len(points)):
        a,b,c,d=[Vector(points[j%len(points)]) for j in (i-1,i,i+1,i+2)]
        for j in range(steps):
            t=j/steps;out.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out


def inside(p,poly):
    odd=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a.y>p.y)!=(b.y>p.y) and p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x:odd=not odd
    return odd


def contour():return [Vector((p.x,p.z)) for p in [point(*v) for v in loop(OUTLINE)]]


def depth(p,outline=None):
    outline=outline or contour();cx,cz=0,2.30;dx,dz=p[0]-cx,p[1]-cz
    if abs(dx)+abs(dz)<1e-8:return -.375
    hits=[]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        ex,ez=b.x-a.x,b.y-a.y;det=dx*ez-dz*ex
        if abs(det)<1e-10:continue
        ax,az=a.x-cx,a.y-cz;t=(ax*ez-az*ex)/det;u=(ax*dz-az*dx)/det
        if t>0 and -1e-6<=u<=1.000001:hits.append(t)
    r=1/min(hits) if hits else 1
    return -.375*math.sqrt(max(0,1-r*r))


def scene():
    QA.mkdir(parents=True,exist_ok=True);s=bpy.data.scenes.new('Cosmic - Reference Contour Character');bpy.context.window.scene=s
    s['status']='Reference-based body/face rig in progress; isolated from installation.'
    s['source_reference']=str(REF)
    mats={name:plain_material('Cosmic '+name,color,rough) for name,color,rough in [
        ('Galaxy',(.07,.006,.12),.65),('Orange',(.95,.19,.001),.60),('Green',(.002,.27,.003),.65),
        ('Eye',(.001,.005,.0015),.11),('Oral interior',(.002,.0003,.001),.95),
        ('Tongue',(.44,.055,.13),.44),('Teeth',(.84,.75,.57),.34)]}
    for name in ['Orange','Green']:mats[name].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.18
    s['material_names']={name:m.name for name,m in mats.items()}
    reference=bpy.data.objects.new('Cosmic source - comparison only',None);s.collection.objects.link(reference)
    reference.empty_display_type='IMAGE';reference.data=bpy.data.images.load(str(REF),check_existing=True);reference.data.pack()
    reference.empty_display_size=1344/SCALE;reference.location=(-2.7,.8,(1178-672)/SCALE);reference.rotation_euler=(math.pi/2,0,0);reference.hide_render=True
    world=bpy.data.worlds.new('Cosmic review world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.18,.18,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45;s.world=world
    for name,loc,power,size in [('Key',(-3,-4,6),420,4),('Fill',(3,-3,3),160,3),('Rim',(1,3,5),260,3)]:
        d=bpy.data.lights.new('Cosmic '+name,'AREA');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.8))-o.location).to_track_quat('-Z','Y').to_euler();d.energy=power;d.size=size
    d=bpy.data.cameras.new('Cosmic Camera');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);s.camera=o;d.type='ORTHO';d.ortho_scale=3.9
    s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1100;s.render.resolution_y=1400;s.render.resolution_percentage=100
    s.view_settings.view_transform='AgX';view()
    print('Separate Cosmic scene created; Clay remains preserved.')


def material(name):return bpy.data.materials[bpy.context.scene['material_names'][name]]


def head():
    outline=contour();front=[Vector((p.x*.94,2.30+(p.y-2.30)*.94)) for p in outline]
    n=120;mouth=[Vector((.44*math.cos(j*math.tau/n),MOUTH[1]+.21*math.sin(j*math.tau/n))) for j in range(n)]
    coords=list(front)+mouth;count=len(outline)
    edges=[(i,(i+1)%count) for i in range(count)]+[(count+j,count+(j+1)%n) for j in range(n)]
    for r in [.92,.86,.78,.68,.57,.45,.32,.19,.08]:
        for p in outline:
            q=Vector((p.x*r,2.30+(p.y-2.30)*r))
            if not inside(q,mouth):coords.append(q)
    dv,de,df,ov,oe,of=delaunay_2d_cdt(coords,edges,[],0,1e-7)
    mapping={original:i for i,ids in enumerate(ov) for original in ids}
    verts=[Vector((p.x,depth(p,outline),p.y)) for p in dv];faces=[]
    for face in df:
        p=sum((dv[i] for i in face),Vector((0,0)))/len(face)
        if inside(p,front) and not inside(p,mouth):faces.append(tuple(face))
    previous=[mapping[i] for i in range(count)]
    for r in [.96,.98,.995,1]:
        current=[]
        for p in outline:
            q=Vector((p.x*r,2.30+(p.y-2.30)*r));current.append(len(verts));verts.append(Vector((q.x,depth(q,outline),q.y)))
        for j in range(count):faces.append((previous[j],previous[(j+1)%count],current[(j+1)%count],current[j]))
        previous=current
    for r in [.996,.985,.96,.92,.86,.78,.68,.57,.45,.32,.19,.08]:
        current=[]
        for p in outline:current.append(len(verts));verts.append(Vector((p.x*r,.30*math.sqrt(1-r*r),2.30+(p.y-2.30)*r)))
        for j in range(count):faces.append((previous[j],previous[(j+1)%count],current[(j+1)%count],current[j]))
        previous=current
    center=len(verts);verts.append(Vector((0,.30,2.30)))
    faces.extend((previous[j],previous[(j+1)%count],center) for j in range(count))
    previous=[mapping[count+j] for j in range(n)];patch=[];start=len(verts)
    levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1]
    for t in levels:
        current=[]
        for j in range(n):
            phi=j*math.tau/n;sn=math.sin(phi)
            inner=Vector((.315*math.cos(phi),MOUTH[1]+.018*sn*sn+(.008 if sn>=0 else .006)*sn))
            q=mouth[j].lerp(inner,t);current.append(len(verts));patch.append((len(verts),j,t));verts.append(Vector((q.x,depth(q,outline),q.y)))
        for j in range(n):faces.append((previous[j],previous[(j+1)%n],current[(j+1)%n],current[j]))
        previous=current
    h=mesh('Cosmic Head',verts,faces,material('Galaxy'));h['mouthPatchStart']=start;h['mouthPatchRingSize']=n;h['armCollisionSurface']=True
    print({'head_vertices':len(verts),'mouth_quad_rings':12,'source_outline_points':len(outline)})


def tube(name,points,radii,mat,rings=60,sides=40):
    pts=[Vector(p) for p in points];data=[]
    for i in range(rings):
        t=i/(rings-1);u=t*(len(pts)-1);k=min(len(pts)-2,int(u));f=u-k
        a0,b0,c0,d0=pts[max(0,k-1)],pts[k],pts[k+1],pts[min(len(pts)-1,k+2)]
        p=.5*(2*b0+(-a0+c0)*f+(2*a0-5*b0+4*c0-d0)*f*f+(-a0+3*b0-3*c0+d0)*f*f*f)
        direction=(.5*((-a0+c0)+2*(2*a0-5*b0+4*c0-d0)*f+3*(-a0+3*b0-3*c0+d0)*f*f)).normalized()
        a=direction.cross(Vector((0,1,0))).normalized();b=direction.cross(a).normalized()
        r=profile([(j/(len(radii)-1),v) for j,v in enumerate(radii)],t)
        data.append([p+r*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides)) for j in range(sides)])
    return closed_rings(name,data,mat)


def ellipsoid(name,center,radii,mat,nr=32,nc=56):
    rings=[]
    for i in range(nr+1):
        theta=math.pi*(.001+.998*i/nr)
        rings.append([(center[0]+radii[0]*math.sin(theta)*math.cos(j*math.tau/nc),center[1]+radii[1]*math.sin(theta)*math.sin(j*math.tau/nc),center[2]+radii[2]*math.cos(theta)) for j in range(nc)])
    return closed_rings(name,rings,mat)


def body():
    rings=[]
    for i in range(69):
        z=.58+1.07*i/68;r=profile([(.58,.28),(.66,.425),(.83,.46),(1.02,.44),(1.20,.435),(1.36,.42),(1.49,.37),(1.65,.19)],z)
        rings.append([(r*math.cos(j*math.tau/64),.015+r*.70*math.sin(j*math.tau/64),z) for j in range(64)])
    torso=closed_rings('Cosmic Torso',rings,material('Galaxy'));torso['armCollisionSurface']=True
    for side,p in ARMS.items():
        sign=1 if side=='L' else -1
        tube('Cosmic Arm '+side,[(sign*.27,.015,1.43),*p],[.13,.135,.126,.096,.083],material('Galaxy'))
        ellipsoid('Cosmic Palm '+side,(p[-1][0],p[-1][1],p[-1][2]+.033),[.083,.075,.091],material('Galaxy'))
        for digit,positions,radii in [
            ('Thumb',[(sign*.710,-.10,.93),(sign*.670,-.115,.89),(sign*.651,-.125,.86),(sign*.648,-.14,.84)],[.050,.047,.038,.010]),
            ('Index',[(sign*.806,-.09,.87),(sign*.839,-.10,.815),(sign*.830,-.12,.765),(sign*.795,-.15,.759)],[.065,.063,.047,.008])]:
            if side=='R':positions=[(x,y,z-.04) for x,y,z in positions]
            finger=tube('Cosmic '+digit+' '+side,positions,radii,material('Galaxy'),rings=33,sides=24)
            finger['digitPoints']=[list(p) for p in positions]
        rings=[]
        for i in range(41):
            z=.32+.53*i/40;r=profile([(.32,.24),(.38,.249),(.55,.225),(.85,.215)],z)
            rings.append([(sign*.245+r*math.cos(j*math.tau/48),.01+r*.89*math.sin(j*math.tau/48),z) for j in range(48)])
        closed_rings('Cosmic Leg '+side,rings,material('Galaxy'))
        rings=[]
        for i in range(45):
            z=.018+.34*i/44;r=profile([(.018,.27),(.04,.347),(.09,.36),(.17,.33),(.27,.265),(.358,.24)],z)
            x=sign*(.34-.095*smooth(.10,.358,z));y=-.14+.13*smooth(.10,.358,z)
            rings.append([(x+r*math.cos(j*math.tau/64),y+r*1.04*math.sin(j*math.tau/64),z) for j in range(64)])
        closed_rings('Cosmic Shoe '+side,rings,material('Orange'))
    for side,pixels in [('R',[(285,370),(266,348),(238,328),(207,312)]),('L',[(594,365),(615,334),(642,310),(672,291)])]:
        pts=[point(x,z,.02) for x,z in pixels]
        tube('Cosmic Antenna '+side,pts,[.083,.077,.076,.110],material('Green'),rings=45)
        ellipsoid('Cosmic Antenna Bulb '+side,pts[-1],(.154,.128,.154),material('Green'))
    print('Squat reference body, two-digit hands, orange feet and green antennae built.')


def fuse_body():
    s=bpy.context.scene
    names=['Cosmic Torso']+[f'Cosmic {part} {side}' for side in ['L','R'] for part in ['Arm','Palm','Thumb','Index','Leg']]
    digits={name:[[float(x) for x in p] for p in obj(name)['digitPoints']] for name in names if 'digitPoints' in obj(name)}
    bpy.ops.object.select_all(action='DESELECT')
    for name in names:obj(name).select_set(True)
    bpy.context.view_layer.objects.active=obj('Cosmic Torso');bpy.ops.object.join();o=bpy.context.object;o.name='Cosmic Body';o['digitPaths']=digits
    mod=o.modifiers.new('Continuous shoulder wrist and hip transitions','REMESH');mod.mode='VOXEL';mod.voxel_size=.013;mod.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=o.modifiers.new('Soft native skin transitions','SMOOTH');mod.factor=1.1;mod.iterations=5;bpy.ops.object.modifier_apply(modifier=mod.name)
    for side in ['L','R']:
        bpy.ops.object.select_all(action='DESELECT')
        for name in ['Cosmic Antenna '+side,'Cosmic Antenna Bulb '+side]:obj(name).select_set(True)
        bpy.context.view_layer.objects.active=obj('Cosmic Antenna '+side);bpy.ops.object.join();a=bpy.context.object
        mod=a.modifiers.new('Continuous antenna bulb','REMESH');mod.mode='VOXEL';mod.voxel_size=.009;mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=a.modifiers.new('Smooth bulb transition','SMOOTH');mod.factor=1;mod.iterations=4;bpy.ops.object.modifier_apply(modifier=mod.name)
    material('Orange').node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.72,.105,.0002,1)
    material('Green').node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.0004,.18,.0008,1)
    print({'continuous_body_vertices':len(o.data.vertices)})


def eyes():
    for side,px,py in [('R',342,508),('L',534,506)]:
        center=point(px,py,-.305);radii=Vector((.327,.255,.308))
        eye=ellipsoid('Cosmic Eye '+side,center,radii,material('Eye'))
        for part,mat in [('Upper','Orange'),('Lower','Green')]:
            nr,nc=25,80;vs=[];faces=[]
            for row in range(nr):
                u=row/(nr-1);theta=.002+(1.50-.002)*u if part=='Upper' else 1.78+(math.pi-.002-1.78)*u
                for j in range(nc):
                    phi=j*math.tau/nc;vs.append(center+Vector((radii.x*math.sin(theta)*math.cos(phi),radii.y*math.sin(theta)*math.sin(phi),radii.z*math.cos(theta)))*1.018)
            for row in range(nr-1):
                for j in range(nc):faces.append((row*nc+j,row*nc+(j+1)%nc,(row+1)*nc+(j+1)%nc,(row+1)*nc+j))
            lid=mesh('Cosmic '+part+' Lid '+side,vs,faces,material(mat));lid['lidCenter']=list(center);lid['lidRadii']=list(radii);lid['lidPart']=part;lid['lidSide']=side
    print('Orange upper and green lower volumetric eyelids fitted to glossy eyes.')


def galaxy():
    m=material('Galaxy');n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Roughness'].default_value=.58;p.inputs['Specular IOR Level'].default_value=.25
    tex=n.new('ShaderNodeTexCoord')
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=8;noise.inputs['Detail'].default_value=5;noise.inputs['Roughness'].default_value=.72
    l.new(tex.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB')
    colors=[(.22,(.001,.0001,.002,1)),(.40,(.009,.0004,.015,1)),(.52,(.065,.003,.10,1)),(.63,(.19,.017,.19,1)),(.78,(.39,.07,.28,1))]
    for i,(position,color) in enumerate(colors):
        e=ramp.color_ramp.elements[i] if i<2 else ramp.color_ramp.elements.new(position);e.position=position;e.color=color
    l.new(noise.outputs['Fac'],ramp.inputs[0]);color=ramp.outputs[0]
    for scale,edge,strength,tint in [(210,.18,.95,(.80,.64,.93,1)),(27,.19,1,(1,.60,.001,1))]:
        vor=n.new('ShaderNodeTexVoronoi');vor.inputs['Scale'].default_value=scale;l.new(tex.outputs['Object'],vor.inputs['Vector'])
        mask=n.new('ShaderNodeValToRGB');mask.color_ramp.elements[0].position=edge*.3;mask.color_ramp.elements[0].color=tint
        mask.color_ramp.elements[1].position=edge;mask.color_ramp.elements[1].color=(0,0,0,1);l.new(vor.outputs['Distance'],mask.inputs[0])
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='ADD';mix.inputs[0].default_value=strength;l.new(color,mix.inputs[1]);l.new(mask.outputs[0],mix.inputs[2]);color=mix.outputs[0]
    l.new(color,p.inputs['Base Color'])
    grain=n.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=330;grain.inputs['Detail'].default_value=2;l.new(tex.outputs['Object'],grain.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.17;bump.inputs['Distance'].default_value=.0018;l.new(grain.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    m['source']='New three-dimensional purple nebula and star-fleck shader; reference PNG is comparison only.'
    print('Purple nebula bands, fine white flecks and sparse golden stars authored in 3D.')


def skeleton():
    data=bpy.data.armatures.new('Cosmic Body Skeleton');rig=bpy.data.objects.new('AvatarRig',data);bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    def bone(name,a,b,parent=None):
        e=data.edit_bones.new(name);e.head=a;e.tail=b
        if parent:e.parent=data.edit_bones[parent]
        return e
    bone('Root',(0,0,0),(0,0,.15));bone('Hips',(0,.015,.64),(0,.015,.83),'Root')
    bone('Spine',(0,.015,.83),(0,.015,1.13),'Hips');bone('Chest',(0,.015,1.13),(0,.015,1.44),'Spine')
    bone('Neck',(0,.015,1.44),(0,.015,1.70),'Chest');bone('Head',(0,.015,1.70),(0,.015,2.66),'Neck')
    paths={name:[[float(x) for x in p] for p in value] for name,value in obj('Cosmic Body')['digitPaths'].items()}
    for side,p in ARMS.items():
        bone('UpperArm.'+side,p[0],p[1],'Chest');bone('Forearm.'+side,p[1],p[2],'UpperArm.'+side);bone('Hand.'+side,p[2],p[3],'Forearm.'+side)
        sign=1 if side=='L' else -1
        bone('Thigh.'+side,(sign*.245,.01,.75),(sign*.245,-.015,.52),'Hips');bone('Shin.'+side,(sign*.245,-.015,.52),(sign*.245,-.03,.32),'Thigh.'+side)
        bone('Foot.'+side,(sign*.245,-.03,.32),(sign*.34,-.32,.10),'Shin.'+side)
        for digit in ['Thumb','Index']:
            positions=paths['Cosmic '+digit+' '+side]
            for i in range(3):
                e=bone(f'{digit}{i+1}.{side}',positions[i],positions[i+1],f'{digit}{i}.{side}' if i else 'Hand.'+side);e.align_roll(Vector((0,-1,0)))
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig['rigVersion']='cosmic-reference-contour-1';rig['installationApproved']=False
    for side in ARMS:
        data.bones['UpperArm.'+side]['armCollisionRestContact']=True
        for digit in ['Thumb','Index']:
            for i,angle in enumerate([.45,.55,.40]):data.bones[f'{digit}{i+1}.{side}']['fingerCurlRadians']=angle
    def closest(p,path):
        result=(1e9,0)
        for i,(a,b) in enumerate(zip(path,path[1:])):
            a,b=Vector(a),Vector(b);d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));dist=(p-(a+d*t)).length
            if dist<result[0]:result=(dist,i+t)
        return result
    surface=obj('Cosmic Body');adj=[[] for _ in surface.data.vertices]
    for e in surface.data.edges:
        a,b=e.vertices;adj[a].append(b);adj[b].append(a)
    remaining={v.index for v in surface.data.vertices if v.co.z<1.05};regions={}
    while remaining:
        first=remaining.pop();component=[first];todo=[first]
        while todo:
            for j in adj[todo.pop()]:
                if j in remaining:remaining.remove(j);component.append(j);todo.append(j)
        meanx=sum(surface.data.vertices[i].co.x for i in component)/len(component)
        for i in component:regions[i]=1 if abs(meanx)>.50 else 0
    for o in list(bpy.context.scene.objects):
        if o.type!='MESH':continue
        groups={b.name:o.vertex_groups.new(name=b.name) for b in data.bones}
        for v in o.data.vertices:
            x,y,z=v.co;side='L' if x>=0 else 'R';p=ARMS[side];w={'Head':1}
            if o.name=='Cosmic Body':
                if z<1.10:t=smooth(.75,1.08,z);w={'Hips':1-t,'Spine':t}
                else:t=smooth(1.10,1.35,z);n=smooth(1.43,1.63,z);w={'Spine':(1-t)*(1-n),'Chest':t*(1-n),'Neck':n}
                leg=1-smooth(.67,.85,z)
                if leg:
                    k=1-smooth(.44,.60,z);f=1-smooth(.30,.40,z);lw={'Thigh.'+side:1-k,'Shin.'+side:k*(1-f),'Foot.'+side:k*f}
                    w={n:a*(1-leg) for n,a in w.items()};w.update({n:a*leg for n,a in lw.items()})
                transition=smooth(1.05,1.40,z)
                arm=regions[v.index] if v.index in regions else smooth(.455-.195*transition,.50+.03*transition,abs(x))
                if arm:
                    e=1-smooth(p[1][2]-.15,p[1][2]+.15,z);hand=1-smooth(p[2][2]-.055,p[2][2]+.06,z)
                    aw={'UpperArm.'+side:1-e,'Forearm.'+side:e*(1-hand),'Hand.'+side:e*hand}
                    if abs(x)>.60 and z<(.98 if side=='L' else .94):
                        options=[(*closest(v.co,paths['Cosmic '+digit+' '+side]),digit) for digit in ['Thumb','Index']]
                        dist,u,digit=min(options);offset=0 if side=='L' else -.04
                        factor=smooth(.12,.90,u)*(1-smooth(.88+offset,.98+offset,z))
                        # Blend only adjacent bones within the nearest native digit.
                        q=max(0,min(2,u-.5));i=min(1,int(q));f=q-i
                        aw={n:a*(1-factor) for n,a in aw.items()};aw[f'{digit}{i+1}.{side}']=(1-f)*factor;aw[f'{digit}{i+2}.{side}']=f*factor
                    w={n:a*(1-arm) for n,a in w.items()};w.update({n:a*arm for n,a in aw.items()})
            elif o.name.startswith('Cosmic Shoe'):w={'Foot.'+o.name[-1]:1}
            for name,a in w.items():
                if a>1e-8:groups[name].add([v.index],a,'REPLACE')
        mod=o.modifiers.new('Body deformation','ARMATURE');mod.object=rig;o.parent=rig
    print({'bones':len(data.bones),'native_digits_per_hand':2})


def mouth_point(j,n=120):
    phi=j*math.tau/n;sn=math.sin(phi);x=.315*math.cos(phi);z=MOUTH[1]+.018*sn*sn+(.008 if sn>=0 else .006)*sn
    return Vector((x,depth((x,z)),z))


def smooth_shoulders(iterations=100):
    import numpy as np
    o=obj('Cosmic Body');count=len(o.data.vertices);groups=list(o.vertex_groups);w=np.zeros((count,len(groups)))
    for v in o.data.vertices:
        for g in v.groups:w[v.index,g.group]=g.weight
    edges=np.array([e.vertices[:] for e in o.data.edges]);a=np.concatenate([edges[:,0],edges[:,1]]);b=np.concatenate([edges[:,1],edges[:,0]]);degree=np.bincount(a,minlength=count)
    mask=np.array([smooth(.17,.29,abs(v.co.x))*(1-smooth(.57,.69,abs(v.co.x)))*smooth(1.0,1.12,v.co.z)*(1-smooth(1.55,1.65,v.co.z)) for v in o.data.vertices])*.70
    for _ in range(iterations):
        mean=np.stack([np.bincount(a,weights=w[b,i],minlength=count)/np.maximum(degree,1) for i in range(w.shape[1])],axis=1)
        w+=(mean-w)*mask[:,None]
    for g in groups:g.remove(list(range(count)))
    for i,row in enumerate(w):
        total=sum(row)
        for j,value in enumerate(row):
            if value>1e-8:groups[j].add([i],float(value/total),'REPLACE')
    print('Shoulder weights relaxed along surface adjacency; fingers and opposite sides remain isolated.')


def runtime_weights():
    o=obj('Cosmic Body');rows=[]
    for v in o.data.vertices:
        w={o.vertex_groups[g.group].name:g.weight for g in v.groups};side='L' if v.co.x>=0 else 'R'
        if any(w.get(n+'.'+side,0)>1e-8 for n in ['UpperArm','Forearm','Hand']):
            trunk=sum(w.pop(n,0) for n in ['Hips','Spine','Chest','Neck','Head'])
            if trunk:w['Chest']=trunk
        digit_names=[f'{digit}{i}.{side}' for digit in ['Thumb','Index'] for i in [1,2,3]]
        if any(w.get(n,0)>1e-8 for n in digit_names):
            if v.co.z>(.98 if side=='L' else .94):
                w['Hand.'+side]=w.get('Hand.'+side,0)+sum(w.pop(n,0) for n in digit_names)
            else:w['Forearm.'+side]=w.get('Forearm.'+side,0)+w.pop('UpperArm.'+side,0)
        row=sorted(w.items(),key=lambda p:-p[1])[:4];total=sum(x for _,x in row);rows.append([(n,x/total) for n,x in row])
    for g in o.vertex_groups:g.remove(list(range(len(rows))))
    for i,row in enumerate(rows):
        for name,value in row:o.vertex_groups[name].add([i],value,'REPLACE')
    print('Four-influence runtime skin: trunk influences merged before limiting, avoiding weight-selection seams.')


def mouth_motion(j,name):
    phi=j*math.tau/120;q=math.cos(phi);sn=math.sin(phi);p=mouth_point(j);v=p.copy();side=1 if name.endswith('Left') else -1
    mask=smooth(-.25,.55,q*side);top=max(0,sn);bottom=max(0,-sn)
    if name in {'jawOpen','mouthClose'}:
        target=Vector((.30*q,0,MOUTH[1]-.045+.112*sn));target.y=depth((target.x,target.z));return (target-p)*(1 if name=='jawOpen' else -1)
    if name in {'jawLeft','jawRight','mouthLeft','mouthRight'}:v.x+=side*.028
    elif name=='jawForward':v.y-=.018
    elif name.startswith('mouthSmile'):v.z+=.030*mask*abs(q);v.x+=side*.012*mask
    elif name.startswith('mouthFrown'):v.z-=.018*mask*abs(q)
    elif name.startswith('mouthDimple'):v.x+=side*.012*mask;v.y+=.009*mask
    elif name.startswith('mouthStretch'):v.x+=side*.028*mask
    elif name in {'mouthPucker','mouthFunnel'}:v.x*=.84 if name=='mouthPucker' else .90;v.z+=.030*sn;v.y-=.02
    elif name=='mouthRollUpper':v.z-=.003*top;v.y+=.008*top
    elif name=='mouthRollLower':v.z+=.003*bottom;v.y+=.008*bottom
    elif name=='mouthShrugUpper':v.z+=.025*top
    elif name=='mouthShrugLower':v.z+=.014*bottom
    elif name.startswith('mouthPress'):v.z-=.002*sn*mask
    elif name.startswith('mouthUpperUp'):v.z+=.033*top*mask
    elif name.startswith('mouthLowerDown'):v.z-=.030*bottom*mask
    return v-p


def facial():
    h=obj('Cosmic Head');base=h.shape_key_add(name='Basis',from_mix=False);start=h['mouthPatchStart'];n=120;levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1]
    outline=contour()
    for name in CHANNELS:
        if name=='tongueOut':continue
        key=h.shape_key_add(name=name,from_mix=False)
        for v,b in zip(key.data,base.data):v.co=b.co
        if name.startswith(('jaw','mouth')):
            deltas=[mouth_motion(j,name) for j in range(n)]
            for row,t in enumerate(levels):
                for j in range(n):
                    index=start+row*n+j;v=base.data[index].co+deltas[j]*t
                    v.y=depth((v.x,v.z),outline)+(0 if name in {'jawOpen','mouthClose'} else deltas[j].y)*t
                    key.data[index].co=v
        else:
            for v,b in zip(key.data,base.data):
                x,y,z=b.co;front=smooth(.0,-.25,y);side=1 if name.endswith('Left') else -1;local=math.exp(-((x-side*.35)/.24)**4)
                if name.startswith('brow'):v.co.z+=(.025 if 'Up' in name else -.020)*front*local*math.exp(-((z-2.76)/.15)**4)
                elif name=='cheekPuff':v.co.y-=.025*front*math.exp(-((z-2.02)/.18)**4)*smooth(.25,.50,abs(x))
                elif name.startswith('cheekSquint'):v.co.z+=.012*front*local*math.exp(-((z-2.04)/.13)**4)
                elif name.startswith('noseSneer'):v.co.z+=.015*front*local*math.exp(-((z-2.18)/.13)**4)
    for side,label in [('L','Left'),('R','Right')]:
        for part in ['Upper','Lower']:
            lid=obj(f'Cosmic {part} Lid {side}');base=lid.shape_key_add(name='Basis',from_mix=False);center=Vector(lid['lidCenter']);r=Vector(lid['lidRadii']);nr,nc=25,80
            for channel,boundary in [('eyeBlink',1.64 if part=='Upper' else 1.643),('eyeWide',1.22 if part=='Upper' else 2.02),('eyeSquint',1.57 if part=='Upper' else 1.69)]:
                key=lid.shape_key_add(name=channel+label,from_mix=False)
                for row in range(nr):
                    u=row/(nr-1);theta=.002+(boundary-.002)*u if part=='Upper' else boundary+(math.pi-.002-boundary)*u
                    for j in range(nc):
                        phi=j*math.tau/nc;key.data[row*nc+j].co=center+Vector((r.x*math.sin(theta)*math.cos(phi),r.y*math.sin(theta)*math.sin(phi),r.z*math.cos(theta)))*1.018
            lid['blinkMethod']='Parameterized matched shell boundaries; production resolveEyeAperture prevents opposing morphs.'
        eye=obj('Cosmic Eye '+side);base=eye.shape_key_add(name='Basis',from_mix=False)
        for axis,direction in [('In',-.010 if side=='L' else .010),('Out',.010 if side=='L' else -.010),('Up',.008),('Down',-.008)]:
            key=eye.shape_key_add(name='eyeLook'+axis+label,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((direction,0,0) if axis in ['In','Out'] else (0,0,direction))
    oral()
    print('52 expression channels, independently fitted eyelids and bounded mouth loops created.')


def bind_head(o):
    rig=obj('AvatarRig');g=o.vertex_groups.new(name='Head');g.add(list(range(len(o.data.vertices))),1,'REPLACE');o.parent=rig;m=o.modifiers.new('Head deformation','ARMATURE');m.object=rig


def oral():
    n=120;inner=[mouth_point(j) for j in range(n)]
    rings=[[(p.x*(1+.15*t),p.y+.004+.28*t,p.z-.02*t+(p.z-MOUTH[1])*t*2) for p in inner] for t in [i/12 for i in range(13)]]
    cavity=closed_rings('Cosmic Oral Cavity',rings,material('Oral interior'))
    bm=bmesh.new();bm.from_mesh(cavity.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[13*n]],context='VERTS');bm.to_mesh(cavity.data);bm.free();bind_head(cavity)
    base=cavity.shape_key_add(name='Basis',from_mix=False)
    for name in CHANNELS:
        if not name.startswith(('mouth','jaw')):continue
        key=cavity.shape_key_add(name=name,from_mix=False)
        deltas=[mouth_motion(j,name) for j in range(n)]
        for i,(v,b) in enumerate(zip(key.data,base.data)):v.co=b.co+deltas[i%n]*(1-smooth(.1,.8,min(1,i//n/12)))
    for row,zc in [('Upper',MOUTH[1]+.063),('Lower',MOUTH[1]-.045)]:
        parts=[]
        for i in range(8):parts.append(ellipsoid(f'Cosmic {row} Tooth {i}',((i-3.5)*.057,-.215+abs(i-3.5)*.004,zc),(.025,.035,.035),material('Teeth'),nr=8,nc=16))
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts:o.select_set(True)
        bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='Cosmic '+row+' Teeth';bind_head(o);base=o.shape_key_add(name='Basis',from_mix=False)
        for name,sign in [('jawOpen',1),('mouthClose',-1)]:
            key=o.shape_key_add(name=name,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((0,0,sign*(-.005 if row=='Upper' else -.08)))
    rings=[];nr,nc=49,24
    for i in range(nr):
        t=i/(nr-1);tip=math.sqrt(max(.02,1-t**8));rings.append([(.095*tip*math.cos(j*math.tau/nc),-.10-.10*t,MOUTH[1]-.037+.021*tip*math.sin(j*math.tau/nc)) for j in range(nc)])
    tongue=closed_rings('Cosmic Long Tongue',rings,material('Tongue'));bind_head(tongue);base=tongue.shape_key_add(name='Basis',from_mix=False)
    for name in ['tongueOut','jawOpen','mouthClose']:
        key=tongue.shape_key_add(name=name,from_mix=False)
        for i,(v,b) in enumerate(zip(key.data,base.data)):
            t=(i//nc)/(nr-1) if i<nr*nc else (0 if i==nr*nc else 1);v.co=b.co
            if name=='tongueOut':v.co.y-=.98*t;v.co.z+=.11*math.sin(math.pi*t)-.42*t*t
            else:v.co.z-=(-1 if name=='mouthClose' else 1)*.04*smooth(0,.38,t)
    tongue['tongueRootAnchored']=True;tongue['additionalReach']=.98


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
    p=obj('AvatarRig').pose.bones[name];p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion(Vector(axis),angle);bpy.context.view_layer.update()


def bake_material():
    reset();s=bpy.context.scene;s.cycles.samples=8;skin=material('Galaxy');skin.use_fake_user=True
    objects=[o for o in s.objects if o.type=='MESH' and skin in list(o.data.materials)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.010);bpy.ops.object.mode_set(mode='OBJECT')
    images=[];node=skin.node_tree.nodes.new('ShaderNodeTexImage');skin.node_tree.nodes.active=node
    for name,size,kind in [('basecolor',2048,'DIFFUSE'),('normal',1024,'NORMAL')]:
        atlas=bpy.data.images.new('Cosmic galaxy '+name,width=size,height=size);node.image=atlas
        if kind=='NORMAL':atlas.colorspace_settings.name='Non-Color';bpy.ops.object.bake(type=kind,use_clear=False,margin=8,normal_space='TANGENT')
        else:bpy.ops.object.bake(type=kind,pass_filter={'COLOR'},use_clear=False,margin=8)
        atlas.filepath_raw=str(GLB.parent/f'cosmic-galaxy-{name}.png');atlas.file_format='PNG';atlas.save();atlas.pack();images.append(atlas)
    baked=plain_material('Cosmic Galaxy - Runtime PBR',(.07,.004,.1),.58);n=baked.node_tree.nodes;l=baked.node_tree.links;p=n.get('Principled BSDF');p.inputs['Specular IOR Level'].default_value=.25
    color=n.new('ShaderNodeTexImage');color.image=images[0];l.new(color.outputs['Color'],p.inputs['Base Color']);tex=n.new('ShaderNodeTexImage');tex.image=images[1];nm=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    for o in objects:o.data.materials[0]=baked
    s.cycles.samples=32
    print('Shared 2048 base-color and 1024 tangent-normal textures baked; procedural source retained.')


def export_runtime():
    reset();rig=obj('AvatarRig');bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in {'MESH','ARMATURE'}:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_morph=True,export_morph_normal=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    rig.hide_set(True);bpy.context.scene['status']='Isolated review rig; physical ZED/Orin and visual acceptance still required.';bpy.ops.wm.save_as_mainfile(filepath=str(OUT))


def validate():
    import numpy as np
    reset();h=obj('Cosmic Head');h.data.calc_loop_triangles();keys=h.data.shape_keys.key_blocks
    base=np.array([v.co[:] for v in keys['Basis'].data]);tri=np.array([t.vertices[:] for t in h.data.loop_triangles]);tri=tri[np.any(tri>=h['mouthPatchStart'],axis=1)]
    def area(p):
        t=p[tri][:,:,[0,2]];a=t[:,1]-t[:,0];b=t[:,2]-t[:,0];return a[:,0]*b[:,1]-a[:,1]*b[:,0]
    original=area(base);report={'status':'Isolated review rig; not physical sensor or deployment validation','mouth':[],'meshes':[],'arms':[],'fingers':[]}
    poses=[{}, {'jawOpen':1},{'jawOpen':1,'mouthClose':1},{'mouthSmileLeft':1,'mouthSmileRight':1},{'jawOpen':.8,'mouthSmileLeft':.7,'mouthSmileRight':.7},{'mouthFrownLeft':1,'mouthFrownRight':1},{'jawOpen':.6,'mouthFunnel':.5,'mouthPucker':.3},{'jawOpen':.8,'tongueOut':1},{'jawOpen':1,'mouthStretchLeft':.7,'mouthStretchRight':.7},{'jawOpen':.4,'jawLeft':1},{'jawOpen':.4,'jawRight':1},{'mouthPressLeft':1,'mouthPressRight':1}]
    for values in poses:
        p=base.copy()
        for name,value in values.items():
            if name in keys:p+=(np.array([v.co[:] for v in keys[name].data])-base)*value
        report['mouth'].append({'values':values,'flipped_triangles':int(np.sum(area(p)*original < -1e-12))})
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(o.data);weights=[sum(g.weight for g in v.groups) for v in o.data.vertices]
        report['meshes'].append({'name':o.name,'vertices':len(bm.verts),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'nonmanifold_nonboundary_edges':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),'weight_error':max(abs(w-1) for w in weights)});bm.free()
    dg=bpy.context.evaluated_depsgraph_get()
    def evaluated(o):
        ev=o.evaluated_get(dg);m=ev.to_mesh();p=np.array([v.co[:] for v in m.vertices]);ev.to_mesh_clear();return p
    body=obj('Cosmic Body');rest=evaluated(body);headrest=evaluated(h);edges=np.array([e.vertices[:] for e in body.data.edges]);before=np.linalg.norm(rest[edges[:,0]]-rest[edges[:,1]],axis=1)
    for side,shoulder,elbow in [('L',-.8,-.7),('L',-1.6,-1.5),('R',.8,-.7),('R',1.6,-1.5)]:
        reset();rotate('UpperArm.'+side,(0,1,0),shoulder);rotate('Forearm.'+side,(1,0,0),elbow);rotate('Hand.'+side,(1,0,0),.4)
        p=evaluated(body);after=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1);ratio=after[before>1e-5]/before[before>1e-5];opposite=rest[:,0]<-.1 if side=='L' else rest[:,0]>.1
        report['arms'].append({'side':side,'shoulder':shoulder,'elbow':elbow,'opposite_drift':float(np.max(np.linalg.norm(p[opposite]-rest[opposite],axis=1))),'head_drift':float(np.max(np.linalg.norm(evaluated(h)-headrest,axis=1))),'edge_stretch_max':float(np.max(ratio)),'edge_stretch_p99':float(np.quantile(ratio,.99))})
    for side in ['L','R']:
        for digit in ['Thumb','Index']:
            reset()
            for i,angle in enumerate([.45,.55,.40]):rotate(f'{digit}{i+1}.{side}',(1,0,0),angle)
            p=evaluated(body);opposite=rest[:,0]<-.1 if side=='L' else rest[:,0]>.1
            report['fingers'].append({'side':side,'digit':digit,'maximum_motion':float(np.max(np.linalg.norm(p-rest,axis=1))),'opposite_drift':float(np.max(np.linalg.norm(p[opposite]-rest[opposite],axis=1)))})
    reset();tongue=obj('Cosmic Long Tongue');tb=tongue.data.shape_keys.key_blocks['Basis'];report['tongue_root_drift']=max((tongue.data.shape_keys.key_blocks[name].data[i].co-tb.data[i].co).length for name in ['tongueOut','jawOpen','mouthClose'] for i in range(24));report['bones']=len(obj('AvatarRig').data.bones)
    (QA/'geometry-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
    assert all(p['flipped_triangles']==0 for p in report['mouth'])
    assert all(p['zero_area_faces']==0 and p['nonmanifold_nonboundary_edges']==0 and p['weight_error']<1e-6 for p in report['meshes'])
    assert all(p['opposite_drift']<1e-6 and p['head_drift']<1e-6 and p['edge_stretch_p99']<1.35 and p['edge_stretch_max']<1.8 for p in report['arms'])
    assert all(p['opposite_drift']<1e-6 and p['maximum_motion']>.015 for p in report['fingers'])
    assert report['tongue_root_drift']<1e-6 and report['bones']==30
    return report


def view(angle=False):
    s=bpy.context.scene;s.camera.location=(4,-8,3) if angle else (0,-8,1.68);s.camera.rotation_euler=(Vector((0,0,1.68))-s.camera.location).to_track_quat('-Z','Y').to_euler()
    for o in s.objects:
        if o.type in {'CAMERA','LIGHT','ARMATURE'}:o.hide_set(True)
    for a in bpy.context.screen.areas:
        if a.type=='VIEW_3D':
            sp=a.spaces.active;sp.shading.type='MATERIAL';sp.overlay.show_cursor=False;sp.overlay.show_floor=False;sp.overlay.show_axis_x=False;sp.overlay.show_axis_y=False
            sp.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2);sp.region_3d.view_location=(-1.35,0,1.7);sp.region_3d.view_distance=5.3;sp.region_3d.view_perspective='ORTHO'


def render(name):bpy.context.scene.render.filepath=str(QA/(name+'.png'));bpy.ops.render.render(write_still=True)
