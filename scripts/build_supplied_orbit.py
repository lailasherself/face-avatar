"""Fresh solid Orbit form study traced from the user's PNG, through live MCP."""
import bpy
import bmesh
import math
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from complete_cosmic_likeness import loop,inside,tube,ellipsoid
from complete_clay_likeness import mesh,closed_rings,plain_material,profile

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'.context/attachments/8gfKpO/lailasherself_purple_alien_from_atlanta_--ar_34_--sref_httpss_77004502-1809-4f55-895b-87757aedf540_1 (1).png'
QA=ROOT/'.context/qa/orbit-fresh-reference'
OUT=ROOT/'blender/likeness-trials/orbit-image-source.blend'
OUTLINE=[(261,410),(269,362),(295,321),(342,291),(401,276),(465,272),(521,281),(579,300),(626,326),(657,365),(675,411),(684,470),(683,532),(676,581),(662,622),(635,650),(598,670),(552,682),(494,687),(432,685),(376,680),(332,666),(299,647),(276,617),(265,579),(261,523),(260,466)]
EYES={'R':[(328,515),(342,507),(368,511),(393,519),(421,530),(446,536),(464,539),(451,547),(426,554),(398,555),(373,550),(350,539),(334,527)],
      'L':[(573,542),(593,534),(614,527),(634,518),(652,516),(664,521),(667,532),(664,544),(654,553),(637,558),(615,556),(591,550)]}
MOUTH=Vector(((504-464)/300,(1150-602)/300))
HC=Vector((.025,(1150-481)/300))


def point(x,z,y=0):return Vector(((x-464)/300,y,(1150-z)/300))
def obj(n):return bpy.context.scene.objects['Orbit '+n]
def mat(n):return bpy.data.materials[bpy.context.scene['orbitMaterials'][n]]
def outline():return [Vector((p.x,p.z)) for p in [point(*v) for v in loop(OUTLINE,4)]]


def depth(p,poly=None):
    poly=poly or outline();d=Vector(p)-HC
    if d.length<1e-8:return -.45
    hits=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        e=b-a;det=d.x*e.y-d.y*e.x
        if abs(det)<1e-10:continue
        c=a-HC;t=(c.x*e.y-c.y*e.x)/det;u=(c.x*d.y-c.y*d.x)/det
        if t>0 and -1e-6<=u<=1.000001:hits.append(t)
    r=1/min(hits) if hits else 1
    return -.45*math.sqrt(max(0,1-r*r))


def scene():
    QA.mkdir(parents=True,exist_ok=True)
    s=bpy.data.scenes.new('Orbit - Fresh Supplied Image Build');bpy.context.window.scene=s
    s['sourceReference']=str(REF);s['sourceMethod']='New traced geometry; no old model imported; reference image is comparison only'
    s['status']='Fresh unrigged form study; not a live replacement'
    colors=[('Skin',(.40,.255,.52),.79),('Belly',(.48,.255,.34),.76),('Orange',(.95,.22,.007),.3),('Gold',(.96,.42,.008),.18),('Pupil',(.0007,.0012,.0006),.045),('Lips',(.035,.065,.085),.56),('Cavity',(.002,.001,.002),.95)]
    s['orbitMaterials']={n:plain_material('Orbit Fresh '+n,c,r).name for n,c,r in colors}
    for label in ['Gold','Pupil','Orange']:
        p=mat(label).node_tree.nodes['Principled BSDF'];p.inputs['Coat Weight'].default_value=.65;p.inputs['Coat Roughness'].default_value=.05
    image=bpy.data.images.load(str(REF),check_existing=True);image.pack()
    ref=bpy.data.objects.new('Orbit supplied PNG - comparison only',None);s.collection.objects.link(ref)
    ref.empty_display_type='IMAGE';ref.data=image;ref.empty_display_size=1232/300;ref.location=(-3.25,.8,(1150-616)/300);ref.rotation_euler=(math.pi/2,0,0);ref.hide_render=True
    world=bpy.data.worlds.new('Orbit fresh review world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.19,.21,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;s.world=world
    for name,location,power,size in [('Key',(-3,-4,6),330,3),('Fill',(3,-3,3),110,3),('Rim',(1,3,5),160,3)]:
        d=bpy.data.lights.new('Orbit fresh '+name,'AREA');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=location;o.rotation_euler=(Vector((0,0,1.8))-o.location).to_track_quat('-Z','Y').to_euler();d.energy=power;d.size=size
    d=bpy.data.cameras.new('Orbit fresh camera');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);s.camera=o;d.type='ORTHO';d.ortho_scale=1232/300
    o.location=(0,-9,(1150-616)/300);o.rotation_euler=(math.pi/2,0,0)
    s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=928;s.render.resolution_y=1232;s.render.resolution_percentage=100
    s.view_settings.view_transform='Standard'


def head():
    poly=outline();count=len(poly);front=[HC+(p-HC)*.975 for p in poly]
    apertures={side:[Vector((p.x,p.z)) for p in [point(*v) for v in loop(points,6)]] for side,points in EYES.items()}
    centers={side:sum(points,Vector((0,0)))/len(points) for side,points in apertures.items()}
    holes={side:[centers[side]+(p-centers[side])*1.28 for p in points] for side,points in apertures.items()}
    holes['mouth']=[MOUTH+Vector((.26*math.cos(j*math.tau/120),.12*math.sin(j*math.tau/120))) for j in range(120)]
    coords=list(front);constraints=[(i,(i+1)%count) for i in range(count)];indexes={}
    for label,points in holes.items():
        start=len(coords);coords+=points;indexes[label]=list(range(start,len(coords)));constraints.extend((start+j,start+(j+1)%len(points)) for j in range(len(points)))
    for r in [.95,.91,.85,.78,.69,.60,.50,.39,.28,.17,.07]:
        for p in poly:
            q=HC+(p-HC)*r
            if not any(inside(q,h) for h in holes.values()):coords.append(q)
    dv,de,df,ov,oe,of=delaunay_2d_cdt(coords,constraints,[],0,1e-7);mapping={j:i for i,ids in enumerate(ov) for j in ids}
    vs=[Vector((p.x,depth(p,poly),p.y)) for p in dv];fs=[];lip_faces=[]
    for f in df:
        center=sum((dv[i] for i in f),Vector((0,0)))/len(f)
        if inside(center,front) and not any(inside(center,h) for h in holes.values()):fs.append(tuple(f))
    previous=[mapping[i] for i in range(count)]
    for r,back in [(r,False) for r in [.986,.996,1]]+[(r,True) for r in [.996,.986,.965,.93,.88,.80,.71,.60,.48,.35,.21,.08]]:
        current=[]
        for p in poly:
            q=HC+(p-HC)*r;current.append(len(vs));vs.append(Vector((q.x,.38*math.sqrt(1-r*r) if back else depth(q,poly),q.y)))
        for j in range(count):fs.append((previous[j],previous[(j+1)%count],current[(j+1)%count],current[j]))
        previous=current
    ci=len(vs);vs.append(Vector((HC.x,.38,HC.y)));fs.extend((previous[j],previous[(j+1)%count],ci) for j in range(count))
    patches={};levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1]
    for label,outer in holes.items():
        n=len(outer);previous=[mapping[i] for i in indexes[label]];start=len(vs)
        for t in levels:
            current=[]
            for j,a in enumerate(outer):
                if label=='mouth':
                    phi=j*math.tau/n;sn=math.sin(phi);inner=MOUTH+Vector((.172*math.cos(phi),.014*sn*sn+(.006 if sn>=0 else .005)*sn))
                else:inner=apertures[label][j]
                p=a.lerp(inner,t);current.append(len(vs));ridge=.009*math.sin(t*math.pi) if label!='mouth' else .012*math.sin(t*math.pi)
                vs.append(Vector((p.x,depth(p,poly)-ridge,p.y)))
            for j in range(n):
                if label=='mouth' and t>.75:lip_faces.append(len(fs))
                fs.append((previous[j],previous[(j+1)%n],current[(j+1)%n],current[j]))
            previous=current
        patches[label]={'start':start,'size':n}
    h=mesh('Orbit Head',vs,fs,mat('Skin'));h['patches']=patches;h['armCollisionSurface']=True;h.data.materials.append(mat('Lips'))
    for i in lip_faces:h.data.polygons[i].material_index=1
    for side,points in apertures.items():
        center=centers[side];rings=[];n=len(points)
        for i in range(49):
            r=1.015*(1-i/49)
            rings.append([(p.x,depth(p,poly)+.011-.007*(1-r*r),p.y) for p in [center+(v-center)*r for v in points]])
        eye=closed_rings('Orbit Eye '+side,rings,mat('Gold'));eye.data.materials.append(mat('Pupil'))
        bm=bmesh.new();bm.from_mesh(eye.data);bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[bm.verts[49*n]],context='VERTS');bm.to_mesh(eye.data);bm.free()
        pupil=point(390,524) if side=='R' else point(638,536);rx,rz=(.078,.089) if side=='R' else (.066,.083)
        for face in eye.data.polygons:
            p=sum((eye.data.vertices[i].co for i in face.vertices),Vector())/len(face.vertices)
            if ((p.x-pupil.x)/rx)**2+((p.z-pupil.z)/rz)**2<1:face.material_index=1
    ellipsoid('Orbit Mouth interior',(MOUTH.x,depth(MOUTH)+.06,MOUTH.y),(.21,.055,.055),mat('Cavity'))


def form():
    parts=[];stations=[(660,464,88),(690,464,143),(744,469,161),(807,474,167),(873,474,154),(935,471,139),(978,468,110)]
    rings=[]
    for i in range(72):
        py=660+(978-660)*i/71;cx=profile([(z,x) for z,x,r in stations],py);rx=profile([(z,r) for z,x,r in stations],py)/300
        p=point(cx,py);rings.append([(p.x+rx*math.cos(j*math.tau/72),rx*.63*math.sin(j*math.tau/72),p.z) for j in range(72)])
    parts.append(closed_rings('Orbit Torso',rings,mat('Skin')))
    arms={'R':[(303,707,.035),(238,720,.015),(189,659,-.14),(142,601,-.29)],'L':[(600,711,.045),(644,774,.015),(708,735,-.14),(770,675,-.29)]}
    digit_pixels={
        'R':{'Thumb':[(164,593),(185,586),(207,575),(224,557)],'Index':[(143,559),(143,532),(141,505),(140,480)],'Middle':[(109,564),(93,547),(77,532),(66,520)],'Ring':[(104,591),(82,593),(57,595),(35,597)]},
        'L':{'Thumb':[(757,666),(733,657),(710,642),(693,647)],'Index':[(789,639),(799,614),(806,586),(810,567)],'Middle':[(813,679),(848,656),(878,636),(897,621)]},
    }
    for side,pixels in arms.items():
        p=[point(x,z,y) for x,z,y in pixels];parts.append(tube('Orbit Arm '+side,[point(465,705,.03),*p],[.16,.175,.185,.145,.13],mat('Skin'),rings=80,sides=40))
        palm=point(137,583,-.31) if side=='R' else point(786,659,-.31)
        parts.append(ellipsoid('Orbit Palm '+side,palm,(.19,.115,.175),mat('Skin')))
        for digit,coords in digit_pixels[side].items():
            path=[point(x,z,-.32-.015*i) for i,(x,z) in enumerate(coords)];r=.061 if digit!='Thumb' else .066
            parts.append(tube('Orbit '+digit+' '+side,path,[r*1.15,r,r*.91,r*.87],mat('Skin'),rings=38,sides=28))
            parts.append(ellipsoid('Orbit '+digit+' Pad '+side,path[-1],(r,r*.87,r*1.06),mat('Skin'),nr=20,nc=32))
        x=342 if side=='R' else 594
        path=[point(x,909,.01),point(x-8 if side=='R' else x+5,1004,.015),point(x-10 if side=='R' else x+12,1102 if side=='L' else 1090,-.04)]
        parts.append(tube('Orbit Leg '+side,path,[.16,.235,.18],mat('Skin'),rings=44,sides=40))
        foot=point(328,1098,-.14) if side=='R' else point(613,1120,-.14)
        parts.append(ellipsoid('Orbit Foot '+side,foot,(.28,.25,.135),mat('Skin')))
        for j in range(3):parts.append(ellipsoid('Orbit Toe '+side+str(j),(foot.x+(j-1)*.14,-.33,foot.z-.016),(.097,.17,.083),mat('Skin'),nr=20,nc=32))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='Orbit Body'
    mod=o.modifiers.new('Continuous native arms palms fingers and feet','REMESH');mod.mode='VOXEL';mod.voxel_size=.011;mod.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=o.modifiers.new('Sculpted junction smoothing','SMOOTH');mod.factor=.6;mod.iterations=4;bpy.ops.object.modifier_apply(modifier=mod.name)
    o['referenceAnatomy']='Four visible camera-left digits and three visible camera-right digits as drawn; hidden anatomy not established by the single image'
    o['referenceArmPixels']=str(arms);o['referenceDigitPixels']=str(digit_pixels)


def antennae():
    specs=[('Rear left',[(361,322,.10),(263,240,.14),(179,180,.13),(118,205,.10),(82,291,.02)],(80,316,.015),(.135,.12,.10)),
           ('Front left',[(404,329,-.015),(357,255,-.04),(294,181,-.10),(220,153,-.12),(208,228,-.15)],(217,253,-.17),(.156,.125,.155)),
           ('Right',[(584,329,.015),(626,245,.005),(691,190,-.04),(762,198,-.10),(832,290,-.14)],(847,319,-.17),(.155,.135,.17))]
    for label,path,tip,size in specs:
        pts=[point(x,z,y) for x,z,y in path]
        tube('Orbit Antenna '+label,pts,[.105,.09,.081,.076,.08],mat('Skin'),rings=100,sides=40)
        collar=point(path[-1][0],path[-1][1],path[-1][2]);ellipsoid('Orbit Collar '+label,collar,(.16,.14,.07),mat('Skin'))
        ellipsoid('Orbit Orange tip '+label,point(*tip),size,mat('Orange'))


def clay():
    for label in ['Skin','Belly']:
        m=mat(label);n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];p.inputs['Specular IOR Level'].default_value=.22
        tex=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=115;noise.inputs['Detail'].default_value=3;l.new(tex.outputs['Object'],noise.inputs['Vector'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.4;bump.inputs['Distance'].default_value=.009;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
    body=obj('Body');body.data.materials.append(mat('Belly'))
    for polygon in body.data.polygons:
        p=polygon.center
        if p.y<-.07 and ((p.x-.025)/.54)**2+((p.z-.99)/.49)**2<1:polygon.material_index=1
    m=mat('Belly');n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];previous=p.inputs['Normal'].links[0].from_socket
    wave=n.new('ShaderNodeTexWave');wave.bands_direction='Z';wave.inputs['Scale'].default_value=38;wave.inputs['Distortion'].default_value=12;wave.inputs['Detail'].default_value=3
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.40;bump.inputs['Distance'].default_value=.009;l.new(wave.outputs['Color'],bump.inputs['Height']);l.new(previous,bump.inputs['Normal']);l.new(bump.outputs['Normal'],p.inputs['Normal'])


def save_render():
    s=bpy.context.scene;s.render.filepath=str(QA/'fresh-front.png');bpy.ops.render.render(write_still=True)
    bpy.data.libraries.write(str(OUT),{s},fake_user=True)
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_overlays=False;area.spaces.active.region_3d.view_perspective='CAMERA'
    print('Saved fresh image-traced source, unrigged:',OUT)
