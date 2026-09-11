"""Coral form study from the supplied PNG; run stages through live Blender MCP."""
import bpy
import math
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from complete_cosmic_likeness import loop, inside, tube, ellipsoid
from complete_clay_likeness import mesh, closed_rings, profile, plain_material

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / '.context/attachments/ZWD70v/lailasherself_add_a_body_--ar_11_--edit_httpss.mj.runuvJVp0ni_da9be720-1394-41cb-abb8-cb0c68dc0d38_0.png'
OUT = ROOT / 'blender/likeness-trials/coral-image-source.blend'
QA = ROOT / '.context/qa/coral-fresh-reference'
OUTLINE = [(340,364),(353,306),(389,266),(436,242),(490,232),(549,244),(600,273),(634,318),(654,369),(651,420),(635,478),(622,546),(602,584),(561,607),(499,612),(443,603),(410,580),(391,546),(379,493),(365,441)]
MOUTH = Vector(((496-512)/250,(819-532)/250))
CENTER = Vector(((498-512)/250,(819-421)/250))


def point(px,py,y=0):
    return Vector(((px-512)/250,y,(819-py)/250))


def mat(name):
    return bpy.data.materials[bpy.context.scene['coralMaterials'][name]]


def contour():
    return [Vector((p.x,p.z)) for p in (point(*p) for p in loop(OUTLINE,5))]


def depth(p,poly=None):
    poly=poly or contour();d=Vector(p)-CENTER;hits=[]
    if d.length<1e-8:return -.34
    for a,b in zip(poly,poly[1:]+poly[:1]):
        e=b-a;det=d.x*e.y-d.y*e.x
        if abs(det)<1e-10:continue
        c=a-CENTER;t=(c.x*e.y-c.y*e.x)/det;u=(c.x*d.y-c.y*d.x)/det
        if t>0 and -1e-6<=u<=1.000001:hits.append(t)
    r=1/min(hits) if hits else 1
    return -.34*math.sqrt(max(0,1-r*r))


def scene():
    QA.mkdir(parents=True,exist_ok=True)
    s=bpy.data.scenes.new('Coral - Fresh Supplied Image Build');bpy.context.window.scene=s
    s['sourceReference']=str(REF);s['sourceMethod']='New PNG-contour geometry; no old model geometry and no image projection'
    s['status']='Unrigged form study; not a live replacement'
    specs=[('Skin',(.28,.105,.16),.55),('Body',(.075,.044,.083),.65),('Lips',(.57,.055,.065),.42),('Eye',(.90,.71,.36),.25),('Pupil',(.001,.045,.082),.12),('Mouth',(.028,.002,.008),.9)]
    s['coralMaterials']={n:plain_material('Coral Fresh '+n,c,r).name for n,c,r in specs}
    ref=bpy.data.objects.new('Coral supplied PNG - comparison only',None);s.collection.objects.link(ref)
    ref.empty_display_type='IMAGE';ref.data=bpy.data.images.load(str(REF),check_existing=True);ref.data.pack()
    ref.empty_display_size=1024/250;ref.location=(-3.4,.8,(819-512)/250);ref.rotation_euler=(math.pi/2,0,0);ref.hide_render=True
    w=bpy.data.worlds.new('Coral fresh world');w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.19,.26,.27,1);w.node_tree.nodes['Background'].inputs[1].default_value=.5;s.world=w
    for name,loc,power,size in [('Key',(-3,-4,6),380,3),('Fill',(3,-3,3),120,3),('Rim',(1,3,5),160,3)]:
        d=bpy.data.lights.new('Coral fresh '+name,'AREA');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler();d.energy=power;d.size=size
    d=bpy.data.cameras.new('Coral fresh camera');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);s.camera=o;d.type='ORTHO';d.ortho_scale=1024/250
    o.location=(0,-9,(819-512)/250);o.rotation_euler=(math.pi/2,0,0)
    s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1024;s.render.resolution_y=1024;s.render.resolution_percentage=100;s.view_settings.view_transform='Standard'


def head():
    poly=contour();n=len(poly);front=[CENTER+(p-CENTER)*.975 for p in poly]
    outer=[MOUTH+Vector((.465*math.cos(j*math.tau/160),.18*math.sin(j*math.tau/160))) for j in range(160)]
    coords=front+outer;edges=[(j,(j+1)%n) for j in range(n)]+[(n+j,n+(j+1)%160) for j in range(160)]
    for r in [.95,.90,.84,.77,.68,.58,.47,.35,.22,.1]:
        for p in poly:
            q=CENTER+(p-CENTER)*r
            if not inside(q,outer):coords.append(q)
    dv,de,df,ov,oe,of=delaunay_2d_cdt(coords,edges,[],0,1e-7);mapping={j:i for i,ids in enumerate(ov) for j in ids}
    verts=[(p.x,depth(p,poly),p.y) for p in dv];faces=[];lip_faces=[]
    for f in df:
        c=sum((dv[i] for i in f),Vector((0,0)))/len(f)
        if inside(c,front) and not inside(c,outer):faces.append(tuple(f))
    previous=[mapping[i] for i in range(n)]
    for r,back in [(r,False) for r in [.99,1]]+[(r,True) for r in [.99,.97,.93,.87,.78,.66,.52,.37,.21,.07]]:
        current=[]
        for p in poly:
            q=CENTER+(p-CENTER)*r;current.append(len(verts));verts.append((q.x,.29*math.sqrt(1-r*r) if back else depth(q,poly),q.y))
        faces.extend((previous[j],previous[(j+1)%n],current[(j+1)%n],current[j]) for j in range(n));previous=current
    ci=len(verts);verts.append((CENTER.x,.29,CENTER.y));faces.extend((previous[j],previous[(j+1)%n],ci) for j in range(n))
    previous=[mapping[n+j] for j in range(160)]
    for k in range(1,17):
        t=k/16;current=[]
        for j,a in enumerate(outer):
            phi=j*math.tau/160;sn=math.sin(phi)
            inner=MOUTH+Vector((.365*math.cos(phi),.054*sn-.018*math.cos(phi*2)))
            p=a.lerp(inner,t);current.append(len(verts));verts.append((p.x,depth(p,poly)-.055*math.sin(t*math.pi/1.35),p.y))
        for j in range(160):
            if t>.35:lip_faces.append(len(faces))
            faces.append((previous[j],previous[(j+1)%160],current[(j+1)%160],current[j]))
        previous=current
    pocket=[]
    for j in range(160):
        p=Vector(verts[previous[j]]);p.y+=.16;pocket.append(len(verts));verts.append(tuple(p))
    cavity_start=len(faces);faces.extend((previous[j],previous[(j+1)%160],pocket[(j+1)%160],pocket[j]) for j in range(160))
    ci=len(verts);verts.append((MOUTH.x,-.08,MOUTH.y));faces.extend((pocket[j],pocket[(j+1)%160],ci) for j in range(160))
    h=mesh('Coral Head',verts,faces,mat('Skin'));h.data.materials.append(mat('Lips'));h.data.materials.append(mat('Mouth'))
    for i in lip_faces:h.data.polygons[i].material_index=1
    for i in range(cavity_start,len(faces)):h.data.polygons[i].material_index=2
    ellipsoid('Coral Nose',point(496,409,-.295),(.104,.185,.227),mat('Skin'),nr=48,nc=64)
    for side,x in [('R',406),('L',588)]:
        p=point(x,383,-.315)
        ellipsoid('Coral Eye '+side,p,(.20,.205,.211),mat('Eye'),nr=64,nc=96)
        pupil=point(x+(0 if side=='R' else 5),397,-.513)
        ellipsoid('Coral Pupil '+side,pupil,(.044,.014,.045),mat('Pupil'),nr=32,nc=48)
        ring=[]
        for j in range(81):
            phi=j*math.tau/80;ring.append((p.x+.221*math.cos(phi),-.295,p.z+.232*math.sin(phi)))
        tube('Coral Eye rim '+side,ring,[.032]*len(ring),mat('Skin'),rings=160,sides=20)


def appendages():
    crowns=[([(369,320),(334,282),(320,251)],(.128,.125,.135)),([(437,276),(416,226),(394,187)],(.137,.13,.145)),([(502,257),(508,211),(509,159)],(.127,.12,.13)),([(563,270),(594,224),(619,185)],(.135,.13,.14)),([(622,319),(662,281),(695,244)],(.13,.12,.145)),([(357,353),(312,348),(286,339)],(.105,.10,.128)),([(642,356),(684,350),(730,336)],(.102,.095,.116))]
    for i,(pixels,size) in enumerate(crowns):
        ps=[point(x,z,.06) for x,z in pixels];tube('Coral Crown stem '+str(i),ps,[.10,.085,.09],mat('Skin'),rings=48,sides=32);ellipsoid('Coral Crown tip '+str(i),ps[-1],size,mat('Skin'))
    for side,pixels in [('R',[(366,404),(333,410),(327,450),(351,468),(375,443)]),('L',[(647,411),(681,407),(690,436),(670,455),(642,465)])]:
        tube('Coral Ear '+side,[point(x,z,.015) for x,z in pixels],[.071,.080,.069,.063,.065],mat('Skin'),rings=72,sides=32)
    rings=[]
    for i in range(64):
        py=590+160*i/63;p=point(514,py,.035)
        rx=profile([(590,.21),(620,.235),(680,.28),(735,.30),(750,.285)],py)
        rings.append([(p.x+rx*math.cos(j*math.tau/64),p.y+.21*math.sin(j*math.tau/64),p.z) for j in range(64)])
    pieces=[closed_rings('Coral Torso',rings,mat('Body'))]
    for side,pixels in [('R',[(452,594),(424,655),(406,704),(403,741)]),('L',[(570,590),(597,648),(619,703),(623,736)])]:
        ps=[point(x,z,.045) for x,z in pixels];m=mat('Body') if side=='R' else mat('Skin')
        pieces.append(tube('Coral Flipper '+side,ps,[.115,.105,.099,.079],m,rings=72,sides=40));pieces.append(ellipsoid('Coral Flipper tip '+side,ps[-1],(.08,.073,.107),m))
    for side,x in [('R',474),('L',553)]:
        rings=[]
        for i in range(40):
            t=i/39;p=point(x,723+90*t,.035);rx=.112 if t<.95 else .108
            rings.append([(p.x+rx*math.cos(j*math.tau/48),p.y+.145*math.sin(j*math.tau/48),p.z) for j in range(48)])
        pieces.append(closed_rings('Coral Leg '+side,rings,mat('Body')))
    bpy.ops.object.select_all(action='DESELECT')
    for o in pieces:o.select_set(True)
    bpy.context.view_layer.objects.active=pieces[0];bpy.ops.object.join();o=bpy.context.object;o.name='Coral Body'
    mod=o.modifiers.new('Continuous flipper body','REMESH');mod.mode='VOXEL';mod.voxel_size=.008;mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=o.modifiers.new('Soft transitions','SMOOTH');mod.factor=.6;mod.iterations=4;bpy.ops.object.modifier_apply(modifier=mod.name)
    o['referenceAnatomy']='Two rounded flippers; no human hands or added fingers'
    skin_index=next(i for i,m in enumerate(o.data.materials) if m==mat('Skin'))
    for p in o.data.polygons:
        if p.center.x>.33:p.material_index=skin_index


def sculpt_joins():
    pieces=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name=='Coral Head' or o.name=='Coral Nose' or o.name.startswith(('Coral Crown','Coral Ear','Coral Eye rim')))]
    bpy.ops.object.select_all(action='DESELECT')
    for o in pieces:o.select_set(True)
    head=bpy.context.scene.objects['Coral Head'];bpy.context.view_layer.objects.active=head;bpy.ops.object.join()
    mod=head.modifiers.new('Continuous sculpted crown and face','REMESH');mod.mode='VOXEL';mod.voxel_size=.006;mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=head.modifiers.new('Blend sculpted transitions','SMOOTH');mod.factor=.65;mod.iterations=24;bpy.ops.object.modifier_apply(modifier=mod.name)
    poly=contour()
    for face in head.data.polygons:
        p=face.center;dx=p.x-MOUTH.x;dz=p.z-MOUTH.y
        if (dx/.45)**2+(dz/.151)**2<1 and p.y<depth((p.x,p.z),poly)+.01:
            face.material_index=1
        elif (dx/.39)**2+(dz/.075)**2<1 and p.y>depth((p.x,p.z),poly)+.03:
            face.material_index=2
    head['topologyStatus']='Sculpted form study; animation retopology still required'


def texture():
    for name in ['Skin','Body','Lips']:
        m=mat(name);n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF']
        tex=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=92;noise.inputs['Detail'].default_value=3;l.new(tex.outputs['Object'],noise.inputs['Vector'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.006;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
        wave=n.new('ShaderNodeTexWave');wave.bands_direction='Z';wave.inputs['Scale'].default_value=38;wave.inputs['Distortion'].default_value=9;wave.inputs['Detail'].default_value=4;l.new(tex.outputs['Object'],wave.inputs['Vector'])
        wrinkles=n.new('ShaderNodeBump');wrinkles.inputs['Strength'].default_value=.22;wrinkles.inputs['Distance'].default_value=.004;l.new(wave.outputs['Color'],wrinkles.inputs['Height']);l.new(bump.outputs['Normal'],wrinkles.inputs['Normal']);l.new(wrinkles.outputs['Normal'],p.inputs['Normal'])
        p.inputs['Coat Weight'].default_value=.09;p.inputs['Coat Roughness'].default_value=.3;p.inputs['Specular IOR Level'].default_value=.26


def save_render():
    s=bpy.context.scene;s.render.filepath=str(QA/'fresh-front.png');bpy.ops.render.render(write_still=True)
    bpy.data.libraries.write(str(OUT),{s},fake_user=True)
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_overlays=False;area.spaces.active.region_3d.view_perspective='CAMERA'
    print('Saved fresh Coral image source, unrigged:',OUT)
