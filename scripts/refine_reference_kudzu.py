"""Reference-specific Kudzu sculpt stages, run sequentially through Blender MCP."""
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector,Quaternion
from build_avatar_fleet import Mesh,material,color
from build_local_characters import smooth,bind,face,pose,uv

ROOT=Path(__file__).resolve().parents[1]
C=dict(head=(.64,.41,.62),hz=2.24,power=.72,eyes=(.305,.025,.228,.125,.203),
       eye='#f3c28c',pupil='#031b0b',upper='#063e20',lower='#064223',sleep=1.52,mouth=(.35,-.285,.011))


def foundation():
    assert 'reference-characters/kudzu-review.blend' in bpy.data.filepath
    rig=bpy.context.scene.objects['AvatarRig'];pose(rig,'T-Pose');rig.animation_data_clear()
    rig['installationApproved']=False;rig['rigVersion']='kudzu-reference-mcp-2'
    for name in ['Body','Feet','ReferenceDetails','Face','Teeth','Tongue']:
        obj=bpy.context.scene.objects.get(name)
        if obj:bpy.data.objects.remove(obj,do_unlink=True)
    skin=bpy.data.materials['kudzu skin'];p=skin.node_tree.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value=.6;p.inputs['Metallic'].default_value=.05
    tex=next(n for n in skin.node_tree.nodes if n.type=='TEX_IMAGE')
    rng=np.random.default_rng(517);size=1024
    pixels=np.ones((size,size,4),dtype=np.float32)
    grain=rng.random((size,size));pixels[:,:,:3]=np.array([.018,.30,.105])*(.65+.6*grain[:,:,None])
    flecks=rng.random((size,size))>.968
    pixels[flecks,:3]=np.array([.70,.94,.06])*(.65+.35*rng.random((int(flecks.sum()),1)))
    image=bpy.data.images.new('Kudzu embedded green mineral flecks',width=size,height=size)
    image.pixels.foreach_set(pixels.ravel());image.update();image.pack();tex.image=image
    skin.node_tree.links.new(tex.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=.09
    for key in ['upper','lower','lip']:
        mat=bpy.data.materials['kudzu '+key];shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Roughness'].default_value=.65
    return {'rig':rig.name,'embeddedSkinPixels':size*size}


def body():
    rig=bpy.context.scene.objects['AvatarRig'];skin=bpy.data.materials['kudzu skin'];mesh=Mesh()
    def torso(u,v):
        z=.69+u*1.11;a=2*math.pi*v
        rx=np.interp(u,[0,.08,.28,.60,.78,1],[.03,.235,.255,.235,.16,.105])
        return rx*math.cos(a),rx*.76*math.sin(a),z
    mesh.grid(64,64,torso,skin)
    ob=mesh.object('Kudzu tapered torso')
    def trunk(p):
        z=p.z;neck=smooth(1.53,1.77,z);chest=smooth(.95,1.4,z)
        return {'Hips':(1-neck)*(1-chest),'Chest':(1-neck)*chest,'Neck':neck}
    bind(ob,rig,trunk);uv(ob);ob['armCollisionSurface']=True
    for side,s in [('L',1),('R',-1)]:
        upper=rig.data.bones['UpperArm.'+side];wrist=rig.data.bones['Hand.'+side].head_local.x*s
        start=upper.head_local.x*s
        arm=Mesh();ts=np.linspace(0,1,48)
        points=[(s*(start+(wrist-start)*t),0,1.55) for t in ts]
        radii=[float(np.interp(t,[0,.12,.40,.51,.72,.95,1],[.112,.118,.07,.059,.085,.047,.044])) for t in ts]
        arm.tube(points,radii,skin,n=28)
        arm.ellipsoid(points[0],(.115,.112,.112),skin,n=28,rings=18)
        ob=arm.object('Kudzu shaped arm '+side)
        def weight(p):
            t=(abs(p.x)-start)/(wrist-start);elbow=smooth(.42,.61,t);hand=smooth(.94,1.07,t)
            return {'UpperArm.'+side:(1-hand)*(1-elbow),'Forearm.'+side:(1-hand)*elbow,'Hand.'+side:hand}
        bind(ob,rig,weight);uv(ob)
        leg=Mesh()
        def surface(u,v):
            z=.035+.87*u;a=2*math.pi*v
            rx=float(np.interp(u,[0,.05,.16,.30,.55,.72,1],[.07,.13,.11,.065,.085,.12,.12]))
            cx=s*(.14+.018*(1-u));y=-.06*(1-smooth(.08,.22,u))
            return cx+rx*math.cos(a),y+rx*.95*math.sin(a),z
        leg.grid(52,40,surface,skin)
        ob=leg.object('Kudzu tapered leg '+side)
        def weights(p):
            foot=1-smooth(.14,.25,p.z);shin=1-smooth(.39,.56,p.z)
            return {'Foot.'+side:foot,'Shin.'+side:(1-foot)*shin,'Thigh.'+side:(1-foot)*(1-shin)}
        bind(ob,rig,weights);uv(ob)
    pose(rig,'Standing')


def facial():
    rig=bpy.context.scene.objects['AvatarRig'];pose(rig,'T-Pose')
    mats={name:bpy.data.materials['kudzu '+name] for name in ['skin','lip','upper','lower','eye','pupil','cavity','tongue','teeth']}
    objects,surface=face(C,rig,mats);ob=objects[0]
    # The reference exposes most of the lower peach sclera, not a narrow slit.
    keys=ob.data.shape_keys.key_blocks;basis=keys['Basis']
    lower_ids=sorted({i for p in ob.data.polygons if ob.data.materials[p.material_index]==mats['lower'] for i in p.vertices})
    for j,i in enumerate(lower_ids):
        local=j%(13*40);u=(local//40)/12;phi=2*math.pi*(local%40)/40
        p=basis.data[i].co;side='Left' if p.x>0 else 'Right';cx=C['eyes'][0]*(1 if p.x>0 else -1);cy=surface(cx,C['eyes'][1])-.027;cz=C['hz']+C['eyes'][1]
        rx,ry,rz=[v+.008 for v in C['eyes'][2:]]
        for key in keys:
            angle=math.pi/2+.012 if key.name=='eyeBlink'+side else .15 if key.name=='eyeWide'+side else .56 if key.name=='eyeSquint'+side else .35
            theta=.001+u*angle
            key.data[i].co=(cx+rx*math.sin(theta)*math.cos(phi),cy+ry*math.sin(theta)*math.sin(phi),cz-rz*math.cos(theta))
    pupils=sorted({i for p in ob.data.polygons if ob.data.materials[p.material_index]==mats['pupil'] for i in p.vertices})
    for i in pupils:
        for key in keys:
            p=key.data[i].co;cx=C['eyes'][0]*(1 if p.x>0 else -1);cy=surface(cx,C['eyes'][1])-.027;cz=C['hz']+C['eyes'][1]
            x=(p.x-cx)/C['eyes'][2]*2.5;z=(p.z-cz)/C['eyes'][4]*2.5
            p.x=cx+C['eyes'][2]*x;p.z=cz+C['eyes'][4]*z;p.y=cy-(C['eyes'][3]+.003)*math.sqrt(max(.001,1-x*x-z*z))
    tongue=objects[2];tk=tongue.data.shape_keys.key_blocks
    for i,p in enumerate(tk['jawOpen'].data):
        u=(i//20)/24;p.co=tk['Basis'].data[i].co+Vector((0,0,-.07*smooth(0,.65,u)))
    ob['armCollisionSurface']=True
    for o in objects:
        for v,b in zip(o.data.vertices,o.data.shape_keys.key_blocks['Basis'].data):v.co=b.co
        for key in o.data.shape_keys.key_blocks:key.value=0
    pose(rig,'Standing')
    return {'faceVertices':len(ob.data.vertices),'channels':len(keys)-1}


def leaf(mesh,origin,length,width,angle,mat,weights):
    origin=Vector(origin);direction=Vector((math.sin(angle),0,math.cos(angle)));across=Vector((math.cos(angle),0,-math.sin(angle)))
    def shape(u,v,back=False):
        knots=[0,.12,.23,.32,.42,.52,.61,.7,.78,.86,.94,1]
        widths=[0,.25,.74,1,.75,.47,.57,.50,.34,.30,.16,0]
        j=min(len(knots)-2,max(0,int(np.searchsorted(knots,u))-1));t=smooth(knots[j],knots[j+1],u)
        edge=widths[j]*(1-t)+widths[j+1]*t
        t=2*v-1;p=origin+direction*(length*u)+across*(width*edge*t)
        p.y-=.035*math.sin(math.pi*u)*(1-t*t)
        if back:p.y+=.008
        return p
    mesh.grid(42,17,lambda u,v:shape(u,v),mat,weights,wrap=False)
    mesh.grid(42,17,lambda u,v:shape(u,1-v,True),mat,weights,wrap=False)
    points=[origin+direction*(length*t)+Vector((0,-.04*math.sin(math.pi*t)-.006,0)) for t in np.linspace(0,1,24)]
    mesh.tube(points,[.008]*24,bpy.data.materials['kudzu vein'],weights,n=6)


def foliage():
    rig=bpy.context.scene.objects['AvatarRig'];pose(rig,'T-Pose');mesh=Mesh();mat=bpy.data.materials['kudzu leaf']
    old=bpy.context.scene.objects.get('Kudzu lobed crown and climbing vines')
    if old:bpy.data.objects.remove(old,do_unlink=True)
    leaf(mesh,(0,-.31,2.75),.72,.40,-.10,mat,{'Head':1})
    for s in [-1,1]:
        leaf(mesh,(s*.36,-.11,2.72),.34,.15,s*.85,mat,{'Head':1})
        leaf(mesh,(s*.55,.02,2.57),.25,.11,s*1.4,mat,{'Head':1})
        # Twisted leaf brows are separate deformable anatomy, not painted lines.
        pts=[(s*(.12+.40*t),-.50,2.51+.035*math.sin(math.pi*t)) for t in np.linspace(0,1,24)]
        mesh.tube(pts,[.038+.012*math.sin(math.pi*t) for t in np.linspace(0,1,24)],mat,{'Head':1},n=12)
    for s in [-1,1]:
        pts=[(s*(.17+.032*math.sin(t*5*math.pi)),-.18-.015*math.cos(t*5*math.pi),.72+t*.92) for t in np.linspace(0,1,64)]
        def weights(p):
            w=smooth(.96,1.4,p.z);return {'Hips':1-w,'Chest':w}
        mesh.tube(pts,[.014]*64,bpy.data.materials['kudzu vein'],weights,n=8)
        for j in [8,26,43,57]:leaf(mesh,pts[j],.17,.10,s*(.5 if j%2 else -.5),mat,weights(Vector(pts[j])))
        for segment in ['UpperArm','Forearm','Thigh','Shin']:
            bone=rig.data.bones[segment+('.L' if s>0 else '.R')];axis=bone.tail_local-bone.head_local
            pts=[bone.head_local+axis*t+Vector((.018*math.sin(t*4*math.pi),-.10,.018*math.cos(t*4*math.pi))) for t in np.linspace(.12,.85,24)]
            mesh.tube(pts,[.012]*24,bpy.data.materials['kudzu vein'],{bone.name:1},n=8)
            leaf(mesh,pts[9],.15,.08,s*.65,mat,{bone.name:1})
    ob=mesh.object('Kudzu lobed crown and climbing vines',rig)
    pose(rig,'Standing');return {'foliageVertices':len(ob.data.vertices)}


def finish_anatomy():
    rig=bpy.context.scene.objects['AvatarRig'];pose(rig,'T-Pose')
    assert not rig.get('palmsRefitted'),'Palms already fitted'
    q=Quaternion((1,0,0),math.pi/2)
    for side in ['L','R']:
        origin=rig.data.bones['Hand.'+side].head_local.copy();hand=bpy.context.scene.objects['ArticulatedHand'+side]
        for v in hand.data.vertices:
            delta=v.co-origin;delta.z*=1.7;v.co=origin+q@delta
        hand.data.update()
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        if bone.name.startswith(('Thumb','Index','Middle','Ring')):
            origin=rig.data.edit_bones['Hand.'+bone.name[-1]].head
            bone.head=origin+q@(bone.head-origin);bone.tail=origin+q@(bone.tail-origin);bone.align_roll(Vector((0,0,-1)))
    bpy.ops.object.mode_set(mode='OBJECT')
    for bone in rig.data.bones:
        if bone.name.startswith(('Thumb','Index','Middle','Ring')):bone['fingerCurlRadians']=.75
    rig['palmsRefitted']=True
    for key in ['upper','lower','lip','leaf','vein']:
        mat=bpy.data.materials['kudzu '+key];p=mat.node_tree.nodes['Principled BSDF']
        p.inputs['Roughness'].default_value=.72;p.inputs['Coat Weight'].default_value=0;p.inputs['Specular IOR Level'].default_value=.15
        if key in C:p.inputs['Base Color'].default_value=color(C[key])
    from refine_reference_glass import rebuild_front
    rebuild_front(config=C,cavity_material='kudzu cavity',local_travel=.11,outer_travel=0)
    head=bpy.context.scene.objects['Face'];keys=head.data.shape_keys.key_blocks
    for key in keys:
        if key.name.startswith('mouth') and key.name!='mouthClose':
            for v,b in zip(key.data,keys['Basis'].data):v.co=b.co+(v.co-b.co)*.6
    for key in keys:
        for i,v in enumerate(key.data):
            if i>=6120:continue
            x,y,z=v.co;w=math.exp(-((x/.42)**6+((z-(C['hz']+C['mouth'][1]))/.11)**4))
            v.co.z+=.03*(min(1,abs(x)/.35)**2-.5)*w
    for v,b in zip(head.data.vertices,keys['Basis'].data):v.co=b.co
    pose(rig,'Standing')
