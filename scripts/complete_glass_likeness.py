"""Glass's own reference-contour build, staged in the live Blender MCP scene."""
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
REF=ROOT/'.context/attachments/ShSwdv/lailasherself_make_it_ready_for_rigging_--ar_23_--edit_httpss_1e0ec3f0-96de-4aa0-b2a2-09716f469244_1.png'
QA=ROOT/'.context/qa/glass-complete'
OUT=ROOT/'blender/likeness-trials/glass-body-rig.blend'
GLB=ROOT/'assets/likeness-trials/glass-body-rig.glb'
OUTLINE=[(147,370),(154,298),(181,223),(229,165),(293,126),(365,100),(442,91),(525,97),(599,118),(666,159),(713,220),(736,284),(738,346),(718,413),(676,477),(620,530),(550,571),(476,593),(407,599),(337,589),(266,569),(210,533),(172,482),(151,429)]
EYES={'R':[(186,351),(203,342),(225,349),(250,370),(273,401),(291,441),(299,478),(294,513),(280,531),(260,534),(235,523),(212,502),(193,473),(179,438),(175,400),(178,370)],
      'L':[(448,353),(468,333),(491,325),(516,325),(543,336),(563,355),(578,383),(584,413),(580,446),(568,474),(548,499),(522,516),(494,523),(469,520),(449,507),(435,485),(430,457),(431,424),(437,389)]}
MOUTH=Vector(((451-450)/300,(1108-551)/300))
ARMS={'R':[(-.22,0,1.53),(-.425,-.01,1.01),(-.58,-.035,.735),(-.61,-.055,.66)],
      'L':[(.285,.025,1.53),(.410,.0,1.06),(.525,-.03,.765),(.56,-.06,.65)]}
ARM_RADII={s:[.085,.067,.060,.075] for s in ARMS}
TORSO=[(.81,.04,.21,.14),(.88,.04,.28,.18),(1.03,.04,.27,.185),(1.23,.03,.195,.145),(1.43,.035,.13,.115),(1.62,.04,.085,.09),(1.76,.04,.09,.095)]
LEGS={s:[(.015,x,.08,.10),(.065,x,.145,.21),(.15,x,.13,.17),(.27,x+.015,.072,.07),(.48,x+.03,.054,.06),(.72,x+.015,.07,.075),(.88,x*.75,.07,.075),(.99,x*.57,.055,.06)] for s,x in [('R',-.305),('L',.25)]}
DIGITS={'R':{'Thumb':[(-.56,-.05,.70),(-.505,-.07,.66),(-.48,-.09,.62),(-.49,-.10,.60)],
             'Index':[(-.64,-.05,.64),(-.68,-.07,.59),(-.70,-.09,.55),(-.68,-.105,.53)],
             'Middle':[(-.61,-.05,.60),(-.59,-.075,.54),(-.55,-.10,.50),(-.53,-.11,.52)]},
        'L':{'Thumb':[(.52,-.05,.68),(.475,-.07,.63),(.45,-.09,.58),(.47,-.10,.565)],
             'Index':[(.60,-.05,.65),(.66,-.07,.615),(.70,-.09,.59),(.69,-.10,.575)],
             'Middle':[(.565,-.05,.60),(.58,-.075,.535),(.61,-.10,.485),(.65,-.11,.49)]}}


def obj(name):return bpy.context.scene.objects[name]
def mat(name):return bpy.data.materials[bpy.context.scene['material_names'][name]]
def point(px,py,y=0):return Vector(((px-450)/300,y,(1108-py)/300))
def contour():return [Vector((p.x,p.z)) for p in [point(*v) for v in loop(OUTLINE)]]


def depth(p,outline=None):
    outline=outline or contour();cx,cz=0,2.527;dx,dz=p[0]-cx,p[1]-cz;hits=[]
    if abs(dx)+abs(dz)<1e-8:return -.63
    for a,b in zip(outline,outline[1:]+outline[:1]):
        ex,ez=b.x-a.x,b.y-a.y;det=dx*ez-dz*ex
        if abs(det)<1e-10:continue
        ax,az=a.x-cx,a.y-cz;t=(ax*ez-az*ex)/det;u=(ax*dz-az*dx)/det
        if t>0 and -1e-6<=u<=1.000001:hits.append(t)
    r=1/min(hits) if hits else 1
    return -.63*math.sqrt(max(0,1-r*r))


def scene():
    QA.mkdir(parents=True,exist_ok=True);s=bpy.data.scenes.new('Glass - Reference Contour Character');bpy.context.window.scene=s
    s['status']='Isolated reference build in progress, not installation approved.';s['source_reference']=str(REF)
    materials={name:plain_material('Glass '+name,color,rough) for name,color,rough in [('Skin',(.004,.006,.018),.52),('Eye',(.014,.009,.030),.31),('Glow',(1,.42,.065),.35),('Oral interior',(.001,.0003,.001),.95),('Teeth',(.70,.62,.44),.35),('Tongue',(.42,.06,.065),.46)]}
    s['material_names']={n:m.name for n,m in materials.items()}
    p=mat('Glow').node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(1,.40,.12,1);p.inputs['Emission Color'].default_value=(1,.40,.05,1);p.inputs['Emission Strength'].default_value=.25
    p=mat('Eye').node_tree.nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.65;p.inputs['Specular IOR Level'].default_value=.1
    ref=bpy.data.objects.new('Glass reference - comparison only',None);s.collection.objects.link(ref);ref.empty_display_type='IMAGE';ref.data=bpy.data.images.load(str(REF),check_existing=True);ref.data.pack();ref.empty_display_size=1344/300;ref.location=(-2.9,.8,(1108-672)/300);ref.rotation_euler=(math.pi/2,0,0);ref.hide_render=True
    world=bpy.data.worlds.new('Glass review world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.16,.16,1);world.node_tree.nodes['Background'].inputs[1].default_value=.40;s.world=world
    for name,loc,power,size in [('Key',(-3,-4,6),420,4),('Fill',(3,-3,3),170,3),('Rim',(1,3,5),260,3)]:
        d=bpy.data.lights.new('Glass '+name,'AREA');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.7))-o.location).to_track_quat('-Z','Y').to_euler();d.energy=power;d.size=size
        if name=='Key':d.shape='RECTANGLE';d.size=.7;d.size_y=2.5;o.location=(2,-4,5)
        elif name=='Fill':d.color=(1,.35,.09);o.location=(-3,-2,3);d.energy=230;d.size=2
        else:d.color=(.25,1,.75)
    d=bpy.data.cameras.new('Glass Camera');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);s.camera=o;d.type='ORTHO';d.ortho_scale=3.85
    s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1100;s.render.resolution_y=1400;s.render.resolution_percentage=100;s.view_settings.view_transform='Standard';view()


def head():
    outline=contour();count=len(outline);front=[Vector((p.x*.975,2.527+(p.y-2.527)*.975)) for p in outline]
    apertures={side:[Vector((p.x,p.z)) for p in [point(*v) for v in loop(points,6)]] for side,points in EYES.items()}
    centers={side:sum(points,Vector((0,0)))/len(points) for side,points in apertures.items()}
    holes={side:[centers[side]+(p-centers[side])*1.22 for p in points] for side,points in apertures.items()}
    holes['mouth']=[MOUTH+Vector((.34*math.cos(j*math.tau/120),.11*math.sin(j*math.tau/120))) for j in range(120)]
    coords=list(front);constraints=[(i,(i+1)%count) for i in range(count)];indexes={}
    for name,points in holes.items():
        start=len(coords);coords+=points;indexes[name]=list(range(start,len(coords)));constraints.extend((start+j,start+(j+1)%len(points)) for j in range(len(points)))
    for r in [.95,.91,.85,.78,.69,.60,.50,.39,.28,.17,.07]:
        for p in outline:
            q=Vector((p.x*r,2.527+(p.y-2.527)*r))
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
            q=Vector((p.x*r,2.527+(p.y-2.527)*r));current.append(len(vs));vs.append(Vector((q.x,.55*math.sqrt(1-r*r) if back else depth(q,outline),q.y)))
        for j in range(count):fs.append((previous[j],previous[(j+1)%count],current[(j+1)%count],current[j]))
        previous=current
    ci=len(vs);vs.append(Vector((0,.55,2.527)));fs.extend((previous[j],previous[(j+1)%count],ci) for j in range(count))
    patches={};levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1]
    for name,outer in holes.items():
        n=len(outer);previous=[mapping[i] for i in indexes[name]];start=len(vs)
        for t in levels:
            current=[]
            for j,a in enumerate(outer):
                if name=='mouth':
                    phi=j*math.tau/n;sn=math.sin(phi);inner=MOUTH+Vector((.24*math.cos(phi),-.006*sn*sn+(.006 if sn>=0 else .005)*sn))
                else:inner=apertures[name][j]
                p=a.lerp(inner,t);current.append(len(vs));vs.append(Vector((p.x,depth(p,outline)+(.008*t*t if name!='mouth' else 0),p.y)))
            for j in range(n):fs.append((previous[j],previous[(j+1)%n],current[(j+1)%n],current[j]))
            previous=current
        patches[name]={'start':start,'size':n}
    h=mesh('Glass Head',vs,fs,mat('Skin'));h['patches']=patches;h['armCollisionSurface']=True
    for side,points in apertures.items():
        center=centers[side];rings=[];n=len(points)
        for i in range(17):
            r=1.01*(1-i/17)
            rings.append([(p.x,depth(p,outline)+.014-.12*(1-r*r),p.y) for p in [center+(v-center)*r for v in points]])
        eye=closed_rings('Glass Eye '+side,rings,mat('Eye'))
        bm=bmesh.new();bm.from_mesh(eye.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[17*n]],context='VERTS');bm.to_mesh(eye.data);bm.free()
        eye['eyeCenter']=list(center)

    print({'head_vertices':len(vs),'eye_apertures':len(apertures),'uniform_mouth_columns':120})


def projections():
    rim_material=plain_material('Glass Raised Aqua Eye Rims',(.008,.20,.23),.11);p=rim_material.node_tree.nodes['Principled BSDF'];p.inputs['Metallic'].default_value=.42;p.inputs['Coat Weight'].default_value=1
    for side,points in EYES.items():
        path=[point(*v) for v in loop(points,6)];center=sum(path,Vector())/len(path);vs=[];fs=[];n=len(path)
        for i,v in enumerate(path):
            tangent=(path[(i+1)%n]-path[(i-1)%n]).normalized();across=Vector((-tangent.z,0,tangent.x));v=center+(v-center)*1.032;v.y=depth((v.x,v.z))-.012
            for j in range(10):vs.append(v+across*(.012*math.cos(j*math.tau/10))+Vector((0,.012*math.sin(j*math.tau/10),0)))
        for i in range(n):
            for j in range(10):fs.append((i*10+j,i*10+(j+1)%10,((i+1)%n)*10+(j+1)%10,((i+1)%n)*10+j))
        o=mesh('Glass Eye Rim '+side,vs,fs,rim_material);base=o.shape_key_add(name='Basis',from_mix=False)
        for kind,factor in [('eyeBlink',-.999),('eyeSquint',-.38),('eyeWide',.12)]:
            key=o.shape_key_add(name=kind+('Left' if side=='L' else 'Right'),from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co;v.co.z+=(b.co.z-center.z)*factor;v.co.y+=depth((v.co.x,v.co.z))-depth((b.co.x,b.co.z))

def body():
    from reference_body_tools import body as build
    build('Glass',mat('Skin'),TORSO,{s:(p,ARM_RADII[s]) for s,p in ARMS.items()},LEGS,DIGITS)

def skin():
    m=mat('Skin');n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF']
    p.inputs['Roughness'].default_value=.14;p.inputs['Metallic'].default_value=.22;p.inputs['Coat Weight'].default_value=1;p.inputs['Coat Roughness'].default_value=.09;p.inputs['IOR'].default_value=1.46
    tc=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');l.new(tc.outputs['Object'],sep.inputs[0])
    height=n.new('ShaderNodeMapRange');height.inputs['From Min'].default_value=.77;height.inputs['From Max'].default_value=1.12;height.clamp=True;l.new(sep.outputs['Z'],height.inputs[0])
    tint=n.new('ShaderNodeMixRGB');tint.inputs[1].default_value=(.025,.36,.41,1);tint.inputs[2].default_value=(.0003,.016,.020,1);l.new(height.outputs[0],tint.inputs[0]);color=tint.outputs[0]
    for scale,edge,tintcolor in [(95,.14,(.006,.48,.60,1)),(160,.065,(.9,.36,.04,1))]:
        v=n.new('ShaderNodeTexVoronoi');v.inputs['Scale'].default_value=scale;l.new(tc.outputs['Object'],v.inputs['Vector'])
        r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].position=.005;r.color_ramp.elements[0].color=tintcolor;r.color_ramp.elements[1].position=edge;r.color_ramp.elements[1].color=(0,0,0,1);l.new(v.outputs['Distance'],r.inputs[0])
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='ADD';mix.inputs[0].default_value=1;l.new(color,mix.inputs[1]);l.new(r.outputs[0],mix.inputs[2]);color=mix.outputs[0]
    l.new(color,p.inputs['Base Color'])
    p.inputs['Transmission Weight'].default_value=.65
    eye=mat('Eye').node_tree.nodes['Principled BSDF'];eye.inputs['Base Color'].default_value=(.0002,.015,.017,1);eye.inputs['Roughness'].default_value=.07;eye.inputs['Metallic'].default_value=.30;eye.inputs['Coat Weight'].default_value=1;eye.inputs['Specular IOR Level'].default_value=.5
    m['source']='Editable volumetric aqua flecks and glass PBR, never source-image projection.'


def skeleton():
    from reference_body_tools import rig
    return rig('Glass',TORSO,{s:(p,ARM_RADII[s]) for s,p in ARMS.items()},LEGS,DIGITS,.88,.47,.14,1.76,2.6,1.16,.38)

def smooth_weights(iterations=750):pass

def mouth_point(j):
    phi=j*math.tau/120;sn=math.sin(phi);p=MOUTH+Vector((.24*math.cos(phi),-.006*sn*sn+(.006 if sn>=0 else .005)*sn));return Vector((p.x,depth(p),p.y))


def mouth_motion(j,name):
    phi=j*math.tau/120;q=math.cos(phi);sn=math.sin(phi);p=mouth_point(j);v=p.copy();side=1 if name.endswith('Left') else -1;mask=smooth(-.25,.55,q*side);top=max(0,sn);bottom=max(0,-sn)
    if name in {'jawOpen','mouthClose'}:
        target=Vector((MOUTH.x+.25*q,0,MOUTH.y-.016+.052*sn));target.y=depth((target.x,target.z));return (target-p)*(1 if name=='jawOpen' else -1)
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
    h=obj('Glass Head');base=h.shape_key_add(name='Basis');patches=h['patches'];levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1];outline=contour()
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
            side='L' if name.endswith('Left') else 'R';patch=patches[side];center=Vector(obj('Glass Eye '+side)['eyeCenter']);factor=-.999 if 'Blink' in name else -.38 if 'Squint' in name else .12
            for row,t in enumerate(levels):
                for j in range(patch['size']):
                    i=patch['start']+row*patch['size']+j;p=base.data[i].co.copy();p.z+=(p.z-center.y)*factor*t;p.y=depth((p.x,p.z),outline)+.008*t*t;key.data[i].co=p
        else:
            side='L' if name.endswith('Left') else 'R';center=Vector(obj('Glass Eye '+side)['eyeCenter'])
            for v,b in zip(key.data,base.data):
                x,y,z=b.co;front=smooth(0,-.3,y);near=math.exp(-((x-center.x)/.20)**4)
                if name.startswith('brow'):v.co.z+=(.02 if 'Up' in name else -.016)*front*near*math.exp(-((z-center.y-.18)/.14)**4)
                elif name.startswith('cheekSquint'):v.co.z+=.01*front*near*math.exp(-((z-center.y+.16)/.13)**4)
                elif name=='cheekPuff':v.co.y-=.018*front*math.exp(-((z-1.66)/.15)**4)
                elif name.startswith('noseSneer'):v.co.z+=.01*front*near*math.exp(-((z-1.86)/.14)**4)
    for side,label in [('L','Left'),('R','Right')]:
        o=obj('Glass Eye '+side);base=o.shape_key_add(name='Basis');center=Vector(o['eyeCenter'])
        for kind,factor in [('eyeBlink',-.999),('eyeSquint',-.38),('eyeWide',.12)]:
            key=o.shape_key_add(name=kind+label,from_mix=False)
            for v,b in zip(key.data,base.data):
                p=b.co.copy();p.z+=(p.z-center.y)*factor;p.y=depth((p.x,p.z),outline)+.020 if kind=='eyeBlink' else b.co.y;v.co=p
        for kind,amount in [('In',-.006 if side=='L' else .006),('Out',.006 if side=='L' else -.006),('Up',.005),('Down',-.005)]:
            key=o.shape_key_add(name='eyeLook'+kind+label,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((amount,0,0) if kind in {'In','Out'} else (0,0,amount))
    oral()


def bind_head(o):
    rig=obj('Glass AvatarRig');g=o.vertex_groups.new(name='Head');g.add(list(range(len(o.data.vertices))),1,'REPLACE');o.parent=rig;m=o.modifiers.new('Head deformation','ARMATURE');m.object=rig


def oral():
    n=120;inner=[mouth_point(j) for j in range(n)];rings=[]
    for row in range(13):
        t=row/12;ring=[]
        for j,p in enumerate(inner):
            phi=j*math.tau/n;rear=Vector((MOUTH.x+.23*math.cos(phi),p.y+.20,MOUTH.y-.005+.060*math.sin(phi)));v=p.lerp(rear,t);v.y+=.004*(1-t);ring.append(v)
        rings.append(ring)
    cavity=closed_rings('Glass Oral Cavity',rings,mat('Oral interior'));bm=bmesh.new();bm.from_mesh(cavity.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[13*n]],context='VERTS');bm.to_mesh(cavity.data);bm.free();bind_head(cavity);base=cavity.shape_key_add(name='Basis')
    for name in CHANNELS:
        if not name.startswith(('jaw','mouth')):continue
        key=cavity.shape_key_add(name=name,from_mix=False);deltas=[mouth_motion(j,name) for j in range(n)]
        for i,(v,b) in enumerate(zip(key.data,base.data)):v.co=b.co+deltas[i%n]*(1-smooth(.1,.8,min(1,i//n/12)))
    for row,zc in [('Upper',MOUTH.y+.024),('Lower',MOUTH.y-.009)]:
        parts=[ellipsoid(f'Glass {row} Tooth {i}',(MOUTH.x+(i-2.5)*.040,-.19,zc),(.018,.025,.024),mat('Teeth'),nr=8,nc=16) for i in range(6)]
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts:o.select_set(True)
        bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='Glass '+row+' Teeth';bind_head(o);base=o.shape_key_add(name='Basis')
        for name,sign in [('jawOpen',1),('mouthClose',-1)]:
            key=o.shape_key_add(name=name,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((0,0,sign*(-.003 if row=='Upper' else -.035)))
    nr,nc=49,24;rings=[]
    for i in range(nr):
        t=i/(nr-1);tip=math.sqrt(max(.02,1-t**8));rings.append([(MOUTH.x+.065*tip*math.cos(j*math.tau/nc),-.12-.09*t,MOUTH.y-.028+.016*tip*math.sin(j*math.tau/nc)) for j in range(nc)])
    o=closed_rings('Glass Long Tongue',rings,mat('Tongue'));bind_head(o);base=o.shape_key_add(name='Basis')
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
    p=obj('Glass AvatarRig').pose.bones[name];p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion(Vector(axis),angle);bpy.context.view_layer.update()


def bake_material():
    reset();s=bpy.context.scene;s.cycles.samples=8;skin=mat('Skin');skin.use_fake_user=True;obj('Glass Head').data.materials[0]=skin
    objects=[o for o in s.objects if o.type=='MESH' and skin in list(o.data.materials)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
    node=skin.node_tree.nodes.new('ShaderNodeTexImage');skin.node_tree.nodes.active=node;images={}
    for name,size,kind in [('basecolor',2048,'DIFFUSE'),('normal',1024,'NORMAL'),('emission',1024,'EMIT')]:
        atlas=bpy.data.images.new('Glass aqua '+name,width=size,height=size);node.image=atlas
        if kind=='NORMAL':atlas.colorspace_settings.name='Non-Color';bpy.ops.object.bake(type=kind,use_clear=False,margin=8,normal_space='TANGENT')
        elif kind=='DIFFUSE':bpy.ops.object.bake(type=kind,pass_filter={'COLOR'},use_clear=False,margin=8)
        else:bpy.ops.object.bake(type=kind,use_clear=False,margin=8)
        atlas.filepath_raw=str(GLB.parent/f'glass-aqua-{name}.png');atlas.file_format='PNG';atlas.save();atlas.pack();images[name]=atlas
    baked=plain_material('Glass Aqua - Runtime PBR',(.004,.06,.08),.14);n=baked.node_tree.nodes;l=baked.node_tree.links;p=n['Principled BSDF'];p.inputs['Specular IOR Level'].default_value=.5;p.inputs['Metallic'].default_value=.22;p.inputs['Coat Weight'].default_value=1;p.inputs['Coat Roughness'].default_value=.09;p.inputs['IOR'].default_value=1.46;p.inputs['Transmission Weight'].default_value=.65
    for name,target in [('basecolor','Base Color'),('emission','Emission Color')]:
        tex=n.new('ShaderNodeTexImage');tex.image=images[name];l.new(tex.outputs['Color'],p.inputs[target])
    p.inputs['Emission Strength'].default_value=0
    tex=n.new('ShaderNodeTexImage');tex.image=images['normal'];normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
    for o in objects:o.data.materials[0]=baked
    head_material=baked.copy();head_material.name='Glass dark optical head - Runtime PBR';head_material.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=0;obj('Glass Head').data.materials[0]=head_material
    s.cycles.samples=32;print('Color, tangent normal and warm emission atlases baked; editable 3D material retained.')


def validate():
    from reference_rig_checks import validate as check
    return check('Glass','Glass AvatarRig',QA,obj('Glass Head')['patches']['mouth']['start'],reset,rotate,expression)


def export_runtime():
    reset();rig=obj('Glass AvatarRig');bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in {'MESH','ARMATURE'}:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_morph=True,export_morph_normal=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    rig.hide_set(True);bpy.context.scene['status']='Isolated review rig; visual acceptance and physical ZED/Orin checks still required.';bpy.ops.wm.save_as_mainfile(filepath=str(OUT))


def view(angle=False):
    s=bpy.context.scene;s.camera.location=(4,-8,3) if angle else (0,-8,1.70);s.camera.rotation_euler=(Vector((0,0,1.70))-s.camera.location).to_track_quat('-Z','Y').to_euler()
    for o in s.objects:
        if o.type in {'CAMERA','LIGHT','ARMATURE'}:o.hide_set(True)
    for a in bpy.context.screen.areas:
        if a.type=='VIEW_3D':
            sp=a.spaces.active;sp.shading.type='MATERIAL';sp.overlay.show_cursor=False;sp.overlay.show_floor=False;sp.overlay.show_axis_x=False;sp.overlay.show_axis_y=False;sp.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2);sp.region_3d.view_location=(-1.4,0,1.6);sp.region_3d.view_distance=5.5;sp.region_3d.view_perspective='ORTHO'


def render(name):bpy.context.scene.render.filepath=str(QA/(name+'.png'));bpy.ops.render.render(write_still=True)
